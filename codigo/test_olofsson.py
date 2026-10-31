"""
Teste do estimador contra o exemplo numerico publicado.

Fonte dos numeros (conferidos no PDF do artigo, Tabelas 6 a 9):
  Olofsson, P., Foody, G., Herold, M., Stehman, S., Woodcock, C., Wulder, M. (2014).
  Good practices for estimating area and assessing accuracy of land change.
  Remote Sensing of Environment 148:42-57. doi:10.1016/j.rse.2014.02.015

O que e conferido:

  Teste A - Tabela 8 (contagens amostrais) -> Tabela 9 (proporcoes de area).
            As 16 celulas de p_ij tem que bater, e com elas a acuracia global,
            a do usuario e a do produtor.

  Teste B - Tabela 6 (matriz populacional) + alocacao "Alloc2" (n = 75, 75, 165,
            325) -> Tabela 7 (erros padrao). Confere a variancia da acuracia
            global, da acuracia do usuario (classes 1 e 3) e da AREA (classes 1
            e 3, em hectares, com area total de 9.000.000 ha = 10 milhoes de
            pixels de 30 m).

  Teste C - casos degenerados do caso binario (mapa perfeito; estrato com zero
            pontos deve levantar erro claro).

Uso:
    python codigo/test_olofsson.py
"""

from __future__ import annotations

import sys

import numpy as np

import common as c
import olofsson

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

falhas = []
resultados = {}


def checar(nome, obtido, esperado, tol, absoluto=True):
    ok = abs(obtido - esperado) <= (tol if absoluto else tol * abs(esperado))
    marca = "ok  " if ok else "FALHA"
    print(f"  [{marca}] {nome:<46s} obtido {obtido:>10.4f} | artigo {esperado:>10.4f}")
    if not ok:
        falhas.append(nome)
    return ok


print("Teste A - Tabela 8 -> Tabela 9 (proporcoes de area) e acuracias")
# Tabela 8: contagens (linhas = mapa; colunas = referencia)
m8 = np.array([
    [66, 0, 5, 4],
    [0, 55, 8, 12],
    [1, 0, 153, 11],
    [2, 1, 9, 313],
], dtype=float)
# Tabela 8: area mapeada de cada classe (pixels) e total
areas_px = np.array([200_000, 150_000, 3_200_000, 6_450_000], dtype=float)
total_px = 10_000_000.0

r = olofsson.estimar_de_matriz(m8, areas_px, area_total=total_px,
                               nomes=["desmatamento", "ganho", "floresta", "nao_floresta"])
# Tabela 9 (proporcoes de area estimadas)
t9 = np.array([
    [0.0176, 0.0000, 0.0013, 0.0011],
    [0.0000, 0.0110, 0.0016, 0.0024],
    [0.0019, 0.0000, 0.2967, 0.0213],
    [0.0040, 0.0020, 0.0179, 0.6212],
])
for i in range(4):
    for j in range(4):
        checar(f"p_{i+1}{j+1}", r["p_ij"][i][j], t9[i, j], 0.0006)

# valores derivados da Tabela 9 (as mesmas contas do artigo)
checar("acuracia global", r["acuracia_global"], 0.9465, 0.0006)
checar("acuracia do usuario 1", r["acuracia_usuario"]["desmatamento"]["valor"], 0.8800, 0.0006)
checar("acuracia do usuario 2", r["acuracia_usuario"]["ganho"]["valor"], 0.7333, 0.0006)
checar("acuracia do usuario 3", r["acuracia_usuario"]["floresta"]["valor"], 0.9272, 0.0006)
checar("acuracia do usuario 4", r["acuracia_usuario"]["nao_floresta"]["valor"], 0.9631, 0.0006)
checar("acuracia do produtor 1", r["acuracia_produtor"]["desmatamento"]["valor"], 0.7489, 0.0012)
checar("acuracia do produtor 2", r["acuracia_produtor"]["ganho"]["valor"], 0.8462, 0.0012)
checar("acuracia do produtor 3", r["acuracia_produtor"]["floresta"]["valor"], 0.9345, 0.0012)
checar("acuracia do produtor 4", r["acuracia_produtor"]["nao_floresta"]["valor"], 0.9616, 0.0012)
resultados["tabela9"] = {
    "p_ij": r["p_ij"],
    "acuracia_global": r["acuracia_global"],
}

