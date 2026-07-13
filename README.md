# Serra do Mar Paranaense — Web GIS 3D

Visualização Web GIS 3D interativa da Serra do Mar paranaense, no estilo das peças da GISCARTA (Mont Blanc): terreno 3D real, cumes, trilhas reais, dashboards e narrativa histórica. Arquivo único, autocontido, sem chave de API.

Por **Avner Paes Gomes** (Data & Geo).

## Como abrir

- **Local:** basta abrir `index.html` no navegador (funciona via `file://`, todos os dados estão embutidos).
- **Hospedado (recomendado para o LinkedIn):** suba a pasta em GitHub Pages, Netlify ou similar e compartilhe o link. Precisa de conexão (os tiles de terreno e satélite são carregados sob demanda).
- **Servidor local para teste:** `py -3 -m http.server 8777` e acesse `http://localhost:8777/`.

## O que a peça mostra

- **Terreno 3D** drapeado com imagem de satélite + relevo sombreado (exagero ajustável).
- **16 cumes** da Serra do Mar PR (Pico Paraná 1.877 m, Caratuva 1.860 m, o maciço Marumbi, Anhangava, etc.), coordenadas e altitudes conferidas contra OSM / pt.Wikipedia / IBGE.
- **65 trilhas e rotas reais** + segmentos, geometria do **OpenStreetMap** (traçados reais de GPS): a travessia do Ibitiraquire, Trilha do Pico Paraná, as vias Frontal/Noroeste/Rochedinho do Marumbi, o Caminho do Itupava, a Estrada da Graciosa e a ferrovia Curitiba-Paranaguá (Serra Verde Express). Clique numa rota para nome e distância.
- **Dashboards** estilo GISCARTA: barras de altitude dos cumes e distribuição por maciço (donut).
- **História interativa** em 6 capítulos, com câmera que voa a cada tema (fatos e fontes reais).
- **Legenda e camadas**: alternar trilhas, relevo, rótulos, e exagero do terreno.

## Fontes de dados e atribuição (obrigatória)

| Camada | Fonte | Licença |
|---|---|---|
| Terreno (DEM) | AWS Terrain Tiles (Mapzen, USGS 3DEP, SRTM/NASA, GMTED2010) | domínio público / ODbL |
| Imagem de satélite | Esri World Imagery (Maxar, Earthstar) | ToS Esri (uso leve / atribuição) |
| Trilhas, estradas, ferrovia | © OpenStreetMap contributors | ODbL |
| Cumes | OSM / pt.Wikipedia / IBGE | — |
| Motor de mapa | MapLibre GL JS | BSD |

A atribuição já aparece no rodapé do mapa. Mantenha-a visível.

## Regenerar as trilhas do OSM

```bash
py -3 fetch_osm_trails.py     # busca no Overpass, cura e escreve serra_trails.geojson (usa cache osm_raw.json)
py -3 embed_trails.py         # injeta serra_trails.geojson dentro do index.html
```

Ajuste as bboxes / regras de curadoria no topo de `fetch_osm_trails.py` (MAX_KM, MIN_KM_UNNAMED, exclusões).

## Arquivos

- `index.html` — a aplicação completa (dados embutidos).
- `fetch_osm_trails.py` — busca e curadoria das trilhas reais do OpenStreetMap.
- `embed_trails.py` — injeta o GeoJSON no HTML.
- `serra_trails.geojson` — trilhas reais curadas (também embutidas no HTML).
- `osm_raw.json` — cache bruto do Overpass.

## Stack

MapLibre GL JS 4.7 · terreno raster-DEM (terrarium) · GeoJSON · SVG dashboards · sem dependências além do MapLibre (CDN). Tokenless.
