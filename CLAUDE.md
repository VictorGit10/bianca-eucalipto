# CLAUDE.md — contexto técnico para a IA da pesquisadora

Este arquivo é para um assistente de IA que for continuar o trabalho. Leia antes de mexer em qualquer coisa.
O `AGENTS.md` aponta para cá. O `README.md` é a versão para gente; o `RELATORIO.md` tem os resultados.

## O que este projeto é

Um teste executado (não um plano) de duas perguntas de um trabalho de mestrado/doutorado sobre plantios de
eucalipto em Goiás: **quantas amostras de treino** usar no Random Forest e **como validar o mapa**.
Recorte de 381 km² em Rio Verde (GO), Sentinel-2 2024, MapBiomas Coleção 11 como rótulo provisório.

## Ambiente

- Windows, Python 3.14 (ambiente do usuário; não há caminho fixo, use `python` do PATH).
- Earth Engine já autenticado: `ee.Initialize(project='SEU-PROJETO-EARTH-ENGINE')`. **Nunca** criar conta,
  pedir chave ou usar credencial nova.
- Pacotes usados: `earthengine-api`, `numpy`, `pandas`, `scikit-learn`, `matplotlib`, `rasterio`, `scipy`,
  `pillow`, `pyproj`, `requests`.
- Rodar tudo a partir da raiz do projeto (os scripts fazem `import common`, então precisam de `codigo/` no path —
  na prática, `python codigo/NN_script.py` funciona porque o Python coloca a pasta do script no `sys.path`).

## Ordem dos scripts e dependências

```
01_escolher_area.py   -> dados/recorte.json, dados/silvicultura_por_municipio.csv, dados/composicao_recorte.csv
02_baixar_imagens.py  -> dados/mosaico_s2.tif, dados/rotulos_mb.tif, dados/rgb_10m.tif, dados/mosaico_meta.json
03_curva_aprendizado.py -> dados/curva_aprendizado.csv, dados/curva_resumo.json, figuras/curva_aprendizado.png
04_mapa.py            -> dados/mapa_predito.tif, dados/mapa_meta.json, figuras/mapa_area.png
05_desenho_validacao.py -> conferencia/index.html (cega, com marcador do pixel),
                           conferencia/pontos.csv (id, lon, lat),
                           conferencia/marcacoes_FICTICIO*.csv, dados/chave/pontos_chave.csv,
                           dados/desenho_validacao.json
06_acuracia.py        -> dados/acuracia_resultado.json, figuras/matriz_confusao.png
07_controle.py        -> dados/controle.json
08_resumo.py          -> imprime e salva dados/resumo_final.json (fonte dos números do relatório)
09_plano_goias.py     -> dados/plano_goias.json (plano para o mapa estadual)
test_olofsson.py      -> dados/teste_olofsson.json (teste contra o exemplo publicado; exit code 1 se falhar)
verificar_referencias.py -> dados/referencias_conferidas.json
```

Dependências: 03, 04 e 07 precisam do `mosaico_s2.tif` e do `rotulos_mb.tif` (passo 02). 05 precisa de
`mapa_predito.tif` e `rgb_10m.tif`. 06 precisa de `desenho_validacao.json`, de `dados/chave/pontos_chave.csv`
(a chave `id` → estrato/classe) e de um CSV de marcações — o CSV **não** traz a classe do mapa, de propósito.
07 precisa de `desenho_validacao.json`. `test_olofsson.py` não depende de nenhum dado do projeto (usa as
tabelas do artigo); `09_plano_goias.py` precisa de `silvicultura_por_municipio.csv` e consulta o Earth Engine.

## Estrutura do código

- `codigo/common.py` — constantes e utilidades. **É aqui que se mexe para mudar o desenho:**
  - `GRUPOS`: agrupamento das classes MapBiomas em 5 grupos (eucalipto, floresta, pastagem, agricultura,
    mosaico_agua). Mudar isso muda tudo a jusante.
  - `CLASSES` (ordem fixa), `CLASSE_ALVO`, `CORES`.
  - `SECA` / `CHUVA` (datas), `ESCALA` (20 m), `CRS_LOCAL` (EPSG:32722), `BANDAS`.
  - `carregar_bandas()`: devolve `X (pixels × bandas)`, `y` (índice do grupo, −1 inválido), `valido`, `forma`.
  - `esticar_rgb()`: alongamento 2–98% para figura (a reflectância da seca é escura).
- `codigo/olofsson.py` — estimador de acurácia e área (estratificado). Duas funções:
  - `estimar_de_matriz(m, areas)` — caso geral q × q (é o que o teste publicado exercita);
  - `estimar(estrato, referencia, areas, mapa_e_alvo)` — caso binário do projeto (eucalipto × não eucalipto).
  **Convenção: `referencia=1` é a classe alvo.** `matriz[i]` = `[n_nao_alvo, n_alvo]` por estrato do mapa.
  As variâncias somam **pelos q estratos** (não colapse a matriz antes de calcular: as fórmulas de OA, PA e
  área são somas por estrato e mudam se você agrupar). `permitir_vazios=True` aceita estrato sem ponto.
  Usado por 06 e 07.
- `codigo/test_olofsson.py` — reproduz as Tabelas 6–9 do Olofsson et al. (2014). **Rode antes de mexer nas
  fórmulas**; se ele falhar, o estimador está errado.
- As imagens em `dados/` são GeoTIFF em EPSG:32722, 20 m (o RGB é 10 m). Bandas do mosaico em **DN 0–10000**
  (não divididas por 10000); os índices já são adimensionais.

