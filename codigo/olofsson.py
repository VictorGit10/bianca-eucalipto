"""
Estimador de acuracia e de area com amostragem aleatoria estratificada
(Olofsson et al. 2014, Remote Sensing of Environment 148:42-57, Eq. 7 para a variancia da PA).

Estrutura:

  _estimar(m, areas, total, esperado, nomes)
      nucleo: q ESTRATOS do mapa x r CLASSES de referencia. `esperado[i]` diz qual
      classe de referencia o estrato i "deveria" ter (para a acuracia global e a
      do usuario). Serve tanto para o caso q x q (validacao multiclasse) quanto
      para o caso q x 2 (binario), sem colapsar as variancias.

  estimar_de_matriz(m, areas, ...)
      caso q x q; e o que o teste contra o exemplo publicado exercita.

  estimar(estrato, referencia, areas, mapa_e_alvo)
      caso binario do projeto (eucalipto x nao eucalipto), com q estratos.

Formulas (Olofsson et al. 2014, Eqs. 4 a 10):
  p_ij   = W_i * n_ij / n_i
  O      = sum_i W_i * th_i,esperado(i)
  V(O)   = sum_i W_i^2 u_i(1-u_i)/(n_i-1)
  U_j    = sum_{i em S_j} (W_i/W_S) * th_ij        (S_j = estratos rotulados j)
  V(U_j) = sum_{i em S_j} (W_i/W_S)^2 th_ij(1-th_ij)/(n_i-1)
  P_j    = sum_i c_i W_i th_ij / p_.j               (c_i = 1 se i em S_j)
  V(P_j) = sum_i (c_i - P_j)^2 W_i^2 th_ij(1-th_ij)/(n_i-1) / p_.j^2
  A_j    = A_total * p_.j
  V(A_j) = A_total^2 * sum_i W_i^2 th_ij(1-th_ij)/(n_i-1)
"""

from __future__ import annotations

import numpy as np

Z95 = 1.959964


def _estimar(m, areas, total, esperado, nomes, vazio=None):
    """Nucleo do estimador: q estratos do mapa x r classes de referencia."""
    m = np.asarray(m, dtype=float)
    areas = np.asarray(areas, dtype=float)
    q, r = m.shape
    esperado = np.asarray(esperado, dtype=int)
    total = float(total)
    W = areas / total

    n = m.sum(axis=1)
    vazio = (n == 0) if vazio is None else np.asarray(vazio, dtype=bool)
    n_seg = np.where(vazio, 1.0, n)
    theta = m / n_seg[:, None]
    usa = ~vazio

    # ------------------------------------------------------------ acuracia global
    acerto_i = theta[np.arange(q), esperado]
    OA = float(np.sum((W * acerto_i)[usa]))
    SE_OA = float(np.sqrt(np.sum(
        (W ** 2 * acerto_i * (1 - acerto_i) / np.maximum(n - 1, 1))[usa])))

    # ------------------------------------------------ acuracia do usuario (U_j)
    UA = []
    for j in range(r):
        S = (esperado == j) & usa
        if not S.any():
            UA.append((float("nan"), float("nan")))
            continue
        w = W[S] / W[S].sum()
        u = float(np.sum(w * theta[S, j]))
        var = float(np.sum(w ** 2 * theta[S, j] * (1 - theta[S, j])
                         / np.maximum(n[S] - 1, 1)))
        UA.append((u, float(np.sqrt(var))))

    # ---------------------------------------------- acuracia do produtor (P_j)
    p_j = np.array([np.sum((W * theta[:, j])[usa]) for j in range(r)])
    PA = []
    for j in range(r):
        if p_j[j] <= 0:
            PA.append((float("nan"), float("nan")))
            continue
        c = (esperado == j).astype(float)
        pa = float(np.sum((W * c * theta[:, j])[usa]) / p_j[j])
        var = np.sum(((c - pa) ** 2 * W ** 2 * theta[:, j] * (1 - theta[:, j])
                      / np.maximum(n - 1, 1))[usa])
        PA.append((pa, float(np.sqrt(var) / p_j[j])))

    # --------------------------------------------------- areas e IC95 (Eqs. 9-10)
    areas_est = []
    for j in range(r):
        a = float(total * p_j[j])
        var = np.sum((W ** 2 * theta[:, j] * (1 - theta[:, j])
                      / np.maximum(n - 1, 1))[usa])
        se = float(total * np.sqrt(var))
        areas_est.append({
            "area_estimada_km2": a,
            "se_km2": se,
            "ic95_km2": [a - Z95 * se, a + Z95 * se],
        })

    return {
        "n_total": int(n.sum()),
        "n_por_estrato": n.astype(int).tolist(),
        "estratos_vazios": [int(i) for i in np.nonzero(vazio)[0]],
        "W": W.tolist(),
        "matriz": m.tolist(),
        "p_ij": (m / n_seg[:, None] * W[:, None]).tolist(),
        "proporcao_area_ref": p_j.tolist(),
        "acuracia_global": OA,
        "se_acuracia_global": SE_OA,
        "acuracia_usuario": {nomes[j]: {"valor": UA[j][0], "se": UA[j][1]}
                             for j in range(r)},
        "acuracia_produtor": {nomes[j]: {"valor": PA[j][0], "se": PA[j][1]}
                              for j in range(r)},
        "areas": {nomes[j]: areas_est[j] for j in range(r)},
        "area_total_km2": total,
        "acerto_por_estrato": acerto_i.tolist(),
    }


