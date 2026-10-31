"""
Passo 09 - do recorte de Rio Verde para o estado de Goias (plano, nao mapa).

A duvida da pesquisadora e para Goias inteiro. Este script nao produz o mapa
estadual: ele levanta os numeros que faltam para planejar esse mapa e a
validacao dele.

  1. Le a tabela de silvicultura por municipio (passo 01) e escolhe 2-3 regioes
     com silvicultura relevante e contextos diferentes (norte, sudoeste, sudeste).
  2. Pede ao Earth Engine a area das 5 classes do mapa em Goias inteiro, numa
     grade grossa (1 km), so para dimensionar a amostra. E uma chamada so, sem
     download de imagem.
  3. Calcula o tamanho da amostra de validacao para o estado com a mesma formula
     do passo 05 (Olofsson), usando o prior de acuracia do mapa local.

Saidas:
  dados/plano_goias.json
"""

from __future__ import annotations

import csv
import sys

import numpy as np

import common as c

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def tamanho_amostra(W, U, se):
    S = np.sqrt(np.asarray(U) * (1 - np.asarray(U)))
    return int(np.ceil((np.sum(np.asarray(W) * S) / se) ** 2))


# ------------------------------------------------------------ 1. municipios
linhas = list(csv.DictReader((c.DADOS / "silvicultura_por_municipio.csv").open(encoding="utf-8")))
for l in linhas:
    l["silv"] = float(l["area_silvicultura_km2"])
    l["mun"] = float(l["area_municipio_km2"])
    l["pct"] = 100 * l["silv"] / l["mun"] if l["mun"] else 0.0

total_estado = sum(l["silv"] for l in linhas)
print(f"silvicultura somada nos 242 municipios de Goias: {total_estado:.0f} km2")

# tres regioes com papeis diferentes: maior area, norte (cerrado/charcoal) e sudeste
candidatos = ["Rio Verde", "Niquelandia", "Catalao"]
regioes = []
for nome in candidatos:
    achado = next((l for l in linhas if l["municipio"].lower() == nome.lower()), None)
    if achado is None:
        print(f"  (municipio {nome} nao esta na tabela)")
        continue
    regioes.append({
        "municipio": achado["municipio"],
        "silvicultura_km2": round(achado["silv"], 1),
        "area_municipio_km2": round(achado["mun"], 1),
        "pct_do_municipio": round(achado["pct"], 2),
        "pct_do_estado": round(100 * achado["silv"] / total_estado, 1),
    })
print("\nregioes sugeridas para repetir a curva de aprendizado:")
for r in regioes:
    print(f"  {r['municipio']:<14s} {r['silvicultura_km2']:7.1f} km2  "
          f"({r['pct_do_municipio']:5.2f}% do municipio, {r['pct_do_estado']:4.1f}% do estado)")

# ------------------------------------------------- 2. areas das classes no estado
print("\nconsultando as areas das 5 classes em Goias (grade de 1 km, uma chamada)...")
ee = c.ee_init()
go = ee.FeatureCollection(c.MUNICIPIOS).filter(ee.Filter.eq("ADM1_NAME", "Goias"))
mapa = ee.Image(f"{c.MB_COL11}/collection_11_{c.MB_ANO}_v1").select("classification")

hist = mapa.reduceRegion(
    ee.Reducer.frequencyHistogram(), go.geometry(), scale=1000,
    maxPixels=int(1e9), tileScale=4,
).getInfo()["classification"]
por_codigo = {int(k): float(v) for k, v in hist.items()}
area_total_estado = sum(por_codigo.values()) * 1.0  # pixels de 1 km = 1 km2
print(f"  area de Goias na grade de 1 km: {area_total_estado:,.0f} km2")

areas_grupo = []
for nome in c.CLASSES:
    km2 = sum(por_codigo.get(cod, 0.0) for cod in c.GRUPOS[nome])
    areas_grupo.append(km2)
areas_grupo = np.array(areas_grupo)
W = areas_grupo / areas_grupo.sum()
print("  areas por grupo (1 km):")
for nome, a, w in zip(c.CLASSES, areas_grupo, W):
    print(f"    {nome:<14s} {a:9,.0f} km2  ({100*w:5.2f}%)")

# ------------------------------------------------------ 3. tamanho da amostra
meta = c.ler_json("mapa_meta.json")
matriz = np.array(meta["matriz_mapa_x_mapbiomas"], dtype=float)
U = np.diag(matriz) / np.maximum(matriz.sum(1), 1)

plano_se = {f"{se:.2f}": tamanho_amostra(W, U, se) for se in (0.02, 0.03, 0.04, 0.05)}
print("\ntamanho da amostra de validacao para o estado (Olofsson, prior local):")
for se, n in plano_se.items():
    print(f"  SE={se} -> {n:5d} pontos")

aloc_prop = np.round(W * plano_se["0.03"]).astype(int)
print(f"  alocacao proporcional com n={plano_se['0.03']}: " +
      ", ".join(f"{nome}={k}" for nome, k in zip(c.CLASSES, aloc_prop)))

# Olofsson recomenda dar 50-100 pontos a classe rara e dividir o resto proporcionalmente.
# Aqui: piso fixo de 100 no eucalipto e o restante proporcional; o n total e o menor
# que atinge o SE alvo (0,03) com essa regra de alocacao.
PISO_RARO = 100
ALVO_SE = 0.03
w_outros = W[1:] / W[1:].sum()


def alocar(n_total):
    a = np.zeros(len(W), dtype=int)
    a[0] = PISO_RARO
    a[1:] = np.maximum(np.round((n_total - PISO_RARO) * w_outros).astype(int), 10)
    return a


def se_de(a):
    return float(np.sqrt(np.sum(W ** 2 * U * (1 - U) / np.maximum(a, 1))))


aloc_piso = alocar(PISO_RARO + 10 * len(W))
while se_de(aloc_piso) > ALVO_SE and aloc_piso.sum() < 5000:
    aloc_piso = alocar(aloc_piso.sum() + 1)
se_com_piso = se_de(aloc_piso)
print(f"  com piso de {PISO_RARO} pontos no eucalipto: " +
      ", ".join(f"{nome}={k}" for nome, k in zip(c.CLASSES, aloc_piso)))
print(f"    n total = {int(aloc_piso.sum())}, SE previsto da acuracia global = {se_com_piso:.3f}")

c.salvar_json({
    "silvicultura_goias_km2": round(total_estado, 1),
    "area_goias_km2": round(float(areas_grupo.sum()), 1),
    "areas_por_grupo_km2": {n: round(float(a), 1) for n, a in zip(c.CLASSES, areas_grupo)},
    "W": {n: round(float(w), 4) for n, w in zip(c.CLASSES, W)},
    "regioes_sugeridas": regioes,
    "n_por_se": plano_se,
    "alocacao_proporcional_se_003": {
        n: int(k) for n, k in zip(c.CLASSES, aloc_prop)
    },
    "alocacao_com_piso_100_no_eucalipto": {
        n: int(k) for n, k in zip(c.CLASSES, aloc_piso)
    },
    "n_total_com_piso": int(aloc_piso.sum()),
    "se_previsto_com_piso": round(se_com_piso, 4),
    "prior_acuracia_usuario": {n: round(float(u), 3) for n, u in zip(c.CLASSES, U)},
    "observacao": "n calculado com prior de acuracia do mapa local (Rio Verde); "
                  "repita a curva antes para o prior das outras regioes",
}, "plano_goias.json")
print("\nsalvo dados/plano_goias.json")
