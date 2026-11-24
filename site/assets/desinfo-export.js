/* Disinformation monitor export: builds PDF, Word and Excel reports in the browser (nothing leaves the browser).
   window.DesinfoExport.download(format, report) with format "pdf" | "docx" | "xlsx" and
     report = { title, info: [[label, value]], note, tables: [{ title, note, cols: [[label, width]], rows: [[cell]] }] }
     cell = "text" or { t: "text", url: "https://..." }
   Same look as the Partner Finder export (UN blue, Noto Sans, emblem). Libraries load only when someone exports. */
(function () {
  "use strict";
  const BLUE = "009EDB", INK = "003D6B", MUTED = "5C6B7E", LIGHT = "E6F4FB";
  const FILE = "disinformation-monitor";
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
  const text = (c) => (c && typeof c === "object" ? c.t : c == null ? "" : String(c));
  const url = (c) => (c && typeof c === "object" && /^https?:\/\//i.test(c.url || "") ? c.url : "");
  function save(blob, ext) {
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
    a.download = `${FILE}_${new Date().toISOString().slice(0, 10)}.${ext}`;
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }
  const scaled = (cols, total) => { const s = cols.reduce((a, c) => a + c[1], 0); return cols.map((c) => c[1] / s * total); };

  /* ------------------------------------------------------------------ PDF */
  async function pdf(r) {
    await script("vendor/jspdf-4.2.1.umd.min.js");
    await script("vendor/jspdf-autotable-5.0.8.min.js");
    const [reg, bold, logo] = await Promise.all([bytes("vendor/NotoSans-Regular.ttf"), bytes("vendor/NotoSans-Bold.ttf"), bytes("un_emblem.png")]);
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
    doc.addFileToVFS("NotoSans-Regular.ttf", b64(reg)); doc.addFont("NotoSans-Regular.ttf", "Noto", "normal");
    doc.addFileToVFS("NotoSans-Bold.ttf", b64(bold)); doc.addFont("NotoSans-Bold.ttf", "Noto", "bold");
    doc.setFont("Noto", "normal");
    const W = doc.internal.pageSize.getWidth(), M = 10;
    doc.addImage("data:image/png;base64," + b64(logo), "PNG", M, 8, 14, 11.5);
    doc.setFontSize(8); doc.setTextColor("#" + MUTED); doc.text("United Nations · DGC Partnerships", M + 17, 12);
    doc.setFont("Noto", "bold"); doc.setFontSize(15); doc.setTextColor("#" + INK); doc.text(r.title, M + 17, 18.5);
    let y = 25; doc.setFontSize(8);
    r.info.forEach(([k, v]) => {
      doc.setFont("Noto", "bold"); doc.setTextColor("#" + INK); doc.text(k + ":", M, y);
      doc.setFont("Noto", "normal"); doc.setTextColor("#0F1A2B");
      const lines = doc.splitTextToSize(v, W - 2 * M - 26); doc.text(lines, M + 26, y); y += 4 * lines.length;
    });
    doc.setFont("Noto", "normal"); doc.setTextColor("#" + MUTED);
    const nl = doc.splitTextToSize(r.note, W - 2 * M); doc.text(nl, M, y); y += 4 * nl.length + 2;
    r.tables.forEach((t) => {
      if (!t.rows.length) return;
      if (y > 175) { doc.addPage(); y = 14; }
      doc.setFont("Noto", "bold"); doc.setFontSize(11); doc.setTextColor("#" + INK); doc.text(t.title, M, y + 4); y += 6;
      if (t.note) { doc.setFont("Noto", "normal"); doc.setFontSize(7.5); doc.setTextColor("#" + MUTED); const tl = doc.splitTextToSize(t.note, W - 2 * M); doc.text(tl, M, y + 2); y += 3.5 * tl.length + 1; }
      const widths = scaled(t.cols, W - 2 * M);
      doc.autoTable({
        startY: y, margin: { left: M, right: M, top: 12, bottom: 12 },
        head: [t.cols.map((c) => c[0])], body: t.rows.map((row) => row.map((c) => ({ content: text(c), _link: url(c) }))),
        showHead: "everyPage", rowPageBreak: "avoid",
        styles: { font: "Noto", fontSize: 7, cellPadding: 1.2, overflow: "linebreak", valign: "top", textColor: "#0F1A2B", lineColor: "#E3EBF1", lineWidth: 0.1 },
        headStyles: { font: "Noto", fontStyle: "bold", fillColor: "#" + INK, textColor: "#FFFFFF", fontSize: 7 },
        alternateRowStyles: { fillColor: "#F7FAFC" },
        columnStyles: Object.fromEntries(widths.map((w, i) => [i, { cellWidth: w }])),
        didParseCell: (d) => { if (d.section === "body" && d.cell.raw && d.cell.raw._link) d.cell.styles.textColor = "#0072BC"; },
        didDrawCell: (d) => { if (d.section === "body" && d.cell.raw && d.cell.raw._link) doc.link(d.cell.x, d.cell.y, d.cell.width, d.cell.height, { url: d.cell.raw._link }); },
      });
      y = doc.lastAutoTable.finalY + 8;
    });
    const pages = doc.internal.getNumberOfPages();
    for (let i = 1; i <= pages; i++) {
      doc.setPage(i); doc.setFont("Noto", "normal"); doc.setFontSize(7); doc.setTextColor("#" + MUTED);
      const H = doc.internal.pageSize.getHeight();
      doc.text(r.title + " · DGC Partnerships", M, H - 5); doc.text(`Page ${i} of ${pages}`, W - M, H - 5, { align: "right" });
    }
    return doc.output("blob");
  }

  /* ---------------------------------------------------------------- Excel */
  async function excel(r) {
    await script("vendor/exceljs-4.4.0.min.js");
    const wb = new window.ExcelJS.Workbook(); wb.creator = r.title;
    const fill = (argb) => ({ type: "pattern", pattern: "solid", fgColor: { argb: "FF" + argb } });
    const info = wb.addWorksheet("About this report");
    info.columns = [{ width: 22 }, { width: 110 }];
    info.getCell("A1").value = r.title; info.getCell("A1").font = { size: 16, bold: true, color: { argb: "FF" + INK } };
    r.info.forEach(([k, v], i) => {
      info.getCell(3 + i, 1).value = k; info.getCell(3 + i, 1).font = { bold: true, color: { argb: "FF" + INK } };
      info.getCell(3 + i, 2).value = v; info.getCell(3 + i, 2).alignment = { wrapText: true, vertical: "top" };
    });
    const nr = 4 + r.info.length; info.mergeCells(nr, 1, nr, 2); info.getCell(nr, 1).value = r.note;
    info.getCell(nr, 1).alignment = { wrapText: true, vertical: "top" }; info.getRow(nr).height = 48;
    info.getCell(nr, 1).font = { italic: true, color: { argb: "FF" + MUTED } };
    r.tables.forEach((t, n) => {
      if (!t.rows.length) return;
      const ws = wb.addWorksheet(`${n + 1} ${t.title}`.replace(/[\\/?*[\]:]/g, " ").slice(0, 31),
        { pageSetup: { paperSize: 9, orientation: "landscape", fitToPage: true, fitToWidth: 1, fitToHeight: 0 } });
      ws.columns = t.cols.map((c) => ({ width: Math.max(10, Math.round(c[1] * 1.2)) }));
      ws.getCell("A1").value = t.title; ws.getCell("A1").font = { size: 13, bold: true, color: { argb: "FF" + INK } };
      ws.getCell("A2").value = t.note || ""; ws.getCell("A2").font = { italic: true, color: { argb: "FF" + MUTED } };
      const head = ws.getRow(4);
      t.cols.forEach((c, i) => { const cell = head.getCell(i + 1); cell.value = c[0]; cell.font = { bold: true, color: { argb: "FFFFFFFF" } }; cell.fill = fill(INK); cell.alignment = { vertical: "middle", wrapText: true }; });
      ws.views = [{ state: "frozen", ySplit: 4 }];
      t.rows.forEach((row, ri) => {
        const rr = ws.getRow(5 + ri);
        row.forEach((c, i) => {
          const cell = rr.getCell(i + 1), tx = text(c), u = url(c);
          cell.value = u && tx ? { text: tx, hyperlink: u } : tx;
          cell.alignment = { wrapText: true, vertical: "top" };
          if (u && tx) cell.font = { color: { argb: "FF0072BC" }, underline: true };
        });
      });
    });
    const buf = await wb.xlsx.writeBuffer();
    return new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  }

  /* ----------------------------------------------------------------- Word */
  async function word(r) {
    await script("vendor/docx-9.7.1.iife.js");
    const logo = await bytes("un_emblem.png");
    const D = window.docx;
    const MARGIN = 567, PAGE_W = 16838, usable = PAGE_W - 2 * MARGIN;
    const run = (t, o = {}) => new D.TextRun({ text: t, font: "Calibri", size: o.size || 15, bold: o.bold, color: o.color, italics: o.italics });
    const para = (c, bold) => {
      const t = text(c), u = url(c);
      if (u && t) return [new D.Paragraph({ children: [new D.ExternalHyperlink({ link: u, children: [new D.TextRun({ text: t, style: "Hyperlink", font: "Calibri", size: 15 })] })] })];
      return (t || "").split("\n").map((line) => new D.Paragraph({ children: [run(line, { bold })] }));
    };
    const blocks = [];
    r.tables.forEach((t) => {
      if (!t.rows.length) return;
      const widths = scaled(t.cols, usable).map(Math.floor);
      const head = new D.TableRow({ tableHeader: true, cantSplit: true, children: t.cols.map((c, i) => new D.TableCell({
        width: { size: widths[i], type: D.WidthType.DXA }, shading: { fill: INK, type: D.ShadingType.CLEAR, color: "auto" },
        children: [new D.Paragraph({ children: [run(c[0], { bold: true, color: "FFFFFF", size: 15 })] })] })) });
      const rows = t.rows.map((row) => new D.TableRow({ cantSplit: true, children: row.map((c, i) => new D.TableCell({
        width: { size: widths[i], type: D.WidthType.DXA }, children: para(c, i === 0) })) }));
      blocks.push(new D.Paragraph({ spacing: { before: 240, after: 60 }, children: [run(t.title, { bold: true, color: INK, size: 24 })] }));
      if (t.note) blocks.push(new D.Paragraph({ spacing: { after: 80 }, children: [run(t.note, { italics: true, color: MUTED, size: 15 })] }));
      blocks.push(new D.Table({ layout: D.TableLayoutType.FIXED, width: { size: usable, type: D.WidthType.DXA }, columnWidths: widths, rows: [head, ...rows] }));
    });
    const doc = new D.Document({
      styles: { default: { document: { run: { font: "Calibri" } } } },
      sections: [{
        properties: { page: { size: { width: 11906, height: 16838, orientation: D.PageOrientation.LANDSCAPE }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
        footers: { default: new D.Footer({ children: [new D.Paragraph({ tabStops: [{ type: D.TabStopType.RIGHT, position: usable }],
          children: [run(r.title + " · DGC Partnerships", { color: MUTED, size: 14 }), new D.TextRun({ children: ["\tPage ", D.PageNumber.CURRENT, " of ", D.PageNumber.TOTAL_PAGES], font: "Calibri", size: 14, color: MUTED })] })] }) },
        children: [
          new D.Paragraph({ children: [new D.ImageRun({ type: "png", data: logo, transformation: { width: 48, height: 40 } }), run("   United Nations · DGC Partnerships", { color: MUTED, size: 18 })] }),
          new D.Paragraph({ spacing: { after: 120 }, children: [run(r.title, { bold: true, color: INK, size: 32 })] }),
          ...r.info.map(([k, v]) => new D.Paragraph({ spacing: { after: 40 }, children: [run(k + ": ", { bold: true, color: INK, size: 17 }), run(v, { size: 17 })] })),
          new D.Paragraph({ spacing: { after: 120 }, children: [run(r.note, { italics: true, color: MUTED, size: 16 })] }),
          ...blocks,
        ],
      }],
    });
    return D.Packer.toBlob(doc);
  }

  async function download(format, report) {
    const make = { pdf, xlsx: excel, docx: word }[format];
    if (!make) throw new Error("Unknown format " + format);
    const blob = await make(report);
    save(blob, format);
    return blob;
  }
  window.DesinfoExport = { download };
})();
