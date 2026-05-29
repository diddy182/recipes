#!/usr/bin/env python3
"""Dump raw text from every src PDF into data/_text/<relpath>.txt.

A reading aid so recipe text can be reviewed and hand-structured into JSON
without re-opening each PDF. Not an auto-extractor — structuring is manual.
"""
import sys
from pathlib import Path
import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src-pdfs"
OUT = ROOT / "data" / "_text"
OUT.mkdir(parents=True, exist_ok=True)

for pdf in sorted(SRC.rglob("*.pdf")):
    rel = pdf.relative_to(SRC).with_suffix(".txt")
    dest = OUT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with pdfplumber.open(pdf) as doc:
            text = "\n".join((p.extract_text() or "") for p in doc.pages)
    except Exception as ex:
        text = f"!! extract failed: {ex}"
    dest.write_text(text, encoding="utf-8")
print(f"dumped {sum(1 for _ in OUT.rglob('*.txt'))} text files to {OUT}")
