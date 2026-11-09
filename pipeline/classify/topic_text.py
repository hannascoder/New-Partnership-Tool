"""Topic keyword matching (plan T1-T3): compares what is known about an outlet
with config/topic_keywords.yaml and returns topics with a strength.

Texts used (each with its role):
  name          outlet name                              -> FOCUS on 1 strong word
  description   Wikidata description, website meta description / title -> FOCUS on 1 strong word
  about         Wikipedia introduction, website About page -> FOCUS on 2 strong words
                (or strong + context), COVERS on 1 strong word
  menu          website menu / section names and their addresses -> DESK
  headlines     website headlines and home page text      -> COVERS on 2+ strong words
Strength codes: 1 = focus, 2 = desk, 3 = covers (smaller = stronger).
"""
import re
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
FOCUS, DESK, COVERS = 1, 2, 3
CJK = re.compile(r"[぀-ヿ㐀-鿿豈-﫿]")


def norm(text):
    """lower case; accents removed from Latin letters only (vowel signs of Hindi,
    Arabic ... are kept); everything that is not a letter, digit or sign
    becomes a space ("Women's rights" -> "women s rights", "COVID-19" -> "covid 19")"""
    out, prev_ascii = [], False
    for ch in unicodedata.normalize("NFKD", (text or "").casefold()):
        cat = unicodedata.category(ch)
        if cat.startswith("M"):
            if not prev_ascii:
                out.append(ch)
            continue
        if ch.isalnum():
            out.append(ch)
            prev_ascii = ch.isascii()
        else:
            out.append(" ")
            prev_ascii = False
    return " ".join("".join(out).split())


class Matcher:
    def __init__(self, path=ROOT / "config" / "topic_keywords.yaml"):
        cfg = yaml.safe_load(open(path, encoding="utf-8"))["topics"]
        self.strong, self.context, self.section = {}, {}, {}
        self.prefix, self.cjk = [], {}
        exclude = set()
        for tid, t in cfg.items():
            subs = t.get("subtopics") or [{"id": None, "strong": t.get("strong") or {}}]
            for sub in subs:
                for terms in (sub.get("strong") or {}).values():
                    for w in terms:
                        self._add(self.strong, str(w), (tid, sub.get("id")))
            for terms in (t.get("context") or {}).values():
                for w in terms:
                    self._add(self.context, str(w), tid)
            for terms in (t.get("sections") or {}).values():
                for w in terms:
                    self.section.setdefault(norm(str(w)), set()).add(tid)
            for terms in (t.get("exclude") or {}).values():
                exclude.update(norm(str(w)) for w in terms)
        self.exclude = sorted(exclude, key=len, reverse=True)
        self.maxlen = max(len(k.split()) for k in list(self.strong) + list(self.context))
        self.subtopics = {tid: [s["id"] for s in (t.get("subtopics") or [])] for tid, t in cfg.items()}
        self.sub_labels = {tid: {s["id"]: s["label"] for s in (t.get("subtopics") or [])} for tid, t in cfg.items()}

    def _add(self, table, word, value):
        if word.endswith("*"):
            self.prefix.append((norm(word[:-1]), table is self.strong, value))
            return
        key = norm(word)
        if CJK.search(key):
            self.cjk.setdefault((id(table), key.replace(" ", "")), set()).add(value)
        elif key:
            table.setdefault(key, set()).add(value)

    def _clean(self, text):
        t = " " + norm(text) + " "
        for e in self.exclude:
            if " " + e + " " in t:
                t = t.replace(" " + e + " ", " ")
        return t.strip()

    def _hits(self, text, table):
        """[(word, values)] for every word / phrase of the table found in the text"""
        out = []
        if not text:
            return out
        t = self._clean(text)
        toks = t.split()
        n = len(toks)
        for i in range(n):
            for L in range(min(self.maxlen, n - i), 0, -1):
                key = " ".join(toks[i:i + L])
                v = table.get(key)
                if v:
                    out.append((key, v))
            for pre, is_strong, val in self.prefix:
                if (table is self.strong) == is_strong and toks[i].startswith(pre):
                    out.append((toks[i], {val}))
        if CJK.search(t):
            flat = t.replace(" ", "")
            for (tid_, key), v in self.cjk.items():
                if tid_ == id(table) and key in flat:
                    out.append((key, v))
        return out

    def _strong_hits(self, text):
        return self._hits(text, self.strong)

    def _context_topics(self, text):
        out = set()
        for _, v in self._hits(text, self.context):
            out |= v
        return out

    def match(self, name="", descriptions=(), abouts=(), menu=(), headlines=()):
        """Returns {topic: {"s": strength, "subs": set(sub ids), "why": text}}"""
        res = {}

        def add(topic, sub, strength, why):
            r = res.setdefault(topic, {"s": 9, "subs": set(), "why": ""})
            if sub:
                r["subs"].add(sub)
            if strength < r["s"]:
                r["s"], r["why"] = strength, why

        # FOCUS: name / descriptions
        for kind, texts in (("name", [name]), ("description", descriptions)):
            for text in texts:
                for term, hits in self._strong_hits(text):
                    for topic, sub in hits:
                        add(topic, sub, FOCUS, f'{kind} mentions "{term}"')
        # About texts (Wikipedia introduction, website About page): the FIRST sentence
        # says what the outlet is -> a strong word there = FOCUS; elsewhere = COVERS
        # (FOCUS also when 3+ different strong words of the topic appear)
        for label, text in abouts:
            first = re.split(r"(?<=[.!?。])\s", (text or "").strip(), maxsplit=1)[0]
            in_first = {topic for _, hs in self._strong_hits(first) for topic, _ in hs}
            per_topic = {}
            for term, hs in self._strong_hits(text):
                for topic, sub in hs:
                    per_topic.setdefault(topic, []).append((term, sub))
            for topic, lst in per_topic.items():
                terms = sorted({t for t, _ in lst})
                s_ = FOCUS if topic in in_first or len(terms) >= 3 else COVERS
                for _, sub in lst:
                    add(topic, sub, s_, f'{label}: "' + '", "'.join(terms[:3]) + '"')
        # DESK: menu entries (section words or strong words), also in the address.
        # Only short entries are sections; a long one is an article link (-> headlines).
        headlines = list(headlines)
        for text, path in menu:
            if len((text or "").split()) > 4:
                headlines.append(text)
                continue
            t = self._clean(text)
            found = False
            for topic in self.section.get(t, ()):
                add(topic, None, DESK, f'website section "{text}"')
                found = True
            for term, hits in self._strong_hits(text):
                for topic, sub in hits:
                    add(topic, sub, DESK, f'website section "{text}"')
                    found = True
            segs = [x for x in (path or "").strip("/").split("/") if x]
            if not found and 1 <= len(segs) <= 3 and not any(ch.isdigit() for ch in "".join(segs)):
                for part in segs:  # a whole address part must be a section word: /climate/, /category/food-security/
                    for topic in self.section.get(self._clean(part), ()):
                        add(topic, None, DESK, f'website section /{"/".join(segs)}/')
        # COVERS: headlines / home page
        if headlines:
            per_topic = {}
            for text in headlines:
                for term, hs in self._strong_hits(text):
                    for topic, sub in hs:
                        per_topic.setdefault(topic, []).append((term, sub))
            for topic, lst in per_topic.items():
                if len(lst) >= 2:
                    terms = sorted({t for t, _ in lst})
                    for _, sub in lst:
                        add(topic, sub, COVERS, 'website headlines: "' + '", "'.join(terms[:3]) + '"')
        return res
