// Prints an HTML file to PDF with the pre-installed Chromium: node tools/print_pdf.js in.html out.pdf
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [, , input, output] = process.argv;
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file://' + path.resolve(input)); await p.waitForTimeout(500);
  await p.pdf({ path: output, format: 'A4', printBackground: true, margin: { top: '14mm', bottom: '14mm', left: '14mm', right: '14mm' } });
  await b.close();
})();
