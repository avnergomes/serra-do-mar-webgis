#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch REAL trail / road / railway geometry for the Serra do Mar paranaense
from OpenStreetMap via the Overpass API, curate it, and emit a compact GeoJSON.

Data (c) OpenStreetMap contributors, ODbL. Stdlib only.
Caches the raw Overpass response in osm_raw.json to avoid re-hitting the API.
"""
import json, sys, os, time, urllib.request, urllib.parse, math, re

ENDPOINTS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
RAW_CACHE = "osm_raw.json"

# Per-statement bboxes: (S, W, N, E)
# REGION spans the same extent as fetch_peaks.py. It used to stop at -25.20/-25.60,
# which silently excluded every range south of the core -- Serra da Prata, Serra da
# Igreja, Araçatuba and Quiriri, 41% of the peaks, had no trails at all.
REGION   = (-26.30, -49.50, -24.60, -48.20)   # whole Serra do Mar PR, as in fetch_peaks.py
RAIL     = (-25.56, -49.12, -25.40, -48.80)   # escarpment railway descent
PEAKS_GEOJSON = "peaks.geojson"
BUFFER_DEG = 0.02      # ~2 km around a massif's peaks, to catch trailheads and approaches

def bb(x):
    return "%f,%f,%f,%f" % x

def massif_boxes(path=PEAKS_GEOJSON):
    """Search boxes for footpaths, derived from where each named massif's peaks actually are.

    Hand-written boxes go stale the moment a massif is added or re-anchored, and a
    single region-wide footpath query would drag in every urban sidewalk in Curitiba.
    The generic 'Serra do Mar (PR)' bucket is skipped for exactly that reason: it is a
    catch-all spread across the whole state, not a place.
    """
    if not os.path.exists(path):
        print("  %s ausente: sem caixas por maciço" % path, file=sys.stderr)
        return []
    geo = json.load(open(path, encoding="utf-8"))
    groups = {}
    for f in geo["features"]:
        m = f["properties"].get("massif")
        if not m or m == "Serra do Mar (PR)":
            continue
        lon, lat = f["geometry"]["coordinates"][:2]
        g = groups.setdefault(m, [lat, lon, lat, lon])
        g[0] = min(g[0], lat); g[1] = min(g[1], lon)
        g[2] = max(g[2], lat); g[3] = max(g[3], lon)
    out = []
    for m in sorted(groups):
        s, w, n, e = groups[m]
        out.append((m, (s-BUFFER_DEG, w-BUFFER_DEG, n+BUFFER_DEG, e+BUFFER_DEG)))
    return out

MASSIF_BOXES = massif_boxes()

QUERY = "[out:json][timeout:240];\n(\n" + "".join([
    '  way["name"="Estrada da Graciosa"](%s);\n' % bb(REGION),
    '  way["name"~"Caminho do Itupava",i](%s);\n' % bb(REGION),
    '  relation["name"~"Itupava",i](%s);\n' % bb(REGION),
    '  relation["route"="hiking"](%s);\n' % bb(REGION),
    '  way["railway"="rail"](%s);\n' % bb(RAIL),
]) + "".join(
    '  way["highway"~"^(path|footway|track|steps)$"](%s);  // %s\n' % (bb(box), m)
    for m, box in MASSIF_BOXES
) + ");\nout geom;\n"

# ---- curation rules ----
EXCLUDE_WAY_NAME = re.compile(
    r"^(Rua|Travessa|Travessona|Avenida|Alameda|Rodovia|Linha)\b"
    r"|Job de Barros|Indiana Jones|Pinguela|^Ponte\b|^Passarela\b", re.I)
EXCLUDE_REL_NAME = re.compile(r"^Caminho da Mata Atl", re.I)   # regional mega-trails
MAX_KM = 50.0     # drop regional through-trails
MIN_KM_UNNAMED = 0.15  # drop tiny unnamed fragments
# A name is no proof a way was actually traced: OSM carries stubs of a couple of metres
# with grand names ("Rota Quiriri - Monte Crista" is 3 nodes spanning 1.5 m). They draw
# as an invisible dot and inflate the "named trails" count, so length decides, not the name.
MIN_KM_ANY = 0.05

HERO = {
    "Trilha do Pico Paraná","Trilha Pico Paraná","Caminho do Itupava","Estrada da Graciosa",
    "Trilha Frontal (branca)","Trilha Noroeste (vermelha)","Trilha Rochedinho (azul)",
    "Anhangava","Pico Caratuva","Estrada de Ferro Engenheiro Bley","Trilha Siririca",
}

def fetch(query):
    data = urllib.parse.urlencode({"data": query}).encode()
    last = None
    for ep in ENDPOINTS:
        for _ in range(2):
            try:
                req = urllib.request.Request(ep, data=data,
                    headers={"User-Agent": "serra-do-mar-webgis/1.0 (portfolio; OSM Overpass)"})
                with urllib.request.urlopen(req, timeout=180) as r:
                    raw = r.read().decode("utf-8", "replace")
                if raw.lstrip().startswith("{"):
                    d = json.loads(raw)
                    with open(RAW_CACHE, "w", encoding="utf-8") as f:
                        json.dump(d, f, ensure_ascii=False)
                    print("Fetched via %s (cached to %s)" % (ep, RAW_CACHE), file=sys.stderr)
                    return d
                last = "non-json (%d bytes)" % len(raw)
            except Exception as e:
                last = "%s: %s" % (type(e).__name__, e)
            time.sleep(3)
        print("  endpoint failed (%s): %s" % (ep, last), file=sys.stderr)
    raise SystemExit("All Overpass endpoints failed. Last: %s" % last)

def load():
    if os.path.exists(RAW_CACHE) and os.path.getsize(RAW_CACHE) > 100:
        print("Using cached %s" % RAW_CACHE, file=sys.stderr)
        return json.load(open(RAW_CACHE, encoding="utf-8"))
    return fetch(QUERY)

def classify(tags):
    if tags.get("railway") == "rail":
        return "ferrovia"
    name = tags.get("name", "")
    if tags.get("highway") in ("primary","secondary","tertiary","unclassified","residential") \
            or name == "Estrada da Graciosa":
        return "estrada"
    return "trilha"

# ---- geometry helpers ----
def _pd(p, a, b):
    (x,y),(x1,y1),(x2,y2) = p, a, b
    dx, dy = x2-x1, y2-y1
    if dx == 0 and dy == 0:
        return math.hypot(x-x1, y-y1)
    t = max(0, min(1, ((x-x1)*dx + (y-y1)*dy) / (dx*dx + dy*dy)))
    return math.hypot(x-(x1+t*dx), y-(y1+t*dy))

def simplify(c, tol=0.00008):
    if len(c) < 3:
        return c
    dmax, idx = 0, 0
    for i in range(1, len(c)-1):
        d = _pd(c[i], c[0], c[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax > tol:
        return simplify(c[:idx+1], tol)[:-1] + simplify(c[idx:], tol)
    return [c[0], c[-1]]

def hav(a, b):
    R = 6371.0
    (lon1,lat1),(lon2,lat2) = a, b
    p1,p2 = math.radians(lat1), math.radians(lat2)
    x = math.sin(math.radians(lat2-lat1)/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(math.radians(lon2-lon1)/2)**2
    return 2*R*math.asin(math.sqrt(x))

def line_km(c):
    return sum(hav(c[i], c[i+1]) for i in range(len(c)-1)) if len(c) > 1 else 0.0

def multi_km(segs):
    return sum(line_km(s) for s in segs)

def to_line(geom):
    return [[round(g["lon"],6), round(g["lat"],6)] for g in geom]

def build(d):
    ways = [e for e in d["elements"] if e["type"] == "way"]
    rels = [e for e in d["elements"] if e["type"] == "relation"]
    feats, dropped = [], {"regional":0, "street":0, "tiny":0, "unnamed_misc":0, "dup_rel":0}
    rel_names = set()

    # 1) route=hiking relations -> one feature each (segments merged)
    for r in rels:
        t = r.get("tags", {})
        nm = t.get("name", "")
        if EXCLUDE_REL_NAME.search(nm):
            dropped["regional"] += 1
            continue
        segs = [s for s in (simplify(to_line(m["geometry"])) for m in r.get("members", [])
                if m.get("type") == "way" and m.get("geometry") and len(m["geometry"]) >= 2) if len(s) >= 2]
        if not segs:
            continue
        km = multi_km(segs)
        if km > MAX_KM:
            dropped["regional"] += 1
            continue
        if nm:
            rel_names.add(nm)
        feats.append({"type":"Feature",
            "properties":{"name": nm or "Trilha", "kind":"trilha",
                          "km": round(km,1), "hero": (nm in HERO), "osm":"r%s"%r["id"]},
            "geometry":{"type":"MultiLineString","coordinates":segs}})

    # 2) named ways grouped by name (OSM splits one road into many segments)
    named = {}   # name -> {"segs":[...], "kind":str}
    for w in ways:
        t = w.get("tags", {})
        nm = t.get("name", "")
        hw = t.get("highway", "")
        rail = t.get("railway", "")
        if nm and EXCLUDE_WAY_NAME.search(nm):
            dropped["street"] += 1
            continue
        if not nm and rail != "rail" and hw not in ("path","steps"):
            dropped["unnamed_misc"] += 1
            continue
        g = w.get("geometry")
        if not g:
            continue
        c = simplify(to_line(g))
        if len(c) < 2:
            continue
        km = line_km(c)
        if km > MAX_KM:
            dropped["regional"] += 1
            continue
        kind = classify(t)
        if nm:
            if nm in rel_names:          # already covered by a hiking relation
                dropped["dup_rel"] += 1
                continue
            e = named.setdefault(nm, {"segs": [], "kind": kind})
            e["segs"].append(c)
            if kind != "trilha":         # roads/rail win over path classification
                e["kind"] = kind
        else:
            if km < MIN_KM_UNNAMED:
                dropped["tiny"] += 1
                continue
            feats.append({"type":"Feature",
                "properties":{"name": "", "kind": kind, "km": round(km,1), "hero": False, "osm":"w%s"%w["id"]},
                "geometry":{"type":"LineString","coordinates":c}})

    for nm, e in named.items():
        km = multi_km(e["segs"])
        # Judged on the merged total, not per segment: a real trail may legitimately have
        # a short piece, but a name whose every segment adds up to a couple of metres is a stub.
        if km < MIN_KM_ANY:
            dropped["stub"] = dropped.get("stub", 0) + 1
            continue
        feats.append({"type":"Feature",
            "properties":{"name": nm, "kind": e["kind"], "km": round(km,1), "hero": (nm in HERO)},
            "geometry":{"type":"MultiLineString","coordinates":e["segs"]}})

    return {"type":"FeatureCollection","features":feats}, dropped

def report(gj, dropped):
    from collections import Counter
    kinds = Counter(f["properties"]["kind"] for f in gj["features"])
    pts = sum(len(f["geometry"]["coordinates"]) if f["geometry"]["type"]=="LineString"
              else sum(len(s) for s in f["geometry"]["coordinates"]) for f in gj["features"])
    print("\n=== CURATED ===")
    print("features:", len(gj["features"]), "| by kind:", dict(kinds), "| points:", pts)
    print("dropped:", dropped)
    named = [f["properties"] for f in gj["features"] if f["properties"]["name"]]
    unnamed = len(gj["features"]) - len(named)
    print("\nNamed features: %d | unnamed trail segments: %d" % (len(named), unnamed))
    for p in sorted(named, key=lambda x: -x["km"]):
        star = "*" if p["hero"] else " "
        print(" %s %-42s %-9s %5.1f km" % (star, p["name"][:42], p["kind"], p["km"]))

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    d = load()
    gj, dropped = build(d)
    with open("serra_trails.geojson", "w", encoding="utf-8") as f:
        json.dump(gj, f, ensure_ascii=False, separators=(",", ":"))
    report(gj, dropped)
    print("\nWritten serra_trails.geojson (%.0f KB)" % (os.path.getsize("serra_trails.geojson")/1024))

if __name__ == "__main__":
    main()
