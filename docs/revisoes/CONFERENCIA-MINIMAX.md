# Conferência independente — pasta `bianca`

Revisão feita depois das correções de 31/10 (`CORRECOES.md`). Não refiz o trabalho: conferi.
Data da conferência: 31/10/2026. Ambiente conferido: Windows, Python 3.14.3, `numpy/pandas/scikit-learn/
rasterio/scipy/pillow/pyproj/matplotlib` importando sem erro.

**Nenhum arquivo existente foi alterado.** Antes de rodar cada script que escreve saída, guardei o
md5 dos arquivos afetados; depois de rodar, os md5 são idênticos aos originais (ver seção 0.2).
O único arquivo novo desta conferência é este.

---

## 0. Escopo do que foi conferido

### 0.1 Scripts que rodei

| Script | Escreve | Resultado |
|---|---|---|
| `03_curva_aprendizado.py` | `dados/curva_aprendizado.csv`, `dados/curva_resumo.json`, `figuras/curva_aprendizado.png` | rodou (190 s), saída **byte a byte igual** à que estava na pasta |
| `04_mapa.py` | `dados/mapa_predito.tif`, `dados/mapa_meta.json`, `figuras/mapa_area.png` | rodou, saída **byte a byte igual** |
| `05_desenho_validacao.py` | `conferencia/index.html`, `conferencia/pontos.csv`, `conferencia/marcacoes_FICTICIO.csv`, `dados/pontos_chave.csv`, `dados/desenho_validacao.json` | rodou, saída **byte a byte igual**; a checagem cega embutida passou |
| `06_acuracia.py` (CSV fictício) | `dados/acuracia_resultado.json`, `figuras/matriz_confusao.png` | rodou, saída **byte a byte igual** |
| `07_controle.py` | `dados/controle.json` | rodou, saída **byte a byte igual**; os 5 `assert` passaram |
| `08_resumo.py` | `dados/resumo_final.json` | rodou, saída **byte a byte igual** |
| `verificar_referencias.py` | `dados/referencias_conferidas.json` | rodou, 10/10 conferidas no Crossref, saída **byte a byte igual** |

Isso é um resultado forte a favor do material: **os números publicados são reprodutíveis** — quem rodar
os scripts de novo, neste PC, obtém exatamente os mesmos arquivos.

**Scripts que não rodei** (por instrução do pedido, e porque não são necessários): `01_escolher_area.py`
e `02_baixar_imagens.py` (chamam o Earth Engine / baixam dados). Em vez disso, conferi os produtos
deles (`dados/recorte.json`, `dados/silvicultura_por_municipio.csv`, `dados/composicao_recorte.csv`,
`dados/mosaico_meta.json` e o tamanho dos `.tif`) e o código.

### 0.2 Como garanti não ter alterado nada

```
md5sum dados/*.json dados/*.tif figuras/*.png conferencia/*   # antes e depois
```

Todos os hashes conferidos antes e depois das execuções são iguais (ex.:
`dados/controle.json` = `beda32a4…`, `conferencia/index.html` = `44c65f49…`, `figuras/mapa_area.png`
= `04d3e832…`). O script de teste extra que usei para o item 4.2 ficou fora da pasta, em
`%TEMP%\opencode`.

### 0.3 Veredito curto

As três correções pedidas em `CORRECOES.md` **foram feitas de verdade**, e os números do relatório
confereem com as saídas dos scripts. Não achei nenhum número errado nem nenhuma conclusão que os
dados não sustentem.

O que achei são **três problemas de materialidade** que nenhum controle do material pega:
(a) a figura `figuras/mapa_area.png` desenha 3 das 5 classes com a cor errada (e a 5ª em branco,
igual ao fundo) — o defeito mais visível do conjunto;
(b) o `06_acuracia.py` **trava com traceback** no cenário exato para o qual a correção 1 criou a
opção "não dá para saber";
(c) a validação "de verdade" usa a **mesma imagem de 10 m que o mapa**, o que limita o que ela
consegue provar — e o relatório apresenta isso como limitação logística, não metodológica.

Detalhe e evidência de cada um na seção 7.

---

## 1. As correções de `CORRECOES.md` foram feitas? (item por item)

### Correção 1 — "o sorteio da validação exclui as bordas" → **FEITA**

- `codigo/05_desenho_validacao.py:96-100` sorteia em **todos** os pixels do estrato
  (`np.nonzero(mapa == k)`), sem filtro de vizinhança. O filtro antigo virou apenas um
  **diagnóstico** (`05:107-113`), que não remove nada.
- Saída conferida: `dados/desenho_validacao.json` → `"amostragem": "uniforme em todos os pixels do
  estrato (sem filtro de borda)"`, `"pontos_em_borda": 44`, `"pct_pontos_em_borda": 40.7`.
- O efeito foi medido, como pedido: `07_controle.py:130-240` implementa o par
  "só pixels puros × todo o estrato" com verdade conhecida. Saída de `07` (rodada por mim):
  `so pixels puros: area 26.2 km2 (vies -2.7%) | acuracia 1.000 (vies +3.8 p.p.) | IC95 cobre a
  verdade 0%` e `todo o estrato: area 27.0 km2 (vies +0.2%) | acuracia 0.967 (vies +0.5 p.p.) |
  IC95 cobre a verdade 90%`. Bate com a tabela do `RELATORIO.md` §14.1.
