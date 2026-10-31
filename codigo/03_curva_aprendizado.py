"""
Passo 03 - a duvida "quantas amostras de treino?".

Experimento: curva de aprendizado do Random Forest no recorte escolhido.

  * N amostras POR CLASSE de treino: 25, 50, 100, 200, 400, 800
  * 5 repeticoes por N (sorteios diferentes)
  * o conjunto de teste e SEMPRE o mesmo dentro de cada protocolo
  * duas formas de separar treino e teste, para mostrar a inflacao espacial:
      aleatorio  -> pixels sorteados ao acaso (treino e teste podem ser vizinhos)
      blocos     -> blocos de 2 x 2 km inteiros vao para treino ou para teste

Os rotulos sao os do MapBiomas (referencia provisoria, ver RELATORIO.md). Portanto
os numeros medem "quanto o modelo reproduz o MapBiomas", nao acuracia real.

Saidas:
  dados/curva_aprendizado.csv   (uma linha por N x repeticao x protocolo)
  dados/curva_resumo.json       (medias, desvios e ponto de estabilizacao)
  figuras/curva_aprendizado.png
"""

from __future__ import annotations

import csv
import time
import warnings

import numpy as np
import rasterio
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support

warnings.filterwarnings("ignore")

import common as c

NS = [25, 50, 100, 200, 400, 800, 1600, 3200]
REPS = 5
SEMENTE = 42
BLOCO_PX = 100  # 100 pixels x 20 m = 2 km


