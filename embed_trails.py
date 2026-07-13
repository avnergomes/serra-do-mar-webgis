#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inject serra_trails.geojson into index.html between the OSM_TRAILS markers."""
import json, re, os, sys

HTML = "index.html"
GJ = "serra_trails.geojson"
START = "/*__OSM_TRAILS_START__*/"
END = "/*__OSM_TRAILS_END__*/"

gj = json.load(open(GJ, encoding="utf-8"))
payload = START + "let OSM_TRAILS=" + json.dumps(gj, ensure_ascii=False, separators=(",", ":")) + ";" + END

html = open(HTML, encoding="utf-8").read()
pat = re.compile(re.escape(START) + ".*?" + re.escape(END), re.S)
if not pat.search(html):
    sys.exit("markers not found in index.html")
html = pat.sub(lambda m: payload, html)
open(HTML, "w", encoding="utf-8").write(html)

feats = len(gj["features"])
print("Injected %d trail features (%.0f KB payload) into %s. New size: %.0f KB"
      % (feats, len(payload)/1024, HTML, os.path.getsize(HTML)/1024))
