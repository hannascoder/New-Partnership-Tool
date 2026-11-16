/* Partner Finder: "Start from a UN mail or text" (owner, 16.11.2026).
   Someone pastes a UN mail; this file reads country, topics, format and language
   from it and sets the normal filters. Rules and word lists: config/dropin.yaml and
   config/topic_keywords.yaml (-> data/dropin.json, built by pipeline/build/dropin.py).
   No AI service; the text never leaves the browser (it is kept for this browser tab
   only, so the other page - Media / NGOs - can use the same text).
   PartnerDropin.analyse(text, rules) can be tested without the page. */
(function () {
  "use strict";
  const KEY = "pf-dropin";
  const CJK = /[぀-ヿ㐀-鿿豈-﫿]/;

  /* same rule as pipeline/classify/topic_text.py norm(): lower case, accents removed from Latin
     letters only, everything that is not a letter or digit becomes a space */
  function norm(text) {
    let out = "", prevAscii = false;
    for (const ch of String(text || "").toLowerCase().normalize("NFKD")) {
      if (/\p{M}/u.test(ch)) { if (!prevAscii) out += ch; continue; }
      if (/[\p{L}\p{N}]/u.test(ch)) { out += ch; prevAscii = ch.charCodeAt(0) < 128; }
      else { out += " "; prevAscii = false; }
    }
    return out.split(/\s+/).filter(Boolean).join(" ");
  }
  const reEsc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const has = (line, list) => { const l = line.toLowerCase(); return list.some((x) => l.includes(String(x).toLowerCase())); };

  /* word tables are prepared once per page */
  function prepare(D) {
    if (D._ready) return D;
    const add = (table, word, value) => {
      const key = norm(word);
      if (!key) return;
      if (CJK.test(key)) { D._cjk.push([key.replace(/ /g, ""), table, value]); return; }
      (table.get(key) || table.set(key, new Set()).get(key)).add(value);
      D._maxlen = Math.max(D._maxlen, key.split(" ").length);
    };
    D._maxlen = 1; D._cjk = []; D._prefix = [];
    D._strong = new Map(); D._context = new Map(); D._place = new Map(); D._caps = [];
    Object.entries(D.topics).forEach(([t, w]) => {
      w.strong.forEach((x) => (x.endsWith("*") ? D._prefix.push([norm(x.slice(0, -1)), t]) : add(D._strong, x, t)));
      w.context.forEach((x) => add(D._context, x, t));
    });
    Object.entries(D.places).forEach(([c, names]) => names.forEach((n) => {
      // names in CAPITALS (UNIFIL, DRC, US) only count when written like that
      if (/^[A-Z0-9]{2,10}$/.test(n)) D._caps.push([new RegExp("(?<![\\p{L}\\p{N}])" + reEsc(n) + "(?![\\p{L}\\p{N}$])", "gu"), c, n]);
      else add(D._place, n, c);
    }));
    D._exclude = D.exclude.map(norm).filter(Boolean);
    D._ready = true;
    return D;
  }

  /* every phrase of the table found in the text: [[phrase, values, token position]];
     consume = a long name hides the short ones inside it ("South Sudan" is not also "Sudan") */
  function hits(D, t, table, consume) {
    const toks = t.split(" "), out = [];
    for (let i = 0; i < toks.length; i++) {
      for (let L = Math.min(D._maxlen, toks.length - i); L > 0; L--) {
        const key = toks.slice(i, i + L).join(" "), v = table.get(key);
        if (v) { out.push([key, v]); if (consume) { i += L - 1; break; } }
      }
    }
    if (CJK.test(t)) { const flat = t.replace(/ /g, ""); D._cjk.forEach(([key, tb, val]) => { if (tb === table && flat.includes(key)) out.push([key, new Set([val])]); }); }
    return out;
  }

  function analyse(text, D) {
    prepare(D);
    const lines = String(text || "").split(/\r?\n/).map((l) => l.trim());
    let cut = lines.findIndex((l) => has(l, D.technical_markers));
    if (cut < 0) cut = lines.length;
    const body = lines.slice(0, cut).filter((l) => l && !has(l, D.skip_lines));
    const tech = lines.slice(cut).join("\n");
    const strip = (s) => D.ignore_phrases.reduce((a, p) => a.replace(new RegExp(reEsc(p), "gi"), " "), s);
    const clean = (s) => { let t = " " + norm(strip(s)) + " "; D._exclude.forEach((e) => { t = t.split(" " + e + " ").join(" "); }); return t.trim(); };
    const headline = body.find((l) => l.length <= 220) || "";
    const parts = [[headline, true], [body.filter((l) => l !== headline).join("\n"), false]];

    // countries: 3 points in the headline, 1 point for every other mention
    const cs = {};
    const cHit = (code, word, head) => { const e = cs[code] || (cs[code] = { code, score: 0, found: new Set() }); e.score += head ? 3 : 1; e.found.add(word); };
    parts.forEach(([raw, head]) => {
      hits(D, clean(raw), D._place, true).forEach(([w, v]) => v.forEach((c) => cHit(c, w, head)));
      const r = strip(raw);
      D._caps.forEach(([re, c, n]) => (r.match(re) || []).forEach(() => cHit(c, n, head)));
    });
    let countries = Object.values(cs).sort((a, b) => b.score - a.score);
    if (countries.length) countries = countries.filter((c) => c.score >= countries[0].score * D.limits.country_share).slice(0, D.limits.max_countries);

    // topics: every different strong word 2 points (4 in the headline); context words 1 point, only next to a strong word
    const ts = {};
    const tGet = (t) => ts[t] || (ts[t] = { id: t, strong: new Map(), context: new Set() });
    parts.forEach(([raw, head]) => {
      const t = clean(raw);
      hits(D, t, D._strong, false).forEach(([w, v]) => v.forEach((id) => { const m = tGet(id).strong; m.set(w, Math.max(m.get(w) || 0, head ? 4 : 2)); }));
      t.split(" ").forEach((tok) => D._prefix.forEach(([pre, id]) => { if (pre && tok.startsWith(pre)) { const m = tGet(id).strong; m.set(tok, Math.max(m.get(tok) || 0, head ? 4 : 2)); } }));
      hits(D, t, D._context, false).forEach(([w, v]) => v.forEach((id) => tGet(id).context.add(w)));
    });
    let topics = Object.values(ts).filter((e) => e.strong.size).map((e) => {
      // "peacekeeping" inside "peacekeeping mission" is the same find, not two
      const words = [...e.strong.keys()], own = words.filter((w) => !words.some((x) => x !== w && (" " + x + " ").includes(" " + w + " ")));
      return { id: e.id, score: own.reduce((n, w) => n + e.strong.get(w), 0) + e.context.size, found: own.concat([...e.context].filter((w) => !e.strong.has(w))) };
    }).sort((a, b) => b.score - a.score);
    if (topics.length) topics = topics.filter((t) => t.score >= D.limits.min_topic_score && t.score >= topics[0].score * D.limits.topic_share).slice(0, D.limits.max_topics);

    // format: the kind of material named most often (letterhead and technical lines count here)
    const whole = " " + norm(text) + " ";
    const count = (w) => whole.split(" " + norm(w) + " ").length - 1;
    const fs = Object.entries(D.formats).map(([id, words]) => [id, words.reduce((n, w) => n + count(w), 0)]).filter((f) => f[1]);
    const top = Math.max(0, ...fs.map((f) => f[1]));
    const formats = fs.filter((f) => f[1] === top).map((f) => f[0]);
    const shape = D.shapes.find((s) => new RegExp("(?<![\\w:])" + reEsc(s) + "(?![\\w:])", "i").test(tech)) || "";
    const duration = (tech.match(/(?<![\d:])\d{1,2}:\d{2}(?::\d{2})?(?![\d:])/) || [""])[0];

    // language: its English name directly before or after a word like "subtitles"
    const langs = [];
    Object.entries(D.languages).forEach(([name, code]) => {
      const n = norm(name.split(" (")[0]);
      if (n && !langs.includes(code) && D.language_words.some((w) => whole.includes(" " + n + " " + norm(w) + " ") || whole.includes(" " + norm(w) + " " + n + " ") || whole.includes(" " + norm(w) + " in " + n + " "))) langs.push(code);
    });
    return { headline, countries: countries.map((c) => ({ code: c.code, score: c.score, found: [...c.found] })), topics, formats, shape, duration, langs };
  }
  window.PartnerDropin = { analyse, norm };
  if (typeof document === "undefined" || !document.getElementById("dropin")) return;

  /* ---------------------------------------------------------------- the page */
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  let D = null, R = null;  // rules, last reading
  const store = {
    get() { try { return JSON.parse(sessionStorage.getItem(KEY) || "null"); } catch (e) { return null; } },
    set(v) { try { v ? sessionStorage.setItem(KEY, JSON.stringify(v)) : sessionStorage.removeItem(KEY); } catch (e) { /* private window */ } },
  };
  const rules = () => (D ? Promise.resolve(D) : fetch("data/dropin.json", { cache: "no-cache" }).then((r) => r.json()).then((d) => (D = d)));
  const realChip = (f, v) => document.querySelector(`#filterBody .chip[data-f="${f}"][data-v="${CSS.escape(v)}"]`);
  const pressed = (b) => !!b && b.getAttribute("aria-pressed") === "true";
  const label = (list, id) => ((list || []).find((x) => x.id === id) || {}).label || id;

  /* the recognised things as a list of {kind, label, found, on(), set(bool), possible} */
  function items() {
    const PF = window.PF, C = PF.cfg(), S = PF.state, out = [];
    const viaChip = (kind, f, v, name, found) => {
      const b = realChip(f, v);
      out.push({ kind, label: name, found, possible: !!b && !b.disabled, on: () => pressed(realChip(f, v)), set: (want) => { const x = realChip(f, v); if (x && !x.disabled && pressed(x) !== want) x.click(); } });
    };
    R.countries.forEach((c) => out.push({ kind: "Country", label: (C.countryName[c.code] || {}).name || c.code, found: c.found, possible: true,
      on: () => S.countries.has(c.code), set: (want) => { want ? S.countries.add(c.code) : S.countries.delete(c.code); PF.drawChosenCountries(); } }));
    R.topics.forEach((t) => viaChip("Topic", "tp", t.id, label(C.categories.topics, t.id), t.found));
    if (PF.mode === "media") R.formats.forEach((f) => viaChip("Format", "m", f, label(C.categories.material, f) + ([R.shape, R.duration].filter(Boolean).length ? " (" + [R.shape.toLowerCase(), R.duration].filter(Boolean).join(", ") + ")" : ""), []));
    R.langs.forEach((l) => {
      const b = realChip("l", l), name = C.langName[l] || l;
      if (b) viaChip("Language", "l", l, name, []);
      else out.push({ kind: "Language", label: name, found: [], possible: true, lang: true, on: () => S.langs.has(l), set: (want) => { want ? S.langs.add(l) : S.langs.delete(l); PF.drawOtherLangs(); } });
    });
    return out;
  }

  function applyReading() {
    const PF = window.PF, S = PF.state, list = items();
    PF.batch(() => {
      // a new text replaces what the last text had set: countries, region, topics, format
      S.countries.clear(); PF.drawChosenCountries();
      if (R.countries.length && $("f-region") && $("f-region").value) { $("f-region").value = ""; $("f-region").dispatchEvent(new Event("change")); }
      document.querySelectorAll('#filterBody .chip[data-f="tp"][aria-pressed="true"], #filterBody .chip[data-f="m"][aria-pressed="true"]').forEach((b) => b.click());
      list.forEach((it) => { if (it.possible && (it.kind !== "Language" || D.apply_language)) it.set(true); });
      // which list: only topic matches, or everything that fits with the matches first (config/dropin.yaml)
      const box = (id, want) => { const el = $(id); if (el && R.topics.length && typeof want === "boolean" && el.checked !== want) { el.checked = want; el.dispatchEvent(new Event("change")); } };
      box("f-onlyMatches", (D.only_matches || {})[PF.mode]);
      box("f-weak", (D.weak_matches || {})[PF.mode]);
    });
  }

  function drawResult() {
    const box = $("dropResult");
    if (!R) { box.innerHTML = ""; return; }
    const list = items(), other = window.PF.mode === "media" ? ["ngos.html", "organisations & NGOs"] : ["./", "media"];
    if (!list.length) { box.innerHTML = '<p class="dropin-note">No country, topic or format was recognised in this text. Please choose the filters on the left by hand.</p>'; return; }
    box.innerHTML = (R.headline ? `<p class="dropin-head">Read from: <b>${esc(R.headline)}</b></p>` : "")
      + '<div class="chips" id="dropChips"></div>'
      + '<p class="hint">Dark buttons are switched on as filters. Click a button to switch it off or on; all other filters on the left work as usual.</p>'
      + (list.some((i) => i.found.length) ? `<details class="explain"><summary>Why these suggestions?</summary><ul class="dropin-why">${list.filter((i) => i.found.length).map((i) => `<li><b>${esc(i.label)}:</b> found “${i.found.slice(0, 8).map(esc).join("”, “")}”</li>`).join("")}</ul></details>` : "")
      + (R.topics.length || R.countries.length ? `<p class="dropin-other"><a href="${other[0]}" id="dropOther">Show matching ${other[1]} for this text →</a></p>` : "");
    list.forEach((it) => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "chip"; b.innerHTML = `<span class="dropin-kind">${it.kind}:</span> ${esc(it.label)}`;
      b.setAttribute("aria-pressed", it.on() ? "true" : "false");
      if (!it.possible) { b.disabled = true; b.title = "There is no filter for this on this page"; }
      else if (it.kind === "Language" && !it.on()) b.title = "Not switched on by itself: click to show only outlets in this language";
      b.addEventListener("click", () => { const want = !it.on(); it.set(want); if (it.kind === "Country" || it.lang) window.PF.apply(); });
      $("dropChips").append(b);
    });
    const o = $("dropOther");
    if (o) o.addEventListener("click", () => store.set({ text: $("dropText").value, run: true }));
  }

  function run(setFilters) {
    const text = $("dropText").value.trim();
    if (!text) { R = null; drawResult(); return; }
    rules().then(() => {
      R = analyse(text, D);
      store.set({ text });
      if (setFilters) applyReading(); else drawResult();
    }).catch(() => { $("dropResult").innerHTML = '<p class="dropin-note">The word lists could not be loaded. Please reload the page.</p>'; });
  }

  $("dropGo").addEventListener("click", () => run(true));
  $("dropClear").addEventListener("click", () => { $("dropText").value = ""; R = null; store.set(null); drawResult(); $("dropText").focus(); });
  $("dropText").addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) run(true); });
  document.addEventListener("pf-applied", () => { if (R) drawResult(); });
  document.addEventListener("pf-ready", () => {
    const saved = store.get();
    if (!saved || !saved.text) return;
    $("dropText").value = saved.text; $("dropin").open = true;
    run(!!saved.run);  // coming from the other page: set the filters; after a reload: only show what was read
  });
})();
