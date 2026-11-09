# Export feature: specification from the owner (06.11.2026)

**When:** after the clustering is finished (step 4 classification and the NGOs).
Until then the simple CSV export list in the preview is a placeholder and will be replaced.

---

Build an export feature for this website: users collect items (e.g. media outlets or
countries) in an "export list" and download that list as PDF, Excel or Word.
Before you change anything, read the code, tell me which page(s) and data it would apply to,
and ask me which columns the export should have. Then show me an example PDF and Excel file
built from real data for approval. Only after I approve, build it into the website.
Work on a new branch and open a pull request; document in English (README, CHANGELOG).

## Selection (two ways, both feed the same export list)
1. Single selection: every result card gets a checkbox "Export". Ticking adds the item to
   the export list, unticking removes it. Ticked cards are highlighted. If the same item is
   shown in two lists on the page, both checkboxes stay in sync.
2. Multi-selection: a button next to "Reset filters": "Add all N to export list", where N is
   the number of items that match the current filters (ALL filtered items, including those
   hidden behind "Show more"). Disabled when there are no results or all are already in the list.
- The export list is KEPT when the filters change, so items from several searches can be
  combined (e.g. first filter Kenya and add, then filter Ghana and add one more).
- Every distinct filter combination that was active when items were added is remembered.
- A sticky bar at the bottom of the page appears only when the list is not empty. It shows
  "N outlets in the export list", the filters used (one set: "Country: Kenya, Language: English";
  several sets: "(1) … · (2) …"), the buttons PDF / Excel / Word and "Clear list".
  While a file is being made the button reads "Preparing…"; on failure show a short error
  message in the bar.

## The filters in the file header
Read the active filters generically from the filter form itself (every select with a value,
every chip group with ticked chips (label = fieldset legend), every ticked checkbox, the search
text), so filters added later automatically appear in the export without code changes.

## File content
- Header on every file: UN emblem (the site's existing emblem image), "United Nations ·
  DGC Partnerships", title of the tool, then: Exported (date, e.g. "29 October 2026"),
  Data as of (data build date), Filters (all filter sets, or "None (all items)"),
  number of items (e.g. "23 outlets (17 Best UN fit, 6 By country & rank)"), and the note
  "Orientation only. Please confirm that an outlet is active before contacting it."
- One list, no item appears twice, split into clearly labelled sections with a heading and a
  one-line explanation each (in the Partner Finder: first "Best UN fit" = items with a UN
  profile, best first; then "By country & rank" = all others, country A–Z then rank).
- Columns: decide with me. Rules from the Partner Finder: no internal scores, no source lists;
  website and contact links are clickable; a "Topic" column shows only the topics that were
  filtered on (all topics if no topic filter was set); a "Notes" column for flags
  (e.g. State-controlled, Unverified, Website not reachable, New).
  Partner Finder: 16 columns since 09.11.2026 (owner added "Target audience" after "Topic").
- PDF and Word: A4 landscape, table header repeated on every page, rows never split across
  pages, footer "<Tool name> · DGC Partnerships   Page x of y".
- Excel: ONE sheet; logo and header rows on top, then a dark header row (frozen when
  scrolling, repeated when printing), section rows as merged, light-blue full-width rows,
  wrapped text, landscape print setup fitted to page width.
- File name: <tool-name>_<YYYY-MM-DD>.pdf / .xlsx / .docx
- Use the site's design colours (UN blue #009EDB, dark ink #003D6B, muted #5C6B7E).

## Technical rules
- Everything runs in the browser; no server, no outside service at runtime.
- Store the libraries in the repository (e.g. assets/vendor/), with a README listing version
  and licence, plus the licence files. Use fixed versions that are at least two weeks old.
  Load them only when someone exports.
  Proven set: jsPDF 4.2.1 + jspdf-autotable 5.0.8 (PDF), ExcelJS 4.4.0 (Excel, needed for
  styles and the logo), docx 9.7.1 (Word), all MIT; Noto Sans Regular/Bold TTF (OFL) embedded
  in the PDF so that accented and non-English Latin, Greek and Cyrillic names print correctly
  (the PDF standard fonts cannot). Note the limit: Arabic/Chinese names may not render in
  the PDF; Excel and Word are fine.
- Put the file-building code in its own file (e.g. assets/<tool>-export.js) exposing
  download(format, list) where list = { sections: [{title, note, items}], filters: [[label, value]],
  topics, updated }. The page only handles selection and calls this.
- In Word use fixed table column widths in DXA (twips), not percentages (LibreOffice and some
  Word versions ignore percentages).
- Test in a real browser (Playwright/Chromium): add all filtered, add one by hand after
  changing filters, download all three formats, untick, clear list, no console errors,
  no horizontal scrolling at 390 px width. Render the PDF pages (and Excel/Word via
  LibreOffice) to images and check them before showing them to me.