def estimar_de_matriz(m, areas, area_total=None, nomes=None, permitir_vazios=False):
    """Caso q x q (validacao multiclasse).

    `areas` e a area de cada estrato do mapa; `area_total` permite manter a base de
    area quando algum estrato ficou sem pontos. Com `permitir_vazios=True`, estratos
    sem ponto entram com zero e nao quebram a conta.
    """
    m = np.asarray(m, dtype=float)
    if m.ndim != 2 or m.shape[0] != m.shape[1]:
        raise ValueError("a matriz de contagens precisa ser quadrada (q x q)")
    q = m.shape[0]
    areas = np.asarray(areas, dtype=float)
    if len(areas) != q:
        raise ValueError("areas precisa ter q elementos")
    total = float(area_total) if area_total is not None else float(areas.sum())
    nomes = nomes or [f"classe {k}" for k in range(q)]
    n = m.sum(axis=1)
    if (n == 0).any() and not permitir_vazios:
        raise ValueError(
            "estrato sem nenhum ponto: " + str([int(i) for i in np.nonzero(n == 0)[0]])
        )
    return _estimar(m, areas, total, np.arange(q), nomes)


def estimar(estrato, referencia, areas_km2, mapa_e_alvo, area_total=None,
            permitir_vazios=False):
    """Caso binario: a classe alvo (1) contra o resto (0).

    `areas_km2` e a area de CADA estrato do mapa (q pode ser maior que 2, porque o
    mapa pode ter varias classes que ele chama de "nao alvo"). As variancias somam
    pelos q estratos - agrupar antes de calcular mudaria a conta.
    """
    estrato = np.asarray(estrato, dtype=int)
    referencia = np.asarray(referencia, dtype=int)
    areas_km2 = np.asarray(areas_km2, dtype=float)
    alvo = np.asarray(mapa_e_alvo, dtype=bool)
    q = len(areas_km2)

    n = np.bincount(estrato, minlength=q).astype(float)
    vazio = n == 0
    if vazio.any() and not permitir_vazios:
        raise ValueError(
            "estrato sem nenhum ponto: " + str([int(i) for i in np.nonzero(vazio)[0]])
        )
    m = np.zeros((q, 2), dtype=float)
    np.add.at(m, (estrato, referencia), 1.0)
    total = float(area_total) if area_total is not None else float(areas_km2.sum())

    r = _estimar(m, areas_km2, total, np.where(alvo, 1, 0), ["nao_alvo", "alvo"],
                 vazio=vazio)
    r["matriz_por_estrato"] = m.tolist()
    r["area_bruta_mapa_km2"] = float(areas_km2[alvo].sum()) if alvo.any() else 0.0
    return r
