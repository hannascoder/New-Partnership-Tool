# Get feedback (page `site/feedback.html`) - plan, decisions of 24.11.2026

Session name: "Talk feedback implementation". Source of the idea: the two Berkeley International Consulting
presentations (UN x BIC Part I / II, fall 2025: UN podcast survey, n=111, 63 % American, 67 % aged 18-21).

## What the owner wants
New tab **"Get feedback"** (top menu, next to Media / Organisations & NGOs / Disinformation). Pick who to
contact (e.g. the Zeppelin University Model UN group), pick the UN product (podcast, video, article ...),
the tool builds the mail with the survey link (Google Forms), people have **one week** to answer and may also
suggest improvements to the survey. Afterwards the answers are evaluated and presented like the Berkeley
slides. Everything free and open (project principle).

## Owner's decisions (24.11.2026)
- **Contact list** = private Google Sheet of the owner (option A). Read by the tool through a **Google service
  account** (free). Private contact data must NEVER go into the public repository or into `site/`.
- Mail: same pop-up as "Send mail" (Outlook app / Outlook web / Gmail, text with yellow [gaps]). Several
  recipients at once go into **BCC**; one by one for personal mails. English only for now.
- List fields: name, type, country, university/place, language, short description, topic/interest, age
  group, main contact (name + mail), extra mails, **sending mode** (only main contact / general address /
  all at once). Filters like on the Media/NGO pages (country, language, type, topic ...).
- Organisations and groups first (no private individuals). Start with **Model UN** as the worked example;
  a suggestion list built from open sources.
- Survey: **one fixed standard survey** (same core questions every time, so products and groups can be
  compared) **plus extra questions per product**. Anonymous. Language English first.
- Products: everything (podcasts, videos, articles, graphics ... in a config file, extendable).
- The owner **starts the evaluation herself** (button), after the one-week deadline. A reminder after
  4 days is allowed. Results: page in the tool in the style of the slides + PDF/PowerPoint export; results are
  stored so rounds can be **compared** (podcast A spring vs. autumn; group vs. group).
- Free text (suggestions): sorted, counted by keywords, best quotes shown (no AI, no cost). A summary by Claude
  in a chat session is possible on request, but is not an automatic part of the tool.

## Core questions (proposal from the Berkeley survey, closed choices + "Other")
1. Overall rating 1-5. 2. Would you recommend it? (yes / no). 3. Length fits? (too short / right / too long).
4. How often do you listen / watch such content? 5. Where do you use it (Spotify, YouTube, Apple, TikTok ...)?
6. When / where (commute, chores, study ...). 7. Barriers (no time, did not know it, not relatable,
language, ads / cost). 8. Topics wanted (the tool's topic list + Other). 9. Are young voices well
represented? 10. Free text: what should we improve? + one box "suggest a better survey question".
Lesson from the Berkeley deck: topic question was open text (unreadable pie chart) -> closed list;
sample was very US / STEM -> contact groups from many countries.

## Owner 24.11.2026 (later): all contacts in ONE place = the private Google Sheet (also the Model UN suggestion list, no split with the repo). Group code in the survey link: yes (anonymous per person, visible per group).

## Open design point (architecture)
The site is static and published from a PUBLIC repository, so a private Sheet cannot be read at build time and
committed. Plan: a very small **Cloudflare Worker** (free plan, behind the same Cloudflare Access login) reads the
Sheet with the service account key (stored as Cloudflare secret, never in the repo) and serves it to the page.
Same for the survey answers (evaluation button calls the Worker). `wrangler.jsonc` then gets a `main` script.
Public organisation data (e.g. the Model UN suggestion list from open sources) may live in the repo like the NGOs.

## Steps (one per session, owner confirms each "done when")
- **F1** Page + menu entry, list view with filters and selection, mail pop-up with feedback template,
  sending modes, BCC. Data for now from a file in the repo (public Model UN suggestion list + a few test
  entries). Done when: owner selects the Zeppelin Model UN group and gets a correct draft in Outlook / Gmail.
- **F1b** Connect the private Google Sheet via service account + Worker (owner does click-by-click setup
  together with Claude: Google Cloud project, service account, share the Sheet, Cloudflare secret).
- **F2** Question bank + standard survey text, product list (config), extra questions per product, deadline
  (1 week) and reminder text. Owner builds the Google Form from the question bank (or later by API).
- **F3** Evaluation: read answers (service account), numbers + charts + quotes, results page, PDF/PPT export,
  stored rounds and comparison.

Mail-merge limits: the tool only opens a draft; the owner clicks "send". Personalised mails go one by one.
GDPR: organisation addresses only; add an opt-out line to the template; owner may want to ask the UN data
protection office (not decided by the tool).

## Status F1 (built 24.11.2026, waiting for the owner's check)
`site/feedback.html` + `assets/feedback.js` (menu entry on all pages), settings `config/feedback.yaml`
(-> `python pipeline/build/feedback_config.py` -> `site/data/feedback-config.json`), Sheet template
`config/feedback_sheet_template.csv`, Worker `worker/index.js` (+ `wrangler.jsonc` main/ASSETS/run_worker_first).
Without the Sheet the page shows DEMO data (example.org). One mail per selected group, several addresses of a
group in BCC, reminder switch, deadline = today + days. Not yet tested on Cloudflare (Worker deploy + Access on /api).
Next: F1b (Google Cloud service account, share Sheet, Cloudflare secrets GOOGLE_SERVICE_ACCOUNT_JSON and
FEEDBACK_SHEET_ID) and the Model UN suggestion list into the Sheet.
