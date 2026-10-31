"""
Passo 08 - juntar os numeros do trabalho num lugar so.

Le os arquivos gerados pelos passos 01 a 07, confere que as entregas existem e
imprime a tabela que sustenta o RELATORIO.md. Todo numero citado no relatorio
sai daqui.

Uso:
    python codigo/08_resumo.py
"""

from __future__ import annotations

import csv
import sys

import common as c

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

rec = c.recorte()
curva = c.ler_json("curva_resumo.json")
mapa = c.ler_json("mapa_meta.json")
desenho = c.ler_json("desenho_validacao.json")
acuracia = c.ler_json("acuracia_resultado.json")
controle = c.ler_json("controle.json")

arquivos = {
    "mosaico_s2.tif": c.DADOS / "mosaico_s2.tif",
    "rotulos_mb.tif": c.DADOS / "rotulos_mb.tif",
    "rgb_10m.tif": c.DADOS / "rgb_10m.tif",
}
baixado_mb = sum(p.stat().st_size for p in arquivos.values() if p.exists()) / 1e6

silv_mb = next(d for d in rec["composicao"] if d["codigo"] == 9)


def linha(rotulo, valor, fonte):
    print(f"{rotulo:<46s} {str(valor):>14s}   ({fonte})")


print("=" * 92)
print("AREA DE TESTE - dados/recorte.json (codigo/01_escolher_area.py)")
print("=" * 92)
linha("municipio escolhido", rec["municipio"], "01")
linha("centro do recorte (lon)", f"{rec['centro'][0]:.3f}", "01")
linha("centro do recorte (lat)", f"{rec['centro'][1]:.3f}", "01")
linha("area de silvicultura no municipio (km2)", f"{rec['silvicultura_municipio_km2']:.1f}", "01")
linha("recorte (km2)", f"{rec['area_km2']:.1f}", "01")
linha("silvicultura dentro do recorte (%)", f"{silv_mb['pct']:.2f}", "01")
linha("silvicultura dentro do recorte (km2)", f"{silv_mb['area_km2']:.1f}", "01")
print("  composicao do recorte (MapBiomas 2024, pixels de 30 m):")
for d in rec["composicao"][:7]:
    linha(f"    {d['classe']}", f"{d['pct']:.2f}% / {d['area_km2']:.1f} km2", "01")
print("  cinco municipios com mais silvicultura em Goias:")
_mun = sorted((d for d in csv.DictReader((c.DADOS / "silvicultura_por_municipio.csv").open(encoding="utf-8"))),
              key=lambda d: -float(d["area_silvicultura_km2"]))[:5]
for d in _mun:
    linha(f"    {d['municipio']}", f"{float(d['area_silvicultura_km2']):.1f} km2", "01")

print("\n" + "=" * 92)
print("IMAGEM - dados/mosaico_meta.json (codigo/02_baixar_imagens.py)")
print("=" * 92)
meta_img = c.ler_json("mosaico_meta.json")
linha("cenas Sentinel-2 na seca", meta_img["n_cenas_seca"], "02")
linha("cenas Sentinel-2 na chuva", meta_img["n_cenas_chuva"], "02")
linha("bandas no mosaico", len(meta_img["bandas"]), "02")
linha("pixels da grade", f"{meta_img['grade'][0]}x{meta_img['grade'][1]}", "02")
linha("tamanho dos arquivos no disco (MB)", f"{baixado_mb:.1f}", "02")

print("\n" + "=" * 92)
print("CURVA DE APRENDIZADO - dados/curva_resumo.json (codigo/03_curva_aprendizado.py)")
print("=" * 92)
linha("pixels validos", f"{sum(curva['pixels_por_classe'].values()):,}", "03")
for nome, n in curva["pixels_por_classe"].items():
    linha(f"  pixels de {nome}", f"{n:,}", "03")
linha("pixels no teste aleatorio", f"{curva['n_teste_aleatorio']:,}", "03")
linha("pixels no teste por blocos", f"{curva['n_teste_blocos']:,}", "03")
linha("blocos de 2 km no teste", f"{curva['blocos_2km_teste']}/{curva['blocos_2km_total']}", "03")
print("  N      F1 aleatorio   F1 blocos   acc aleatorio   acc blocos")
for i, n in enumerate(curva["ns"]):
    print(f"  {n:<5d}  {curva['aleatorio']['f1_eucalipto_media'][i]:>11.3f}"
          f"   {curva['blocos']['f1_eucalipto_media'][i]:>8.3f}"
          f"   {curva['aleatorio']['acuracia_global_media'][i]:>12.3f}"
          f"   {curva['blocos']['acuracia_global_media'][i]:>9.3f}")