- A regra de rotulagem está na página (`conferencia/index.html`, instrução "Regra de rotulagem") e no
  `README.md` (passo 3). ✓

### Correção 2 — "conferência às cegas de verdade" → **FEITA**

Conferi por busca direta nos artefatos finais:

```
grep -c -iE "classe_mapa|\bestrato\b" conferencia/index.html   -> 0
```

- `conferencia/index.html`: o array `PONTOS` tem **exatamente** as chaves `id, lon, lat, img_det,
  img_ctx` (conferido extraindo o JSON do HTML com Python: 108 pontos, todas as entradas com as
  mesmas 5 chaves). Nenhuma ocorrência de `classe_mapa` ou `estrato` no arquivo inteiro.
- `conferencia/pontos.csv`: só `id, lon, lat` (108 linhas). ✓
- CSV exportado pela página: só `id, lon, lat, marcacao` (`05_desenho_validacao.py:318`). ✓
- A chave foi para `dados/pontos_chave.csv` (`id, estrato, classe_mapa, lon, lat, x_utm, y_utm,
  borda`), lida só pelo `06` (`codigo/06_acuracia.py:53-69`), que junta por `id` e avisa se faltar
  chave. ✓
- Os ids estão embaralhados: os 12 primeiros pontos do mapa de chave são
  `eucalipto, pastagem, agricultura, mosaico_agua, mosaico_agua, pastagem, …` — a ordem não entrega o
  estrato. ✓
- O `05` tem a checagem automática que aborta o script se a página deixar de ser cega
  (`05:344-352`), e ela passou na execução que rodei. ✓

### Correção 3 — "números desatualizados" → **FEITA, com uma ressalva (item 7.5)**

- As duas políticas de "não sei" estão lado a lado, com nome, no `RELATORIO.md` §5.4 e §14.3, e o
  `08_resumo.py` imprime as duas (`08:115-126`). Confirmei a saída: `nao sei excluido → 0.852 ±
  0.067, UA 0.545, PA 0.374, 60.3 km2 (34.8 a 85.8)` e `nao sei = nao eucalipto → 0.853 ± 0.063,
  UA 0.500, PA 0.369, 56.1 km2 (32.0 a 80.3)`.
- A seção "Correções de 31/10" (§14) existe no `RELATORIO.md`, com o que mudou, o antes/depois e a
  origem de cada número. ✓
- **Ressalva:** o pedido era "faça o `08_resumo.py` imprimir **todos** os números citados". Ele
  imprime a maioria, mas ainda não imprime alguns números que o relatório cita (item 7.5).

### Correção 4 — "cuidado" → **OK**

- O CSV fictício continua marcado: coluna `ficticio=SIM` nas 108 linhas; `06` imprime o aviso
  "este CSV esta marcado como FICTICIO"; `dados/acuracia_resultado.json` tem `"ficticio": true`; o
  título da figura `figuras/matriz_confusao.png` diz "(n = 101, FICTICIO)".
- Os passos 03 e 04 não foram mexidos: rodei os dois e as saídas são byte a byte iguais às que
  estavam na pasta, e os números da curva e do mapa no relatório batem.

---

## 2. Números conferidos (18)

Todos conferidos contra o arquivo de dados ou contra a saída do script indicado.

| # | Número no `RELATORIO.md` | Onde conferi | Resultado |
|---|---|---|---|
| 1 | F1 eucalipto 0,398 (N=25) → 0,691 (N=3.200), aleatório | `dados/curva_resumo.json` + rerun do `03` | confere |
| 2 | F1 por blocos 0,425 → 0,607 | idem + rerun do `03` | confere |
| 3 | Ganho por dobrada: +0,014 / +0,086 / +0,037 / +0,040 / +0,054 / +0,034 / +0,027 | `curva_resumo.json` | confere |
| 4 | dp do F1 cai de 0,021 para 0,004 | `curva_resumo.json` | confere |
| 5 | teste aleatório 190.609 px; teste por blocos 195.300 px (20 de 100 blocos de 2 km) | `curva_resumo.json` | confere |
| 6 | Concordância com o MapBiomas 0,763 | `dados/mapa_meta.json` + rerun do `04` | confere |
| 7 | Áreas do mapa: 41,4 / 65,7 / 118,1 / 100,4 / 55,6 km² | `mapa_meta.json` + rerun do `04` | confere |
| 8 | Rio Verde 129,3 km²; Niquelândia 99,2; Catalão 96,9; 242 municípios | `dados/silvicultura_por_municipio.csv` | confere |
| 9 | Recorte 381,0 km²; silvicultura 9,07% / 36,4 km² | `dados/recorte.json`, `composicao_recorte.csv` | confere |
| 10 | n = 108 (SE 0,04); tabela SE → 430 / 191 / 108 / 69 / 18 | `dados/desenho_validacao.json` | confere |
| 11 | Alocação 12 / 19 / 33 / 28 / 16 | idem | confere |
| 12 | 44 pontos em borda (40,7%); 530.035 pixels puros de 953.046 | idem | confere |
| 13 | Exemplo fictício: 0,852 ± 0,067; UA 0,545; PA 0,374; 60,3 km² (34,8–85,8) | saída do `06` que rodei | confere |
| 14 | Variante "não sei = erro": 0,853 ± 0,063; UA 0,500; PA 0,369; 56,1 km² (32,0–80,3) | idem | confere |
| 15 | Controles do classificador: 0,760 / 0,193 (embaralhado) / 0,310 (regra boba) | `dados/controle.json` + rerun do `07` | confere |
| 16 | Estimador: média 49,2 km² para verdade 49,1 (viés +0,07%), cobertura do IC95 94,0%; contagem crua −15,7% | idem | confere |
| 17 | Controle de borda: puros 26,2 km² (−2,7%), acurácia 1,000 (+3,8 p.p.), cobertura 0%; todo o estrato 27,0 km² (+0,2%), 0,967 (+0,5 p.p.), cobertura 90% | idem | confere |
| 18 | 58 e 48 cenas; 19 bandas; grade 954×999; 62,7 MB; página de 2,6 MB | `dados/mosaico_meta.json`, saída do `08`, `ls` | confere (ver ressalva 7.4 sobre o significado dos 62,7 MB) |

