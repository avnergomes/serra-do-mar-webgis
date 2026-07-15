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

- **273 cumes nomeados** da Serra do Mar paranaense, agrupados em 9 conjuntos nomeados (Ibitiraquire, Marumbi, Anhangava-Baitaca, Graciosa-Capivari, Serra do Canal, Serra da Prata, Serra da Igreja, Serra do Araçatuba e Serra do Quiriri) mais um balde genérico, coloridos por região e rotulados por altitude (cumes emblemáticos com rótulo fixo; demais ao passar o mouse ou tocar).
- **127 trilhas e rotas reais** nomeadas (326 feições no total), geometria do **OpenStreetMap**, cobrindo os nove conjuntos: travessia do Ibitiraquire, vias Frontal/Noroeste/Rochedinho do Marumbi, Caminho do Itupava, Torre da Prata, a travessia Araçatuba-Monte Crista, a Estrada da Graciosa e a ferrovia Curitiba-Paranaguá (Serra Verde Express).
- **Perfil de elevação ao clicar num caminho**: a trilha clicada é destacada e o popup traz o perfil (altitude máxima, mínima, D+ e D−), com o ponto exato do clique marcado. Passar o mouse pelo perfil mostra a altitude e a distância naquele ponto, e um marcador acompanha no mapa. Vale para as trilhas do OSM e para os GPX enviados.
- **462 locais de interesse** (POIs) do OSM, com toggles por categoria: refúgios/abrigos, inícios de trilha, estacionamentos, mirantes, pontos de água, cachoeiras e campings.
- **36 unidades de conservação** (limites) do OSM, como contorno tracejado com preenchimento sutil (clique para nome e área).
- **440 vias de escalada** (322 vias + 118 boulders) em **11 montanhas**, vindas da planilha `Lista de Rotas de Escalada.xlsx`: Anhangava (com os boulders do Castelinhos), Morro do Canal, o maciço Marumbi (Abrolhos, Esfinge, Torre dos Sinos, Ponta do Tigre, Gigante, Olimpo) e o Ibitiraquire (Ferraria, Ibitirati, Itapiroca). Clique numa área para a lista completa, agrupada por setor, com grau, altura e ano de conquista. Marcador colorido pela faixa de dificuldade dominante.
- **27 paredões / costões naturais** (`natural=cliff`) do OSM, como linha tracejada de contexto.
- **Envio de GPX**: qualquer visitante arrasta um `.gpx` na aba GPX e vê a trilha e os pontos no mapa na hora, com distância calculada. Com o backend publicado (`gas/`), o arquivo vai para o Google Drive e volta para todo mundo depois de aprovado; sem backend, tudo continua funcionando só no navegador dele.
- **Painel de dados**: barras de altitude dos cumes e distribuição por região (donut).
- **História interativa** em 13 capítulos, um para cada conjunto montanhoso (norte a sul) mais os temáticos (Mata Atlântica, geologia, Graciosa, ferrovia), com a câmera voando a cada tema (2D e 3D) num zoom escolhido por capítulo.
- **Modo 3D (Cesium)**: terreno real ArcGIS + satélite Esri, com os 273 cumes posicionados sobre o relevo.
- **Responsivo**: no celular, os painéis viram uma gaveta inferior com abas (História · Dados · Camadas) e os alvos de toque são ampliados.

## Fontes de dados e atribuição (obrigatória)

| Camada | Fonte | Licença |
|---|---|---|
| Imagem de satélite (2D e 3D) | Esri World Imagery (Maxar, Earthstar) | ToS Esri (uso leve / atribuição) |
| Terreno 3D (modo Cesium) | ArcGIS World Elevation 3D (Terrain3D) | ToS Esri, sem chave |
| Cumes, trilhas, POIs, parques, paredões | © OpenStreetMap contributors (Overpass) | ODbL |
| Altitude das trilhas (perfil) | SRTM 30m via OpenTopoData | CC BY 4.0 (NASA/USGS) |
| Cumes (enriquecimento) | Wikidata | CC0 |
| Vias de escalada | `Lista de Rotas de Escalada.xlsx` (compilação da comunidade) | uso interno do projeto |
| Motor 2D | Leaflet 1.9.4 | BSD |
| Motor 3D (opcional) | CesiumJS 1.124 | Apache 2.0 |

