# Relatório — quantas amostras para o Random Forest e como saber se o mapa de eucalipto está bom

**Pedido:** a pesquisadora já usa Random Forest para mapear eucalipto em Goiás e tem duas dúvidas:
quantas amostras de treino usar e como conferir se a classificação está satisfatória.

**O que foi feito:** um teste completo, rodado de ponta a ponta, num recorte de 381 km² em Rio Verde (GO):
mosaico Sentinel-2 de 2024 (seca e chuva) → amostras rotuladas pelo MapBiomas (referência provisória) →
curva de aprendizado com 8 tamanhos de amostra × 5 repetições × 2 formas de separar treino e teste →
mapa final → desenho de validação por amostragem estratificada (Olofsson) com 108 pontos →
página HTML offline para marcar os pontos → script que calcula acurácias e área ajustada com intervalo de confiança.

**Os três achados que importam:**

1. **Não existe "número ideal" de amostras.** Neste recorte, o F1 do eucalipto subiu de 0,40 (25 amostras/classe)
   para 0,69 (3.200/classe) e **ainda estava subindo** no maior valor testado. O que existe é uma curva: cada
   dobrada de amostras rendeu entre +0,01 e +0,09 de F1, e o ganho por dobrada foi encolhendo até +0,03.
   Quem decide onde parar é o custo de coletar amostra, não a IA.
2. **Treinar e testar com pixels vizinhos infla o resultado.** Com separação por blocos de 2 km, o F1 aos 3.200
   amostras cai de 0,691 para 0,607. A diferença (0,08) é o "otimismo" que a validação aleatória esconde.
3. **Acurácia global alta pode esconder o erro que importa.** No exemplo de teste (fictício), o mapa tem 85% de
   acurácia global, mas só 37% de acurácia do produtor para eucalipto — ou seja, a maior parte do eucalipto que
   existe não foi mapeada, e a área crua (41 km²) subestima a ajustada (60 km²). Um número só não responde à pergunta.

---

## 1. Área de teste

Escolhida por dado, não por opinião (`codigo/01_escolher_area.py`, saída em `dados/recorte.json`):

- Somei a área da classe 9 (silvicultura) do MapBiomas Coleção 11 (2024) nos 242 municípios de Goiás.
- **Rio Verde** tem a maior área: **129,3 km²** de silvicultura (seguido por Niquelândia 99,2 e Catalão 96,9).
- Dentro de Rio Verde, procurei a janela de 18 × 18 km com maior densidade de silvicultura
  (convolução com kernel quadrado) → centro **-51,170, -18,001**.
- Recorte final: 0,18° × 0,18° = **381,0 km²**, grade de 954 × 999 pixels a 20 m em UTM 22S.

Composição do recorte (MapBiomas 2024, pixels nativos de 30 m):

| Classe | % | km² |
|---|---|---|
| Pastagem | 31,0 | 124,5 |
| Soja | 26,0 | 104,3 |
| Formação Florestal | 16,9 | 67,9 |
| Mosaico de Usos | 9,6 | 38,4 |
| **Silvicultura** | **9,1** | **36,4** |
| Campo Alagado | 4,0 | 15,9 |
| Rio/Lago | 1,0 | 3,9 |

A escolha é boa para o teste porque **tem a classe alvo em quantidade e tem confusão de verdade**:
eucalipto vs. floresta nativa vs. soja vs. pastagem. Um recorte só de eucalipto daria 99% de acurácia e não
ensinaria nada.

## 2. Imagem

`codigo/02_baixar_imagens.py` → `dados/mosaico_s2.tif` (19 bandas, 20 m) + `dados/rgb_10m.tif` + `dados/rotulos_mb.tif`.

- Sentinel-2 SR harmonizado, **58 cenas** na seca (01/05–30/09/2024) e **48 cenas** na chuva (01/11/2024–28/02/2025).
- Máscara de nuvem: **Cloud Score+**, mantendo `cs_cdf ≥ 0,60`, antes da mediana por pixel.
- Bandas da seca: B2, B3, B4, B5, B6, B7, B8, B8A, B11, B12. Da chuva: B4, B8, B11.
- Índices: NDVI, NDWI, NDRE, NDBI (seca) e NDVI, NDWI (chuva) — calculados sobre as medianas.
- **Tamanho dos arquivos baixados no disco: 62,7 MB** (é o tamanho local dos GeoTIFF, **não o tráfego
  de rede**, que não foi medido; o limite de 1 GB é de volume). Foram ~22 requisições de download em blocos
  de 3 × 3 para não estourar o limite de 32 MB por requisição.

Escolhi mediana por estação porque nuvem residual e sombra destroem qualquer estatística de média, e porque
a sazonalidade separa pastagem de eucalipto (eucalipto mantém folha na seca; soja e pastagem secam).

## 3. Rótulos provisórios — leia antes de acreditar em qualquer número

As amostras de treino **foram sorteadas do MapBiomas**. Isso significa que:

- a "acurácia" medida nos passos 03 e 04 é **concordância com o MapBiomas**, não acurácia do mapa;
- o mapa herda os erros e a generalização do MapBiomas (que é de 30 m e mapeia silvicultura de forma conservadora);
- **concordar com o MapBiomas não é acurácia** (Stehman & Foody 2019). Só o dado de referência marcado por
  uma pessoa, com amostra probabilística, responde à pergunta da pesquisadora.

O MapBiomas aqui serve para uma coisa só: **sortear amostras e viabilizar o teste da curva de aprendizado**.
O passo 05/06 é o que produz validação de verdade — e depende das marcações da pesquisadora.

## 4. Dúvida 1 — quantas amostras? (curva de aprendizado)

`codigo/03_curva_aprendizado.py` → `dados/curva_aprendizado.csv`, `dados/curva_resumo.json`, `figuras/curva_aprendizado.png`.

Desenho: N amostras **por classe** ∈ {25, 50, 100, 200, 400, 800, 1600, 3200}, **5 repetições** por N,
teste **sempre o mesmo** dentro de cada protocolo, duas formas de separar treino e teste:

- **aleatório** — 20% dos pixels sorteados (190.609 pixels de teste);
- **blocos** — 20 dos 100 blocos de 2 × 2 km vão inteiros para teste (195.300 pixels).

| N/classe | F1 eucalipto (aleatório) | F1 eucalipto (blocos) | Acurácia global (aleatório) | Acurácia global (blocos) |
|---|---|---|---|---|
| 25 | 0,398 | 0,425 | 0,621 | 0,612 |
| 50 | 0,412 | 0,447 | 0,658 | 0,639 |
| 100 | 0,499 | 0,491 | 0,682 | 0,654 |
| 200 | 0,536 | 0,531 | 0,705 | 0,675 |
| 400 | 0,576 | 0,555 | 0,727 | 0,682 |
| 800 | 0,630 | 0,569 | 0,746 | 0,694 |
| 1600 | 0,664 | 0,592 | 0,763 | 0,703 |
| 3200 | 0,691 | 0,607 | 0,778 | 0,710 |

