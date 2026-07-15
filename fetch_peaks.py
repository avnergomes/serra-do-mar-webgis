#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Atlas do montanhismo paranaense: fetch ALL named peaks of the Serra do Mar PR
from TWO sources (OpenStreetMap natural=peak + Wikidata mountains in Parana),
assign a massif/region, and write peaks.geojson.
Data: OSM (ODbL), Wikidata (CC0). Stdlib only."""
import json, sys, os, time, urllib.request, urllib.parse, math

OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
# full Serra do Mar paranaense mountaineering belt (S, W, N, E)
REGION = (-26.30, -49.50, -24.60, -48.20)
OSM_CACHE = "peaks_osm_raw.json"
WD_CACHE = "peaks_wikidata_raw.json"

# Massif anchors (name, lat, lon); nearest within RADIUS wins, else the generic bucket.
# Anchors sit on the namesake summit wherever one exists, because anchoring on a guessed
# centroid mis-sorted whole groups: the peak literally called "Morro dos Perdidos" used to
# land in "Serra da Igreja", while its neighbours 2 km away landed in "Morro dos Perdidos".
MASSIFS = [
    ("Ibitiraquire",       -25.25, -48.82),
    ("Marumbi",            -25.45, -48.92),
    ("Anhangava-Baitaca",  -25.39, -49.00),
    ("Serra do Canal",     -25.51, -48.98),
    ("Graciosa-Capivari",  -25.35, -48.905),
    ("Serra da Prata",     -25.62, -48.62),
    ("Serra da Igreja",    -25.75, -48.93),
    # Serra do Araçatuba (Tijucas do Sul / Guaratuba): anchored on Pico Araçatuba, 1.673 m,
    # the highest point of Paraná outside the Ibitiraquire. Morro dos Perdidos is a summit
    # inside this range, not a range of its own, so it no longer gets its own anchor.
    ("Serra do Araçatuba", -25.905, -48.990),
    # Serra do Quiriri, on the SC border, was being swallowed by the Perdidos anchor even
    # though it is a separate range ~12 km further south.
    ("Serra do Quiriri",   -26.015, -48.950),
]
RADIUS = 0.16  # deg (~17 km)

def http(url, data=None, headers=None, timeout=120):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def overpass(query, cache):
    if os.path.exists(cache) and os.path.getsize(cache) > 100:
        print("  using cache", cache, file=sys.stderr)
        return json.load(open(cache, encoding="utf-8"))
    data = urllib.parse.urlencode({"data": query}).encode()
    last = None
    for ep in OVERPASS:
        for _ in range(2):
            try:
                raw = http(ep, data=data, headers={"User-Agent": "serra-do-mar-atlas/1.0"}, timeout=180)
                if raw.lstrip().startswith("{"):
                    d = json.loads(raw)
                    json.dump(d, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
                    print("  overpass ok via", ep, file=sys.stderr)
                    return d
                last = "non-json %d bytes" % len(raw)
            except Exception as e:
                last = "%s: %s" % (type(e).__name__, e)
            time.sleep(3)
        print("  overpass fail", ep, last, file=sys.stderr)
    raise SystemExit("overpass failed: %s" % last)

def wikidata(cache):
    if os.path.exists(cache) and os.path.getsize(cache) > 100:
        print("  using cache", cache, file=sys.stderr)
        return json.load(open(cache, encoding="utf-8"))
    sparql = """
