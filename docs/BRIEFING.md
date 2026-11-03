# BRIEFING: UN Partner Finder v2 – kompletter Neuaufbau

> Dieses Briefing ist die vollständige Grundlage für den Bau. Bitte zuerst komplett lesen. Ergänzende Dokumente im Projekt „UN Partnership Unit“: `claude/partner-finder-v2-plan.md` (Plan & Datenwörterbuch) und `claude/partner-finder-auto-update.md` (automatische Aktualisierung). Bei Widersprüchen gilt dieses Briefing.

---

## A. Wer ich bin und wie du mit mir arbeitest

- Ich arbeite in der UN-Unit **DGC Partnerships** und baue dieses Tool für meine Unit.
- **Ich habe bisher keine Erfahrung mit Web-Entwicklung und mache das zum ersten Mal.**
- So arbeiten wir:
  1. **Erklär jeden Schritt einfach**, ohne Fachjargon, oder erklär den Fachbegriff, wenn er nötig ist.
  2. **Immer nur einen Schritt aus dem Aktionsplan (Abschnitt N) pro Sitzung.** Erst weitermachen, wenn das „Fertig wenn“ erfüllt ist und ich es bestätigt habe.
  3. Wenn ich selbst etwas klicken muss (GitHub, Cloudflare), **führ mich Klick für Klick**. Sag mir, was ich sehen sollte, und frag nach einem Screenshot, wenn ich hänge.
  4. **Frag nach, bevor du größere Entscheidungen triffst**, die nicht in diesem Briefing stehen. Kleine technische Entscheidungen triffst du selbst und nennst sie kurz.
  5. **Alle erlaubten Werte (Kategorien, Länder, Sprachen …) gehören in Konfigurationsdateien, nicht in den Code.** Ich will sie später selbst lesen und ändern können.
  6. Halte es **einfach und wartbar**: statische Website, keine Datenbank, kein eigener Server, keine unnötigen Frameworks.
  7. Am Ende jeder Sitzung: kurze Zusammenfassung, was gemacht wurde, was ich prüfen soll und was der nächste Schritt ist.

---

## B. Was das Tool ist und wofür

- Ein **Partnership Finding Tool für die UN**. Die Oberfläche ist **komplett auf Englisch**.
- Erstmal eine **Website**, die langfristig immer weiter ausgebaut wird.
- **Grundidee / Anwendungsfall:** Jemand aus der Partnership Unit hat ein Medienprodukt, z. B. **ein Video zu Frauenrechten in der DR Kongo**, und möchte dafür passende Abnehmer weltweit finden.
- Abnehmer sind z. B. News Outlets, NGOs usw. **Version 1 = nur Medien.** NGOs, Netzwerke, Universitäten und Creator kommen später. **Das Datenmodell und die Filter müssen jetzt schon so gebaut sein, dass diese später nur ein neuer Organisationstyp sind**, ohne Umbau.
- Die erste Liste ist eine **Open-Source-Liste** aus offenen Verzeichnissen und öffentlichen Netzwerklisten.

---

## C. Rahmenbedingungen (entschieden)

| Thema | Entscheidung |
|---|---|
| Nutzer | **Nur meine Unit (DGC Partnerships)**, intern |
| Kontaktdaten | **dürfen enthalten sein**, deshalb dürfen Seite **und** Daten nicht öffentlich sein |
| Vorgaben | internes Projekt, keine UN-Vorgaben zu Hosting/Branding/Datenschutz |
| Form | **eigenständige Seite**, aber **in den bestehenden Atlas eingebunden** (Atlas hat Tabs: World Map, Partner Finder, Misinformation Monitor, Data & sources) |
| Hosting | wie der Atlas: **GitHub → Cloudflare Pages** |
| Repo | **eigenes, privates Repo** für den Partner Finder (das Atlas-Repo `hannascoder/Partnership-DGC-Atlas-Expansion` ist öffentlich, dort dürfen keine Daten mit Kontakten liegen) |
| Zugang | **Cloudflare Access**: Login nur für freigegebene E-Mail-Adressen |
| Altdaten | **Alles Alte wird verworfen**: alte Excel-Listen, alter UN-fit-Score, alte Rankings, alte Top-10-Handrecherche. Alles wird **frisch aus den Quellen** gesammelt und nach den neuen Regeln eingeordnet. |
| Datenbasis | **keine Excel als Grundlage.** Daten kommen aus offenen Quellen, **aktualisieren sich automatisch** (Abschnitt K). Excel/CSV nur noch als Export. |
| Umfang | **Alle Outlets** kommen rein. Eingegrenzt wird über Filter (inkl. Top 10 / Top 50 pro Land). |
| Zeit | keine Deadline, viel Zeit, also lieber gründlich und sauber |

