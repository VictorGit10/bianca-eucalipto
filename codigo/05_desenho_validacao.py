"""
Passo 05 - desenho da validacao (Olofsson et al. 2014) e pagina de conferencia.

O que este script faz:

  1. Le o mapa produzido no passo 04 e calcula a area de cada estrato.
  2. Calcula o tamanho da amostra pela formula de Olofsson (amostragem aleatoria
     estratificada), usando como prior a acuracia do usuario estimada pela
     concordancia do mapa com o MapBiomas. O prior e uma aproximacao: a validacao
     de verdade substitui esse prior pelo dado de referencia que a pessoa marca.
  3. Sorteia os pontos em TODOS os pixels de cada estrato, com probabilidade
     conhecida e nao nula para cada pixel. Nao ha filtro de borda: excluir pixels
     de borda quebraria a amostragem probabilistica (e justamente na borda que o
     mapa mais erra), inflando a acuracia e enviesando a area. O ponto de borda
     se resolve na interpretacao, com a opcao "nao da para saber".
  4. Recorta duas imagens por ponto (detalhe de 700 m e contexto de 2 km) a
     partir do mosaico Sentinel-2 de 10 m ja baixado.
  5. Gera conferencia/index.html: pagina unica, offline, que mostra os pontos e
     guarda as marcacoes no navegador. A pagina e CEGA: nao tem a classe do mapa
     em lugar nenhum (nem no HTML, nem no CSV que ela exporta).
  6. Grava a chave (id -> estrato e classe do mapa) em dados/chave/pontos_chave.csv,
     que so o script de calculo (06) le.
  7. Gera tambem um CSV de exemplo claramente FICTICIO, para testar o passo 06.

Saidas:
  conferencia/index.html            (cega: id, lon, lat e imagens)
  conferencia/pontos.csv            (cega: id, lon, lat)
  conferencia/marcacoes_FICTICIO.csv
  dados/chave/pontos_chave.csv      (id, estrato, classe_mapa, lon, lat, x, y)
  dados/desenho_validacao.json
"""

from __future__ import annotations

import base64
import csv
import io
import json
import sys

import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer
from scipy.ndimage import uniform_filter

import common as c

SE_ALVO = 0.04  # erro padrao alvo da acuracia global (0,04 ~ +-8 pontos percentuais com 95%)
if "--se" in sys.argv:
    SE_ALVO = float(sys.argv[sys.argv.index("--se") + 1])
MIN_POR_ESTRATO = 10

# ---------------------------------------------------------------- 1. estratos
with rasterio.open(c.DADOS / "mapa_predito.tif") as src:
    mapa = src.read(1)
    transform = src.transform
valido = mapa != 255
area_px_km2 = (c.ESCALA ** 2) / 1e6
n_classes = len(c.CLASSES)
contagem = np.bincount(mapa[valido], minlength=n_classes)
area_estrato = contagem * area_px_km2
W = contagem / contagem.sum()
area_total = float(contagem.sum() * area_px_km2)

meta = c.ler_json("mapa_meta.json")
matriz = np.array(meta["matriz_mapa_x_mapbiomas"], dtype=float)
ua_prior = np.diag(matriz) / np.maximum(matriz.sum(1), 1)

# ------------------------------------------------------- 2. tamanho da amostra
S_h = np.sqrt(ua_prior * (1 - ua_prior))
tabela_se = {}
for se in (0.02, 0.03, 0.04, 0.05, 0.10):
    tabela_se[se] = int(np.ceil((np.sum(W * S_h) / se) ** 2))
n_bruto = tabela_se[round(SE_ALVO, 2)]
print(f"area mapeada: {area_total:.1f} km2")
print(f"prior de acuracia do usuario (concordancia com MapBiomas): "
      + ", ".join(f"{n}={v:.2f}" for n, v in zip(c.CLASSES, ua_prior)))
print(f"tamanho da amostra por erro padrao alvo: " +
      ", ".join(f"SE={k:.2f}->{v}" for k, v in tabela_se.items()))

# alocacao proporcional com piso
n_h = np.maximum(np.round(W * n_bruto).astype(int), MIN_POR_ESTRATO)
while n_h.sum() > n_bruto:  # tira dos maiores estratos
    i = int(np.argmax(n_h - MIN_POR_ESTRATO))
    n_h[i] -= 1
while n_h.sum() < n_bruto:  # poe nos maiores estratos
    n_h[int(np.argmax(W * n_bruto - n_h))] += 1
print("alocacao: " + ", ".join(f"{n}={k}" for n, k in zip(c.CLASSES, n_h)))

