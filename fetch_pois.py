#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Atlas do montanhismo paranaense: fetch points of interest (refuges, parking,
water, viewpoints, waterfalls, camps, trailheads) from OpenStreetMap and write
pois.geojson. Restricted to the mountain zones to avoid urban noise.
Data (c) OpenStreetMap contributors, ODbL. Stdlib only."""
import json, sys, os, time, urllib.request, urllib.parse

OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
CACHE = "pois_raw.json"

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
            'nwr["tourism"~"^(alpine_hut|wilderness_hut)$"](%s);' % b,
            'nwr["amenity"="shelter"](%s);' % b,
            'nwr["amenity"="parking"](%s);' % b,
            'nwr["tourism"="viewpoint"](%s);' % b,
            'nwr["tourism"="camp_site"](%s);' % b,
            'nwr["amenity"="drinking_water"](%s);' % b,
            'nwr["natural"="spring"](%s);' % b,
            'nwr["waterway"="waterfall"](%s);' % b,
            'nwr["information"="trailhead"](%s);' % b,
            'nwr["highway"="trailhead"](%s);' % b,
        ]
    return "[out:json][timeout:180];(" + "".join(parts) + ");out center tags;"

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

# category -> (label, emoji, color)
def categorize(t):
    tour = t.get("tourism"); am = t.get("amenity"); nat = t.get("natural")
    ww = t.get("waterway"); info = t.get("information"); hw = t.get("highway")
    if tour in ("alpine_hut", "wilderness_hut") or am == "shelter":
        return ("refugio", "Refúgio / abrigo", "🏠", "#f4a261")
    if hw == "trailhead" or info == "trailhead":
        return ("trailhead", "Início de trilha", "🥾", "#b5e48c")
    if am == "parking":
        return ("parking", "Estacionamento", "🅿️", "#8ecae6")
    if tour == "viewpoint":
        return ("mirante", "Mirante", "🔭", "#e9c46a")
    if tour == "camp_site":
        return ("camping", "Camping", "⛺", "#95d5b2")
    if am == "drinking_water" or nat == "spring":
        return ("agua", "Água", "💧", "#48cae4")
    if ww == "waterfall":
        return ("cachoeira", "Cachoeira", "💦", "#90e0ef")
    return (None, None, None, None)

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("Fetching POIs ...", file=sys.stderr)
    d = overpass(zone_union())
    feats, seen = [], set()
    for e in d["elements"]:
        t = e.get("tags", {})
        cat, label, emoji, color = categorize(t)
        if not cat:
            continue
        if e["type"] == "node":
            lat, lon = e.get("lat"), e.get("lon")
        else:
            c = e.get("center", {}); lat, lon = c.get("lat"), c.get("lon")
        if lat is None or lon is None:
            continue
        key = (cat, round(lat, 5), round(lon, 5))
        if key in seen:
            continue
        seen.add(key)
        feats.append({"type": "Feature",
            "properties": {"name": t.get("name", ""), "cat": cat, "label": label, "emoji": emoji, "color": color},
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]}})
    gj = {"type": "FeatureCollection", "features": feats}
    json.dump(gj, open("pois.geojson", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    from collections import Counter
    byc = Counter(f["properties"]["cat"] for f in feats)
    named = sum(1 for f in feats if f["properties"]["name"])
    print("\n=== POIs ATLAS ===")
    print("total POIs: %d | named: %d | file %.0f KB" % (len(feats), named, os.path.getsize("pois.geojson") / 1024))
    for c, n in byc.most_common():
        print("  %-12s %d" % (c, n))

if __name__ == "__main__":
    main()
