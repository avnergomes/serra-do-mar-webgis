#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate en/index.html: the English entry point, for crawlers and shared links.

The in-page toggle already switches the whole atlas, but Open Graph tags and <title> are
read by Facebook, LinkedIn, WhatsApp and Google *before* any JavaScript runs. A single
Portuguese page therefore always previews in Portuguese, whatever language the reader sees.
So English gets a real URL, with its own head and its own share card.

It is a full copy rather than a redirect stub: /en/ is then a genuine, indexable page with
English content, and hreflang links the two so search engines treat them as translations
instead of duplicates. The duplication is safe because this file is generated, never edited:
run it after any change to index.html.
"""
import io, os, re, sys

SRC = "index.html"
OUT_DIR = "en"
OUT = os.path.join(OUT_DIR, "index.html")
SITE = "https://avnergomes.github.io/serra-do-mar-webgis/"

EN_TITLE = "Serra do Mar Paranaense · Mountaineering Atlas"
EN_DESC = ("Web GIS of the Serra do Mar in Paraná, Brazil: 273 summits, real OpenStreetMap "
           "trails, climbing routes, elevation profiles and an interactive story in 13 chapters.")

# Assets sit at the repo root; from /en/ they need one level up.
RELATIVE = ["favicon.svg", "favicon-32.png", "favicon-180.png",
            "vendor/leaflet.css", "vendor/leaflet.js"]


def build():
    sys.stdout.reconfigure(encoding="utf-8")
    if not os.path.exists(SRC):
        raise SystemExit("faltando %s" % SRC)
    h = io.open(SRC, encoding="utf-8").read()

    # ---- 1) assets one level up ----
    for a in RELATIVE:
        for attr in ('src="', 'href="'):
            h = h.replace(attr + a + '"', attr + "../" + a + '"')
        h = h.replace("'" + a + "'", "'../" + a + "'")   # the JS loader strings

    # ---- 2) html lang + title ----
    h = h.replace('<html lang="pt-BR">', '<html lang="en">', 1)
    h = re.sub(r"<title>.*?</title>", "<title>%s</title>" % EN_TITLE, h, count=1, flags=re.S)
    h = re.sub(r'<meta name="description" content="[^"]*" />',
               '<meta name="description" content="%s" />' % EN_DESC, h, count=1)

    # ---- 3) the brand block: English head, English card, /en/ URLs ----
    start, end = "  <!--__BRAND__-->\n", "  <!--__BRAND_END__-->\n"
    i, j = h.find(start), h.find(end)
    if i < 0 or j < 0:
        raise SystemExit("bloco __BRAND__ nao encontrado: rode make_brand.py antes")
    block = (
        '  <link rel="icon" href="../favicon.svg" type="image/svg+xml" />\n'
        '  <link rel="icon" href="../favicon-32.png" sizes="32x32" type="image/png" />\n'
        '  <link rel="apple-touch-icon" href="../favicon-180.png" />\n'
        '  <meta name="theme-color" content="#07110f" />\n'
        '  <link rel="canonical" href="%sen/" />\n'
        '  <link rel="alternate" hreflang="pt-BR" href="%s" />\n'
        '  <link rel="alternate" hreflang="en" href="%sen/" />\n'
        '  <link rel="alternate" hreflang="x-default" href="%s" />\n'
        '  <meta property="og:type" content="website" />\n'
        '  <meta property="og:site_name" content="Serra do Mar Mountaineering Atlas" />\n'
        '  <meta property="og:title" content="%s" />\n'
        '  <meta property="og:description" content="%s" />\n'
        '  <meta property="og:url" content="%sen/" />\n'
        '  <meta property="og:image" content="%sog-image-en.png" />\n'
        '  <meta property="og:image:width" content="1200" />\n'
        '  <meta property="og:image:height" content="630" />\n'
        '  <meta property="og:image:alt" content="Skyline of the Serra do Mar in Paraná from '
        'north to south, with Pico Paraná marked at 1,877 metres." />\n'
        '  <meta property="og:locale" content="en_US" />\n'
        '  <meta property="og:locale:alternate" content="pt_BR" />\n'
        '  <meta name="twitter:card" content="summary_large_image" />\n'
        '  <meta name="twitter:title" content="%s" />\n'
        '  <meta name="twitter:description" content="273 summits, real trails, climbing routes '
        'and elevation profiles in a self-contained Web GIS." />\n'
        '  <meta name="twitter:image" content="%sog-image-en.png" />\n'
    ) % (SITE, SITE, SITE, SITE, EN_TITLE, EN_DESC, SITE, SITE, EN_TITLE, SITE)
    h = h[:i] + start + block + end + h[j + len(end):]

    # ---- 4) this page defaults to English ----
    # An explicit choice in localStorage still wins: someone who picked Portuguese meant it,
    # even arriving on a shared /en/ link. PAGE_LANG only replaces the browser guess.
    old = "  return (navigator.language || 'pt').toLowerCase().indexOf('pt') === 0 ? 'pt' : 'en';"
    if old not in h:
        raise SystemExit("bloco de deteccao de idioma nao encontrado")
    h = h.replace(old, "  return 'en';   // generated page: /en/ is the English entry point", 1)

    os.makedirs(OUT_DIR, exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="").write(h)

    # ---- 5) the Portuguese page gets the matching hreflang ----
    p = io.open(SRC, encoding="utf-8").read()
    tags = ('  <link rel="canonical" href="%s" />\n'
            '  <link rel="alternate" hreflang="pt-BR" href="%s" />\n'
            '  <link rel="alternate" hreflang="en" href="%sen/" />\n'
            '  <link rel="alternate" hreflang="x-default" href="%s" />\n') % (SITE, SITE, SITE, SITE)
    p = re.sub(r'  <link rel="canonical".*?<link rel="alternate" hreflang="x-default"[^\n]*\n',
               "", p, flags=re.S)
    if '  <meta name="theme-color" content="#07110f" />\n' not in p:
        raise SystemExit("theme-color nao encontrado em index.html")
    p = p.replace('  <meta name="theme-color" content="#07110f" />\n',
                  '  <meta name="theme-color" content="#07110f" />\n' + tags, 1)
    p = p.replace('  <meta property="og:locale" content="pt_BR" />\n',
                  '  <meta property="og:locale" content="pt_BR" />\n'
                  '  <meta property="og:locale:alternate" content="en_US" />\n', 1)
    io.open(SRC, "w", encoding="utf-8", newline="").write(p)

    print("%s  %.0f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("  lang=en, og-image-en.png, canonical %sen/" % SITE)
    print("  assets remapeados: %s" % ", ".join(RELATIVE))
    print("%s: hreflang pt-BR/en/x-default adicionados" % SRC)


if __name__ == "__main__":
    build()
