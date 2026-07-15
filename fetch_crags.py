#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Atlas do montanhismo paranaense: fetch rock climbing features (crags, boulders,
vias, cliffs) from OpenStreetMap and write crags.geojson. Includes natural cliff
geometry for coastal and mountain climbing zones. Stdlib only."""
import json, sys, os, time, urllib.request, urllib.parse

OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
CACHE = "crags_raw.json"

# mountain zones (S, W, N, E) - avoids the Curitiba urban core (west of -49.2)
ZONES = [
    (-25.56, -49.07, -25.20, -48.78),  # Marumbi / Ibitiraquire / Baitaca / Canal / Graciosa
    (-25.78, -48.78, -25.42, -48.48),  # Serra da Prata / coastal front (Morretes/Paranagua)
    (-26.10, -49.08, -25.58, -48.55),  # Guaratuba / Morro dos Perdidos / Serra da Igreja
]

def zone_union():
    parts = []
    for z in ZONES:
        b = "%f,%f,%f,%f" % z
        parts += [
            'nwr["sport"="climbing"](%s);' % b,
            'nwr["climbing"](%s);' % b,
            'way["natural"="cliff"](%s);' % b,
        ]
    return "[out:json][timeout:180];(" + "".join(parts) + ");out center tags geom;"

def overpass(query):
    if os.path.exists(CACHE) and os.path.getsize(CACHE) > 100:
        print("  using cache", CACHE, file=sys.stderr)
        return json.load(open(CACHE, encoding="utf-8"))
    data = urllib.parse.urlencode({"data": query}).encode()
    last = None
    for ep in OVERPASS:
        for _ in range(2):
            try:
                req = urllib.request.Request(ep, data=data, headers={"User-Agent": "serra-do-mar-atlas/1.0"})
                with urllib.request.urlopen(req, timeout=180) as r:
                    raw = r.read().decode("utf-8", "replace")
                if raw.lstrip().startswith("{"):
                    d = json.loads(raw)
                    json.dump(d, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
                    print("  overpass ok via", ep, file=sys.stderr)
                    return d
                last = "non-json %d bytes" % len(raw)
            except Exception as e:
                last = "%s: %s" % (type(e).__name__, e)
            time.sleep(3)
        print("  overpass fail", ep, last, file=sys.stderr)
    raise SystemExit("overpass failed: %s" % last)

def categorize(t):
    climbing = t.get("climbing")
    climbing_boulder = t.get("climbing:boulder")
    sport = t.get("sport")
    natural = t.get("natural")
    if climbing == "route_bottom":
        return ("via", "Via de escalada", "🧗", "#e76f51")
    if climbing == "boulder" or climbing_boulder == "yes":
        return ("boulder", "Boulder", "🪨", "#c77dff")
    if climbing == "crag":
        return ("setor", "Setor de escalada", "⛰️", "#f4845f")
    if climbing == "area":
        return ("area", "Área de escalada", "🗺️", "#ffb703")
    if natural == "cliff":
        return ("paredao", "Paredão / costão", "🧱", "#adb5bd")
    if sport == "climbing":
        return ("escalada", "Escalada (genérico)", "🧗", "#e76f51")
    return (None, None, None, None)

GRADE_PREFIX = "climbing:grade:"

def extract_grades(t):
    grades = {}
    for k, v in t.items():
        if k.startswith(GRADE_PREFIX):
            grades[k[len(GRADE_PREFIX):]] = v
    return grades if grades else None

def extract_styles(t):
    styles = []
    style_keys = [
        ("climbing:sport", "sport"),
        ("climbing:trad", "trad"),
        ("climbing:boulder", "boulder"),
        ("climbing:toprope", "toprope"),
        ("climbing:multipitch", "multipitch"),
        ("climbing:ice", "ice"),
        ("climbing:mixed", "mixed"),
    ]
    for key, suffix in style_keys:
        if t.get(key) == "yes":
            styles.append(suffix)
    return styles if styles else None

def try_int(v):
    try:
        return int(v)
    except (ValueError, TypeError):
        return v

def line_of(e):
    # "out geom" returns the vertex list under "geometry" (not "geom").
    return [p for p in e.get("geometry", e.get("geom", [])) if p.get("lat") is not None]

def point_of(e):
    if e["type"] == "node":
        return e.get("lat"), e.get("lon")
    c = e.get("center")
    if c:
        return c.get("lat"), c.get("lon")
    b = e.get("bounds")  # what "out geom" gives instead of a center
    if b:
        return (b["minlat"] + b["maxlat"]) / 2.0, (b["minlon"] + b["maxlon"]) / 2.0
    g = line_of(e)
    if g:
        return sum(p["lat"] for p in g) / len(g), sum(p["lon"] for p in g) / len(g)
    return None, None

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("Fetching crags ...", file=sys.stderr)
    d = overpass(zone_union())
    feats, seen = [], set()
    for e in d["elements"]:
        t = e.get("tags", {})
        cat, label, emoji, color = categorize(t)
        if not cat:
            continue
        if cat == "paredao":
            g = line_of(e)
            if len(g) < 2:
                continue
            coords = [[round(pt["lon"], 6), round(pt["lat"], 6)] for pt in g]
            key = (cat, round(g[0]["lon"], 5), round(g[0]["lat"], 5), len(coords))
            if key in seen:
                continue
            seen.add(key)
            geom = {"type": "LineString", "coordinates": coords}
        else:
            lat, lon = point_of(e)
            if lat is None or lon is None:
                continue
            key = (cat, round(lat, 5), round(lon, 5))
            if key in seen:
                continue
            seen.add(key)
            geom = {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]}
        props = {"name": t.get("name", ""), "cat": cat, "label": label, "emoji": emoji, "color": color}
        grades = extract_grades(t)
        if grades:
            props["grades"] = grades
        if "climbing:routes" in t:
            props["routes"] = try_int(t["climbing:routes"])
        if "climbing:length" in t:
            props["length"] = try_int(t["climbing:length"])
        if "climbing:bolts" in t:
            props["bolts"] = try_int(t["climbing:bolts"])
        if "climbing:pitches" in t:
            props["pitches"] = try_int(t["climbing:pitches"])
        if "rock" in t:
            props["rock"] = t["rock"]
        styles = extract_styles(t)
        if styles:
            props["styles"] = styles
        feats.append({"type": "Feature", "properties": props, "geometry": geom})
    gj = {"type": "FeatureCollection", "features": feats}
    json.dump(gj, open("crags.geojson", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    from collections import Counter
    byc = Counter(f["properties"]["cat"] for f in feats)
    named = sum(1 for f in feats if f["properties"]["name"])
    graded = sum(1 for f in feats if "grades" in f["properties"])
    print("\n=== ESCALADA ATLAS ===")
    print("total feicoes: %d | nomeadas: %d | com grau: %d | file %.0f KB" % (len(feats), named, graded, os.path.getsize("crags.geojson") / 1024))
    for c, n in byc.most_common():
        print("  %-12s %d" % (c, n))

if __name__ == "__main__":
    main()
