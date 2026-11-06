# Working on this repository

Read `docs/BRIEFING.md` first. It is the full plan; its section A says how to work with the owner, section N is the step-by-step action plan. Do only one step per session, and continue only when the owner has confirmed its "done when".

Decisions made after the briefing was written (these win over the briefing):

- **The Atlas** is the repository `hannascoder/UN-Media-Consumption-Map-copy-2` (public), live at `dgc-atlas-hanna-extension.hannacstevens.workers.dev`. The briefing's mention of `Partnership-DGC-Atlas-Expansion` as the Atlas is outdated: that is the old Partner Finder (private), which keeps running unchanged until the new tool is tested (after step 10). Nothing from it is reused.
- **Build separately first, integrate later.** The Partner Finder is its own private site. Integration into the Atlas (step 8) means: same design (`site/assets/atlas.css` is a copy of the Atlas file), a link/tab in the Atlas menu, and the Partner Finder may read the Atlas's public data. Private partner data never goes into the public Atlas.
- **Hosting:** Cloudflare Workers with static assets (Cloudflare's current way; `wrangler.jsonc` publishes only `site/`), instead of Cloudflare Pages. Same behaviour: every push to `main` is published automatically.
- **Access:** Cloudflare Access on all URLs (production and previews), only the owner for now. The owner logs in with their Cloudflare account. Planned for step 9: one Cloudflare API token as a GitHub secret, login by email code (One-time PIN) for colleagues, and the list of allowed emails as a file in the repo synced by a workflow, so nobody has to use the Cloudflare dashboard.
- **Step 0 is done.** The Atlas link was moved to step 8.
- **Misinformation Monitor:** not part of the new tool for now; backlog.
- **Regions:** UN M49. Show region, then the intermediate region if there is one, otherwise the subregion (see config/README.md).

- **Category rules:** `docs/KATEGORIEN.md` (decisions of 05.11.2026 at the end). The search bar is left out of v1 for now.
- **REMIND THE OWNER (open to-dos they asked to be reminded of):** (1) add NGOs as a new organisation type (phase 2); (2) add the internal SDG Media Compact member list once the owner gets it from DGC Campaigns; (3) sign up for a free Podcast Index API key (owner: later, not necessarily in step 4); (4) download the Covering Climate Now Airtable table as CSV once (guide the owner click by click). NGO sources: see docs/BACKLOG.md. Mention these at the end of each step summary until they are done.

- **Export feature (queued by the owner):** after step 4 and the NGOs are done, follow `docs/EXPORT_SPEC.md` exactly (read code, ask for columns, show sample PDF + Excel for approval, then build on a new branch with PR, README + CHANGELOG in English).

Rules: the website interface is English. Explanations to the owner are in German, simple, without jargon. All allowed values (categories, countries, languages) live in config files, not in code.
