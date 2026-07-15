#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bake elevation into serra_trails.geojson so the atlas can draw elevation profiles.

OSM ways carry no altitude, so every vertex is sampled against SRTM 30m via the
public OpenTopoData API and written back as the third ordinate ([lon, lat, ele]).
Doing this at build time keeps the published atlas free of a runtime dependency:
visitors never call the DEM service, so there is no rate limit, no latency and
nothing to break when the service is down.

Raw responses are cached in elevation_raw.json (gitignored, like the other
collectors). Delete it to force a re-query.
"""
import io, json, os, sys, time
import urllib.parse
import urllib.request, urllib.error

TRAILS = "serra_trails.geojson"
CACHE = "elevation_raw.json"
API = "https://api.opentopodata.org/v1/srtm30m"
BATCH = 100          # locations per request, the API's documented cap
SLEEP = 1.1          # the public endpoint allows 1 call/sec
RETRIES = 4


def iter_lines(geom):
    """Yield each coordinate list in a LineString or MultiLineString."""
    if geom["type"] == "LineString":
        yield geom["coordinates"]
    elif geom["type"] == "MultiLineString":
        for line in geom["coordinates"]:
            yield line


def key_of(pt):
    """SRTM is 30 m; 5 decimals (~1 m) is far finer than the data and dedupes exact repeats."""
    return (round(pt[0], 5), round(pt[1], 5))


def fetch_batch(points):
    """points: [(lon, lat), ...] -> [elev or None, ...]"""
    locs = "|".join("%.5f,%.5f" % (lat, lon) for lon, lat in points)
    url = "%s?locations=%s" % (API, urllib.parse.quote(locs, safe="|,-."))
    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "serra-do-mar-webgis/1.0"})
            with urllib.request.urlopen(req, timeout=45) as r:
                data = json.loads(r.read().decode("utf-8"))
            if data.get("status") != "OK":
                raise RuntimeError(data.get("error") or data.get("status"))
            return [x.get("elevation") for x in data["results"]]
        except Exception as err:
            last = err
            wait = SLEEP * (2 ** attempt)
            print("   retry %d/%d em %.1fs (%s)" % (attempt + 1, RETRIES, wait, err))
            time.sleep(wait)
    raise SystemExit("falhou apos %d tentativas: %s" % (RETRIES, last))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if not os.path.exists(TRAILS):
        raise SystemExit("faltando %s" % TRAILS)
    geo = json.load(io.open(TRAILS, encoding="utf-8"))

    # Collect every distinct vertex across every trail.
    wanted = []
    seen = set()
    for f in geo["features"]:
        for line in iter_lines(f["geometry"]):
            for pt in line:
                k = key_of(pt)
                if k not in seen:
                    seen.add(k)
                    wanted.append(k)

    cache = {}
    if os.path.exists(CACHE):
        raw = json.load(io.open(CACHE, encoding="utf-8"))
        cache = {tuple(map(float, k.split(","))): v for k, v in raw.items()}
        print("cache: %d pontos" % len(cache))

    todo = [p for p in wanted if p not in cache]
    print("vertices distintos: %d | ja em cache: %d | a buscar: %d"
          % (len(wanted), len(wanted) - len(todo), len(todo)))

    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        elevs = fetch_batch(chunk)
        for p, e in zip(chunk, elevs):
            cache[p] = e
        done = min(i + BATCH, len(todo))
        print("  %d/%d (%.0f%%)" % (done, len(todo), 100.0 * done / len(todo)))
        json.dump({"%s,%s" % k: v for k, v in cache.items()},
                  io.open(CACHE, "w", encoding="utf-8"))   # checkpoint every batch
        if done < len(todo):
            time.sleep(SLEEP)

    # Write the third ordinate back into every vertex.
    filled = missing = 0
    for f in geo["features"]:
        g = f["geometry"]
        if g["type"] == "LineString":
            g["coordinates"] = [_with_z(pt, cache) for pt in g["coordinates"]]
        elif g["type"] == "MultiLineString":
            g["coordinates"] = [[_with_z(pt, cache) for pt in line] for line in g["coordinates"]]
        for line in iter_lines(g):
            for pt in line:
                if len(pt) > 2:
                    filled += 1
                else:
                    missing += 1

    # Per-trail elevation stats, so the popup does not recompute them in the browser.
    for f in geo["features"]:
        eles = [pt[2] for line in iter_lines(f["geometry"]) for pt in line if len(pt) > 2]
        if not eles:
            continue
        gain = 0
        for line in iter_lines(f["geometry"]):
            zs = [pt[2] for pt in line if len(pt) > 2]
            for a, b in zip(zs, zs[1:]):
                if b > a:
                    gain += b - a
        f["properties"]["ele_min"] = int(min(eles))
        f["properties"]["ele_max"] = int(max(eles))
        f["properties"]["ele_gain"] = int(round(gain))

    json.dump(geo, io.open(TRAILS, "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))

    print("\nvertices com altitude: %d | sem: %d" % (filled, missing))
    print("%s: %.0f KB" % (TRAILS, os.path.getsize(TRAILS) / 1024))
    print("\namostra:")
    for f in sorted(geo["features"],
                    key=lambda x: -(x["properties"].get("ele_gain") or 0))[:8]:
        p = f["properties"]
        print("  %-38s %5s-%5s m  D+ %4s m  %s km" % (
            (p.get("name") or "(sem nome)")[:38], p.get("ele_min", "?"),
            p.get("ele_max", "?"), p.get("ele_gain", "?"), p.get("km", "?")))


def _with_z(pt, cache):
    e = cache.get(key_of(pt))
    if e is None:
        return [pt[0], pt[1]]
    return [pt[0], pt[1], int(round(e))]


if __name__ == "__main__":
    main()
