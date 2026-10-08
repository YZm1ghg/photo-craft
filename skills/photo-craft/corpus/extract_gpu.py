#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GPU extraction for your own photography book library.

Runs on the RTX 4060 via onnxruntime-gpu + the nvidia-cu12 wheels. Measured
~2.5-4 s/page vs 75-167 s/page on CPU, so a multi-thousand-page library takes
hours instead of days.

  out/txt/<slug>.txt    readable text, page-marked with <<<Page n>>>
  out/meta/<slug>.json  extraction stats (mode, pages, chars, mean_conf)
  out/done/<slug>       completion marker -> safe to re-run / resume

Usage:
  PHOTO_BOOKS_DIR=/path/to/your/books python extract_gpu.py
  python extract_gpu.py --only 7 8 11
  python extract_gpu.py --force          # redo even if done
"""
import os, sys, gc, json, time, io, glob, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
# Your own library of legally obtained PDFs. No default is shipped.
SRC = os.environ.get("PHOTO_BOOKS_DIR")
if not SRC:
    cfgp = os.path.join(HERE, "config.json")
    if os.path.exists(cfgp):
        try:
            SRC = json.load(open(cfgp, encoding="utf-8")).get("books_dir")
        except (ValueError, OSError):
            SRC = None
if not SRC or not os.path.isdir(SRC):
    raise SystemExit(
        "source PDF dir not set — set $PHOTO_BOOKS_DIR or corpus/config.json "
        '({"books_dir": "..."}) to your own library of photography books.'
    )
OUT = os.path.join(HERE, "out")
TXT, META, DONE = (os.path.join(OUT, k) for k in ("txt", "meta", "done"))
# Skip non-photography files by slug substring. Edit for your own library.
EXCLUDE = {"岛"}

# --- make the CUDA/cuDNN DLLs from the nvidia wheels visible to onnxruntime ---
import nvidia
_nv = os.path.dirname(nvidia.__file__)
for _sub in os.listdir(_nv):
    for _leaf in ("bin", "lib"):
        _d = os.path.join(_nv, _sub, _leaf)
        if os.path.isdir(_d):
            try:
                os.add_dll_directory(_d)
            except OSError:
                pass
            os.environ["PATH"] = _d + os.pathsep + os.environ["PATH"]

import numpy as np
import fitz
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

DPI = 170
PROBE = [8, 12, 16, 22]
MIN_CHARS = 200            # a book yielding less than this failed OCR; do not
                           # mark it done (guards against silent empty output)
ENGINE = None


def log(*a):
    print(*a, flush=True)


def slugify(name):
    s = name.rsplit(".", 1)[0]
    for ch in '\\/:*?"<>|':
        s = s.replace(ch, "_")
    return s[:90]


def engine():
    global ENGINE
    if ENGINE is None:
        t = time.time()
        ENGINE = RapidOCR(det_use_cuda=True, rec_use_cuda=True)
        log(f"    [engine] CUDA ready in {time.time()-t:.1f}s")
    return ENGINE


def native_quality(doc):
    n = len(doc)
    tot = k = 0
    for i in PROBE:
        if i < n:
            tot += len(doc[i].get_text().strip())
            k += 1
    return tot / max(1, k)


def ocr_page(page, dpi=DPI):
    eng = engine()
    pm = page.get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", [pm.width, pm.height], pm.samples)
    res, _ = eng(np.array(img))
    if not res:
        return "", 0.0
    return "\n".join(r[1] for r in res), sum(r[2] for r in res) / len(res)


def run_book(fn):
    s = slugify(fn)
    path = os.path.join(SRC, fn)
    t0 = time.time()
    doc = fitz.open(path)
    pages = len(doc)
    q = native_quality(doc)
    mode = "native" if q >= 60 else "ocr"

    buf = io.StringIO()
    buf.write(f"# {fn}\n# pages={pages} mode={mode}\n\n")
    confs, empty = [], 0

    if mode == "native":
        for i in range(pages):
            t = doc[i].get_text()
            if t.strip():
                buf.write(f"\n<<<Page {i+1}>>>\n{t}\n")
            else:
                empty += 1
    else:
        for i in range(pages):
            try:
                t, c = ocr_page(doc[i])
            except Exception as e:
                t, c = "", 0.0
                if i < 3:
                    log(f"    p{i+1} ocr-err {type(e).__name__}")
            if t.strip():
                buf.write(f"\n<<<Page {i+1}>>>\n{t}\n")
                confs.append(c)
            else:
                empty += 1
            if (i + 1) % 25 == 0:
                el = time.time() - t0
                eta = el / (i + 1) * (pages - i - 1)
                log(f"    p{i+1}/{pages} el={el/60:.1f}m eta={eta/60:.1f}m")

    text = buf.getvalue()
    with open(os.path.join(TXT, s + ".txt"), "w", encoding="utf-8") as fh:
        fh.write(text)
    conf = round(sum(confs) / len(confs), 4) if confs else None
    meta = dict(file=fn, pages=pages, mode=mode, chars=len(text),
                empty_pages=empty, mean_conf=conf,
                secs=round(time.time() - t0, 1))
    with open(os.path.join(META, s + ".json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    # Only mark complete when we actually got text. A silent OCR failure must
    # not look like success, or resume will skip the book forever.
    if len(text) < MIN_CHARS:
        doc.close()
        gc.collect()
        meta["status"] = "FAILED-empty"
        return meta
    open(os.path.join(DONE, s), "w").write("ok")
    doc.close()
    gc.collect()
    meta["status"] = "ok"
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, nargs="*")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    for d in (TXT, META, DONE):
        os.makedirs(d, exist_ok=True)

    pdfs = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".pdf"))
    jobs = []
    for i, fn in enumerate(pdfs, 1):
        if slugify(fn) in EXCLUDE:
            continue
        if a.only and i not in a.only:
            continue
        jobs.append((i, fn))

    log(f"[gpu-extract] {len(jobs)} books to process")
    t0 = time.time()
    done = 0
    for idx, (num, fn) in enumerate(jobs, 1):
        s = slugify(fn)
        if os.path.exists(os.path.join(DONE, s)) and not a.force:
            log(f"[{idx}/{len(jobs)}] skip (done) :: {s[:46]}")
            continue
        try:
            m = run_book(fn)
        except Exception as e:
            log(f"[{idx}/{len(jobs)}] FAIL {s[:40]}: {type(e).__name__}: {e}")
            continue
        if m.get("status") != "ok":
            log(f"[{idx}/{len(jobs)}] !! {m['status']} :: {s[:44]} "
                f"(chars={m['chars']}) — will retry next run")
            continue
        done += 1
        log(f"[{idx}/{len(jobs)}] {m['mode']} {m['pages']}p conf={m['mean_conf']} "
            f"chars={m['chars']} {m['secs']}s :: {s[:44]}")
        log(f"    elapsed {(time.time()-t0)/60:.1f} min")
    log(f"[gpu-extract] DONE, {done} books this run, {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