Detalhe que merece registro: os números "antes da correção" da tabela do §14.1 do relatório
(0,900 ± 0,060; UA 0,833; PA 0,526; 65,6 km²) **não são reproduzíveis hoje** — a versão com filtro de
borda não existe mais no código e a pasta não é um repositório git, então não há como recuperá-la.
Ou seja: essa coluna é história, não resultado. Ver seção 8.

---

## 3. Testes

**Não existe suíte de testes** (nenhum arquivo `test_*.py`, nenhum `pytest`/`unittest` na pasta). Os
testes automatizados do projeto são os `assert` dentro do `07_controle.py` e a checagem cega dentro
do `05`. Rodei ambos:

| Teste | Onde | Resultado |
|---|---|---|
| Classificador ganha da regra boba e do rótulo embaralhado | `07:81` | **passou** (0,760 > 0,310 e > 0,193) |
| Estimador de área sem viés e com IC95 cobrindo ~95% | `07:128` | **passou** (viés +0,07%; cobertura 94,0%) |
| Sorteio sem filtro de borda não enviesado | `07:240` | **passou** (+0,2% de viés; +0,5 p.p.) |
| Mapa 100% certo → área ajustada = área crua | `07:256-257` | **passou** (41,4 = 41,4; acurácia 1,000) |
| Conferência cega (0 ocorrência de `classe_mapa`/`estrato`; chaves do `PONTOS`) | `05:344-352` | **passou** |
| Forma dos blocos e grade dos rótulos | `02:95, 02:214` | **não verificado** (script não roda sem Earth Engine) |

Os controles são bons de verdade: o de rótulos embaralhados e o de "mapa 100% certo" são testes que
falhariam se o código estivesse errado, e o de borda mostra a diferença de método com verdade
conhecida. É o ponto mais forte do trabalho.

**Ressalva sobre o controle de borda:** o número "IC95 cobre a verdade em **0%**" é o resultado de um
cenário sintético em que, por construção, os pixels "puros" do estrato eucalipto são **100%**
eucalipto de verdade (o próprio script imprime `0.973 (todos os pixels) x 1.000 (so pixels puros)`).
Ou seja: o filtro elimina justamente os pixels que erravam, e o estimador degenera na contagem crua.
O **mecanismo** é real e está bem demonstrado; a **magnitude** (0% e +3,8 p.p.) é de cenário
artificial e não deve ser lida como "sempre 0%". O relatório diz que é sintético, mas o número em
negrito no §6 e no §14.1 pode ser lido como lei geral. Ver item 7.6.

---

## 4. Método — o que é sólido e o que não é

### 4.1 O que está sólido

- **A amostragem voltou a ser probabilística.** Sorteio uniforme em todos os pixels do estrato,
  com probabilidade de inclusão conhecida e não nula (`05:96-100`). É o que o estimador de Olofsson
  exige, e o controle de borda prova que a diferença importa.
- **As fórmulas do estimador estão corretas.** Conferi `codigo/olofsson.py` linha a linha contra
  Olofsson et al. (2014): `p_ij = W_i·n_ij/n_i`; acurácia global `OA = Σ W_i·a_i`; erro padrão
  `√(Σ W_i²·a_i(1−a_i)/(n_i−1))`; variância da área `Â²·Σ W_i²·(n_ij/n_i)(1−n_ij/n_i)/(n_i−1)`.
  Bate com as equações do artigo (a do tamanho da amostra, a da variância da acurácia global e a
  da variância da área ajustada). A "convenção: referência=1 é a classe alvo" está
  documentada e o caso degenerado "mapa 100% certo" fecha com 41,4 = 41,4 km².