A atribuição já aparece no rodapé do mapa. Mantenha-a visível. Cobertura de picos validada contra PeakVisor (OSM 273 ≈ PeakVisor 275 para o Paraná). Nenhuma chave de API é necessária: 2D e 3D usam serviços públicos gratuitos.

## Regenerar os dados

```bash
py -3 fetch_peaks.py        # cumes (OSM natural=peak + Wikidata) -> peaks.geojson
py -3 fetch_pois.py         # POIs (refúgios, água, mirantes, etc.) -> pois.geojson
py -3 fetch_parks.py        # unidades de conservação (OSM protected_area) -> parks.geojson
py -3 fetch_osm_trails.py   # trilhas/estradas/ferrovia (Overpass) -> serra_trails.geojson
py -3 fetch_crags.py        # paredões naturais (OSM natural=cliff) -> crags.geojson
py -3 fetch_elevation.py    # altitude (SRTM 30m) -> grava Z em serra_trails.geojson
py -3 parse_routes.py       # vias da planilha -> routes.geojson (mapa) + routes.json (completo)
py -3 embed_atlas.py        # injeta peaks + pois + parks + routes + crags no index.html
py -3 embed_trails.py       # injeta serra_trails.geojson no index.html
py -3 make_logo.py          # gera e injeta a logo do header (portfólio)
```

Os coletores cacheam o resultado bruto do Overpass/Wikidata (arquivos `*_raw.json`, ignorados no git). Ajuste bboxes e regras de curadoria no topo de cada `fetch_*.py`. Para reconsultar o Overpass, apague o cache antes: os coletores usam o `*_raw.json` sem revalidar.

### Conjuntos e cobertura das trilhas

Os conjuntos saem de âncoras em `fetch_peaks.py`: vence a âncora mais próxima dentro de
~17 km, e o resto cai no balde genérico `Serra do Mar (PR)`. Duas correções que valem
lembrar, porque erraram calado:

- As âncoras agora ficam **sobre o cume homônimo**, não num centroide chutado. Com o chute,
  o pico literalmente chamado `Morro dos Perdidos` caía em `Serra da Igreja`, enquanto os
  vizinhos a 2 km dele caíam em `Morro dos Perdidos`.
- `Serra do Araçatuba` e `Serra do Quiriri` são conjuntos distintos e não existiam.
  O Pico Araçatuba (1.673 m, o mais alto do Paraná fora do Ibitiraquire) estava dentro de
  `Serra da Igreja`, e o Quiriri, 12 km ao sul, estava misturado no mesmo balde.
  `Morro dos Perdidos` é um cume dentro do Araçatuba, não um conjunto.

`fetch_osm_trails.py` **deriva as caixas de busca de `peaks.geojson`**, uma por conjunto
nomeado, com folga de ~2 km. Caixas escritas à mão envelhecem quando um conjunto é criado ou
reancorado, e foi exatamente o que aconteceu: o bbox parava em -25,60 e excluía calado toda a
metade sul (Prata, Igreja, Araçatuba, Quiriri), 41% dos cumes, que ficaram sem trilha nenhuma.
O balde genérico é pulado de propósito: ele cobre o estado inteiro, e uma consulta de
`highway=path` nessa extensão traria cada calçada de Curitiba.

Nome não prova que a via foi traçada: o OSM tem tocos de poucos metros com nomes grandiosos
(a `Rota Quiriri - Monte Crista` são 3 nós somando 1,5 m). Quem decide é o comprimento
(`MIN_KM_ANY`), não o nome. A travessia de verdade está lá, como `Trilha Araçatuba - Monte
Crista`, com 21,8 km.

### Sobre `parse_routes.py`

