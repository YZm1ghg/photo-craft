#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 2 toolkit for the photography book library.
  python tools.py list                  -> extraction status table
  python tools.py status                -> how many books are searchable
  python tools.py index                 -> build out/index.json (chapter map per book)
  python tools.py search <kw> [--top N] [--book KEY]
  python tools.py read <book> <lo> <hi>
Book keys: a source number (per library-map.md) or a slug substring.

The source PDF directory is resolved in this order (first hit wins):
  1. $PHOTO_BOOKS_DIR
  2. corpus/config.json  -> {"books_dir": "..."}
There is no built-in default: point one of the above at YOUR OWN library of
legally obtained photography books. Without it, search/read still work off out/
(the corpus you build yourself); only book NUMBERING falls back to index.json.
This plugin ships no book text.
"""
import os, re, sys, json, glob

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
TXT, META, DONE = (os.path.join(OUT, k) for k in ("txt", "meta", "done"))

# Non-photography files to skip when numbering the source library (match by
# slug substring). Delete this entry if your own library has nothing to exclude.
EXCLUDE = {"岛"}
# No built-in default: the user must supply their own book directory via
# $PHOTO_BOOKS_DIR or corpus/config.json ({"books_dir": "..."}).
DEFAULT_SRC = None


def _find_src():
    """Return the source PDF dir, or None when the user has not set one."""
    env = os.environ.get("PHOTO_BOOKS_DIR")
    if env and os.path.isdir(env):
        return env
    cfgp = os.path.join(HERE, "config.json")
    if os.path.exists(cfgp):
        try:
            d = json.load(open(cfgp, encoding="utf-8")).get("books_dir")
            if d and os.path.isdir(d):
                return d
        except (ValueError, OSError):
            pass
    return DEFAULT_SRC


SRC = _find_src()

_SRC_HINT = (
    "source PDF dir not set — set $PHOTO_BOOKS_DIR or corpus/config.json "
    '({"books_dir": "..."}) to your own library of books. '
    "Search/read still work on anything you have already extracted into out/."
)


def slugify(name):
    s = name.rsplit(".", 1)[0]
    for ch in '\\/:*?"<>|':
        s = s.replace(ch, "_")
    return s[:90]


def _canonical():
    """[(num, slug)] in source order, derived from the PDFs when available."""
    if not SRC:
        return []
    try:
        pdfs = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".pdf"))
    except OSError:
        return []
    return [(i, slugify(f)) for i, f in enumerate(pdfs, 1)
            if slugify(f) not in EXCLUDE]

PAGE_RE = re.compile(r"<<<Page (\d+)>>>")
# Heading shapes actually used across this library: 第N章/节/课/单元/部分, 单元,
# 課, Chapter N, "N.N title", plus bare Chinese headings that appear as a short
# standalone line at the top of a page (typical of OCR'd Taiwanese editions).
CHAP_RE = re.compile(
    r"^\s*("
    r"第\s*[0-9一二三四五六七八九十百]+\s*[章节節部篇讲講課课单元單元部分]"
    r"|[Cc]hapter\s+\d+"
    r"|[0-9]{1,2}[\.\-][0-9]{1,2}\s+\S"
    r"|(上篇|下篇|中篇|概述|绪论|結語|结语|前言|導論|导论|後記|后记)"
    r")"
)


def books():
    """All books that have a text file, sorted by canonical source number."""
    nums = {slug: num for num, slug in _canonical()}
    if not nums:
        # Source PDFs unavailable (e.g. the corpus was shared on its own):
        # recover the numbering that was baked into index.json at build time so
        # "read 11" still hits the right book.
        idxp = os.path.join(OUT, "index.json")
        if os.path.exists(idxp):
            try:
                idx = json.load(open(idxp, encoding="utf-8"))
                nums = {s: v.get("num", 999) for s, v in idx.items()}
            except (ValueError, OSError):
                nums = {}
    out = []
    for p in glob.glob(os.path.join(TXT, "*.txt")):
        s = os.path.basename(p)[:-4]
        num = nums.get(s)
        if num is None:                       # fall back to a leading number
            m = re.match(r"^(\d+)[\.\s]", s)
            num = int(m.group(1)) if m else 999
        out.append((num, s, p))
    out.sort(key=lambda t: (t[0], t[1]))
    return out


def load(slug):
    with open(os.path.join(TXT, slug + ".txt"), encoding="utf-8") as fh:
        return fh.read()


def splits(text):
    parts = PAGE_RE.split(text)
    return [(int(parts[i]), parts[i + 1]) for i in range(1, len(parts), 2)]


def resolve(key):
    bs = books()
    if key.isdigit():
        n = int(key)
        for num, slug, _ in bs:
            if num == n:
                return slug
    hits = [s for _, s, _ in bs if key in s]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise SystemExit(f"no book matches {key!r}")
    print("multiple matches:", file=sys.stderr)
    for h in hits:
        print("  ", h, file=sys.stderr)
    return hits[0]


def _meta(slug):
    """Read out/meta/<slug>.json, tolerating a missing or malformed file."""
    mp = os.path.join(META, slug + ".json")
    if not os.path.exists(mp):
        return {}
    try:
        with open(mp, encoding="utf-8-sig") as fh:
            return json.load(fh)
    except (ValueError, OSError):
        return {}


def cmd_list():
    bs = books()
    if not bs:
        print(_SRC_HINT)
        print("no books extracted yet — out/txt/ is empty.")
        return
    for num, slug, path in bs:
        m = _meta(slug)
        print(f"{num:>3} | {m.get('mode','?'):>6} | {m.get('pages','?'):>4}p | "
              f"{m.get('chars',0):>8}ch | conf={m.get('mean_conf')} | {slug[:56]}")
    print(f"\ntotal books extracted: {len(bs)}")


def cmd_status():
    """Is the library searchable yet? Which numbers are still missing?"""
    have = {num for num, _, _ in books()}
    canon = _canonical()
    if not canon:
        print(_SRC_HINT)
        if not have:
            print("no extracted books found in out/ either — nothing to show.")
            return []
        return cmd_list()
    missing = [(n, s) for n, s in canon if n not in have]
    total_ch = sum(_meta(s).get("chars", 0) for _, s, _ in books())
    print(f"extracted {len(have)}/{len(canon)} books, {total_ch:,} chars")
    if missing:
        print(f"still extracting/queued: {', '.join(str(n) for n, _ in missing)}")
    else:
        print("library complete — all books searchable")
    return missing


def cmd_index():
    idx = {}
    for num, slug, path in books():
        text = load(slug)
        pgs = splits(text)
        chapters = []
        for pg, body in pgs:
            for line in body.split("\n")[:14]:
                line = line.strip()
                if 2 <= len(line) <= 42 and CHAP_RE.match(line):
                    chapters.append({"page": pg, "title": line})
                    break
        # These editions often expose the real structure on a 目录 / Contents page
        # rather than as per-page headings, so keep that page's text verbatim.
        toc = ""
        for pg, body in pgs[:24]:
            if re.search(r"目\s*录|目\s*錄|Contents|CONTENTS", body[:400]):
                toc = re.sub(r"[ \t]+", " ", body)
                toc = re.sub(r"\n{2,}", "\n", toc).strip()[:1800]
                break
        idx[slug] = {
            "num": num,
            "pages": len(pgs),
            "chars": len(text),
            "chapters": chapters,
            "toc": toc,
            "page1_hint": (pgs[0][1][:300] if pgs else ""),
        }
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(idx, fh, ensure_ascii=False, indent=2)
    tot = sum(v["chars"] for v in idx.values())
    withtoc = sum(1 for v in idx.values() if v["toc"])
    print(f"indexed {len(idx)} books, {tot:,} chars, {withtoc} with a TOC page")


def iter_pages(book_filter=None):
    """Yield (slug, page, body) for one book, or all books when no filter.

    The filter is resolved the same way `read` resolves it — so a book NUMBER
    ("7"), a partial title ("美国纽约"), or a book name all work. A raw substring
    test would silently return nothing for numeric keys.
    """
    if book_filter:
        slugs = {resolve(book_filter)}
    else:
        slugs = None
    for num, slug, path in books():
        if slugs is not None and slug not in slugs:
            continue
        for pg, body in splits(load(slug)):
            yield slug, pg, body


def cmd_search(kw, top=40, book=None):
    pat = re.compile(re.escape(kw), re.I)
    rows = []
    for slug, pg, body in iter_pages(book):
        for m in pat.finditer(body):
            a, b = max(0, m.start() - 80), m.end() + 120
            snippet = re.sub(r"\s+", " ", body[a:b]).strip()
            rows.append((slug, pg, snippet))
    rows.sort(key=lambda r: r[0])
    print(f"{len(rows)} hits for {kw!r}\n")
    for slug, pg, sn in rows[:top]:
        print(f"[{slug[:42]} p{pg}] …{sn}…")


def cmd_range(book, lo, hi):
    if not books():
        raise SystemExit(_SRC_HINT)
    slug = resolve(book)
    for pg, body in splits(load(slug)):
        if lo <= pg <= hi:
            body = re.sub(r"\n{3,}", "\n\n", body).strip()
            print(f"\n===== {slug}  p{pg} =====\n{body}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "list":
        cmd_list()
    elif a[0] == "status":
        cmd_status()
    elif a[0] == "index":
        cmd_index()
    elif a[0] == "search":
        kw = a[1]
        top = 40
        book = None
        if "--top" in a:
            top = int(a[a.index("--top") + 1])
        if "--book" in a:
            book = a[a.index("--book") + 1]
        cmd_search(kw, top, book)
    elif a[0] in ("read", "chapter"):
        cmd_range(a[1], int(a[2]), int(a[3]))
    else:
        print(__doc__)
