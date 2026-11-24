/* "Get feedback" page (plan: docs/FEEDBACK_PLAN.md, step F1).
   Contacts: GET /api/contacts (Worker reads the private Google Sheet). If that is not set up yet, demo data is shown
   with a clear banner. Mails are only drafted (mailto / Outlook web / Gmail); BCC is used when a group has several addresses. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const store = { get(k, d) { try { return localStorage.getItem(k) ?? d; } catch (e) { return d; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* ignore */ } } };
  let CFG, ROWS = [], VIEW = [];
  const selected = new Set(), modeOverride = {};
  const FILTERS = [["country", "Country"], ["language", "Language"], ["type", "Type"], ["topic", "Topic"], ["age_group", "Age group"]];
  const filt = {}; let nameQ = "";

  const splitMails = (s) => String(s || "").split(/[;,\s]+/).map((x) => x.trim()).filter((x) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(x));
  const modeOf = (r, i) => modeOverride[i] || r.send_mode || "main";
  // who gets the mail: {to, bcc}
  function recipients(r, mode) {
    const main = splitMails(r.contact_email), gen = splitMails(r.general_email), extra = splitMails(r.extra_emails);
    let all = mode === "general" ? gen : mode === "all" ? [...main, ...gen, ...extra] : main;
    all = [...new Set(all)];
    return { to: all[0] || "", bcc: all.slice(1) };
  }

  async function load() {
    CFG = await (await fetch("data/feedback-config.json")).json();
    let data;
    try {
      const r = await fetch("/api/contacts", { cache: "no-store" });
      if (!r.ok) throw new Error(String(r.status));
      data = await r.json();
      $("fbBanner").innerHTML = "";
    } catch (e) {
      data = await (await fetch("data/feedback-demo.json")).json();
      $("fbBanner").innerHTML = '<div class="fb-banner"><b>Demo data.</b> The private Google Sheet is not connected yet (or you are viewing this page locally). The entries below are made up and use example.org addresses. See docs/FEEDBACK_PLAN.md, step F1b.</div>';
    }
    ROWS = data.contacts || [];
    init();
  }

  function init() {
    $("fbProduct").innerHTML = CFG.products.map((p) => `<option value="${esc(p.id)}">${esc(p.label)}</option>`).join("");
    $("fbProduct").value = store.get("fb.product", CFG.products[0].id);
    $("fbProduct").onchange = () => store.set("fb.product", $("fbProduct").value);
    $("fbLink").value = store.get("fb.link", ""); $("fbLink").oninput = () => store.set("fb.link", $("fbLink").value.trim());
    $("fbDays").value = store.get("fb.days", CFG.response_days);
    $("fbDays").oninput = () => { store.set("fb.days", $("fbDays").value); deadlineHint(); };
    deadlineHint();
    drawFilters(); apply();
    $("fbWrite").onclick = startMails;
  }
  const deadline = () => { const d = new Date(Date.now() + (parseInt($("fbDays").value, 10) || CFG.response_days) * 864e5);
    return d.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }); };
  const deadlineHint = () => { $("fbDeadline").textContent = "Deadline in the mail: " + deadline(); };

  function drawFilters() {
    const opts = (k) => [...new Set(ROWS.map((r) => r[k]).filter(Boolean))].sort((a, b) => a.localeCompare(b));
    $("fbFilters").innerHTML = `<label>Name<input id="fq" type="search" placeholder="Search names"></label>` +
      FILTERS.map(([k, l]) => `<label>${l}<select data-f="${k}"><option value="">All</option>${opts(k).map((o) => `<option>${esc(o)}</option>`).join("")}</select></label>`).join("") +
      `<label>Has e-mail<select data-f="_mail"><option value="">All</option><option value="yes">Yes</option><option value="no">No</option></select></label>`;
    $("fbFilters").oninput = (e) => {
      if (e.target.id === "fq") nameQ = e.target.value.toLowerCase(); else if (e.target.dataset.f) filt[e.target.dataset.f] = e.target.value;
      apply();
    };
  }

  function apply() {
    VIEW = ROWS.map((r, i) => ({ r, i })).filter(({ r, i }) => {
      if (nameQ && !(r.name || "").toLowerCase().includes(nameQ) && !(r.description || "").toLowerCase().includes(nameQ)) return false;
      for (const [k] of FILTERS) if (filt[k] && r[k] !== filt[k]) return false;
      if (filt._mail) { const has = !!recipients(r, modeOf(r, i)).to; if ((filt._mail === "yes") !== has) return false; }
      return true;
    });
    $("fbCount").textContent = `${VIEW.length} of ${ROWS.length} groups`;
    const head = `<tr><th><input type="checkbox" id="fbAll" aria-label="Select all shown"></th><th>Group</th><th>Type · age</th><th>Country · place</th><th>Language · topic</th><th>Contact</th><th>Send to</th></tr>`;
    $("fbTable").innerHTML = head + VIEW.map(({ r, i }) => {
      const mode = modeOf(r, i), rc = recipients(r, mode), n = rc.bcc.length + (rc.to ? 1 : 0);
      return `<tr><td><input type="checkbox" class="fb-pick" data-i="${i}" ${selected.has(i) ? "checked" : ""} ${rc.to ? "" : "disabled"} aria-label="Select ${esc(r.name)}"></td>
        <td><b>${esc(r.name)}</b><br><span class="hint">${esc(r.description)}</span></td>
        <td>${esc(r.type)}<br>${esc(r.age_group)}</td><td>${esc(r.country)}<br>${esc(r.place)}</td><td>${esc(r.language)}<br>${esc(r.topic)}</td>
        <td>${esc(r.contact_name)}${rc.to ? `<br>${esc(rc.to)}${n > 1 ? ` <span class="hint">+${n - 1}</span>` : ""}` : '<br><span class="nomail">no e-mail for this mode</span>'}</td>
        <td><select class="fb-mode" data-i="${i}">${CFG.send_modes.map((m) => `<option value="${m.id}" ${m.id === mode ? "selected" : ""}>${esc(m.label)}</option>`).join("")}</select></td></tr>`;
    }).join("");
    counter();
  }
  function counter() { $("fbSel").textContent = `${selected.size} selected`; $("fbWrite").disabled = !selected.size; }
  $("fbTable").addEventListener("change", (e) => {
    const t = e.target;
    if (t.id === "fbAll") { VIEW.forEach(({ r, i }) => { if (recipients(r, modeOf(r, i)).to) (t.checked ? selected.add(i) : selected.delete(i)); }); apply(); }
    else if (t.classList.contains("fb-pick")) { (t.checked ? selected.add(+t.dataset.i) : selected.delete(+t.dataset.i)); counter(); }
    else if (t.classList.contains("fb-mode")) { const i = +t.dataset.i; modeOverride[i] = t.value; if (!recipients(ROWS[i], t.value).to) selected.delete(i); apply(); }
  });

  /* ---------- mails: one per selected group, one after the other ---------- */
  const markGaps = (t) => esc(t).replace(/\[([^\]]+)\]/g, '<mark style="background:#ffff00">[$1]</mark>');
  function buildMail(i) {
    const r = ROWS[i], rc = recipients(r, modeOf(r, i));
    const prod = CFG.products.find((p) => p.id === $("fbProduct").value) || CFG.products[0];
    let link = $("fbLink").value.trim();
    const code = encodeURIComponent(r.group_code || "");
    link = !link ? "[survey link]" : link.includes("{group}") ? link.replace(/\{group\}/g, code) : link;
    const fill = (t) => t.replace(/\{name\}/g, r.name.replace(/\s*\((DEMO|EXAMPLE)[^)]*\)/i, "")).replace(/\{product\}/g, prod.label.replace(/\s*\(.*\)$/, ""))
      .replace(/\{link\}/g, link).replace(/\{deadline\}/g, deadline());
    const remind = $("fbRemind").checked;
    return { to: rc.to, bcc: rc.bcc, group: r.name,
      subject: fill(remind ? CFG.mail.reminder_subject : CFG.mail.subject),
      body: (remind ? fill(CFG.mail.reminder_intro) : "") + fill(CFG.mail.body).replace(/\s+$/, "") + "\n" };
  }
  let queue = [], pos = 0;
  function startMails() { queue = [...selected].sort((a, b) => a - b); pos = 0; showMail(); }
  async function copyMail(m) {
    const html = `<div style="font-family:Calibri,Arial,sans-serif;font-size:11pt">${markGaps(m.body).replace(/\n/g, "<br>")}</div>`;
    try { await navigator.clipboard.write([new ClipboardItem({ "text/html": new Blob([html], { type: "text/html" }), "text/plain": new Blob([m.body], { type: "text/plain" }) })]); return true; }
    catch (e) { return false; }
  }
  function showMail() {
    let d = $("mailDialog");
    if (!d) {
      d = document.createElement("dialog"); d.id = "mailDialog"; d.className = "mail-dialog";
      d.innerHTML = `<form method="dialog" class="mail-box"><h2>Feedback mail</h2><p class="mail-queue" id="mailQueue"></p>
        <p class="row"><b>To:</b> <span id="mailTo"></span></p><p class="row"><b>BCC:</b> <span id="mailBcc"></span></p><p class="row"><b>Subject:</b> <span id="mailSubject"></span></p>
        <div class="mail-preview" id="mailPreview"></div>
        <p class="hint">Yellow = please fill in or check. Your mail program opens with the text; the same text with the yellow marks is copied – paste it over the draft to keep the marks. Several addresses of one group are put in BCC, so they do not see each other.</p>
        <div class="mail-actions"><button type="button" class="btn-primary" data-open="app">Open in mail app</button>
        <button type="button" class="btn-quiet" data-open="owa">Outlook on the web</button><button type="button" class="btn-quiet" data-open="gmail">Gmail</button>
        <button type="button" class="btn-quiet" data-open="copy">Copy text</button><button type="button" class="btn-quiet" id="mailNext">Next group →</button><button class="btn-quiet" value="close">Close</button></div>
        <p class="hint" id="mailStatus" role="status"></p></form>`;
      document.body.append(d);
      d.addEventListener("click", async (e) => {
        if (e.target.id === "mailNext") { e.preventDefault(); pos++; if (pos < queue.length) showMail(); else d.close(); return; }
        const b = e.target.closest("[data-open]"); if (!b) return;
        const m = d._mail, q = encodeURIComponent, bcc = m.bcc.join(",");
        const ok = await copyMail(m);
        $("mailStatus").textContent = ok ? "Text with yellow marks copied." : "Copying did not work – please select the text above and copy it.";
        const url = { app: `mailto:${m.to}?subject=${q(m.subject)}${bcc ? "&bcc=" + q(bcc) : ""}&body=${q(m.body.replace(/\n/g, "\r\n"))}`,
          owa: `https://outlook.office.com/mail/deeplink/compose?to=${q(m.to)}${bcc ? "&bcc=" + q(bcc) : ""}&subject=${q(m.subject)}&body=${q(m.body)}`,
          gmail: `https://mail.google.com/mail/?view=cm&fs=1&to=${q(m.to)}${bcc ? "&bcc=" + q(bcc) : ""}&su=${q(m.subject)}&body=${q(m.body)}` }[b.dataset.open];
        if (url) { if (b.dataset.open === "app") location.href = url; else window.open(url, "_blank", "noopener"); }
      });
    }
    const m = buildMail(queue[pos]); d._mail = m;
    $("mailQueue").textContent = `Mail ${pos + 1} of ${queue.length} · ${m.group}`;
    $("mailTo").textContent = m.to; $("mailBcc").textContent = m.bcc.join(", ") || "–"; $("mailSubject").innerHTML = markGaps(m.subject);
    $("mailPreview").innerHTML = markGaps(m.body).replace(/\n/g, "<br>"); $("mailStatus").textContent = "";
    $("mailNext").style.display = queue.length > 1 ? "" : "none"; $("mailNext").textContent = pos + 1 < queue.length ? "Next group →" : "Finish";
    if (!d.open) d.showModal();
  }

  load().catch((e) => { $("fbBanner").innerHTML = `<div class="fb-banner">Could not load the page data: ${esc(e.message)}</div>`; });
})();