---

## D. Länder & Geografie

- **Nur die 193 UN-Mitgliedstaaten.**
- **Beobachterstaaten (Palestine, Holy See)** werden **zusätzlich als eigene, gekennzeichnete Gruppe** geführt.
- Outlets aus **Gebieten, die keine Mitgliedstaaten sind** (z. B. Hongkong, Taiwan, Kosovo, Puerto Rico), werden **ausgeblendet und nicht einem Staat zugeordnet**, weil das politisch heikel wäre.
- **Regionen** nach dem **UN-Schema M49** (Africa, Americas, Asia, Europe, Oceania + Subregionen wie „Middle Africa“), aus dem Land abgeleitet.
- **Scope:** Local · National · Regional (multi-country) · International.
- **SUPER WICHTIG: Sitz vs. Publikum.** Jedes Outlet hat ein **Sitzland** (`country_base`) **und** eine Liste der **Länder, die es erreicht** (`audience_countries`). Das muss **klar sichtbar und filterbar** sein.
  - Standard: Das Outlet erreicht sein Sitzland.
  - Internationale Sender (BBC-Sprachdienste/BBC Afrique, RFI, DW, VOA, Al Jazeera, CGTN …) bekommen ihre Zielländer über Sprachdienste bzw. die Korrekturliste.
  - Bei jedem Wert wird gespeichert, **warum** (`home_country`, `language_service`, `manual`).
  - Beispiel: Die Suche „DR Congo“ muss auch Sender finden, die im Kongo gehört werden, aber woanders sitzen.
  - In der Oberfläche: Checkbox „Include outlets that **reach** this country“ (Standard **an**). Die Ergebniskarte zeigt „Based in: … · Reaches: …“.

---

## E. Sprachen

- **9 Sprachen als Buttons:**
  - die 6 offiziellen UN-Sprachen: **Arabic, Chinese (Mandarin), English, French, Russian, Spanish**
  - zusätzliche UN-News-Sprachen: **Hindi, Portuguese, Kiswahili (Swahili)**
- Dazu ein **Dropdown „Other language“** für alle anderen Sprachen.
- Dazu eine **Checkbox „Also show outlets without language information“** (Standard **aus**).
- Ist keine Sprache gewählt, werden alle angezeigt.

---

## F. „My material“: was habe ich?

- **Suchleiste oben** (siehe M) **und** Buttons zum Anklicken: **Video · Audio · Photo · Text · Graphic/Infographic**
- **Podcast ist kein Material, sondern ein Kanal.** Wer Audio hat, findet Radio **und** Podcasts.
- Das Material wird **automatisch in passende Kanäle übersetzt**:
  - Video → TV, Website, Social media
  - Audio → Radio, Podcast
  - Photo / Graphic → Print, Website, Social media
  - Text → Print, Website, News agency, Newsletter
- Für später vormerken: Länge (Kurzclip vs. Doku), Untertitel vorhanden, Lizenz (free to republish).

---

## G. Channel, Organisationstyp, Ownership: klar getrennt

Wichtig: Diese drei Fragen waren in der alten Version vermischt (z. B. stand „News agency“ unter Channel). Sie werden **drei getrennte Filter**:

| Filter | Frage | Werte |
|---|---|---|
| **Organisation type** | *Wer* ist das? | v1: News outlet · News agency · Public service broadcaster · Community media · Fact-checking organisation. Später: NGO / civil society · Network / association · Academic / research · Creator / influencer |
| **Channel** | *Wo* veröffentlichen sie? | TV · Radio · Print · Website · Podcast · Social media · Newsletter |
| **Ownership** | *Wem* gehört es? | Public service · Private · State-controlled · Community / non-profit · Unknown |

