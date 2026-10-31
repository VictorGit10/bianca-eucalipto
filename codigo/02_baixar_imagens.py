"""
Passo 02 - baixar o mosaico Sentinel-2 e os rotulos provisorios do MapBiomas.

O que entra no mosaico (recorte de ~20 x 20 km, 20 m/pixel, UTM 22S):

  seca 2024 (01/05 a 30/09)  -> B2, B3, B4, B5, B6, B7, B8, B8A, B11, B12
  chuva 2024/25 (01/11 a 28/02) -> B4, B8, B11
  indices calculados das medianas -> NDVI, NDWI, NDRE, NDBI (seca) e NDVI, NDWI (chuva)

Mascara de nuvem: Cloud Score+ (banda cs_cdf >= 0,60), aplicada antes da mediana.
Mosaico: mediana por pixel de cada estacao.

Rotulos: MapBiomas Colecao 11, ano 2024, classe original (nao agrupada). O
agrupamento em 5 classes e feito no passo 03, no Python - assim a escolha fica
visivel e reversivel.

Tudo e baixado em blocos (tiles) para nao passar do limite de 32 MB por requisicao
do getDownloadURL, e remontado com rasterio em um unico GeoTIFF.

Saidas:
  dados/mosaico_s2.tif   (19 bandas, float32, 20 m)
  dados/rotulos_mb.tif   (1 banda, uint8, classe MapBiomas, 20 m)
  dados/rgb_10m.tif      (3 bandas, uint8, 10 m - so para os recortes da conferencia)
  dados/mosaico_meta.json
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import rasterio
import requests
from rasterio.transform import from_origin

import common as c

FORCAR = "--forcar" in sys.argv

ee = c.ee_init()
rec = c.recorte()
caixa = ee.Geometry.Rectangle(rec["bbox"])


# ------------------------------------------------------------------ utilidades
def grade_utm(caixa, escala, nx, ny):
    """Grade UTM alinhada ao pixel, dividida em nx x ny blocos."""
    coords = caixa.transform(c.CRS_LOCAL, 1).coordinates().getInfo()[0]
    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    x0 = math.floor(xmin / escala) * escala
    y0 = math.floor(ymin / escala) * escala
    x1 = math.ceil(xmax / escala) * escala
    y1 = math.ceil(ymax / escala) * escala
    # larguras inteiras em pixels, divisiveis por nx/ny
    larg = int(round((x1 - x0) / escala))
    alt = int(round((y1 - y0) / escala))
    larg += (-larg) % nx
    alt += (-alt) % ny
    return x0, y0, x0 + larg * escala, y0 + alt * escala, larg, alt


def baixar_blocos(img, x0, y0, x1, y1, larg, alt, escala, destino: Path, nx, ny):
    """Baixa a imagem em nx*ny blocos e remonta num GeoTIFF unico."""
    lw, lh = larg // nx, alt // ny  # pixels por bloco
    bandas = len(img.bandNames().getInfo())
    dados = np.full((bandas, alt, larg), np.nan, dtype="float32")
    mascara = np.zeros((alt, larg), dtype="uint8")
    for j in range(ny):
        for i in range(nx):
            bx0 = x0 + i * lw * escala
            by1 = y1 - j * lh * escala
            bx1 = bx0 + lw * escala
            by0 = by1 - lh * escala
            regiao = ee.Geometry.Rectangle([bx0, by0, bx1, by1], proj=c.CRS_LOCAL, geodesic=False)
            url = img.getDownloadURL(
                {
                    "region": regiao,
                    "scale": escala,
                    "crs": c.CRS_LOCAL,
                    "format": "GEO_TIFF",
                    "filePerBand": False,
                }
            )
            r = requests.get(url, timeout=300)
            r.raise_for_status()
            tmp = c.DADOS / "_bloco.tif"
            tmp.write_bytes(r.content)
            with rasterio.open(tmp) as src:
                arr = src.read()
                assert arr.shape[1:] == (lh, lw), (
                    f"bloco {i},{j}: {arr.shape} != {(bandas, lh, lw)}"
                )
                dados[:, j * lh : (j + 1) * lh, i * lw : (i + 1) * lw] = arr
                # guarda a mascara de validade (nodata) do bloco
                if src.nodata is not None:
                    val = ~np.all(arr == src.nodata, axis=0)
                else:
                    val = np.ones((lh, lw), dtype=bool)
                mascara[j * lh : (j + 1) * lh, i * lw : (i + 1) * lw] = val.astype("uint8")
            tmp.unlink(missing_ok=True)
            print(f"        bloco {j * nx + i + 1}/{nx * ny} ok ({len(r.content)/1e6:.1f} MB)")
    with rasterio.open(
        destino,
        "w",
        driver="GTiff",
        height=alt,
        width=larg,
        count=bandas,
        dtype="float32",
        crs=c.CRS_LOCAL,
        transform=from_origin(x0, y1, escala, escala),
        compress="deflate",
        nodata=float("nan"),
    ) as dst:
        dst.write(dados)
        dst.write_mask(mascara * 255)
    print(f"        salvo {destino.name} ({destino.stat().st_size/1e6:.1f} MB, {larg}x{alt} px, {bandas} bandas)")
    return dados


# ------------------------------------------------------------------- mosaico S2
def colecao_s2(inicio, fim):
    cs = ee.ImageCollection(c.CS_PLUS)
    s2 = (
        ee.ImageCollection(c.S2)
        .filterDate(inicio, fim)
        .filterBounds(caixa)
        .linkCollection(cs, ["cs", "cs_cdf"])
    )
    return s2


def compor(inicio, fim, bandas, prefixo):
    col = colecao_s2(inicio, fim)

    def limpar(img):
        # cs_cdf alto = pixel provavelmente limpo
        return img.updateMask(img.select("cs_cdf").gte(0.6))

    n = col.size().getInfo()
    med = col.map(limpar).select(bandas).median()
    med = med.rename([f"{b}_{prefixo}" for b in bandas])
    return med, n


print("[1/3] montando o mosaico Sentinel-2 (mediana por estacao, mascara Cloud Score+)")
img_seca, n_seca = compor(
    *c.SECA, ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"], "seca"
)
img_chuva, n_chuva = compor(*c.CHUVA, ["B4", "B8", "B11"], "chuva")
print(f"      cenas na seca: {n_seca} | cenas na chuva: {n_chuva}")


def indices(seca, chuva):
    ndvi_s = seca.select("B8_seca").subtract(seca.select("B4_seca")).divide(
        seca.select("B8_seca").add(seca.select("B4_seca"))
    )
    ndwi_s = seca.select("B3_seca").subtract(seca.select("B8_seca")).divide(
        seca.select("B3_seca").add(seca.select("B8_seca"))
    )
    ndre_s = seca.select("B8_seca").subtract(seca.select("B5_seca")).divide(
        seca.select("B8_seca").add(seca.select("B5_seca"))
    )
    ndbi_s = seca.select("B11_seca").subtract(seca.select("B8_seca")).divide(
        seca.select("B11_seca").add(seca.select("B8_seca"))
    )
    ndvi_c = chuva.select("B8_chuva").subtract(chuva.select("B4_chuva")).divide(
        chuva.select("B8_chuva").add(chuva.select("B4_chuva"))
    )
    ndwi_c = chuva.select("B4_chuva").subtract(chuva.select("B8_chuva")).divide(
        chuva.select("B4_chuva").add(chuva.select("B8_chuva"))
    )
    return ee.Image.cat(
        [
            ndvi_s.rename("NDVI_seca"),
            ndwi_s.rename("NDWI_seca"),
            ndre_s.rename("NDRE_seca"),
            ndbi_s.rename("NDBI_seca"),
            ndvi_c.rename("NDVI_chuva"),
            ndwi_c.rename("NDWI_chuva"),
        ]
    )


ind = indices(img_seca, img_chuva)

x0, y0, x1, y1, larg, alt = grade_utm(caixa, c.ESCALA, 3, 3)
print(f"      grade: {larg} x {alt} px ({larg*c.ESCALA/1000:.1f} x {alt*c.ESCALA/1000:.1f} km)")

alvo = c.DADOS / "mosaico_s2.tif"
if alvo.exists() and not FORCAR:
    print(f"[2/3] reaproveitando {alvo.name} (use --forcar para refazer)")
    bandas_nomes = list(c.BANDAS)
else:
    print("      baixando 19 bandas em blocos 3x3...")
    pilha = ee.Image.cat([img_seca, ind, img_chuva]).toFloat()
    baixar_blocos(pilha, x0, y0, x1, y1, larg, alt, c.ESCALA, alvo, 3, 3)
    bandas_nomes = pilha.bandNames().getInfo()

# ------------------------------------------------------------------ rotulos MB
alvo_lab = c.DADOS / "rotulos_mb.tif"
print("[3/3] rotulos MapBiomas na mesma grade de 20 m (vizinho mais proximo)")
if alvo_lab.exists() and not FORCAR:
    print(f"      reaproveitando {alvo_lab.name}")
else:
    mapa = ee.Image(f"{c.MB_COL11}/collection_11_{c.MB_ANO}_v1").select("classification")
    mapa = mapa.reproject(crs=c.CRS_LOCAL, scale=c.ESCALA).toUint8()
    xa, ya, xb, yb, la, aa = x0, y0, x1, y1, larg, alt
    assert (la, aa) == (larg, alt), "grade dos rotulos diferente da grade do mosaico"
    baixar_blocos(mapa, xa, ya, xb, yb, la, aa, c.ESCALA, alvo_lab, 3, 3)

# --------------------------------------------------------- RGB 10 m (recortes)
alvo_rgb = c.DADOS / "rgb_10m.tif"
if alvo_rgb.exists() and not FORCAR:
    print(f"      reaproveitando {alvo_rgb.name}")
else:
    rgb = c.rgb_do_mosaico(img_seca)
    xa, ya, xb, yb, la, aa = grade_utm(caixa, 10, 2, 2)
    baixar_blocos(rgb, xa, ya, xb, yb, la, aa, 10, alvo_rgb, 2, 2)

c.salvar_json(
    {
        "bandas": bandas_nomes,
        "n_cenas_seca": n_seca,
        "n_cenas_chuva": n_chuva,
        "grade": [larg, alt],
        "escala_m": c.ESCALA,
        "crs": c.CRS_LOCAL,
        "periodo_seca": c.SECA,
        "periodo_chuva": c.CHUVA,
        "mascara_nuvem": "Cloud Score+ cs_cdf >= 0.6",
    },
    "mosaico_meta.json",
)
print("      pronto: dados/mosaico_s2.tif, dados/rotulos_mb.tif, dados/rgb_10m.tif")