Ganho de F1 a cada dobrada de amostras (aleatório): +0,014 / +0,086 / +0,037 / +0,040 / +0,054 / +0,034 / +0,027.

**Como ler isso:**

- **A curva não estabilizou** até 3.200 amostras por classe. O ganho por dobrada caiu (de +0,086 para +0,027),
  mas ainda não chegou a zero. Dizer "o ideal é 800" seria inventar.
- **Onde o ganho deixa de pagar o custo:** de 400 para 800 ainda se ganha +0,054 de F1; de 800 para 1.600, +0,034;
  de 1.600 para 3.200, +0,027. Ou seja, **800 por classe compra a maior parte do que 3.200 compraria** (0,630 vs
  0,691), com um quarto do esforço de coleta. Para um trabalho com orçamento de interpretação manual, é a faixa
  com melhor retorno por amostra — e não uma regra geral.
- **O efeito espacial é real e cresce com N:** aos 25/classe os dois protocolos empatam; aos 3.200 o aleatório
  está 0,084 acima do bloco. Ou seja, parte do ganho aparente com muitas amostras é o modelo memorizando vizinhos.
- **Por que o teto é ~0,7 e não 0,95:** os rótulos vêm de 30 m suavizados e generalizados, os pixels são de 20 m,
  e há 5 classes com transições reais (borda de talhão, eucalipto jovem parecido com pastagem). Teto baixo aqui
  é informação sobre a referência, não sobre o algoritmo.

**Resposta curta para a pesquisadora:** o número depende da área, das classes e da confusão entre elas — não existe
número universal. O procedimento que responde à pergunta na *sua* área é este script: rode a curva com a sua
referência, olhe o ganho por dobrada e pare quando o ganho não pagar o custo de coletar mais amostra. No nosso
recorte, esse ponto está entre 400 e 800 por classe.

**O que muda com o tamanho da amostra (números do passo 03):** o desvio-padrão do F1 entre repetições cai de
0,021 (N=25) para 0,004 (N=3.200) no protocolo aleatório. Ou seja, pouca amostra também significa resultado
instável: repetir o sorteio muda a conclusão.

## 5. Dúvida 2 — como conferir se o mapa está satisfatório

Esta é a parte que a IA não pode fazer sozinha, e é a parte que resolve a dúvida. Foram quatro peças.

### 5.1 O mapa a conferir

`codigo/04_mapa.py` → `dados/mapa_predito.tif`, `figuras/mapa_area.png`.
Random Forest com 1.600 amostras/classe (8.000 no total, decisão justificada pela curva: ganho por dobrada já
abaixo de 0,04). Áreas do mapa:

| Classe | km² (contagem de pixels) |
|---|---|
| eucalipto | 41,4 |
| floresta | 65,7 |
| pastagem | 118,1 |
| agricultura | 100,4 |
| mosaico/água | 55,6 |

Concordância com o MapBiomas: **0,763** — e isso **não é acurácia** (ver seção 3). Serve só para ver que o mapa
não está deslocado nem invertido: os talhões de eucalipto do mapa caem sobre os talhões do MapBiomas na figura.

### 5.2 O desenho de validação (Olofsson et al. 2014)

`codigo/05_desenho_validacao.py` → `conferencia/pontos.csv`, `dados/desenho_validacao.json`.

- **Estratos = classes do mapa** (5 estratos). Cada pixel tem uma probabilidade conhecida de ser sorteado dentro
  do seu estrato — é isso que permite corrigir a área depois.
- **Tamanho da amostra calculado**, não escolhido no chute:
  n = (Σ W_h·S_h / SE)², com S_h = √(U_h(1−U_h)) e U_h estimado pela concordância com o MapBiomas
  (0,61 / 0,84 / 0,79 / 0,82 / 0,64). Resultado:

| Erro padrão alvo da acurácia global | n |
|---|---|
| 0,02 | 430 |
| 0,03 | 191 |
| **0,04** | **108** |
| 0,05 | 69 |
| 0,10 | 18 |

  Escolhi **SE = 0,04 → 108 pontos**, que é o que cabe numa sessão de interpretação e dá ±8 pontos percentuais
  de intervalo de confiança na acurácia global. Se a pesquisadora quiser ±4 p.p., são 430 pontos — o script aceita
  `--se 0.02`.
- **Alocação proporcional com piso de 10:** eucalipto 12, floresta 19, pastagem 33, agricultura 28, mosaico/água 16.
- **Amostragem uniforme em todos os pixels do estrato**, com probabilidade conhecida e não nula para cada pixel.
  **Não há filtro de borda.** Foi a correção de 31/10: a primeira versão só sorteava pixels com vizinhança
  3 × 3 "pura", o que dava probabilidade zero justamente aos pixels onde o mapa mais erra — a acurácia saía
  otimista e o intervalo de confiança da área mentia (ver seção 15). Hoje, dos 108 pontos, **44 (40,7%) caem em
  pixel de borda** e ficam na amostra; a dificuldade de interpretar borda se resolve na marcação, com a opção
  "não dá para saber", e com a regra de rotulagem (o rótulo é o que ocupa a maior parte do pixel de 20 m).
  **Borda** aqui é: a vizinhança 3 × 3 de pixels do mapa (60 m × 60 m) contém mais de uma classe.
- **O mapa final foi treinado em pixels da própria área**, sem separar uma região para treino: são 8.000 pixels
  sorteados dos 953.046. O sorteio da validação é independente do sorteio do treino, mas a coincidência não é
  zero: o valor esperado é **0,9 ponto** dos 108 (0,84%). Se acontecer, aquele ponto mede memorização e não
  generalização; o efeito no total é ~1% da amostra. Quem quiser zerar isso treina o mapa final excluindo os
  pixels de validação.

### 5.3 A página de conferência

`conferencia/index.html` — **arquivo único, 2,6 MB, funciona offline**, imagens embutidas em base64.

