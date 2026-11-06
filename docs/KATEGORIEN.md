# Wer fällt in welchen Filter? (Entwurf zur Freigabe)

Dieses Dokument legt für **jeden Filter** fest, nach welcher Regel ein Outlet einen Wert bekommt.
Grundsätze (aus dem Briefing, K4):

- Ein Wert wird **nur vergeben, wenn eine Quelle es belegt**. Es wird nichts geraten.
- Bei jedem Wert wird gespeichert, **woher** er kommt (`method` + `source`). Die Website zeigt das als Tooltip.
- Widersprechen sich zwei Quellen, gewinnt die Methode, die weiter oben steht:
  `override` (deine Korrektur) → `source_field` (Quelle sagt es direkt) → `membership` (Mitglied eines Netzwerks) → `website_check` → `keyword` → `default`.
- Gibt es keinen Beleg, steht dort ausdrücklich **`unknown`** (bei Themen: `general_news`).
- Die Regeln selbst stehen später lesbar in `config/rules.yaml`. Dieses Dokument ist die Vorlage dafür.

Abkürzungen der Quellen: **WD** = Wikidata · **MC** = Media Cloud · **RB** = Radio Browser · **IPTV** = iptv-org ·
**WP** = Wikipedia-Liste · **Web** = Website-Check (prüft die Startseite des Outlets, kommt in Schritt 4).

> Zahlen in eckigen Klammern **[…]** trage ich ein, sobald der erste Datenabruf durchgelaufen ist.

---

## 0. Wer kommt überhaupt rein?

Ein Eintrag wird aufgenommen, wenn **alle** Bedingungen zutreffen:

1. **Land:** Sitzland ist einer der 193 Mitgliedstaaten oder ein Beobachterstaat. Sonst raus (z. B. Hongkong, Taiwan, Kosovo).
   Ausnahme: internationale Outlets, deren Sitzland erlaubt ist (BBC → GBR) bleiben drin, auch wenn sie anderswo gehört werden.
2. **Existiert noch:** Nicht als eingestellt markiert (WD „aufgelöst“/„eingestellt“-Datum, IPTV `closed`).
   Ein Radiostream, der gerade nicht läuft, ist **kein** Grund zum Entfernen (Streams fallen oft kurz aus).
3. **Ist ein Medium mit Informationsangebot.** → **Frage 1** unten (Musik-, Sport-, Unterhaltungssender).
4. Kein Erwachsenen-Inhalt (IPTV `is_nsfw`).

---

## 1. Organisation type (*Wer* ist das?): genau **ein** Wert pro Outlet

| Wert | Regel (in dieser Reihenfolge geprüft, der erste Treffer gilt) | Belege |
|---|---|---|
| **Fact-checking organisation** | IFCN-Unterzeichner **oder** EFCSN-Mitglied **oder** WD-Klasse „Faktencheck-Organisation/-Website“ **oder** WP-Liste der Faktencheck-Websites | membership / source_field |
| **News agency** | WD-Klasse „news agency“ (oder Unterklasse) **oder** WP „List of news agencies“ | source_field |
| **Public service broadcaster** | Mitglied einer Rundfunkunion (EBU, ABU, AUB, ASBU, CBU, OTI, PIBA) als Vollmitglied **oder** WD-Klasse „public broadcaster“, **und** nicht „state-controlled“ nach Abschnitt 3 → **Frage 3** | membership / source_field |
| **Community media** | WD-Klasse „community radio/TV“ **oder** Mitglied eines Community-Radio-Verbands **oder** RB-Tag `community` *(nur zusammen mit einer zweiten Quelle, weil RB-Tags von Nutzern frei eingegeben werden)* | source_field / membership |
| **News outlet** | alle anderen aufgenommenen Medien | default |

Später (Phase 2) kommen NGO, Network, Academic, Creator dazu. Das Datenmodell hat dafür schon Platz.

→ **Frage 2:** Nur ein Typ pro Outlet (mein Vorschlag) oder mehrere?

---

## 2. Channel (*Wo* veröffentlichen sie?): **mehrere** Werte möglich

