# Correções pedidas após a conferência (31/10/2026)

Leia este arquivo inteiro antes de mexer. As regras de `REGRAS-COMUNS.md` continuam valendo. Ao terminar, acrescente ao `RELATORIO.md` uma seção **"Correções de 31/10"** dizendo o que mudou, os números antes e depois, e de qual script cada número novo saiu.

## 1. Erro de método: o sorteio da validação exclui as bordas (corrigir)
`codigo/05_desenho_validacao.py` só sorteia pixels "puros" (vizinhança 3×3 da mesma classe). Isso quebra a amostragem probabilística do Olofsson: os pixels de borda, onde o mapa mais erra, ficam com probabilidade zero de entrar. A acurácia estimada fica otimista e a área ajustada fica enviesada.
- Sorteie em **todos** os pixels de cada estrato (probabilidade de inclusão conhecida e não nula para todos).
- A dificuldade de interpretar ponto de borda se resolve com a opção "não dá para saber" e com a regra de rotulagem (rótulo do pixel de 20 m pelo que ocupa a maior parte dele), não excluindo pixels. Escreva essa regra na página e no README.
- **Mostre o efeito:** no teste do estimador com verdade conhecida (controle do `07`), compare o viés da acurácia e da área entre "sorteio só em pixels puros" e "sorteio em todo o estrato". Se o sorteio só em puros tiver viés, isso vira um achado do relatório.

## 2. Conferência às cegas de verdade (corrigir)
Hoje a página não mostra a classe do mapa na tela, mas `classe_mapa` e `estrato` estão dentro do JavaScript da página e no `conferencia/pontos.csv`. Quem abrir o CSV ou o código vê o palpite do mapa.
- A página e o CSV que vão para a pesquisadora devem ter só `id`, `lon`, `lat` e as imagens.
- A chave com estrato e classe do mapa fica em `dados/` (por exemplo `dados/pontos_chave.csv`) e é lida pelo `06_acuracia.py`, que junta pelo `id`.
- Confira com uma busca no `index.html` final que não sobrou `classe_mapa`, `estrato` nem nome de classe associado a ponto.

## 3. Números do relatório desatualizados (corrigir)
O relatório diz área ajustada de 65,6 km² (IC95 42,9–88,3) no exemplo fictício, mas `python codigo/06_acuracia.py conferencia/marcacoes_FICTICIO.csv` dá hoje 62,9 km² (IC95 41,7–84,1). Depois das correções 1 e 2, **rode tudo de novo na ordem** (05 → 06 → 07 → 08) e atualize **todos** os números do relatório e do README a partir das saídas. Faça o `08_resumo.py` imprimir todos os números citados, para a conferência ser direta.

## 4. Cuidado
- Mantenha o CSV fictício claramente marcado como fictício.
- Não mude a curva de aprendizado (passo 03) nem o mapa (passo 04): estão conferidos.