- **A comparação aleatório × blocos não é injusta.** Esta era a minha principal suspeita: os dois
  protocolos são avaliados em conjuntos de teste **diferentes** (e com composição diferente — 9,08%
  de eucalipto no teste aleatório contra 10,69% no teste por blocos), então a diferença de 0,084
  poderia ser artefato da composição. **Testei:** retreinei os dois modelos com N=3.200 (a mesma
  lógica de sorteio do `03`) e avaliei os dois em **ambos** os conjuntos de teste:
  - modelo treinado no protocolo aleatório: F1 = 0,691 no teste aleatório e 0,692 no teste por blocos;
  - modelo treinado no protocolo por blocos: F1 = 0,696 no teste aleatório e 0,607 no teste por blocos.
  Ou seja, medido no **mesmo** conjunto de teste, a diferença é **+0,085** (0,692 contra 0,607) —
  praticamente a mesma dos +0,084 do relatório. **A conclusão do §4 do relatório se sustenta** e o
  número está certo. (Bônus: o modelo por blocos é *melhor* no teste aleatório — 0,696 contra 0,691 —
  o que confirma que é o **conjunto de teste** que é permissivo, não o treinamento.)
- **O controle de vazamento/train-test do `07` é honesto** e a lição foi aprendida (§7 do relatório).
- **A transparência sobre o CSV fictício é exemplar** e a página é de fato cega.

### 4.2 Problemas de método

