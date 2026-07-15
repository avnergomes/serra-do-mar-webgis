#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the favicon and the Open Graph image, then wire them into index.html.

The og-image is the real skyline of the Serra do Mar, built from the same peaks.geojson the
atlas plots: a horizon that *is* the data, rather than stock scenery, and one that stays
true when the data changes because it is regenerated from it. The stats under the title come
from the geojson files too, so the preview cannot quietly go stale.

The favicon does NOT use the data. The real skyline was tried there first and collapsed into
a green smudge at 16 px; an icon is a mark, not a chart. See the note above PEAK.

Outputs: favicon.svg, favicon-{16,32,180}.png, og-image.png (1200x630).
Idempotent: rerun after the data changes and both images plus the <head> follow.
"""
import io, json, os, re, sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

PEAKS = "peaks.geojson"
HTML = "index.html"
SITE = "https://avnergomes.github.io/serra-do-mar-webgis/"

# Straight from index.html's :root, so the brand cannot drift between page and preview.
BG       = (7, 17, 15)
ACCENT   = (18, 214, 154)
ACCENT_2 = (126, 224, 194)
TXT      = (233, 245, 240)
TXT_DIM  = (157, 180, 172)
IBITI    = (255, 90, 60)

F_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"
F_SEMI = r"C:\Windows\Fonts\seguisb.ttf"
F_REG  = r"C:\Windows\Fonts\segoeui.ttf"

SS = 3   # supersample: draw big, downscale, get anti-aliasing for free


def font(path, size):
    return ImageFont.truetype(path, size)


def load_peaks():
    d = json.load(open(PEAKS, encoding="utf-8"))
    out = []
    for f in d["features"]:
        p = f["properties"]
        if not p.get("ele"):
            continue
        lon, lat = f["geometry"]["coordinates"][:2]
        out.append({"name": p.get("name") or "", "ele": p["ele"], "lat": lat, "lon": lon})
    out.sort(key=lambda p: -p["lat"])          # north to south
    return out


def skyline(peaks, bins=84, floor=700, north=None, south=None):
    """A horizon: the highest summit at each step along the range, north to south.

    Three things had to be got right, each learned by getting it wrong first:
      * Plotting peaks in latitude order gives sawtooth noise, not a skyline, because
        neighbours in latitude can sit far apart in longitude. Max per bin is what an eye
        on the horizon actually sees.
      * `floor` drops isolated coastal hillocks that punch false canyons through the range
        (a 68 m morro sitting between two 1.500 m massifs).
      * Empty bins are interpolated, never smoothed with a rolling max: the rolling max
        spread each summit sideways and flattened the Pico Paraná into a mesa.
    """
    P = [p for p in peaks if p["ele"] >= floor
         and (north is None or p["lat"] <= north)
         and (south is None or p["lat"] >= south)]
    if len(P) < 2:
        return []
    latN, latS = P[0]["lat"], P[-1]["lat"]
    span = (latN - latS) or 1e-9
    buckets = [[] for _ in range(bins)]
    for p in P:
        i = min(bins - 1, int((latN - p["lat"]) / span * bins))
        buckets[i].append(p["ele"])
    raw = [max(b) if b else None for b in buckets]
    known = [i for i, v in enumerate(raw) if v is not None]
    if not known:
        return []
    out = []
    for i in range(bins):
        if raw[i] is not None:
            out.append(float(raw[i]))
            continue
        lo = [k for k in known if k < i]
        hi = [k for k in known if k > i]
        if lo and hi:
            a, b = lo[-1], hi[0]
            out.append(raw[a] + (raw[b] - raw[a]) * (i - a) / (b - a))
        else:
            out.append(float(raw[known[-1] if lo else known[0]]))
    return [(i / (bins - 1.0), e) for i, e in enumerate(out)]


def apex_index(xs):
    return max(range(len(xs)), key=lambda i: xs[i][1])


def ridge_path(xs, x0, x1, ytop, ybase, emin, emax):
    span = max(1.0, emax - emin)
    return [(x0 + f * (x1 - x0), ybase - (e - emin) / span * (ybase - ytop)) for f, e in xs]


def hx(c):
    return "#%02x%02x%02x" % c


# --------------------------------------------------------------------------- favicon
# A favicon is a mark, not a chart. The real 273-summit skyline was tried here first and
# collapsed into a green smudge at 16 px, where roughly five shapes fit and nothing else
# survives. So the icon is a drawn peak, at the proportions of the Pico Paraná's own
# profile: one dominant summit, a shoulder to the left, a notch to the right. The data
# story belongs to the og-image, which has 1200 px to tell it.
# Unit space, y down, (0,0) top-left of the square.
PEAK = [(-0.04, 0.90), (0.19, 0.62), (0.30, 0.71), (0.55, 0.23),
        (0.72, 0.55), (0.82, 0.47), (1.04, 0.90)]
SUMMIT = (0.55, 0.23)


def _peak_pts(S, inset=0.0):
    return [((x * (1 - 2 * inset) + inset) * S, (y * (1 - 2 * inset) + inset) * S)
            for x, y in PEAK]


def _favicon_master(with_dot):
    S = 180 * SS
    r = int(S * 0.22)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=r, fill=BG + (255,))

    pts = _peak_pts(S)
    # The mountain is drawn on its own layer and masked by the rounded square, else the
    # polygon runs past the corner radius and squares the bottom off.
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(layer, "RGBA").polygon(pts + [(S * 1.04, S), (-S * 0.04, S)],
                                          fill=ACCENT + (255,))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=r, fill=255)
    layer.putalpha(Image.composite(layer.split()[3], Image.new("L", (S, S), 0), mask))
    im.alpha_composite(layer)

    if with_dot:
        cx, cy = SUMMIT[0] * S, SUMMIT[1] * S
        rr = S * 0.052
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=BG + (255,))
        rr = S * 0.030
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(255, 255, 255, 255))
    return im


def make_favicon():
    # The summit dot is a smudge of grey at 16 px, where it lands on 1 pixel: the silhouette
    # alone reads better. Dropping detail at the smallest size is how icons are drawn.
    with_dot, plain = _favicon_master(True), _favicon_master(False)
    for size, name, src in [(180, "favicon-180.png", with_dot),
                            (32, "favicon-32.png", with_dot),
                            (16, "favicon-16.png", plain)]:
        src.resize((size, size), Image.LANCZOS).save(name)
        print("  %-16s %d x %d%s" % (name, size, size, "" if src is with_dot else "  (sem o ponto)"))


def make_favicon_svg():
    S = 64.0
    pts = _peak_pts(S)
    area = " ".join("%.2f,%.2f" % p for p in pts) + " %.2f,%.2f %.2f,%.2f" % (
        S * 1.04, S, -S * 0.04, S)
    sx, sy = SUMMIT[0] * S, SUMMIT[1] * S
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">\n'
        '  <defs><clipPath id="r"><rect width="64" height="64" rx="14"/></clipPath></defs>\n'
        '  <rect width="64" height="64" rx="14" fill="%s"/>\n'
        '  <polygon points="%s" fill="%s" clip-path="url(#r)"/>\n'
        '  <circle cx="%.2f" cy="%.2f" r="3.3" fill="%s"/>\n'
        '  <circle cx="%.2f" cy="%.2f" r="1.9" fill="#fff"/>\n'
        '</svg>\n'
    ) % (hx(BG), area, hx(ACCENT), sx, sy, hx(BG), sx, sy)
    open("favicon.svg", "w", encoding="utf-8").write(svg)
    print("  favicon.svg      vetorial")


# -------------------------------------------------------------------------- og-image
def make_og(stats):
    W, H = 1200, 630
    w, h = W * SS, H * SS
    im = Image.new("RGBA", (w, h), BG + (255,))

    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([w * 0.60, h * -0.40, w * 1.3, h * 0.55], fill=IBITI + (18,))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(w * 0.055)))
    d = ImageDraw.Draw(im, "RGBA")

    # The range gets its own band at the bottom; type never crosses it.
    xs = skyline(load_peaks(), bins=56, floor=700)
    emaxv = max(e for _, e in xs)
    eminv = min(e for _, e in xs)
    emin = eminv - (emaxv - eminv) * 0.55
    base, top = h * 1.03, h * 0.70
    pts = ridge_path(xs, -w * 0.03, w * 1.03, top, base, emin, emaxv)

    def fill_ridge(poly, c, a_top, a_bot):
        """Mint gradient under the ridge, as in the atlas's own elevation chart.

        A flat fill was invisible here: any dark green close to the background reads as
        background. The gradient is what separates the range from the night behind it.
        """
        grad = Image.new("L", (1, 256))
        for i in range(256):
            grad.putpixel((0, i), int(a_top + (a_bot - a_top) * i / 255.0))
        grad = grad.resize((w, int(base - top) + 2), Image.BILINEAR)
        band = Image.new("L", (w, h), 0)
        band.paste(grad, (0, int(top)))
        shape = Image.new("L", (w, h), 0)
        ImageDraw.Draw(shape).polygon(poly, fill=255)
        layer = Image.new("RGBA", (w, h), c + (0,))
        layer.putalpha(Image.composite(band, Image.new("L", (w, h), 0), shape))
        im.alpha_composite(layer)

    # A flatter copy behind reads as haze on the far ranges.
    back = [(x + w * 0.012, base - (base - y) * 0.60) for x, y in pts]
    fill_ridge(back + [(w * 1.03, h), (-w * 0.03, h)], ACCENT_2, 60, 6)
    d.line(back, fill=ACCENT_2 + (60,), width=int(1.5 * SS), joint="curve")

    fill_ridge(pts + [(w * 1.03, h), (-w * 0.03, h)], ACCENT, 120, 8)
    d.line(pts, fill=ACCENT + (255,), width=int(3.4 * SS), joint="curve")

    cx, cy = pts[apex_index(xs)]
    for rr, a in ((30 * SS, 38), (16 * SS, 85)):
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=ACCENT + (a,))
    rr = 7 * SS
    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(255, 255, 255, 255))
    d.text((cx + 40 * SS, cy - 21 * SS), "Pico Paraná",
           font=font(F_SEMI, int(18 * SS)), fill=TXT + (255,))
    d.text((cx + 40 * SS, cy + 2 * SS), "1.877 m  ·  o teto do Sul",
           font=font(F_BOLD, int(18 * SS)), fill=ACCENT + (255,))

    # Type lives in the top ~62%, the range in the bottom ~38%. They never meet.
    x = 66 * SS
    d.text((x, 54 * SS), "ATLAS DO MONTANHISMO  ·  WEB GIS",
           font=font(F_BOLD, int(16 * SS)), fill=ACCENT + (255,))
    d.text((x, 86 * SS),  "Serra do Mar", font=font(F_BOLD, int(74 * SS)), fill=TXT + (255,))
    d.text((x, 166 * SS), "Paranaense",   font=font(F_BOLD, int(74 * SS)), fill=ACCENT_2 + (255,))
    d.text((x, 262 * SS), "A muralha de granito entre o planalto e o litoral,",
           font=font(F_REG, int(22 * SS)), fill=TXT_DIM + (255,))
    d.text((x, 292 * SS), "mapeada cume a cume.",
           font=font(F_REG, int(22 * SS)), fill=TXT_DIM + (255,))

    y = 348 * SS
    f_v, f_l = font(F_BOLD, int(34 * SS)), font(F_SEMI, int(12 * SS))
    for i, (v, l) in enumerate(stats):
        sx = x + i * 158 * SS
        d.text((sx, y), v, font=f_v, fill=TXT + (255,))
        d.text((sx, y + 44 * SS), l, font=f_l, fill=TXT_DIM + (255,))
        if i:
            d.line([(sx - 28 * SS, y + 4 * SS), (sx - 28 * SS, y + 54 * SS)],
                   fill=(120, 190, 170, 80), width=max(1, SS))

    # Byline top-right: the bottom belongs to the silhouette.
    fb, fr = font(F_BOLD, int(17 * SS)), font(F_REG, int(17 * SS))
    tail = "·  Data & Geo"
    tw = d.textlength(tail, font=fr)
    nw = d.textlength("Avner Paes Gomes", font=fb)
    rx = w - 66 * SS - tw - 10 * SS - nw
    d.text((rx, 58 * SS), "Avner Paes Gomes", font=fb, fill=TXT + (255,))
    d.text((rx + nw + 10 * SS, 58 * SS), tail, font=fr, fill=TXT_DIM + (255,))

    im.convert("RGB").resize((W, H), Image.LANCZOS).save("og-image.png", optimize=True)
    print("  og-image.png     %d x %d, %.0f KB" % (W, H, os.path.getsize("og-image.png") / 1024))


def stats_from_data():
    peaks = json.load(open(PEAKS, encoding="utf-8"))["features"]
    out = [("%d" % len(peaks), "CUMES")]
    try:
        r = json.load(open("routes.geojson", encoding="utf-8"))["features"]
        out.append(("%d" % sum(f["properties"]["total"] for f in r), "VIAS DE ESCALADA"))
    except Exception:
        pass
    try:
        t = json.load(open("serra_trails.geojson", encoding="utf-8"))["features"]
        out.append(("%d" % sum(1 for f in t if f["properties"].get("name")), "TRILHAS REAIS"))
    except Exception:
        pass
    massifs = {f["properties"].get("massif") for f in peaks} - {"Serra do Mar (PR)", None}
    out.append(("%d" % len(massifs), "CONJUNTOS"))
    return out


def wire_html():
    """Idempotent: replace the block if present, else insert right after <title>."""
    html = open(HTML, encoding="utf-8").read()
    block = (
        '  <link rel="icon" href="favicon.svg" type="image/svg+xml" />\n'
        '  <link rel="icon" href="favicon-32.png" sizes="32x32" type="image/png" />\n'
        '  <link rel="apple-touch-icon" href="favicon-180.png" />\n'
        '  <meta name="theme-color" content="#07110f" />\n'
        '  <meta property="og:type" content="website" />\n'
        '  <meta property="og:site_name" content="Atlas do Montanhismo Paranaense" />\n'
        '  <meta property="og:title" content="Serra do Mar Paranaense · Atlas do Montanhismo" />\n'
        '  <meta property="og:description" content="Web GIS da Serra do Mar paranaense: 273 cumes,'
        ' trilhas reais do OpenStreetMap, vias de escalada, perfis de elevação e narrativa'
        ' interativa em 13 capítulos." />\n'
        '  <meta property="og:url" content="%s" />\n'
        '  <meta property="og:image" content="%sog-image.png" />\n'
        '  <meta property="og:image:width" content="1200" />\n'
        '  <meta property="og:image:height" content="630" />\n'
        '  <meta property="og:image:alt" content="Silhueta da Serra do Mar paranaense de norte a'
        ' sul, com o Pico Paraná destacado a 1.877 metros." />\n'
        '  <meta property="og:locale" content="pt_BR" />\n'
        '  <meta name="twitter:card" content="summary_large_image" />\n'
        '  <meta name="twitter:title" content="Serra do Mar Paranaense · Atlas do Montanhismo" />\n'
        '  <meta name="twitter:description" content="273 cumes, trilhas reais, vias de escalada e'
        ' perfis de elevação num Web GIS autocontido." />\n'
        '  <meta name="twitter:image" content="%sog-image.png" />\n'
    ) % (SITE, SITE, SITE)

    start, end = "  <!--__BRAND__-->\n", "  <!--__BRAND_END__-->\n"
    payload = start + block + end
    if start in html:
        html = re.sub(re.escape(start) + r".*?" + re.escape(end),
                      lambda m: payload, html, flags=re.S)
        how = "atualizado"
    else:
        anchor = re.search(r"[ \t]*<title>.*?</title>[ \t]*\n", html, re.S)
        if not anchor:
            raise SystemExit("<title> nao encontrado em %s" % HTML)
        html = html[:anchor.end()] + payload + html[anchor.end():]
        how = "inserido"
    open(HTML, "w", encoding="utf-8").write(html)
    print("  head %s (%d tags)" % (how, block.count("<link") + block.count("<meta")))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("favicon:")
    make_favicon()
    make_favicon_svg()
    print("og-image:")
    st = stats_from_data()
    print("  stats:", ", ".join("%s %s" % (v, l) for v, l in st))
    make_og(st)
    print("html:")
    wire_html()


if __name__ == "__main__":
    main()
