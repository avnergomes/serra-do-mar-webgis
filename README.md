# Atlas do Montanhismo Paranaense — Web GIS

Atlas interativo das montanhas da Serra do Mar paranaense: mapa 2D rápido e confiável com cumes, trilhas reais, locais de interesse, unidades de conservação e narrativa histórica, mais um **modo 3D opcional** (terreno real) acionado por um botão. Arquivo único, autocontido, sem chave de API.

Por **Avner Paes Gomes** (Data & Geo) · [portfólio](https://avnergomes.github.io/portfolio) · **mapa ao vivo:** https://avnergomes.github.io/serra-do-mar-webgis/

## Como abrir

- **Local:** abra `index.html` no navegador (o mapa 2D funciona via `file://`, todos os dados estão embutidos).
- **Hospedado:** já publicado em GitHub Pages (link acima). Precisa de conexão (tiles de satélite sob demanda; o 3D baixa o Cesium na primeira vez).
- **Servidor local:** `py -3 -m http.server 8777` e acesse `http://localhost:8777/`.

## 2D por padrão, 3D sob demanda

O mapa abre em **2D (Leaflet)** — leve, sem WebGL nem workers, renderiza de forma confiável em qualquer placa de vídeo (inclusive GPUs integradas Intel). O botão **3D** no topo carrega o **Cesium** sob demanda e mostra o mesmo território com **terreno 3D real** e imagem de satélite; o botão **2D** volta na hora. Assim o atlas nunca fica preso num motor 3D pesado, e o 3D só roda quando o usuário pede.

## O que o atlas mostra

- **273 cumes nomeados** da Serra do Mar paranaense (Pico Paraná 1.877 m, Caratuva, Ibitirati, o maciço Marumbi, Anhangava-Baitaca, Serra do Canal, Serra da Prata, Morro dos Perdidos, Serra da Igreja), coloridos por região e rotulados por altitude (cumes emblemáticos com rótulo fixo; demais ao passar o mouse ou tocar).
- **75 trilhas e rotas reais** + segmentos, geometria do **OpenStreetMap**: travessia do Ibitiraquire, vias Frontal/Noroeste/Rochedinho do Marumbi, Caminho do Itupava, Estrada da Graciosa e a ferrovia Curitiba-Paranaguá (Serra Verde Express). Clique numa rota para nome e distância.
- **462 locais de interesse** (POIs) do OSM, com toggles por categoria: refúgios/abrigos, inícios de trilha, estacionamentos, mirantes, pontos de água, cachoeiras e campings.
- **36 unidades de conservação** (limites) do OSM, como contorno tracejado com preenchimento sutil (clique para nome e área).
- **Painel de dados**: barras de altitude dos cumes e distribuição por região (donut).
- **História interativa** em 6 capítulos, com a câmera voando a cada tema (2D e 3D).
- **Modo 3D (Cesium)**: terreno real ArcGIS + satélite Esri, com os 273 cumes posicionados sobre o relevo.
- **Responsivo**: no celular, os painéis viram uma gaveta inferior com abas (História · Dados · Camadas) e os alvos de toque são ampliados.

## Fontes de dados e atribuição (obrigatória)

| Camada | Fonte | Licença |
|---|---|---|
| Imagem de satélite (2D e 3D) | Esri World Imagery (Maxar, Earthstar) | ToS Esri (uso leve / atribuição) |
| Terreno 3D (modo Cesium) | ArcGIS World Elevation 3D (Terrain3D) | ToS Esri, sem chave |
| Cumes, trilhas, POIs, parques | © OpenStreetMap contributors (Overpass) | ODbL |
| Cumes (enriquecimento) | Wikidata | CC0 |
| Motor 2D | Leaflet 1.9.4 | BSD |
| Motor 3D (opcional) | CesiumJS 1.124 | Apache 2.0 |

A atribuição já aparece no rodapé do mapa. Mantenha-a visível. Cobertura de picos validada contra PeakVisor (OSM 273 ≈ PeakVisor 275 para o Paraná). Nenhuma chave de API é necessária: 2D e 3D usam serviços públicos gratuitos.

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
- `vendor/leaflet.js` · `vendor/leaflet.css` · `vendor/images/` — Leaflet auto-hospedado (motor 2D).
- `fetch_peaks.py` · `fetch_pois.py` · `fetch_parks.py` · `fetch_osm_trails.py` — coletores OSM/Wikidata.
- `embed_atlas.py` · `embed_trails.py` · `make_logo.py` — injetores.
- `peaks.geojson` · `pois.geojson` · `parks.geojson` · `serra_trails.geojson` — dados curados (também embutidos no HTML).

## Stack

**Leaflet 1.9.4** (2D, main-thread, canvas para 273 cumes + 462 POIs, sem WebGL/workers) como padrão · **CesiumJS 1.124** carregado sob demanda para o modo 3D (terreno ArcGIS + satélite Esri) · GeoJSON para trilhas e parques · SVG para os dashboards. Tokenless.
