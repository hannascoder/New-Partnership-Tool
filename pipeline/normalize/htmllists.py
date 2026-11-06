"""Small helpers to read member lists out of saved HTML pages.

Uses only Python's built-in HTML parser: the page becomes a simple tree of
Node objects, which the parsers in networks.py walk through."""
import html as htmllib
import re
from html.parser import HTMLParser

VOID = {"br", "img", "hr", "meta", "link", "input", "source", "wbr", "col", "area", "base", "embed", "param", "track"}


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs), parent, []

    def text(self):
        out = []
        for c in self.children:
            out.append(c if isinstance(c, str) else ("" if c.tag in ("sup", "style", "script") else c.text()))
        return re.sub(r"\s+", " ", "".join(out)).strip()

    def find_all(self, tag):
        for c in self.children:
            if isinstance(c, Node):
                if c.tag == tag:
                    yield c
                yield from c.find_all(tag)

    def first(self, tag):
        return next(self.find_all(tag), None)

    def classes(self):
        return set((self.attrs.get("class") or "").split())

    def ancestors(self):
        p = self.parent
        while p is not None:
            yield p
            p = p.parent


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def parse(html_text):
    b = _Builder()
    b.feed(html_text)
    return b.root


def walk(node):
    """All nodes in document order."""
    for c in node.children:
        if isinstance(c, Node):
            yield c
            yield from walk(c)


def wiki_link(node):
    """(title, text) of the first link to a Wikipedia article inside node, else (None, None)."""
    for a in node.find_all("a"):
        href = a.attrs.get("href") or ""
        if href.startswith("/wiki/") and ":" not in href[6:]:
            return htmllib.unescape(a.attrs.get("title") or ""), a.text()
    return None, None


def own_text(li):
    """Text of a list item without its nested lists."""
    parts = []
    for c in li.children:
        if isinstance(c, str):
            parts.append(c)
        elif c.tag not in ("ul", "ol", "sup", "style", "script"):
            parts.append(c.text())
    return re.sub(r"\s+", " ", " ".join(parts)).strip()