- **Social media** ist aufklappbar: YouTube, Facebook, Instagram, TikTok, X, WhatsApp, Telegram (jeweils Links).
- **State-controlled** wird neutral als Ownership-Wert geführt, **immer mit Quellenangabe** (z. B. „per RSF / Media Ownership Monitor“), ohne wertendes Design.

---

## H. Themen (Topics): Mehrfachauswahl, schließen NICHT aus

- Themen sind sehr wichtig, aber **viele Outlets sind Generalisten. Themen dürfen deshalb nicht ausschließen**, sie bestimmen nur die **Reihenfolge** (Abschnitt L).
- Gruppiert nach den **5 Ps der Agenda 2030**, mit sichtbarer SDG-Nummer:

**People**
- Poverty (SDG 1)
- Hunger & food (SDG 2)
- Health & well-being (SDG 3)
- Quality education (SDG 4)
- Gender equality (SDG 5)

**Planet**
- Clean water & sanitation (SDG 6)
- Responsible consumption & production (SDG 12)
- Climate action (SDG 13)
- Life below water (SDG 14)
- Life on land (SDG 15)

**Prosperity**
- Affordable & clean energy (SDG 7)
- Decent work & economic growth (SDG 8)
- Industry, innovation & infrastructure (SDG 9)
- Reduced inequalities (SDG 10)
- Sustainable cities & communities (SDG 11)

**Peace**
- Peace, justice & strong institutions (SDG 16)

**Partnership**
- Partnerships for the goals (SDG 17)

**Beats & audiences** (Themen außerhalb der SDGs)
- aus meiner ursprünglichen Liste: General news / no specific focus · Fact-checking & misinformation · Science · Business & economy · Culture · Religion · Community & local · Humanitarian aid
- ergänzt: Human rights · Migration & refugees · Conflict & security · Technology, digital & AI · Agriculture & rural · Disasters & emergencies · Children & youth · Indigenous peoples · Disability & inclusion · Media freedom & journalism · Elections & governance · Sports · Diaspora

**Bewusste Änderungen an meiner ursprünglichen Liste:**
- „Education“ → in SDG 4 aufgegangen (keine Dopplung)
- „Development & SDGs“ → entfällt, die SDGs selbst decken das ab
- „UN general“ → kein Thema, sondern beim UN-Profil („Existing UN relationship“)
- „Missinformation“ → „Fact-checking & misinformation“
- „General information no specifics“ → „General news“. Das ist der **Standardwert**, wenn sonst nichts erkannt wird.

Jedes Thema zeigt, **woher es kommt** (Tooltip, z. B. „via Covering Climate Now“).

---

## I. UN profile: Mehrfachauswahl, beeinflusst die Reihenfolge

Beschreibt, ob ein Outlet besonders gut zur UN passt. Meine ursprünglichen drei plus Ergänzungen:

- Educational / explanatory *(von mir)*
- Solutions / constructive journalism *(von mir)*
- Development journalism *(von mir)*
- Open to partner content / republishes third-party content *(wertvollster Wert: „Nehmen die mein Video?“)*
- Existing UN relationship (UN News partner, UNIC, SDG Media Compact)
- Public service mandate
- Storytelling & documentary
- Fact-checking (IFCN signatory)
- Reaches underserved audiences (ländlich, Community Radio, Minderheitensprachen)
- Youth audience
- Multilingual

---

## J. Weitere Filter & Checkboxen

- **Size:** ◉ All · ○ Top 50 per country · ○ Top 10 per country
  - „Top“ heißt **die bekanntesten** („prominence“), nicht die größten, weil es kaum Reichweitendaten gibt.
  - Prominenz = Anzahl der Wikipedia-Sprachversionen (aus Wikidata) + Anzahl unabhängiger Quellen, in denen das Outlet vorkommt. Tooltip auf der Seite erklärt das.
- **Checkboxen:**
  - Only verified (2+ sources)
  - Hide state-controlled
  - Has social media
  - Has public contact (nur Redaktions-/Organisationsadressen)
  - Hide outlets whose website did not answer
  - Only new (found in the last 4 months)
