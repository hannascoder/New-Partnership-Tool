/* Partner Finder: filters the outlets in data/outlets.json in the browser.
   All allowed values come from data/config.json (built from config/).
   Filter logic (briefing L): hard filters must match; within one filter OR,
   between filters AND. Topics and UN profile only change the order. */
(function () {
  "use strict";
  const PAGE = 50;
  const S = { scope: new Set(), scopeUnknown: false, reach: true, worldwide: false, own: new Set(), ownUnknown: false, nets: new Set(), orgType: new Set(), material: new Set(), langs: new Set(), noLang: false, region: "", country: "",
              channel: new Set(), size: "all", tp: new Set(), subOff: {}, au: new Set(), un: new Set(), onlyMatches: false, checks: new Set(), sort: "auto" };
  let CFG, ALL = [], shown = 0, current = [];
  const exportList = new Set(loadList());
  let filterSets = loadSets();  // every distinct filter combination active when items were added
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function loadList() { try { return JSON.parse(localStorage.getItem("pf-export") || "[]"); } catch (e) { return []; } }
  function loadSets() { try { return JSON.parse(localStorage.getItem("pf-export-filters") || "[]"); } catch (e) { return []; } }
  function saveList() {
    try { localStorage.setItem("pf-export", JSON.stringify([...exportList])); localStorage.setItem("pf-export-filters", JSON.stringify(filterSets)); }
    catch (e) { /* private window: the list still works until the page is closed */ }
  }

  Promise.all([fetch("data/config.json").then((r) => r.json()), fetch("data/outlets.json").then((r) => r.json())])
    .then(([cfg, outlets]) => { CFG = cfg; ALL = expand(outlets, cfg.codes || {}); init(); restoreHash(); apply(); })
    .catch(() => { $("counter").textContent = "The data could not be loaded. Please reload the page."; });

  /* outlets.json stores repeated values as short codes (pipeline/build/site_data.py compact()) */
  function expand(list, codes) {
    const arr = ["ch", "s", "oa", "nw"], first = ["o", "ow", "sc"];
    list.forEach((o) => {
      arr.forEach((k) => { if (o[k] && codes[k]) o[k] = o[k].map((v) => (typeof v === "number" ? codes[k][v] : v)); });
      first.forEach((k) => { if (o[k] && codes[k] && typeof o[k][0] === "number") o[k][0] = codes[k][o[k][0]]; });
      if (!o.f && codes.f) o.f = codes.f;
      if (!o.s) o.s = [];
      if (o.so && codes.so) Object.keys(o.so).forEach((k) => { const v = o.so[k]; if (codes.so[k] && !/^https?:/.test(v)) o.so[k] = codes.so[k].replace("{}", v); });
    });
    return list;
  }

  function chip(label, pressed, onClick, opts = {}) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "chip"; b.innerHTML = label;
    b.setAttribute("aria-pressed", pressed ? "true" : "false");
    if (opts.disabled) { b.disabled = true; b.title = opts.title || "Available after step 4 (classification)"; }
    if (opts.title && !opts.disabled) b.title = opts.title;
    b.addEventListener("click", () => { onClick(b); });
    if (onClick._v !== undefined) { b.dataset.f = SETNAME.get(onClick._set) || ""; b.dataset.v = onClick._v; }
    if (opts.f) { b.dataset.f = opts.f; b.dataset.v = opts.v; }
    return b;
  }
  function toggle(set, value) {
    const fn = (b) => { set.has(value) ? set.delete(value) : set.add(value); b.setAttribute("aria-pressed", set.has(value)); apply(); };
    fn._set = set; fn._v = value; return fn;
  }
  /* -------- shareable link: the chosen filters are kept in the page address (#...) -------- */
  const SETS = { m: "material", l: "langs", sc: "scope", ot: "orgType", ch: "channel", ow: "own", nw: "nets", tp: "tp", au: "au", un: "un", ck: "checks" };
  const SETNAME = new Map(Object.entries(SETS).map(([k, v]) => [S[v], k]));
  const FLAGS = { nl: "f-noLang", su: "f-scopeUnknown", ww: "f-worldwide", ou: "f-ownUnknown", om: "f-onlyMatches" };
  let restoring = false;
  function saveHash() {
    if (restoring) return;
    const p = new URLSearchParams();
    Object.entries(SETS).forEach(([k, v]) => { if (S[v].size) p.set(k, [...S[v]].join(",")); });
    const off = Object.entries(S.subOff).filter(([t, o]) => o.size && S.tp.has(t)).map(([t, o]) => t + ":" + [...o].join("|"));
    if (off.length) p.set("off", off.join(";"));
    if (S.region) p.set("rg", S.region);
    if (S.country) p.set("c", S.country);
    if (S.size !== "all") p.set("size", S.size);
    if (S.sort !== "auto") p.set("sort", S.sort);
    if (!S.reach) p.set("rch", "0");
    Object.entries(FLAGS).forEach(([k, id]) => { if ($(id) && $(id).checked) p.set(k, "1"); });
    const h = p.toString();
    history.replaceState(null, "", h ? "#" + h : location.pathname + location.search);
  }
  function restoreHash() {
    const p = new URLSearchParams(location.hash.slice(1));
    if (![...p.keys()].length) return;
    restoring = true;
    const fire = (el, ev) => el && el.dispatchEvent(new Event(ev));
    if (p.get("rg")) { $("f-region").value = p.get("rg"); fire($("f-region"), "change"); }
    if (p.get("c")) { $("f-country").value = p.get("c"); fire($("f-country"), "change"); }
    Object.keys(SETS).forEach((k) => (p.get(k) || "").split(",").filter(Boolean).forEach((v) => {
      const b = document.querySelector(`.chip[data-f="${k}"][data-v="${CSS.escape(v)}"]`);
      if (b && !b.disabled) b.click();
      else if (k === "l") { S.langs.add(v); drawOtherLangs(); }
      else if (k === "ck") { const c = document.querySelector(`#f-checks input[data-v="${CSS.escape(v)}"]`); if (c && !c.disabled) { c.checked = true; fire(c, "change"); } }
    }));
    (p.get("off") || "").split(";").filter(Boolean).forEach((x) => {
      const [t, subs] = x.split(":");
      (subs || "").split("|").forEach((s) => { const b = document.querySelector(`.chip[data-f="sub:${CSS.escape(t)}"][data-v="${CSS.escape(s)}"]`); if (b) b.click(); });
    });
    if (p.get("size")) { const r = document.querySelector(`input[name="size"][value="${CSS.escape(p.get("size"))}"]`); if (r) { r.checked = true; fire(r, "change"); } }
    if (p.get("sort")) { $("sort").value = p.get("sort"); fire($("sort"), "change"); }
    if (p.get("rch") === "0") { $("f-reach").checked = false; fire($("f-reach"), "change"); }
    Object.entries(FLAGS).forEach(([k, id]) => { if (p.get(k) && $(id)) { $(id).checked = true; fire($(id), "change"); } });
    restoring = false;
  }
  const visible = (list) => list.filter((x) => !x.later && !x.hidden);

  function init() {
    const C = CFG.categories;
    const countryName = {}; CFG.countries.forEach((c) => { countryName[c.iso3] = c; });
    CFG.countryName = countryName;
    CFG.langName = {}; CFG.languages.concat(CFG.language_buttons).forEach((l) => { CFG.langName[l.code] = l.name; });

    C.material.forEach((m) => $("f-material").append(chip(esc(m.label), false, toggle(S.material, m.id), { title: "Finds outlets on: " + m.channels.join(", ") })));
    CFG.language_buttons.forEach((l) => $("f-langButtons").append(chip(esc(l.name), false, toggle(S.langs, l.code))));
    const btn = new Set(CFG.language_buttons.map((l) => l.code));
    CFG.languages.filter((l) => !btn.has(l.code)).forEach((l) => $("f-otherLang").append(new Option(l.name, l.code)));
    $("f-otherLang").addEventListener("change", (e) => { if (e.target.value) { S.langs.add(e.target.value); drawOtherLangs(); apply(); } e.target.value = ""; });
    $("f-noLang").addEventListener("change", (e) => { S.noLang = e.target.checked; apply(); });

    Object.keys(CFG.regions).forEach((r) => {
      const g = document.createElement("optgroup"); g.label = r;
      g.append(new Option(r + " (all)", "R:" + r));
      CFG.regions[r].forEach((s) => g.append(new Option(s, "S:" + s)));
      $("f-region").append(g);
    });
    $("f-region").addEventListener("change", (e) => { S.region = e.target.value; S.country = ""; drawCountries(); apply(); });
    $("f-country").addEventListener("change", (e) => { S.country = e.target.value; apply(); });
    drawCountries();
    const scCount = {}; ALL.forEach((o) => { if (o.sc) scCount[o.sc[0]] = (scCount[o.sc[0]] || 0) + 1; });
    C.scope.forEach((s) => $("f-scope").append(chip(esc(s.label) + ` <span class="sdg">${(scCount[s.id] || 0).toLocaleString("en")}</span>`, false, toggle(S.scope, s.id))));
    $("f-scopeUnknown").addEventListener("change", (e) => { S.scopeUnknown = e.target.checked; apply(); });
    $("f-reach").addEventListener("change", (e) => { S.reach = e.target.checked; apply(); });
    $("f-worldwide").addEventListener("change", (e) => { S.worldwide = e.target.checked; apply(); });
    const typeCount = {}; ALL.forEach((o) => { if (o.o) typeCount[o.o[0]] = (typeCount[o.o[0]] || 0) + 1; });
    visible(C.org_type).forEach((o) => $("f-orgType").append(chip(esc(o.label) + ` <span class="sdg">${(typeCount[o.id] || 0).toLocaleString("en")}</span>`, false, toggle(S.orgType, o.id))));
    visible(C.channel).forEach((c) => $("f-channel").append(chip(esc(c.label), false, toggle(S.channel, c.id))));
    const ownCount = {}; ALL.forEach((o) => { if (o.ow) ownCount[o.ow[0]] = (ownCount[o.ow[0]] || 0) + 1; });
    C.ownership.filter((o) => o.id !== "unknown").forEach((o) => $("f-ownership").append(chip(esc(o.label) + ` <span class="sdg">${(ownCount[o.id] || 0).toLocaleString("en")}</span>`, false, toggle(S.own, o.id))));
    $("f-ownUnknown").addEventListener("change", (e) => { S.ownUnknown = e.target.checked; apply(); });
    const netCount = {}; ALL.forEach((o) => (o.nw || []).forEach((n) => { netCount[n] = (netCount[n] || 0) + 1; }));
    CFG.networks.forEach((n) => $("f-network").append(chip(esc(n.label) + ` <span class="sdg">${(netCount[n.id] || 0).toLocaleString("en")}</span>`, false, toggle(S.nets, n.id))));
    C.size.forEach((s) => {
      const l = document.createElement("label");
      l.innerHTML = `<input type="radio" name="size" value="${esc(s.id)}" ${s.default ? "checked" : ""}> ${esc(s.label)}`;
      l.querySelector("input").addEventListener("change", () => { S.size = s.id; apply(); });
      $("f-size").append(l);
    });
    $("sizeNote").textContent = CFG.size_note || "";
    const tpCount = {}, subCount = {};
    ALL.forEach((o) => {
      topicsOf(o).forEach((t) => { tpCount[t] = (tpCount[t] || 0) + 1; });
      (o.tp || []).forEach((e) => (e[3] || []).forEach((s) => { const k = e[0] + "/" + s; subCount[k] = (subCount[k] || 0) + 1; }));
    });
    C.topic_groups.forEach((g) => {
      const d = document.createElement("div"); d.className = "topic-group";
      d.innerHTML = `<h3>${esc(g.label)}</h3>`;
      const ch = document.createElement("div"); ch.className = "chips";
      const subBoxes = [];
      C.topics.filter((t) => t.group === g.id).forEach((t) => {
        const n = tpCount[t.id] || 0;
        let box = null;
        if (t.subtopics) {  // sub-topics: shown when the topic is chosen, all included until unticked
          box = document.createElement("div"); box.className = "subtopics"; box.hidden = true;
          box.innerHTML = `<p class="hint">${esc(t.label)}: all sub-topics are included. Untick to be more specific.</p>`;
          const sc = document.createElement("div"); sc.className = "chips";
          t.subtopics.forEach((s) => {
            const b = chip(esc(s.label) + ` <span class="sdg">${(subCount[t.id + "/" + s.id] || 0).toLocaleString("en")}</span>`, true, (btn) => {
              const off = S.subOff[t.id] || (S.subOff[t.id] = new Set());
              off.has(s.id) ? off.delete(s.id) : off.add(s.id);
              btn.setAttribute("aria-pressed", off.has(s.id) ? "false" : "true"); apply();
            });
            b.classList.add("sub"); b.dataset.f = "sub:" + t.id; b.dataset.v = s.id; sc.append(b);
          });
          box.append(sc); subBoxes.push(box);
        }
        const label = (t.sdg ? `SDG ${t.sdg} ` : "") + t.label;
        ch.append(chip(esc(label) + ` <span class="sdg">${n.toLocaleString("en")}</span>`, false, (b) => {
          S.tp.has(t.id) ? S.tp.delete(t.id) : S.tp.add(t.id);
          b.setAttribute("aria-pressed", S.tp.has(t.id));
          if (box) {
            box.hidden = !S.tp.has(t.id);
            if (!S.tp.has(t.id)) { delete S.subOff[t.id]; box.querySelectorAll(".chip").forEach((x) => x.setAttribute("aria-pressed", "true")); }
          }
          apply();
        }, Object.assign({ f: "tp", v: t.id }, n ? { title: t.default ? "Includes all outlets without a topic in the sources" : "" } : { disabled: true, title: "No outlet found for this topic yet" })));
      });
      d.append(ch); subBoxes.forEach((b) => d.append(b)); $("f-topics").append(d);
    });
    const auCount = {}; ALL.forEach((o) => (o.au || []).forEach((a) => { auCount[a] = (auCount[a] || 0) + 1; }));
    C.audience.forEach((a) => {
      const n = auCount[a.id] || 0;
      $("f-audience").append(chip(esc(a.label) + ` <span class="sdg">${n.toLocaleString("en")}</span>`, false, toggle(S.au, a.id),
        n ? { title: a.description || "" } : { disabled: true, title: "No open source for this yet (the website check may add it later)" }));
    });
    const unCount = {}; ALL.forEach((o) => (o.un || []).forEach((u) => { unCount[u] = (unCount[u] || 0) + 1; }));
    C.un_profile.filter((u) => !u.shown_in).forEach((u) => {
      const n = unCount[u.id] || 0;
      $("f-unProfile").append(chip(esc(u.label) + ` <span class="sdg">${n.toLocaleString("en")}</span>`, false, toggle(S.un, u.id),
        n ? { title: u.description || "" } : { disabled: true, title: "No open source for this yet (hand corrections or the website check may add it later)" }));
    });
    const om = C.checkboxes.find((c) => c.id === "only_topic_matches") || { label: "Only show topic matches" };
    $("onlyMatchesLabel").textContent = om.label;
    if (om.description) $("onlyMatchesLabel").parentElement.title = om.description;
    $("f-onlyMatches").addEventListener("change", (e) => { S.onlyMatches = e.target.checked; apply(); });
    const checkAvail = { only_verified: true, has_social_media: true, has_public_contact: true, hide_state_controlled: true,
                         hide_website_down: true, only_new: true, only_active: true };
    C.checkboxes.filter((c) => !["include_reach", "include_no_language", "only_topic_matches"].includes(c.id)).forEach((c) => {
      const l = document.createElement("label");
      l.className = "check" + (checkAvail[c.id] ? "" : " pending");
      l.innerHTML = `<input type="checkbox" ${checkAvail[c.id] ? "" : "disabled"}> ${esc(c.label)}${checkAvail[c.id] ? "" : ' <span class="soon">step 4</span>'}`;
      l.querySelector("input").dataset.v = c.id;
      l.querySelector("input").addEventListener("change", (e) => { e.target.checked ? S.checks.add(c.id) : S.checks.delete(c.id); apply(); });
      $("f-checks").append(l);
    });
    [["auto", "Best match / A–Z (automatic)"]].concat(C.sort.map((s) => [s.id, s.label])).forEach(([v, l]) => $("sort").append(new Option(l, v)));
    $("sort").addEventListener("change", (e) => { S.sort = e.target.value; apply(); });

    $("reset").addEventListener("click", () => location.reload());
    $("more").addEventListener("click", () => draw(false));
    $("addAll").addEventListener("click", () => {
      let added = 0;
      current.forEach((o) => { if (!exportList.has(o.i)) { exportList.add(o.i); added++; } });
      if (added) rememberFilters();
      saveList(); syncChecks(); updateExportCount();
    });
    $("clearExport").addEventListener("click", () => { exportList.clear(); filterSets = []; saveList(); syncChecks(); updateExportCount(); });
    document.querySelectorAll("#exportBar [data-format]").forEach((b) => b.addEventListener("click", () => doExport(b)));
    $("filtersToggle").addEventListener("click", (e) => {
      const open = $("filters").classList.toggle("open"); e.target.setAttribute("aria-expanded", open);
    });
    $("dataInfo").textContent = `Data collected ${CFG.data_date} · page built ${CFG.built}`;
    updateExportCount();
  }

  function drawOtherLangs() {
    const box = $("f-otherChosen"); box.innerHTML = "";
    const btn = new Set(CFG.language_buttons.map((l) => l.code));
    [...S.langs].filter((c) => !btn.has(c)).forEach((c) => box.append(chip(esc(CFG.langName[c] || c) + " ✕", true, () => { S.langs.delete(c); drawOtherLangs(); apply(); })));
  }

  function inRegion(c) {
    if (!S.region) return true;
    const k = CFG.countryName[c]; if (!k) return false;
    return S.region.startsWith("R:") ? k.region === S.region.slice(2) : k.subregion === S.region.slice(2);
  }
  function drawCountries() {
    const sel = $("f-country"); sel.length = 1;
    const list = CFG.countries.filter((c) => inRegion(c.iso3)).sort((a, b) => a.name.localeCompare(b.name));
    list.filter((c) => c.status === "member").forEach((c) => sel.append(new Option(c.name, c.iso3)));
    const obs = list.filter((c) => c.status === "observer");
    if (obs.length) { const g = document.createElement("optgroup"); g.label = "Observer states"; obs.forEach((c) => g.append(new Option(c.name, c.iso3))); sel.append(g); }
  }

  function reachesTarget(o, c) {
    if (!o.rc || !(c in o.rc)) return false;
    return S.worldwide || CFG.why[o.rc[c]] !== "worldwide";
  }

  /* "new" = first found less than new_months (categories.yaml) before the data date */
  function activeSince() {
    const d = new Date(CFG.data_date); d.setMonth(d.getMonth() - (CFG.active_months || 3));
    return d.toISOString().slice(0, 10);
  }
  function newSince() {
    const d = new Date(CFG.data_date); d.setMonth(d.getMonth() - (CFG.new_months || 4));
    return d.toISOString().slice(0, 10);
  }
  function anyFilter() {
    return S.scope.size || S.own.size || S.nets.size || S.orgType.size || S.material.size || S.langs.size || S.region || S.country || S.channel.size || S.size !== "all" || S.tp.size || S.au.size || S.un.size || S.checks.size;
  }
  /* an outlet without any topic in the sources counts as "General news" (the default topic) */
  function topicsOf(o) { return o.tp ? o.tp.map((e) => e[0]) : ["general_news"]; }
  /* o.tp entries: [topic, strength (1 main focus, 2 own section, 3 covers it), reason, [sub-topics]] */
  function tpEntry(o, t) { return o.tp ? o.tp.find((e) => e[0] === t) : (t === "general_news" ? ["general_news", 3, -1] : null); }
  function topicMatch(o, t) {
    const e = tpEntry(o, t); if (!e) return null;
    const off = S.subOff[t]; if (!off || !off.size) return e;
    return (e[3] || []).some((s) => !off.has(s)) ? e : null;  // narrowed: only outlets with a chosen sub-topic
  }
  const STRENGTH = new Proxy({}, { get: (_, k) => ((CFG && CFG.topic_strength) || { 1: "main focus", 2: "own section", 3: "covers it" })[k] });
  function why(o, kind, id) {
    if (kind === "tp") {
      const e = tpEntry(o, id); if (!e || e[2] < 0) return "no topic in the sources: general news";
      const t = CFG.categories.topics.find((x) => x.id === id) || {};
      const subs = (e[3] || []).map((s) => ((t.subtopics || []).find((x) => x.id === s) || {}).label).filter(Boolean);
      return STRENGTH[e[1]] + ": " + (CFG.why[e[2]] || "") + (subs.length ? " · " + subs.join("; ") : "");
    }
    if (kind === "au") return CFG.why[o.aw[o.au.indexOf(id)]] || "";
    return CFG.why[o.uw[o.un.indexOf(id)]] || "";
  }

  function apply() {
    if (restoring) return;
    saveHash();
    const C = CFG.categories;
    let matChannels = null, matTypes = null;
    if (S.material.size) {
      matChannels = new Set(); matTypes = new Set();
      C.material.filter((m) => S.material.has(m.id)).forEach((m) => { m.channels.forEach((c) => matChannels.add(c)); (m.also_org_types || []).forEach((t) => matTypes.add(t)); });
    }
    $("materialHint").textContent = matChannels ? "Shows outlets on: " + [...matChannels].map((c) => (C.channel.find((x) => x.id === c) || {}).label || c).join(", ") : "";
    current = ALL.filter((o) => {
      if (S.country) { if (o.c !== S.country && !(S.reach && reachesTarget(o, S.country))) return false; }
      else if (!inRegion(o.c)) return false;
      if (S.scope.size) {
        const v = o.sc ? o.sc[0] : "unknown";
        if (!(S.scope.has(v) || (v === "unknown" && S.scopeUnknown))) return false;
      }
      const ch = o.ch || [];
      if (matChannels && !ch.some((c) => matChannels.has(c)) && !(matTypes && o.o && matTypes.has(o.o[0]))) return false;
      if (S.channel.size && !ch.some((c) => S.channel.has(c))) return false;
      if (S.langs.size) {
        if (!o.l) { if (!S.noLang) return false; } else if (!o.l.some((l) => S.langs.has(l))) return false;
      }
      if (S.orgType.size) {
        const types = new Set(S.orgType);
        // "Text" also finds news agencies (categories.yaml: also_org_types)
        if (!o.o || !(types.has(o.o[0]) || (o.oa || []).some((t) => types.has(t)))) return false;
      }
      if (S.own.size) {
        const v = o.ow ? o.ow[0] : "unknown";
        if (!(S.own.has(v) || (v === "unknown" && S.ownUnknown))) return false;
      }
      if (S.nets.size && !(o.nw || []).some((n) => S.nets.has(n))) return false;
      if (S.checks.has("hide_state_controlled") && o.ow && o.ow[0] === "state_controlled") return false;
      if (S.size === "top10" && o.r > 10) return false;
      if (S.size === "top50" && o.r > 50) return false;
      if (S.checks.has("only_verified") && o.s.length < 2) return false;
      if (S.checks.has("has_social_media") && !o.so) return false;
      if (S.checks.has("has_public_contact") && !o.em && !o.cp) return false;
      if (S.checks.has("only_active") && !(o.lp && o.lp >= activeSince())) return false;
      if (S.checks.has("hide_website_down") && o.wd) return false;  // website did not answer at the last check
      if (S.checks.has("only_new") && o.f < newSince()) return false;
      return true;
    });
    current.forEach((o) => {
      o._m = [...S.tp].map((t) => [t, topicMatch(o, t)]).filter((x) => x[1]).map(([t, e]) => ["tp", t, e[1]]).concat((o.au || []).filter((a) => S.au.has(a)).map((a) => ["au", a])).concat((o.un || []).filter((u) => S.un.has(u)).map((u) => ["un", u]));
    });
    if (S.onlyMatches && (S.tp.size || S.au.size || S.un.size)) current = current.filter((o) => o._m.length);
    const mode = S.sort === "auto" ? (anyFilter() ? "best_match" : "az") : S.sort;
    const key = (o) => o._k || (o._k = (o.n || "").replace(/^[^\p{L}\p{N}]+/u, ""));  // "__STUDY__" sorts under S
    const byName = (a, b) => key(a).localeCompare(key(b), "en", { sensitivity: "base" });
    // best match: topics count by strength (main focus 3, own section 2, covers it 1), audiences and UN profiles 1 each
    const score = (o) => o._s != null ? o._s : (o._s = o._m.reduce((n, m) => n + (m[0] === "tp" ? 4 - m[2] : 1), 0));
    current.forEach((o) => { o._s = null; });
    // equal match: outlets based in the chosen country before outlets that only reach it (owner, 09.11.2026)
    const home = (o) => (S.country && o.c === S.country ? 1 : 0);
    if (mode === "best_match") current.sort((a, b) => score(b) - score(a) || home(b) - home(a) || b.p - a.p || byName(a, b));
    else if (mode === "country") current.sort((a, b) => (CFG.countryName[a.c] || {}).name.localeCompare((CFG.countryName[b.c] || {}).name) || byName(a, b));
    else current.sort(byName);
    const countries = new Set(current.map((o) => o.c)).size;
    const verified = current.filter((o) => o.s.length >= 2).length;
    $("counter").innerHTML = `<b>${current.length.toLocaleString("en")}</b> ${current.length === 1 ? "outlet" : "outlets"} in <b>${countries}</b> ${countries === 1 ? "country" : "countries"} · ${verified.toLocaleString("en")} verified`;
    draw(true);
    updateAddAll();
  }

  function card(o) {
    const C = CFG.categories, k = CFG.countryName[o.c] || {};
    const chans = (o.ch || []).map((c) => (C.channel.find((x) => x.id === c) || {}).label || c).join(", ");
    const langs = (o.l || []).map((l) => CFG.langName[l] || l).join(", ") || "<span class='pending'>no information</span>";
    const src = o.s.map((s) => CFG.source_labels[s] || s).join(", ");
    const social = Object.entries(o.so || {}).map(([k2, u]) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(k2)}</a>`).join(" · ");
    const verified = o.s.length >= 2 ? '<span class="badge verified">verified</span>' : '<span class="badge unverified">1 source</span>';
    const tip = (kind, id, label) => `<span class="tag" title="${esc(why(o, kind, id))}">${esc(label)}</span>`;
    const tpl = topicsOf(o).map((t) => {
      const e = tpEntry(o, t);
      const link = e && e[4] && /^https?:/.test(e[4]) ? ` <a href="${esc(e[4])}" target="_blank" rel="noopener" title="Open this section of the website">section ↗</a>` : "";
      return tip("tp", t, lab(C.topics, t)) + (o.tp ? ` <span class="pending">(${STRENGTH[e[1]]}${link ? "" : ""})</span>` : "") + link;
    }).join(", ");
    const aul = (o.au || []).map((a) => tip("au", a, lab(C.audience, a))).join(", ");
    const unl = (o.un || []).map((u) => tip("un", u, lab(C.un_profile, u))).join(", ");
    const inList = exportList.has(o.i);
    return `<li class="card${inList ? " selected" : ""}" data-id="${esc(o.i)}"><div class="card-top"><h3>${esc(o.n)}</h3>${verified}</div>
      <p class="meta">Based in: <b>${esc(k.name || o.c)}</b> (${esc(k.subregion || "")}) · ${reachText(o)}${o.sc && o.sc[0] !== "unknown" ? ` · Scope: ${esc((C.scope.find((x) => x.id === o.sc[0]) || {}).label || o.sc[0])} <span class="pending" title="${esc(CFG.why[o.sc[1]])}">ⓘ</span>` : ""}</p>
      ${freedomText(k)}
      ${o.a ? `<p class="row">Also known as: ${esc(o.a.join(", "))}</p>` : ""}
      ${o.o ? `<p class="row"><b>Type:</b> ${esc((C.org_type.find((x) => x.id === o.o[0]) || {}).label || o.o[0])} <span class="pending">(${esc(CFG.why[o.o[1]])})</span></p>` : ""}
      ${o.ow && o.ow[0] !== "unknown" ? `<p class="row"><b>Ownership:</b> ${esc((C.ownership.find((x) => x.id === o.ow[0]) || {}).label || o.ow[0])} <span class="pending">(${esc(CFG.why[o.ow[1]])})</span></p>` : `<p class="row"><b>Ownership:</b> Unknown <span class="pending" title="No open source says who owns this outlet. This does not mean it is independent or state-run.">ⓘ</span></p>`}
      ${o.oa ? `<p class="row"><b>Also listed as:</b> ${esc(o.oa.map((t) => (C.org_type.find((x) => x.id === t) || {}).label || t).join(", "))}</p>` : ""}
      <p class="row"><b>Languages:</b> ${langs}</p>
      ${o.sv ? `<p class="row"><b>Language services:</b> ${esc(o.sv.join(", "))}</p>` : ""}
      <p class="row"><b>Channels:</b> ${esc(chans) || "<span class='pending'>no information</span>"}</p>
      <p class="row"><b>Topics:</b> ${tpl}</p>
      ${aul ? `<p class="row"><b>Target audience:</b> ${aul}</p>` : ""}
      ${unl ? `<p class="row"><b>UN profile:</b> ${unl}</p>` : ""}
      ${o.w ? `<p class="row"><b>Website:</b> <a href="${esc(o.w)}" target="_blank" rel="noopener">${esc(o.w.replace(/^https?:\/\//, "").replace(/\/$/, ""))}</a></p>` : ""}
      ${social ? `<p class="row"><b>Social media:</b> ${social}</p>` : ""}
      ${o.em ? `<p class="row"><b>Contact:</b> <a href="mailto:${esc(o.em)}">${esc(o.em)}</a>${o.cp ? ` · <a href="${esc(o.cp)}" target="_blank" rel="noopener">contact page ↗</a>` : ""}</p>`
        : o.cp ? `<p class="row"><b>Contact:</b> <a href="${esc(o.cp)}" target="_blank" rel="noopener">contact page ↗</a></p>` : ""}
      ${o.lp ? `<p class="row pending">Latest article seen on the website: ${esc(o.lp)}${o.lp < activeSince() ? " (no recent article found)" : ""}</p>` : ""}
      <p class="row pending">Sources: ${esc(src)} · id ${esc(o.i)}${CFG.feedback_email ? ` · <a href="${esc(reportLink(o))}">Report an error</a>` : ""}</p>
      ${o._m && o._m.length ? `<span class="matches">Matches: ${esc(o._m.map(([k2, id, s]) => lab(k2 === "tp" ? C.topics : k2 === "au" ? C.audience : C.un_profile, id) + (k2 === "tp" && s ? ` (${STRENGTH[s]})` : "")).join(", "))}</span>` : ""}
      <p><label class="export-check"><input type="checkbox" class="export-box" data-id="${esc(o.i)}" ${inList ? "checked" : ""}> Export</label></p></li>`;
  }

  function reportLink(o) {
    const k = CFG.countryName[o.c] || {};
    const body = `Outlet: ${o.n} (${k.name || o.c}), id ${o.i}\nWebsite: ${o.w || "-"}\n\nWhat is wrong (e.g. topic, type, ownership, contact, outlet closed)?\n\n\nFilters used: ${location.href}`;
    return `mailto:${CFG.feedback_email}?subject=${encodeURIComponent("Partner Finder: error report " + o.i)}&body=${encodeURIComponent(body)}`;
  }
  function basisText(b) {
    return b.startsWith("language_service:") ? "via " + b.slice(17) : b === "broadcast_area" ? "broadcast area" : b === "worldwide" ? "worldwide broadcaster" : "international broadcaster";
  }
  function reachText(o) {
    const C = CFG.countryName;
    if (!o.rc) return "Reaches: " + esc((C[o.c] || {}).name || o.c);
    const n = Object.keys(o.rc).length + 1;
    if (S.country && S.country !== o.c && S.country in o.rc) {
      return `Reaches: <b>${esc((C[S.country] || {}).name)}</b> (${esc(basisText(CFG.why[o.rc[S.country]]))}) and ${n - 1} other countries`;
    }
    if (n >= 150) return "Reaches: worldwide";
    return "Reaches: " + esc([o.c].concat(Object.keys(o.rc)).slice(0, 6).map((c) => (C[c] || {}).name || c).join(", ")) + (n > 6 ? ` and ${n - 6} more` : "");
  }
  function freedomText(k) {
    const f = k.freedom; if (!f || f.press_freedom_rank == null) return "";
    const src = (f.press_freedom_source || "").split("|")[0].trim();
    return `<p class="row pending">Press freedom in ${esc(k.name)}: rank ${esc(f.press_freedom_rank)} of 180, score ${esc(f.press_freedom_score)} (${esc(src)})`
      + (f.political_freedom_status ? ` · Political freedom: ${esc(f.political_freedom_status)}` : "")
      + (f.internet_freedom_status ? ` · Internet freedom: ${esc(f.internet_freedom_status)}` : "")
      + (f.political_freedom_status || f.internet_freedom_status ? " (Freedom House)" : "") + "</p>";
  }

  function draw(fromStart) {
    if (fromStart) { shown = 0; $("cards").innerHTML = ""; }
    const slice = current.slice(shown, shown + PAGE);
    $("cards").insertAdjacentHTML("beforeend", slice.map(card).join(""));
    shown += slice.length;
    $("more").hidden = shown >= current.length;
    $("more").textContent = `Show more (${(current.length - shown).toLocaleString("en")} left)`;
  }

  $("cards").addEventListener("change", (e) => {
    const box = e.target.closest("input.export-box"); if (!box) return;
    const id = box.dataset.id;
    if (box.checked) { exportList.add(id); rememberFilters(); } else exportList.delete(id);
    saveList(); syncChecks(id); updateExportCount();
  });

  /* every checkbox / card of the same item stays in sync (the item may be shown more than once) */
  function syncChecks(onlyId) {
    document.querySelectorAll(onlyId ? `input.export-box[data-id="${onlyId}"]` : "input.export-box").forEach((b) => {
      const on = exportList.has(b.dataset.id); b.checked = on;
      const card = b.closest(".card"); if (card) card.classList.toggle("selected", on);
    });
  }

  /* the active filters, read generically from the filter form: every chip group with
     pressed chips, every select with a value, every ticked checkbox (label = group heading).
     Filters added later appear in the export without code changes. */
  function activeFilters() {
    const out = [];
    document.querySelectorAll("#filterBody .fgroup").forEach((g) => {
      const head = g.querySelector("h2"); const label = head ? head.childNodes[0].textContent.trim() : "";
      const chips = [...g.querySelectorAll('.chip[aria-pressed="true"]:not(.sub)')].map((c) => c.childNodes[0].textContent.replace(" ✕", "").trim());
      // a select is named by its own label ("Country: Kenya"), chips and radios by the group heading
      g.querySelectorAll("select").forEach((sel) => {
        const own = sel.closest("label"); const name = own ? own.childNodes[0].textContent.trim() : label;
        if (sel.value && sel.selectedOptions[0]) out.push([name, sel.selectedOptions[0].textContent.trim()]);
      });
      const values = chips.slice();
      g.querySelectorAll('input[type="radio"]:checked').forEach((r) => { if (!r.defaultChecked) values.push(r.parentElement.textContent.trim()); });
      if (values.length) out.push([label, values.join(", ")]);
      // ticked checkboxes (those ticked by default, like "include reach", only when changed)
      g.querySelectorAll('input[type="checkbox"]').forEach((c) => {
        if (c.checked !== c.defaultChecked) out.push([c.parentElement.textContent.replace("step 4", "").trim(), c.checked ? "" : "off"]);
      });
    });
    Object.entries(S.subOff).forEach(([t, off]) => {
      if (!off.size || !S.tp.has(t)) return;
      const tt = CFG.categories.topics.find((x) => x.id === t) || {};
      out.push([tt.label + " – only", (tt.subtopics || []).filter((s) => !off.has(s.id)).map((s) => s.label).join("; ")]);
    });
    const search = document.querySelector('#filterBody input[type="search"]');
    if (search && search.value.trim()) out.unshift(["Search", search.value.trim()]);
    return out;
  }
  function filterText(set) { return set.length ? set.map(([l, v]) => (v ? `${l}: ${v}` : l)).join(", ") : "None (all items)"; }
  function rememberFilters() {
    const set = activeFilters(), key = JSON.stringify(set);
    if (!filterSets.some((s2) => JSON.stringify(s2) === key)) filterSets.push(set);
  }
  function headerFilters() {
    if (!filterSets.length) return [];
    if (filterSets.length === 1) return filterSets[0];
    return filterSets.map((set, i) => [`(${i + 1})`, filterText(set)]);
  }
  async function doExport(btn) {
    const fmt = btn.dataset.format, old = btn.textContent;
    const orientation = (document.querySelector('input[name="orient"]:checked') || {}).value || "landscape";
    $("exportError").textContent = ""; btn.textContent = "Preparing…"; btn.disabled = true;
    try {
      const topics = new Set(S.tp);  // only the chosen topics are listed in the file (EXPORT_SPEC)
      const list = buildExportList([...exportList], headerFilters(), S.country || null, topics);
      await window.PartnerExport.download(fmt, list, { orientation });
    } catch (err) {
      $("exportError").textContent = "The file could not be made (" + (err && err.message ? err.message : "unknown error") + "). Please try again.";
    } finally { btn.textContent = old; btn.disabled = false; }
  }

  /* --------------------------------------------- export rows (finder-export.js) */
  const lab = (list, id) => (list.find((x) => x.id === id) || {}).label || id;
  function flags(o) {
    const f = [];
    if (o.ow && o.ow[0] === "state_controlled") f.push("State-controlled");
    if (o.s.length < 2) f.push("Unverified");
    if (o.wd) f.push("Website not reachable");
    if (o.lp && o.lp < activeSince()) f.push("No recent article (last " + o.lp + ")");
    return f.join(", ");
  }
  function exportRow(o, countryFilter, topicFilter) {
    const C = CFG.categories, K = CFG.countryName, k = K[o.c] || {};
    let reaches = "";
    if (o.rc) {
      if (countryFilter && countryFilter !== o.c && countryFilter in o.rc) reaches = `${(K[countryFilter] || {}).name} (${basisText(CFG.why[o.rc[countryFilter]])})`;
      else reaches = Object.keys(o.rc).length + 1 >= 150 ? "Worldwide" : [o.c].concat(Object.keys(o.rc)).map((c) => (K[c] || {}).name || c).join(", ");
    }
    const types = [o.o ? lab(C.org_type, o.o[0]) : ""].concat((o.oa || []).map((t) => lab(C.org_type, t))).filter(Boolean);
    const topics = topicsOf(o).filter((t) => !topicFilter || !topicFilter.size || topicFilter.has(t)).map((t) => lab(C.topics, t));
    return {
      name: o.n, type: types.join(" / "), country: k.name || o.c, reaches,
      scope: o.sc && o.sc[0] !== "unknown" ? lab(C.scope, o.sc[0]) : "",
      languages: (o.l || []).map((l) => CFG.langName[l] || l).join(", "),
      channels: (o.ch || []).map((c) => lab(C.channel, c)).join(", "),
      ownership: o.ow ? lab(C.ownership, o.ow[0]) : "Unknown",
      topic: topics.join(", "),
      audience: (o.au || []).map((a) => lab(C.audience, a)).join(", "),
      unProfile: (o.un || []).map((u) => lab(C.un_profile, u)).join(", "),
      memberOf: (o.nw || []).map((n) => (CFG.networks.find((x) => x.id === n) || {}).label || n).join(", "),
      website: o.w || "", contact: o.em || o.cp || "",
      social: Object.entries(o.so || {}).map(([k2, u]) => [{ youtube: "YouTube", facebook: "Facebook", instagram: "Instagram", tiktok: "TikTok", x: "X", telegram: "Telegram" }[k2] || k2, u]),
      notes: flags(o),
    };
  }
  /* sections (EXPORT_SPEC): "Best UN fit" = items with a UN profile, best first;
     then "By country & rank" = all others, country A-Z, then rank */
  function buildExportList(ids, filterSets, countryFilter, topicFilter) {
    const byId = {}; ALL.forEach((o) => { byId[o.i] = o; });
    const items = [...new Set(ids)].map((id) => byId[id]).filter(Boolean);
    const K = CFG.countryName;
    const fit = items.filter((o) => (o.un || []).length).sort((a, b) => b.un.length - a.un.length || b.p - a.p || a.n.localeCompare(b.n));
    const rest = items.filter((o) => !(o.un || []).length).sort((a, b) => ((K[a.c] || {}).name || "").localeCompare((K[b.c] || {}).name || "") || a.r - b.r);
    const row = (o) => exportRow(o, countryFilter, topicFilter);
    return {
      sections: [
        { title: "Best UN fit", note: "Outlets with a UN profile (e.g. existing UN relationship), best match first.", items: fit.map(row) },
        { title: "By country & rank", note: "All other outlets, by country (A–Z), then by prominence rank within the country.", items: rest.map(row) }],
      filters: filterSets, count: items.length, updated: CFG.data_date,
    };
  }
  window.PF = { exportList: buildExportList, all: () => ALL, cfg: () => CFG };

  function updateExportCount() {
    const n = exportList.size;
    $("exportBar").hidden = n === 0;
    $("exportCount").textContent = `${n.toLocaleString("en")} ${n === 1 ? "outlet" : "outlets"} in the export list`;
    $("exportFilters").textContent = filterSets.length <= 1 ? "Filters: " + filterText(filterSets[0] || [])
      : "Filters: " + filterSets.map((set, i) => `(${i + 1}) ${filterText(set)}`).join(" · ");
    updateAddAll();
  }
  function updateAddAll() {
    const missing = current.filter((o) => !exportList.has(o.i)).length;
    const b = $("addAll");
    b.textContent = `Add all ${current.length.toLocaleString("en")} to export list`;
    b.disabled = current.length === 0 || missing === 0;
  }
})();
