/* Disinformation monitor (page desinfo.html). Reads site/data/desinfo/*.json, all rules in config. No tracking. */
(function () {
  "use strict";
  var D = "data/desinfo/";
  var S = { topic: "", un: false, region: "", country: "", from: "", to: "", view: "trends", shown: 50, span: 30, basis: "publisher" };
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
  function load(name, optional) {
    return fetch(D + name).then(function (r) { if (!r.ok) throw new Error(name); return r.json(); })
      .catch(function (e) { if (optional) return null; throw e; });
  }
  function series() { return S.basis === "about" ? DATA.seriesAbout : DATA.series; }
  function covered() { return S.basis === "about" ? DATA.coveredA : DATA.coveredP; }

  // ---------- filters ----------
  function ok(c, un) {
    if (S.un && !un) return false;
    if (S.country) return c === S.country;
    if (S.region) return !!c && DATA.countries[c] && DATA.countries[c].region === S.region;
    return true;
  }
  function okItem(i) {
    if (S.basis !== "about") return ok(i.country, i.un);
    if (!(S.country || S.region)) return ok("", i.un);
    return (i.about || []).some(function (c) { return ok(c, i.un); });
  }
  function inRange(d) { return d >= S.from && d <= S.to; }

  function aggregate() {
    // one pass: per topic range / last7 / base28, per day, per country (current topic)
    var A = { topics: {}, days: {}, countries: {}, rank: {}, total: 0, unTotal: 0 }, to = day(S.to);
    series().forEach(function (r) {
      var d = r[0], q = r[1], c = r[2], un = r[3], n = r[4];
      // the country ranking ignores the region / country filter, so it always shows where to look next
      if (q === S.topic && c && inRange(d) && (!S.un || un)) A.rank[c] = (A.rank[c] || 0) + n;
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
  function setRange(days) { S.span = days; S.to = DATA.last; S.from = iso(day(DATA.last) - days + 1); }
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

  // ---------- UN material and content gaps ----------
  function unOf(q) { return (DATA.un && DATA.un.topics && DATA.un.topics[q]) || { n12: 0, n90: 0, langs: {}, top: [] }; }
  function gapStatus(fc, un) {
    var g = DATA.config.gap;
    if (fc >= g.red_min_factchecks && un <= g.red_max_un) return "red";
    if (fc >= g.yellow_min_factchecks && un <= g.yellow_max_un) return "amber";
    if (fc >= g.yellow_min_factchecks) return "green";
    return "";
  }
  function unLinks(top) {
    var ul = el("ul");
    top.forEach(function (x) {
      ul.appendChild(el("li", {}, [el("a", { href: safeUrl(x.u), target: "_blank", rel: "noopener noreferrer", text: x.t }),
        document.createTextNode(" — " + x.a + ", " + x.d + " (" + x.l + ")")]));
    });
    return ul;
  }
  function renderUnBox(A) {
    var box = $("unBox"); box.textContent = "";
    if (!S.topic || !DATA.un) { box.hidden = true; return; }
    box.hidden = false;
    var u = unOf(S.topic), fc = (A.topics[S.topic] || { range: 0 }).range, st = gapStatus(fc, u.n12);
    box.appendChild(el("h3", { text: "UN material on “" + topicName(S.topic) + "”" }));
    var langs = Object.keys(u.langs).map(function (l) { return l + " " + u.langs[l]; }).join(", ");
    box.appendChild(el("p", { text: u.n12 + " UN article" + (u.n12 === 1 ? "" : "s") + " in the last 12 months (" + u.n90 + " in the last 90 days)" +
      (langs ? "; languages: " + langs : "") + "." }));
    if (u.top.length) box.appendChild(unLinks(u.top));
    else box.appendChild(el("p", { class: "hint", text: "No UN article found on this topic in the sources we read. " +
      (st === "red" ? "With the fact-checks of this window this is a content gap (see the tab “Content gaps”)." : "") }));
  }
  function langCounts(topic) {
    var out = {};
    DATA.items.forEach(function (i) {
      if (!inRange(i.date) || i.topics.indexOf(topic) < 0 || !okItem(i)) return;
      out[i.lang] = (out[i.lang] || 0) + 1;
    });
    return out;
  }
  function renderGaps(A) {
    var rows = [], box = $("gapList"); box.textContent = "";
    if (DATA.un) box.appendChild(el("p", { class: "hint", text: "Based on " + DATA.un.articles + " UN articles from " + DATA.un.sources_ok + " of " + DATA.un.sources +
      " sources (last 12 months). If a source did not answer, its articles are missing and a gap may be overstated: see reports/desinfo_sources.md." }));
    if (!DATA.un) { box.appendChild(el("p", { class: "hint", text: "The UN content has not been collected yet. It appears after the next daily update." })); return; }
    DATA.topics.forEach(function (t) {
      var fc = (A.topics[t.qid] || { range: 0 }).range, u = unOf(t.qid), st = gapStatus(fc, u.n12);
      if (st) rows.push({ t: t, fc: fc, u: u, st: st });
    });
    var rank = { red: 0, amber: 1, green: 2 };
    rows.sort(function (a, b) { return rank[a.st] - rank[b.st] || b.fc - a.fc; });
    if (!rows.length) { box.appendChild(el("p", { class: "hint", text: "No topic reaches the minimum number of fact-checks in this window and filter. Try a longer window." })); return; }
    rows.forEach(function (r) {
      var label = { red: "Gap", amber: "Thin", green: "Covered" }[r.st];
      var name = el("button", { class: "name", type: "button", text: r.t.label });
      name.onclick = function () { S.topic = r.t.qid; S.view = "trends"; S.shown = 50; render(); };
      var head = el("div", { class: "gap-head" }, [name, el("span", { text: r.fc + " fact-checks" }),
        el("span", { text: r.u.n12 + " UN articles" }), el("span", { class: "badge " + r.st, text: label }), el("span", { class: "langs" })]);
      // languages of the fact-checks versus UN material in that language
      var lc = langCounts(r.t.qid), langBox = head.lastChild, uncovered = [];
      Object.keys(lc).filter(function (l) { return lc[l] >= 2; }).sort(function (a, b) { return lc[b] - lc[a]; }).slice(0, 4).forEach(function (l) {
        var un = r.u.langs[l] || 0, known = DATA.un.languages.indexOf(l) >= 0;
        if (!un) uncovered.push(l);
        langBox.appendChild(el("span", { class: "badge" + (un ? "" : " amber"), title: known ? "UN articles in this language" : "no UN feed in this language",
          text: l + " " + lc[l] + " · UN " + (known ? un : "n/a") }));
      });
      var sug = (DATA.config.suggestions.groups || {})[r.t.group] || DATA.config.suggestions.default;
      var det = el("details", {}, [el("summary", { text: "What we could do" })]);
      if (r.st !== "green") {
        var ul = el("ul");
        ul.appendChild(el("li", { text: "Responsible UN bodies: " + sug.agencies.join(", ") }));
        ul.appendChild(el("li", { text: "Formats that usually work: " + sug.formats.join("; ") }));
        if (uncovered.length) ul.appendChild(el("li", { text: "Languages of the fact-checks with no UN article yet: " + uncovered.join(", ") }));
        ul.appendChild(el("li", { text: "Start from the fact-checks below (tab “Worldwide trends”, click the topic): they name the claim and the evidence." }));
        det.appendChild(ul);
      }
      if (r.u.top.length) { det.appendChild(el("p", { class: "hint", text: "Existing UN material to reuse:" })); det.appendChild(unLinks(r.u.top)); }
      box.appendChild(el("div", { class: "gap-row" }, [head, det]));
    });
  }

  // ---------- map ----------
  var COLORS = ["#E6F4FB", "#B3DDF2", "#66BDE6", "#2E9CD4", "#0072BC", "#003D6B"];
  function color(n, cov) {
    if (!cov) return "#C9CED3";                         // no data (grey)
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
  function trendText(c) {
    var t = DATA.trends && DATA.trends[c];
    return t ? t.queries.slice(0, 3).map(function (x) { return x.q; }).join(", ") : "";
  }
  function renderMap(A) {
    var cov = covered();
    ensureMap().then(function () {
      if (!layer) return;
      layer.eachLayer(function (l) {
        var c = l.__iso, n = A.countries[c] || 0, has = !!cov[c];
        l.setStyle({ fillColor: color(n, has) });
        var name = (DATA.countries[c] && DATA.countries[c].name) || (l.feature.properties.name || c);
        l.unbindTooltip().bindTooltip(name + ": " + (has ? n + " fact-check" + (n === 1 ? "" : "s") : "no data"), { sticky: true });
      });
    });
    // panel for the chosen country: search trends are a substitute signal, clearly marked
    var p = $("countryPanel"); p.textContent = "";
    if (!S.country) { p.hidden = true; return; }
    p.hidden = false;
    var nm = DATA.countries[S.country].name, n = A.countries[S.country] || 0, tt = DATA.trends && DATA.trends[S.country];
    p.appendChild(el("b", { text: nm + ": " + (cov[S.country] ? n + " fact-check" + (n === 1 ? "" : "s") + " in this window" : "no fact-checks in the data yet") }));
    if (!cov[S.country]) p.appendChild(el("p", { class: "hint", text: "No fact-checker of this country is covered yet. The list in reports/desinfo_coverage.md shows which countries are next." }));
    if (tt) p.appendChild(el("p", { text: "Searched for in " + nm + " right now (Google Trends, not a fact-check): " + tt.queries.map(function (x) { return x.q + " (" + x.t + ")"; }).join(", ") + ". Data source: Google Trends." }));
    var clear = el("button", { class: "btn-quiet", type: "button", text: "Show all countries" });
    clear.onclick = function () { S.country = ""; render(); };
    p.appendChild(clear);
  }

  // ---------- local voices already in the Partner Finder ----------
  var GROUPS = [
    { k: "fc", title: "Fact-checkers", link: "./#c={iso3}&ot=fact_checker" },
    { k: "cm", title: "Community media (e.g. community radio)", link: "./#c={iso3}&ot=community_media" },
    { k: "nw", title: "Well-known news outlets", link: "./#c={iso3}&ot=news_outlet,news_agency,public_service_broadcaster" },
    { k: "ngo", title: "Organisations & NGOs", link: "ngos.html#c={iso3}" },
    { k: "iv", title: "UNDP iVerify (UN fact-checking platform)", link: null, onlyIfPresent: true }
  ];
  function renderPartners() {
    var box = $("partnersBox"); box.textContent = "";
    var p = DATA.partners && S.country && DATA.partners[S.country];
    if (!p) { box.hidden = true; return; }
    box.hidden = false;
    box.appendChild(el("h3", { text: "Local voices in " + DATA.countries[S.country].name + " (already in the Partner Finder)" }));
    box.appendChild(el("p", { class: "hint", text: "Credible organisations that could carry verified information. Taken from the Partner Finder data; only organisations, no persons. A group with no entry means none is in the Partner Finder yet." }));
    var grid = el("div", { class: "p-grid" });
    GROUPS.forEach(function (g) {
      var d = p[g.k];
      if (!d && g.onlyIfPresent) return;
      var col = el("div", { class: "p-col" }, [el("h4", { text: g.title + " (" + d.n + ")" })]);
      if (!d.n) col.appendChild(el("p", { class: "hint", text: "None in the Partner Finder yet." }));
      else {
        var ul = el("ul");
        d.top.forEach(function (x) {
          var li = el("li");
          li.appendChild(x.w ? el("a", { href: safeUrl(x.w), target: "_blank", rel: "noopener noreferrer", text: x.n }) : document.createTextNode(x.n));
          if (x.l && x.l.length) li.appendChild(document.createTextNode(" (" + x.l.join(", ") + ")"));
          ul.appendChild(li);
        });
        col.appendChild(ul);
        if (!g.link) { grid.appendChild(col); return; }
        var m = S.topic && DATA.ptopics[S.topic];      // the chosen topic goes along as a Partner Finder topic (and sub-topic)
        var tail = "";
        if (m) {
          tail = "&tp=" + m[0];
          if (m[1]) {                                  // only this sub-topic: the others of the topic are switched off
            var off = (DATA.psubs[m[0]] || []).filter(function (x) { return x !== m[1]; });
            if (off.length) tail += "&off=" + m[0] + ":" + off.join("|");
          }
        }
        col.appendChild(el("a", { class: "more", href: g.link.replace("{iso3}", p.iso3) + tail,
          text: "Open all " + d.n + " in the Partner Finder" + (m ? " (topic: " + topicName(S.topic) + ")" : "") + " →" }));
      }
      grid.appendChild(col);
    });
    box.appendChild(grid);
  }
  function renderCountryRank(A) {
    var box = $("countryRank"); box.textContent = "";
    var rows = Object.keys(A.rank).sort(function (a, b) { return A.rank[b] - A.rank[a]; }).slice(0, 14);
    if (!rows.length) { box.appendChild(el("span", { class: "hint", text: "No country with fact-checks in this window." })); return; }
    rows.forEach(function (c) {
      if (!DATA.countries[c]) return;
      var b = el("button", { class: "chip", type: "button", "aria-pressed": String(S.country === c), text: DATA.countries[c].name + " · " + A.rank[c] });
      b.onclick = function () { S.country = c; S.region = ""; S.shown = 50; render(); };
      box.appendChild(b);
    });
  }

  // ---------- items ----------
  function matches(i) {
    if (!inRange(i.date)) return false;
    if (S.topic && i.topics.indexOf(S.topic) < 0) return false;
    return okItem(i);
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
      if (i.net === "iverify") tags.appendChild(el("span", { class: "badge", title: "Published on a UNDP iVerify country site", text: "iVerify (UNDP)" }));
      if (i.un) tags.appendChild(el("span", { class: "badge", text: "UN-related" }));
      (i.about || []).slice(0, 3).forEach(function (c) { if (DATA.countries[c]) tags.appendChild(el("span", { class: "badge", text: "about: " + DATA.countries[c].name })); });
      i.topics.slice(0, 5).forEach(function (q) { tags.appendChild(el("span", { class: "badge", text: topicName(q) })); });
      var kids = [el("div", { class: "meta", text: meta }),
        el("a", { href: safeUrl(i.url), target: "_blank", rel: "noopener noreferrer", text: i.title })];
      if (i.title_en && i.title_en.toLowerCase() !== i.title.toLowerCase())
        kids.push(el("div", { class: "tr", text: "English (automatic translation): " + i.title_en }));
      kids.push(tags);
      box.appendChild(el("div", { class: "item" }, kids));
    });
    $("moreBtn").hidden = list.length <= S.shown;
  }

  // ---------- export (PDF, Word, Excel) ----------
  function buildReport(format) {
    var A = aggregate(), latin = /^[\u0000-\u024F\u2000-\u206F\u20A0-\u20CF]*$/;
    var scope = [S.topic ? "Topic: " + topicName(S.topic) : "All topics"];
    if (S.country) scope.push("Country: " + DATA.countries[S.country].name); else if (S.region) scope.push("Region: " + S.region);
    scope.push(S.basis === "about" ? "Country = the country the fact-check is about" : "Country = where the fact-checker works");
    if (S.un) scope.push("UN-related only");
    var info = [["Exported", new Date().toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })],
      ["Data as of", DATA.last], ["Window", S.from + " to " + S.to], ["Filters", scope.join(" · ")],
      ["Totals", A.total + " fact-checks in this window, " + A.unTotal + " UN-related, " + Object.keys(A.countries).length + (Object.keys(A.countries).length === 1 ? " country" : " countries")]];
    var tables = [];
    // 1. topics
    var trows = DATA.topics.map(function (t) { return { t: t, x: A.topics[t.qid] }; }).filter(function (r) { return r.x && r.x.range > 0; })
      .sort(function (a, b) { return b.x.range - a.x.range; }).slice(0, 60).map(function (r) {
        var rs = rising(r.x);
        return [r.t.label, r.t.group, String(r.x.range), String(r.x.last7), rs ? (rs.red ? "Rising" : (rs.ratio ? "x" + rs.ratio.toFixed(1) : "new")) : "not enough history"];
      });
    tables.push({ title: "Topics", note: "Fact-checks per topic in the window. “Rising” = more than twice the usual weekly number.",
      cols: [["Topic", 30], ["Group", 16], ["Fact-checks", 12], ["Last 7 days", 12], ["Trend", 14]], rows: trows });
    // 2. countries
    var crows = Object.keys(A.rank).sort(function (a, b) { return A.rank[b] - A.rank[a]; }).slice(0, 30).filter(function (c) { return DATA.countries[c]; })
      .map(function (c) { return [DATA.countries[c].name, DATA.countries[c].region, String(A.rank[c])]; });
    tables.push({ title: "Countries with the most fact-checks", note: "Countries without any fact-checker covered yet are not listed: grey on the map means “no data”, not “no disinformation”.",
      cols: [["Country", 30], ["Region", 20], ["Fact-checks", 12]], rows: crows });
    // 3. content gaps
    var grows = [];
    if (DATA.un) {
      var rank = { red: 0, amber: 1, green: 2 }, list = [];
      DATA.topics.forEach(function (t) {
        var fc = (A.topics[t.qid] || { range: 0 }).range, u = unOf(t.qid), st = gapStatus(fc, u.n12);
        if (st) list.push({ t: t, fc: fc, u: u, st: st });
      });
      list.sort(function (a, b) { return rank[a.st] - rank[b.st] || b.fc - a.fc; });
      list.slice(0, 60).forEach(function (r) {
        var lc = langCounts(r.t.qid), langs = Object.keys(lc).filter(function (l) { return lc[l] >= 2; }).sort(function (a, b) { return lc[b] - lc[a]; }).slice(0, 4)
          .map(function (l) { return l + " " + lc[l] + " (UN " + (DATA.un.languages.indexOf(l) >= 0 ? (r.u.langs[l] || 0) : "n/a") + ")"; }).join(", ");
        var sug = (DATA.config.suggestions.groups || {})[r.t.group] || DATA.config.suggestions.default, top = r.u.top[0];
        grows.push([r.t.label, String(r.fc), String(r.u.n12), { red: "Gap", amber: "Thin", green: "Covered" }[r.st], langs,
          r.st === "green" ? "" : sug.agencies.join(", "), r.st === "green" ? "" : sug.formats.join("; "),
          top ? { t: top.t + " (" + top.a + ", " + top.d + ")", url: top.u } : ""]);
      });
    }
    tables.push({ title: "Content gaps: do we already have something?", note: DATA.un ? "Fact-checks in the window compared with UN articles of the last 12 months (" + DATA.un.articles + " articles from " + DATA.un.sources_ok + " of " + DATA.un.sources + " sources). Rough estimate from key words: please check before publishing." : "",
      cols: [["Topic", 20], ["Fact-checks", 9], ["UN articles (12 mo)", 10], ["Status", 8], ["Languages (UN articles in it)", 22], ["Responsible UN bodies", 20], ["Formats that usually work", 28], ["UN material to reuse", 30]], rows: grows });
    // 4. fact-checks
    var items = DATA.items.filter(matches).slice(0, 300);
    var irows = items.map(function (i) {
      var title = i.title, en = i.title_en && i.title_en.toLowerCase() !== i.title.toLowerCase() ? i.title_en : "";
      if (format === "pdf" && !latin.test(title)) { title = en || "(title in another script: see the link)"; en = ""; }   // the PDF font has no Arabic, Hindi or Chinese letters
      return [i.date, i.publisher + (i.net === "iverify" ? " (iVerify, UNDP)" : ""), i.country && DATA.countries[i.country] ? DATA.countries[i.country].name : "",
        { t: title, url: i.url }, en, i.rating || "", i.topics.slice(0, 4).map(topicName).join(", ")];
    });
    tables.push({ title: "Fact-checks (" + Math.min(items.length, 300) + " newest of " + DATA.items.filter(matches).length + ")",
      note: "Headline of the fact-check by independent fact-checkers; the claims themselves are not reproduced. English = automatic machine translation of the title.",
      cols: [["Date", 9], ["Fact-checker", 16], ["Country", 13], ["Title (link)", 40], ["English (automatic)", 34], ["Rating", 10], ["Topics", 18]], rows: irows });
    // 5. local voices
    var vrows = [], pv = DATA.partners && S.country && DATA.partners[S.country];
    if (pv) GROUPS.forEach(function (g) { (pv[g.k] ? pv[g.k].top : []).forEach(function (x) { vrows.push([g.title, { t: x.n, url: x.w }, (x.l || []).join(", ")]); }); });
    tables.push({ title: "Local voices in " + (S.country ? DATA.countries[S.country].name : "") + " (already in the Partner Finder)",
      note: "Organisations only. The full lists are in the Partner Finder.", cols: [["Group", 22], ["Name (link)", 50], ["Languages", 14]], rows: vrows });
    return { title: "Disinformation monitor", info: info, tables: tables,
      note: "Automatic evaluation of fact-checks published by independent fact-checkers; please check the original before using it. Topics and countries are assigned by rules, not by hand. Sources: Google Fact Check Tools, fact-checker feeds, UN News and UN agency feeds, Wikipedia-based topic list of the Audience Intelligence Atlas, Google Trends (Data source: Google Trends)." };
  }
  function setupExport() {
    var row = $("exportRow");
    row.querySelectorAll("button").forEach(function (b) {
      b.onclick = function () {
        if (!window.DesinfoExport) return;
        var msg = $("exportMsg"), old = msg.textContent;
        row.querySelectorAll("button").forEach(function (x) { x.disabled = true; });
        msg.textContent = "Preparing the file…";
        window.DesinfoExport.download(b.dataset.fmt, buildReport(b.dataset.fmt)).then(function () { msg.textContent = old; })
          .catch(function (e) { msg.textContent = "The export did not work: " + e.message; })
          .then(function () { row.querySelectorAll("button").forEach(function (x) { x.disabled = false; }); });
      };
    });
  }

  // ---------- render ----------
  function render() {
    if (DATA.syncSelects) DATA.syncSelects();
    var A = aggregate();
    renderRange(A); renderTopics(A);
    var base = Object.keys((A.topics[""] || { baseDays: {} }).baseDays).length;
    $("notice").hidden = base >= 14;
    $("notice").textContent = "The red marker needs at least two weeks of collected data before the selected week; it appears automatically once the daily archive is long enough.";
    $("stats").textContent = "";
    [[A.total, "fact-checks in this window"], [A.unTotal, "UN-related"], [Object.keys(A.countries).length, "countries with fact-checks"]].forEach(function (s) {
      $("stats").appendChild(el("div", { class: "stat" }, [el("b", { text: String(s[0]) }), el("span", { text: s[1] })]));
    });
    ["trends", "map", "gaps"].forEach(function (v) {
      $("view-" + v).hidden = S.view !== v;
      $("tab-" + v).setAttribute("aria-selected", String(S.view === v));
    });
    if (S.view === "trends") { renderTrends(A); renderCountryRank(A); }
    else if (S.view === "gaps") renderGaps(A);
    else { renderLegend(); renderMap(A); if (map) setTimeout(function () { map.invalidateSize(); }, 50); }
    renderUnBox(A);
    renderPartners();
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
    DATA.syncSelects = function () { $("f-region").value = S.region; countries(); };
    $("f-region").onchange = function () { S.region = this.value; S.country = ""; countries(); S.shown = 50; render(); };
    $("f-country").onchange = function () { S.country = this.value; S.shown = 50; render(); };
    $("f-region").value = S.region;
  }

  Promise.all([load("items.json"), load("series.json"), load("topics.json"), load("countries.json"), load("config.json"),
               load("summary.json"), load("series_about.json", true), load("un_content.json", true), load("trends.json", true), load("partners.json", true), load("partner_topics.json", true)]).then(function (r) {
    DATA.items = r[0]; DATA.series = r[1]; DATA.topics = r[2].topics; DATA.countries = r[3]; DATA.config = r[4];
    DATA.seriesAbout = r[6] || r[1]; DATA.un = r[7]; DATA.trends = r[8]; DATA.partners = r[9]; DATA.ptopics = (r[10] && r[10].topics) || {}; DATA.psubs = (r[10] && r[10].subs) || {};
    DATA.topicById = {}; DATA.topics.forEach(function (t) { DATA.topicById[t.qid] = t; });
    DATA.coveredP = {}; DATA.coveredA = {}; var f = "9999", l = "0000";
    DATA.series.forEach(function (x) { if (x[2]) DATA.coveredP[x[2]] = 1; if (x[0] < f) f = x[0]; if (x[0] > l) l = x[0]; });
    DATA.seriesAbout.forEach(function (x) { if (x[2]) DATA.coveredA[x[2]] = 1; });
    DATA.first = f; DATA.last = r[5].last_date || l;
    setRange(30); fillSelects();
    $("f-un").onchange = function () { S.un = this.checked; S.shown = 50; render(); };
    $("basis-pub").onchange = $("basis-about").onchange = function () { S.basis = $("basis-about").checked ? "about" : "publisher"; S.shown = 50; render(); };
    $("f-topicSearch").oninput = function () { render(); };
    $("dateApply").onclick = function () {
      var a = $("dateFrom").value, b = $("dateTo").value;
      if (a && b && a <= b) { S.from = a; S.to = b; S.span = 0; S.shown = 50; render(); }
    };
    $("tab-trends").onclick = function () { S.view = "trends"; render(); };
    $("tab-map").onclick = function () { S.view = "map"; render(); };
    $("tab-gaps").onclick = function () { S.view = "gaps"; render(); };
    $("moreBtn").onclick = function () { S.shown += 50; renderItems(); };
    setupExport();
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
