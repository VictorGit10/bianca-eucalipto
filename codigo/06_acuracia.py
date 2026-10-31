"""
Passo 06 - ler o CSV marcado na pagina de conferencia e calcular as acuracias
e a area ajustada, seguindo Olofsson et al. (2014).

Uso:
    python codigo/06_acuracia.py                       # usa conferencia/marcacoes.csv
    python codigo/06_acuracia.py caminho/do/arquivo.csv
    python codigo/06_acuracia.py --nao-sei erro        # "nao sei" conta como erro

O CSV precisa ter as colunas: id, estrato, classe_mapa, lon, lat, marcacao.
  marcacao = eucalipto | nao_eucalipto | nao_sei  (vazio = ponto nao marcado)

Politica padrao para "nao sei": o ponto sai da conta e o tamanho da amostra de
cada estrato e recalculado com os pontos restantes. Isso pode enviesar a area;
por isso o script imprime quantos pontos sairam e roda tambem a politica
"erro" (nao sei = nao eucalipto) para comparacao.

Saidas:
  dados/acuracia_resultado.json
  figuras/matriz_confusao.png
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

import common as c
import olofsson

POLITICA = "excluir"
args = [a for a in sys.argv[1:] if not a.startswith("--")]
if "--nao-sei" in sys.argv:
    POLITICA = sys.argv[sys.argv.index("--nao-sei") + 1]

caminho = args[0] if args else str(c.CONFERENCIA / "marcacoes.csv")
if not os.path.exists(caminho):
    alternativa = c.CONFERENCIA / "marcacoes_FICTICIO.csv"
    print(f"AVISO: {caminho} nao encontrado.")
    if alternativa.exists():
        print(f"       usando o CSV FICTICIO {alternativa.name} so para demonstrar a conta.")
        print("       Os numeros abaixo NAO sao resultado de validacao.")
        caminho = str(alternativa)
    else:
        raise SystemExit("Nada para calcular. Marque os pontos na pagina e exporte o CSV.")

df = pd.read_csv(caminho)
print(f"arquivo: {caminho} ({len(df)} linhas)")

# A classe do mapa nao esta no CSV (conferencia cega): ela vem da chave.
chave_caminho = c.CHAVE / "pontos_chave.csv"
if not chave_caminho.exists():
    raise SystemExit(
        "Falta dados/chave/pontos_chave.csv. Rode: python codigo/05_desenho_validacao.py"
    )
chave = pd.read_csv(chave_caminho)
sobrando = [col for col in ("estrato", "classe_mapa") if col in df.columns]
if sobrando:
    print(f"AVISO: colunas {sobrando} no CSV foram ignoradas; a chave e {chave_caminho.name}")
    df = df.drop(columns=sobrando)
df = df.merge(chave[["id", "estrato", "classe_mapa"]], on="id", how="left")
sem_chave = df["classe_mapa"].isna()
if sem_chave.any():
    print(f"AVISO: {int(sem_chave.sum())} pontos do CSV nao existem na chave e foram ignorados")
    df = df[~sem_chave]
df["classe_mapa"] = df["classe_mapa"].astype(int)

if "ficticio" in df.columns:
    print("*** ATENCAO: este CSV esta marcado como FICTICIO. Os numeros abaixo testam o")
    print("*** script, nao descrevem a acuracia do mapa.")
    FICTICIO = True
else:
    FICTICIO = False

df["marcacao"] = df["marcacao"].fillna("").astype(str).str.strip().str.lower()
df["marcacao"] = df["marcacao"].str.replace(" ", "_").replace({"não_sei": "nao_sei"})

validas = ["eucalipto", "nao_eucalipto", "nao_sei", ""]
invalidos = ~df["marcacao"].isin(validas)
if invalidos.any():
    print(f"AVISO: {invalidos.sum()} linhas com marcacao desconhecida foram ignoradas: "
          f"{sorted(df.loc[invalidos, 'marcacao'].unique())[:5]}")
    df = df[~invalidos]

vazios = int((df["marcacao"] == "").sum())
nao_sei = int((df["marcacao"] == "nao_sei").sum())
print(f"marcados: {len(df) - vazios} de {len(df)} | 'nao sei': {nao_sei} | em branco: {vazios}")
print("\nNOTA: a acuracia global calculada aqui e BINARIA (eucalipto x nao eucalipto).")
print("      Ela NAO e comparavel com a acuracia de 5 classes da curva de aprendizado")
print("      (passo 03): sao perguntas diferentes, com numero de classes diferente.")

desenho = c.ler_json("desenho_validacao.json")
areas = np.array([desenho["area_estrato_km2"][n] for n in c.CLASSES])
mapa_e_alvo = np.array([n == c.CLASSE_ALVO for n in c.CLASSES])


def rodar(politica: str):
    d = df.copy()
    if politica == "excluir":
        d = d[d["marcacao"].isin(["eucalipto", "nao_eucalipto"])]
    else:
        d = d[d["marcacao"] != ""]
        d["marcacao"] = d["marcacao"].replace({"nao_sei": "nao_eucalipto"})
    estrato = d["classe_mapa"].to_numpy(dtype=int)
    referencia = (d["marcacao"] == "eucalipto").to_numpy(dtype=int)

    alvo_idx = int(np.argmax(mapa_e_alvo))
    if (estrato == alvo_idx).sum() == 0:
        print(f"  AVISO (politica '{politica}'): nenhum ponto no estrato '{c.CLASSE_ALVO}'.")
        print("        Sem ele nao da para estimar a area do eucalipto nesta politica;")
        print("        o resultado dela e omitido. Use a politica 'nao_sei = nao eucalipto'.")
        return None, len(d)

    faltando = [c.CLASSES[k] for k in range(len(c.CLASSES)) if (estrato == k).sum() == 0]
    if faltando:
        print(f"  AVISO (politica '{politica}'): sem nenhum ponto em {faltando}.")
        print("        Esses estratos saem da estimativa (a area deles NAO e corrigida);")
        print("        o resultado abaixo vale para os estratos que sobraram.")
    return olofsson.estimar(estrato, referencia, areas, mapa_e_alvo,
                            area_total=float(areas.sum()), permitir_vazios=True), len(d)


res_excluir, n_ex = rodar("excluir")
res_erro, n_er = rodar("erro")
res = res_excluir if res_excluir is not None else res_erro
if res_excluir is None:
    print("\nA politica 'excluir' nao pode ser calculada; os numeros abaixo sao os da politica")
    print("'nao sei = nao eucalipto', que e a unica calculavel neste caso.")


def mostra(r, titulo):
    if r is None:
        print(f"\n=== {titulo}: nao calculavel (ver aviso acima) ===")
        return
    print(f"\n=== {titulo} (n = {r['n_total']}) ===")
    print(f"  acuracia global: {r['acuracia_global']:.3f} +- {1.96*r['se_acuracia_global']:.3f} (IC95)")
    ordem = ["alvo", "nao_alvo"]
    for k in ordem:
        v = r["acuracia_usuario"][k]
        print(f"  acuracia do usuario ({k}): {v['valor']:.3f} +- {1.96*v['se']:.3f}")
    for k in ordem:
        v = r["acuracia_produtor"][k]
        print(f"  acuracia do produtor ({k}): {v['valor']:.3f} +- {1.96*v['se']:.3f}")
    a = r["areas"]["alvo"]
    print(f"  area do mapa (contagem de pixels): {r['area_bruta_mapa_km2']:.1f} km2")
    print(f"  area ajustada pela amostra:        {a['area_estimada_km2']:.1f} +- "
          f"{1.96*a['se_km2']:.1f} km2 (IC95: {a['ic95_km2'][0]:.1f} a {a['ic95_km2'][1]:.1f})")
    print("  matriz (linhas = estrato do mapa, colunas = referencia):")
    print("    " + " ".join(f"{n:>12s}" for n in ["mapa", "eucalipto", "nao_euc"]))
    for i, nome in enumerate(c.CLASSES):
        print(f"    {nome:>12s} " + " ".join(f"{int(v):12d}" for v in (r["matriz"][i][1], r["matriz"][i][0])))

if res_excluir is not None:
    mostra(res_excluir, "politica padrao: 'nao sei' excluido")
print("\n(comparacao) o mesmo dado tratando 'nao sei' como 'nao eucalipto':")
mostra(res_erro, "politica 'nao sei' = nao eucalipto")

# --------------------------------------------------------------- figura
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

m = np.array(res["matriz"])[:, [1, 0]]
pct = np.array(res["p_ij"])[:, [1, 0]] * 100

fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=160)
im = ax.imshow(pct, cmap="Blues", vmin=0, aspect="auto")
ax.set_xticks([0, 1])
ax.set_xticklabels(["eucalipto", "nao eucalipto"])
ax.set_yticks(range(len(c.CLASSES)))
ax.set_yticklabels(c.CLASSES)
ax.set_xlabel("referencia (o que foi marcado na conferencia)", fontsize=9.5)
ax.set_ylabel("estrato do mapa", fontsize=9.5)
for i in range(len(c.CLASSES)):
    for j in range(2):
        cor = "white" if pct[i, j] > pct.max() * 0.6 else "black"
        ax.text(j, i, f"{int(m[i, j])} pts\n{pct[i, j]:.1f}% da area",
                ha="center", va="center", fontsize=9, color=cor)
ax.set_title(f"Matriz de confusao binaria (n = {res['n_total']}"
             + (", FICTICIO)" if FICTICIO else ")"), fontsize=11)
fig.colorbar(im, ax=ax, label="% da area total estimada")
fig.tight_layout()
fig.savefig(c.FIGURAS / "matriz_confusao.png", bbox_inches="tight")
print("\nfigura: figuras/matriz_confusao.png")

c.salvar_json(
    {
        "arquivo": str(caminho).replace("\\", "/").split("/")[-1],
        "chave": "dados/chave/pontos_chave.csv",
        "ficticio": FICTICIO,
        "politica_padrao": "excluir nao_sei",
        "politica_excluir_calculavel": res_excluir is not None,
        "n_marcados": int(len(df) - vazios),
        "n_nao_sei": int(nao_sei),
        "n_em_branco": int(vazios),
        "classe_alvo": c.CLASSE_ALVO,
        "tipo_acuracia": "binaria (eucalipto x nao eucalipto)",
        "resultado": res,
        "resultado_nao_sei_como_erro": res_erro,
    },
    "acuracia_resultado.json",
)
print("salvo dados/acuracia_resultado.json")