# ------------------------------------------------------------------ 3. pontos
# Sorteio uniforme em TODOS os pixels do estrato. Cada pixel tem probabilidade
# conhecida (n_h / N_h) de ser sorteado - e isso que o estimador exige.
rng = np.random.default_rng(2024)
pontos = []
for k in range(n_classes):
    lin, col = np.nonzero(mapa == k)
    escolha = rng.choice(len(lin), size=int(n_h[k]), replace=False)
    for i in escolha:
        pontos.append((int(lin[i]), int(col[i]), k))

# id aleatorio: a ordem dos pontos nao pode revelar o estrato
ordem = rng.permutation(len(pontos))
pontos = [pontos[i] for i in ordem]

# diagnostico (nao filtra nada): quantos pontos caem em pixel de borda do mapa
puro = np.zeros_like(mapa, dtype=bool)
for k in range(n_classes):
    frac = uniform_filter((mapa == k).astype("float32"), size=3)
    puro |= (mapa == k) & (frac > 0.999)
n_borda = sum(1 for lin, col, _ in pontos if not puro[lin, col])
print(f"pontos sorteados: {len(pontos)} | em pixel de borda do mapa: {n_borda} "
      f"({100*n_borda/len(pontos):.0f}%) - mantidos, sem filtro")

transformer = Transformer.from_crs(c.CRS_LOCAL, "EPSG:4326", always_xy=True)

with rasterio.open(c.DADOS / "rgb_10m.tif") as src:
    rgb = src.read().astype("float32")
    rgb_t = src.transform
rgb = c.esticar_rgb(rgb)


def recorte_rgb(lin20, col20, lado_m):
    """Recorta um quadrado de lado_m metros do RGB de 10 m centrado no pixel."""
    x = transform.c + (col20 + 0.5) * transform.a
    y = transform.f + (lin20 + 0.5) * transform.e
    h = int(lado_m / 10 / 2)
    col10 = int(round((x - rgb_t.c) / rgb_t.a - 0.5))
    lin10 = int(round((y - rgb_t.f) / rgb_t.e - 0.5))
    arr = rgb[:, max(0, lin10 - h): lin10 + h, max(0, col10 - h): col10 + h]
    return Image.fromarray(np.moveaxis(arr, 0, -1))