| Kanal | Regel | Belege |
|---|---|---|
| **TV** | WD-Klasse Fernsehsender/-kanal **oder** Eintrag in IPTV | source_field |
| **Radio** | WD-Klasse Radiosender **oder** Eintrag in RB | source_field |
| **Print** | WD-Klasse Zeitung/Zeitschrift, **außer** WD sagt „Online-Zeitung“ (reine Online-Zeitungen sind *nicht* Print) | source_field |
| **Website** | hat eine eigene Website (WD, MC, RB, IPTV) – nach dem Website-Check nur, wenn sie antwortet | source_field / website_check |
| **Podcast** | Podcast-Feed auf der Website gefunden **oder** Treffer im Podcast Index (→ **Frage 6**) **oder** WD-Klasse Podcast | website_check / source_field |
| **Social media** | mindestens ein Konto (YouTube, Facebook, Instagram, TikTok, X, WhatsApp, Telegram) in WD **oder** als Link auf der Startseite | source_field / website_check |
| **Newsletter** | Newsletter-Anmeldung auf der Startseite gefunden | website_check |

Material → Kanal (aus `categories.yaml`): Video → TV, Website, Social · Audio → Radio, Podcast · Photo/Graphic → Print, Website, Social · Text → Print, Website, Newsletter **+ alle News agencies**.

---

## 3. Ownership (*Wem* gehört es?): genau **ein** Wert, immer mit Quelle

| Wert | Regel | Belege |
|---|---|---|
| **State-controlled** | Eigentümer/Mutterorganisation in WD ist eine Regierung, ein Ministerium, ein Staat, eine Partei oder das Militär **oder** Media Ownership Monitor sagt staatlich **oder** öffentlicher Sender in einem Land mit RSF-Kategorie „very serious situation“ → **Frage 3** | source_field / rule |
| **Public service** | öffentlicher Rundfunk (siehe Org-Typ) und nicht state-controlled | membership / source_field |
| **Community / non-profit** | Community media **oder** Eigentümer in WD ist Stiftung, Verein, Genossenschaft, NGO | source_field |
| **Private** | Eigentümer in WD ist ein Unternehmen oder eine Person **oder** Media Ownership Monitor sagt privat | source_field |
| **Unknown** | kein Beleg | default |

Hinweis: Zum Eigentümer gibt es nur für einen Teil der Outlets offene Daten [Anteil mit WD-Eigentümer: …]. „Unknown“ wird also häufig sein.
Die Checkbox „Hide state-controlled“ blendet nur aus, was belegt staatlich ist. „Unknown“ bleibt sichtbar.

---

## 4. Land, Scope und Publikum

**Sitzland (`country_base`):** WD „Land“ → sonst MC-Länder-Sammlung → sonst RB/IPTV-Ländercode. Widersprechen sich die Quellen, gilt WD und der Fall kommt in die Widerspruchsliste.

**Scope:** genau ein Wert

| Wert | Regel |
|---|---|
| **International** | sendet/erscheint in vielen Ländern: IPTV-Sendegebiet umfasst mehrere Regionen/„international“ **oder** WD-Wirkungsbereich „Welt“ **oder** steht in der Liste internationaler Sender (`overrides.csv`, z. B. BBC World Service, RFI, DW, Al Jazeera) |
| **Regional (multi-country)** | Sendegebiet/Wirkungsbereich umfasst 2+ Länder, aber nicht weltweit |
| **National** | MC-Sammlung „National“ **oder** WD-Wirkungsbereich = das Land **oder** IPTV-Sendegebiet = das Land |
| **Local** | MC-Sammlung „State & Local“ **oder** WD-Wirkungsbereich = Stadt/Region **oder** IPTV-Sendegebiet = Teilgebiet |
| **Unknown** | kein Beleg → **Frage 4** |

**Publikum (`audience_countries`):** Sitzland (`home_country`) + Länder aus dem IPTV-Sendegebiet, aus MC-Sammlungen anderer Länder und aus Sprachdiensten (`language_service`) + Korrekturliste (`manual`). Bei jedem Land steht der Grund.

---

## 5. Sprachen: **mehrere** möglich