for p in ("aleatorio", "blocos"):
    est = curva[p]["n_estabiliza_f1"]
    linha(f"estabiliza (F1) - {p}", "nao estabilizou" if est is None else est, "03")
linha("ganho de F1 por dobrada (aleatorio)",
      " ".join(f"{g:+.3f}" for g in curva["aleatorio"]["ganhos_por_dobrada"]), "03")
linha("dp do F1: N=25 -> N=3200 (aleatorio)",
      f"{curva['aleatorio']['f1_eucalipto_dp'][0]:.3f} -> {curva['aleatorio']['f1_eucalipto_dp'][-1]:.3f}", "03")
linha("F1 aos 3200: aleatorio - blocos",
      f"{curva['aleatorio']['f1_eucalipto_media'][-1] - curva['blocos']['f1_eucalipto_media'][-1]:+.3f}", "03")

print("\n" + "=" * 92)
print("MAPA - dados/mapa_meta.json (codigo/04_mapa.py)")
print("=" * 92)
linha("amostras de treino", f"{mapa['n_treino']:,}", "04")
linha("amostras por classe no mapa", mapa["n_por_classe"], "04")
for nome, v in mapa["area_por_classe_mapa_km2"].items():
    linha(f"  area de {nome} (km2, contagem de pixels)", f"{v:.1f}", "04")
linha("concordancia com o MapBiomas", f"{mapa['concordancia_com_mapbiomas']:.3f}", "04")

print("\n" + "=" * 92)
print("DESENHO DE VALIDACAO - dados/desenho_validacao.json (codigo/05_desenho_validacao.py)")
print("=" * 92)
linha("erro padrao alvo escolhido", desenho["se_alvo"], "05")
linha("margem de erro de 95% na acuracia global (p.p.)",
      f"+-{1.96*desenho['se_alvo']*100:.1f}", "05")
for se, n in desenho["n_por_erro_padrao"].items():
    linha(f"  n para SE={se}", n, "05")
print("  prior de acuracia do usuario por estrato (concordancia com MapBiomas):")
for nome, u in desenho["ua_prior"].items():
    linha(f"    {nome}", f"{u:.3f}", "05")
linha("pontos sorteados", desenho["n_pontos"], "05")
for nome, n in desenho["alocacao"].items():
    linha(f"  pontos no estrato {nome}", n, "05")
linha("pontos em pixel de borda do mapa",
      f"{desenho['pontos_em_borda']} ({desenho['pct_pontos_em_borda']}%)", "05")
linha("pixels com vizinhanca 3x3 pura (diagnostico)",
      f"{desenho['pixels_puros_3x3']:,}", "05")
linha("amostragem", desenho["amostragem"][:40] + "...", "05")

