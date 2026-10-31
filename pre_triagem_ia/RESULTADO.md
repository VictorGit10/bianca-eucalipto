# A IA consegue conferir o mapa? Teste de pré-triagem com um modelo com visão (31/10/2026)

Resposta curta à pergunta do formulário ("Talvez para conferir se a classificação é satisfatória? Isso é possível?"): **um modelo com visão ajuda a decidir onde olhar com mais cuidado, mas não serve como referência**, e a confiança que ele declara não indica se acertou.

## Como foi feito
- 30 dos 108 recortes da página de conferência (Sentinel-2 de 10 m, cor verdadeira, seca de 2024, ~700 m de lado): todos os 12 pontos que o mapa chama de eucalipto, todos os 8 que o MapBiomas chama de silvicultura (7 em comum) e 17 outros sorteados. 11 dos 30 são de borda.
- Os nomes foram trocados (img_01 a img_30) e embaralhados; o modelo não viu nenhuma classe.
- Modelo: Gemini 3.8 Flash (Medium), pelo Antigravity. Pedido em `PEDIDO-AO-MODELO.md`. Resposta: eucalipto / não eucalipto / não sei, com confiança e motivo.
- Comparação contra o MapBiomas 2024 (que também **não** é verdade de campo) e contra o mapa do Random Forest. A tabela por ponto está em `dados/chave/pre_triagem_ia.csv` (na pasta da chave, para não revelar classes antes da marcação).

## Resultado
| | MapBiomas = silvicultura (8) | MapBiomas = outra classe (22) |
|---|---|---|
| Gemini: eucalipto | 4 | 1 |
| Gemini: não eucalipto | 4 | 15 |
| Gemini: não sei | 0 | 6 |

- Dos 4 pontos de silvicultura que o modelo chamou de "pastagem" ou "agricultura", todos vieram com confiança 0,95. Pelo menos um parece talhão colhido na imagem da seca: o modelo descreve o que vê, não o uso da terra.
- O único "eucalipto" errado (mata nativa segundo o MapBiomas e o mapa) é um bloco escuro e homogêneo que, a 10 m, não se distingue de um talhão adulto. Também com 0,95.
- Os 6 "não sei" caíram em estradas internas, bordas de talhão e plantio jovem. É justamente onde a pessoa deve abrir a imagem de alta resolução.
- Em 3 pontos em que o mapa diz eucalipto e o MapBiomas diz pastagem, o modelo concordou com o MapBiomas.

## O que isso quer dizer para a validação
1. Não usar a resposta do modelo como rótulo de referência: com 30 pontos, errou 5 com confiança máxima.
2. Uso que faz sentido: ordenar os pontos para a marcação humana (os "não sei" e as divergências entre modelo e mapa primeiro, com alta resolução e outra data), e escrever o motivo de cada decisão.
3. Isso vale para este teste (30 pontos, um município, uma imagem de 10 m). Com imagem de alta resolução o resultado pode ser outro; não foi testado.
