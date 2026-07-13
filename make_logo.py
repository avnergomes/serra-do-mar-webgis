#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Make a small transparent logo from the portfolio logo2 (white, no bg) and
inline it into index.html's .pf-logo <img> (idempotent via regex)."""
import base64, io, os, re
from PIL import Image

SRC = r"C:\Users\avner\OneDrive\Documentos\GitHub\portfolio\assets\logo2.png"
HTML = "index.html"
OUT = "logo_small.png"

im = Image.open(SRC).convert("RGBA")
# trim by the alpha channel (transparent margins around the white mark)
alpha = im.split()[3]
bbox = alpha.getbbox()
if bbox:
    im = im.crop(bbox)
# center on a transparent square canvas with a small margin
side = int(max(im.size) * 1.12)
sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2), im)
sq = sq.resize((128, 128), Image.LANCZOS)
sq.save(OUT)

buf = io.BytesIO()
sq.save(buf, format="PNG", optimize=True)
datauri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

html = open(HTML, encoding="utf-8").read()
pat = re.compile(r'(<img class="pf-logo" src=")[^"]*(")')
if pat.search(html):
    html = pat.sub(lambda m: m.group(1) + datauri + m.group(2), html)
    open(HTML, "w", encoding="utf-8").write(html)
    print("Replaced .pf-logo src with logo2 data URI (%.1f KB). HTML now %.0f KB. transparent=%s"
          % (len(datauri) / 1024, os.path.getsize(HTML) / 1024, im.mode == "RGBA"))
else:
    print("No .pf-logo <img> found in index.html")