print("\n" + "=" * 92)
print("EXEMPLO FICTICIO - dados/acuracia_resultado.json (codigo/06_acuracia.py)")
print("(numeros de TESTE do script, NAO sao a acuracia do mapa; acuracia BINARIA)")
print("=" * 92)
for rotulo, chave_res in (("nao sei excluido", "resultado"),
                          ("nao sei = nao eucalipto", "resultado_nao_sei_como_erro")):
    r = acuracia[chave_res]
    print(f"  -- politica: {rotulo}")
    print(f"     tipo de acuracia: {acuracia.get('tipo_acuracia', 'binaria')}")
    linha("     n usado", r["n_total"], "06")
    linha("     acuracia global", f"{r['acuracia_global']:.3f} +- {1.96*r['se_acuracia_global']:.3f}", "06")
    linha("     acuracia do usuario (alvo)", f"{r['acuracia_usuario']['alvo']['valor']:.3f}", "06")
    linha("     SE da acuracia do usuario (alvo)", f"{r['acuracia_usuario']['alvo']['se']:.3f}", "06")
    linha("     acuracia do usuario (nao_alvo)", f"{r['acuracia_usuario']['nao_alvo']['valor']:.3f}", "06")
    linha("     acuracia do produtor (alvo)", f"{r['acuracia_produtor']['alvo']['valor']:.3f}", "06")
    linha("     SE da acuracia do produtor (alvo)", f"{r['acuracia_produtor']['alvo']['se']:.3f}", "06")
    linha("     acuracia do produtor (nao_alvo)", f"{r['acuracia_produtor']['nao_alvo']['valor']:.3f}", "06")
    linha("     SE da acuracia do produtor (nao_alvo)", f"{r['acuracia_produtor']['nao_alvo']['se']:.3f}", "06")
    linha("     area de eucalipto no mapa (km2)", f"{r['area_bruta_mapa_km2']:.1f}", "06")
    linha("     area ajustada de eucalipto (km2)", f"{r['areas']['alvo']['area_estimada_km2']:.1f}", "06")
    linha("     SE da area ajustada (km2)", f"{r['areas']['alvo']['se_km2']:.1f}", "06")
    linha("     IC95 da area ajustada (km2)",
          f"{r['areas']['alvo']['ic95_km2'][0]:.1f} a {r['areas']['alvo']['ic95_km2'][1]:.1f}", "06")

print("\n" + "=" * 92)
print("TESTE DO ESTIMADOR - dados/teste_olofsson.json (codigo/test_olofsson.py)")
print("(reproduz o exemplo publicado do Olofsson et al. 2014, Tabelas 6 a 9)")
print("=" * 92)
try:
    teste = c.ler_json("teste_olofsson.json")
    linha("falhas no teste", len(teste["falhas"]), "teste")
    linha("SE da area 1 - artigo 3.138 ha", f"{teste['resultados']['tabela7']['se_area_1_ha']:.0f}", "teste")
    linha("SE da area 3 - artigo 9.270 ha", f"{teste['resultados']['tabela7']['se_area_3_ha']:.0f}", "teste")
    linha("SE da acuracia global - artigo 0,011", f"{teste['resultados']['tabela7']['se_acuracia_global']:.4f}", "teste")
except FileNotFoundError:
    print("  (rode python codigo/test_olofsson.py)")

print("\n" + "=" * 92)
print("PLANO PARA GOIAS - dados/plano_goias.json (codigo/09_plano_goias.py)")
print("=" * 92)
plano = c.ler_json("plano_goias.json")
linha("silvicultura somada nos municipios (km2)", f"{plano['silvicultura_goias_km2']:.0f}", "09")
linha("area de Goias na grade de 1 km (km2)", f"{plano['area_goias_km2']:.0f}", "09")
linha("eucalipto no estado (km2, 1 km)", f"{plano['areas_por_grupo_km2']['eucalipto']:.0f}", "09")
linha("eucalipto no estado (% da area)", f"{100*plano['W']['eucalipto']:.2f}", "09")
for se, n in plano["n_por_se"].items():
    linha(f"n de validacao para o estado (SE={se})", n, "09")
linha("n com piso de 100 no eucalipto", plano["n_total_com_piso"], "09")
linha("SE previsto com esse piso", f"{plano['se_previsto_com_piso']:.3f}", "09")
for r in plano["regioes_sugeridas"]:
    linha(f"  regiao {r['municipio']} (km2)", f"{r['silvicultura_km2']:.1f}", "09")

print("\n" + "=" * 92)
print("CONTROLES - dados/controle.json (codigo/07_controle.py)")
print("=" * 92)
k = controle["classificador"]
linha("acuracia do modelo", f"{k['acuracia_modelo']:.3f}", "07")
linha("acuracia com rotulos embaralhados", f"{k['acuracia_rotulos_embaralhados']:.3f}", "07")
linha("acuracia da regra boba", f"{k['acuracia_regra_boba']:.3f}", "07")
e = controle["estimador"]
linha("verdade simulada (km2)", f"{e['verdade_km2']:.1f}", "07")
linha("media estimada (km2)", f"{e['media_estimada_km2']:.1f}", "07")
linha("vies do estimador (%)", f"{e['vies_pct']:+.2f}", "07")
linha("cobertura do IC95 (%)", f"{e['cobertura_ic95_pct']:.1f}", "07")
linha("area sem correcao nessa simulacao (km2)", f"{e['area_sem_correcao_km2']:.1f}", "07")
linha("erro da area sem correcao (%)", f"{e['erro_da_area_sem_correcao_pct']:+.1f}", "07")
fb = controle["filtro_de_borda"]
linha("--- filtro de borda no sorteio (paisagem sintetica)", "", "07")
linha("verdade simulada de eucalipto (km2)", f"{fb['verdade_km2']:.1f}", "07")
linha("acuracia global verdadeira do mapa sintetico", f"{fb['acuracia_global_verdadeira']:.3f}", "07")
linha("fracao eucalipto no estrato (todos os pixels)",
      f"{fb['theta_eucalipto_no_estrato']['todos']:.3f}", "07")
