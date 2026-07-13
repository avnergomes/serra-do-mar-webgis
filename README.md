# Atlas do Montanhismo Paranaense — Web GIS 3D

Atlas interativo 3D das montanhas da Serra do Mar paranaense, no estilo das peças da GISCARTA (Mont Blanc): terreno 3D real, cumes, trilhas reais, locais de interesse e narrativa histórica. Arquivo único, autocontido, sem chave de API.

Por **Avner Paes Gomes** (Data & Geo) · [portfólio](https://avnergomes.github.io/portfolio) · **mapa ao vivo:** https://avnergomes.github.io/serra-do-mar-webgis/

## Como abrir

- **Local:** abra `index.html` no navegador (funciona via `file://`, todos os dados estão embutidos).
- **Hospedado:** já publicado em GitHub Pages (link acima). Precisa de conexão (tiles de terreno e satélite sob demanda).
- **Servidor local:** `py -3 -m http.server 8777` e acesse `http://localhost:8777/`.

## O que o atlas mostra

- **Terreno 3D** com imagem de satélite + relevo sombreado (exagero ajustável).
- **273 cumes nomeados** da Serra do Mar paranaense (Pico Paraná 1.877 m, Caratuva, Ibitirati, o maciço Marumbi, Anhangava-Baitaca, Serra do Canal, Serra da Prata, Morro dos Perdidos, Serra da Igreja), agrupados por região e rotulados por altitude (declutter automático).
- **75 trilhas e rotas reais** + segmentos, geometria do **OpenStreetMap**: travessia do Ibitiraquire, vias Frontal/Noroeste/Rochedinho do Marumbi, Caminho do Itupava, Estrada da Graciosa e a ferrovia Curitiba-Paranaguá (Serra Verde Express). Clique numa rota para nome e distância.
- **462 locais de interesse** (POIs) do OSM, com toggles por categoria: refúgios/abrigos, inícios de trilha, estacionamentos, mirantes, pontos de água, cachoeiras e campings.
- **36 unidades de conservação** (limites) do OSM: PE Pico do Marumbi, PE Pico Paraná, PE Serra da Baitaca, PE Roberto Ribas Lange, PE da Graciosa, PE do Boguaçu e outras, como contorno tracejado com preenchimento sutil (clique para nome e área).
- **Painel de dados**: barras de altitude dos cumes e distribuição por região (donut).
- **História interativa** em 6 capítulos, com câmera que voa a cada tema.
- **Legenda e camadas**: alternar trilhas, POIs (e por categoria), relevo, rótulos e exagero do terreno.

## Fontes de dados e atribuição (obrigatória)

| Camada | Fonte | Licença |
|---|---|---|
| Terreno (DEM) | AWS Terrain Tiles (Mapzen, USGS 3DEP, SRTM/NASA, GMTED2010) | domínio público / ODbL |
| Imagem de satélite | Esri World Imagery (Maxar, Earthstar) | ToS Esri (uso leve / atribuição) |
| Cumes, trilhas, POIs | © OpenStreetMap contributors (Overpass) | ODbL |
| Cumes (enriquecimento) | Wikidata | CC0 |
| Motor de mapa | MapLibre GL JS 4.7 | BSD |

A atribuição já aparece no rodapé do mapa. Mantenha-a visível. Cobertura de picos validada contra PeakVisor (OSM 273 ≈ PeakVisor 275 para o Paraná).

## Regenerar os dados

```bash
py -3 fetch_peaks.py        # cumes (OSM natural=peak + Wikidata) -> peaks.geojson
py -3 fetch_pois.py         # POIs (refúgios, água, mirantes, etc.) -> pois.geojson
py -3 fetch_parks.py        # unidades de conservação (OSM protected_area) -> parks.geojson
py -3 fetch_osm_trails.py   # trilhas/estradas/ferrovia (Overpass) -> serra_trails.geojson
py -3 embed_atlas.py        # injeta peaks + pois + parks no index.html
py -3 embed_trails.py       # injeta serra_trails.geojson no index.html
py -3 make_logo.py          # gera e injeta a logo do header (portfólio)
```

Os coletores cacheam o resultado bruto do Overpass/Wikidata (arquivos `*_raw.json`, ignorados no git). Ajuste bboxes e regras de curadoria no topo de cada `fetch_*.py`.

## Arquivos versionados

- `index.html` — a aplicação completa (todos os dados embutidos).
- `fetch_peaks.py` · `fetch_pois.py` · `fetch_osm_trails.py` — coletores OSM/Wikidata.
- `embed_atlas.py` · `embed_trails.py` · `make_logo.py` — injetores.
- `peaks.geojson` · `pois.geojson` · `serra_trails.geojson` — dados curados (também embutidos no HTML).

## Stack

MapLibre GL JS 4.7 · terreno raster-DEM (terrarium) · camadas GPU (circle/symbol) para 273 cumes + 462 POIs · GeoJSON · SVG dashboards · glyphs demotiles. Tokenless.
