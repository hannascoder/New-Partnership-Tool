# Partner Finder – Quellen-Linkliste

Stand: 05.11.2026 · Links und Zahlen am 05.11.2026 recherchiert. ⚠️ = Adresse nicht direkt bestätigt, beim ersten Öffnen prüfen.
Priorität: **1** = Hauptquelle für Masse · **2** = wichtige Ergänzung · **3** = für Themen/UN-Profil/Ownership (wenig neue Outlets, aber wertvolle Etiketten)

---

## 0. Für ALLE Medientypen (das Grundgerüst)

| Prio | Quelle | Link | Was drin ist | Abruf |
|---|---|---|---|---|
| 1 | **Wikidata** – Abfrage-Werkzeug | https://query.wikidata.org/ | Zeitungen, Sender, Agenturen, Online-Medien mit Land, Sprache, Website, Inhaber, Typ, Social-Media-Konten (auch YouTube), Anzahl Wikipedia-Sprachversionen | API (SPARQL), automatisch |
| 1 | Wikidata – Doku zum Datenzugriff | https://www.wikidata.org/wiki/Wikidata:Data_access | Anleitung, wie man Wikidata abfragt | – |
| 2 | Wikipedia – Listen von Zeitungen | https://en.wikipedia.org/wiki/Lists_of_newspapers | Länderlisten von Zeitungen | API, automatisch |
| 2 | Wikipedia – Listen von Radiosendern | https://en.wikipedia.org/wiki/Lists_of_radio_stations | Länderlisten von Radiosendern | API, automatisch |
| 2 | Wikipedia – Listen von TV-Sendern | https://en.wikipedia.org/wiki/Lists_of_television_channels | Länderlisten von TV-Sendern | API, automatisch |

---

## 1. TEXT & BILD – Zeitungen, Magazine, Nachrichten-Websites

| Prio | Quelle | Link | Was drin ist | Abruf |
|---|---|---|---|---|
| 1 | **Media Cloud Directory** | https://www.mediacloud.org/media-cloud-directory | über 60.000 Nachrichtenquellen, Länder-Sammlungen für fast alle Länder; Länderlisten ursprünglich aus ABYZ, seitdem erweitert und bereinigt | API (kostenloser Schlüssel) |
| 1 | Media Cloud – Datensatz zum Download | https://zenodo.org/records/18189311 | Snapshot aller geografischen Sammlungen + Quellen (08.01.2026) – ohne API nutzbar | Download |
| 1 | Media Cloud – Python-Bibliothek | https://pypi.org/p/mediacloud | Werkzeug für den automatischen Abruf | – |
| 1 | Media Cloud – Feldbeschreibung | https://www.mediacloud.org/documentation/source-guide | was jedes Feld einer Quelle bedeutet | – |
| Reserve | ABYZ News Links | http://www.abyznewslinks.com/ | Zeitungen/Online nach Land und Stadt | keine API; nur falls Media Cloud Lücken hat; Nutzungsbedingungen prüfen |

---

## 2. AUDIO – Radio & Podcasts

### Radio
| Prio | Quelle | Link | Was drin ist | Abruf |
|---|---|---|---|---|
| 1 | **Radio Browser** | https://www.radio-browser.info/ | ca. 58.000 Sender, 238 Länder, 635 Sprachen; viele reine Musik-Streams → auf Tags news/talk/community filtern | API, automatisch |
| 1 | Radio Browser – API-Doku | https://api.radio-browser.info/ ⚠️ | Anleitung zur Schnittstelle | – |
| 3 | AMARC (Weltverband Community Radio) | https://en.wikipedia.org/wiki/World_Association_of_Community_Radio_Broadcasters | ca. 3.000 Mitglieder in 110 Ländern; kein offenes Mitgliederverzeichnis gefunden → über regionale Verbände/Listen | manuell |

### Podcasts
| Prio | Quelle | Link | Was drin ist | Abruf |
|---|---|---|---|---|
| 2 | **Podcast Index** | https://podcastindex.org/ | offenes Podcast-Verzeichnis mit über 4 Mio. Feeds; auf Kategorie „News“ filtern und mit Outlets abgleichen (welche Zeitung/welcher Sender hat einen Podcast) | API (kostenloser Schlüssel) oder kompletter Download als Datei |
| 2 | Podcast Index – API-Schlüssel | https://api.podcastindex.org/ | Anmeldung für den Schlüssel | – |

---

## 3. VIDEO – Fernsehen & Online-Video

| Prio | Quelle | Link | Was drin ist | Abruf |
|---|---|---|---|---|
| 1 | **iptv-org Database** | https://github.com/iptv-org/database | über 10.000 Sender mit Land, Sprache, Kategorie (z. B. „news“), Website | CSV-Dateien, automatisch |
| 1 | iptv-org API | https://github.com/iptv-org/api | dieselben Daten als JSON | automatisch |
| 2 | Wikidata (siehe 0) | https://query.wikidata.org/ | YouTube-Kanäle von Outlets (als Social-Media-Konto) | automatisch |

