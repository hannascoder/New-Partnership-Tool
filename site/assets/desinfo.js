/* Disinformation monitor (page desinfo.html). Reads site/data/desinfo/*.json, all rules in config. No tracking. */
(function () {
  "use strict";
  var D = "data/desinfo/";
  var S = { topic: "", un: false, region: "", country: "", from: "", to: "", view: "trends", shown: 50, span: 30 };
  var DATA = {}, map = null, layer = null;

  function $(id) { return document.getElementById(id); }
  function el(tag, attrs, kids) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "text") e.textContent = attrs[k]; else if (k === "class") e.className = attrs[k]; else e.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (c) { e.appendChild(c); });
    return e;
  }
  function safeUrl(u) { return /^https?:\/\//i.test(u || "") ? u : "#"; }
  function day(s) { return new Date(s + "T00:00:00Z").getTime() / 864e5; }
  function iso(n) { return new Date(n * 864e5).toISOString().slice(0, 10); }
  function load(name) { return fetch(D + name).then(function (r) { if (!r.ok) throw new Error(name); return r.json(); }); }

  // ---------- filters on rows [date, topic, iso2, un, n] ----------
  function ok(c, un) {
    if (S.un && !un) return false;
    if (S.country) return c === S.country;
    if (S.region) return !!c && DATA.countries[c] && DATA.countries[c].region === S.region;
    return true;
  }
  function inRange(d) { return d >= S.from && d <= S.to; }

  function aggregate() {
    // one pass: per topic range / last7 / base28, per day (all topics), per country (current topic)
    var A = { topics: {}, days: {}, countries: {}, total: 0, unTotal: 0 }, to = day(S.to);
    DATA.series.forEach(function (r) {
      var d = r[0], q = r[1], c = r[2], un = r[3], n = r[4];
      if (!ok(c, un)) return;
      var dd = day(d), t;
      if (!A.topics[q]) A.topics[q] = { range: 0, last7: 0, base: 0, baseDays: {} };
      t = A.topics[q];
      if (inRange(d)) t.range += n;
      if (dd > to - 7 && dd <= to) t.last7 += n;
      else if (dd > to - 35 && dd <= to - 7) { t.base += n; t.baseDays[d] = 1; }
      if (q === S.topic) {
        A.days[d] = (A.days[d] || 0) + n;
        if (inRange(d) && c) A.countries[c] = (A.countries[c] || 0) + n;
        if (inRange(d)) { A.total += n; if (un) A.unTotal += n; }
      }
    });
    return A;
  }

  // ---------- timeline ----------
  function setRange(days) {
    S.span = days; S.to = DATA.last; S.from = iso(day(DATA.last) - days + 1);
  }
  function renderRange(A) {
    var box = $("rangeButtons"); box.textContent = "";
    [["Latest day", 1], ["7 days", 7], ["30 days", 30], ["12 months", 365]].forEach(function (b) {
      var btn = el("button", { class: "chip", type: "button", "aria-pressed": String(S.span === b[1] && S.to === DATA.last), text: b[0] });
      btn.onclick = function () { setRange(b[1]); render(); };
      box.appendChild(btn);
    });
    $("dateFrom").value = S.from; $("dateTo").value = S.to;
    $("dateFrom").min = $("dateTo").min = DATA.first; $("dateFrom").max = $("dateTo").max = DATA.last;
    $("rangeInfo").textContent = "Data from " + DATA.first + " to " + DATA.last + ". The page updates daily.";
    var N = 120, end = day(DATA.last), max = 1, i, v;
    for (i = 0; i < N; i++) { v = A.days[iso(end - i)] || 0; if (v > max) max = v; }
    var w = 1000 / N, svg = '<svg viewBox="0 0 1000 64" preserveAspectRatio="none">';
    for (i = N - 1; i >= 0; i--) {
      var d = iso(end - i); v = A.days[d] || 0;
      var h = Math.max(v ? 2 : 0, 60 * v / max), x = (N - 1 - i) * w;
      svg += '<rect class="bar' + (inRange(d) ? ' in' : '') + '" x="' + x.toFixed(1) + '" y="' + (62 - h).toFixed(1) +
             '" width="' + (w - 1).toFixed(1) + '" height="' + h.toFixed(1) + '"><title>' + d + ': ' + v + '</title></rect>';
    }
    $("spark").innerHTML = svg + "</svg>";
  }

  // ---------- topics ----------
  function topicName(q) { var t = DATA.topicById[q]; return t ? t.label : q; }
  function rising(t) {
    var cfg = DATA.config.red_marker;
    if (!t || Object.keys(t.baseDays).length < 14) return null;        // not enough history yet
    var weekly = t.base / 4;
    return { red: t.last7 >= cfg.min_items && t.last7 > cfg.factor * weekly, ratio: weekly ? t.last7 / weekly : null };
  }
  function renderTopics(A) {
    var box = $("topicList"); box.textContent = "";
    var q = $("f-topicSearch").value.trim().toLowerCase();
    function btn(id, label, n, red) {
      var b = el("button", { class: "topic-btn" + (n ? "" : " zero"), type: "button", "aria-pressed": String(S.topic === id) },
                 [el("span", { text: label + (red ? " ▲" : "") }), el("span", { class: "n", text: String(n) })]);
      if (red) b.firstChild.classList.add("rise");
      b.onclick = function () { S.topic = id; S.shown = 50; render(); };
      return b;
    }
    box.appendChild(btn("", "All topics", (A.topics[""] || { range: 0 }).range, false));
    var groups = {};
    DATA.topics.forEach(function (t) {
      if (q && t.label.toLowerCase().indexOf(q) < 0) return;
      (groups[t.group] = groups[t.group] || []).push(t);
    });
    Object.keys(groups).sort().forEach(function (g) {
      var det = el("details", {}, [el("summary", { text: g })]);
      if (q || groups[g].some(function (t) { return t.qid === S.topic; })) det.open = true;
      groups[g].sort(function (a, b) {
        return ((A.topics[b.qid] || { range: 0 }).range - (A.topics[a.qid] || { range: 0 }).range) || a.label.localeCompare(b.label);
      }).forEach(function (t) {
        var x = A.topics[t.qid], r = rising(x);
        det.appendChild(btn(t.qid, t.label, x ? x.range : 0, r && r.red));
      });
      box.appendChild(det);
    });
  }
  function renderTrends(A) {
    var rows = DATA.topics.map(function (t) { return { t: t, x: A.topics[t.qid] || { range: 0, last7: 0, base: 0, baseDays: {} } }; })
      .filter(function (r) { return r.x.range > 0; })
      .sort(function (a, b) { return b.x.range - a.x.range; });
    var box = $("trendList"); box.textContent = "";
    if (!rows.length) { box.appendChild(el("p", { class: "hint", text: "No fact-checks matched a topic in this window and filter." })); return; }
    var max = rows[0].x.range;
    rows.slice(0, 60).forEach(function (r) {
      var rs = rising(r.x), badge = el("span", { class: "badge" + (rs && rs.red ? " red" : ""),
        text: rs ? (rs.red ? "Rising" : (rs.ratio ? "×" + rs.ratio.toFixed(1) : "new")) : "—" });
      var row = el("button", { class: "trend-row", type: "button" }, [
        el("span", { text: r.t.label + " · " + r.t.group }),
        el("span", { class: "trend-bar" }, [el("i", { style: "width:" + (100 * r.x.range / max).toFixed(1) + "%" })]),
        el("b", { text: String(r.x.range) }), el("span", { class: "rise-col" }, [badge])]);
      row.onclick = function () { S.topic = r.t.qid; S.shown = 50; render(); };
      box.appendChild(row);
    });
  }

  // ---------- map ----------
  var COLORS = ["#E6F4FB", "#B3DDF2", "#66BDE6", "#2E9CD4", "#0072BC", "#003D6B"];
  function color(n, covered) {
    if (!covered) return "#C9CED3";                         // no data (grey)
    if (!n) return COLORS[0];
    return COLORS[Math.min(5, 1 + Math.floor(Math.log2(n)))];
  }
  function renderLegend() {
    var l = $("legend"); l.textContent = "";
    l.appendChild(el("span", {}, [el("i", { style: "background:#C9CED3" }), document.createTextNode("No data")]));
    [["0", 0], ["1", 1], ["2–3", 2], ["4–7", 4], ["8–15", 8], ["16+", 16]].forEach(function (b, i) {
      l.appendChild(el("span", {}, [el("i", { style: "background:" + COLORS[i] }), document.createTextNode(b[0])]));
    });
  }
  function ensureMap() {
    if (map || !window.L) return Promise.resolve();
    map = L.map("map", { center: [20, 10], zoom: 2, minZoom: 1, maxZoom: 6, attributionControl: true });
    map.attributionControl.addAttribution("Boundaries: Natural Earth, generalized; not an official endorsement by the United Nations");
    return fetch("data/boundaries/countries.geojson").then(function (r) { return r.json(); }).then(function (g) {
      layer = L.geoJSON(g, { style: function () { return { weight: .6, color: "#fff", fillOpacity: 1, fillColor: "#C9CED3" }; },
        onEachFeature: function (f, l) {
          var c = f.properties["ISO3166-1-Alpha-2"]; l.__iso = c;
          l.on("click", function () { if (DATA.countries[c]) { S.country = c; S.region = ""; S.shown = 50; render(); } });
        } }).addTo(map);
    });
  }
  function renderMap(A) {
    ensureMap().then(function () {
      if (!layer) return;
      layer.eachLayer(function (l) {
        var c = l.__iso, n = A.countries[c] || 0, covered = !!DATA.covered[c];
        l.setStyle({ fillColor: color(n, covered) });
        var name = (DATA.countries[c] && DATA.countries[c].name) || (l.feature.properties.name || c);
        l.unbindTooltip().bindTooltip(name + ": " + (covered ? n + " fact-check" + (n === 1 ? "" : "s") : "no data"), { sticky: true });
      });
    });
  }

  // ---------- items ----------
  function matches(i) {
    if (!inRange(i.date)) return false;
    if (S.topic && i.topics.indexOf(S.topic) < 0) return false;
    return ok(i.country, i.un);
  }
  function renderItems() {
    var list = DATA.items.filter(matches), box = $("items"); box.textContent = "";
    var scope = (S.topic ? topicName(S.topic) : "All topics") + (S.country ? " · " + DATA.countries[S.country].name : S.region ? " · " + S.region : "");
    $("itemsTitle").textContent = "Fact-checks (" + list.length + ") — " + scope;
    if (!list.length) box.appendChild(el("p", { class: "hint", text: "No fact-checks in this window and filter. Try a longer window." }));
    list.slice(0, S.shown).forEach(function (i) {
      var meta = i.date + " · " + i.publisher + (i.country && DATA.countries[i.country] ? " · " + DATA.countries[i.country].name : "") +
                 (i.rating ? " · rated: " + i.rating : "") + " · " + i.lang;
      var tags = el("div", { class: "tags" });
      if (i.un) tags.appendChild(el("span", { class: "badge", text: "UN-related" }));
      i.topics.slice(0, 5).forEach(function (q) { tags.appendChild(el("span", { class: "badge", text: topicName(q) })); });
      box.appendChild(el("div", { class: "item" }, [el("div", { class: "meta", text: meta }),
        el("a", { href: safeUrl(i.url), target: "_blank", rel: "noopener noreferrer", text: i.title }), tags]));
    });
    $("moreBtn").hidden = list.length <= S.shown;
  }

  // ---------- render ----------
  function render() {
    var A = aggregate();
    renderRange(A); renderTopics(A);
    var cfgNote = $("notice");
    var base = Object.keys((A.topics[""] || { baseDays: {} }).baseDays).length;
    cfgNote.hidden = base >= 14;
    cfgNote.textContent = "The red marker needs at least two weeks of collected data before the selected week; it will appear automatically once the daily archive is long enough.";
    $("stats").textContent = "";
    [[A.total, "fact-checks in this window"], [A.unTotal, "UN-related"], [Object.keys(A.countries).length, "countries with fact-checks"]].forEach(function (s) {
      $("stats").appendChild(el("div", { class: "stat" }, [el("b", { text: String(s[0]) }), el("span", { text: s[1] })]));
    });
    $("view-trends").hidden = S.view !== "trends"; $("view-map").hidden = S.view !== "map";
    $("tab-trends").setAttribute("aria-selected", String(S.view === "trends")); $("tab-map").setAttribute("aria-selected", String(S.view === "map"));
    if (S.view === "trends") renderTrends(A); else { renderLegend(); renderMap(A); if (map) setTimeout(function () { map.invalidateSize(); }, 50); }
    renderItems();
  }

  function fillSelects() {
    var regions = {}, cs = DATA.countries;
    Object.keys(cs).forEach(function (c) { regions[cs[c].region] = 1; });
    Object.keys(regions).sort().forEach(function (r) { $("f-region").appendChild(el("option", { value: r, text: r })); });
    function countries() {
      var sel = $("f-country"); sel.textContent = ""; sel.appendChild(el("option", { value: "", text: "All countries" }));
      Object.keys(cs).filter(function (c) { return !S.region || cs[c].region === S.region; })
        .sort(function (a, b) { return cs[a].name.localeCompare(cs[b].name); })
        .forEach(function (c) { sel.appendChild(el("option", { value: c, text: cs[c].name })); });
      sel.value = S.country;
    }
    countries();
    $("f-region").onchange = function () { S.region = this.value; S.country = ""; countries(); S.shown = 50; render(); };
    $("f-country").onchange = function () { S.country = this.value; S.shown = 50; render(); };
    $("f-region").value = S.region;
  }

  Promise.all(["items.json", "series.json", "topics.json", "countries.json", "config.json", "summary.json"].map(load)).then(function (r) {
    DATA.items = r[0]; DATA.series = r[1]; DATA.topics = r[2].topics; DATA.countries = r[3]; DATA.config = r[4];
    DATA.topicById = {}; DATA.topics.forEach(function (t) { DATA.topicById[t.qid] = t; });
    DATA.covered = {}; var f = "9999", l = "0000";
    DATA.series.forEach(function (x) { if (x[2]) DATA.covered[x[2]] = 1; if (x[0] < f) f = x[0]; if (x[0] > l) l = x[0]; });
    DATA.first = f; DATA.last = r[5].last_date || l;
    setRange(30); fillSelects();
    $("f-un").onchange = function () { S.un = this.checked; S.shown = 50; render(); };
    $("f-topicSearch").oninput = function () { render(); };
    $("dateApply").onclick = function () {
      var a = $("dateFrom").value, b = $("dateTo").value;
      if (a && b && a <= b) { S.from = a; S.to = b; S.span = 0; S.shown = 50; render(); }
    };
    $("tab-trends").onclick = function () { S.view = "trends"; render(); };
    $("tab-map").onclick = function () { S.view = "map"; render(); };
    $("moreBtn").onclick = function () { S.shown += 50; renderItems(); };
    $("filtersToggle").onclick = function () { var o = $("filters").classList.toggle("open"); this.setAttribute("aria-expanded", String(o)); };
    $("spark").onclick = function (e) {
      var rc = this.getBoundingClientRect(), i = Math.floor((e.clientX - rc.left) / rc.width * 120);
      S.to = S.from = iso(day(DATA.last) - (119 - i)); S.span = 0; render();
    };
    render();
  }).catch(function (e) {
    $("notice").hidden = false;
    $("notice").textContent = "The data could not be loaded (" + e.message + "). The daily update creates these files; try again later.";
  });
})();
