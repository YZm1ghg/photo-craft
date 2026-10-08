#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build per-book detail cards from the extracted corpus:
  out/cards/<slug>.md   -> front matter (mode/pages/chars) + detected chapter list
                           + keyword coverage + opening text preview
Run:  python make_cards.py          (all books present in out/txt)
      python make_cards.py 1 7 8    (only those book numbers)
"""
import os, re, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
TXT, META, CARDS = (os.path.join(OUT, k) for k in ("txt", "meta", "cards"))
os.makedirs(CARDS, exist_ok=True)

PAGE_RE = re.compile(r"<<<Page (\d+)>>>")
CHAP_RE = re.compile(
    r"^\s*(第\s*[0-9一二三四五六七八九十百]+\s*[章节部篇讲]|"
    r"[Cc]hapter\s+\d+|[0-9]{1,2}\.[0-9]{1,2}\s+\S)"
)

PROBES = [
    "曝光", "光圈", "快门", "ISO", "感光度", "白平衡", "色温", "景深", "对焦", "测光",
    "构图", "三分法", "引导线", "框架", "留白", "透视", "光线", "布光", "光比", "逆光",
    "侧光", "顶光", "柔光", "硬光", "反光板", "闪光灯", "离机闪", "高速同步", "压光",
    "色彩", "色调", "饱和度", "对比度", "HSL", "调色", "预设", "曲线", "图层", "蒙版",
    "磨皮", "液化", "锐化", "RAW", "raw", "Lightroom", "Photoshop", "修图", "后期",
    "人像", "摆姿", "美姿", "眼神光", "特写", "半身", "全身", "儿童", "婚礼", "婚纱",
    "写真", "商业", "静物", "商品", "风光", "街拍", "纪实", "表情", "情绪", "氛围",
    "沟通", "引导", "客户", "报价", "接单", "拍摄计划", "流程", "镜头", "焦段", "广角",
    "长焦", "定焦", "机位", "角度", "视线", "节奏", "风格", "审美", "视觉",
]


def splits(text):
    parts = PAGE_RE.split(text)
    return [(int(parts[i]), parts[i + 1]) for i in range(1, len(parts), 2)]


def build(slug):
    tp = os.path.join(TXT, slug + ".txt")
    if not os.path.exists(tp):
        return None
    text = open(tp, encoding="utf-8").read()
    meta = {}
    mp = os.path.join(META, slug + ".json")
    if os.path.exists(mp):
        meta = json.load(open(mp, encoding="utf-8"))
    pgs = splits(text)

    chapters = []
    for pg, body in pgs:
        for line in body.split("\n")[:14]:
            line = line.strip()
            if 2 <= len(line) <= 42 and CHAP_RE.match(line):
                chapters.append((pg, line))
                break

    hits = sorted(((k, len(re.findall(re.escape(k), text, re.I))) for k in PROBES),
                  key=lambda t: -t[1])
    hits = [(k, n) for k, n in hits if n >= 3][:24]

    L = [f"# {meta.get('file', slug)}", ""]
    L.append(f"- 抽取模式：**{meta.get('mode','?')}**")
    L.append(f"- 页数：{meta.get('pages','?')}  |  字符数：{meta.get('chars',0):,}"
             f"  |  空页：{meta.get('empty_pages','?')}")
    if meta.get("mean_conf") is not None:
        L.append(f"- OCR 平均置信度：**{meta['mean_conf']}**")
    L.append("")

    if chapters:
        L.append(f"## 检出章节（{len(chapters)} 条）")
        L.append("")
        for pg, t in chapters[:60]:
            L.append(f"- p{pg} · {t}")
        L.append("")

    L.append("## 主题词覆盖（出现次数 ≥3）")
    L.append("")
    L.append(" | ".join(f"`{k}`×{n}" for k, n in hits))
    L.append("")

    L.append("## 正文开头（前 6 页）")
    L.append("")
    body_txt = "".join(b for _, b in pgs[:6])
    body_txt = re.sub(r"[ \t]+", " ", body_txt)
    body_txt = re.sub(r"\n{3,}", "\n\n", body_txt).strip()
    L.append("```")
    L.append(body_txt[:2400])
    L.append("```")
    L.append("")
    L.append("---")
    L.append(f'检索原文：`python tools.py search "关键词" --book "{slug[:24]}"`')
    L.append(f"读取段落：`python tools.py read {slug.split('.')[0]} <起页> <止页>`")

    md = "\n".join(L)
    open(os.path.join(CARDS, slug + ".md"), "w", encoding="utf-8").write(md)
    return len(md)


if __name__ == "__main__":
    want = set(sys.argv[1:])
    n = 0
    for fn in sorted(os.listdir(TXT)):
        if not fn.endswith(".txt"):
            continue
        slug = fn[:-4]
        num = slug.split(".")[0]
        if want and num not in want:
            continue
        r = build(slug)
        if r:
            n += 1
            print(f"card {slug} ({r} bytes)")
    print(f"built {n} cards -> {CARDS}")
