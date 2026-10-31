# Pré-triagem visual de pontos de validação

Nesta pasta há 30 imagens (img_01.jpg a img_30.jpg). Cada uma é um recorte Sentinel-2 em cor verdadeira, 10 m de resolução, de cerca de 700 m × 700 m, da estação seca de 2024, no município de Rio Verde (GO, Cerrado). O ponto a classificar é o **pixel do centro da imagem** (um quadrado de ~20 m).

Para cada imagem, olhe a imagem de fato e diga se o centro é plantio de **eucalipto** (silvicultura: talhões geométricos, textura homogênea, verde-escuro), **nao_eucalipto** (floresta nativa, pastagem, agricultura, água, solo, área urbana) ou **nao_sei** (resolução insuficiente, borda entre classes, plantio jovem ou recém-colhido).

Escreva o arquivo `resultado.csv` nesta pasta com as colunas:
`img,classe,confianca,motivo`
- classe: eucalipto | nao_eucalipto | nao_sei
- confianca: 0 a 1
- motivo: até 15 palavras sobre o que você viu.

Não invente: se não der para decidir, use nao_sei.
