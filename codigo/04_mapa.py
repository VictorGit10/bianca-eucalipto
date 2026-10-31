"""
Passo 04 - treinar o modelo final e gerar o mapa da area de teste.

Decisao do tamanho de treino: 1.600 amostras por classe (8.000 no total).
Justificativa nos dados do passo 03: o F1 do eucalipto ainda subia, mas cada
dobrada de amostras passou a render menos de 0,04 de F1. A escolha final e da
pesquisadora; o script aceita --n para refazer com outro valor.

O mapa e comparado com o MapBiomas apenas como conferencia grosseira. Concordar
com o MapBiomas NAO e acuracia: os dois vem da mesma referencia por tras dos
rotulos de treino.

Saidas:
  dados/mapa_predito.tif     (1 banda uint8: indice em common.CLASSES, 255 = nodata)
  dados/mapa_meta.json       (areas por classe e concordancia com o MapBiomas)
  figuras/mapa_area.png
"""

from __future__ import annotations

import sys

import numpy as np
import rasterio
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch
from sklearn.ensemble import RandomForestClassifier

import common as c
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

N_FINAL = 1600
if "--n" in sys.argv:
    N_FINAL = int(sys.argv[sys.argv.index("--n") + 1])

X, y, valido, forma = c.carregar_bandas()
lin, col = np.nonzero(valido)
n_classes = len(c.CLASSES)
print(f"pixels validos: {len(y):,} | treino: {N_FINAL} por classe")

r = np.random.default_rng(7)
tr = np.concatenate(
    [r.choice(np.nonzero(y == k)[0], size=min(N_FINAL, int((y == k).sum())), replace=False)
     for k in range(n_classes)]
)
modelo = RandomForestClassifier(
    n_estimators=300, max_features="sqrt", min_samples_leaf=1, n_jobs=-1, random_state=7
)
modelo.fit(X[tr], y[tr])
print(f"  treinado com {len(tr):,} amostras")

pred = modelo.predict(X).astype("uint8")
mapa = np.full(forma, 255, dtype="uint8")
mapa[lin, col] = pred

x0 = None
with rasterio.open(c.DADOS / "mosaico_s2.tif") as src:
    perfil = src.profile.copy()
perfil.update(count=1, dtype="uint8", nodata=255, compress="deflate")
with rasterio.open(c.DADOS / "mapa_predito.tif", "w", **perfil) as dst:
    dst.write(mapa, 1)

# ---------------------------------------------------- areas e concordancia
area_px_km2 = (c.ESCALA ** 2) / 1e6
contagem_mapa = np.bincount(pred, minlength=n_classes)
rot = np.full(forma, -1, dtype="int16")
with rasterio.open(c.DADOS / "rotulos_mb.tif") as src:
    rot = src.read(1).astype("int16")
cod2classe = {cod: i for i, nome in enumerate(c.CLASSES) for cod in c.GRUPOS[nome]}
y_full = np.full(forma, -1, dtype="int16")
for cod, i in cod2classe.items():
    y_full[rot == cod] = i

concordancia = float((mapa[valido] == y_full[valido]).mean())
matriz = np.zeros((n_classes, n_classes), dtype=int)  # linhas: mapa, colunas: MapBiomas
np.add.at(matriz, (mapa[valido], y_full[valido]), 1)

meta = {
    "n_por_classe": N_FINAL,
    "n_treino": int(len(tr)),
    "classes": c.CLASSES,
    "area_total_km2": round(float(valido.sum() * area_px_km2), 1),
    "area_por_classe_mapa_km2": {
        nome: round(float(v * area_px_km2), 1) for nome, v in zip(c.CLASSES, contagem_mapa)
    },
    "concordancia_com_mapbiomas": round(concordancia, 4),
    "matriz_mapa_x_mapbiomas": matriz.tolist(),
    "aviso": "concordancia com o MapBiomas nao e acuracia (mesma fonte de rotulos)",
}
c.salvar_json(meta, "mapa_meta.json")
for nome, v in zip(c.CLASSES, contagem_mapa):
    print(f"  {nome:<14s} {v:8,d} px  {v*area_px_km2:7.1f} km2")
print(f"  concordancia com MapBiomas: {concordancia:.3f} (nao e acuracia)")

# ------------------------------------------------------------------- figura
with rasterio.open(c.DADOS / "rgb_10m.tif") as src:
    rgb = c.esticar_rgb(src.read()).transpose(1, 2, 0)
    rgb_ext = [src.bounds.left / 1000, src.bounds.right / 1000,
               src.bounds.bottom / 1000, src.bounds.top / 1000]
with rasterio.open(c.DADOS / "mosaico_s2.tif") as src:
    ext = [src.bounds.left / 1000, src.bounds.right / 1000,
           src.bounds.bottom / 1000, src.bounds.top / 1000]

cores = [c.CORES[n] for n in c.CLASSES]
cmap = ListedColormap(cores)          # exatamente uma cor por classe
cmap.set_bad("#ffffff")               # sem dado
norm = BoundaryNorm(np.arange(n_classes + 1) - 0.5, cmap.N)

fig, eixos = plt.subplots(1, 3, figsize=(15, 5.2), dpi=150)
eixos[0].imshow(rgb, extent=rgb_ext)
eixos[0].set_title("Sentinel-2, composicao seca 2024\n(cor verdadeira, 10 m)")

m_mb = np.ma.masked_where(~valido, y_full)
eixos[1].imshow(m_mb, cmap=cmap, norm=norm, extent=ext, interpolation="nearest")
silv_mb = next(d["area_km2"] for d in c.recorte()["composicao"] if d["codigo"] == 9)
eixos[1].set_title(f"MapBiomas 2024 (referencia provisoria)\neucalipto = {silv_mb:.0f} km2 no MapBiomas")

m_rf = np.ma.masked_where(~valido, mapa)
eixos[2].imshow(m_rf, cmap=cmap, norm=norm, extent=ext, interpolation="nearest")
eixos[2].set_title(f"Mapa do Random Forest\n({N_FINAL}/classe, concordancia {concordancia:.0%} com o MapBiomas)")

for ax in eixos[1:]:
    ax.set_xlabel("UTM 22S, leste (km)")
    ax.set_ylabel("UTM 22S, norte (km)")
eixos[0].set_xlabel("UTM 22S, leste (km)")
eixos[0].set_ylabel("UTM 22S, norte (km)")

legenda = [Patch(facecolor=c.CORES[n], edgecolor="0.4", label=n) for n in c.CLASSES]
fig.legend(handles=legenda, loc="lower center", ncol=5, frameon=False, fontsize=9)
fig.suptitle(f"Area de teste: {c.recorte()['municipio']}, GO - {meta['area_total_km2']:.0f} km2", fontsize=12)
fig.tight_layout(rect=(0, 0.06, 1, 0.94))
fig.savefig(c.FIGURAS / "mapa_area.png", bbox_inches="tight")
print("  figura: figuras/mapa_area.png")
