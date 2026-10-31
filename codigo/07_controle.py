"""
Passo 07 - controles: os numeros do trabalho fazem sentido?

Sem controle, uma acuracia de 90% ou uma area de 65 km2 podem ser artefato de
codigo errado. Este script roda tres testes que falhariam se houvesse erro:

  1. Classificador com rotulos embaralhados: se o Random Forest aprende sinal de
     verdade, embaralhar os rotulos tem que DERRUBAR a acuracia para perto do
     acaso. Se continuasse alta, haveria vazamento de informacao.

  2. Classificador contra a "regra boba": prever sempre a classe mais comum.
     O modelo tem que ganhar da regra boba, senao nao esta servindo para nada.

  3. Estimador de area (Olofsson) com verdade conhecida: simulamos uma paisagem
     em que a area de eucalipto e conhecida, repetimos o sorteio estratificado
     300 vezes e conferimos (a) se o estimador acerta em media e (b) se o
     intervalo de 95% cobre a verdade em ~95% das repeticoes. Tambem mostramos
     que a contagem crua de pixels (sem correcao) erra feio nesse mesmo teste.

Saidas:
  dados/controle.json
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

import common as c
import olofsson

SEMENTE = 123
resultado = {}

# ------------------------------------------------------------------ 1 e 2
print("[1/4] controle do classificador (rotulos embaralhados e regra boba)")
X, y, valido, _ = c.carregar_bandas()
rng = np.random.default_rng(SEMENTE)
perm = rng.permutation(len(y))
corte = int(0.2 * len(y))
te, tr_pool = perm[:corte], perm[corte:]
N_TREINO = 1600
n_classes = len(c.CLASSES)

def treina(rotulos):
    escolhidos = []
    for k in range(n_classes):
        cand = np.intersect1d(np.nonzero(rotulos == k)[0], tr_pool)
        escolhidos.append(rng.choice(cand, size=min(N_TREINO, len(cand)), replace=False))
    tr = np.concatenate(escolhidos)
    m = RandomForestClassifier(n_estimators=200, n_jobs=-1, random_state=SEMENTE)
    m.fit(X[tr], rotulos[tr])
    return m

modelo = treina(y)
pred = modelo.predict(X[te])
acc_real = accuracy_score(y[te], pred)
f1_real = f1_score(y[te], pred, labels=[0], average=None)[0]

y_emb = y.copy()
y_emb[tr_pool] = rng.permutation(y_emb[tr_pool])
modelo_emb = treina(y_emb)
pred_emb = modelo_emb.predict(X[te])
acc_emb = accuracy_score(y[te], pred_emb)

classe_comum = int(np.bincount(y[te], minlength=n_classes).argmax())
acc_boba = float((y[te] == classe_comum).mean())

print(f"  modelo normal: acuracia {acc_real:.3f} | F1 eucalipto {f1_real:.3f}")
print(f"  rotulos embaralhados: acuracia {acc_emb:.3f}")
print(f"  regra boba ('sempre {c.CLASSES[classe_comum]}'): acuracia {acc_boba:.3f}")
resultado["classificador"] = {
    "acuracia_modelo": float(acc_real),
    "f1_eucalipto_modelo": float(f1_real),
    "acuracia_rotulos_embaralhados": float(acc_emb),
    "acuracia_regra_boba": acc_boba,
    "classe_mais_comum": c.CLASSES[classe_comum],
    "veredito": "ok" if acc_real > max(acc_emb, acc_boba) + 0.10 else "suspeito",
}
assert resultado["classificador"]["veredito"] == "ok", "controle do classificador falhou"

# ---------------------------------------------------------------- 3. area
print("\n[2/4] controle do estimador de area (verdade conhecida, 300 simulacoes)")
desenho = c.ler_json("desenho_validacao.json")
areas = np.array([desenho["area_estrato_km2"][n] for n in c.CLASSES])
n_h = np.array([desenho["alocacao"][n] for n in c.CLASSES])
mapa_e_alvo = np.array([n == c.CLASSE_ALVO for n in c.CLASSES])

# "verdade" simulada: fracao de eucalipto em cada estrato do mapa.
# O mapa acerta muito no estrato eucalipto e erra bastante nos outros.
theta = np.array([0.75, 0.05, 0.08, 0.02, 0.06])
verdade_km2 = float(np.sum(areas * theta))
bruto_km2 = float(areas[0])
print(f"  verdade simulada: {verdade_km2:.1f} km2 de eucalipto (mapa cru diria {bruto_km2:.1f})")

rng2 = np.random.default_rng(SEMENTE)
estimativas, cobertura, cobertura_bruta = [], [], []
for _ in range(300):
    estrato, referencia = [], []
    for i in range(len(areas)):
        k = rng2.binomial(n_h[i], theta[i])
        estrato += [i] * n_h[i]
        referencia += [1] * k + [0] * (n_h[i] - k)
    r = olofsson.estimar(np.array(estrato), np.array(referencia), areas, mapa_e_alvo)
    est = r["areas"]["alvo"]
    estimativas.append(est["area_estimada_km2"])
    cobertura.append(est["ic95_km2"][0] <= verdade_km2 <= est["ic95_km2"][1])
    cobertura_bruta.append(bruto_km2 == verdade_km2)

estimativas = np.array(estimativas)
erro_pct = 100 * (estimativas.mean() - verdade_km2) / verdade_km2
print(f"  estimador: media {estimativas.mean():.1f} km2 | vies {erro_pct:+.1f}% "
      f"| dp {estimativas.std(ddof=1):.1f} km2")
print(f"  cobertura do IC95: {100*np.mean(cobertura):.1f}% (esperado ~95%)")
resultado["estimador"] = {
    "verdade_km2": verdade_km2,
    "media_estimada_km2": float(estimativas.mean()),
    "vies_pct": float(erro_pct),
    "dp_km2": float(estimativas.std(ddof=1)),
    "cobertura_ic95_pct": float(100 * np.mean(cobertura)),
    "area_sem_correcao_km2": bruto_km2,
    "erro_da_area_sem_correcao_pct": float(100 * (bruto_km2 - verdade_km2) / verdade_km2),
    "theta_simulado": theta.tolist(),
    "n_simulacoes": 300,
    "veredito": "ok" if abs(erro_pct) < 5 and 90 <= 100 * np.mean(cobertura) <= 99 else "suspeito",
}
assert resultado["estimador"]["veredito"] == "ok", "controle do estimador falhou"

# ------------------- 3. sorteio em pixels "puros" x em todo o estrato (borda)
print("\n[3/4] efeito de excluir pixels de borda do sorteio (paisagem sintetica)")
from scipy.ndimage import uniform_filter

N_SIM = 400          # 400 x 400 pixels de 20 m = 8 x 8 km
Q = len(c.CLASSES)
rng3 = np.random.default_rng(11)

# verdade: fundo em blocos de 100 px com 4 classes + 40 talhoes de eucalipto (classe 0)
T = np.zeros((N_SIM, N_SIM), dtype=np.int16)
for i in range(0, N_SIM, 100):
    for j in range(0, N_SIM, 100):
        T[i:i + 100, j:j + 100] = rng3.integers(1, Q)
for _ in range(40):
    h, w = int(rng3.integers(25, 70)), int(rng3.integers(25, 70))
    r0, c0 = int(rng3.integers(0, N_SIM - h)), int(rng3.integers(0, N_SIM - w))
    T[r0:r0 + h, c0:c0 + w] = 0

# mapa: acerta no interior e "vaza" a classe vizinha na borda (erro tipico de classificador)
cont = np.stack([uniform_filter((T == k).astype(np.float32), 3, mode="nearest") for k in range(Q)])
ii, jj = np.meshgrid(np.arange(N_SIM), np.arange(N_SIM), indexing="ij")
borda = cont[T, ii, jj] < 0.999
cont2 = cont.copy()
cont2[T, ii, jj] = -1  # ignora a propria classe
viz = cont2.argmax(axis=0)
M = T.copy()
troca = borda & (rng3.random((N_SIM, N_SIM)) < 0.8)
# erosao assimetrica, como num classificador que suaviza bordas: o talhao pequeno
# perde borda para o vizinho mais frequentemente do que o vizinho perde para ele
prob_flip = np.where(T == 0, 0.85, 0.40)
troca = borda & (rng3.random((N_SIM, N_SIM)) < prob_flip)
M[troca] = viz[troca]

puro_M = np.zeros_like(M, dtype=bool)
for k in range(Q):
    frac = uniform_filter((M == k).astype(np.float32), 3, mode="nearest")
    puro_M |= (M == k) & (frac > 0.999)

area_km2 = (c.ESCALA ** 2) / 1e6
area_verdade = float((T == 0).sum() * area_km2)
areas_sim = np.bincount(M.ravel(), minlength=Q).astype(float) * area_km2
alvo_sim = np.array([k == 0 for k in range(Q)])
oa_verdade = float((M == T).mean())

W_sim = areas_sim / areas_sim.sum()
n_h_sim = np.maximum(np.round(W_sim * 108).astype(int), 10)
while n_h_sim.sum() > 108:
    n_h_sim[int(np.argmax(n_h_sim - 10))] -= 1

Mf, Tf = M.ravel(), (T.ravel() == 0).astype(int)
print(f"  verdade: {area_verdade:.1f} km2 de eucalipto | mapa cru diria {areas_sim[0]:.1f} km2")
print(f"  acuracia global real do mapa sintetico: {oa_verdade:.3f}")

# o mecanismo: dentro do estrato "eucalipto" do mapa, qual fracao e eucalipto de verdade?
sel = M == 0
theta_todos = float(Tf[sel.ravel()].mean())
theta_puros = float(Tf[(sel & puro_M).ravel()].mean())
print(f"  no estrato eucalipto, fracao que e eucalipto de verdade: "
      f"{theta_todos:.3f} (todos os pixels) x {theta_puros:.3f} (so pixels puros)")

def simular(so_puros: bool, repeticoes: int = 200, semente: int = 77):
    r = np.random.default_rng(semente)
    frames = [np.nonzero((M == k).ravel() & (puro_M.ravel() if so_puros else True))[0]
              for k in range(Q)]
    areas_est, oa_est, cobre = [], [], []
    for _ in range(repeticoes):
        est, ref = [], []
        for k in range(Q):
            take = min(int(n_h_sim[k]), len(frames[k]))
            esc = r.choice(frames[k], size=take, replace=False)
            est += [k] * take
            ref += Tf[esc].tolist()
        res = olofsson.estimar(np.array(est), np.array(ref), areas_sim, alvo_sim)
        a = res["areas"]["alvo"]
        areas_est.append(a["area_estimada_km2"])
        oa_est.append(res["acuracia_global"])
        cobre.append(a["ic95_km2"][0] <= area_verdade <= a["ic95_km2"][1])
    return np.array(areas_est), np.array(oa_est), float(np.mean(cobre))

area_puros, oa_puros, cob_puros = simular(True)
area_todos, oa_todos, cob_todos = simular(False)
for nome, a, oa, cob in (("so pixels puros", area_puros, oa_puros, cob_puros),
                         ("todo o estrato", area_todos, oa_todos, cob_todos)):
    print(f"  {nome:16s}: area {a.mean():5.1f} km2 (vies {100*(a.mean()-area_verdade)/area_verdade:+5.1f}%)"
          f" | acuracia {oa.mean():.3f} (vies {100*(oa.mean()-oa_verdade):+5.1f} p.p.)"
          f" | IC95 cobre a verdade {100*cob:.0f}%")

resultado["filtro_de_borda"] = {
    "verdade_km2": area_verdade,
    "area_crua_mapa_km2": float(areas_sim[0]),
    "acuracia_global_verdadeira": oa_verdade,
    "theta_eucalipto_no_estrato": {"todos": theta_todos, "puros": theta_puros},
    "so_pixels_puros": {
        "area_media_km2": float(area_puros.mean()),
        "vies_area_pct": float(100 * (area_puros.mean() - area_verdade) / area_verdade),
        "acuracia_media": float(oa_puros.mean()),
        "vies_acuracia_p_p": float(100 * (oa_puros.mean() - oa_verdade)),
        "cobertura_ic95_area_pct": float(100 * cob_puros),
    },
    "todo_o_estrato": {
        "area_media_km2": float(area_todos.mean()),
        "vies_area_pct": float(100 * (area_todos.mean() - area_verdade) / area_verdade),
        "acuracia_media": float(oa_todos.mean()),
        "vies_acuracia_p_p": float(100 * (oa_todos.mean() - oa_verdade)),
        "cobertura_ic95_area_pct": float(100 * cob_todos),
    },
    "repeticoes": 200,
    "veredito": "ok" if abs(100 * (area_todos.mean() - area_verdade) / area_verdade) < 5
                  and abs(100 * (oa_todos.mean() - oa_verdade)) < 2 else "suspeito",
}
assert resultado["filtro_de_borda"]["veredito"] == "ok", "o sorteio sem filtro ficou enviesado"

# ------------------------------------------------- 4. mapa perfeito = area crua
print("\n[4/4] caso degenerado: mapa 100% certo")
estrato = np.concatenate([[i] * 20 for i in range(len(areas))])
referencia = np.concatenate([[1] * 20 if mapa_e_alvo[i] else [0] * 20 for i in range(len(areas))])
r = olofsson.estimar(estrato, referencia, areas, mapa_e_alvo)
print(f"  area ajustada {r['areas']['alvo']['area_estimada_km2']:.1f} km2 | "
      f"area crua {r['area_bruta_mapa_km2']:.1f} km2")
print(f"  acuracia global {r['acuracia_global']:.3f} | UA {r['acuracia_usuario']['alvo']['valor']:.3f} "
      f"| PA {r['acuracia_produtor']['alvo']['valor']:.3f}")
resultado["mapa_perfeito"] = {
    "area_ajustada_km2": r["areas"]["alvo"]["area_estimada_km2"],
    "area_crua_km2": r["area_bruta_mapa_km2"],
    "acuracia_global": r["acuracia_global"],
}
assert abs(r["areas"]["alvo"]["area_estimada_km2"] - r["area_bruta_mapa_km2"]) < 1e-6
assert abs(r["acuracia_global"] - 1.0) < 1e-9

resultado["veredito_geral"] = "todos os controles passaram"
c.salvar_json(resultado, "controle.json")
print("\ntodos os controles passaram; salvo dados/controle.json")