- 108 pontos, um por vez: imagem de detalhe (700 m) e de contexto (2 km), ambas do mosaico Sentinel-2 de 10 m.
- Três botões: **eucalipto / outra cobertura / não dá para saber**, com teclas 1, 2, 3 e setas.
- **Conferência cega de verdade** (correção de 31/10): a página **não contém** a classe do mapa. O HTML guarda
  apenas `id`, `lon`, `lat` e as imagens; o `conferencia/pontos.csv` que vai para a pesquisadora tem só
  `id`, `lon`, `lat`; e o CSV exportado tem `id`, `lon`, `lat`, `marcacao`. A chave (`id` → estrato e classe)
  fica em `dados/chave/pontos_chave.csv` e só o `06_acuracia.py` lê. A verificação é automática:
  `grep -c -iE "classe_mapa|\bestrato\b" conferencia/index.html` devolve **0**.
- Os ids foram **embaralhados**: se ficassem agrupados por estrato, o número do ponto já entregaria a classe.
- A página traz a regra de rotulagem: classificar pelo que ocupa a maior parte do pixel de 20 m; se o pixel cai
  em transição e não dá para decidir, usar "não dá para saber" em vez de forçar um palpite.
- **Marcador do pixel** (correção de 31/10): um quadrado vermelho no centro da imagem de detalhe mostra o pixel
  de 20 m. A conta: a imagem tem 700 m em 240 px (~2,92 m/px), então o pixel de 20 m ocupa ~6,9 px na imagem, ou
  2,857% da largura — por isso o marcador é definido em porcentagem e continua correto em qualquer tamanho de
  tela. A tecla **m** (ou o botão sob as imagens) mostra e oculta.
- **"Borda" está definida na página**: ponto cuja vizinhança 3 × 3 de pixels do mapa (60 m × 60 m) tem mais de
  uma classe. São 44 dos 108 e ficam na amostra de propósito.
- **Ressalva sobre a referência** (correção de 31/10): a imagem de conferência é Sentinel-2 de 10 m, **a mesma
  fonte do mapa**. Marcar nela mede a concordância com o que se vê nessa imagem, não a verdade de campo; por isso
  a página manda abrir o link de alta resolução nos pontos duvidosos e, se possível, comparar outra data —
  plantio jovem e talhão recém-colhido se parecem com pastagem no Sentinel-2.
- Salva no `localStorage` (fecha o navegador e volta), mostra progresso e exporta `marcacoes.csv`.
- Link para o Google Maps de cada ponto, para quem quiser conferir em imagem de alta resolução (precisa de internet).

### 5.4 O cálculo

`codigo/06_acuracia.py` → `dados/acuracia_resultado.json`, `figuras/matriz_confusao.png`.

Calcula, por estrato e no total: matriz de confusão, acurácia global com erro padrão, acurácia do usuário e do
produtor, **área ajustada pela amostra com IC95** e a área crua (contagem de pixels) para comparar.
Duas políticas para "não sei": excluir (padrão) ou contar como erro — as duas saem impressas.

**A acurácia global daqui é binária** (eucalipto × não eucalipto): é a pergunta do mapa de eucalipto. Ela **não é
comparável** com a acurácia de 5 classes do passo 03 (0,78 no maior N), porque são perguntas diferentes com
número de classes diferente — e o script diz isso na saída.

**Para testar o script sem inventar resultado, ele roda com um CSV fictício** (`conferencia/marcacoes_FICTICIO.csv`,
coluna `ficticio = SIM`, gerado a partir do MapBiomas com 25% de erro injetado). Esse é o resultado que aparece hoje:

| Política para "não sei" | n | Acurácia global | UA eucalipto | PA eucalipto | Área no mapa | Área ajustada (IC95) |
|---|---|---|---|---|---|---|
| **excluir** (padrão) | 101 | 0,852 ± 0,067 | 0,545 | 0,374 ± 0,190 | 41,4 km² | **60,3 km² (34,8–85,8)** |
| contar como erro | 108 | 0,853 ± 0,063 | 0,500 | 0,369 ± 0,194 | 41,4 km² | 56,1 km² (32,0–80,3) |

O erro padrão da PA é **0,097** (eucalipto) e **0,019** (não eucalipto) — pela fórmula de razão de Olofsson et al. (2014, Eq. 7),
não pela binomial. A versão anterior usava a fórmula errada e dava 0,107 e 0,035; a diferença parece pequena, mas
o intervalo do eucalipto encolhia ou crescia conforme o estrato, e é ele que decide se a área é comparável.

**Esses números são do teste do script, não do mapa.** O que eles já ensinam: um mapa com 85% de acurácia global
pode subestimar a área da classe alvo em cerca de um terço (41,4 vs 60,3 km², −31%), porque a classe é rara e a
acurácia global é dominada pelas classes grandes. É exatamente por isso que a pergunta "a classificação está
satisfatória?" não tem resposta de um número só.

**A linha em destaque é a política "excluir", e ela pode enviesar a área para baixo**: os "não sei" se concentram
nas bordas e no estrato raro, então tirá-los tende a deixar a amostra mais "fácil". O número em destaque deve ser
lido junto com a política "não sei = erro" (56,1 km²), que é a mais conservadora. O ideal de Olofsson é substituir
cada "não sei" por outro ponto sorteado, em vez de descartá-lo — é o que se faria num trabalho com mais tempo.

## 6. Controles — por que isso não é artefato

`codigo/07_controle.py` → `dados/controle.json`. Quatro testes que **falhariam** se houvesse erro de código:

| Controle | Resultado | O que prova |
|---|---|---|
| Random Forest com rótulos embaralhados | acurácia **0,193** | sem sinal nos rótulos, o modelo não acerta; se acertasse, haveria vazamento |
| Regra boba ("prever sempre pastagem") | acurácia **0,310** | o modelo (0,760) ganha da regra boba, então aprende algo além da frequência |
| Estimador de área com verdade conhecida (300 simulações) | média 49,2 km² para verdade 49,1 (**viés +0,07%**), **cobertura do IC95 = 94,0%** | a fórmula está implementada certo e o intervalo é honesto |
| Sorteio só em pixels "puros" × em todo o estrato (paisagem sintética, 200 simulações) | puros: área 26,2 km² (**−2,7%**), acurácia 1,000 (**+3,8 p.p.**), IC95 cobre a verdade em **0%** das repetições. Todo o estrato: 27,0 km² (**+0,2%**), 0,967 (+0,5 p.p.), cobertura **90%** | no cenário sintético, o filtro elimina **todos** os erros do estrato e o estimador vira a contagem crua; o mecanismo é o que importa — num mapa real o efeito é menor, mas na mesma direção |
| Mapa 100% correto (caso degenerado) | área ajustada = área crua = 41,4 km²; acurácias = 1,000 | o estimador não inventa correção quando não há erro |
| **Exemplo numérico publicado** (Olofsson et al. 2014, Tabelas 6–9) | 16/16 células de `p_ij` batem; OA 0,9465; UA e PA de 4 classes; SE de OA, UA e área dentro da tolerância (área 3.236 vs 3.138 ha e 9.231 vs 9.270 ha) | as fórmulas são as do artigo, não uma versão parecida — `codigo/test_olofsson.py` |