- **Kein UN-fit-Score**, weder als Filter noch als Zahl.

---

## K. Datenbasis: Quellen, Kategorisierung, automatische Aktualisierung

### K1. Architektur
```
Quellen → fetch/ (1 Skript pro Quelle, Rohdaten in raw/)
       → normalize/ (gleiches Format)
       → merge/ (Dubletten zusammenführen, nur 193+2 Länder)
       → classify/ (Regeln vergeben Kategorien)
       → overrides.csv (meine Handkorrekturen, gewinnen immer)
       → validate/ (Prüfungen + Berichte)
       → site/data/outlets.json  ← die Website liest NUR diese Datei
```
Die Website holt **nicht live** von fremden Seiten. Sie filtert die fertige JSON-Datei im Browser.

### K2. Quellen
| Quelle | Abruf | Automatisch? | Liefert v. a. |
|---|---|---|---|
| Wikidata | SPARQL-API | ja | Name, Land, Sprache, Website, Inhaber, Typ, Social, Wikipedia-Sprachversionen |
| Wikipedia-Listen | API | ja | Namen, Land |
| Radio Browser | API | ja | Radio, Sprache, Land, Website, Tags |
| iptv-org | GitHub-Dateien | ja | TV, Land, Sprache, Kategorien |
| ABYZ | keine API | nein: einmal frisch sammeln, Snapshot in `raw/manual/`, alle 6–12 Monate erneuern. **Nutzungsbedingungen prüfen** | Print/Online, Land, Stadt |
| Netzwerk-/Mitgliederlisten: GFMD, SDG Media Compact, PINA, EJN, IFCN, GIJN, OCCRP, Covering Climate Now, Rundfunkunionen, Community-Radio-Listen | HTML | halbautomatisch (Snapshot) | Themen, UN-Profil, Org-Typ |
| Ownership: RSF, Media Ownership Monitor o. ä. | Snapshot | halbautomatisch | Ownership / state-controlled |
| Website-Check | eigenes Skript | ja | erreichbar? Social-Links, RSS/Podcast, Newsletter, Kontaktseite, Seitensprache, „About“-Text |
| `overrides.csv` | ich | – | Korrekturen, Zielländer internationaler Sender |

### K3. Datenfelder (ein Eintrag = eine Organisation)
`id` (stabil!) · `name`, `name_alt` · `website` · `org_type` · `ownership` (+ Quelle) · `channels` · `social` · `country_base` · `region`, `subregion` · `city` · `scope` · `audience_countries` (+ `audience_basis`) · `languages` (ISO 639) · `topics` · `un_profile` · `sources` · `verified` · `prominence` · `rank_in_country` (→ top10/top50) · `website_status` + `last_checked` · `first_seen`, `last_seen` · `contact_email`, `contact_page`

**Jeder eingeordnete Wert wird mit Herkunft gespeichert:** `{value, method, source}`.

### K4. Wie kategorisiert wird (Rangfolge: höhere Methode gewinnt bei Widerspruch)
1. **override:** meine Korrekturliste
2. **source_field:** Die Quelle sagt es direkt (Radio Browser → Radio; Wikidata „newspaper“ → Print)
3. **membership:** Mitgliedschaft (IFCN → Fact-checker + Fact-checking; Covering Climate Now → Climate; Rundfunkunion → Public service broadcaster)
4. **website_check:** auf der Website gefunden (Podcast-Feed, Social-Links, Newsletter …)
5. **ai_classification** (optional, Entscheidung erst nach dem Coverage-Bericht): KI liest den „About“-Text und wählt **nur aus den festen Listen**, mit kurzer Begründung. Zuerst nur Top 50 pro Land (~10.000), Stichprobe von 100 prüfe ich von Hand. Ergebnisse werden gecacht.
6. **keyword:** eindeutige Schlagwörter in Name/Beschreibung
7. **default:** Topic `general_news`, Ownership `unknown`, Audience = Sitzland

Regeln stehen lesbar in `config/rules.yaml`, z. B.:
```yaml
- if: { member_of: covering-climate-now }
  add: { topics: [climate] }
```

