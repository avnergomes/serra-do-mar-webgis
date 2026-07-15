#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Atlas do montanhismo paranaense: fetch conservation-unit boundaries
(protected areas / parks) of the Serra do Mar PR from OpenStreetMap and write
parks.geojson. Keeps parks/reserves, drops the huge APAs (sustainable-use).
Data (c) OpenStreetMap contributors, ODbL. Needs shapely."""
import json, sys, os, time, urllib.request, urllib.parse, math
from shapely.geometry import LineString, mapping
from shapely.ops import polygonize, unary_union

OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
CACHE = "parks_raw.json"
REGION = (-26.30, -49.50, -24.60, -48.20)  # S,W,N,E
CAP_KM2 = 150.0           # drop APAs and the huge far karst/coastal parks (keep mountaineering-scale UCs)
DEG2_TO_KM2 = 111.32 * 111.32 * math.cos(math.radians(25.5))

QUERY = """[out:json][timeout:180];
(
  relation["boundary"="protected_area"](%f,%f,%f,%f);
  relation["leisure"="nature_reserve"](%f,%f,%f,%f);
  way["boundary"="protected_area"](%f,%f,%f,%f);
  way["leisure"="nature_reserve"](%f,%f,%f,%f);
);
out geom;""" % (REGION * 4)

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

def classify(t):
    name = (t.get("name") or "")
    pt = (t.get("protection_title") or "")
    pc = t.get("protect_class") or ""
    blob = (name + " " + pt).lower()
    if "parque nacional" in blob or "parna" in blob:
        return ("PARNA", "Parque Nacional", "#38bdf8")
    if "área de proteção ambiental" in blob or blob.startswith("apa") or " apa" in blob or pc in ("5", "6"):
        return ("APA", "APA", None)          # dropped
    if "parque estadual" in blob or "parque natural" in blob or ("parque" in blob) or pc == "2":
        return ("PE", "Parque Estadual", "#2dd4bf")
    if "rppn" in blob or "reserva" in blob or t.get("leisure") == "nature_reserve":
        return ("Reserva", "Reserva Natural", "#a3e635")
    if "estação ecológica" in blob:
        return ("ESEC", "Estação Ecológica", "#c084fc")
    if "refúgio" in blob or "monumento" in blob:
        return ("Outro", "Unidade de conservação", "#facc15")
    return (None, None, None)

def ways_of(el):
    """Return list of coordinate-lists (lon,lat) for the boundary ways."""
    if el["type"] == "way":
        g = el.get("geometry") or []
        return [[(p["lon"], p["lat"]) for p in g]] if len(g) >= 2 else []
    out = []
    for m in el.get("members", []):
        if m.get("type") == "way" and m.get("role") in ("outer", "", None) and m.get("geometry"):
            g = m["geometry"]
            if len(g) >= 2:
                out.append([(p["lon"], p["lat"]) for p in g])
    return out

def build_polygon(coord_lists):
    lines = [LineString(c) for c in coord_lists if len(c) >= 2]
    if not lines:
        return None
    try:
        polys = list(polygonize(unary_union(lines)))
    except Exception:
        polys = []
    if not polys:
        return None
    geom = unary_union(polys)
    geom = geom.simplify(0.0012, preserve_topology=True)
    return geom

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("Fetching protected areas ...", file=sys.stderr)
    d = overpass(QUERY)
    feats, dropped = [], {"apa_or_big": 0, "no_geom": 0, "unnamed": 0, "dupe": 0, "other": 0}
    seen = set()
    for el in d["elements"]:
        t = el.get("tags", {})
        name = t.get("name")
        if not name:
            dropped["unnamed"] += 1
            continue
        klass, label, color = classify(t)
        if not klass or klass == "APA":
            dropped["apa_or_big"] += 1
            continue
        geom = build_polygon(ways_of(el))
        if geom is None or geom.is_empty:
            dropped["no_geom"] += 1
            continue
        km2 = geom.area * DEG2_TO_KM2
        if km2 > CAP_KM2:
            dropped["apa_or_big"] += 1
            continue
        # The name alone does not identify a unit: OSM carries the Graciosa park as two
        # relations spelled differently ("Parque Estadual Serra da Graciosa" and "Parque
        # Estadual da Graciosa"), so a name-only key kept both and inflated the count.
        # ref:CNUC is the federal registry id of the unit, so an equal code proves an
        # equal unit whatever the spelling. Both keys keep first-seen, and here every
        # tie-break agrees: the survivor is also the richer-tagged and larger polygon.
        keys = {name.lower()}
        if t.get("ref:CNUC"):
            keys.add(("cnuc", t["ref:CNUC"]))
        if keys & seen:
            dropped["dupe"] += 1
            continue
        seen |= keys
        feats.append({"type": "Feature",
            "properties": {"name": name, "klass": klass, "label": label, "color": color, "km2": round(km2, 1)},
            "geometry": mapping(geom)})
    feats.sort(key=lambda f: -f["properties"]["km2"])
    gj = {"type": "FeatureCollection", "features": feats}
    json.dump(gj, open("parks.geojson", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("\n=== UNIDADES DE CONSERVAÇÃO ===")
    print("kept: %d | dropped: %s | file %.0f KB" % (len(feats), dropped, os.path.getsize("parks.geojson") / 1024))
    for f in feats:
        p = f["properties"]
        print("  %-46s %-18s %8.1f km²" % (p["name"][:46], p["label"], p["km2"]))

if __name__ == "__main__":
    main()