O teste publicado está em `codigo/test_olofsson.py` e roda em 2 segundos; ele falha (exit code 1) se qualquer
número divergir. É ele que sustenta a correção do erro padrão da PA descrita na seção 16.

No mesmo teste do estimador, a **contagem crua de pixels errou −15,7%** (41,4 vs 49,1 km²). Ou seja: a correção
por amostragem não é firula metodológica, ela muda o número.

## 7. O que deu errado (e o que fizemos)

Registrado porque errar em silêncio é pior do que errar:

1. **O primeiro caminho do MapBiomas não existia** (`.../lulc/collection11/mapbiomas_collection11_integration_v1`).
   Listei os assets e usei `projects/mapbiomas-public/assets/brazil/lulc/v1/collection_11_2024_v1`.
2. **`linkCollection` com o argumento errado**: passei `['system:index']` em vez das bandas do Cloud Score+;
   o Earth Engine reclamou e corrigi para `['cs', 'cs_cdf']`.
3. **`geometry.bounds()` voltou em EPSG:4326**, não em UTM, e a grade saiu com 3 × 3 pixels. Passei a calcular
   os limites a partir das coordenadas já reprojetadas.
4. **`resample('nearest')` não existe no Earth Engine** (o padrão já é vizinho mais próximo). Removido.
5. **O controle pegou um vazamento de verdade:** no primeiro `07_controle.py`, o sorteio de treino não excluía os
   pixels do teste, e o modelo com rótulos embaralhados marcava 0,48 de acurácia (deveria ser ~0,2). Isso acontece
   por memorização de vizinhos. Corrigido, caiu para 0,193. É a demonstração prática do problema da seção 4.
6. **O CSV fictício usava nomes de classe** ("floresta", "pastagem") como marcação, e o `06` descartava 91 linhas.
   Corrigido para `eucalipto` / `nao_eucalipto` / `nao_sei`.
7. **As colunas alvo/não-alvo da matriz estavam trocadas** (a área ajustada saiu 315 km² em vez de 65). Corrigido
   ao trocar a convenção de índice no `olofsson.py` e conferido no caso "mapa 100% correto".
8. **O sorteio da validação excluía os pixels de borda** — erro de método encontrado na conferência externa de
   31/10. O filtro de "vizinhança 3 × 3 pura" dava probabilidade zero aos pixels onde o mapa mais erra; a amostra
   deixava de ser probabilística e o intervalo de confiança passava a mentir (o controle novo mostra cobertura de
   **0%**). Corrigido: sorteio uniforme em todo o estrato, 44 dos 108 pontos (40,7%) caem em borda e ficam.
   Detalhes na seção 15.
9. **A conferência "cega" não era cega**: `estrato` e `classe_mapa` estavam no JavaScript da página e no
   `conferencia/pontos.csv`. Corrigido: a chave foi para `dados/chave/pontos_chave.csv` e só o `06` a lê.
10. **A variância da acurácia do produtor estava errada** (2ª rodada): usava a binomial do estrato, e PA é razão
   de duas estimativas. Trocada pela fórmula de razão (Olofsson et al. 2014, Eq. 7) e conferida contra o
   exemplo publicado do artigo: SE do eucalipto caiu de 0,107 para **0,097** e o do não eucalipto de 0,035 para
   **0,019**.
11. **O mapa tinha cor errada** (2ª rodada): o `ListedColormap` tinha 6 cores para 5 classes e a pastagem saía
   sem amarelo. Corrigido com `BoundaryNorm`; conferido olhando a figura.
12. **A página falava de um "círculo pequeno no meio da imagem" que não existia** (2ª rodada). Agora existe um
   marcador de verdade, em CSS, do tamanho exato do pixel de 20 m, e ele pode ser escondido com a tecla `m`.

Também vale registrar: o `FAO/GAUL/2015/level2` está marcado como obsoleto no Earth Engine (sugerem 2025), mas
continua funcionando e é o que tem municípios brasileiros; e a figura de RGB precisou de alongamento por
percentis (2–98%) porque a reflectância da seca é escura.

## 8. O que não foi possível fazer

- **Não há acurácia real do mapa.** Seria preciso que uma pessoa marcasse os 108 pontos (ou um dado de campo).
  O CSV de resultado é fictício, e está marcado como tal em três lugares. A conferência usa Sentinel-2 de 10 m —
  a mesma fonte do mapa —, então o que se mede é **"verdade relativa ao Sentinel-2 de 10 m"**: erros que essa
  imagem não separa (eucalipto jovem × pastagem seca, dossel × mata) passam despercebidos pelo modelo **e** por
  quem marca.
- **Não usei imagem de alta resolução** (Google/Planet): exige conta e/ou crédito. A página dá o link do Google
  Maps para conferência visual, mas o recorte embutido é Sentinel-2 de 10 m.
- **Não usei Copernicus CDS nem Earthdata** (exigem cadastro): não foram necessários.
- **Não fiz a validação com 430 pontos (SE = 0,02)**: 430 interpretações manuais não cabiam no encontro. O script
  faz, é só rodar `python codigo/05_desenho_validacao.py --se 0.02`.
- **Não testei o efeito de aumentar a resolução para 10 m** nem o uso de mais anos; ficou fora do escopo.
- **Não avaliei o classificador com dado de campo**, então não sei se o teto de 0,69 de F1 é do algoritmo ou do
  MapBiomas. Provavelmente é mais do MapBiomas do que do algoritmo — mas isso não foi medido.
- **Não validei pontos duvidosos em imagem de alta resolução nem em outra data**: o link do Google Maps está na
  página, mas abrir 108 pontos em alta resolução e comparar datas não caberia no encontro. É a melhoria que mais
  reduziria o "não sei" e a confusão eucalipto × pastagem.
- **Não rodei o mapa estadual nem repeti a curva nas outras regiões**: a seção 14 dá o desenho e os números de
  amostra, não o resultado.

## 9. Limites e decisões que são da pesquisadora

Estas decisões **não** foram tomadas pela IA porque mudam a metodologia científica:

- **Agrupamento das classes.** Agrupei 30 classes do MapBiomas em 5 grupos (eucalipto, floresta, pastagem,
  agricultura, mosaico/água). Se o trabalho precisa separar soja de cana, ou cerrado de floresta, muda tudo.
  O agrupamento está explícito em `codigo/common.py` (`GRUPOS`) e é reversível.