A planilha é mantida à mão e cada aba tem um formato próprio, então o parser trata: graus esparsos (a célula é preenchida uma vez e vale para as linhas abaixo), setores lado a lado em blocos de colunas (Purunã, Macarrão), linhas de soma e cabeçalhos repetidos no meio da tabela, e grafias variantes do mesmo setor.

Ele produz dois arquivos:

- `routes.geojson` — só o escopo do mapa (Serra do Mar / PR montanha), agrupado por montanha e geolocalizado contra `peaks.geojson`. É o que entra no `index.html`.
- `routes.json` — a planilha inteira sem filtro, incluindo o que fica fora do mapa: São Luis Purunã e Macarrão (Ponta Grossa, sem coordenada disponível), as vias históricas de SP e RJ, os desempenhos do Big 1000/500 e as listas curadas (big 500, Croquiteca Raiz 1000, treino de fendas).

**Graus:** a planilha mistura três escalas (brasileira, francesa e V/Hueco para boulder), que não compartilham eixo numérico. Em vez de forjar uma conversão, o parser classifica em quatro faixas (Iniciante, Intermediário, Avançado, Elite) alinhadas só no nível da faixa, e preserva o texto original do grau, além de decompor os componentes (livre, artificial `A0-A3`, exposição `E1-E5`, misto `M1-M3`, variante entre parênteses).

**Geolocalização:** a planilha nomeia setores, mas só as montanhas têm coordenada, então cada marcador é uma montanha e o popup reagrupa por setor. Os boulders do Castelinhos do Anhangava sobem no ponto do Anhangava: o `Castelinho` do `peaks.geojson` é outro morro, 94 km ao sul, e inventar coordenada seria pior que agrupar.

## Arquivos versionados

- `index.html` — a aplicação completa (todos os dados embutidos).
- `vendor/leaflet.js` · `vendor/leaflet.css` · `vendor/images/` — Leaflet auto-hospedado (motor 2D).
- `fetch_peaks.py` · `fetch_pois.py` · `fetch_parks.py` · `fetch_osm_trails.py` · `fetch_crags.py` · `fetch_elevation.py` — coletores OSM/Wikidata/SRTM.
- `parse_routes.py` — parser da planilha de escalada.
- `embed_atlas.py` · `embed_trails.py` · `make_logo.py` — injetores.
- `peaks.geojson` · `pois.geojson` · `parks.geojson` · `serra_trails.geojson` · `crags.geojson` · `routes.geojson` · `routes.json` — dados curados (também embutidos no HTML).
- `Lista de Rotas de Escalada.xlsx` — planilha-fonte das vias de escalada.
- `gas/` — backend de contribuições GPX (Google Apps Script + clasp). Ver `gas/README.md`.

## Painéis

Os dois painéis flutuantes (`#legend` e `#dash`) usam abas, e cada aba cabe inteira: nenhum
dos dois precisa de barra de rolagem, no desktop ou no celular. As camadas são chips de
ligar/desligar num grid de duas colunas, com um único objeto de estado (`LAYER_ON`) governando
os chips, as camadas do Leaflet e o espelho no Cesium, para 2D e 3D nunca discordarem sobre o
que está ligado.

> **Por que a classe se chama `pn-body` e não `body`:** alguma extensão no Chrome do autor
> injeta `margin-bottom:180px` em todo elemento com `class="body"`, com origem USER. A regra
> não aparece em `document.styleSheets` nem no fonte (`grep 180px` não acha nada), inflava
> cada painel em 182px e produzia uma cauda vazia na caixa de camadas mais 268px de
> sobreposição sobre a História. Renomear a classe resolveu: `.body` é um nome genérico
> demais para uma página conviver com extensões. Se algum painel voltar a crescer sem
> motivo, teste com `document.createElement('div')` de classe `body` e compare o
> `marginBottom` computado com o de uma classe inventada.

## Stack

**Leaflet 1.9.4** (2D, main-thread, canvas para 273 cumes + 462 POIs, sem WebGL/workers) como padrão · **CesiumJS 1.124** carregado sob demanda para o modo 3D (terreno ArcGIS + satélite Esri) · GeoJSON para trilhas e parques · SVG para os dashboards. Tokenless.
