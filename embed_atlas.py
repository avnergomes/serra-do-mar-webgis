#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inject peaks.geojson and pois.geojson into index.html between their markers."""
import json, re, os, sys

HTML = "index.html"

def inject(html, start, end, varname, gjfile):
    gj = json.load(open(gjfile, encoding="utf-8"))
    payload = start + "let %s=" % varname + json.dumps(gj, ensure_ascii=False, separators=(",", ":")) + ";" + end
    pat = re.compile(re.escape(start) + ".*?" + re.escape(end), re.S)
    if not pat.search(html):
        sys.exit("markers %s ... %s not found" % (start, end))
    return pat.sub(lambda m: payload, html), len(gj["features"])

html = open(HTML, encoding="utf-8").read()
html, npk = inject(html, "/*__PEAKS_GEO__*/", "/*__PEAKS_END__*/", "PEAKS_GEO", "peaks.geojson")
html, npo = inject(html, "/*__POIS_GEO__*/", "/*__POIS_END__*/", "POIS_GEO", "pois.geojson")
open(HTML, "w", encoding="utf-8").write(html)
print("Injected %d peaks + %d POIs. index.html now %.0f KB" % (npk, npo, os.path.getsize(HTML) / 1024))