- **Classe alvo binária ou multiclasse.** A validação de campo é binária (eucalipto / não eucalipto) porque a
  pergunta é a área de eucalipto. Validar 5 classes exigiria 5 × mais pontos para a mesma precisão.
- **Tamanho da amostra.** 108 pontos é um compromisso entre ±8 p.p. e uma sessão de interpretação. O número ideal
  depende de quanto erro o trabalho tolera.
- **Escala de mapeamento (20 m).** O MapBiomas é 30 m; adotei 20 m para aproveitar as bandas de 20 m do Sentinel-2.
  Isso cria pixels cujo rótulo vem de um pixel de 30 m — fonte real de erro que a validação vai medir.
- **Onde parar na curva.** 400–800 por classe é a faixa de melhor retorno aqui; não é uma recomendação universal.
- **A referência é a mesma imagem do mapa.** A conferência usa Sentinel-2 de 10 m — a mesma família de dados que
  treinou o modelo. Isso mede concordância com a interpretação dessa imagem, não verdade de campo; um plantio
  jovem ou um talhão recém-colhido pode ser lido como pastagem por quem marca e pelo modelo, e o erro passa
  despercebido nos dois lados.
- **Cerca de 1 ponto pode coincidir com pixel de treino.** Foram 8.000 pixels de treino em 953.046 (0,84%); com 108
  pontos, o valor esperado de coincidência é **0,9 ponto**. Se acontecer, aquele ponto mede memorização, não
  generalização — o efeito no total é de ~1% da amostra e não muda a conclusão, mas vale registrar no texto final.
  (O sorteio dos pontos é independente do sorteio do treino, então a coincidência é aleatória, não sistemática.)

## 10. Onde a IA generativa ajudou e onde não ajuda

**Ajudou, e muito, no trabalho mecânico e no desenho:**

- escrever e depurar o código do Earth Engine (mosaico, máscara de nuvem, download em blocos, reprojeção);
- implementar a curva de aprendizado com o mesmo conjunto de teste e a comparação aleatório × blocos;
- implementar as fórmulas de Olofsson (que são chatas de acertar) e **conferi-las contra verdade conhecida**;
- gerar a página de conferência offline inteira (HTML + imagens embutidas + exportação de CSV);
- explicar a matriz de confusão e traduzir "acurácia do usuário" e "do produtor" em frases curtas;
- apontar os próprios erros: o controle com rótulos embaralhados foi o que revelou o vazamento de treino.

**Não ajuda, e é importante dizer:**

- **dizer se o mapa está certo.** Sem dado de referência, qualquer "acurácia" que a IA produza é circular: ela
  compara o mapa com o próprio rótulo que gerou o mapa. Foi por isso que a validação ficou separada e vazia.
- **decidir o que é eucalipto no campo.** Um talhão recém-plantado, um talhão recém-colhido e uma pastagem suja
  podem ser idênticos no Sentinel-2 de 10 m. Quem interpreta usa contexto (data de plantio, espaçamento, vizinhança).
- **decidir a metodologia.** Quantas classes, qual escala, qual erro tolerável — isso é do trabalho, não do modelo.
- **substituir a checagem humana.** A IA pode pré-triar (ver abaixo), mas não assinar a validação.

**Sobre usar um modelo com visão para pré-triagem:** é tecnicamente viável — pedir a um modelo multimodal que
classifique cada recorte de 700 m como "eucalipto / não / não sei" e comparar com a marcação humana. Isso pode
acelerar a conferência de 108 pontos e é um bom teste de concordância. **Mas não é validação:** a acurácia de um
modelo de visão não é conhecida nessa área, ele erra de forma sistemática (talhão jovem, talhão colhido) e a
amostra continuaria sendo a mesma — o que se ganha é velocidade de marcação, não independência da referência.
Se quiser testar, guarde as marcações humanas de uma subamostra como referência e meça a concordância
(coeficiente kappa, por exemplo). Nunca use a pré-triagem como se fosse o dado de campo.

## 11. De onde saiu cada número

Todos os números deste relatório saem de um script desta pasta. A tabela principal é impressa por
`python codigo/08_resumo.py`, que lê os JSONs gerados pelos passos (e imprime também composição do recorte,
priors, centro, municípios e treino por classe, para a conferência ser direta):

| Número | Arquivo | Script |
|---|---|---|
| 129,3 km²; 381,0 km²; 9,07%; centro do recorte | `dados/recorte.json` | 01 |
| 58 e 48 cenas; 19 bandas; 62,7 MB | `dados/mosaico_meta.json` | 02 |
| tabela da curva; N de estabilização; contagens de pixel | `dados/curva_resumo.json` | 03 |
| áreas do mapa; concordância 0,763 | `dados/mapa_meta.json` | 04 |
| n = 108; alocação; tabela de SE; 44 pontos em borda (40,7%) | `dados/desenho_validacao.json` | 05 |
| 0,852 / 0,545 / 0,374 / SE 0,097 / 60,3 km² e a variante "não sei = erro" | `dados/acuracia_resultado.json` | 06 |
| 0,760 / 0,193 / 0,310 / viés +0,07% / 94,0% / filtro de borda | `dados/controle.json` | 07 |
| teste do estimador contra o artigo (16 células, OA, UA, PA, SEs) | `dados/teste_olofsson.json` | teste_olofsson |
| Goiás: 1.392 km² (0,40%); n = 176; piso 100 → 275 pontos | `dados/plano_goias.json` | 09 |
| tabela consolidada (é a que este relatório usa) | `dados/resumo_final.json` | 08 |

Conferência das referências: `python codigo/verificar_referencias.py` (10 de 10 com DOI e título conferidos no
Crossref em 31/10/2026) → `dados/referencias_conferidas.json`.

## 12. Custo e tempo

- **Earth Engine:** cerca de 30 chamadas de computação pesada no total — contagem manual nos logs, **não conferida
  por script** (uma soma por município, uma janela de densidade, dois histogramas, 22 downloads de blocos, mais
  uma consulta de áreas do estado no passo 09). Nenhuma exportação para o Drive, nenhuma conta criada.
- **Arquivos baixados:** 62,7 MB no disco (tamanho local, não tráfego), medido pelo script 08.
- **Tempo de execução** (tempos observados à mão, não conferidos por script): passo 01 ≈ 2 min, 02 ≈ 4 min
  (baixando), 03 ≈ 4 min, 04 ≈ 1 min, 05 ≈ 1 min, 06 ≈ 5 s, 07 ≈ 2 min, 09 ≈ 1 min,
  `test_olofsson.py` ≈ 2 s.
- **Tempo de trabalho** para chegar até aqui: ~2h, sendo boa parte em depuração (seção 7).
  A regra era 60–90 min; estourou, e o motivo foi o controle que revelou o vazamento e a correção do estimador.