WD „Sprache des Werks“ · RB-Sprachcodes · IPTV-Sprachen der Sendung · MC-Sprache · Web: Sprache der Startseite.
Alles wird auf ISO-639-3-Codes aus `languages.csv` gebracht. Kein Beleg → **keine Sprache**. Solche Outlets erscheinen nur mit der Checkbox „Also show outlets without language information“.

---

## 6. Topics: **mehrere**, schließen nie aus, nur Reihenfolge

| Thema | Wird vergeben bei … |
|---|---|
| Fact-checking & misinformation | Org-Typ Fact-checker |
| Climate action | Covering-Climate-Now-Partner · WD-Themengebiet Klima/Umwelt · IPTV/RB-Kategorie dazu |
| Business & economy | WD-Genre/Themengebiet Wirtschaft · IPTV-Kategorie `business` · RB-Tag `business`/`economy` |
| Science | WD-Themengebiet Wissenschaft · IPTV `science` |
| Culture | IPTV `culture` · WD-Genre Kultur |
| Religion | IPTV `religious` · RB-Tags wie `religious`, `christian`, `islamic` · WD-Genre religiöses Programm |
| Sports | IPTV `sports` · RB-Tag `sports` · WD-Genre Sport |
| Children & youth | IPTV `kids` · WD-Genre Kinderprogramm |
| Quality education (SDG 4) | IPTV `education` · WD-Genre Bildung |
| Community & local | Org-Typ Community media oder Scope Local |
| Human rights, Migration, Gender equality, Health … | **nur** über Netzwerk-Mitgliedschaft, WD-Themengebiet oder eindeutige Schlagwörter im Namen (z. B. „Health“) – das wird selten sein |
| General news | Standard, wenn kein anderes Thema belegt ist (IPTV `news`, RB `news`, WD „news“ zählen auch hierzu) |

Ehrlicher Hinweis: Für die meisten SDG-Themen gibt es **keine offene Quelle auf Outlet-Ebene**. Die meisten Outlets werden „General news“ sein. Das ist korrekt, weil sie Generalisten sind. Genauer wird es nur mit dem Website-Check („About“-Text) oder mit der optionalen KI-Einordnung (Schritt 5b).

Die genaue Liste „Quell-Kategorie → unser Thema“ erstelle ich aus den **tatsächlich vorkommenden** Kategorien und Tags [nach dem Abruf].

---

## 7. UN profile: **mehrere**, nur Reihenfolge

| Profil | Regel | Offene Quelle vorhanden? |
|---|---|---|
| Existing UN relationship | SDG-Media-Compact-Mitglied (später: UN-News-Partner, UNIC – nur intern) | ✅ |
| Fact-checking (IFCN signatory) | IFCN-Liste | ✅ |
| Public service mandate | Org-Typ Public service broadcaster | ✅ |
| Reaches underserved audiences | Community media **oder** Sprache ist keine der 9 Button-Sprachen und keine Amtssprache des Landes | ✅ teilweise |
| Multilingual | 2 oder mehr belegte Sprachen | ✅ |
| Storytelling & documentary | IPTV `documentary` · WD-Genre Dokumentation | ✅ teilweise |
| Educational / explanatory | IPTV `education` · WD-Genre Bildung | ✅ teilweise |
| Youth audience | IPTV `kids` / WD Jugendprogramm | ✅ teilweise |
| Solutions / constructive journalism | Mitglied eines Netzwerks für konstruktiven Journalismus (falls Liste verfügbar) | ⚠️ kaum |
| Development journalism | GFMD-Mitglied / Earth Journalism Network | ⚠️ kaum |
| Open to partner content | keine offene Quelle | ❌ nur per Korrektur oder KI |

---

## 8. Checkboxen und Größe

| Checkbox | Regel |
|---|---|
| Only verified (2+ sources) | in mindestens **2 voneinander unabhängigen** Quellen gefunden (WD, MC, RB, IPTV, WP-Listen, Netzwerklisten zählen je einzeln) |
| Hide state-controlled | blendet Ownership = State-controlled aus |
| Has social media | Kanal Social media vorhanden |
| Has public contact | Redaktions-/Organisationsadresse (WD „E-Mail“ oder Kontaktseite auf der Website), **keine** Adressen von Personen |
| Hide outlets whose website did not answer | Website-Check der letzten Prüfung fehlgeschlagen |
| Only new | zum ersten Mal gefunden vor weniger als 4 Monaten |

