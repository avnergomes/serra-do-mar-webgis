#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Marca cada trilha de serra_trails.geojson com uma coluna `oficial` na tabela de
atributos, com base SOMENTE em fonte oficial (plano de manejo / plano de uso público
do IAT). Nada é marcado "oficial" sem uma regra documentada; o resto fica "nd" (não
verificada) e recebe ênfase reduzida no mapa.

Regras (documentadas em FONTES_REGRAS_UC.md):
- Pico Paraná (PEPP): trilha dentro do parque que dá acesso a um cume/atrativo
  CONSOLIDADO no Plano de Uso Público (Portaria IAT 470/2025, seção 2.7, Tabelas 1-13).
- Marumbi: trilhas sinalizadas por cor (branca/Frontal, vermelha/Noroeste, azul/
  Rochedinho), o Circuito e o Caminho do Itupava (Plano de Manejo PE Pico do Marumbi).
- Serra da Baitaca: trilha de acesso ao Anhangava (Plano de Manejo PE Serra da Baitaca).
- Nomes com marcador de informalidade (mal demarcada, perigosa, conquista, picada,
  confusão, clandestina) nunca são marcados oficiais.

Editar as listas abaixo é como o Avner ajusta o que é oficial. Rode e depois
`py -3 embed_trails.py` para reinjetar.
"""
import json, sys

TRAILS = "serra_trails.geojson"
PARKS = "parks.geojson"

FONTE = {
    'pp': 'Plano de Uso Público do PE Pico Paraná (Portaria IAT 470/2025), seção 2.7 – trilhas/atrativos consolidados',
    'marumbi': 'Plano de Manejo do PE Pico do Marumbi (IAT) – trilhas sinalizadas (branca/vermelha/azul/amarela), Circuito e Caminho do Itupava',
    'baitaca': 'Plano de Manejo do PE Serra da Baitaca (IAT) – trilhas de acesso ao Anhangava, Pão de Loth, Samambaia e ao Campo de Asa Delta',
}
# Cumes/atrativos consolidados no plano do Pico Paraná (exige UC == Pico Paraná).
PP_CONSOLIDATED = ['caratuva', 'pico paran', 'itapiroca', 'uniao', 'união', 'ferraria',
                   'taipabu', 'taipa', 'tucum', 'camapu', 'cerro verde', 'siririca',
                   'pedra branca', 'ibitirati', 'morro dos camelos', 'discoporto',
                   'disco porto', 'janela da cotia']
# Marumbi / Baitaca: nomes distintivos, casados independentemente do polígono da UC
# (o limite do OSM às vezes deixa a trilha oficial um pouco de fora).
MARUMBI_OFICIAL = ['frontal', 'noroeste', 'rochedinho', 'torre amarela', 'circuito marumbi', 'itupava']
# Serra da Baitaca: casadas só dentro do parque (samambaia é palavra comum). A "Trilha Mal
# Demarcada para o Corvo" fica de fora pelo marcador de informalidade (INFORMAL).
BAITACA_OFICIAL = ['anhangava', 'baitaca', 'pão de lo', 'pao de lo', 'asa delta', 'samambaia', 'confus']
INFORMAL = ['mal demarcad', 'perigos', 'conquista', 'picada', 'cuidado', 'clandestin']
# Trilhas que o cliente pediu para inativar (não desenhar no mapa): oficial='off'.
# "Trilha para o Anhangava": trecho que sai bem do lado do Estacionamento Baitacão do Anhangava.
HIDE_NAMES = {'trilha para o anhangava'}

# ---- point-in-polygon ----
def rings_of(g):
    if g['type'] == 'Polygon': return [g['coordinates']]
    if g['type'] == 'MultiPolygon': return g['coordinates']
    return []

def pip(x, y, ring):
    ins = False; n = len(ring); j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]; xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            ins = not ins
        j = i
    return ins

def in_feature(x, y, g):
    for poly in rings_of(g):
        if poly and pip(x, y, poly[0]):
            if not any(pip(x, y, poly[h]) for h in range(1, len(poly))):
                return True
    return False

def samples(g):
    if g['type'] == 'LineString': segs = [g['coordinates']]
    elif g['type'] == 'MultiLineString': segs = g['coordinates']
    else: segs = []
    pts = []
    for s in segs: pts.extend(s)
    step = max(1, len(pts) // 8)
    return pts[::step]

def main():
    trails = json.load(open(TRAILS, encoding="utf-8"))
    parks = json.load(open(PARKS, encoding="utf-8"))

    def uc_of(f):
        tally = {}
        for pt in samples(f['geometry']):
            for pk in parks['features']:
                if in_feature(pt[0], pt[1], pk['geometry']):
                    nm = pk['properties']['name']; tally[nm] = tally.get(nm, 0) + 1
                    break
        return max(tally, key=tally.get) if tally else None

    n_of = 0
    rep = []
    n_infra = 0; n_hidden = 0
    for f in trails['features']:
        p = f['properties']
        # Estrada da Graciosa e a ferrovia são infraestrutura de referência (mesmo status
        # das rodovias), não trilhas de caminhada: não entram na régua oficial/não oficial.
        if p.get('kind') != 'trilha':
            p['oficial'] = 'infra'; p.pop('oficial_fonte', None); n_infra += 1
            continue
        name = (p.get('name') or '').strip()
        nl = name.lower()
        if nl in HIDE_NAMES:
            p['oficial'] = 'off'; p.pop('oficial_fonte', None); n_hidden += 1
            continue
        uc = uc_of(f)
        oficial, fonte = 'nd', ''
        informal = any(k in nl for k in INFORMAL)
        if name and not informal:
            if uc == 'Parque Estadual Pico Paraná' and any(k in nl for k in PP_CONSOLIDATED):
                oficial, fonte = 'sim', FONTE['pp']
            elif any(k in nl for k in MARUMBI_OFICIAL):
                oficial, fonte = 'sim', FONTE['marumbi']
            elif uc == 'Parque Estadual Serra da Baitaca' and any(k in nl for k in BAITACA_OFICIAL) and 'cachoeira' not in nl:
                oficial, fonte = 'sim', FONTE['baitaca']
        p['oficial'] = oficial
        if fonte:
            p['oficial_fonte'] = fonte; n_of += 1
            rep.append((name, uc or '-'))
        else:
            p.pop('oficial_fonte', None)

    json.dump(trails, open(TRAILS, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("Trilhas oficiais marcadas: %d de %d feições (%d infraestrutura, %d ocultas)\n"
          % (n_of, len(trails['features']), n_infra, n_hidden))
    for nm, uc in sorted(rep):
        print("  [oficial] %-38s  (%s)" % (nm[:38], uc))

if __name__ == "__main__":
    main()