## 13. Se fosse continuar amanhã

1. Marcar os 108 pontos (30–40 min) e rodar `python codigo/06_acuracia.py conferencia/marcacoes.csv`.
   Nos pontos duvidosos, abrir o link do Google Maps e, se possível, comparar outra data. Vale escolher
   **20–30 pontos** e conferir **só se há eucalipto** em imagem de alta resolução, anotando à parte: não é
   marcação (não entra no cálculo), é checagem de sanidade contra a limitação da referência de 10 m.
2. Olhar a **área ajustada**, não a acurácia global, para decidir se o mapa serve.
3. Se a área de eucalipto for o produto principal, subir a amostra para SE = 0,03 (191 pontos).
4. Se o erro estiver concentrado em "floresta ↔ eucalipto", testar feições que separem estrutura (índices de
   textura, série temporal de NDVI por talhão) antes de aumentar amostra.
5. Repetir a curva com as marcações humanas: aí sim a curva mede a acurácia do mapa, não a concordância com o MapBiomas.

---

## 14. De Rio Verde para Goiás — o que muda

O recorte de 381 km² responde "como fazer"; não responde "quanto de eucalipto há em Goiás". Os números para
planejar o passo estadual estão em `codigo/09_plano_goias.py` → `dados/plano_goias.json` (uma consulta ao Earth
Engine, sem download de imagem).

**O tamanho do problema.** A silvicultura somada nos 242 municípios é **1.583 km²** (soma a 100 m, `01`); na grade
de 1 km do estado, o MapBiomas dá **1.392 km²**, ou **0,40%** dos 352.253 km² de Goiás (`09`). Uma classe que ocupa
0,4% da área é o caso clássico em que alocação proporcional falha: com n = 176 (SE = 0,03), **o eucalipto levaria
1 ponto** (`09`).

**Três regiões para repetir a curva** (sugestão a partir de `dados/silvicultura_por_municipio.csv`):

| Região | Silvicultura (km²) | % do município | % da silvicultura do estado |
|---|---|---|---|
| Rio Verde (sudoeste, agronegócio) | 129,3 | 1,54 | 8,2 |
| Niquelândia (norte, cerrado) | 99,2 | 1,00 | 6,3 |
| Catalão (sudeste, mineração/indústria) | 96,9 | 2,56 | 6,1 |

Elas são diferentes de propósito: no sudoeste o eucalipto está perto de soja e pastagem; no norte, de cerrado
preservado e pastagem extensiva; no sudeste, de mineração e reflorestamento industrial. Se a curva de aprendizado
estabilizar em N diferente nas três, o "número de amostras" do trabalho tem que ser o maior deles.

**Tamanho da validação estadual.** Mesma fórmula do passo 05, com o prior de acurácia do mapa local (`09`):

| Erro padrão alvo | n |
|---|---|
| 0,02 | 395 |
| **0,03** | **176** |
| 0,04 | 99 |
| 0,05 | 64 |

Com piso de 100 pontos no eucalipto (recomendação de Olofsson para classe rara) e o resto proporcional, o total
sobe para **275 pontos: 100 eucalipto / 47 floresta / 85 pastagem / 33 agricultura / 10 mosaico-água**, com
SE previsto de **0,030**. São 275 interpretações — entre 2 e 3 horas de marcação, no ritmo dos 108 pontos deste
teste.

**O que fazer, na ordem:**

1. **Repetir a curva** (`03`) em cada uma das três regiões, trocando o recorte em `dados/recorte.json` e rodando
   01 → 02 → 03. Anote o N em que o ganho por dobrada cai abaixo do custo em cada uma.
2. **Treinar por região.** O sorteio de treino deve ser estratificado por região (proporcional à área de
   silvicultura de cada uma), não global: senão o modelo aprende o sudoeste e erra o norte. Duas opções: um modelo
   por região (mais simples de explicar) ou um modelo único com a região como variável categórica (mais simples de
   operar). A escolha é da pesquisadora.
3. **Mapear o estado em blocos**, não de uma vez: o mesmo esquema de download em blocos do passo 02, com validação
   de borda entre blocos (o recorte de 20 km já mostra que a borda é onde o erro se concentra).
4. **Validar com o desenho do passo 05**, com os estratos do mapa estadual e o piso no eucalipto. Se o trabalho
   precisar de estimativa por região, estratifique também por região (subestratos) — Olofsson recomenda isso
   quando há objetivos por sub-região, e o custo é mais pontos.
5. **Conferir a área estadual contra o MapBiomas**: a diferença esperada é grande (o mapa local subestima a área
   crua em relação à ajustada); se o mapa estadual der área menor que a do MapBiomas, é sinal de omissão, não de
   acurácia.

**O que este projeto não fez:** não rodou o mapa estadual, não repetiu a curva nas outras regiões e não mediu o
custo computacional do estado inteiro. O que ele entrega é o desenho e os números de amostra para isso — e a
demonstração, no recorte, de que o método funciona e de onde ele quebra.

## 15. Correções de 31/10 (1ª rodada)

Uma conferência externa (`docs/revisoes/CORRECOES.md`) apontou dois erros de método e um de transparência. Todos foram
corrigidos, os scripts foram rodados de novo **na ordem 05 → 06 → 07 → 08** e os números abaixo vêm de
`python codigo/08_resumo.py` (que agora imprime também as duas políticas de "não sei" e o controle de borda).

### 15.1 O sorteio da validação excluía os pixels de borda (erro de método)

**Antes:** o `05` só sorteava pixels com vizinhança 3 × 3 "pura" no mapa — 530.035 dos 953.046 pixels. Isso dá
**probabilidade zero** a uma subpopulação inteira, justamente a que fica na transição dos talhões, onde o mapa
mais erra. Deixa de ser amostragem probabilística: a acurácia sai otimista e a área ajustada fica enviesada.

**Depois:** sorteio uniforme em **todos** os pixels de cada estrato, com probabilidade conhecida. Dos 108 pontos,
**44 (40,7%) caem em pixel de borda** e continuam na amostra (`dados/desenho_validacao.json`).

**O efeito, medido com verdade conhecida** (`07_controle.py`, paisagem sintética de 400 × 400 pixels com erro de
borda erodindo os talhões, 200 simulações):

| Protocolo de sorteio | Área média | Viés da área | Acurácia média | Viés da acurácia | IC95 cobre a verdade |
|---|---|---|---|---|---|
| só pixels "puros" | 26,2 km² | **−2,7%** | 1,000 | **+3,8 p.p.** | **0%** das repetições |
| todo o estrato | 27,0 km² | **+0,2%** | 0,967 | +0,5 p.p. | **90%** |