def b64(img: Image.Image, px: int) -> str:
    img = img.resize((px, px), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=72, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


registros = []  # inclui estrato/classe: vai so para dados/chave/pontos_chave.csv
for i, (lin, col, k) in enumerate(pontos, start=1):
    x = transform.c + (col + 0.5) * transform.a
    y = transform.f + (lin + 0.5) * transform.e
    lon, lat = transformer.transform(x, y)
    registros.append({
        "id": i,
        "estrato": c.CLASSES[k],
        "classe_mapa": k,
        "lon": round(lon, 6),
        "lat": round(lat, 6),
        "x": round(x, 1),
        "y": round(y, 1),
        "borda": not bool(puro[lin, col]),
        "img_det": b64(recorte_rgb(lin, col, 700), 240),
        "img_ctx": b64(recorte_rgb(lin, col, 2000), 320),
    })

# chave (so em dados/, para o calculo)
with (c.CHAVE / "pontos_chave.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["id", "estrato", "classe_mapa", "lon", "lat", "x_utm", "y_utm", "borda"])
    for r in registros:
        w.writerow([r["id"], r["estrato"], r["classe_mapa"], r["lon"], r["lat"],
                    r["x"], r["y"], int(r["borda"])])

# CSV que vai para a pesquisadora: cego
with (c.CONFERENCIA / "pontos.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["id", "lon", "lat"])
    for r in registros:
        w.writerow([r["id"], r["lon"], r["lat"]])
print(f"{len(registros)} pontos -> dados/chave/pontos_chave.csv e conferencia/pontos.csv (cego)")

# --------------------------------------------------- 4. CSV ficticio (teste)
cod2classe = {cod: i for i, nome in enumerate(c.CLASSES) for cod in c.GRUPOS[nome]}
with rasterio.open(c.DADOS / "rotulos_mb.tif") as src:
    rot = src.read(1)
rng_f = np.random.default_rng(99)
linhas_f = []
for r in registros:
    cod = int(rot[int((r["y"] - transform.f) / transform.e),
                  int((r["x"] - transform.c) / transform.a)])
    verdade = c.CLASSES[cod2classe[cod]] if cod in cod2classe else None
    u = rng_f.random()
    if verdade is None or u < 0.10:
        marca = "nao_sei"
    elif u < 0.25:
        marca = "nao_eucalipto" if verdade == "eucalipto" else "eucalipto"
    else:
        marca = "eucalipto" if verdade == "eucalipto" else "nao_eucalipto"
    linhas_f.append([r["id"], r["lon"], r["lat"], marca])

with (c.CONFERENCIA / "marcacoes_FICTICIO.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["id", "lon", "lat", "marcacao", "ficticio"])
    for l in linhas_f:
        w.writerow(l + ["SIM"])

# variante para testar a robustez do 06: todos os pontos de um estrato viram "nao sei"
estrato_por_id = {r["id"]: r["estrato"] for r in registros}
alvo_vazio = c.CLASSES[-1]
with (c.CONFERENCIA / "marcacoes_FICTICIO_estrato_vazio.csv").open(
        "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["id", "lon", "lat", "marcacao", "ficticio"])
    for l in linhas_f:
        marca = "nao_sei" if estrato_por_id[l[0]] == alvo_vazio else l[3]
        w.writerow([l[0], l[1], l[2], marca, "SIM"])

# -------------------------------------------------------------- 5. pagina HTML
MODELO = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Conferência do mapa de eucalipto</title>
<style>
:root{--tinta:#1c1c1c;--papel:#f6f4ee;--fraco:#8a8576;--ok:#1f6f43;--nao:#a3372a;--ns:#6b5f8a}
*{box-sizing:border-box}
body{margin:0;background:var(--papel);color:var(--tinta);font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
header{position:sticky;top:0;background:var(--papel);border-bottom:1px solid #ddd7c7;padding:12px 20px;display:flex;gap:18px;align-items:center;flex-wrap:wrap;z-index:10}
h1{font-size:16px;margin:0;font-weight:600}
.barra{flex:1;min-width:140px;height:8px;background:#e2ddcd;border-radius:4px;overflow:hidden}
.barra>i{display:block;height:100%;background:var(--ok);width:0;transition:width .2s}
small{color:var(--fraco)}
main{max-width:1000px;margin:0 auto;padding:18px 20px 60px}
.instrucoes{background:#fff;border:1px solid #e4dfd1;border-radius:10px;padding:14px 16px;margin-bottom:16px}
.instrucoes p{margin:.35em 0}
.cartao{background:#fff;border:1px solid #e4dfd1;border-radius:12px;padding:16px;display:grid;grid-template-columns:300px 1fr;gap:18px}
.imgs{display:flex;flex-direction:column;gap:8px}
.imgs img{width:100%;border-radius:8px;display:block;image-rendering:auto}
.moldura{position:relative;display:block;line-height:0}
.moldura img{width:100%;border-radius:8px;display:block}
.marcador{position:absolute;left:50%;top:50%;width:2.857%;aspect-ratio:1/1;
  transform:translate(-50%,-50%);border:1.5px solid #ff2d55;
  box-shadow:0 0 0 1.5px rgba(255,255,255,.95), 0 0 4px 2px rgba(0,0,0,.65);
  pointer-events:none}
.marcador.oculto{display:none}
.lado h2{margin:.1em 0 .4em;font-size:20px}
.coord{font-family:ui-monospace,Consolas,monospace;font-size:13px;color:var(--fraco);word-break:break-all}
.acoes{display:flex;flex-direction:column;gap:10px;margin-top:18px;max-width:420px}
button{font:inherit;padding:11px 14px;border-radius:9px;border:1.5px solid #d8d2c2;background:#fff;cursor:pointer;text-align:left}
button:hover{border-color:#9d9683}
button.escolhido.b-euc{border-color:var(--ok);background:#eaf5ee}
button.escolhido.b-nao{border-color:var(--nao);background:#fbeceb}
button.escolhido.b-ns{border-color:var(--ns);background:#f0eef7}
.nav{display:flex;gap:10px;margin-top:22px;flex-wrap:wrap}
.nav button{padding:9px 16px}
kbd{font-family:ui-monospace,monospace;background:#f0ece1;border:1px solid #d8d2c2;border-radius:4px;padding:1px 5px;font-size:12px}
.rodape{margin-top:26px;display:flex;gap:12px;flex-wrap:wrap;align-items:center}
#aviso{font-size:13px;color:var(--fraco)}
@media(max-width:760px){.cartao{grid-template-columns:1fr}}
</style>
</head>
<body>
<header>
  <h1>Conferência do mapa de eucalipto</h1>
  <div class="barra"><i id="progresso"></i></div>
  <small id="contador">0 de 0 marcados</small>
</header>
<main>
  <div class="instrucoes">
    <p><b>O que fazer:</b> para cada ponto, olhe as duas imagens Sentinel-2 e marque se ali havia <b>plantio de eucalipto</b>, <b>outra cobertura</b> ou se <b>não dá para saber</b>.</p>
    <p>A imagem de cima é o detalhe (700 m de lado); a de baixo mostra o contexto (2 km). Use as teclas <kbd>1</kbd> <kbd>2</kbd> <kbd>3</kbd> e as setas para navegar.</p>
    <p><b>O quadrado vermelho</b> marca o pixel de 20 m que você está classificando, no centro da imagem de detalhe. Como a imagem tem 700 m em ~300 px na tela, o pixel de 20 m ocupa uns 3% da largura. A tecla <kbd>m</kbd> (ou o botão abaixo das imagens) mostra e oculta o quadrado, para você ver o entorno sem ele.</p>
    <p><b>Regra de rotulagem:</b> classifique pelo que ocupa a <b>maior parte desse pixel</b>, não pelo que está em volta. Se o pixel cai em transição de talhão e você não consegue decidir, use <b>3 - não dá para saber</b>; não force um palpite.</p>
    <p><b>O que é "borda":</b> um ponto é de borda quando a vizinhança de 3 x 3 pixels do mapa (60 m x 60 m) tem mais de uma classe. São 44 dos 108 pontos e eles fazem parte da amostra de propósito: é onde o mapa mais erra. Não é defeito do sorteio nem motivo para responder diferente.</p>
    <p><b>Ressalva sobre a referência:</b> a imagem é Sentinel-2 de 10 m, a mesma fonte usada no mapa. Marcar nela mede a concordância com o que se vê <i>nessa imagem</i>, não a verdade de campo. Nos pontos duvidosos, abra o link do Google Maps (imagem de alta resolução) e, se possível, compare outra data: plantio jovem e talhão recém-colhido se parecem com pastagem no Sentinel-2.</p>
    <p>Sua marcação fica salva neste navegador. Ao terminar, clique em <b>Exportar CSV</b>. Nada é enviado para a internet: a página funciona offline.</p>
    <p>Esta página <b>não mostra</b> (e não guarda) a classe que o mapa previu para nenhum ponto: a conferência é cega.</p>
  </div>
  <div class="cartao">
    <div class="imgs">
      <div class="moldura">
        <img id="img_det" alt="detalhe">
        <div id="marcador" class="marcador"></div>
      </div>
      <img id="img_ctx" alt="contexto">
      <button id="btn_marcador" style="font-size:13px;padding:7px 10px">Ocultar marcador (m)</button>
    </div>
    <div class="lado">
      <h2 id="titulo">Ponto 1</h2>
      <div class="coord" id="coord"></div>
      <div class="acoes">
        <button class="b-euc" data-v="eucalipto">1 - Eucalipto (plantio)</button>
        <button class="b-nao" data-v="nao_eucalipto">2 - Outra cobertura (não é eucalipto)</button>
        <button class="b-ns" data-v="nao_sei">3 - Não dá para saber</button>
      </div>
      <div class="nav">
        <button id="anterior">&larr; Anterior</button>
        <button id="proximo">Próximo &rarr;</button>
      </div>
      <p><small><a id="mapa_link" href="#" target="_blank" rel="noopener">abrir no Google Maps (precisa de internet)</a></small></p>
    </div>
  </div>
  <div class="rodape">
    <button id="exportar"><b>Exportar CSV</b></button>
    <button id="limpar">Apagar todas as marcações</button>
    <span id="aviso"></span>
  </div>
</main>
<script>
const PONTOS = __DADOS__;
const CHAVE = "conferencia-eucalipto-v1";
let marcacoes = {};
try { marcacoes = JSON.parse(localStorage.getItem(CHAVE) || "{}"); } catch (e) { marcacoes = {}; }
let atual = 0;

function salvar(){ try { localStorage.setItem(CHAVE, JSON.stringify(marcacoes)); } catch (e) {} }
function pinta(){
  const p = PONTOS[atual];
  document.getElementById("titulo").textContent = "Ponto " + p.id + "  (" + (atual+1) + " de " + PONTOS.length + ")";
  document.getElementById("coord").textContent = p.lat.toFixed(5) + ", " + p.lon.toFixed(5);
  document.getElementById("img_det").src = p.img_det;
  document.getElementById("img_ctx").src = p.img_ctx;
  document.getElementById("img_det").alt = "detalhe do ponto " + p.id;
  document.getElementById("mapa_link").href = "https://www.google.com/maps/@" + p.lat + "," + p.lon + ",600m/data=!3m1!1e3";
  document.querySelectorAll(".acoes button").forEach(b => {
    b.classList.toggle("escolhido", marcacoes[p.id] === b.dataset.v);
  });
  const feitos = Object.values(marcacoes).filter(v => v).length;
  document.getElementById("contador").textContent = feitos + " de " + PONTOS.length + " marcados";
  document.getElementById("progresso").style.width = (100*feitos/PONTOS.length) + "%";
}
function marcar(v){
  marcacoes[PONTOS[atual].id] = v;
  salvar(); pinta();
  if (atual < PONTOS.length - 1) { atual++; pinta(); }
}
function mover(d){ atual = Math.min(PONTOS.length-1, Math.max(0, atual+d)); pinta(); }
document.querySelectorAll(".acoes button").forEach(b => b.onclick = () => marcar(b.dataset.v));
document.getElementById("anterior").onclick = () => mover(-1);
document.getElementById("proximo").onclick = () => mover(1);
let marcadorLigado = true;
function alternarMarcador(){
  marcadorLigado = !marcadorLigado;
  document.getElementById("marcador").classList.toggle("oculto", !marcadorLigado);
  document.getElementById("btn_marcador").textContent =
    (marcadorLigado ? "Ocultar" : "Mostrar") + " marcador (m)";
}
document.getElementById("btn_marcador").onclick = alternarMarcador;
document.addEventListener("keydown", e => {
  if (e.key === "1") marcar("eucalipto");
  else if (e.key === "2") marcar("nao_eucalipto");
  else if (e.key === "3") marcar("nao_sei");
  else if (e.key === "m" || e.key === "M") alternarMarcador();
  else if (e.key === "ArrowLeft") mover(-1);
  else if (e.key === "ArrowRight") mover(1);
});
document.getElementById("exportar").onclick = () => {
  const linhas = [["id","lon","lat","marcacao"]];
  PONTOS.forEach(p => linhas.push([p.id, p.lon, p.lat, marcacoes[p.id] || ""]));
  const csv = linhas.map(l => l.join(",")).join("\\n");
  const a = document.createElement("a");
  a.href = "data:text/csv;charset=utf-8," + encodeURIComponent(csv);
  a.download = "marcacoes.csv";
  a.click();
  document.getElementById("aviso").textContent = "CSV gerado: " + (linhas.length - 1) + " pontos.";
};
document.getElementById("limpar").onclick = () => {
  if (confirm("Apagar todas as marcações deste navegador?")) { marcacoes = {}; salvar(); atual = 0; pinta(); }
};
pinta();
</script>
</body>
</html>
"""

dados_js = [
    {"id": r["id"], "lon": r["lon"], "lat": r["lat"],
     "img_det": r["img_det"], "img_ctx": r["img_ctx"]}
    for r in registros
]
html = MODELO.replace("__DADOS__", json.dumps(dados_js, ensure_ascii=False))
(c.CONFERENCIA / "index.html").write_text(html, encoding="utf-8")

# checagem automatica da conferencia cega (se falhar, o script para)
for proibida in ("classe_mapa", "estrato"):
    if proibida in html:
        raise SystemExit(f"ERRO: '{proibida}' apareceu no HTML - a conferencia nao e cega")
chaves_ok = {"id", "lon", "lat", "img_det", "img_ctx"}
if any(set(d) != chaves_ok for d in dados_js):
    raise SystemExit("ERRO: o array de pontos tem chave alem de id/lon/lat/imagens")
print(f"pagina: conferencia/index.html ({len(html)/1e6:.1f} MB, offline)")
print("checagem cega: ok (0 ocorrencias de classe_mapa/estrato; pontos so com id/lon/lat/imagens)")

c.salvar_json(
    {
        "se_alvo": SE_ALVO,
        "n_por_erro_padrao": tabela_se,
        "n_pontos": int(sum(n_h)),
        "alocacao": {n: int(v) for n, v in zip(c.CLASSES, n_h)},
        "area_estrato_km2": {n: round(float(v), 1) for n, v in zip(c.CLASSES, area_estrato)},
        "area_total_km2": round(area_total, 1),
        "ua_prior": {n: round(float(v), 3) for n, v in zip(c.CLASSES, ua_prior)},
        "amostragem": "uniforme em todos os pixels do estrato (sem filtro de borda)",
        "pontos_em_borda": int(n_borda),
        "pct_pontos_em_borda": round(100 * n_borda / len(pontos), 1),
        "pixels_puros_3x3": int(puro.sum()),
    },
    "desenho_validacao.json",
)
print("salvo dados/desenho_validacao.json")
