# Third-party files used by the export (PDF, Excel, Word)

Stored in the repository (no outside service at runtime) and loaded only when someone exports.
Versions are fixed; each was published at least two weeks before it was added (06.11.2026).

| File | Library | Version | Published | Licence | Licence file |
|---|---|---|---|---|---|
| `jspdf-4.2.1.umd.min.js` | jsPDF | 4.2.1 | 2026-03-17 | MIT | `licenses/jspdf.txt` |
| `jspdf-autotable-5.0.8.min.js` | jspdf-autotable | 5.0.8 | 2026-05-17 | MIT | `licenses/jspdf-autotable.txt` |
| `exceljs-4.4.0.min.js` | ExcelJS | 4.4.0 | 2023-10-19 | MIT | `licenses/exceljs.txt` |
| `docx-9.7.1.iife.js` | docx | 9.7.1 | 2026-05-27 | MIT | `licenses/docx.txt` |
| `NotoSans-Regular.ttf`, `NotoSans-Bold.ttf` | Noto Sans (notofonts/latin-greek-cyrillic) | as of 06.11.2026 | – | SIL Open Font License 1.1 | `licenses/noto-sans-OFL.txt` |

The fonts are embedded in the PDF so that accented and non-English Latin, Greek and Cyrillic
names print correctly. Limit: Arabic and Chinese names may not render in the PDF; Excel and Word are fine.