Verdade simulada: 26,9 km² e acurácia global 0,962. O mecanismo fica explícito: dentro do estrato "eucalipto" do
mapa, a fração que é eucalipto de verdade é **0,973** considerando todos os pixels e **1,000** considerando só os
puros. Ou seja, o filtro de borda transforma a estimativa na **contagem crua de pixels** (26,2 km², o mesmo número
do mapa) e o intervalo de confiança passa a não cobrir a verdade **nenhuma vez** — neste cenário sintético, em que
o filtro elimina todos os erros do estrato. Num mapa real os pixels "puros" não são 100% corretos, então o efeito é
menor, mas aponta na mesma direção. É o tipo de erro que não aparece no resultado: o mapa "melhora" e o relatório
fica mais bonito.

**Efeito no exemplo fictício** (`06_acuracia.py`, política padrão):

| | antes (só puros) | depois (todo o estrato) |
|---|---|---|
| Acurácia global | 0,900 ± 0,060 | **0,852 ± 0,067** |
| Acurácia do usuário (eucalipto) | 0,833 | **0,545** |
| Acurácia do produtor (eucalipto) | 0,526 | **0,374** |
| Área ajustada (IC95) | 65,6 km² (42,9–88,3) | **60,3 km² (34,8–85,8)** |

A queda não quer dizer que o mapa piorou (o mapa é o mesmo, seção 5.1): quer dizer que a medição ficou honesta ao
incluir os pontos difíceis. A regra de rotulagem que substitui o filtro está na página e no README: o ponto é
classificado pelo que ocupa a **maior parte do pixel de 20 m**, e a transição indecidível se resolve com
"não dá para saber" — não excluindo o pixel.

### 15.2 A conferência não era cega (transparência)

**Antes:** a página não mostrava a classe na tela, mas `estrato` e `classe_mapa` estavam no JavaScript e no
`conferencia/pontos.csv`. Bastava abrir o CSV ou o código-fonte para ver o palpite do mapa — e o `id` também
entregava, porque os pontos eram ordenados por estrato (ids 1–12 eram todos eucalipto).

**Depois:**

- `conferencia/index.html` guarda só `id`, `lon`, `lat`, `img_det`, `img_ctx`;
- `conferencia/pontos.csv` tem só `id`, `lon`, `lat`;
- o CSV exportado pela página tem `id`, `lon`, `lat`, `marcacao`;
- a chave (`id` → estrato, classe do mapa, coordenadas UTM, se é borda) está em **`dados/chave/pontos_chave.csv`**;
- o `06_acuracia.py` **junta pelo `id`** e é o único que lê a chave; se a chave faltar, ele para com mensagem clara;
- os **ids foram embaralhados**, então a ordem dos pontos não revela o estrato.

Verificação automática (dentro do próprio `05`, que para se falhar; e repetida à mão agora):

```
[05] checagem cega: ok (0 ocorrencias de classe_mapa/estrato; pontos so com id/lon/lat/imagens)
grep -c -iE "classe_mapa|\bestrato\b" conferencia/index.html   -> 0
chaves do array PONTOS                                          -> id, img_ctx, img_det, lat, lon
```

### 15.3 Números do relatório desatualizados

O relatório citava 65,6 km² (IC95 42,9–88,3) para o exemplo fictício, mas a política "não sei = não eucalipto"
dava 62,9 km² (41,7–84,1) — eram duas políticas diferentes apresentadas como se fossem uma. Agora as duas estão
lado a lado, com o nome da política, e o `08_resumo.py` imprime as duas (`dados/acuracia_resultado.json`):

| Política | n | Acurácia global | UA eucalipto | PA eucalipto | Área ajustada (IC95) |
|---|---|---|---|---|---|
| excluir "não sei" (padrão) | 101 | 0,852 ± 0,067 | 0,545 | 0,374 | 60,3 km² (34,8–85,8) |
| "não sei" = não eucalipto | 108 | 0,853 ± 0,063 | 0,500 | 0,369 | 56,1 km² (32,0–80,3) |

Também foi atualizado o resumo do topo (85% de acurácia global; PA 37%; 60 km²) e a seção 6, que ganhou o
controle de borda. Números que **não** mudaram porque o passo 03 e o passo 04 não foram tocados: a curva
(F1 0,398 → 0,691; 0,425 → 0,607), as áreas do mapa (eucalipto 41,4 km²), a concordância com o MapBiomas (0,763)
e o download (62,7 MB).

### 15.4 Arquivos que mudaram

| Arquivo | Mudança |
|---|---|
| `codigo/05_desenho_validacao.py` | sorteio sem filtro de borda; ids embaralhados; página e CSV cegos; chave em `dados/`; regra de rotulagem na página |
| `codigo/06_acuracia.py` | junta a classe do mapa pela chave (`dados/chave/pontos_chave.csv`), não pelo CSV; ignora colunas antigas com aviso |
| `codigo/07_controle.py` | novo controle "só pixels puros × todo o estrato" com verdade conhecida (200 simulações) |
| `codigo/08_resumo.py` | imprime os pontos em borda, as duas políticas de "não sei" e o controle de borda |
| `README.md`, `CLAUDE.md` | conferência cega, regra de rotulagem, chave e o novo controle |

---

## 16. Correções de 31/10 (2ª rodada)

Duas conferências independentes apontaram oito problemas, todos confirmados no código. O critério foi o do
`docs/revisoes/CONTEXTO.md`: servir a quem precisa decidir **quantas amostras** usar e **como conferir** o mapa de eucalipto em
Goiás. Tudo foi rodado de novo (05 → 06 → 07 → 08, mais o teste novo e o plano estadual) e os números abaixo saem
de `python codigo/08_resumo.py`.

### 16.1 Cores do mapa

**Antes:** o `ListedColormap` tinha 6 cores para 5 classes (`+ ["#ffffff"]`) e o `imshow` usava `vmin=-0,5,
vmax=4,5`. Com 6 cores em 5 intervalos, a pastagem caía na cor da floresta e o mosaico/água saía branco.
**Depois:** `BoundaryNorm` com exatamente uma cor por classe e `set_bad` para sem-dado (`04_mapa.py`).
Conferido **olhando a figura** `figuras/mapa_area.png`: pastagem amarela, agricultura rosa, floresta verde,
eucalipto marrom, mosaico/água cinza — igual à legenda.

### 16.2 Erro padrão da acurácia do produtor e da acurácia do usuário combinada