linha("fracao eucalipto no estrato (so pixels puros)",
      f"{fb['theta_eucalipto_no_estrato']['puros']:.3f}", "07")
for nome, ch in (("so pixels puros", "so_pixels_puros"), ("todo o estrato", "todo_o_estrato")):
    d = fb[ch]
    linha(f"  {nome}: area media (km2)", f"{d['area_media_km2']:.1f}", "07")
    linha(f"  {nome}: vies da area (%)", f"{d['vies_area_pct']:+.1f}", "07")
    linha(f"  {nome}: acuracia media", f"{d['acuracia_media']:.3f}", "07")
    linha(f"  {nome}: vies da acuracia (p.p.)", f"{d['vies_acuracia_p_p']:+.1f}", "07")
    linha(f"  {nome}: IC95 da area cobre a verdade (%)", f"{d['cobertura_ic95_area_pct']:.0f}", "07")

print("\n" + "=" * 92)
print("ENTREGAS")
print("=" * 92)
entregas = [
    c.RAIZ / "RELATORIO.md",
    c.RAIZ / "README.md",
    c.RAIZ / "CLAUDE.md",
    c.RAIZ / "AGENTS.md",
    c.RAIZ / "REFERENCIAS.md",
    c.FIGURAS / "curva_aprendizado.png",
    c.FIGURAS / "mapa_area.png",
    c.FIGURAS / "matriz_confusao.png",
    c.CONFERENCIA / "index.html",
    c.CONFERENCIA / "pontos.csv",
    c.CONFERENCIA / "marcacoes_FICTICIO.csv",
    c.CONFERENCIA / "marcacoes_FICTICIO_estrato_vazio.csv",
    c.CHAVE / "pontos_chave.csv",
]
for p in entregas:
    estado = "ok" if p.exists() else "FALTA"
    tamanho = f"{p.stat().st_size/1e6:.1f} MB" if p.exists() else ""
    print(f"  [{estado:>5s}] {p.relative_to(c.RAIZ)} {tamanho}")

c.salvar_json(
    {
        "area_km2": rec["area_km2"],
        "silvicultura_recorte_pct": silv_mb["pct"],
        "cenas_seca": meta_img["n_cenas_seca"],
        "cenas_chuva": meta_img["n_cenas_chuva"],
        "bandas": len(meta_img["bandas"]),
        "baixado_mb": round(baixado_mb, 1),
        "curva": {p: curva[p]["f1_eucalipto_media"] for p in ("aleatorio", "blocos")},
        "areas_mapa_km2": mapa["area_por_classe_mapa_km2"],
        "concordancia_mapbiomas": mapa["concordancia_com_mapbiomas"],
        "pontos_validacao": desenho["n_pontos"],
        "pontos_em_borda": desenho["pontos_em_borda"],
        "pct_pontos_em_borda": desenho["pct_pontos_em_borda"],
        "exemplo_ficticio": {
            "acuracia_global": acuracia["resultado"]["acuracia_global"],
            "area_ajustada_km2": acuracia["resultado"]["areas"]["alvo"]["area_estimada_km2"],
            "acuracia_global_nao_sei_como_erro":
                acuracia["resultado_nao_sei_como_erro"]["acuracia_global"],
            "area_ajustada_nao_sei_como_erro_km2":
                acuracia["resultado_nao_sei_como_erro"]["areas"]["alvo"]["area_estimada_km2"],
        },
        "controles": {"classificador": k, "estimador": e, "filtro_de_borda": fb},
    },
    "resumo_final.json",
)
print("\nsalvo dados/resumo_final.json")