**(a) A referência "de verdade" vem da mesma imagem de 10 m que o mapa.**
As fotos da conferência saem de `dados/rgb_10m.tif`, que é a cor verdadeira do **mesmo mosaico
Sentinel-2** usado para treinar e para classificar (a seca de 2024, `02:222`). A pesquisadora vai
julgar eucalipto × não eucalipto **na mesma imagem de 10 m** que o modelo usou. Consequência
metodológica que o relatório não diz: **qualquer confusão que a imagem de 10 m não consegue
separar não será detectada pela validação** — eucalipto jovem × pastagem, dossel fechado × mata
nativa, resto de corte × capim. Um erro desses é "verdadeiro" para quem olha a foto e para o
modelo, ao mesmo tempo, e a validação vai dar concordância alta sem detectar o erro. O §8 do
relatório lista "não usei imagem de alta resolução" como limitação **logística** ("exige conta
e/ou crédito"), e não como limitação **do alcance da validação**. Isso é a mesma falha de raciocínio
que o §3 do relatório critica no MapBiomas, aplicada à própria ferramenta. *(item 7.1)*

**(b) O `06_acuracia.py` quebra justamente no cenário que a correção 1 criou.**
A opção "não dá para saber" existe porque os 44 pontos de borda são difíceis. Se a pesquisadora
marcar "não sei" nos 12 pontos do estrato eucalipto (o estrato mais difícil: 12 pontos é pouco, e a
classe alvo é justamente a que o modelo erra), o `06` **morre com traceback** e não produz nada:

```
(politica excluir) sem pontos em: ['eucalipto']
...
ValueError: estrato sem nenhum ponto: [0] - o desenho estratificado exige pelo menos 1 ponto em cada estrato
```

O motivo é a ordem em `06_acuracia.py:112-113`: `res_excluir` é calculado primeiro e a exceção
sobe; a política alternativa ("não sei" = erro), que resolveria o caso, nunca chega a ser rodada.
O `README.md` diz "o script avisa e o resultado fica mais incerto" — na verdade ele para. *(item 7.2)*

**(c) A recomendação "400–800 amostras por classe" é justificada só pela curva otimista.**
O §4 diz: "800 por classe compra a maior parte do que 3.200 compraria (0,630 vs 0,691), com um
quarto do esforço". Esses dois números são da curva **aleatória**, que o próprio relatório mostra ser
inflada. Na curva **por blocos** os mesmos valores são 0,569 e 0,607 (ganhos por dobrada depois de
800: +0,023 e +0,015, contra +0,034 e +0,027). A **recomendação não muda** (na curva honesta a curva
achata ainda mais cedo, o que reforça "400–800"), mas a frase usa números que a pesquisadora não
deve usar como referência para o próprio trabalho. *(item 7.3)*

**(d) Pequeno vazamento entre treino do mapa e amostra de validação.**
O mapa final (`04`) treina em 8.000 pixels sorteados de **toda** a área, e os 108 pontos de
validação também saem de toda a área — sem exclusão dos pixels de treino. Em média, ~1 dos 108
pontos é pixel de treino (8.000/953.046 = 0,84%), onde o mapa tende a acertar mais. O efeito
esperado é de menos de 1 ponto, mas o desenho não é estritamente independente. *(item 7.7)*

**(e) A política padrão de "não sei" (excluir) enviesa a área — e é a que está em destaque.**
O §5.4 e o §14.3 colocam em destaque a linha "excluir" (60,3 km²). Excluir os "não sei" tira
pontos do estrato em que eles mais importam (borda, classe rara) e pode empurrar a área ajustada
para o lado errado. O `06` já avisa isso no código e o `README` menciona; o `RELATORIO.md`, onde os
números em destaque aparecem, não. *(item 7.8)*

---

## 5. Honestidade — o que está certo e o que ficou de fora

**Está certo e acima da média:**

- O relatório separa, em todo o texto, "acurácia do script" de "acurácia do mapa", e marca o CSV
  fictício em todos os lugares (arquivo, saída do script, JSON, título da figura).
- O §3 assume explicitamente que a concordância com o MapBiomas **não é acurácia**, e explica por quê.
- O §6 dá controles que poderiam ter sido omitidos; o §7 lista os próprios erros, inclusive o
  vazamento de treino/teste.
- As ressalvas honestas existem onde costumam faltar: "não conferida por script" (nº de chamadas do
  Earth Engine), "tempos observados à mão", "não avaliei o classificador com dado de campo".
- A seção "Onde a IA generativa ajudou e onde não ajuda" é Specificamente honesta sobre o que a IA
  não pode fazer (assinar validação, decidir metodologia).

**O que ficou de fora ou foi exagerado:**

1. **A figura do mapa engana** (item 7.4): o `RELATORIO.md` §5.1 usa `figuras/mapa_area.png` como
   evidência ("os talhões de eucalipto do mapa caem sobre os talhões do MapBiomas na figura") e a
   figura está com as cores trocadas. A leitura do eucalipto (marrom nos dois painéis) continua
   correta, mas o leitor não consegue ler as outras classes — vai ver um buraco branco no meio do
   mapa e vai ler a legenda errado.
2. **"Total baixado do Earth Engine: 62,7 MB"** (§2 e §12) — o número é o **tamanho dos arquivos
   locais comprimidos** (`mosaico_s2.tif` 50,7 MB + `rgb_10m.tif` 11,8 MB + `rotulos_mb.tif` 0,15 MB,
   todos com `compress="deflate"`), não o volume transferido. O bruto baixado em 22 blocos foi
   da ordem de 85–90 MB. O limite de 1 GB foi respeitado com folga, mas o número está rotulado
   errado.
3. **"Todos os números deste relatório saem de `python codigo/08_resumo.py`"** (§11) — não é
   literalmente verdade: o `08` não imprime os priors U_h (0,61 / 0,84 / 0,79 / 0,82 / 0,64), a
   tabela de composição do recorte, o nº de treino por classe (1.600), os dois municípios seguintes
   (Niquelândia 99,2 e Catalão 96,9) nem o centro do recorte. Todos estão em JSONs do `dados/`, então
   são verificáveis — mas a frase exagera, e a correção 3 pedia exatamente que o `08` imprimisse
   todos os números citados.
4. **O alcance da validação** (§4.2(a) acima): o relatório diz que a validação "de verdade"
   responde à pergunta, e é verdade em relação à referência do MapBiomas, mas **não** em relação ao
   que o Sentinel-2 de 10 m consegue mostrar. Falta essa frase.
5. A tabela de composição do recorte (§1) parece completa, mas omite 5 classes que somam 2,5%
   (savânica, outras lavouras temporárias, cana, campestre, outras áreas não vegetadas).

---

## 6. Utilidade para a pesquisadora

**O material responde às duas perguntas?** Sim, e responde bem.

- *"Quantas amostras usar?"* — resposta honesta e transferível: não existe número universal, o que
  existe é a curva, e o procedimento é "rode a curva com a sua referência e pare quando o ganho por
  dobrada não pagar o custo". Mais o achado que ninguém dá de graça: **treinar e testar com pixels
  vizinhos infla o resultado em ~0,08 de F1**. Isso é aplicável ao trabalho dela, que provavelmente
  tem o mesmo desenho de amostragem.
- *"Como conferir se a classificação está satisfatória?"* — resposta completa e, o mais importante,
  **operacional**: a página de conferência existe, é cega, funciona offline, exporta CSV, e o script
  dá acurácia do usuário, do produtor e **área ajustada com IC95**, que é a métrica que responde à
  pergunta do produto (área de eucalipto).

**O que falta / o que eu apertaria antes de entregar à pesquisadora:**

1. Desenhar o marcador na imagem (item 7.9) — é barato e é o que faz a "regra de rotulagem"
   funcionar na prática.
2. Consertar o crash do `06` (item 7.2) — é o caminho que ela vai Percorrer em 5 minutos.
3. Corrigir as cores da figura (item 7.4) — ela vai mostrar essa figura para o orientador.
4. Recomendar, em uma linha, que uma subamostra de 20–30 pontos seja conferida em imagem de alta
   resolução (Google Earth, link que a página já dá) **só para checar se o Sentinel-2 de 10 m
   mostra eucalipto** — isso não substitui a validação, mas protege contra o item 4.2(a).
5. Um parágrafo honesto sobre o que a validação **não** detecta.

**Não falta:** as entregas pedidas no `PEDIDO.md` estão todas lá (curva de aprendizado, PNG do
mapa, página de conferência, script de acurácia, 10 referências com DOI conferido, `README.md`,
`CLAUDE.md` + `AGENTS.md`, `RELATORIO.md` com a seção final pedida).

---

## 7. Problemas encontrados (gravidade · evidência · o que fazer)

Nenhum problema **crítico**: não achei número errado, vazamento que invalide conclusão, nem
afirmação que os dados não sustentem.

### 7.1 · Importante · A referência humana vem da mesma imagem de 10 m do mapa

**Evidência.** `codigo/02_baixar_imagens.py:222` gera `dados/rgb_10m.tif` a partir de
`img_seca` — a mesma mediana Sentinel-2 de 2024 que alimenta as 19 bandas de `mosaico_s2.tif`; a
conferência usa recortes desse arquivo (`05:117-131`). O `RELATORIO.md` §8 menciona a ausência de
imagem de alta resolução só como questão de custo/crédito; §10 fala de "decidir o que é eucalipto
no campo", mas sem dizer que a conferência **não** mede essa decisão.

**Por que importa.** Erros de confusão que a imagem de 10 m não separa (eucalipto jovem × pastagem
seca, dossel × mata) são indistinguíveis para o modelo **e** para quem olha a foto: a validação vai
dar concordância alta sem detectar o erro. A frase do §3 ("só o dado de referência marcado por uma
pessoa responde à pergunta") precisa de uma ressalva: responde à pergunta *dentro do que o
Sentinel-2 de 10 m mostra*.

**O que fazer.** Acrescentar ao §5.2 e ao §8: (a) a conferência é "verdade relativa ao Sentinel-2 de
10 m"; (b) é por isso que "não dá para saber" existe e por que o texto manda não forçar palpite;
(c) recomendar que, para 20–30 dos 108 pontos, a pesquisadora confira **só se há eucalipto** em
imagem de alta resolução (o link da página já leva ao Google Maps na coordenada) e anote em
separado — sem usar isso como marcação, apenas como checagem de sanidade.

### 7.2 · Importante · `06_acuracia.py` quebra (sem saída) quando um estrato fica sem ponto

**Evidência.** Reproduzido: CSV com os 12 pontos do estrato eucalipto marcados como "nao_sei" →
`06_acuracia.py:112` → `ValueError: estrato sem nenhum ponto: [0]`, sem produzir resultado e sem
rodar a política alternativa ("não sei" = não eucalipto), que resolveria o caso
(`06_acuracia.py:97-113` calcula `res_excluir` antes de `res_erro`).

**Por que importa.** É exatamente o cenário previsto para os 44 pontos de borda e para a classe
alvo (12 pontos). A pesquisadora perde a sessão de marcação por causa de um traceback, e o
`README.md` promete um aviso, não uma queda.

**O que fazer.** Envolver a política "excluir" em `try/except ValueError`; quando faltar estrato,
imprimir mensagem clara ("marque ao menos 1 ponto do estrato X, ou rode com `--nao-sei erro`") e
continuar com a política "erro", que é sempre calculável. Registrar o caso no `RELATORIO.md` §7.

### 7.3 · Importante · `figuras/mapa_area.png` desenha 3 das 5 classes com a cor errada

**Evidência.** `codigo/04_mapa.py:107-108` monta `ListedColormap` com **6** cores (5 classes +
branco) e `imshow(..., vmin=-0.5, vmax=n_classes-0.5)` (linhas 116 e 122). Com 6 cores no
colormap e 5 valores, o matplotlib escolhe o índice `int(x·6)`:

| valor da classe | deveria ser | sai como |
|---|---|---|
| 0 eucalipto | `#7a5900` | `#7a5900` ✔ |
| 1 floresta | `#1f8a4c` | `#1f8a4c` ✔ |
| 2 **pastagem** | `#ffd966` | **`#e974ed`** (a cor da agricultura) ✘ |
| 3 **agricultura** | `#e974ed` | **`#9c9c9c`** (a cor do mosaico/água) ✘ |
| 4 **mosaico/água** | `#9c9c9c` | **`#ffffff`** (branco = fundo/nodata) ✘ |

Confirmei no PNG final por contagem de cores: **zero** pixels de `#ffd966` (amarelo da pastagem) nos
dois painéis, 84.712 px magenta (que é a pastagem: 31,03% da área), 74.760 px cinza (agricultura:
27,34%) e ~40 mil px brancos dentro do mapa (mosaico/água: 14,85%) — ou seja, **um buraco branco no
meio da área** que parece falta de dado. A legenda (`04:132`) usa `c.CORES` direto, então ela está
correta e não bate com o mapa.

**Por que importa.** É uma entrega obrigatória (`PEDIDO.md`: "o mapa da área de teste (PNG)") e o
`RELATORIO.md` §5.1 a usa como evidência de que "o mapa não está deslocado nem invertido". Os
**números** do mapa não mudam (áreas e concordância vêm do array, não da cor), e a leitura do
eucalipto — a única que o §5.1 usa — continua correta, porque a cor do eucalipto (índice 0) está
certa nos dois painéis. Mas quem ler a figura vai interpretar 3 classes errado.

**O que fazer.** `cmap = ListedColormap([c.CORES[n] for n in c.CLASSES])` (5 cores) mantendo
`cmap.set_bad("white")` para o nodata, ou usar `BoundaryNorm([-0.5, .5, 1.5, 2.5, 3.5, 4.5], n)`.
Rerodar o `04` e olhar a figura antes de entregar.

### 7.4 · Menor · "62,7 MB baixado do Earth Engine" é o tamanho dos arquivos locais comprimidos

**Evidência.** `08_resumo.py:28-33` soma `mosaico_s2.tif` + `rotulos_mb.tif` + `rgb_10m.tif`
(50,7 + 0,15 + 11,8 MB), todos gravados com `compress="deflate"` (`02:117`). O volume realmente
transferido em 22 blocos foi maior (o bruto de 19 bandas float32 954×999 é ~72 MB).

**O que fazer.** Escrever "62,7 MB em disco (arquivos comprimidos)" ou registrar o total
transferido no log do `02`. O limite de 1 GB foi respeitado com folga nos dois casos.

### 7.5 · Menor · O `08_resumo.py` ainda não imprime todos os números que o relatório cita

**Evidência.** A §11 do `RELATORIO.md` afirma: "Todos os números deste relatório saem de
`python codigo/08_resumo.py`". O `08` não imprime: os priors U_h (0,61 / 0,84 / 0,79 / 0,82 / 0,64),
a tabela de composição do recorte (§1), o treino por classe (1.600 em §5.1), Niquelândia 99,2 e
Catalão 96,9 (§1) e o centro do recorte (-51,170 / -18,001). Todos existem em `dados/recorte.json`,
`dados/mapa_meta.json` e `dados/silvicultura_por_municipio.csv` — são verificáveis, mas não saem do
`08`, que era o pedido da correção 3 ("para a conferência ser direta").

**O que fazer.** Acrescentar ~8 linhas ao `08` para imprimir esses números, ou suavizar a frase da
§11 para "todos os números saem de um script desta pasta; o `08` imprime a tabela principal".

### 7.6 · Menor · "IC95 cobre a verdade em 0%" é número de cenário sintético extremo

**Evidência.** `07_controle.py:136-166`: no cenário, a fração eucalipto-no-estrato é 0,973 para
todos os pixels e **1,000** para os pixels puros — ou seja, o filtro de borda elimina *todos* os
erros por construção, e o estimador vira a contagem crua (o próprio script imprime
`so pixels puros: area 26.2 km2`, idêntico à `area_crua_mapa_km2` = 26.1712).

**Por que importa.** O mecanismo é real e importante; o "0%" em negrito no §6 e no §14.1 pode ser
lido como lei. No mapa real o efeito será menor (os pixels puros não são 100% corretos), embora na
mesma direção.

**O que fazer.** Reescrever a frase como "no cenário sintético, o filtro de borda eliminou todos os
erros do estrato e o intervalo passou a cobrir a verdade em 0% das repetições; o mecanismo é o que
importa: o estimador vira a contagem crua".

### 7.7 · Menor · Os 108 pontos de validação não excluem os pixels de treino do mapa

**Evidência.** `04_mapa.py:44-48` treina em 8.000 pixels sorteados de toda a área;
`05_desenho_validacao.py:96-100` sorteia a validação em toda a área, sem exclusão.

**Por que importa.** Em média ~1 dos 108 pontos (0,84%) é pixel de treino, onde o mapa tende a
acertar mais. O efeito esperado é de menos de 1 ponto, mas o desenho não é estritamente independente
e o `RELATORIO.md` §3 fala de "vazamento" em outro contexto sem tratar este.

**O que fazer.** Registrar em uma linha no §5.2 que o mapa final foi treinado em pixels da própria
área (não há holdout geográfico no mapa final), que o impacto esperado é < 1 ponto dos 108, e que
quem quiser zerar isso treina o mapa final com os pixels de validação excluídos.

### 7.8 · Menor · A política que pode enviesar (excluir "não sei") é a que está em destaque

**Evidência.** `06_acuracia.py:99-103` (política padrão) e o §5.4 / §14.3 do relatório, que destacam
a linha "excluir (padrão) — 60,3 km² (34,8–85,8)".

**Por que importa.** Excluir os "não sei" tira pontos — sobretudo do estrato raro e de borda — e
pode empurrar a área ajustada para o lado errado. O `06` avisa no docstring e o `README` menciona;
o `RELATORIO.md`, onde o número aparece em destaque, não.

**O que fazer.** Acrescentar ao §5.4: "a linha em destaque é a política 'excluir'; ela pode enviesar
a área para baixo porque os 'não sei' se concentram nas bordas; por isso o número em destaque deve
ser lido junto com a política 'não sei = erro' (56,1 km²), que é mais conservadora".

### 7.9 · Menor · A página manda procurar um círculo que não existe

**Evidência.** `conferencia/index.html`, linha 48: "o ponto marca o centro de um pixel de 20 m
(**o circulo pequeno no meio da imagem**)". Busquei no HTML inteiro por `circle`, `circulo`,
`border-radius:50%`, `::after`, `::before`, `position:absolute`: **nenhuma ocorrência** — não há
nenhuma marca desenhada sobre a imagem. (Conferi que o recorte está de fato centrado no ponto:
extraí as imagens base64 e comparei o RGB do pixel geográfico com o centro do recorte — diferença
média de 3–9 valores, só JPEG.)

**Por que importa.** A regra de rotulagem que a correção 1 pediu depende de o ponto ser localizável
na imagem. Na imagem de detalhe (700 m em 240 px), um pixel de 20 m tem ~7 px: dá para ver, mas sem
marcador é fácil errar o centro — e errar o centro significa marcar o pixel errado.

**O que fazer.** Ou desenhar o marcador (um `div`/SVG com `border-radius:50%` sobre a imagem, ou um
retângulo de 20 m), ou trocar o texto por "o ponto está no **centro** da imagem".

### 7.10 · Menor · "Pixel de borda" não está definido no texto

**Evidência.** No código, "borda" = "a vizinhança 3×3 não é toda da mesma classe"
(`05:107-110`), o que inclui pixels que ainda são 8/9 da sua classe. O número em destaque é 44 de
108 (40,7%). O `README.md` diz "44 dos 108 pontos caem em borda de talhão" sem definir; o
`RELATORIO.md` §14.1 define ("530.035 dos 953.046 pixels"), mas o §5.2 e o `CLAUDE.md` não.

**O que fazer.** Definir em uma linha no §5.2 e no `README.md`: "borda = vizinhança 3×3 (60 m)
contém outra classe".

### 7.11 · Menor · `CLAUDE.md` expõe o nome de usuário do Windows

**Evidência.** `CLAUDE.md:14` — "Windows, Python 3.14 em
`<python local>`". É o único dado pessoal em todo o
conjunto (busquei e-mail/nome em todos os `.md`, `.py`, `.csv` e `.json`: só essa ocorrência).

**O que fazer.** Trocar por `C:\Users\<usuario>\AppData\Local\Python\pythoncore-3.14-64` ou só
"Python 3.14 (instalação local do usuário)". A regra 7 das `REGRAS-COMUNS.md` pede saídas sem dado
pessoal.

### 7.12 · Menor · A chave da conferência cega fica na mesma pasta do material da pesquisadora

**Evidência.** `dados/pontos_chave.csv` (com estrato e classe do mapa) está ao lado de
`conferencia/index.html`, e o `README.md` só pede "Não abra antes de marcar".

**Por que importa.** A "cegueira" é garantida pelo código, não pelo acesso: quem abrir o CSV — ou o
`git diff`/o gerenciador de arquivos — quebra a cegueira. Como os ids estão embaralhados, nem
mesmo a ordem entrega o estrato; mas o conteúdo do arquivo entrega.

**O que fazer.** Gerar a chave no momento do cálculo (o `06` já sabe derivá-la do `mapa_predito.tif`
+ o sorteio, se o `05` for chamado com a mesma semente), ou entregar a chave em arquivo separado,
fora da pasta que vai para a pesquisadora.

---

## 8. O que não foi verificado

1. **Os números "antes da correção"** da tabela do §14.1 do relatório (0,900 ± 0,060; UA 0,833;
   PA 0,526; 65,6 km² (42,9–88,3)) e a afirmação de que a versão anterior do `06` dava 62,9 km²
   (41,7–84,1). **Não verificado:** a versão com filtro de borda não existe mais no código e a pasta
   não é um repositório git, então não há histórico para reproduzir. São afirmações de quem fez as
   correções, sem forma de checagem independente hoje.
2. **O passo 01 e o passo 02** (escolha da área e download do mosaico). **Não verificado** por
   executá-los (chamam o Earth Engine / baixam dados, vedado pelo pedido). Conferi apenas: o código,
   a saída de `dados/recorte.json`, `dados/silvicultura_por_municipio.csv`,
   `dados/composicao_recorte.csv`, `dados/mosaico_meta.json` e o tamanho/forma dos GeoTIFF.
   Consequentemente, **não verificado** o número de chamadas ao Earth Engine (~30) e os tempos de
   execução citados no §12 — o próprio relatório já os marca como "não conferidos".
3. **A mosaicagem em si** (58 e 48 cenas, máscara Cloud Score+, medianas). Só conferi o que o
   `mosaico_meta.json` registra; não refiz a consulta ao Sentinel-2.
4. **Se a "paisagem sintética" do `07` representa bem o caso real.** O controle é internamente
   consistente e o mecanismo está certo, mas a magnitude do viés depende de como a erosão de borda
   foi simulada (`prob_flip` 0,85 / 0,40, `07:159-161`) — parâmetro escolhido pelo autor.
5. **A usability real da página por uma pessoa** (tempo de interpretação por ponto, legibilidade do
   JPEG de 240 px, se a pessoa entende "pixel de 20 m"). Conferi o HTML e as imagens
   programaticamente, não a experiência de uso.

---

## 9. Conclusão

O trabalho está em boa forma e o que a correção de 31/10 tinha por objetivo **está feito e é
verificável**: a amostragem voltou a ser probabilística (com o efeito medido contra verdade
conhecida), a conferência está cega de verdade (verificado por busca e por parsing do HTML), os
números foram atualizados e são **reproduzíveis byte a byte** ao rodar os scripts. Os controles do
`07` são o ponto mais forte do conjunto e passam.

O que ainda impede entregar sem ressalva são três itens: as **cores trocadas na figura do mapa**
(entrega obrigatória, engana quem lê), o **crash do `06`** no cenário de "não sei" (que é o caminho
que a pesquisadora vai percorrer) e a **falta da ressalva sobre o alcance da validação** (a
referência vem da mesma imagem de 10 m do mapa). Os demais são de acabamento e estão listados na
seção 7 com a correção sugerida.

Nenhum número do relatório foi encontrado errado, e nenhuma conclusão me parece maior do que os
dados permitem.
