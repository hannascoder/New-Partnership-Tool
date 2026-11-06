/* Partner Finder: filters the outlets in data/outlets.json in the browser.
   All allowed values come from data/config.json (built from config/).
   Filter logic (briefing L): hard filters must match; within one filter OR,
   between filters AND. Topics and UN profile only change the order. */
(function () {
  "use strict";
  const PAGE = 50;
  const S = { own: new Set(), ownUnknown: false, nets: new Set(), orgType: new Set(), material: new Set(), langs: new Set(), noLang: false, region: "", country: "",
              channel: new Set(), size: "all", un: new Set(), checks: new Set(), sort: "auto" };
  let CFG, ALL = [], shown = 0, current = [];
  const exportList = new Set(loadList());
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function loadList() { try { return JSON.parse(localStorage.getItem("pf-export") || "[]"); } catch (e) { return []; } }
  function saveList() { try { localStorage.setItem("pf-export", JSON.stringify([...exportList])); } catch (e) { /* private window */ } }

  Promise.all([fetch("data/config.json").then((r) => r.json()), fetch("data/outlets.json").then((r) => r.json())])
    .then(([cfg, outlets]) => { CFG = cfg; ALL = outlets; init(); apply(); })
    .catch(() => { $("counter").textContent = "The data could not be loaded. Please reload the page."; });

  function chip(label, pressed, onClick, opts = {}) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "chip"; b.innerHTML = label;
    b.setAttribute("aria-pressed", pressed ? "true" : "false");
    if (opts.disabled) { b.disabled = true; b.title = opts.title || "Available after step 4 (classification)"; }
    if (opts.title && !opts.disabled) b.title = opts.title;
    b.addEventListener("click", () => { onClick(b); });
    return b;
  }
  function toggle(set, value) { return (b) => { set.has(value) ? set.delete(value) : set.add(value); b.setAttribute("aria-pressed", set.has(value)); apply(); }; }
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
    C.scope.forEach((s) => $("f-scope").append(chip(esc(s.label), false, () => {}, { disabled: true })));
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
    C.topic_groups.forEach((g) => {
      const d = document.createElement("div"); d.className = "topic-group";
      d.innerHTML = `<h3>${esc(g.label)}</h3>`;
      const ch = document.createElement("div"); ch.className = "chips";
      C.topics.filter((t) => t.group === g.id).forEach((t) => ch.append(chip(esc(t.label) + (t.sdg ? ` <span class="sdg">SDG ${t.sdg}</span>` : ""), false, () => {}, { disabled: true })));
      d.append(ch); $("f-topics").append(d);
    });
    const unAvailable = new Set(["un_relationship"]);
    C.un_profile.forEach((u) => $("f-unProfile").append(chip(esc(u.label), false, toggle(S.un, u.id),
      unAvailable.has(u.id) ? { title: u.description || "SDG Media Compact member" } : { disabled: true, title: "Available after step 4 (classification)" })));
    const checkAvail = { only_verified: true, has_social_media: true, has_public_contact: true, hide_state_controlled: true };
    C.checkboxes.filter((c) => !["include_reach", "include_no_language"].includes(c.id)).forEach((c) => {
      const l = document.createElement("label");
      l.className = "check" + (checkAvail[c.id] ? "" : " pending");
      l.innerHTML = `<input type="checkbox" ${checkAvail[c.id] ? "" : "disabled"}> ${esc(c.label)}${checkAvail[c.id] ? "" : ' <span class="soon">step 4</span>'}`;
      l.querySelector("input").addEventListener("change", (e) => { e.target.checked ? S.checks.add(c.id) : S.checks.delete(c.id); apply(); });
      $("f-checks").append(l);
    });
    [["auto", "Best match / A–Z (automatic)"]].concat(C.sort.map((s) => [s.id, s.label])).forEach(([v, l]) => $("sort").append(new Option(l, v)));
    $("sort").addEventListener("change", (e) => { S.sort = e.target.value; apply(); });

    $("reset").addEventListener("click", () => location.reload());
    $("more").addEventListener("click", () => draw(false));
    $("addAll").addEventListener("click", () => { current.forEach((o) => exportList.add(o.i)); saveList(); updateExportCount(); draw(true); });
    $("openExport").addEventListener("click", openExport);
    $("closeExport").addEventListener("click", () => $("exportDialog").close());
    $("clearExport").addEventListener("click", () => { exportList.clear(); saveList(); updateExportCount(); openExport(); draw(true); });
    $("downloadCsv").addEventListener("click", downloadCsv);
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

  function anyFilter() {
    return S.own.size || S.nets.size || S.orgType.size || S.material.size || S.langs.size || S.region || S.country || S.channel.size || S.size !== "all" || S.un.size || S.checks.size;
  }

  function apply() {
    const C = CFG.categories;
    let matChannels = null, matTypes = null;
    if (S.material.size) {
      matChannels = new Set(); matTypes = new Set();
      C.material.filter((m) => S.material.has(m.id)).forEach((m) => { m.channels.forEach((c) => matChannels.add(c)); (m.also_org_types || []).forEach((t) => matTypes.add(t)); });
    }
    $("materialHint").textContent = matChannels ? "Shows outlets on: " + [...matChannels].map((c) => (C.channel.find((x) => x.id === c) || {}).label || c).join(", ") : "";
    current = ALL.filter((o) => {
      if (S.country ? o.c !== S.country : !inRegion(o.c)) return false;
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
      if (S.checks.has("has_public_contact") && !o.em) return false;
      return true;
    });
    current.forEach((o) => { o._m = (o.un || []).filter((u) => S.un.has(u)); });
    const mode = S.sort === "auto" ? (anyFilter() ? "best_match" : "az") : S.sort;
    const byName = (a, b) => (a.n || "").localeCompare(b.n || "");
    if (mode === "best_match") current.sort((a, b) => b._m.length - a._m.length || b.p - a.p || byName(a, b));
    else if (mode === "country") current.sort((a, b) => (CFG.countryName[a.c] || {}).name.localeCompare((CFG.countryName[b.c] || {}).name) || byName(a, b));
    else current.sort(byName);
    const countries = new Set(current.map((o) => o.c)).size;
    const verified = current.filter((o) => o.s.length >= 2).length;
    $("counter").innerHTML = `<b>${current.length.toLocaleString("en")}</b> ${current.length === 1 ? "outlet" : "outlets"} in <b>${countries}</b> ${countries === 1 ? "country" : "countries"} · ${verified.toLocaleString("en")} verified`;
    draw(true);
  }

  function card(o) {
    const C = CFG.categories, k = CFG.countryName[o.c] || {};
    const chans = (o.ch || []).map((c) => (C.channel.find((x) => x.id === c) || {}).label || c).join(", ");
    const langs = (o.l || []).map((l) => CFG.langName[l] || l).join(", ") || "<span class='pending'>no information</span>";
    const src = o.s.map((s) => CFG.source_labels[s] || s).join(", ");
    const social = Object.entries(o.so || {}).map(([k2, u]) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(k2)}</a>`).join(" · ");
    const verified = o.s.length >= 2 ? '<span class="badge verified">verified</span>' : '<span class="badge unverified">1 source</span>';
    const unl = (o.un || []).map((u) => (C.un_profile.find((x) => x.id === u) || {}).label).join(", ");
    const inList = exportList.has(o.i);
    return `<li class="card"><div class="card-top"><h3>${esc(o.n)}</h3>${verified}</div>
      <p class="meta">Based in: <b>${esc(k.name || o.c)}</b> (${esc(k.subregion || "")}) · Reaches: <span class="pending">step 4</span></p>
      ${o.a ? `<p class="row">Also known as: ${esc(o.a.join(", "))}</p>` : ""}
      ${o.o ? `<p class="row"><b>Type:</b> ${esc((C.org_type.find((x) => x.id === o.o[0]) || {}).label || o.o[0])} <span class="pending">(${esc(CFG.why[o.o[1]])})</span></p>` : ""}
      ${o.ow && o.ow[0] !== "unknown" ? `<p class="row"><b>Ownership:</b> ${esc((C.ownership.find((x) => x.id === o.ow[0]) || {}).label || o.ow[0])} <span class="pending">(${esc(CFG.why[o.ow[1]])})</span></p>` : ""}
      ${o.oa ? `<p class="row"><b>Also listed as:</b> ${esc(o.oa.map((t) => (C.org_type.find((x) => x.id === t) || {}).label || t).join(", "))}</p>` : ""}
      <p class="row"><b>Languages:</b> ${langs}</p>
      <p class="row"><b>Channels:</b> ${esc(chans) || "<span class='pending'>no information</span>"}</p>
      ${unl ? `<p class="row"><b>UN profile:</b> ${esc(unl)}</p>` : ""}
      ${o.w ? `<p class="row"><b>Website:</b> <a href="${esc(o.w)}" target="_blank" rel="noopener">${esc(o.w.replace(/^https?:\/\//, "").replace(/\/$/, ""))}</a></p>` : ""}
      ${social ? `<p class="row"><b>Social media:</b> ${social}</p>` : ""}
      ${o.em ? `<p class="row"><b>Contact:</b> <a href="mailto:${esc(o.em)}">${esc(o.em)}</a></p>` : ""}
      <p class="row pending">Sources: ${esc(src)} · id ${esc(o.i)}</p>
      ${o._m && o._m.length ? `<span class="matches">Matches: ${esc(o._m.map((u) => (C.un_profile.find((x) => x.id === u) || {}).label).join(", "))}</span>` : ""}
      <p><button class="btn-quiet add" data-id="${esc(o.i)}" aria-pressed="${inList}">${inList ? "✓ In export list" : "+ Add to export list"}</button></p></li>`;
  }

  function draw(fromStart) {
    if (fromStart) { shown = 0; $("cards").innerHTML = ""; }
    const slice = current.slice(shown, shown + PAGE);
    $("cards").insertAdjacentHTML("beforeend", slice.map(card).join(""));
    shown += slice.length;
    $("more").hidden = shown >= current.length;
    $("more").textContent = `Show more (${(current.length - shown).toLocaleString("en")} left)`;
  }

  $("cards").addEventListener("click", (e) => {
    const b = e.target.closest("button.add"); if (!b) return;
    const id = b.dataset.id;
    exportList.has(id) ? exportList.delete(id) : exportList.add(id);
    saveList(); updateExportCount();
    b.setAttribute("aria-pressed", exportList.has(id)); b.textContent = exportList.has(id) ? "✓ In export list" : "+ Add to export list";
  });

  function updateExportCount() { $("exportCount").textContent = exportList.size.toLocaleString("en"); }
  function openExport() {
    $("exportInfo").textContent = exportList.size ? `${exportList.size.toLocaleString("en")} outlets in the list.` : "The list is empty. Add outlets with “+ Add to export list”.";
    $("exportDialog").showModal();
  }
  function downloadCsv() {
    const byId = {}; ALL.forEach((o) => { byId[o.i] = o; });
    const C = CFG.categories;
    const head = ["id", "name", "type", "ownership", "country", "region", "languages", "channels", "website", "contact", "social media", "sources", "verified"];
    const rows = [...exportList].map((id) => byId[id]).filter(Boolean).map((o) => {
      const k = CFG.countryName[o.c] || {};
      return [o.i, o.n, o.o ? ((C.org_type.find((x) => x.id === o.o[0]) || {}).label || o.o[0]) : "",
        o.ow ? ((C.ownership.find((x) => x.id === o.ow[0]) || {}).label || o.ow[0]) : "", k.name, k.subregion, (o.l || []).map((l) => CFG.langName[l] || l).join("; "),
        (o.ch || []).map((c) => (C.channel.find((x) => x.id === c) || {}).label || c).join("; "), o.w || "", o.em || "",
        Object.values(o.so || {}).join(" "), o.s.map((s) => CFG.source_labels[s] || s).join("; "), o.s.length >= 2 ? "yes" : "no"];
    });
    const csv = [head].concat(rows).map((r) => r.map((v) => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`).join(",")).join("\r\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }));
    a.download = `partner-finder-export-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click(); URL.revokeObjectURL(a.href);
  }
})();
