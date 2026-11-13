/* Partner Finder: filters the outlets in data/outlets-N.json in the browser.
   All allowed values come from data/config.json (built from config/).
   Filter logic (briefing L): hard filters must match; within one filter OR,
   between filters AND. Topics, target audience and UN profile are "matches":
   with "Only show matches" (default) they narrow the list, otherwise they only change the order. */
(function () {
  "use strict";
  const PAGE = 50;
  // two pages share this script (owner 12.11.2026): index.html = media, ngos.html = NGOs (<body data-mode>)
  const MODE = document.body.dataset.mode === "ngo" ? "ngo" : "media";
  const WORD = MODE === "ngo" ? ["organisation", "organisations"] : ["outlet", "outlets"];
  const KEY = MODE === "ngo" ? "pf-ngo-export" : "pf-export";
  const S = { scope: new Set(), scopeUnknown: false, reach: true, worldwide: false, own: new Set(), ownUnknown: false, nets: new Set(), orgType: new Set(), material: new Set(), langs: new Set(), noLang: false, region: "", countries: new Set(),
              channel: new Set(), size: "all", tp: new Set(), subOff: {}, platforms: new Set(), chUnknown: false, au: new Set(), un: new Set(), onlyMatches: false, allMatches: false, checks: new Set(), sort: "auto",
              ngoStatus: new Set(), ngoType: new Set(), ngoEcosoc: false, ngoHideReg: false, hqOnly: false, gscope: new Set(),
              orgKind: new Set(), sector: new Set(), ngoAll: false, unPartner: false, q: "", qAll: false };
  let CFG, ALL = [], shown = 0, current = [], nMatch = 0, DEFAULT_CHECKS = new Set();
  const exportList = new Set(loadList());
  let filterSets = loadSets();  // every distinct filter combination active when items were added
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (n) => (n || 0).toLocaleString("en");

  function loadList() { try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch (e) { return []; } }
  function loadSets() { try { return JSON.parse(localStorage.getItem(KEY + "-filters") || "[]"); } catch (e) { return []; } }
  function saveList() {
    try { localStorage.setItem(KEY, JSON.stringify([...exportList])); localStorage.setItem(KEY + "-filters", JSON.stringify(filterSets)); }
    catch (e) { /* private window: the list still works until the page is closed */ }
  }

  fetch("data/config.json", { cache: "no-cache" }).then((r) => r.json())
    .then((cfg) => Promise.all((MODE === "ngo" ? cfg.ngo_files || [] : cfg.outlet_files || ["outlets.json"]).map((f) => fetch("data/" + f + "?v=" + encodeURIComponent(cfg.built || "")).then((r) => r.json())))
      .then((parts) => [cfg, [].concat(...parts)]))
    .then(([cfg, outlets]) => { CFG = cfg; ALL = expand(outlets, cfg.codes || {}); init(); restoreHash(); apply(); openActiveGroups(); hideLoader(); })
    .catch(() => {
      const msg = "The data could not be loaded. Please reload the page.";
      $("counter").textContent = msg;
      hideLoader();
    });

  /* the flipping directory in the results area (index.html / ngos.html) goes as soon as the list is ready */
  function hideLoader() { if ($("loader")) $("loader").remove(); }

  /* outlets.json stores repeated values as short codes (pipeline/build/site_data.py compact()) */
  function expand(list, codes) {
    const arr = ["ch", "s", "oa", "nw"], first = ["o", "ow", "sc"];
    list.forEach((o) => {
      arr.forEach((k) => { if (o[k] && codes[k]) o[k] = o[k].map((v) => (typeof v === "number" ? codes[k][v] : v)); });
      first.forEach((k) => { if (o[k] && codes[k] && typeof o[k][0] === "number") o[k][0] = codes[k][o[k][0]]; });
      if (!o.f && codes.f) o.f = codes.f;
      if (!o.s) o.s = [];
      if (o.w) {  // links on the outlet's own website are stored as "/path"
        const origin = (/^https?:\/\//.test(o.w) ? o.w : "http://" + o.w).replace(/^(https?:\/\/[^/]+).*$/, "$1");
        if (o.cp && o.cp[0] === "/") o.cp = origin + o.cp;
        (o.tp || []).forEach((e) => { if (e[4] && e[4][0] === "/") e[4] = origin + e[4]; });
      }
      if (o.so && codes.so) Object.keys(o.so).forEach((k) => { const v = o.so[k]; if (codes.so[k] && !/^https?:/.test(v)) o.so[k] = codes.so[k].replace("{}", v); });
    });
    return list;
  }

  /* -------- numbers on the buttons: they follow the other filters (review 13.11.2026) --------
     CNT[group][value] = the <span> on the button; FACET[group](o) = the values an outlet has. */
  const CNT = {};
  const FACET = {
    scope: (o) => [o.sc ? o.sc[0] : "unknown"], orgType: (o) => (o.o ? [o.o[0]].concat(o.oa || []) : []), channel: (o) => o.ch || [],
    platform: (o) => Object.keys(o.so || {}), nets: (o) => o.nw || [], langs: (o) => o.l || [],
    ngoStatus: (o) => o.us || [], ngoType: (o) => (o.nt || []).map((t) => t[0]), gscope: (o) => (o.gs ? [o.gs] : []),
    orgKind: (o) => [o.ok || "ngo"], sector: (o) => (o.gc && o.gc[2] ? [o.gc[2]] : []),
    tp: (o) => topicsOf(o), sub: (o) => [].concat(...(o.tp || []).map((e) => (e[3] || []).map((x) => e[0] + "/" + x))), au: (o) => o.au || [], un: (o) => o.un || [],
  };
  const SOFT = ["tp", "sub", "au", "un"];
  function totals(group) { const c = {}; ALL.forEach((o) => FACET[group](o).forEach((v) => { c[v] = (c[v] || 0) + 1; })); return c; }
  function counted(group, value, label) {  // button label with a number that apply() keeps up to date
    return `${label} <span class="sdg" data-g="${esc(group)}" data-c="${esc(value)}"></span>`;
  }
  function registerCounts() { document.querySelectorAll("#filterBody .sdg[data-g]").forEach((sp) => { (CNT[sp.dataset.g] || (CNT[sp.dataset.g] = {}))[sp.dataset.c] = sp; }); }

  function chip(label, pressed, onClick, opts = {}) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "chip"; b.innerHTML = label;
    b.setAttribute("aria-pressed", pressed ? "true" : "false");
    if (opts.disabled) { b.disabled = true; b.title = opts.title || "No data for this yet"; }
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
  const SETS = { m: "material", l: "langs", sc: "scope", ot: "orgType", ch: "channel", ow: "own", nw: "nets", tp: "tp", au: "au", un: "un", pl: "platforms", ns: "ngoStatus", nt: "ngoType", gs: "gscope", ok: "orgKind", se: "sector" };
  const SETNAME = new Map(Object.entries(SETS).map(([k, v]) => [S[v], k]));
  const FLAGS = { cu: "f-chUnknown", nl: "f-noLang", su: "f-scopeUnknown", ww: "f-worldwide", om: "f-onlyMatches", am: "f-allMatches", ne: "f-ngoEcosoc", nr: "f-ngoHideReg", hq: "f-hqOnly", na: "f-ngoAll", up: "f-unPartner" };  // saved when different from the default
  let restoring = false;
  function saveHash() {
    if (restoring) return;
    const p = new URLSearchParams();
    Object.entries(SETS).forEach(([k, v]) => { if (S[v].size) p.set(k, [...S[v]].join(",")); });
    const off = Object.entries(S.subOff).filter(([t, o]) => o.size && S.tp.has(t)).map(([t, o]) => t + ":" + [...o].join("|"));
    if (off.length) p.set("off", off.join(";"));
    if (S.region) p.set("rg", S.region);
    if (S.countries.size) p.set("c", [...S.countries].join(","));
    if (S.size !== "all") p.set("size", S.size);
    if (S.sort !== "auto") p.set("sort", S.sort);
    if (!S.reach) p.set("rch", "0");
    if (S.q) p.set("q", S.q);
    // checkboxes under "More": ck = ticked ones that are off by default, cko = unticked ones that are on by default
    const on = [...S.checks].filter((c) => !DEFAULT_CHECKS.has(c)), offc = [...DEFAULT_CHECKS].filter((c) => !S.checks.has(c));
    if (on.length) p.set("ck", on.join(","));
    if (offc.length) p.set("cko", offc.join(","));
    Object.entries(FLAGS).forEach(([k, id]) => { const el = $(id); if (el && el.checked !== el.defaultChecked) p.set(k, el.checked ? "1" : "0"); });
    const h = p.toString();
    history.replaceState(null, "", h ? "#" + h : location.pathname + location.search);
  }
  function restoreHash() {
    const p = new URLSearchParams(location.hash.slice(1));
    if (![...p.keys()].length) return;
    restoring = true;
    const fire = (el, ev) => el && el.dispatchEvent(new Event(ev));
    if (p.get("rg")) { $("f-region").value = p.get("rg"); fire($("f-region"), "change"); }
    (p.get("c") || "").split(",").filter((c) => CFG.countryName[c]).forEach((c) => S.countries.add(c));
    drawChosenCountries();
    Object.keys(SETS).forEach((k) => (p.get(k) || "").split(",").filter(Boolean).forEach((v) => {
      const b = document.querySelector(`.chip[data-f="${k}"][data-v="${CSS.escape(v)}"]`);
      if (b && !b.disabled) b.click();
      else if (k === "l") { S.langs.add(v); drawOtherLangs(); }
    }));
    const setCheck = (v, on) => { const c = document.querySelector(`#f-checks input[data-v="${CSS.escape(v)}"]`); if (c && !c.disabled && c.checked !== on) { c.checked = on; fire(c, "change"); } };
    (p.get("ck") || "").split(",").filter(Boolean).forEach((v) => setCheck(v, true));
    (p.get("cko") || "").split(",").filter(Boolean).forEach((v) => setCheck(v, false));
    (p.get("off") || "").split(";").filter(Boolean).forEach((x) => {
      const [t, subs] = x.split(":");
      (subs || "").split("|").forEach((s) => { const b = document.querySelector(`.chip[data-f="sub:${CSS.escape(t)}"][data-v="${CSS.escape(s)}"]`); if (b) b.click(); });
    });
    if (p.get("size")) { const r = document.querySelector(`input[name="size"][value="${CSS.escape(p.get("size"))}"]`); if (r) { r.checked = true; fire(r, "change"); } }
    if (p.get("sort")) { $("sort").value = p.get("sort"); fire($("sort"), "change"); }
    if (p.get("rch") === "0" && $("f-reach")) { $("f-reach").checked = false; fire($("f-reach"), "change"); }
    if (p.get("q") && $("q")) { $("q").value = p.get("q"); S.q = p.get("q").trim(); }
    Object.entries(FLAGS).forEach(([k, id]) => { if (p.get(k) && $(id)) { $(id).checked = p.get(k) !== "0"; fire($(id), "change"); } });
    restoring = false;
  }
  const visible = (list) => list.filter((x) => !x.later && !x.hidden);

  /* -------- filter groups fold in and out; the heading shows how many choices are active -------- */
  const OPEN_KEY = "pf-open-" + MODE;
  function setupGroups() {
    let saved = {}; try { saved = JSON.parse(localStorage.getItem(OPEN_KEY) || "{}"); } catch (e) { /* ignore */ }
    document.querySelectorAll("#filterBody .fgroup").forEach((g, i) => {
      const h = g.querySelector("h2"); if (!h) return;
      const title = h.textContent.trim(); g.dataset.title = title;
      const body = document.createElement("div"); body.className = "fbody";
      while (h.nextSibling) body.append(h.nextSibling);
      g.append(body);
      const open = title in saved ? saved[title] : i < 3;
      h.innerHTML = `<button type="button" class="fhead" aria-expanded="${open}"><span class="ftitle">${esc(title)}</span><span class="fcount" hidden></span><span class="farrow" aria-hidden="true"></span></button>`;
      body.hidden = !open;
      h.firstChild.addEventListener("click", () => setOpen(g, body.hidden, true));
    });
  }
  function setOpen(g, open, remember) {
    g.querySelector(".fbody").hidden = !open; g.querySelector(".fhead").setAttribute("aria-expanded", open);
    if (!remember) return;
    try { const sv = JSON.parse(localStorage.getItem(OPEN_KEY) || "{}"); sv[g.dataset.title] = open; localStorage.setItem(OPEN_KEY, JSON.stringify(sv)); } catch (e) { /* ignore */ }
  }
  function openActiveGroups() {  // a shared link: groups with a chosen filter are shown open
    document.querySelectorAll("#filterBody .fgroup").forEach((g) => { if (controlsOf(g).length) setOpen(g, true, false); });
  }
  /* every active choice of one filter group: [label, undo()] (chips, selects, radios, checkboxes changed from their default) */
  function controlsOf(g) {
    const out = [];
    g.querySelectorAll('.chip[aria-pressed="true"]:not(.sub)').forEach((c) => out.push([c.childNodes[0].textContent.replace(" ✕", "").trim(), () => c.click()]));
    g.querySelectorAll('.chip.sub[aria-pressed="false"]').forEach((c) => { if (!c.closest("[hidden]")) out.push(["without: " + c.childNodes[0].textContent.trim(), () => c.click()]); });
    g.querySelectorAll("select").forEach((sel) => { if (sel.value && !sel.dataset.adder) out.push([sel.selectedOptions[0].textContent.trim(), () => { sel.value = ""; sel.dispatchEvent(new Event("change")); }]); });
    g.querySelectorAll('input[type="radio"]:checked').forEach((r) => { if (!r.defaultChecked) out.push([r.parentElement.textContent.trim(), () => { const d = g.querySelector('input[type="radio"][name="' + r.name + '"]'); const def = [...g.querySelectorAll('input[type="radio"]')].find((x) => x.defaultChecked) || d; def.checked = true; def.dispatchEvent(new Event("change")); }]); });
    g.querySelectorAll('input[type="checkbox"]').forEach((c) => {
      if (c.checked !== c.defaultChecked && !c.closest("[hidden]")) out.push([(c.checked ? "" : "off: ") + c.parentElement.textContent.replace("no data yet", "").trim(), () => c.click()]);
    });
    return out;
  }
  function drawActive() {
    const bar = $("activeBar"); if (!bar) return;
    bar.innerHTML = "";
    const add = (text, undo) => { const b = document.createElement("button"); b.type = "button"; b.className = "achip"; b.innerHTML = esc(text) + ' <span aria-hidden="true">✕</span>'; b.setAttribute("aria-label", "Remove filter: " + text); b.addEventListener("click", undo); bar.append(b); };
    if (S.q) add("Name: " + S.q, () => { $("q").value = ""; S.q = ""; S.qAll = false; apply(); });
    document.querySelectorAll("#filterBody .fgroup").forEach((g) => {
      const list = controlsOf(g), fc = g.querySelector(".fcount");
      if (fc) { fc.hidden = !list.length; fc.textContent = list.length || ""; }
      list.forEach(([label, undo]) => add(label.length > 60 ? label.slice(0, 58) + "…" : label, undo));
    });
    bar.hidden = !bar.children.length;
    if (bar.children.length) { const l = document.createElement("span"); l.className = "alabel"; l.textContent = "Active filters:"; bar.prepend(l); }
  }

  function init() {
    const C = CFG.categories;
    const countryName = {}; CFG.countries.forEach((c) => { countryName[c.iso3] = c; });
    CFG.countryName = countryName;
    CFG.langName = {}; CFG.languages.concat(CFG.language_buttons).forEach((l) => { CFG.langName[l.code] = l.name; });
    setupGroups();
    const T = {}; Object.keys(FACET).forEach((g) => { T[g] = totals(g); });  // whole list: decides which buttons have data at all

    const chName = (c) => (C.channel.find((x) => x.id === c) || {}).label || c, plName = (c) => ((C.social_platform || []).find((x) => x.id === c) || {}).label || c;
    if ($("f-material")) C.material.forEach((m) => $("f-material").append(chip(esc(m.label), false, toggle(S.material, m.id), { title: "Finds outlets on: " + m.channels.map(chName).concat((m.platforms || []).map(plName)).join(", ") })));
    CFG.language_buttons.forEach((l) => $("f-langButtons").append(chip(counted("langs", l.code, esc(l.name)), false, toggle(S.langs, l.code))));
    const btn = new Set(CFG.language_buttons.map((l) => l.code));
    CFG.languages.filter((l) => !btn.has(l.code)).forEach((l) => $("f-otherLang").append(new Option(l.name, l.code)));
    $("f-otherLang").dataset.adder = "1";
    $("f-otherLang").addEventListener("change", (e) => { if (e.target.value) { S.langs.add(e.target.value); drawOtherLangs(); apply(); } e.target.value = ""; });
    $("f-noLang").addEventListener("change", (e) => { S.noLang = e.target.checked; apply(); });

    Object.keys(CFG.regions).forEach((r) => {
      const g = document.createElement("optgroup"); g.label = r;
      g.append(new Option(r + " (all)", "R:" + r));
      CFG.regions[r].forEach((s) => g.append(new Option(s, "S:" + s)));
      $("f-region").append(g);
    });
    $("f-region").addEventListener("change", (e) => { S.region = e.target.value; S.countries.clear(); drawCountries(); drawChosenCountries(); apply(); });
    $("f-country").dataset.adder = "1";  // several countries can be chosen, one after the other (review 13.11.2026)
    $("f-country").addEventListener("change", (e) => { if (e.target.value) { S.countries.add(e.target.value); drawChosenCountries(); apply(); } e.target.value = ""; });
    drawCountries();
    if ($("f-scope")) {
    C.scope.forEach((s) => $("f-scope").append(chip(counted("scope", s.id, esc(s.label)), false, toggle(S.scope, s.id), { title: s.description || "" })));
    $("f-scopeUnknown").addEventListener("change", (e) => { S.scopeUnknown = e.target.checked; apply(); });
    $("f-reach").addEventListener("change", (e) => { S.reach = e.target.checked; apply(); });
    $("f-worldwide").addEventListener("change", (e) => { S.worldwide = e.target.checked; apply(); });
    }
    if ($("f-orgType")) {
    if ($("orgTypeHelp")) $("orgTypeHelp").innerHTML = visible(C.org_type).filter((o) => o.description).map((o) => `<dt>${esc(o.label)}</dt><dd>${esc(o.description)}</dd>`).join("");
    visible(C.org_type).forEach((o) => $("f-orgType").append(chip(counted("orgType", o.id, esc(o.label)), false, toggle(S.orgType, o.id))));
    visible(C.channel).forEach((c) => {
      const t = toggle(S.channel, c.id);
      const fn = (b) => {
        t(b);
        if (c.id === "social_media") {  // fold-out: social media platforms (categories.yaml social_platform)
          $("f-platformBox").hidden = !S.channel.has("social_media");
          if (!S.channel.has("social_media")) { S.platforms.clear(); $("f-platform").querySelectorAll(".chip").forEach((x) => x.setAttribute("aria-pressed", "false")); apply(); }
        }
      };
      fn._set = t._set; fn._v = t._v;
      $("f-channel").append(chip(counted("channel", c.id, esc(c.label)), false, fn));
    });
    (C.social_platform || []).forEach((pl) => {
      $("f-platform").append(chip(counted("platform", pl.id, esc(pl.label)), false, toggle(S.platforms, pl.id),
        T.platform[pl.id] ? {} : { disabled: true, title: "No outlet with this platform found yet" }));
    });
    $("f-chUnknown").addEventListener("change", (e) => { S.chUnknown = e.target.checked; apply(); });
    }
    if ($("f-network")) CFG.networks.forEach((n) => $("f-network").append(chip(counted("nets", n.id, esc(n.label)), false, toggle(S.nets, n.id))));
    C.size.forEach((s) => {
      const l = document.createElement("label");
      l.innerHTML = `<input type="radio" name="size" value="${esc(s.id)}" ${s.default ? "checked" : ""}> ${esc(s.label)}`;
      l.querySelector("input").addEventListener("change", () => { S.size = s.id; apply(); });
      $("f-size").append(l);
    });
    const forPage = (t) => (MODE === "ngo" ? (t || "").replace(/outlets/g, "NGOs").replace(/outlet/g, "NGO") : t || "");
    $("sizeNote").textContent = forPage(MODE === "ngo" ? CFG.size_note_ngo || CFG.size_note : CFG.size_note);
    if ($("strengthNote")) $("strengthNote").textContent = forPage(CFG.topic_strength_note);
    C.topic_groups.forEach((g) => {
      const d = document.createElement("div"); d.className = "topic-group";
      d.innerHTML = `<h3>${esc(g.label)}</h3>`;
      const ch = document.createElement("div"); ch.className = "chips";
      const subBoxes = [];
      C.topics.filter((t) => t.group === g.id).forEach((t) => {
        const n = T.tp[t.id] || 0;
        let box = null;
        if (t.subtopics) {  // sub-topics: shown when the topic is chosen, all included until unticked
          box = document.createElement("div"); box.className = "subtopics"; box.hidden = true;
          box.innerHTML = `<p class="hint">${esc(t.label)}: all sub-topics are included. Untick to be more specific.</p>`;
          const sc = document.createElement("div"); sc.className = "chips";
          t.subtopics.forEach((s) => {
            const b = chip(counted("sub", t.id + "/" + s.id, esc(s.label)), true, (btn) => {
              const off = S.subOff[t.id] || (S.subOff[t.id] = new Set());
              off.has(s.id) ? off.delete(s.id) : off.add(s.id);
              btn.setAttribute("aria-pressed", off.has(s.id) ? "false" : "true"); apply();
            });
            b.classList.add("sub"); b.dataset.f = "sub:" + t.id; b.dataset.v = s.id; sc.append(b);
          });
          box.append(sc); subBoxes.push(box);
        }
        const label = (t.sdg ? `SDG ${t.sdg} ` : "") + t.label;
        ch.append(chip(counted("tp", t.id, esc(label)), false, (b) => {
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
    C.audience.forEach((a) => {
      $("f-audience").append(chip(counted("au", a.id, esc(a.label)), false, toggle(S.au, a.id),
        T.au[a.id] ? { title: a.description || "" } : { disabled: true, title: "No open source for this yet (the website check may add it later)" }));
    });
    if ($("f-unProfile")) C.un_profile.filter((u) => !u.shown_in).forEach((u) => {
      $("f-unProfile").append(chip(counted("un", u.id, esc(u.label)), false, toggle(S.un, u.id),
        T.un[u.id] ? { title: u.description || "" } : { disabled: true, title: "No open source for this yet (hand corrections or the website check may add it later)" }));
    });
    const om = C.checkboxes.find((c) => c.id === "only_topic_matches") || { label: "Only show topic matches" };
    $("onlyMatchesLabel").textContent = om.label;
    S.onlyMatches = !!om.default; $("f-onlyMatches").checked = S.onlyMatches; $("f-onlyMatches").defaultChecked = S.onlyMatches;
    if (om.description) $("onlyMatchesLabel").parentElement.title = om.description;
    $("f-onlyMatches").addEventListener("change", (e) => { S.onlyMatches = e.target.checked; apply(); });
    const am = C.checkboxes.find((c) => c.id === "all_topic_matches");
    if ($("f-allMatches")) {
      if (am) { $("allMatchesLabel").textContent = am.label; $("f-allMatches").parentElement.title = am.description || ""; }
      $("f-allMatches").addEventListener("change", (e) => { S.allMatches = e.target.checked; apply(); });
    }
    const checkAvail = { only_verified: true, has_social_media: true, has_public_contact: true, hide_state_controlled: true,
                         hide_website_down: true, only_new: true, only_active: true, only_news: true };
    // "Only new" is of no use while everything was found in the same weeks (before the first automatic update)
    const since = newSince(); if (!ALL.some((o) => o.f < since)) checkAvail.only_new = "hide";
    // NGO page: no state-controlled media, no "news media" box; "verified" = more than one NGO list
    C.checkboxes.filter((c) => !["include_reach", "include_no_language", "only_topic_matches", "all_topic_matches"].includes(c.id) && checkAvail[c.id] !== "hide"
      && !(MODE === "ngo" && ["hide_state_controlled", "only_news"].includes(c.id))).forEach((c) => {
      const l = document.createElement("label");
      l.className = "check" + (checkAvail[c.id] ? "" : " pending");
      l.innerHTML = `<input type="checkbox" ${checkAvail[c.id] ? "" : "disabled"}> <span>${esc(MODE === "ngo" ? forPage(c.label) : c.label)}${checkAvail[c.id] ? "" : ' <span class="soon">no data yet</span>'}</span>`;
      if (c.description) l.title = c.description;
      const inp = l.querySelector("input");
      inp.dataset.v = c.id;
      if (c.default && checkAvail[c.id]) { inp.checked = true; inp.defaultChecked = true; S.checks.add(c.id); DEFAULT_CHECKS.add(c.id); }
      inp.addEventListener("change", (e) => { e.target.checked ? S.checks.add(c.id) : S.checks.delete(c.id); apply(); });
      $("f-checks").append(l);
    });
    [["auto", "Best match, then best known"]].concat(C.sort.filter((s) => s.id !== "best_match").map((s) => [s.id, s.label])).forEach(([v, l]) => $("sort").append(new Option(l, v)));
    $("sort").addEventListener("change", (e) => { S.sort = e.target.value; apply(); });

    // "Reset filters": the address keeps the filters, so it is emptied first (until 13.11.2026 the reload restored them)
    $("reset").addEventListener("click", () => { history.replaceState(null, "", location.pathname + location.search); location.reload(); });
    if ($("copyLink")) $("copyLink").addEventListener("click", (e) => {
      const done = () => { const b = e.currentTarget || $("copyLink"); const old = "Copy link"; $("copyLink").textContent = "Link copied ✓"; setTimeout(() => { $("copyLink").textContent = old; }, 2000); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(location.href).then(done, () => window.prompt("Copy this link:", location.href));
      else window.prompt("Copy this link:", location.href);
    });
    if ($("q")) {
      $("q").placeholder = `Search ${WORD[1]} by name…`;
      let timer = null;
      $("q").addEventListener("input", (e) => { clearTimeout(timer); timer = setTimeout(() => { S.q = e.target.value.trim(); S.qAll = false; apply(); }, 200); });
    }
    $("cards").addEventListener("click", (e) => {
      if (e.target.id === "searchAll") { S.qAll = true; apply(); }
      if (e.target.id === "resetInline") $("reset").click();
    });
    $("counter").addEventListener("click", (e) => {
      if (e.target.id !== "showMore") return;
      const g = $("f-checks").closest(".fgroup"); setOpen(g, true, false);
      if (!$("filters").classList.contains("open")) $("filtersToggle").click();
      g.scrollIntoView({ block: "center" }); const f = g.querySelector("input"); if (f) f.focus();
    });
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
    initNgo(T);
    registerCounts();
    $("dataInfo").textContent = `Data collected ${CFG.data_date} · page built ${CFG.built}`;
    updateExportCount();
  }

  /* -------- NGO page (config/ngo.yaml): UN status, type of work, geographic scope, based in / active in -------- */
  const ECOSOC_STATUS = ["ecosoc_general", "ecosoc_special", "ecosoc_roster"];
  function initNgo(T) {
    const N = CFG.ngo;
    if (MODE !== "ngo" || !N) return;
    $("ngoPageHint").textContent = N.page_hint || "";
    $("ngoEcosocLabel").textContent = N.only_ecosoc_label;
    $("ngoHideRegLabel").textContent = N.hide_registered_label;
    $("hqOnlyLabel").textContent = N.hq_only_label;
    N.un_status.forEach((u) => $("f-ngoStatus").append(chip(counted("ngoStatus", u.id, esc(u.label)), false, toggle(S.ngoStatus, u.id),
      T.ngoStatus[u.id] ? { title: u.note || "" } : { disabled: true, title: "No NGO with this status in the sources yet" })));
    N.type_of_work.forEach((t) => $("f-ngoType").append(chip(counted("ngoType", t.id, esc(t.label)), false, toggle(S.ngoType, t.id))));
    (N.geo_scope || []).forEach((g) => $("f-gscope").append(chip(counted("gscope", g.id, esc(g.label)), false, toggle(S.gscope, g.id),
      T.gscope[g.id] ? {} : { disabled: true, title: "Not read from the ECOSOC profiles yet" })));
    $("f-ngoEcosoc").addEventListener("change", (e) => { S.ngoEcosoc = e.target.checked; apply(); });
    $("f-ngoHideReg").addEventListener("change", (e) => { S.ngoHideReg = e.target.checked; apply(); });
    $("f-hqOnly").addEventListener("change", (e) => { S.hqOnly = e.target.checked; apply(); });
    // organisation type, sector (UN Global Compact), "all chosen statuses", existing UN partner (owner 13.11.2026)
    (N.org_kind || []).forEach((k) => $("f-orgKind").append(chip(counted("orgKind", k.id, esc(k.label)), false, toggle(S.orgKind, k.id),
      T.orgKind[k.id] ? {} : { disabled: true, title: "None in the sources yet" })));
    const secs = Object.keys(T.sector).sort();
    if (secs.reduce((n, x) => n + T.sector[x], 0) >= 50) secs.forEach((x) => $("f-sector").append(chip(counted("sector", x, esc(x)), false, toggle(S.sector, x))));
    else $("f-sector").closest(".fgroup").hidden = true;
    $("ngoAllLabel").textContent = N.all_status_label || "Must have all chosen statuses";
    const UP = N.un_partner || {};
    $("unPartnerLabel").textContent = UP.filter_label || "Only existing UN partners";
    $("unPartnerHint").textContent = UP.explanation || "";
    $("f-ngoAll").addEventListener("change", (e) => { S.ngoAll = e.target.checked; apply(); });
    $("f-unPartner").addEventListener("change", (e) => { S.unPartner = e.target.checked; apply(); });
  }

  function drawOtherLangs() {
    const box = $("f-otherChosen"); box.innerHTML = "";
    const btn = new Set(CFG.language_buttons.map((l) => l.code));
    [...S.langs].filter((c) => !btn.has(c)).forEach((c) => box.append(chip(esc(CFG.langName[c] || c) + " ✕", true, () => { S.langs.delete(c); drawOtherLangs(); apply(); })));
  }
  function drawChosenCountries() {
    const box = $("f-countryChosen"); if (!box) return; box.innerHTML = "";
    [...S.countries].forEach((c) => box.append(chip(esc((CFG.countryName[c] || {}).name || c) + " ✕", true, () => { S.countries.delete(c); drawChosenCountries(); apply(); })));
    $("f-country").options[0].textContent = S.countries.size ? "Add another country…" : "All countries";
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
  /* the chosen country an outlet from elsewhere is shown for (reach / country of activity), or "" */
  function viaCountry(o) {
    if (!S.countries.size || S.countries.has(o.c)) return "";
    return [...S.countries].find((c) => (o.rc && c in o.rc) || (o.ca && o.ca.includes(c))) || "";
  }

  /* "new" = first found less than new_months (categories.yaml) before the data date */
  function monthsBefore(n) {
    const d = new Date(CFG.data_date); d.setMonth(d.getMonth() - n);
    return d.toISOString().slice(0, 10);
  }
  function activeSince() { return monthsBefore(CFG.active_months || 3); }
  function newSince() { return monthsBefore(CFG.new_months || 4); }
  /* an outlet without any topic in the sources counts as "General news" (the default topic) */
  function topicsOf(o) { return o.tp ? o.tp.map((e) => e[0]) : ["general_news"]; }
  /* o.tp entries: [topic, strength (1 main focus, 2 own section, 3 covers it), reason, [sub-topics]] */
  function tpEntry(o, t) { return o.tp ? o.tp.find((e) => e[0] === t) : (t === "general_news" ? ["general_news", 3, -1] : null); }
  function topicMatch(o, t) {
    const e = tpEntry(o, t); if (!e) return null;
    const off = S.subOff[t]; if (!off || !off.size) return e;
    return (e[3] || []).some((s) => !off.has(s)) ? e : null;  // narrowed: only outlets with a chosen sub-topic
  }
  const STRENGTH = new Proxy({}, { get: (_, k) => ((CFG && CFG.topic_strength) || { 1: "Specialist", 2: "Has a section on it", 3: "Reports on it" })[k] });
  /* "General news" has no strength: a "specialist for general news" makes no sense (review 13.11.2026) */
  const strengthOf = (t, s) => (t === "general_news" || !s ? "" : STRENGTH[s]);
  function why(o, kind, id) {
    if (kind === "tp") {
      const e = tpEntry(o, id); if (!e || e[2] < 0) return "no topic in the sources: general news";
      const t = CFG.categories.topics.find((x) => x.id === id) || {};
      const subs = (e[3] || []).map((s) => ((t.subtopics || []).find((x) => x.id === s) || {}).label).filter(Boolean);
      return (strengthOf(id, e[1]) ? strengthOf(id, e[1]) + ": " : "") + (CFG.why[e[2]] || "") + (subs.length ? " · " + subs.join("; ") : "");
    }
    if (kind === "au") return CFG.why[o.aw[o.au.indexOf(id)]] || "";
    return CFG.why[o.uw[o.un.indexOf(id)]] || "";
  }
  /* the reason of a topic without its strength (the details list shows the strength next to the name) */
  function whyTopic(o, id) {
    const e = tpEntry(o, id); if (!e || e[2] < 0) return "no topic in the sources: counted as general news";
    const t = CFG.categories.topics.find((x) => x.id === id) || {};
    const subs = (e[3] || []).map((x) => ((t.subtopics || []).find((y) => y.id === x) || {}).label).filter(Boolean);
    return (CFG.why[e[2]] || "") + (subs.length ? " · " + subs.join("; ") : "");
  }
  const fold = (s) => String(s || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();

  /* -------- the hard filters, one test per filter group --------
     An outlet is shown when it passes every group. The number on a button counts the outlets that pass
     all OTHER groups, so it says what a click on that button would add. */
  function tests() {
    const C = CFG.categories, T = [];
    if (S.q) {
      const words = fold(S.q).split(/\s+/).filter(Boolean);
      T.push(["q", (o) => { const h = o._q || (o._q = fold(o.n + " " + (o.a || []).join(" ") + " " + (o.w || ""))); return words.every((w) => h.includes(w)); }]);
      if (S.qAll) return T;  // "search all": the name alone decides
    }
    if (MODE === "ngo") {
      if (S.ngoStatus.size) T.push(["ngoStatus", (o) => (S.ngoAll ? [...S.ngoStatus].every((u) => (o.us || []).includes(u)) : (o.us || []).some((u) => S.ngoStatus.has(u)))]);
      if (S.orgKind.size) T.push(["orgKind", (o) => S.orgKind.has(o.ok || "ngo")]);
      if (S.sector.size) T.push(["sector", (o) => !!(o.gc && S.sector.has(o.gc[2]))]);
      if (S.unPartner || S.ngoEcosoc || S.ngoHideReg) T.push(["ngoChecks", (o) => !(S.unPartner && !o.up) && !(S.ngoEcosoc && !(o.us || []).some((u) => ECOSOC_STATUS.includes(u))) && !(S.ngoHideReg && o.ro)]);
      if (S.ngoType.size) T.push(["ngoType", (o) => (o.nt || []).some((t) => S.ngoType.has(t[0]))]);
      if (S.gscope.size) T.push(["gscope", (o) => S.gscope.has(o.gs)]);
    }
    const activeIn = (o) => !S.hqOnly && o.ca;  // NGO page: countries of activity count unless "only based in"
    if (S.countries.size) T.push(["geo", (o) => S.countries.has(o.c) || (S.reach && [...S.countries].some((c) => reachesTarget(o, c))) || !!(activeIn(o) && o.ca.some((c) => S.countries.has(c)))]);
    else if (S.region) T.push(["geo", (o) => inRegion(o.c) || !!(activeIn(o) && o.ca.some(inRegion))]);
    if (S.scope.size) T.push(["scope", (o) => { const v = o.sc ? o.sc[0] : "unknown"; return S.scope.has(v) || (v === "unknown" && S.scopeUnknown); }]);
    if (S.material.size) {
      const mc = new Set(), mt = new Set(), mp = new Set();
      C.material.filter((m) => S.material.has(m.id)).forEach((m) => { m.channels.forEach((c) => mc.add(c)); (m.also_org_types || []).forEach((t) => mt.add(t)); (m.platforms || []).forEach((t) => mp.add(t)); });
      T.push(["material", (o) => o.ng || (!(o.ch || []).length && S.chUnknown) || (o.ch || []).some((c) => mc.has(c)) || Object.keys(o.so || {}).some((k) => mp.has(k)) || !!(o.o && mt.has(o.o[0]))]);
    }
    if (S.channel.size) T.push(["channel", (o) => (!(o.ch || []).length && S.chUnknown) || (o.ch || []).some((c) => S.channel.has(c))]);
    if (S.platforms.size) T.push(["platform", (o) => Object.keys(o.so || {}).some((k) => S.platforms.has(k))]);
    if (S.langs.size) T.push(["langs", (o) => (o.l ? o.l.some((l) => S.langs.has(l)) : S.noLang)]);
    if (S.orgType.size) T.push(["orgType", (o) => o.ng || !!(o.o && (S.orgType.has(o.o[0]) || (o.oa || []).some((t) => S.orgType.has(t))))]);
    if (S.nets.size) T.push(["nets", (o) => (o.nw || []).some((n) => S.nets.has(n))]);
    if (S.checks.size) {
      const k = S.checks, act = activeSince(), nw = newSince();
      T.push(["checks", (o) => !(k.has("only_news") && o.nn) && !(k.has("hide_state_controlled") && o.ow && o.ow[0] === "state_controlled")
        && !(k.has("only_verified") && o.s.length < 2) && !(k.has("has_social_media") && !o.so) && !(k.has("has_public_contact") && !o.em && !o.cp)
        && !(k.has("only_active") && !(o.lp && o.lp >= act)) && !(k.has("hide_website_down") && (o.wd || o.ww)) && !(k.has("only_new") && o.f < nw)]);
    }
    return T;
  }

  function apply() {
    if (restoring) return;
    saveHash();
    const C = CFG.categories;
    if ($("materialHint")) {
      const names = new Set();
      C.material.filter((m) => S.material.has(m.id)).forEach((m) => { m.channels.forEach((c) => names.add((C.channel.find((x) => x.id === c) || {}).label || c)); (m.platforms || []).forEach((p) => names.add(((C.social_platform || []).find((x) => x.id === p) || {}).label || p)); });
      $("materialHint").textContent = names.size ? "Shows outlets on: " + [...names].join(", ") : "";
    }
    const T = tests(), nearly = {};
    let hard = [];
    ALL.forEach((o) => {
      let fails = 0, g = null;
      for (let i = 0; i < T.length && fails < 2; i++) if (!T[i][1](o)) { fails++; g = T[i][0]; }
      if (!fails) hard.push(o); else if (fails === 1) (nearly[g] || (nearly[g] = [])).push(o);
    });
    // "Top 10 / Top 50 per country": the best-known among the outlets that fit all other filters, so the
    // list is not cut short when e.g. state-controlled media are hidden (review 13.11.2026). An outlet from
    // elsewhere that reaches the chosen country must be in the top of its own country.
    if (S.size !== "all") {
      const max = S.size === "top10" ? 10 : 50, per = {}, keep = new Set();
      hard.concat(nearly.geo || []).forEach((o) => { (per[o.c] || (per[o.c] = [])).push(o); });
      Object.values(per).forEach((l) => l.sort((a, b) => a.r - b.r).slice(0, max).forEach((o) => keep.add(o)));
      hard = hard.filter((o) => keep.has(o));
    }
    // numbers on the buttons
    Object.keys(CNT).forEach((g) => {
      const c = {}, f = FACET[g], add = (o) => f(o).forEach((v) => { c[v] = (c[v] || 0) + 1; });
      hard.forEach(add);
      if (!SOFT.includes(g)) (nearly[g === "platform" ? "platform" : g] || []).forEach(add);
      Object.entries(CNT[g]).forEach(([v, sp]) => { sp.textContent = num(c[v]); sp.parentElement.classList.toggle("empty", !c[v] && sp.parentElement.getAttribute("aria-pressed") !== "true"); });
    });
    const nSoft = S.tp.size + S.au.size + S.un.size;
    hard.forEach((o) => {
      o._m = [...S.tp].map((t) => [t, topicMatch(o, t)]).filter((x) => x[1]).map(([t, e]) => ["tp", t, e[1]]).concat((o.au || []).filter((a) => S.au.has(a)).map((a) => ["au", a])).concat((o.un || []).filter((u) => S.un.has(u)).map((u) => ["un", u]));
    });
    current = hard;
    if (nSoft && S.allMatches) current = current.filter((o) => o._m.length === nSoft);       // must match every chosen topic / audience / profile
    else if (nSoft && S.onlyMatches) current = current.filter((o) => o._m.length);          // must match at least one
    const mode = S.sort === "auto" ? "best_match" : S.sort;
    const key = (o) => o._k || (o._k = (o.n || "").replace(/^[^\p{L}\p{N}]+/u, ""));  // "__STUDY__" sorts under S
    const byName = (a, b) => key(a).localeCompare(key(b), "en", { sensitivity: "base" });
    // best match: topics count by strength (main focus 3, own section 2, covers it 1), audiences and UN profiles 1 each
    const score = (o) => o._s != null ? o._s : (o._s = o._m.reduce((n, m) => n + (m[0] === "tp" ? 4 - m[2] : 1), 0));
    current.forEach((o) => { o._s = null; });
    // equal match: outlets based in the chosen country before outlets that only reach it (owner, 09.11.2026)
    const home = (o) => (S.countries.has(o.c) ? 1 : 0);
    if (mode === "best_match") current.sort((a, b) => score(b) - score(a) || home(b) - home(a) || b.p - a.p || byName(a, b));
    else if (mode === "country") current.sort((a, b) => ((CFG.countryName[a.c] || {}).name || "").localeCompare((CFG.countryName[b.c] || {}).name || "") || a.r - b.r || byName(a, b));
    else current.sort(byName);
    const countries = new Set(current.map((o) => o.c)).size;
    const verified = current.filter((o) => o.s.length >= 2).length;
    nMatch = nSoft ? current.filter((o) => o._m.length).length : 0;
    const what = current.length === 1 ? WORD[0] : WORD[1];
    $("counter").innerHTML = `<b>${num(current.length)}</b> ${what} in <b>${countries}</b> ${countries === 1 ? "country" : "countries"} · ${num(verified)} verified`
      + (nSoft && !S.onlyMatches && !S.allMatches ? ` · <span class="matchcount"><b>${num(nMatch)}</b> match your ${MODE === "ngo" ? "topics / audience" : "topics / audience / UN profile"} (shown first)</span>` : "");
    // say what the boxes that are ticked by default hide (state-controlled media, non-news channels)
    const hid = (nearly.checks || []).length, defOn = [...DEFAULT_CHECKS].some((c) => S.checks.has(c));
    if (hid && defOn && !S.qAll) $("counter").insertAdjacentHTML("beforeend", ` · <button type="button" class="linklike" id="showMore" title="State-controlled media and pure sports, music, children's or religious channels are hidden by default. Click to change this under “More”.">${num(hid)} hidden by the boxes under “More”</button>`);
    // a name search that other filters cut down: say so and offer to search everything
    let note = "";
    if (S.q && !S.qAll) {
      const qt = T.find((t) => t[0] === "q")[1], all = ALL.filter(qt).length;
      if (all > current.length) note = `<li class="divider note">${num(all - current.length)} more ${all - current.length === 1 ? WORD[0] : WORD[1]} with this name ${all - current.length === 1 ? "is" : "are"} hidden by your other filters. <button type="button" class="btn-quiet" id="searchAll">Show all ${num(all)}</button></li>`;
    } else if (S.q && S.qAll) note = `<li class="divider note">Showing every ${WORD[0]} with this name; the other filters are ignored while you search.</li>`;
    if (!current.length && !note) note = `<li class="divider note">No ${WORD[0]} fits all your filters. Remove one of the active filters above, or <button type="button" class="btn-quiet" id="resetInline">reset all filters</button></li>`;
    draw(true, note);
    drawActive();
    updateAddAll();
  }

  const row = (label, html) => (html ? `<p class="row"><b>${label}:</b> ${html}</p>` : "");
  function card(o) {
    const C = CFG.categories, k = CFG.countryName[o.c] || {};
    const chans = (o.ch || []).map((c) => (C.channel.find((x) => x.id === c) || {}).label || c).join(", ");
    const langs = (o.l || []).map((l) => CFG.langName[l] || l).join(", ") || "<span class='pending'>no information</span>";
    const src = o.s.map((s) => CFG.source_labels[s] || s).join(", ");
    const social = Object.entries(o.so || {}).map(([k2, u]) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(k2)}</a>`).join(" · ");
    const verified = o.s.length >= 2 ? '<span class="badge verified" title="Listed by 2 or more independent sources">verified</span>' : '<span class="badge unverified" title="Listed by one source only">1 source</span>';
    const inList = exportList.has(o.i);
    const N = CFG.ngo || {};
    // topics: the chosen ones first, then the strongest; the short card shows 4, the details all with their reason
    const matched = new Set((o._m || []).filter((m) => m[0] === "tp").map((m) => m[1]));
    const tlist = topicsOf(o).map((t) => [t, tpEntry(o, t)]).sort((a, b) => (matched.has(b[0]) - matched.has(a[0])) || ((a[1] ? a[1][1] : 9) - (b[1] ? b[1][1] : 9)));
    const tshort = tlist.slice(0, 4).map(([t, e]) => `<span class="tag${matched.has(t) ? " hit" : ""}">${esc(lab(C.topics, t))}</span>` + (o.tp && strengthOf(t, e[1]) ? ` <span class="pending">(${esc(strengthOf(t, e[1]))})</span>` : "")).join(", ")
      + (tlist.length > 4 ? ` <span class="pending">+${tlist.length - 4} more in the details</span>` : "");
    const reason = (text, url) => `<span class="why">${esc(text)}${url && /^https?:/.test(url) ? ` · <a href="${esc(url)}" target="_blank" rel="noopener">open section ↗</a>` : ""}</span>`;
    const tfull = tlist.map(([t, e]) => `<li><b>${esc(lab(C.topics, t))}</b>${o.tp && strengthOf(t, e[1]) ? " – " + esc(strengthOf(t, e[1])) : ""} ${reason(whyTopic(o, t), e && e[4])}</li>`).join("");
    const aufull = (o.au || []).map((a) => `<li><b>${esc(lab(C.audience, a))}</b> ${reason(why(o, "au", a))}</li>`).join("");
    const unfull = (o.un || []).map((u) => `<li><b>${esc(lab(C.un_profile, u))}</b> ${reason(why(o, "un", u))}</li>`).join("");
    const gcRow = o.gc ? `<p class="row"><b>UN Global Compact:</b> participant${o.gc[0] ? " since " + esc(o.gc[0]) : ""}${o.gc[2] ? " · Sector: " + esc(o.gc[2]) : ""}${o.gc[3] ? ` · <a href="${esc(o.gc[3])}" target="_blank" rel="noopener">Global Compact profile ↗</a>` : ""}</p>`
      + (o.gc[1] && (N.gc_status_note || {})[o.gc[1]] ? `<p class="row warn">ⓘ ${esc(N.gc_status_note[o.gc[1]])}</p>` : "") : "";
    const typeLine = o.ng
      ? (o.ok && o.ok !== "ngo" ? esc(lab(N.org_kind || [], o.ok)) + " · " : "") + (esc((o.us || []).map((u) => lab(N.un_status || [], u)).join(", ")) || "<span class='pending'>no UN status</span>")
      : esc((C.org_type.find((x) => x.id === (o.o || [])[0]) || {}).label || (o.o || [])[0] || "") + (o.ow && o.ow[0] === "state_controlled" ? ' · <span class="warn">State-controlled</span>' : "");
    const contact = (o.em ? `<a href="mailto:${esc(o.em)}">${esc(o.em)}</a>` : "") + (o.em && o.cp ? " · " : "") + (o.cp ? `<a href="${esc(o.cp)}" target="_blank" rel="noopener">contact page ↗</a>` : "");
    const site = o.w ? `<a href="${esc(o.w)}" target="_blank" rel="noopener">${esc(o.w.replace(/^https?:\/\//, "").replace(/\/$/, ""))}</a>` : "";
    const ownRow = o.ng ? "" : o.ow && o.ow[0] !== "unknown" ? `<p class="row"><b>Ownership:</b> ${esc((C.ownership.find((x) => x.id === o.ow[0]) || {}).label || o.ow[0])}${o.on ? ` · <b>Owner:</b> ${esc(o.on.join(", "))}` : ""} ${reason(CFG.why[o.ow[1]])}</p>`
      : `<p class="row"><b>Ownership:</b> Unknown${o.on ? ` · <b>Owner:</b> ${esc(o.on.join(", "))}` : ""} <span class="why">No open source says what kind of owner this is. This does not mean it is independent or state-run.</span></p>`;
    const details = `
      ${o.ng ? "" : freedomText(k)}
      ${o.a ? `<p class="row"><b>Also known as:</b> ${esc(o.a.join(", "))}</p>` : ""}
      ${o.o && !o.ng ? `<p class="row"><b>Type:</b> ${esc((C.org_type.find((x) => x.id === o.o[0]) || {}).label || o.o[0])} ${reason(CFG.why[o.o[1]])}</p>` : ""}
      ${o.oa ? row("Also listed as", esc(o.oa.map((t) => (C.org_type.find((x) => x.id === t) || {}).label || t).join(", "))) : ""}
      ${ownRow}
      ${o.sc && o.sc[0] !== "unknown" ? `<p class="row"><b>Scope:</b> ${esc((C.scope.find((x) => x.id === o.sc[0]) || {}).label || o.sc[0])} ${reason(CFG.why[o.sc[1]])}</p>` : ""}
      ${o.ng && o.pu ? `<p class="row"><b>ECOSOC:</b> <a href="${esc(o.pu)}" target="_blank" rel="noopener">ECOSOC profile ↗</a></p>` : ""}
      ${gcRow}
      ${o.ng && o.nt ? `<p class="row"><b>Type of work:</b></p><ul class="reasons">${o.nt.map((t) => `<li><b>${esc(lab(N.type_of_work || [], t[0]))}</b> ${reason(CFG.why[t[1]] || "")}</li>`).join("")}</ul>` : ""}
      ${o.ng && o.ds && o.ds.length > 220 ? `<p class="row desc">${esc(o.ds)}</p>` : ""}
      ${o.sv ? row("Language services", esc(o.sv.join(", "))) : ""}
      <p class="row"><b>Topics and why:</b></p><ul class="reasons">${tfull}</ul>
      ${aufull ? `<p class="row"><b>Target audience and why:</b></p><ul class="reasons">${aufull}</ul>` : ""}
      ${unfull ? `<p class="row"><b>UN profile and why</b> <span class="pending">(hints found automatically – please check)</span><b>:</b></p><ul class="reasons">${unfull}</ul>` : ""}
      ${row("Social media", social)}
      ${o.lp ? `<p class="row pending">Latest article seen on the website: ${esc(o.lp)}${o.lp < activeSince() ? " (no recent article found)" : ""}</p>` : ""}
      <p class="row pending">Sources: ${esc(src)} · id ${esc(o.i)} · <a href="${esc(reportLink(o))}" target="_blank" rel="noopener">Report an error</a></p>`;
    return `<li class="card${inList ? " selected" : ""}${o.ng ? " is-ngo" : ""}" data-id="${esc(o.i)}"><div class="card-top"><h3>${esc(o.n)}</h3>${o.up ? `<span class="badge partner" title="${esc(((N.un_partner || {}).explanation) || "")}">${esc((N.un_partner || {}).label || "Existing UN partner")}</span>` : ""}${verified}</div>
      <p class="meta">Based in: <b>${esc(k.name || o.c)}</b> (${esc(k.subregion || "")})${o.ng ? (activeText(o) ? " · " + activeText(o) : "") : " · " + reachText(o)}${!o.ng && o.sc && o.sc[0] !== "unknown" ? ` · ${esc((C.scope.find((x) => x.id === o.sc[0]) || {}).label || o.sc[0])}` : ""}</p>
      ${o.ng && o.ds ? `<p class="row desc">${esc(o.ds.length > 220 ? o.ds.slice(0, 220).replace(/\s+\S*$/, "") + " …" : o.ds)}</p>` : ""}
      <p class="row"><b>${o.ng ? "UN status" : "Type"}:</b> ${typeLine} · <b>Languages:</b> ${langs}${o.ng ? "" : ` · <b>Channels:</b> ${esc(chans) || "<span class='pending'>no information</span>"}`}</p>
      ${o.ro ? `<p class="row warn">ⓘ ${esc(((N.un_status || []).find((u) => u.id === "ecosoc_registered") || {}).note || "Only registered in the ECOSOC database.")}</p>` : ""}
      ${o.ng && o.nt ? row("Type of work", esc(o.nt.map((t) => lab(N.type_of_work || [], t[0])).join(", "))) : ""}
      <p class="row"><b>Topics:</b> ${tshort}</p>
      ${(o.au || []).length ? row("Target audience", esc(o.au.map((a) => lab(C.audience, a)).join(", "))) : ""}
      ${(o.un || []).length ? row("UN profile", esc(o.un.map((u) => lab(C.un_profile, u)).join(", "))) : ""}
      ${o.ww ? `<p class="row warn">⚠ Website may no longer belong to this outlet: ${esc(o.ww)}</p>` : ""}
      ${site || contact ? `<p class="row">${site ? `<b>Website:</b> ${site}${o.wd ? ' <span class="warn">(did not answer at the last check)</span>' : ""}` : ""}${site && contact ? " · " : ""}${contact ? `<b>Contact:</b> ${contact}` : ""}</p>` : ""}
      ${o._m && o._m.length ? `<span class="matches">Matches: ${esc(o._m.map(([k2, id, s]) => lab(k2 === "tp" ? C.topics : k2 === "au" ? C.audience : C.un_profile, id) + (k2 === "tp" && strengthOf(id, s) ? ` (${strengthOf(id, s)})` : "")).join(", "))}</span>` : ""}
      <div class="card-foot"><label class="export-check"><input type="checkbox" class="export-box" data-id="${esc(o.i)}" ${inList ? "checked" : ""}> Export</label>
      <details class="more-info"><summary>Details and reasons</summary>${details}</details></div></li>`;
  }

  /* "Report an error" opens a pre-filled error report (GitHub issue; the owner's e-mail address is not public) */
  function reportLink(o) {
    const k = CFG.countryName[o.c] || {};
    const body = `${MODE === "ngo" ? "Organisation" : "Outlet"}: ${o.n} (${k.name || o.c}), id ${o.i}\nWebsite: ${o.w || "-"}\n\nWhat is wrong (e.g. topic, type, ownership, contact, outlet closed)?\n\n\nFilters used: ${location.href}`;
    if (CFG.feedback_email) return `mailto:${CFG.feedback_email}?subject=${encodeURIComponent("Partner Finder: error report " + o.i)}&body=${encodeURIComponent(body)}`;
    return `${CFG.feedback_url || "https://github.com/hannascoder/New-Partnership-Tool/issues/new"}?title=${encodeURIComponent("Error report: " + o.n + " (" + o.i + ")")}&body=${encodeURIComponent(body)}`;
  }
  function activeText(o) {
    const C = CFG.countryName, N = CFG.ngo || {};
    const gs = o.gs ? "Scope: " + esc(lab(N.geo_scope || [], o.gs)) : "";
    if (!o.ca || !o.ca.length) return gs;
    const names = o.ca.map((c) => (C[c] || {}).name || c);
    const via = viaCountry(o), vname = via ? (C[via] || {}).name : "";
    const hit = via && o.ca.includes(via) ? `<b>${esc(vname)}</b>, ` : "";
    return `Also active in: ${hit}${esc(names.filter((x) => !hit || x !== vname).slice(0, 6).join(", "))}${names.length > 6 ? ` and ${names.length - 6} more` : ""}` + (gs ? " · " + gs : "");
  }
  function basisText(b) {
    return b.startsWith("language_service:") ? "via " + b.slice(17) : b === "broadcast_area" ? "broadcast area" : b === "worldwide" ? "worldwide broadcaster" : "international broadcaster";
  }
  function reachText(o) {
    const C = CFG.countryName;
    if (!o.rc) return "Reaches: " + esc((C[o.c] || {}).name || o.c);
    const n = Object.keys(o.rc).length + 1;
    const via = viaCountry(o);
    if (via && via in o.rc) {
      return `Reaches: <b>${esc((C[via] || {}).name)}</b> (${esc(basisText(CFG.why[o.rc[via]]))}) and ${n - 1} other countries`;
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

  function draw(fromStart, note) {
    if (fromStart) { shown = 0; $("cards").innerHTML = note || ""; }
    const slice = current.slice(shown, shown + PAGE);
    const soft = S.tp.size || S.au.size || S.un.size;
    $("cards").insertAdjacentHTML("beforeend", slice.map((o, j) => {
      const divider = soft && !S.onlyMatches && !S.allMatches && shown + j === nMatch && nMatch < current.length
        ? `<li class="divider">${nMatch ? `Other ${WORD[1]} that fit your other filters (no match for the chosen topics, audience or UN profile)` : `No ${WORD[0]} matches the chosen topics, audience or UN profile – showing all ${WORD[1]} that fit your other filters`}</li>` : "";
      return divider + card(o);
    }).join(""));
    shown += slice.length;
    $("more").hidden = shown >= current.length;
    $("more").textContent = `Show more (${num(current.length - shown)} left)`;
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
      const label = g.dataset.title || "";
      const chips = [...g.querySelectorAll('.chip[aria-pressed="true"]:not(.sub)')].map((c) => c.childNodes[0].textContent.replace(" ✕", "").trim());
      // a select is named by its own label ("Country: Kenya"), chips and radios by the group heading
      g.querySelectorAll("select").forEach((sel) => {
        const own = sel.closest("label"); const name = own ? own.childNodes[0].textContent.trim() : label;
        if (sel.value && sel.selectedOptions[0] && !sel.dataset.adder) out.push([name, sel.selectedOptions[0].textContent.trim()]);
      });
      const values = chips.slice();
      g.querySelectorAll('input[type="radio"]:checked').forEach((r) => { if (!r.defaultChecked) values.push(r.parentElement.textContent.trim()); });
      if (values.length) out.push([label, values.join(", ")]);
      // ticked checkboxes (those ticked by default, like "include reach", only when changed)
      g.querySelectorAll('input[type="checkbox"]').forEach((c) => {
        if (c.checked !== c.defaultChecked) out.push([c.parentElement.textContent.replace("no data yet", "").trim(), c.checked ? "" : "off"]);
      });
    });
    Object.entries(S.subOff).forEach(([t, off]) => {
      if (!off.size || !S.tp.has(t)) return;
      const tt = CFG.categories.topics.find((x) => x.id === t) || {};
      out.push([tt.label + " – only", (tt.subtopics || []).filter((s) => !off.has(s.id)).map((s) => s.label).join("; ")]);
    });
    const search = $("q");
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
      const list = buildExportList([...exportList], headerFilters(), S.countries.size === 1 ? [...S.countries][0] : null, topics);
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
    if (o.ro) f.push("Only registered in ECOSOC (not checked by the UN)");
    if (o.gc && o.gc[1] && o.gc[1] !== "Active") f.push("UN Global Compact: " + o.gc[1]);
    if (o.s.length < 2 && !o.ng) f.push("Unverified");
    if (o.wd) f.push("Website not reachable");
    if (o.ww) f.push("Website may no longer belong to the outlet");
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
    if (o.ng) {
      const N = CFG.ngo || {};
      return {
        name: o.n + (o.ok && o.ok !== "ngo" ? ` (${lab(N.org_kind || [], o.ok)})` : ""),
        type: [o.up ? (N.un_partner || {}).label || "Existing UN partner" : ""].concat((o.us || []).map((u) => lab(N.un_status || [], u) + (u === "un_global_compact" && o.gc && o.gc[0] ? " since " + o.gc[0] : ""))).filter(Boolean).join(", "),
        country: k.name || o.c,
        reaches: (o.ca || []).map((c) => (K[c] || {}).name || c).join(", "),
        scope: o.gs ? lab(N.geo_scope || [], o.gs) : "",
        languages: (o.l || []).map((l) => CFG.langName[l] || l).join(", "),
        channels: (o.nt || []).map((t) => lab(N.type_of_work || [], t[0])).join(", "),
        ownership: o.ds || "",
        topic: topicsOf(o).filter((t) => !topicFilter || !topicFilter.size || topicFilter.has(t)).map((t) => lab(C.topics, t)).join(", "),
        audience: (o.au || []).map((a) => lab(C.audience, a)).join(", "),
        unProfile: [o.pu, o.gc && o.gc[3]].filter(Boolean).join(" "), memberOf: "",
        website: o.w || "", contact: o.em || o.cp || "",
        social: Object.entries(o.so || {}).map(([k2, u]) => [{ youtube: "YouTube", facebook: "Facebook", instagram: "Instagram", tiktok: "TikTok", x: "X", telegram: "Telegram" }[k2] || k2, u]),
        notes: flags(o),
      };
    }
    return {
      name: o.n, type: types.join(" / "), country: k.name || o.c, reaches,
      scope: o.sc && o.sc[0] !== "unknown" ? lab(C.scope, o.sc[0]) : "",
      languages: (o.l || []).map((l) => CFG.langName[l] || l).join(", "),
      channels: (o.ch || []).map((c) => lab(C.channel, c)).join(", "),
      ownership: o.ng ? "" : (o.ow ? lab(C.ownership, o.ow[0]) : "Unknown") + (o.on ? " (" + o.on.join(", ") + ")" : ""),
      topic: topics.join(", "),
      audience: (o.au || []).map((a) => lab(C.audience, a)).join(", "),
      unProfile: (o.un || []).map((u) => lab(C.un_profile, u)).join(", "),
      memberOf: o.ng ? (o.us || []).map((u) => lab((CFG.ngo || {}).un_status || [], u)).concat((o.nt || []).map((t) => "Type of work: " + lab((CFG.ngo || {}).type_of_work || [], t[0]))).join(", ")
        : (o.nw || []).map((n) => (CFG.networks.find((x) => x.id === n) || {}).label || n).join(", "),
      website: o.w || "", contact: o.em || o.cp || "",
      social: Object.entries(o.so || {}).map(([k2, u]) => [{ youtube: "YouTube", facebook: "Facebook", instagram: "Instagram", tiktok: "TikTok", x: "X", telegram: "Telegram" }[k2] || k2, u]),
      notes: flags(o),
    };
  }
  /* sections (EXPORT_SPEC): "Best UN fit" = items with a UN profile, best first;
     then "By country & rank" = all others, country A-Z, then rank */
  function buildExportList(ids, filterSets, countryFilter, topicFilter) {
    const byId = {}; ALL.forEach((o) => { byId[o.i] = o; });
    const all = [...new Set(ids)].map((id) => byId[id]).filter(Boolean);
    const items = all.filter((o) => !o.ng), ngoItems = all.filter((o) => o.ng);  // owner: NGOs separate in the export
    const K = CFG.countryName;
    const fit = items.filter((o) => (o.un || []).length).sort((a, b) => b.un.length - a.un.length || b.p - a.p || a.n.localeCompare(b.n));
    const rest = items.filter((o) => !(o.un || []).length).sort((a, b) => ((K[a.c] || {}).name || "").localeCompare((K[b.c] || {}).name || "") || a.r - b.r);
    const row = (o) => exportRow(o, countryFilter, topicFilter);
    if (MODE === "ngo") {  // NGO page: own columns (owner 12.11.2026: UN status, type of work, countries of activity)
      return {
        sections: [{ title: "NGOs", note: "By country (A–Z), then by UN status and prominence.",
          items: ngoItems.sort((a, b) => ((K[a.c] || {}).name || "").localeCompare((K[b.c] || {}).name || "") || a.r - b.r).map(row) }],
        filters: filterSets, count: all.length, updated: CFG.data_date, itemWord: "NGO", layout: NGO_LAYOUT,
      };
    }
    return {
      sections: [
        { title: "Best UN fit", note: "Outlets with a UN profile (e.g. existing UN relationship), best match first.", items: fit.map(row) },
        { title: "By country & rank", note: "All other outlets, by country (A–Z), then by prominence rank within the country.", items: rest.map(row) },
        { title: "NGOs", note: "Non-governmental organisations, by country (A–Z), then by UN status and prominence.",
          items: ngoItems.sort((a, b) => ((K[a.c] || {}).name || "").localeCompare((K[b.c] || {}).name || "") || a.r - b.r).map(row) }],
      filters: filterSets, count: all.length, updated: CFG.data_date,
    };
  }
  const NGO_LAYOUT = {
    file: "partner-finder-ngos",
    note: "Orientation only. Please confirm that an NGO is active before contacting it.",
    cols: [["name", "Name", 24], ["type", "UN status", 18], ["country", "Based in", 14], ["reaches", "Also active in", 20],
      ["scope", "Geographic scope", 13], ["languages", "Languages", 16], ["channels", "Type of work", 16], ["ownership", "Description", 34],
      ["topic", "Topic", 16], ["audience", "Target audience", 14], ["unProfile", "UN profile pages", 16], ["website", "Website", 20],
      ["contact", "Contact", 19], ["social", "Social media", 16], ["notes", "Notes", 18]],
    groups: {
      outlet: [["name", ""], ["type", "UN status"], ["country", "Based in"], ["scope", "Geographic scope"], ["channels", "Type of work"]],
      reach: [["ownership", ""], ["reaches", "Also active in"], ["languages", "Languages"], ["topic", "Topic"], ["audience", "Target audience"]],
      more: [["unProfile", "UN profile pages"], ["social", "Social media"], ["notes", "Notes"]] },
    portrait: [["outlet", "NGO", 50], ["reach", "Description & work", 66], ["website", "Website", 26], ["contact", "Contact", 26], ["more", "ECOSOC, social media & notes", 26]],
  };
  window.PF = { exportList: buildExportList, all: () => ALL, cfg: () => CFG };

  function updateExportCount() {
    const n = exportList.size;
    $("exportBar").hidden = n === 0;
    $("exportCount").textContent = `${n.toLocaleString("en")} ${n === 1 ? WORD[0] : WORD[1]} in the export list`;
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