**Größe (Top 10/50 pro Land):** Prominenz = Anzahl Wikipedia-Sprachversionen (WD) + Anzahl Quellen. Rang innerhalb des Sitzlandes.

---

## Entscheidungen (05.11.2026, von der Projektleitung bestätigt)

1. **Welche Medien rein?** Nur Medien mit Informationsangebot.
   - **Rein** (Quell-Kategorie): news, general, public, legislative, education, documentary, culture, science, business, kids, religious, weather, **sports**.
     Ohne Kategorie: nur wenn eine zweite Quelle das Outlet als Medium bestätigt.
   - **Raus:** shop, music, movies, series, comedy, animation, classic, relax, cooking, travel, auto, outdoor, lifestyle, entertainment, family, interactive, xxx.
   - Für Radio gilt dasselbe sinngemäß (RB-Tags); die genaue Tag-Liste folgt nach dem Abruf.
2. **Genau ein Organisationstyp** pro Outlet, Reihenfolge wie in Abschnitt 1.
3. **State-controlled / Public service** wie in Abschnitt 3. Nichts wird deswegen ausgeblendet, nur markiert (Checkbox „Hide state-controlled“).
4. **Scope ohne Beleg = unknown** (nicht automatisch National).
5. **Podcast Index:** kostenloser Schlüssel wird später (Schritt 4) angelegt. Bis dahin Podcasts nur über WD und Website-Check.
6. **Rundfunkunionen:** Wo die Websites automatische Abrufe sperren (EBU, ABU), werden die Mitgliederlisten aus Wikipedia genommen.
   **Kontakte:** nur Adressen der Organisation (z. B. newsroom@…), keine persönlichen Adressen.
   **SDG Media Compact:** öffentliche Liste; die Projektleitung versucht, die interne Liste über DGC Campaigns zu bekommen.

### Notizen aus dem Datenabruf (05.11.2026)
- **ABYZ**: Seite trägt „Copyright 2000-2022 ABYZ Web Links Inc.“, keine offene Lizenz → bleibt Reserve, wird nicht abgerufen.
- **IFCN**: Liste wird per Programmschnittstelle geladen; diese Adresse wird jetzt direkt abgerufen.
- **Covering Climate Now**: Verzeichnis ist eine Airtable-Tabelle ohne offene Schnittstelle → einmalig als CSV herunterladen (Snapshot in `raw/manual/`).
- **Staatsmedien-Liste (Wikipedia)**: Hauptquelle dort ist der „State Media Monitor“ (Media and Journalism Research Center). Prüfen, ob dessen Liste direkt nutzbar ist – sie unterscheidet staatlich kontrolliert / unabhängig öffentlich.

### Entscheidungen 06.11.2026
- **RSF entscheidet nicht mehr über „state-controlled“.** Nur der State Media Monitor (über die Wikipedia-Liste der Staatsmedien) stuft öffentliche Sender als staatlich kontrolliert ein. Unabhängige öffentlich-rechtliche Sender sind nie „state-controlled“.
- **Pressefreiheit als Länder-Info** auf jeder Karte, wie im Atlas: RSF-Rang/Punktzahl, Freedom House (politische Freiheit, Internetfreiheit), jeweils mit Quelle. Daten direkt aus dem öffentlichen Atlas.
- **„Unknown“ wird erklärt:** „No open source says who owns this outlet. This does not mean it is independent or state-run.“
- **Ownership-Lücken:** (a) Eigentümernamen aus iptv-org abgleichen – jetzt; (c) Website-Check – nach 4d, zuerst Top 50 pro Land, ohne KI; (b) Media Ownership Monitor – vorerst nicht (wenige Länder, Lizenz CC BY-ND).
- **„Only show topic matches“** (Schalter, Standard aus) und **„Also show outlets without this information“** bei allen harten Filtern.
- **Filter „Member of“** (SDG Media Compact, Rundfunkunionen, Faktenchecker-Netzwerke).
- **EBU-Vollmitglieder mit privatem Eigentümer** (ITV, TV 2) erscheinen unter beiden Typen.

