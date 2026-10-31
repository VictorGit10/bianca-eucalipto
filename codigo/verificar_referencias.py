"""
Passo extra - conferir as referencias do REFERENCIAS.md no Crossref.

Nenhuma referencia deve entrar no trabalho sem esta conferencia: o DOI tem que
existir em https://api.crossref.org/works/<doi> e o titulo tem que bater com o
titulo citado no arquivo.

Uso:
    python codigo/verificar_referencias.py

Saida: lista no terminal + dados/referencias_conferidas.json
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata

import requests

import common as c

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ARQUIVO = c.RAIZ / "REFERENCIAS.md"
PALAVRAS_IGNORADAS = {
    "de", "da", "do", "das", "dos", "e", "a", "o", "as", "os", "em", "para",
    "com", "the", "of", "and", "in", "on", "for", "with", "to",
}


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"[^a-zA-Z0-9 ]", " ", texto)
    return re.sub(r"\s+", " ", texto.lower()).strip()


def palavras(texto: str) -> set[str]:
    return {p for p in normalizar(texto).split() if p not in PALAVRAS_IGNORADAS and len(p) > 2}


linhas = [l for l in ARQUIVO.read_text(encoding="utf-8").splitlines() if l.strip().startswith("|")]
resultados = []
print(f"conferindo {ARQUIVO.name} no Crossref\n")

for linha in linhas:
    celulas = [x.strip() for x in linha.strip("|").split("|")]
    if len(celulas) < 4 or not celulas[0].isdigit():
        continue
    numero, citacao, doi, motivo = celulas[0], celulas[1], celulas[2], celulas[3]
    doi = re.sub(r"https?://(dx\.)?doi\.org/", "", doi)
    if not re.match(r"^10\.\d{4,9}/\S+$", doi):
        print(f"[{numero}] DOI em formato estranho: {doi}")
        resultados.append({"numero": numero, "doi": doi, "ok": False, "erro": "formato"})
        continue
    try:
        r = requests.get(f"https://api.crossref.org/works/{doi}", timeout=60)
        if r.status_code != 200:
            print(f"[{numero}] {doi} -> HTTP {r.status_code}")
            resultados.append({"numero": numero, "doi": doi, "ok": False, "erro": f"HTTP {r.status_code}"})
            continue
        msg = r.json()["message"]
    except Exception as e:  # rede instavel
        print(f"[{numero}] {doi} -> erro de rede ({type(e).__name__})")
        resultados.append({"numero": numero, "doi": doi, "ok": False, "erro": str(e)})
        continue

    titulo_crossref = msg["title"][0]
    ano = (msg.get("issued", {}).get("date-parts") or [[None]])[0][0]
    revista = (msg.get("container-title") or ["?"])[0]
    alvo, real = palavras(titulo_crossref), palavras(citacao)
    coincidencia = len(alvo & real) / max(len(alvo), 1)
    ok = coincidencia >= 0.75
    marca = "OK " if ok else "NAO"
    print(f"[{numero}] {marca} {doi} ({ano}, {revista[:40]}) - titulo confere {coincidencia:.0%}")
    print(f"      crossref: {titulo_crossref}")
    if not ok:
        print(f"      no arquivo: {citacao[:150]}")
    resultados.append({
        "numero": numero,
        "doi": doi,
        "ok": ok,
        "coincidencia_titulo": round(coincidencia, 3),
        "titulo_crossref": titulo_crossref,
        "ano": ano,
        "revista": revista,
    })

n_ok = sum(1 for r in resultados if r["ok"])
print(f"\n{n_ok} de {len(resultados)} conferidas")
c.salvar_json({"conferidas_em": "2026-10-31", "total": len(resultados),
               "ok": n_ok, "itens": resultados}, "referencias_conferidas.json")
if n_ok != len(resultados):
    sys.exit(1)