## Armadilhas encontradas (não repita)

1. **Asset do MapBiomas:** `.../lulc/collection11/mapbiomas_collection11_integration_v1` **não existe**.
   O mapa anual está em `projects/mapbiomas-public/assets/brazil/lulc/v1/collection_11_2024_v1`
   (ImageCollection com 121 imagens, filtro por `system:index`).
2. **Cloud Score+:** `linkCollection(cs, ['cs','cs_cdf'])` — o segundo argumento são **bandas**, não
   `['system:index']`. Máscara usada: `cs_cdf >= 0.6`.
3. **`geometry.bounds()`** devolve a caixa em EPSG:4326 mesmo depois de `transform()`. Para a grade UTM,
   calcule mín/máx a partir de `coordinates()`.
4. **`resample('nearest')` não existe no EE** (`Invalid interpolation mode`). O padrão do `reproject` já é
   vizinho mais próximo para imagens inteiras.
5. **`getDownloadURL` tem limite de 32 MB por requisição.** O `02` baixa em blocos 3×3 (19 bandas) e remonta
   com `rasterio`. Se mudar a área, aumente `nx/ny`.
6. **Grade dos rótulos:** use a mesma grade do mosaico (mesmo `nx/ny`), senão o `assert` de forma quebra.
7. **Vazamento treino/teste:** no `07`, o sorteio de treino precisa excluir os índices do teste. Sem isso, o
   controle com rótulos embaralhados dá ~0,48 em vez de ~0,19 — foi assim que o bug apareceu.
8. **Console do Windows (cp1252):** imprimir títulos do Crossref com hífen tipográfico quebra o script.
   Os scripts que falam com o Crossref fazem `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`.
9. **Nunca reintroduzir filtro de borda no sorteio da validação.** A primeira versão do `05` só sorteava pixels
   com vizinhança 3 × 3 "pura" e isso foi corrigido em 31/10: dá probabilidade zero aos pixels onde o mapa mais
   erra, a amostra deixa de ser probabilística e o IC95 da área passa a cobrir a verdade em 0% das simulações
   (controle em `07_controle.py`, seção "filtro_de_borda" em `dados/controle.json`). O ponto de borda se resolve
   com "não dá para saber" e com a regra de rotulagem (maior parte do pixel de 20 m).
10. **A página e o `conferencia/pontos.csv` têm que continuar cegos.** Só `id`, `lon`, `lat` (e imagens, no HTML).
    A classe do mapa vive em `dados/chave/pontos_chave.csv`. Teste: `grep -c -iE "classe_mapa|\bestrato\b"
    conferencia/index.html` tem que devolver 0, e o array `PONTOS` só pode ter `id`, `lon`, `lat`, `img_det`,
    `img_ctx`. Os ids são embaralhados para a ordem não revelar o estrato.

## O que NÃO se pode afirmar com este material

- **Não existe acurácia real do mapa.** Os rótulos de treino e o CSV de exemplo vêm do MapBiomas.
  O `marcacoes_FICTICIO.csv` tem `ficticio=SIM` — se algum número dele vazar para um texto como se fosse
  resultado, o trabalho está errado.
- **Concordância com o MapBiomas (0,763) não é acurácia.**
- **A curva não estabilizou** até 3.200 amostras por classe. Não escreva "o ideal é 800".
- **A área ajustada do exemplo fictício (60,3 km², política padrão) não é a área de eucalipto do mapa.**
  A do mapa é 41,4 km² (contagem de pixels, sem correção). A acurácia global fictícia é 0,852, não 0,900:
  os números antigos vinham da versão com filtro de borda, corrigida em 31/10.
- **Os 44 pontos de borda não são defeito da amostra.** São 40,7% dos 108 e fazem parte do desenho probabilístico;
  se algum dia "sumirem" da amostra, é sinal de que o filtro de borda voltou.
- **A acurácia global do `06` é binária** (eucalipto × não eucalipto) e não é comparável com a acurácia de
  5 classes da curva (passo 03, 0,78 no maior N). Não escreva "o mapa tem 85% e a curva 78%, então...".
- **O mapa tem uma cor por classe** (`BoundaryNorm`). Se alguém voltar a `vmin/vmax` com `ListedColormap`, as
  classes trocam de cor e a figura passa a mentir — confira a legenda antes de publicar.

## Convenções

- Tudo em português, sem acento nos nomes de arquivo e de variável (o console do Windows não ajuda).
- Números só entram em texto se saírem de `08_resumo.py` ou de um JSON em `dados/`.
- Toda referência precisa passar em `verificar_referencias.py` (DOI + título no Crossref).
- Figuras: 150–160 dpi, sem título gigante, legenda em português, `bbox_inches='tight'`.

## Se for continuar

1. Marcar os 108 pontos e rodar `06` — é o único caminho para uma acurácia de verdade.
2. Se precisar de mais precisão: `05 --se 0.03` (191 pontos) ou `--se 0.02` (430).
3. Se for mudar o agrupamento de classes, refaça 03→07 em ordem; todos dependem de `common.GRUPOS`.
4. Se for usar outro município, apague `dados/silvicultura_por_municipio.csv` ou rode `01 --forcar`.
5. Para o estado: leia a seção 14 do `RELATORIO.md` e `dados/plano_goias.json` (gerado pelo `09`). O caminho é
   repetir a curva em 3 regiões antes de treinar o mapa estadual — não pule essa etapa.
6. Se mexer em `olofsson.py`, rode `test_olofsson.py` antes e depois.
