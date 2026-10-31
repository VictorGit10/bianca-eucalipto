"""
Passo 01 - escolher a area de teste.

Pergunta: onde, em Goias, existe silvicultura (classe 9 do MapBiomas) em quantidade
suficiente para um teste de classificacao?

Metodo:
  1. Baixa os municipios de Goias do GAUL nivel 2 (publico, sem cadastro).
  2. Soma a area da classe 9 do MapBiomas Colecao 11 (ano 2024) por municipio.
  3. Escolhe o municipio com mais silvicultura e, dentro dele, a janela de 18 x 18 km
     com maior densidade de silvicultura (convolucao com kernel quadrado).
  4. Define o recorte final (0,18 grau x 0,18 grau, ~20 x 20 km) e descreve a
     composicao de classes dentro dele.

Saidas:
  dados/silvicultura_por_municipio.csv
  dados/recorte.json
  dados/composicao_recorte.csv
"""

from __future__ import annotations

import csv
import sys

import common as c

FORCAR = "--forcar" in sys.argv

ee = c.ee_init()

# ---------------------------------------------------------------- 1. municipios
municipios = ee.FeatureCollection(c.MUNICIPIOS).filter(
    ee.Filter.eq("ADM1_NAME", "Goias")
)
n_mun = municipios.size().getInfo()
print(f"[1/4] municipios de Goias no GAUL: {n_mun}")

# ------------------------------------- 2. area de silvicultura por municipio
csv_mun = c.DADOS / "silvicultura_por_municipio.csv"
if csv_mun.exists() and not FORCAR:
    print(f"      reaproveitando {csv_mun.name} (use --forcar para refazer)")
    linhas = list(csv.DictReader(csv_mun.open(encoding="utf-8")))
else:
    print("      somando a classe 9 por municipio (uma chamada reduceRegions, escala 100 m)")
    mapa = ee.Image(f"{c.MB_COL11}/collection_11_{c.MB_ANO}_v1")
    area_silv = mapa.eq(9).multiply(ee.Image.pixelArea())
    tabela = area_silv.reduceRegions(
        collection=municipios, reducer=ee.Reducer.sum(), scale=100, tileScale=8
    )
    feicoes = tabela.map(
        lambda f: ee.Feature(
            None,
            {
                "municipio": f.get("ADM2_NAME"),
                "area_silvicultura_km2": ee.Number(f.get("sum")).divide(1e6),
                "area_municipio_km2": f.geometry().area(100).divide(1e6),
            },
        )
    ).getInfo()["features"]
    linhas = sorted(
        (f["properties"] for f in feicoes),
        key=lambda d: -(d["area_silvicultura_km2"] or 0),
    )
    with csv_mun.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh, fieldnames=["municipio", "area_silvicultura_km2", "area_municipio_km2"]
        )
        w.writeheader()
        for d in linhas:
            w.writerow(
                {
                    "municipio": d["municipio"],
                    "area_silvicultura_km2": round(d["area_silvicultura_km2"] or 0, 2),
                    "area_municipio_km2": round(d["area_municipio_km2"] or 0, 1),
                }
            )
    print(f"      salvo em {csv_mun.name}")

print("      cinco municipios com mais silvicultura (km2):")
for d in linhas[:5]:
    print(f"        {d['municipio']:<28s} {float(d['area_silvicultura_km2']):8.1f}")

municipio = linhas[0]["municipio"]
print(f"[2/4] municipio escolhido: {municipio} (maior area de silvicultura do estado)")

# -------------------------- 3. janela de 18 km com maior densidade de silvicultura
mun = municipios.filter(ee.Filter.eq("ADM2_NAME", municipio))
mapa = ee.Image(f"{c.MB_COL11}/collection_11_{c.MB_ANO}_v1")
kernel = ee.Kernel.square(radius=9000, units="meters", normalize=False)
densidade = mapa.eq(9).unmask(0).convolve(kernel)

maximo = densidade.reduceRegion(
    ee.Reducer.max(), mun.geometry(), 300, tileScale=8
).getInfo()["classification"]
ponto = (
    densidade.eq(maximo)
    .selfMask()
    .reduceToVectors(
        geometry=mun.geometry(),
        scale=300,
        geometryType="centroid",
        maxPixels=int(1e7),
    )
    .first()
    .geometry()
    .coordinates()
    .getInfo()
)
centro = [round(ponto[0], 3), round(ponto[1], 3)]
print(f"[3/4] centro da janela mais densa: {centro} (18x18 km)")

# ------------------------------------------------------------- 4. recorte final
d = 0.09  # metade do lado, em graus -> 0,18 grau ~ 20 km
bbox = [centro[0] - d, centro[1] - d, centro[0] + d, centro[1] + d]
caixa = ee.Geometry.Rectangle(bbox)

hist = mapa.reduceRegion(
    ee.Reducer.frequencyHistogram(),
    caixa,
    scale=30,
    maxPixels=int(1e9),
    tileScale=8,
).getInfo()["classification"]

total = sum(hist.values())
comp = []
for k, v in sorted(hist.items(), key=lambda kv: -kv[1]):
    cod = int(k)
    comp.append(
        {
            "codigo": cod,
            "classe": c.LEGENDA.get(cod, f"classe {cod}"),
            "pct": round(100 * v / total, 2),
            "area_km2": round(v * 900 / 1e6, 1),  # pixel de 30 m = 900 m2
        }
    )

with (c.DADOS / "composicao_recorte.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["codigo", "classe", "pct", "area_km2"])
    w.writeheader()
    w.writerows(comp)

area_km2 = caixa.area(100).getInfo() / 1e6
saida = {
    "municipio": municipio,
    "centro": centro,
    "bbox": bbox,
    "lado_graus": 2 * d,
    "area_km2": round(area_km2, 1),
    "escala_m": c.ESCALA,
    "crs_local": c.CRS_LOCAL,
    "mapbiomas_ano": c.MB_ANO,
    "silvicultura_municipio_km2": float(linhas[0]["area_silvicultura_km2"]),
    "composicao": comp,
}
c.salvar_json(saida, "recorte.json")

print(f"[4/4] recorte: {area_km2:.1f} km2 em {c.CRS_LOCAL}")
print("      composicao (MapBiomas 2024, pixels de 30 m):")
for d_ in comp[:8]:
    print(f"        {d_['classe']:<34s} {d_['pct']:6.2f}%  {d_['area_km2']:7.1f} km2")
print("      salvo dados/recorte.json")