### K5. Qualitätskontrolle nach jedem Lauf
- **Coverage-Bericht:** Anteil der Outlets mit Wert pro Feld, gesamt und pro Land
- **Stichprobe:** 30 zufällige Outlets zum Gegenlesen
- **Widerspruchsliste:** wo sich Methoden widersprechen
- **Änderungsbericht:** neu / verschwunden / geändert

### K6. Automatische Aktualisierung (GitHub Actions)
- Zeitplan: Pipeline **monatlich**, Website-Check **wöchentlich** (rotierend, jeweils ein Teil), dazu ein Knopf zum manuellen Start
- Ergebnis wird ins private Repo gespeichert, danach veröffentlicht Cloudflare automatisch neu
- **Stabile IDs**, damit Korrekturen, `first_seen` und KI-Ergebnisse erhalten bleiben
- **Nicht sofort löschen:** Ein verschwundenes Outlet wird markiert und erst nach 3 Läufen ausgeblendet
- **Quelle fällt aus:** letzte gute Version dieser Quelle nehmen und im Bericht vermerken
- **Sicherheitsbremse:** nicht veröffentlichen, wenn die Gesamtzahl um > 10 % fällt, unerlaubte Länder auftauchen oder Pflichtfelder fehlen. Dann bleibt die alte Version online.
- **Fehler-Mail ist Pflicht.** Der Lauf des Misinformation Monitors ist seit dem 16.09.2026 unbemerkt kaputt, das darf hier nicht passieren.
- Teure Schritte (Website-Check, KI) **nur für neue/geänderte Outlets + rotierenden Teil**, um unter 6 h pro Lauf und im Freikontingent zu bleiben

### K7. Repo-Struktur
```
config/            categories.yaml, rules.yaml, countries.csv (193+2, M49), languages.csv
overrides.csv
raw/               Rohdaten der Quellen;  raw/manual/ = Snapshots ohne API
cache/             Website-Check, KI-Ergebnisse, first_seen/last_seen
pipeline/          fetch/, normalize/, merge/, classify/, validate/, run_all.py
reports/           Coverage, Stichprobe, Widersprüche, Änderungen
site/              die Website;  site/data/outlets.json
.github/workflows/ update.yml
```

---

## L. Filter-Logik & Sortierung

- **Harte Filter** (müssen zutreffen): Suche, Material/Channel, Sprache, Region/Land/Scope, Organisation type, Ownership, Size, alle Checkboxen
- **Weiche Filter** (bestimmen nur die Reihenfolge): **Topics** und **UN profile**
- **Innerhalb eines Filters ODER** (Radio *oder* TV), **zwischen Filtern UND** (Radio/TV *und* DR Congo)
- **Sortierung** per Dropdown:
  - **Best match:** Standard, sobald Filter aktiv sind. Zählt, wie viele gewählte Themen und UN-Profile zutreffen; bei Gleichstand Prominenz, dann A–Z.
  - **A–Z:** Standard, wenn **kein Filter** gesetzt ist, dann einfach alle Medien alphabetisch
  - **Country**
- **Jede Ergebniskarte zeigt „Matches: …“**, also warum sie oben steht.

---

## M. Oberfläche

**Suchleiste oben**
- v1: Stichwortsuche in Name, Stadt, Inhaber, Netzwerk
- Später (Backlog): „Describe your product“, z. B. „video on women's rights in DR Congo, French“. Eine KI schlägt daraus Filter vor. Im Design jetzt schon Platz dafür vormerken.

**Filterbereich** in dieser Reihenfolge: Search · My material · Language (+ Other language, + Checkbox ohne Sprachinfo) · Region / Country / Scope (+ Checkbox „reach“) · Organisation type · Channel · Ownership · Size · Topics (5 Ps + Beats) · UN profile · Checkboxen · Sort

**Ergebnisse**
- Zählerzeile, z. B. „X outlets in Y countries · Z verified“
- Buttons „Reset filters“ und „Add all to export list“
- Karte pro Outlet: Name · Based in + Reaches · Sprachen · Kanäle · Typ · Ownership · Themen · UN-Profil · Kontakt · Social-Links · Quellen · last checked · verified-Badge · „Matches: …“
- Detailansicht beim Klick
- **Shortlist / Export** als Excel/CSV
- Link „Report an error / suggest an outlet“ (v1: einfaches Formular oder mailto)
- **Hinweis zur Aktualität**, z. B. „data updated … · page built …“