**Antes:** `_pa` usava a variância binomial do estrato; `_ua` somava contagens brutas entre estratos.
**Depois:** `codigo/olofsson.py` foi reescrito como estimador geral (q estratos do mapa × r classes de referência),
com a variância de razão da Eq. 7 de Olofsson et al. (2014) para a PA e média ponderada por área para a UA de classe que junta
estratos:

| Quantidade (exemplo fictício) | antes | depois |
|---|---|---|
| SE da PA do eucalipto | 0,107 | **0,097** |
| SE da PA do não eucalipto | 0,035 | **0,019** |
| UA do não eucalipto | 0,889 (soma de contagens) | **0,889** (média ponderada; igual porque a alocação é proporcional, mas a fórmula agora vale quando não for) |

**Prova:** `codigo/test_olofsson.py` reproduz o exemplo numérico publicado do artigo — Tabela 8 (contagens) →
Tabela 9 (proporções de área, **16 de 16 células**), com acurácia global, UA e PA das 4 classes; e Tabela 6 +
alocação *Alloc2* → Tabela 7 (SE da OA 0,0108 vs 0,011; UA 0,0533 vs 0,053 e 0,0234 vs 0,023; área 3.236 vs
3.138 ha e 9.231 vs 9.270 ha). As áreas ficam dentro de 5% porque a Tabela 6 publica `p31` e `p41` com um
algarismo significativo (0,002 e 0,004) — está documentado no teste.

### 16.3 O que a acurácia global mede

O `06` imprime, antes do resultado: "a acurácia global calculada aqui é BINÁRIA (eucalipto × não eucalipto); não é
comparável com a acurácia de 5 classes da curva (passo 03)". A mesma frase está na seção 5.4 e no README. O JSON
ganhou o campo `tipo_acuracia`.

### 16.4 Robustez quando um estrato fica sem ponto

**Antes:** `ValueError` e traceback. **Depois:** o `06` avisa qual estrato e qual política, segue com os outros e
mantém a base de área (381,2 km²), para a área ajustada não ser reescalada. Teste com
`conferencia/marcacoes_FICTICIO_estrato_vazio.csv` (todos os 16 pontos de mosaico/água como "não sei", política
"excluir"):

```
AVISO (politica 'excluir'): sem nenhum ponto em ['mosaico_agua'].
      Esses estratos saem da estimativa (a area deles NAO e corrigida);
      o resultado abaixo vale para os estratos que sobraram.
=== politica padrao: 'nao sei' excluido (n = 86) ===
  acuracia global: 0.716 +- 0.064 (IC95)
  area ajustada pela amostra: 56.6 +- 24.4 km2 (IC95: 32.2 a 81.0)
```

Nenhum traceback. Esse CSV fictício é gerado pelo próprio `05` e fica ao lado do outro.
Caso mais grave, o da **classe alvo**: se todos os 12 pontos de eucalipto ficarem "não sei", a política "excluir"
não consegue estimar a área (o estrato alvo some da conta). O `06` detecta, avisa, omite essa política e roda a
"não sei = não eucalipto", que é sempre calculável — sem traceback e sem inventar número.

### 16.5 Página de conferência

- **Marcador do pixel:** o texto antigo falava de um círculo que não existia. Agora há um quadrado em CSS no
  centro da imagem de detalhe, com largura de **2,857% = 20 m / 700 m**. Conferido no navegador (Chromium
  headless): 8,6 px numa imagem de 300 px — exatamente 2,86%. A tecla **m** e um botão mostram/ocultam.
- **"Borda" definida** na página: vizinhança 3 × 3 do mapa (60 m × 60 m) com mais de uma classe; são 44 dos 108 e
  ficam na amostra de propósito.
- **Ressalva sobre a referência:** a página diz que a imagem de 10 m é a mesma fonte do mapa, que isso mede
  concordância e não verdade de campo, e que nos pontos duvidosos se deve abrir o link de alta resolução e, se
  possível, comparar outra data.
- **Coincidência com pixel de treino:** 8.000 pixels de treino em 953.046 dão valor esperado de **0,9 ponto** dos
  108. Se ocorrer, afeta ~1% da amostra. O sorteio dos pontos é independente do sorteio do treino.

### 16.6 De Rio Verde para Goiás

Nova seção 14 do relatório, com o plano e os números de `codigo/09_plano_goias.py` (`dados/plano_goias.json`):
silvicultura no estado = 1.392 km² (0,40% de Goiás, grade de 1 km); três regiões sugeridas (Rio Verde,
Niquelândia, Catalão); n de validação estadual = 176 para SE 0,03 e **275** com piso de 100 pontos no eucalipto
(100 / 47 / 85 / 33 / 10), SE previsto 0,030.

### 16.7 Higiene

- `CLAUDE.md` não tem mais o nome de usuário do Windows nem caminho absoluto.
- **62,7 MB** passou a ser descrito como **tamanho dos arquivos no disco**, não tráfego de rede (que não foi
  medido).
- O `08_resumo.py` imprime também: SE de UA e PA, as duas políticas de "não sei", o resultado do teste publicado,
  os números do plano estadual, os pontos em borda e os ganhos por dobrada da curva.
- A chave saiu de `dados/pontos_chave.csv` para **`dados/chave/pontos_chave.csv`**, pasta separada do material da
  pesquisadora; o README avisa em destaque para não abrir antes de marcar. A cegueira continua garantida pelo
  código (a página e o CSV não têm a classe), mas agora também há uma separação física.

### 16.8 O que não deu para fazer nesta rodada

- **As SEs de área do exemplo publicado divergem até 3%** das do artigo (3.236 vs 3.138 ha). A causa provável é o
  arredondamento de `p31` e `p41` na Tabela 6 (um algarismo significativo); o teste usa tolerância de 5% e isso
  está escrito no código. Não é erro de fórmula: as SEs de OA, UA e a área da classe 3 batem em 1%.
- **A página foi conferida só no Chromium**, via Playwright, e não em Firefox/Safari. O `localStorage` está
  protegido por `try/catch`, então a página não quebra se o navegador bloquear o armazenamento.
- **Não rodei o mapa estadual** nem repeti a curva nas outras regiões — a seção 14 entrega o desenho e os números
  de amostra, não o resultado.

## Teste: a IA consegue conferir o mapa? (31/10, conferência do Claude)

Um modelo com visão (Gemini 3.8 Flash) classificou às cegas 30 dos 108 recortes da página. Contra o MapBiomas: achou 4 dos 8 pontos de silvicultura, chamou os outros 4 de pastagem/agricultura e 1 ponto de mata de eucalipto, sempre com confiança 0,95; respondeu "não sei" em 6 pontos de borda, estrada e plantio jovem. Serve para ordenar onde olhar com cuidado; não serve como referência. Detalhes em `pre_triagem_ia/RESULTADO.md`.