SELECT ?item ?itemLabel ?ele ?lat ?lon WHERE {
  ?item wdt:P31/wdt:P279* wd:Q8502 .
  ?item wdt:P131* wd:Q15499 .
  ?item p:P625 [ psv:P625 [ wikibase:geoLatitude ?lat ; wikibase:geoLongitude ?lon ] ] .
  OPTIONAL { ?item wdt:P2044 ?ele }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "pt,en" }
}"""
    url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(sparql)
    try:
        raw = http(url, headers={"User-Agent": "serra-do-mar-atlas/1.0 (avnerpaesgomes@gmail.com)",
                                 "Accept": "application/sparql-results+json"}, timeout=90)
        d = json.loads(raw)
        json.dump(d, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
        print("  wikidata ok", file=sys.stderr)
        return d
    except Exception as e:
        print("  wikidata FAILED (%s) - continuing with OSM only" % e, file=sys.stderr)
        return {"results": {"bindings": []}}

def massif_of(lat, lon):
    best, bd = None, 1e9
    for nm, la, lo in MASSIFS:
        d = math.hypot(lat - la, lon - lo)
        if d < bd:
            best, bd = nm, d
    return best if bd <= RADIUS else "Serra do Mar (PR)"

def fele(v):
    try:
        return round(float(str(v).replace(",", ".").split()[0]))
    except Exception:
        return None

def near(a, peaks, tol=0.004):  # ~450 m dedupe
    for p in peaks:
        if abs(a[0] - p["lat"]) < tol and abs(a[1] - p["lon"]) < tol:
            return p
    return None

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("Fetching OSM peaks ...", file=sys.stderr)
    osm = overpass("[out:json][timeout:120];node[\"natural\"=\"peak\"](%f,%f,%f,%f);out;" % REGION, OSM_CACHE)
    peaks = []
    for e in osm["elements"]:
        if e["type"] != "node":
            continue
        t = e.get("tags", {})
        nm = t.get("name")
        if not nm:
            continue
        peaks.append({"name": nm, "ele": fele(t.get("ele")), "lat": e["lat"], "lon": e["lon"],
                      "massif": massif_of(e["lat"], e["lon"]), "src": "osm"})
    print("OSM named peaks:", len(peaks), file=sys.stderr)

    print("Fetching Wikidata mountains ...", file=sys.stderr)
    wd = wikidata(WD_CACHE)
    added, enriched = 0, 0
    for b in wd["results"]["bindings"]:
        try:
            lat = float(b["lat"]["value"]); lon = float(b["lon"]["value"])
        except Exception:
            continue
        if not (REGION[0] <= lat <= REGION[2] and REGION[1] <= lon <= REGION[3]):
            continue
        nm = b.get("itemLabel", {}).get("value", "")
        ele = fele(b.get("ele", {}).get("value")) if "ele" in b else None
        m = near((lat, lon), peaks)
        if m:
            if m["ele"] is None and ele:
                m["ele"] = ele; enriched += 1
            if "wikidata" not in m["src"]:
                m["src"] = m["src"] + "+wikidata"
        elif nm and not nm.startswith("Q"):
            peaks.append({"name": nm, "ele": ele, "lat": lat, "lon": lon,
                          "massif": massif_of(lat, lon), "src": "wikidata"})
            added += 1
    print("Wikidata added:", added, "| enriched OSM ele:", enriched, file=sys.stderr)

    gj = {"type": "FeatureCollection", "features": [
        {"type": "Feature",
         "properties": {"name": p["name"], "ele": p["ele"], "massif": p["massif"], "src": p["src"]},
         "geometry": {"type": "Point", "coordinates": [round(p["lon"], 6), round(p["lat"], 6)]}}
        for p in peaks]}
    json.dump(gj, open("peaks.geojson", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    from collections import Counter
    bym = Counter(p["massif"] for p in peaks)
    withele = sum(1 for p in peaks if p["ele"])
    print("\n=== PEAKS ATLAS ===")
    print("total named peaks: %d | with elevation: %d | file %.0f KB"
          % (len(peaks), withele, os.path.getsize("peaks.geojson") / 1024))
    print("by massif/region:")
    for m, c in bym.most_common():
        print("  %-22s %d" % (m, c))
    print("top 15 by elevation:")
    for p in sorted([p for p in peaks if p["ele"]], key=lambda x: -x["ele"])[:15]:
        print("  %5d m  %-30s %-20s [%s]" % (p["ele"], p["name"][:30], p["massif"], p["src"]))

if __name__ == "__main__":
    main()