Hinweis: Für reine Online-Video-Outlets (nur YouTube/TikTok) gibt es keine gute offene Liste. Sie kommen über Wikidata und später über den Organisationstyp „Creator“.

---

## 4. ALLES IN EINEM – Outlets mit mehreren Kanälen

Beispiel: Eine Zeitung mit Website, Videos und Podcast, oder ein öffentlich-rechtlicher Sender mit TV, Radio und Online.
Dafür gibt es **keine eigene Quelle**. Die Kanäle werden zusammengesetzt aus:
- **Wikidata** (verknüpfte Sender, Social-Media-Konten, YouTube),
- **Website-Check** (Podcast-Feed, Video-Bereich, Newsletter, Social-Links auf der Startseite),
- **Podcast Index** (Abgleich: hat die Zeitung einen Podcast?),
- **Rundfunkunionen**: Ihre Mitglieder sind fast immer TV + Radio + Online.

| Prio | Quelle | Link | Was drin ist |
|---|---|---|---|
| 2 | EBU (Europa + Partner weltweit) | https://www.ebu.ch/about/members | 70 Mitglieder (115 Organisationen) in 57 Ländern, Mitgliederliste zum Download |
| 2 | ABU (Asien-Pazifik) | https://www.abu.org.my/56tt | 224 Mitglieder in 66 Ländern (Stand 30.06.2026) |
| 2 | AUB (Afrika) | https://www.uar-aub.org/ours-members | nationale Radio- und TV-Organisationen Afrikas |
| 2 | Weitere Rundfunkunionen | ⚠️ noch zu recherchieren | ASBU (arabische Staaten), CBU (Karibik), OTI (Ibero-Amerika), PIBA (Pazifik) |

---

## 5. NACHRICHTENAGENTUREN

| Prio | Quelle | Link | Was drin ist |
|---|---|---|---|
| 2 | Wikipedia – List of news agencies | https://en.wikipedia.org/wiki/List_of_news_agencies | Agenturen nach Land |
| 2 | Wikidata (siehe 0) | https://query.wikidata.org/ | Typ „news agency“ |

---

## 6. NETZWERKE – für Themen & UN-Profil

| Prio | Quelle | Link | Gibt den Etiketten … |
|---|---|---|---|
| 3 | **SDG Media Compact** | https://www.un.org/sustainabledevelopment/sdg-media-compact-about/ | UN-Profil „Existing UN relationship“; fast 400 Mitglieder in 160 Ländern. **Tipp: Mitgliederliste intern bei DGC (Campaigns) anfragen** |
| 3 | Covering Climate Now – Partner Directory | https://coveringclimatenow.org/partners/partner-directory/ | Thema Climate; über 500 Partner, internationale Partner aus 60 Ländern |
| 3 | IFCN – verifizierte Fact-Checker | https://ifcncodeofprinciples.poynter.org/signatories ⚠️ | Typ Fact-checker + Thema Fact-checking |
| 3 | Wikipedia – List of fact-checking websites | https://en.wikipedia.org/wiki/List_of_fact-checking_websites | Ergänzung zu IFCN |
| 3 | GIJN – Mitgliederverzeichnis | https://gijn.org/ (Membership Directory) ⚠️ | investigativ, Rechenschaft; 266 Mitgliedsorganisationen in 95 Ländern (meist NGOs/Non-Profits) |
| 3 | GFMD | https://gfmd.info/ | Medienentwicklung; ca. 200 Organisationen in 70 Ländern (eher für NGOs, Phase 2) |
| 3 | Earth Journalism Network (EJN) | https://earthjournalism.net/ ⚠️ | Umwelt, Klima, Biodiversität |
| 3 | OCCRP | https://www.occrp.org/ ⚠️ | investigativ, Korruption |
| 3 | PINA (Pacific Islands News Association) | ⚠️ noch zu recherchieren | Pazifik-Medien |

---

## 7. OWNERSHIP – wem gehört es / state-controlled

| Prio | Quelle | Link | Was drin ist |
|---|---|---|---|
| 3 | **Media Ownership Monitor (RSF / Global Media Registry)** | https://www.mom-rsf.org/ | Eigentümer der wichtigsten Medien in über 26 Ländern; Lizenz CC BY-ND 4.0 (Namensnennung, keine Bearbeitung) → vor Nutzung prüfen |
| 3 | RSF World Press Freedom Index | https://rsf.org/en/index | Pressefreiheit pro Land (Kontext, kein Outlet-Wert) |
| 2 | Wikidata (siehe 0) | https://query.wikidata.org/ | Eigentümer („owned by“) |

---

## Empfohlene Reihenfolge beim Bauen (Schritt 2)

1. Wikidata (liefert die festen IDs)
2. Media Cloud (Masse bei Text/Online)
3. Radio Browser (Radio)
4. iptv-org (TV)
5. Rundfunkunionen (öffentlich-rechtliche Mehrkanal-Sender)
6. Podcast Index (Podcasts den Outlets zuordnen)
7. Netzwerklisten (Themen/UN-Profil)
8. Ownership-Quellen
9. ABYZ nur, wenn danach noch Lücken bleiben
