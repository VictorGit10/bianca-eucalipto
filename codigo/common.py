"""
Funcoes comuns aos scripts deste projeto.

Tudo em portugues. Rode os scripts na ordem indicada no README:

    01_escolher_area.py     -> escolhe o recorte de teste e salva dados/recorte.json
    02_baixar_imagens.py    -> baixa (Earth Engine) o mosaico Sentinel-2 e os rotulos do MapBiomas
    03_curva_aprendizado.py -> curva de aprendizado (a duvida "quantas amostras")
    04_mapa.py              -> treina o modelo final, gera o mapa e o PNG da area
    05_desenho_validacao.py -> sorteio estratificado (Olofsson) + pagina HTML de conferencia
    06_acuracia.py          -> le o CSV marcado e calcula acuracias e area ajustada
    07_controle.py          -> testes de controle (o classificador e o estimador funcionam?)

Os arquivos grandes (GeoTIFF baixado) ficam em dados/ e nao devem ser comitados.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
FIGURAS = RAIZ / "figuras"
CONFERENCIA = RAIZ / "conferencia"
# a chave da conferencia cega fica fora da pasta que vai para a pesquisadora
CHAVE = DADOS / "chave"
for _p in (DADOS, FIGURAS, CONFERENCIA, CHAVE):
    _p.mkdir(exist_ok=True)

PROJETO_EE = "SEU-PROJETO-EARTH-ENGINE"

# Assets publicos usados (nenhum exige cadastro alem da conta Earth Engine ja autenticada)
MB_COL11 = "projects/mapbiomas-public/assets/brazil/lulc/v1"
MB_ANO = 2024
S2 = "COPERNICUS/S2_SR_HARMONIZED"
CS_PLUS = "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED"
MUNICIPIOS = "FAO/GAUL/2015/level2"  # nivel 2 = municipios no Brasil (publico)

# Epocas do mosaico (um ano agricola: seca de 2024 + chuva de 2024/2025)
SECA = ("2024-05-01", "2024-09-30")
CHUVA = ("2024-11-01", "2025-02-28")

CRS_LOCAL = "EPSG:32722"  # UTM 22S cobre o oeste de Goias
ESCALA = 20  # metros/pixel do recorte de trabalho

# Bandas e indices do mosaico, na ordem em que sao gravados em dados/mosaico_s2.tif
BANDAS_SECA = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"]
BANDAS_CHUVA = ["B4", "B8", "B11"]
INDICES = ["NDVI_seca", "NDWI_seca", "NDRE_seca", "NDBI_seca", "NDVI_chuva", "NDWI_chuva"]
BANDAS = (
    [f"{b}_seca" for b in BANDAS_SECA]
    + INDICES
    + [f"{b}_chuva" for b in BANDAS_CHUVA]
)

# Legenda MapBiomas Colecao 11 (apenas as classes que aparecem na area)
LEGENDA = {
    3: "Formacao Florestal",
    4: "Formacao Savanica",
    9: "Silvicultura",
    11: "Campo Alagado e Area Pantanosa",
    12: "Formacao Campestre",
    15: "Pastagem",
    20: "Cana",
    21: "Mosaico de Usos",
    25: "Outras Areas nao Vegetadas",
    30: "Mineracao",
    31: "Aquicultura",
    33: "Rio, Lago e Oceano",
    39: "Soja",
    40: "Arroz",
    41: "Outras Lavouras Temporarias",
    46: "Cafe",
    48: "Outras Lavouras Perenes",
}

# Agrupamento usado no teste: o que o Random Forest vai tentar separar.
# 9 = eucalipto (classe alvo). As demais classes sao agrupadas para o teste ficar
# com massa suficiente em cada grupo. A escolha do agrupamento e decisao cientifica
# da pesquisadora; aqui e apenas uma proposta explicita e reversivel.
GRUPOS = {
    "eucalipto": [9],
    "floresta": [3, 4],
    "pastagem": [15],
    "agricultura": [39, 20, 40, 41, 46, 48],
    "mosaico_agua": [21, 11, 12, 25, 30, 31, 33],
}
# ordem fixa das classes (importante para a matriz de confusao)
CLASSES = ["eucalipto", "floresta", "pastagem", "agricultura", "mosaico_agua"]
CLASSE_ALVO = "eucalipto"

# Cores do MapBiomas (aproximadas) para os mapas
CORES = {
    "eucalipto": "#7a5900",
    "floresta": "#1f8a4c",
    "pastagem": "#ffd966",
    "agricultura": "#e974ed",
    "mosaico_agua": "#9c9c9c",
}


def ee_init():
    """Inicializa o Earth Engine com o projeto ja autenticado nesta maquina."""
    import ee

    ee.Initialize(project=PROJETO_EE)
    return ee


def recorte() -> dict:
    """Le o recorte escolhido no passo 01."""
    caminho = DADOS / "recorte.json"
    if not caminho.exists():
        raise SystemExit(
            "Falta dados/recorte.json. Rode primeiro: python codigo/01_escolher_area.py"
        )
    return json.loads(caminho.read_text(encoding="utf-8"))


def salvar_json(obj, nome: str) -> Path:
    caminho = DADOS / nome
    caminho.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return caminho


def ler_json(nome: str):
    return json.loads((DADOS / nome).read_text(encoding="utf-8"))


def rgb_do_mosaico(img):
    """Converte reflectancia (DN 0-10000) em RGB uint8 para figura/recorte visual."""
    return (
        img.select(["B4_seca", "B3_seca", "B2_seca"])
        .divide(10000)
        .multiply(255 * 2.5)
        .clamp(0, 255)
        .toUint8()
    )


def esticar_rgb(arr, lo=2, hi=98):
    """Estica cada banda de um RGB (0-255 ou float) para 0-255 usando percentis."""
    import numpy as np

    arr = arr.astype("float32")
    out = np.zeros_like(arr)
    for i in range(arr.shape[0]):
        a, b = np.nanpercentile(arr[i], [lo, hi])
        if b <= a:
            b = a + 1
        out[i] = np.clip((arr[i] - a) / (b - a) * 255, 0, 255)
    return out.astype("uint8")


def carregar_bandas() -> "np.ndarray":
    """Le o mosaico baixado: array (pixels, bandas) so dos pixels validos.

    Retorna tambem a forma (linhas, colunas) e a mascara de pixels validos.
    Pixels validos = todas as 19 bandas finitas e rotulo MapBiomas conhecido.
    """
    import numpy as np
    import rasterio

    with rasterio.open(DADOS / "mosaico_s2.tif") as src:
        X = src.read().astype("float32")
    with rasterio.open(DADOS / "rotulos_mb.tif") as src:
        rot = src.read(1).astype("int16")

    codigo_para_classe = {}
    for i, nome in enumerate(CLASSES):
        for cod in GRUPOS[nome]:
            codigo_para_classe[cod] = i

    y = np.full(rot.shape, -1, dtype="int16")
    for cod, i in codigo_para_classe.items():
        y[rot == cod] = i

    valido = (y >= 0) & np.all(np.isfinite(X), axis=0)
    return X[:, valido].T, y[valido], valido, X.shape[1:]
