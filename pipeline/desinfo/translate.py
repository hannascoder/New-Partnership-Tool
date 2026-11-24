"""Disinformation monitor: automatic English translation of fact-check titles.

Open source and free: Argos Translate (MIT licence, models are open, no key, no server; runs inside the daily GitHub
Actions job). Only the TITLE of a fact-check is translated (short, one sentence); the original always stays first.
Memory: cache/desinfo_translations.json {item id: english title}; every title is translated once.
Report: reports/desinfo_translation.md. A language without a model is listed there and simply stays untranslated.
If Argos cannot be installed or started, the run goes on without translation (nothing else depends on it).
"""
import json
import signal
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CFG = yaml.safe_load(open(ROOT / "config" / "desinfo.yaml", encoding="utf-8"))["translation"]
ITEMS = ROOT / "cache" / "desinfo_items.json"
MEMORY = ROOT / "cache" / "desinfo_translations.json"
REPORT = ROOT / "reports" / "desinfo_translation.md"


def lang2(code):
    return (code or "").lower().replace("_", "-").split("-")[0]


def load_argos():
    import argostranslate.package as pkg
    import argostranslate.translate as tr
    pkg.update_package_index()
    return pkg, tr, pkg.get_available_packages()


def translator_for(lang, pkg, tr, available, cache):
    """A function text -> English for this language; "none" if no model exists; "error" if it could not be loaded now."""
    if lang in cache:
        return cache[lang]
    fn = "none"
    try:
        def find():
            langs = tr.get_installed_languages()
            src = next((l for l in langs if l.code == lang), None)
            en = next((l for l in langs if l.code == "en"), None)
            if src and en:
                try:
                    return src.get_translation(en)
                except Exception:  # noqa: BLE001
                    return None
            return None
        t = find()
        if t is None:
            cand = next((p for p in available if p.from_code == lang and p.to_code == "en"), None)
            if cand:
                pkg.install_from_path(cand.download())
                t = find()
        fn = t.translate if t else "none"
    except Exception as e:  # noqa: BLE001 - e.g. download failed: try again in the next run
        print(f"model for {lang} could not be loaded: {e}", file=sys.stderr)
        fn = "error"
    cache[lang] = fn
    return fn


def run(items, memory, get_translator, max_per_run, max_chars, skip, deadline=None, on_progress=None):
    """Translate the newest untranslated titles. get_translator(lang) -> function or None. Returns (done, unsupported).
    Stops (cleanly) when the deadline (time.time() value) has passed; on_progress() is called every 25 titles."""
    todo = [i for i in items if i["id"] not in memory and lang2(i["lang"]) not in skip and i.get("title")]
    todo.sort(key=lambda i: i["date"], reverse=True)
    done, unsupported = Counter(), Counter()
    for n, i in enumerate(todo[:max_per_run]):
        if deadline and time.time() > deadline:
            break
        if on_progress and n and n % 25 == 0:
            on_progress()
        lang = lang2(i["lang"])
        fn = get_translator(lang)
        if fn == "error":
            continue                         # try again in the next run
        if fn is None or fn == "none":
            unsupported[lang] += 1
            memory[i["id"]] = ""            # no model: remembered, asked again on the 1st of every month
            continue
        try:
            text = fn(i["title"][:max_chars]).strip()
        except Exception:  # noqa: BLE001
            continue
        memory[i["id"]] = text
        done[lang] += 1
    return done, unsupported


STAGES = []          # [(stage, seconds, note)] written into the report as we go


def write_report(memory, items, done, unsupported, status):
    waiting = sum(1 for i in items if i["id"] not in memory and lang2(i["lang"]) not in CFG["skip_languages"])
    L = ["# Disinformation monitor: automatic English translation", "",
         f"Run: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} | Argos Translate (open source) | status: {status}", "",
         f"Translated in this run: {sum(done.values())} | in memory: {sum(1 for v in memory.values() if v)} | waiting: {waiting}", "",
         "## Time per stage", ""] + [f"- {n}: {sec:.0f} s {note}" for n, sec, note in STAGES] + [
         "", "| Language | Translated now | Without a model (left untranslated) |", "|---|---|---|"]
    for lang in sorted(set(done) | set(unsupported)):
        L.append(f"| {lang} | {done.get(lang, 0)} | {unsupported.get(lang, 0)} |")
    L += ["", "Only titles are translated, by machine; the original is always shown first on the page."]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")


def save_memory(memory):
    json.dump(memory, open(MEMORY, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


def main():
    if not ITEMS.exists():
        print("no items yet")
        return
    t0 = time.time()
    items = json.load(open(ITEMS, encoding="utf-8"))
    memory = json.load(open(MEMORY, encoding="utf-8")) if MEMORY.exists() else {}
    ids = {i["id"] for i in items}
    memory = {k: v for k, v in memory.items() if k in ids}           # forget what left the 12-month window
    if datetime.now(timezone.utc).day == 1:       # models appear over time: ask again once a month
        memory = {k: v for k, v in memory.items() if v}
    done, unsupported, status = Counter(), Counter(), "started"
    # if the job is stopped from outside (time limit), keep what we have and say so in the report
    def on_term(signum, frame):
        STAGES.append(("stopped from outside", time.time() - t0, "(time limit of the job)"))
        save_memory(memory)
        write_report(memory, items, done, unsupported, "stopped by the time limit of the job")
        sys.exit(0)
    signal.signal(signal.SIGTERM, on_term)
    try:
        t1 = time.time()
        pkg, tr, available = load_argos()
        STAGES.append(("start Argos and read the model index", time.time() - t1, f"({len(available)} models listed)"))
        write_report(memory, items, done, unsupported, "running")
        cache = {}

        def get_translator(lang):
            t2 = time.time()
            known = lang in cache
            fn = translator_for(lang, pkg, tr, available, cache)
            if not known:
                STAGES.append((f"model {lang} -> en", time.time() - t2, "(ready)" if callable(fn) else f"({fn})"))
            return fn

        def progress():
            save_memory(memory)
            write_report(memory, items, done_now, unsupported_now, "running")

        done_now, unsupported_now = Counter(), Counter()
        deadline = time.time() + CFG["budget_seconds"]
        t3 = time.time()
        done, unsupported = run(items, memory, get_translator, CFG["max_per_run"], CFG["max_title_chars"],
                                set(CFG["skip_languages"]), deadline, progress)
        STAGES.append(("translate titles", time.time() - t3, f"({sum(done.values())} titles)"))
        status = "ok" if time.time() <= deadline else "stopped at the time budget (the rest follows in the next run)"
    except Exception as e:  # noqa: BLE001 - translation is optional
        status = f"not available in this run: {type(e).__name__}: {e}"
    save_memory(memory)
    write_report(memory, items, done, unsupported, status)
    print(f"translated {sum(done.values())}, no model for {dict(unsupported)}, status {status}")


if __name__ == "__main__":
    main()