print("\nTeste B - Tabela 6 + alocacao Alloc2 -> Tabela 7 (erros padrao)")
# Tabela 6: matriz populacional em proporcao de area
p6 = np.array([
    [0.014, 0.000, 0.003, 0.003],
    [0.000, 0.009, 0.003, 0.003],
    [0.002, 0.000, 0.288, 0.030],
    [0.004, 0.002, 0.025, 0.614],
])
W6 = p6.sum(axis=1)             # 0.020, 0.015, 0.320, 0.645
n_aloc2 = np.array([75, 75, 165, 325], dtype=float)
m6 = p6 / W6[:, None] * n_aloc2[:, None]   # contagens esperadas por estrato
area_total_ha = 900_000.0                   # 10 milhoes de pixels de 30 m = 9.000 km2 = 900 mil ha

r2 = olofsson.estimar_de_matriz(m6, W6 * area_total_ha, area_total=area_total_ha,
                                nomes=["desmatamento", "ganho", "floresta", "nao_floresta"])
# Tabela 7, coluna Alloc2
checar("SE da acuracia global", r2["se_acuracia_global"], 0.011, 0.0006)
checar("SE da acuracia do usuario 1", r2["acuracia_usuario"]["desmatamento"]["se"], 0.053, 0.001)
checar("SE da acuracia do usuario 3", r2["acuracia_usuario"]["floresta"]["se"], 0.023, 0.001)
# a Tabela 6 arredonda p31 e p41 para 1 algarismo significativo (0,002 e 0,004),
# o que mexe na variancia da area; por isso a tolerancia de 5%
checar("SE da area 1 (ha)", r2["areas"]["desmatamento"]["se_km2"], 3138.0, 0.05, absoluto=False)
checar("SE da area 3 (ha)", r2["areas"]["floresta"]["se_km2"], 9270.0, 0.05, absoluto=False)
resultados["tabela7"] = {
    "se_acuracia_global": r2["se_acuracia_global"],
    "se_area_1_ha": r2["areas"]["desmatamento"]["se_km2"],
    "se_area_3_ha": r2["areas"]["floresta"]["se_km2"],
}

print("\nTeste C - casos degenerados do caso binario")
areas5 = np.array([41.4, 65.7, 118.1, 100.4, 55.6])
alvo5 = np.array([True, False, False, False, False])
estrato = np.repeat(np.arange(5), 20)
ref = np.where(np.repeat(alvo5, 20), 1, 0)
rp = olofsson.estimar(estrato, ref, areas5, alvo5)
checar("mapa perfeito: area ajustada = area crua", rp["areas"]["alvo"]["area_estimada_km2"],
       41.4, 1e-6)
checar("mapa perfeito: acuracia global", rp["acuracia_global"], 1.0, 1e-12)

# estrato sem ponto tem que dar erro explicito, nao traceback generico
try:
    olofsson.estimar(np.repeat(np.arange(4), 20), np.ones(80, dtype=int), areas5, alvo5)
    print("  [FALHA] estrato sem ponto nao levantou erro")
    falhas.append("estrato sem ponto")
except ValueError as e:
    print(f"  [ok  ] estrato sem ponto -> ValueError: {str(e)[:60]}")

print("\n" + ("TODOS OS TESTES PASSARAM" if not falhas else f"FALHAS: {falhas}"))
c.salvar_json({"falhas": falhas, "resultados": resultados,
               "fonte": "Olofsson et al. 2014, doi:10.1016/j.rse.2014.02.015, Tabelas 6-9"},
              "teste_olofsson.json")
sys.exit(1 if falhas else 0)
