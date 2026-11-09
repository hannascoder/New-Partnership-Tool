/* Partner Finder export: builds PDF, Excel and Word files in the browser.
   Exposes window.PartnerExport.download(format, list) where
     list = { sections: [{title, note, items}], filters: [[label, value]], topics, updated, count }
     item = { name, type, country, reaches, scope, languages, channels, ownership, topic, audience,
              unProfile, memberOf, website, contact, social: [[label, url]], notes }
   The libraries (assets/vendor/) are loaded only when someone exports. */
(function () {
  "use strict";
  const TOOL = "Partner Finder";
  const FILE = "partner-finder";
  const BLUE = "009EDB", INK = "003D6B", MUTED = "5C6B7E", LIGHT = "E6F4FB";
  const NOTE = "Orientation only. Please confirm that an outlet is active before contacting it.";
  // landscape: one column per field
  const COLS = [
    ["name", "Name", 24], ["type", "Type", 18], ["country", "Country", 16], ["reaches", "Reaches", 20],
    ["scope", "Scope", 17], ["languages", "Languages", 18], ["channels", "Channels", 16], ["ownership", "Ownership", 19],
    ["topic", "Topic", 14], ["audience", "Target audience", 14], ["unProfile", "UN profile", 13], ["memberOf", "Member of", 14], ["website", "Website", 20],
    ["contact", "Contact", 19], ["social", "Social media", 16], ["notes", "Notes", 20]];
  // portrait: the same fields grouped into five columns (labels inside the cell)
  const GROUPS = {
    outlet: [["name", ""], ["type", "Type"], ["country", "Country"], ["scope", "Scope"], ["ownership", "Ownership"]],
    reach: [["reaches", "Reaches"], ["languages", "Languages"], ["channels", "Channels"], ["topic", "Topic"],
            ["audience", "Target audience"], ["unProfile", "UN profile"], ["memberOf", "Member of"]],
    more: [["social", "Social media"], ["notes", "Notes"]]};
  const COLS_PORTRAIT = [["outlet", "Outlet", 52], ["reach", "Reach & content", 64], ["website", "Website", 26],
                         ["contact", "Contact", 26], ["more", "Social media & notes", 26]];
  const BASE = (document.currentScript && document.currentScript.src.replace(/[^/]*$/, "")) || "assets/";

  const loaded = {};
  function script(src) {
    if (!loaded[src]) {
      loaded[src] = new Promise((ok, fail) => {
        const s = document.createElement("script"); s.src = BASE + src; s.onload = ok;
        s.onerror = () => fail(new Error("Could not load " + src)); document.head.appendChild(s);
      });
    }
    return loaded[src];
  }
  async function bytes(path) {
    const r = await fetch(BASE + path); if (!r.ok) throw new Error("Could not load " + path);
    return new Uint8Array(await r.arrayBuffer());
  }
  function b64(u8) { let s = ""; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000)); return btoa(s); }
  function today() { return new Date().toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }); }
  function stamp() { return new Date().toISOString().slice(0, 10); }
  function save(blob, ext) {
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `${FILE}_${stamp()}.${ext}`;
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }
  function cellText(it, key) {
    if (GROUPS[key]) {
      return GROUPS[key].map(([k, l]) => [l, cellText(it, k)]).filter(([, v]) => v).map(([l, v]) => (l ? l + ": " : "") + v).join("\n");
    }
    if (key === "website") return (it.website || "").replace(/^https?:\/\//, "").replace(/\/$/, "");
    if (key === "social") return (it.social || []).map((s) => s[0]).join(", ");
    return it[key] == null ? "" : String(it[key]);
  }
  function link(it, key) {
    if (key === "website" && it.website) return it.website;
    if (key === "contact" && it.contact) return it.contact.includes("@") && !it.contact.startsWith("http") ? "mailto:" + it.contact : it.contact;
    if (key === "social" && it.social && it.social.length) return it.social[0][1];
    return null;
  }
  function headerLines(list) {
    const counts = list.sections.filter((s) => s.items.length).map((s) => `${s.items.length} ${s.title}`).join(", ");
    return [
      ["Exported", today()],
      ["Data as of", list.updated || ""],
      ["Filters", list.filters && list.filters.length ? list.filters.map((f) => f[1] ? `${f[0]}: ${f[1]}` : f[0]).join(" · ") : "None (all items)"],
      ["Items", `${list.count} outlet${list.count === 1 ? "" : "s"}${counts ? ` (${counts})` : ""}`]];
  }

  /* ------------------------------------------------------------------ PDF */
  async function pdf(list, opts = {}) {
    const portrait = opts.orientation === "portrait", cols = portrait ? COLS_PORTRAIT : COLS;
    await script("vendor/jspdf-4.2.1.umd.min.js");
    await script("vendor/jspdf-autotable-5.0.8.min.js");
    const [reg, bold, logo] = await Promise.all([bytes("vendor/NotoSans-Regular.ttf"), bytes("vendor/NotoSans-Bold.ttf"), bytes("un_emblem.png")]);
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ orientation: portrait ? "portrait" : "landscape", unit: "mm", format: "a4" });
    doc.addFileToVFS("NotoSans-Regular.ttf", b64(reg)); doc.addFont("NotoSans-Regular.ttf", "Noto", "normal");
    doc.addFileToVFS("NotoSans-Bold.ttf", b64(bold)); doc.addFont("NotoSans-Bold.ttf", "Noto", "bold");
    doc.setFont("Noto", "normal");
    const W = doc.internal.pageSize.getWidth(), M = 10;
    doc.addImage("data:image/png;base64," + b64(logo), "PNG", M, 8, 14, 11.5);
    doc.setFontSize(8); doc.setTextColor("#" + MUTED); doc.text("United Nations · DGC Partnerships", M + 17, 12);
    doc.setFont("Noto", "bold"); doc.setFontSize(15); doc.setTextColor("#" + INK); doc.text(TOOL, M + 17, 18.5);
    let y = 25; doc.setFontSize(8);
    headerLines(list).forEach(([k, v]) => {
      doc.setFont("Noto", "bold"); doc.setTextColor("#" + INK); doc.text(k + ":", M, y);
      doc.setFont("Noto", "normal"); doc.setTextColor("#0F1A2B");
      const lines = doc.splitTextToSize(v, W - 2 * M - 22); doc.text(lines, M + 22, y); y += 4 * lines.length;
    });
    doc.setFont("Noto", "normal"); doc.setTextColor("#" + MUTED); doc.text(NOTE, M, y); y += 4;

    const total = cols.reduce((a, c) => a + c[2], 0), scale = (W - 2 * M) / total;
    const body = [];
    list.sections.forEach((s) => {
      if (!s.items.length) return;
      body.push([{ content: `${s.title} — ${s.note}`, colSpan: cols.length, _section: true,
        styles: { fillColor: "#" + LIGHT, textColor: "#" + INK, fontStyle: "bold", fontSize: 8 } }]);
      s.items.forEach((it) => body.push(cols.map(([k]) => ({ content: cellText(it, k), _link: link(it, k), _bold: k === "outlet" }))));
    });
    doc.autoTable({
      startY: y, margin: { left: M, right: M, top: 12, bottom: 12 },
      head: [cols.map((c) => c[1])], body, showHead: "everyPage", rowPageBreak: "avoid",
      styles: { font: "Noto", fontSize: portrait ? 7 : 6.5, cellPadding: 1.2, overflow: "linebreak", valign: "top", textColor: "#0F1A2B", lineColor: "#E3EBF1", lineWidth: 0.1 },
      headStyles: { font: "Noto", fontStyle: "bold", fillColor: "#" + INK, textColor: "#FFFFFF", fontSize: 7 },
      columnStyles: Object.fromEntries(cols.map((c, i) => [i, { cellWidth: c[2] * scale }])),
      didParseCell: (d) => { if (d.section === "body" && d.cell.raw && d.cell.raw._link) d.cell.styles.textColor = "#0072BC"; },
      didDrawCell: (d) => {
        if (d.section === "body" && d.cell.raw && d.cell.raw._link) doc.link(d.cell.x, d.cell.y, d.cell.width, d.cell.height, { url: d.cell.raw._link });
      },
    });
    const pages = doc.internal.getNumberOfPages();
    for (let i = 1; i <= pages; i++) {
      doc.setPage(i); doc.setFont("Noto", "normal"); doc.setFontSize(7); doc.setTextColor("#" + MUTED);
      const H = doc.internal.pageSize.getHeight();
      doc.text(`${TOOL} · DGC Partnerships`, M, H - 5); doc.text(`Page ${i} of ${pages}`, W - M, H - 5, { align: "right" });
    }
    return doc.output("blob");
  }

  /* ---------------------------------------------------------------- Excel */
  async function excel(list) {
    await script("vendor/exceljs-4.4.0.min.js");
    const logo = await bytes("un_emblem.png");
    const wb = new window.ExcelJS.Workbook(); wb.creator = TOOL;
    const ws = wb.addWorksheet(TOOL, { pageSetup: { paperSize: 9, orientation: "landscape", fitToPage: true, fitToWidth: 1, fitToHeight: 0,
      margins: { left: 0.3, right: 0.3, top: 0.4, bottom: 0.4, header: 0.2, footer: 0.2 } } });
    ws.headerFooter.oddFooter = `&L${TOOL} · DGC Partnerships&RPage &P of &N`;
    ws.columns = COLS.map((c) => ({ key: c[0], width: Math.round(c[2] * 1.15) }));
    const img = wb.addImage({ base64: b64(logo), extension: "png" });
    ws.addImage(img, { tl: { col: 0, row: 0 }, ext: { width: 52, height: 43 } });
    ws.getRow(1).height = 20; ws.getRow(2).height = 20;
    ws.getCell("B1").value = "United Nations · DGC Partnerships"; ws.getCell("B1").font = { size: 9, color: { argb: "FF" + MUTED } };
    ws.getCell("B2").value = TOOL; ws.getCell("B2").font = { size: 16, bold: true, color: { argb: "FF" + INK } };
    let r = 4;
    headerLines(list).forEach(([k, v]) => {
      ws.getCell(r, 1).value = k; ws.getCell(r, 1).font = { bold: true, color: { argb: "FF" + INK } };
      ws.mergeCells(r, 2, r, COLS.length); ws.getCell(r, 2).value = v; ws.getCell(r, 2).alignment = { wrapText: true, vertical: "top" };
      r++;
    });
    ws.mergeCells(r, 1, r, COLS.length); ws.getCell(r, 1).value = NOTE; ws.getCell(r, 1).font = { italic: true, color: { argb: "FF" + MUTED } };
    r += 2;
    const headRow = ws.getRow(r);
    COLS.forEach((c, i) => {
      const cell = headRow.getCell(i + 1); cell.value = c[1];
      cell.font = { bold: true, color: { argb: "FFFFFFFF" } };
      cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF" + INK } };
      cell.alignment = { vertical: "middle", wrapText: true };
    });
    ws.views = [{ state: "frozen", ySplit: r }];
    ws.pageSetup.printTitlesRow = `${r}:${r}`;
    r++;
    list.sections.forEach((s) => {
      if (!s.items.length) return;
      ws.mergeCells(r, 1, r, COLS.length);
      const sc = ws.getCell(r, 1); sc.value = `${s.title} — ${s.note}`;
      sc.font = { bold: true, color: { argb: "FF" + INK } };
      sc.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF" + LIGHT } };
      r++;
      s.items.forEach((it) => {
        const row = ws.getRow(r);
        COLS.forEach(([k], i) => {
          const cell = row.getCell(i + 1), text = cellText(it, k), url = link(it, k);
          cell.value = url && text ? { text, hyperlink: url } : text;
          cell.alignment = { wrapText: true, vertical: "top" };
          if (url && text) cell.font = { color: { argb: "FF0072BC" }, underline: true };
        });
        r++;
      });
    });
    const buf = await wb.xlsx.writeBuffer();
    return new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  }

  /* ----------------------------------------------------------------- Word */
  async function word(list, opts = {}) {
    const portrait = opts.orientation === "portrait", COLS_ = portrait ? COLS_PORTRAIT : COLS;
    await script("vendor/docx-9.7.1.iife.js");
    const logo = await bytes("un_emblem.png");
    const D = window.docx;
    const PAGE_W = portrait ? 11906 : 16838, PAGE_H = portrait ? 16838 : 11906, MARGIN = 567; // A4 in twips, 1 cm margins
    const usable = PAGE_W - 2 * MARGIN, total = COLS_.reduce((a, c) => a + c[2], 0);
    const widths = COLS_.map((c) => Math.floor(c[2] / total * usable));
    const run = (t, o = {}) => new D.TextRun({ text: t, font: "Calibri", size: o.size || 14, bold: o.bold, color: o.color });
    const cellParas = (it, k) => {
      const t = cellText(it, k), url = link(it, k);
      if (url && t) return [new D.Paragraph({ children: [new D.ExternalHyperlink({ link: url, children: [new D.TextRun({ text: t, style: "Hyperlink", font: "Calibri", size: 14 })] })] })];
      return (t || "").split("\n").map((line, i) => new D.Paragraph({ children: [run(line, { bold: k === "outlet" && i === 0 })] }));
    };
    const header = new D.TableRow({ tableHeader: true, cantSplit: true, children: COLS_.map((c, i) => new D.TableCell({
      width: { size: widths[i], type: D.WidthType.DXA }, shading: { fill: INK, type: D.ShadingType.CLEAR, color: "auto" },
      children: [new D.Paragraph({ children: [run(c[1], { bold: true, color: "FFFFFF", size: 15 })] })] })) });
    const rows = [header];
    list.sections.forEach((s) => {
      if (!s.items.length) return;
      rows.push(new D.TableRow({ cantSplit: true, children: [new D.TableCell({ columnSpan: COLS_.length,
        width: { size: usable, type: D.WidthType.DXA }, shading: { fill: LIGHT, type: D.ShadingType.CLEAR, color: "auto" },
        children: [new D.Paragraph({ children: [run(`${s.title} — ${s.note}`, { bold: true, color: INK, size: 16 })] })] })] }));
      s.items.forEach((it) => rows.push(new D.TableRow({ cantSplit: true, children: COLS_.map(([k], i) => new D.TableCell({
        width: { size: widths[i], type: D.WidthType.DXA }, children: cellParas(it, k) })) })));
    });
    const info = headerLines(list).map(([k, v]) => new D.Paragraph({ spacing: { after: 40 }, children: [run(k + ": ", { bold: true, color: INK, size: 17 }), run(v, { size: 17 })] }));
    const doc = new D.Document({
      styles: { default: { document: { run: { font: "Calibri" } } } },
      sections: [{
        // docx swaps width and height itself for landscape: always pass the portrait size
        properties: { page: { size: { width: 11906, height: 16838, orientation: portrait ? D.PageOrientation.PORTRAIT : D.PageOrientation.LANDSCAPE }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
        footers: { default: new D.Footer({ children: [new D.Paragraph({ tabStops: [{ type: D.TabStopType.RIGHT, position: usable }],
          children: [run(`${TOOL} · DGC Partnerships`, { color: MUTED }), new D.TextRun({ children: ["\tPage ", D.PageNumber.CURRENT, " of ", D.PageNumber.TOTAL_PAGES], font: "Calibri", size: 14, color: MUTED })] })] }) },
        children: [
          new D.Paragraph({ children: [new D.ImageRun({ type: "png", data: logo, transformation: { width: 48, height: 40 } }),
            run("   United Nations · DGC Partnerships", { color: MUTED, size: 18 })] }),
          new D.Paragraph({ spacing: { after: 120 }, children: [run(TOOL, { bold: true, color: INK, size: 32 })] }),
          ...info,
          new D.Paragraph({ spacing: { after: 160 }, children: [new D.TextRun({ text: NOTE, italics: true, color: MUTED, font: "Calibri", size: 16 })] }),
          new D.Table({ layout: D.TableLayoutType.FIXED, width: { size: usable, type: D.WidthType.DXA }, columnWidths: widths, rows }),
        ],
      }],
    });
    return D.Packer.toBlob(doc);
  }

  /* opts.orientation: "landscape" (default) or "portrait" (PDF and Word) */
  async function download(format, list, opts = {}) {
    const make = { pdf, xlsx: excel, docx: word }[format];
    if (!make) throw new Error("Unknown format " + format);
    const blob = await make(list, opts);
    save(blob, format);
    return blob;
  }
  window.PartnerExport = { download, build: { pdf, xlsx: excel, docx: word } };
})();
