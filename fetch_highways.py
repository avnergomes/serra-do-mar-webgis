#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch the main road network of the Serra do Mar paranaense from OpenStreetMap
so the atlas has location-reference highways: the federal trunk roads the user
asked for (BR-277, BR-116, BR-376) plus the Curitiba beltway (Rodoanel /
Contorno), and the state highways (PR-*) that are the real access roads to the
massifs. Emits a compact highways.geojson, one feature per road (segments merged).

Data (c) OpenStreetMap contributors, ODbL. Stdlib only.
Caches the raw Overpass response in highways_raw.json to avoid re-hitting the API.
"""
import json, sys, os, time, urllib.request, urllib.parse, math, re

ENDPOINTS = [
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
RAW_CACHE = "highways_raw.json"
OUT = "highways.geojson"

# Same extent as fetch_peaks.py / fetch_osm_trails.py: the whole Serra do Mar PR
# plus Curitiba, so the reference roads reach from the capital to the coast.
REGION = (-26.30, -49.50, -24.60, -48.20)   # (S, W, N, E)

def bb(x):
    return "%f,%f,%f,%f" % x

# Federal trunk roads the client named, the belt included. Curitiba's ring road is
# tagged in OSM as "Rodoanel Contorno Leste" / "Rodoanel Contorno Sul", so name
# catches it even where the ref is shared with BR-116/BR-476.
FED_REFS = ("BR-277", "BR-116", "BR-376")
QUERY = (
    "[out:json][timeout:240];\n(\n"
    '  way["highway"]["ref"~"^BR-(277|116|376)"](%s);\n' % bb(REGION) +
    '  way["highway"]["name"~"^Rodoanel",i](%s);\n' % bb(REGION) +
    '  way["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]["ref"~"^PR-"](%s);\n' % bb(REGION) +
    ");\nout geom;\n"
)

# ---- geometry helpers (same math as fetch_osm_trails.py) ----
def _pd(p, a, b):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(x - x1, y - y1)
    t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))

MIN_KM_ACCESS = 2.0   # drop PR stubs: short connectors add clutter, not reference value
# The Estrada da Graciosa (PR-410) is already a named, described road on the trails
# layer; drawing it again here would double-line the most emblematic access road.
EXCLUDE_KEYS = {"PR-410"}

def simplify(c, tol=0.00035):   # ~35 m: highways are reference lines, not trails
    if len(c) < 3:
        return c
    dmax, idx = 0, 0
    for i in range(1, len(c) - 1):
        d = _pd(c[i], c[0], c[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax > tol:
        return simplify(c[:idx + 1], tol)[:-1] + simplify(c[idx:], tol)
    return [c[0], c[-1]]

def hav(a, b):
    R = 6371.0
    (lon1, lat1), (lon2, lat2) = a, b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    x = math.sin(math.radians(lat2 - lat1) / 2) ** 2 + \
        math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))

def line_km(c):
    return sum(hav(c[i], c[i + 1]) for i in range(len(c) - 1)) if len(c) > 1 else 0.0

def to_line(geom):
    return [[round(g["lon"], 6), round(g["lat"], 6)] for g in geom]

# ---- fetch / cache ----
def fetch(query):
    data = urllib.parse.urlencode({"data": query}).encode()
    last = None
    for ep in ENDPOINTS:
        for _ in range(2):
            try:
                req = urllib.request.Request(ep, data=data,
                    headers={"User-Agent": "serra-do-mar-webgis/1.0 (portfolio; OSM Overpass)"})
                with urllib.request.urlopen(req, timeout=200) as r:
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

# ---- classification / grouping ----
def group_of(tags):
    """Return (group_key, kind, label) or None to drop.

    One feature per road: federal roads group by their BR ref, the beltway by the
    name "Rodoanel", the state network by its PR ref. Concurrency segments
    ("BR-116;BR-277") fall to the first federal ref we care about, so their
    geometry is drawn once, not twice.
    """
    name = tags.get("name", "") or ""
    ref = tags.get("ref", "") or ""
    if re.match(r"^Rodoanel", name, re.I):
        return ("Rodoanel", "rodovia", "Rodoanel")
    tokens = [t.strip() for t in ref.replace(",", ";").split(";") if t.strip()]
    for fr in FED_REFS:                       # priority order = FED_REFS order
        if fr in tokens:
            return (fr, "rodovia", fr)
    for tk in tokens:
        if tk.startswith("PR-"):
            return (tk, "acesso", tk)
    return None

def clean_name(nm):
    """OSM names carry the road's proper name; strip the marginal/duplicate noise."""
    nm = re.sub(r"^Marginal( (Norte|Sul|Leste|Oeste|d[ao]))? ", "", nm, flags=re.I).strip()
    return nm

def build(d):
    ways = [e for e in d["elements"] if e["type"] == "way"]
    groups = {}   # key -> {"kind","label","segs":[...],"names":{name:count}}
    for w in ways:
        t = w.get("tags", {})
        g = w.get("geometry")
        if not g:
            continue
        gr = group_of(t)
        if not gr:
            continue
        key, kind, label = gr
        c = simplify(to_line(g))
        if len(c) < 2:
            continue
        e = groups.setdefault(key, {"kind": kind, "label": label, "segs": [], "names": {}})
        e["segs"].append(c)
        nm = clean_name(t.get("name", "") or "")
        # The beltway's own name is the label; any other name is the road's proper name.
        if nm and not re.match(r"^Rodoanel", nm, re.I):
            e["names"][nm] = e["names"].get(nm, 0) + 1

    feats = []
    for key, e in groups.items():
        if key in EXCLUDE_KEYS:
            continue
        km = sum(line_km(s) for s in e["segs"])
        if e["kind"] == "acesso" and km < MIN_KM_ACCESS:
            continue
        name = max(e["names"], key=e["names"].get) if e["names"] else ""
        feats.append({
            "type": "Feature",
            "properties": {"ref": key, "label": e["label"], "name": name,
                           "kind": e["kind"], "km": round(km, 1)},
            "geometry": {"type": "MultiLineString", "coordinates": e["segs"]},
        })
    # federal first, then by length: the map draws them in this order (federal on top)
    feats.sort(key=lambda f: (f["properties"]["kind"] != "rodovia", -f["properties"]["km"]))
    return {"type": "FeatureCollection", "features": feats}

def report(gj):
    from collections import Counter
    kinds = Counter(f["properties"]["kind"] for f in gj["features"])
    pts = sum(sum(len(s) for s in f["geometry"]["coordinates"]) for f in gj["features"])
    print("\n=== HIGHWAYS ===")
    print("features:", len(gj["features"]), "| by kind:", dict(kinds), "| points:", pts)
    for f in gj["features"]:
        p = f["properties"]
        print("  %-9s %-10s %6.1f km  %s" % (p["kind"], p["ref"], p["km"], p["name"]))

def main():
    d = load()
    gj = build(d)
    report(gj)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(gj, f, ensure_ascii=False, separators=(",", ":"))
    print("\nWrote %s (%.0f KB)" % (OUT, os.path.getsize(OUT) / 1024))

if __name__ == "__main__":
    main()
