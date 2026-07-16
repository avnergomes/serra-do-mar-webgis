#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inject the generated GeoJSON layers into index.html between their markers.

Sources: peaks/pois/parks come from the fetch_*.py OSM collectors; routes.geojson
comes from parse_routes.py (the climbing workbook); crags.geojson from fetch_crags.py."""
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
html, npa = inject(html, "/*__PARKS_GEO__*/", "/*__PARKS_END__*/", "PARKS_GEO", "parks.geojson")
html, nrt = inject(html, "/*__ROUTES_GEO__*/", "/*__ROUTES_END__*/", "ROUTES_GEO", "routes.geojson")
html, ncr = inject(html, "/*__CRAGS_GEO__*/", "/*__CRAGS_END__*/", "CRAGS_GEO", "crags.geojson")
html, nhw = inject(html, "/*__HIGHWAYS_GEO__*/", "/*__HIGHWAYS_END__*/", "HIGHWAYS_GEO", "highways.geojson")
open(HTML, "w", encoding="utf-8").write(html)
nvias = sum(len(f["properties"].get("vias", []))
            for f in json.load(open("routes.geojson", encoding="utf-8"))["features"])
print("Injected %d peaks + %d POIs + %d parks + %d areas de escalada (%d vias) + %d paredoes + %d rodovias."
      % (npk, npo, npa, nrt, nvias, ncr, nhw))
print("index.html now %.0f KB" % (os.path.getsize(HTML) / 1024))