**Allgemein:** Englisch, gut auf dem Handy nutzbar, barrierearm (WCAG-Grundlagen), passend zum Atlas-Design.

**Inspiration:** Die bisherige Partner-Finder-Seite im Atlas (Screenshot vom 03.11.2026) ist nur Inspiration und wird **komplett neu gebaut**. Übernehmen: Zählerzeile, Reset, Export-Liste, Aktualitätshinweis, Button-Optik der Filter. Nicht übernehmen: UN-fit-Score, Vermischung von Channel und Organisationstyp, alte Themenliste.

---

## N. Schritt-für-Schritt-Aktionsplan

Eine Sitzung pro Schritt. Weiter erst, wenn „Fertig wenn“ erfüllt ist.

| # | Schritt | Fertig wenn |
|---|---|---|
| 0 | **Repo & Zugang:** neues privates Repo (lege ich auf GitHub an), Platzhalterseite „Partner Finder – coming soon“, mit Cloudflare Pages verbinden, Cloudflare Access einrichten (nur freigegebene E-Mails), Link im Atlas | Seite im privaten Browserfenster zeigt zuerst einen Login; Repo ist „Private“ |
| 1 | **Konfiguration:** `categories.yaml`, `countries.csv` (193 + 2, M49), `languages.csv`, leere `rules.yaml`, leere `overrides.csv` | alle erlaubten Werte aus D–J stehen in Dateien |
| 2 | **Fetcher pro Quelle:** zuerst Wikidata, Radio Browser, iptv-org, dann Netzwerklisten, ABYZ, Ownership. **Stabile IDs von Anfang an** | jede Quelle läuft einzeln und speichert Rohdaten |
| 3 | **Normalisieren + Zusammenführen** | keine offensichtlichen Dubletten; 20 bekannte Outlets stimmen |
| 4 | **Klassifizieren** (Methoden 1–4, 6, 7) + Overrides für ~50 internationale Sender mit Zielländern | jedes Feld hat einen Wert oder ausdrücklich `unknown` |
| 5 | **Berichte** (Coverage, Stichprobe, Widersprüche) → ich entscheide, welche Filter in v1 sinnvoll sind und ob KI nötig ist | Entscheidung getroffen |
| 5b | *(optional)* **KI-Einordnung** für Top 50 pro Land + Stichprobe von 100 | Qualität von mir freigegeben |
| 6 | **Wireframe** der Seite (Filter, Ergebnisse, Detail, Shortlist) | Layout von mir freigegeben |
| 7 | **Website v1** mit allen Filtern, Sortierung, Export | Testfall „Video · French · Gender equality + Human rights · DR Congo“ liefert sinnvolle Treffer **inkl. internationaler Sender** |
| 8 | **In den Atlas einbinden** (Tab/Link, gleiches Design) | vom Atlas aus erreichbar |
| 9 | **Automatisieren** (GitHub Actions, Sicherheitsbremse, Fehler-Mail) | ein automatischer Lauf ist erfolgreich durchgelaufen, ein simulierter Fehler löst eine Mail aus |
| 10 | **Test mit 2–3 Kollegen** mit echten Medienprodukten | Feedback eingearbeitet |

---

## O. Backlog (später, aber beim Bauen im Kopf behalten)

- „Describe your product“: Freitext → KI schlägt Filter vor
- Weitere Organisationstypen: NGOs, Netzwerke, Universitäten, Creator
- „Similar outlets“, gespeicherte Suchen, Treffer auf der Weltkarte des Atlas
- Pitch-Tracking (angeschrieben / Antwort / veröffentlicht) oder Anbindung an Salesforce
- Reichweiten-/Publikumsdaten
- Material-Details (Länge, Untertitel, Lizenz)

---

## P. Offene Punkte

1. KI-Einordnung ja/nein → Entscheidung nach Schritt 5
2. ABYZ-Nutzungsbedingungen prüfen (vor Schritt 2)

---

**Jetzt starten mit: Schritt 0.**