# ------------------------------------------------------------------- leitura
X, y, valido, forma = c.carregar_bandas()
lin, col = np.nonzero(valido)
# identidade do bloco de 2 km de cada pixel
bloco = (lin // BLOCO_PX) * 1000 + (col // BLOCO_PX)
n_classes = len(c.CLASSES)
print(f"pixels validos: {len(y):,} | bandas: {X.shape[1]}")
contagem = np.bincount(y, minlength=n_classes)
for nome, n in zip(c.CLASSES, contagem):
    print(f"  {nome:<14s} {n:8,d} px")

idx_por_classe = [np.nonzero(y == k)[0] for k in range(n_classes)]


# ----------------------------------------------------------------- protocolos
rng = np.random.default_rng(SEMENTE)

# (A) aleatorio: 20% dos pixels para teste
perm = rng.permutation(len(y))
corte = int(0.2 * len(y))
teste_a = np.sort(perm[:corte])
treino_pool_a = np.sort(perm[corte:])

# (B) blocos: 20% dos blocos de 2 km para teste
blocos_unicos = np.unique(bloco)
rng_b = np.random.default_rng(SEMENTE + 1)
teste_blocos = set(rng_b.choice(blocos_unicos, size=max(1, int(0.2 * len(blocos_unicos))), replace=False).tolist())
mask_teste_b = np.isin(bloco, list(teste_blocos))
teste_b = np.nonzero(mask_teste_b)[0]
treino_pool_b = np.nonzero(~mask_teste_b)[0]
print(f"teste aleatorio: {len(teste_a):,} px | teste por blocos: {len(teste_b):,} px "
      f"em {len(teste_blocos)} de {len(blocos_unicos)} blocos")

# os pools filtram os pixels de cada classe
pool_por_classe = {}
for nome, pool in (("aleatorio", treino_pool_a), ("blocos", treino_pool_b)):
    pool_por_classe[nome] = [np.intersect1d(idx, pool) for idx in idx_por_classe]
    faltando = [c.CLASSES[k] for k, v in enumerate(pool_por_classe[nome]) if len(v) < max(NS)]
    if faltando:
        print(f"  aviso: em '{nome}' estas classes tem menos de {max(NS)} px: {faltando}")


def avaliar(modelo, Xte, yte) -> dict:
    pred = modelo.predict(Xte)
    p, r, f, _ = precision_recall_fscore_support(
        yte, pred, labels=range(n_classes), zero_division=0
    )
    f1_por_classe = f1_score(yte, pred, labels=range(n_classes), average=None, zero_division=0)
    return {
        "acuracia_global": accuracy_score(yte, pred),
        "f1_eucalipto": f1_por_classe[0],
        "precisao_eucalipto": p[0],
        "recall_eucalipto": r[0],
        "f1_macro": f1_score(yte, pred, average="macro", zero_division=0),
    }


# ------------------------------------------------------------------ execucao
linhas = []
t0 = time.time()
for protocolo, teste in (("aleatorio", teste_a), ("blocos", teste_b)):
    Xte, yte = X[teste], y[teste]
    for n in NS:
        for rep in range(REPS):
            r = np.random.default_rng(SEMENTE + 1000 * NS.index(n) + rep)
            escolhidos = []
            for k in range(n_classes):
                pool = pool_por_classe[protocolo][k]
                take = min(n, len(pool))
                escolhidos.append(r.choice(pool, size=take, replace=False))
            tr = np.concatenate(escolhidos)
            modelo = RandomForestClassifier(
                n_estimators=200,
                min_samples_leaf=1,
                max_features="sqrt",
                n_jobs=-1,
                random_state=int(r.integers(1e6)),
            )
            modelo.fit(X[tr], y[tr])
            m = avaliar(modelo, Xte, yte)
            m.update({"protocolo": protocolo, "n_por_classe": n, "rep": rep,
                      "n_treino": len(tr)})
            linhas.append(m)
        sub = [l for l in linhas if l["protocolo"] == protocolo and l["n_por_classe"] == n]
        print(f"  {protocolo:<10s} N={n:<4d} F1 euc={np.mean([s['f1_eucalipto'] for s in sub]):.3f} "
              f"acc={np.mean([s['acuracia_global'] for s in sub]):.3f}  ({time.time()-t0:.0f}s)")

campos = ["protocolo", "n_por_classe", "rep", "n_treino", "acuracia_global",
          "f1_eucalipto", "precisao_eucalipto", "recall_eucalipto", "f1_macro"]
with (c.DADOS / "curva_aprendizado.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=campos)
    w.writeheader()
    for l in linhas:
        w.writerow({k: (round(l[k], 5) if isinstance(l[k], float) else l[k]) for k in campos})

# ------------------------------------------------------------- resumo e figura
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

resumo = {}
fig, eixos = plt.subplots(1, 2, figsize=(11, 4.2), dpi=160)
for protocolo, cor, marca in (("aleatorio", "#c0392b", "o"), ("blocos", "#1f6feb", "s")):
    med, sd, acc, acc_sd = [], [], [], []
    for n in NS:
        vals = [l["f1_eucalipto"] for l in linhas
                if l["protocolo"] == protocolo and l["n_por_classe"] == n]
        acs = [l["acuracia_global"] for l in linhas
               if l["protocolo"] == protocolo and l["n_por_classe"] == n]
        med.append(np.mean(vals)); sd.append(np.std(vals, ddof=1))
        acc.append(np.mean(acs)); acc_sd.append(np.std(acs, ddof=1))
    resumo[protocolo] = {
        "n": NS,
        "f1_eucalipto_media": [round(v, 4) for v in med],
        "f1_eucalipto_dp": [round(v, 4) for v in sd],
        "acuracia_global_media": [round(v, 4) for v in acc],
        "acuracia_global_dp": [round(v, 4) for v in acc_sd],
    }
    eixos[0].errorbar(NS, med, yerr=sd, color=cor, marker=marca, capsize=3,
                      label=f"treino/teste {protocolo}")
    eixos[1].errorbar(NS, acc, yerr=acc_sd, color=cor, marker=marca, capsize=3,
                      label=f"treino/teste {protocolo}")

# ponto de estabilizacao: primeiro N a partir do qual o ganho de F1 por dobrada
# de amostras fica abaixo de 0,01 (se nunca fica, a curva nao estabilizou)
for protocolo in ("aleatorio", "blocos"):
    med = np.array(resumo[protocolo]["f1_eucalipto_media"])
    ganhos = np.diff(med)
    resumo[protocolo]["ganhos_por_dobrada"] = [round(float(g), 4) for g in ganhos]
    estavel = None
    for i, g in enumerate(ganhos):
        if np.all(ganhos[i:] < 0.01):
            estavel = int(NS[i])
            break
    resumo[protocolo]["n_estabiliza_f1"] = estavel
    resumo[protocolo]["ganho_total_f1"] = round(float(med[-1] - med[0]), 4)
    resumo[protocolo]["f1_em_3200"] = float(med[-1])

for ax, titulo, ylab in (
    (eixos[0], "F1 da classe eucalipto", "F1 (eucalipto)"),
    (eixos[1], "Acuracia global", "acuracia global"),
):
    ax.set_xscale("log")
    ax.set_xticks(NS)
    ax.set_xticklabels([str(n) for n in NS])
    ax.set_xlabel("amostras de treino por classe")
    ax.set_ylabel(ylab)
    ax.set_title(titulo)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="lower right")
    ax.set_ylim(0, 1.02)
fig.suptitle("Curva de aprendizado - Random Forest, recorte de teste em Goias", fontsize=11)
fig.tight_layout()
fig.savefig(c.FIGURAS / "curva_aprendizado.png", bbox_inches="tight")
print(f"figura: figuras/curva_aprendizado.png ({time.time()-t0:.0f}s no total)")

resumo["pixels_por_classe"] = {n: int(v) for n, v in zip(c.CLASSES, contagem)}
resumo["n_teste_aleatorio"] = int(len(teste_a))
resumo["n_teste_blocos"] = int(len(teste_b))
resumo["blocos_2km_teste"] = len(teste_blocos)
resumo["blocos_2km_total"] = int(len(blocos_unicos))
resumo["ns"] = NS
resumo["repeticoes"] = REPS
c.salvar_json(resumo, "curva_resumo.json")

for protocolo in ("aleatorio", "blocos"):
    r = resumo[protocolo]
    print(f"\n{protocolo}: F1 eucalipto por N = " +
          ", ".join(f"{n}:{v:.3f}" for n, v in zip(NS, r["f1_eucalipto_media"])))
    print("  ganho de F1 a cada dobrada de amostras: " +
          ", ".join(f"+{g:.3f}" for g in r["ganhos_por_dobrada"]))
    if r["n_estabiliza_f1"] is None:
        print("  a curva NAO estabilizou ate o maior N testado")
    else:
        print(f"  estabiliza em N={r['n_estabiliza_f1']} (ganhos seguintes < 0,01)")
print("\nsalvo dados/curva_aprendizado.csv e dados/curva_resumo.json")
