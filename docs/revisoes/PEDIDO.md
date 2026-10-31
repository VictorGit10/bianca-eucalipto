# Pedido — quantas amostras para o Random Forest e como saber se o mapa de eucalipto está bom

Leia antes `REGRAS-COMUNS.md` e `CONTEXTO.md` (os dois estão nesta pasta).

## O que queremos
A pesquisadora já usa Random Forest (que é aprendizado de máquina) e não sabe onde entraria "a IA". Ela tem duas dúvidas reais: **quantas amostras usar** e **como conferir se a classificação está satisfatória**. Queremos responder as duas **com um teste executado** numa área real de Goiás, e mostrar onde a IA generativa ajuda (escrever e revisar o código, desenhar a amostragem, montar a ferramenta de conferência) e onde ela **não** substitui a pessoa (a validação com dado de referência).

## Passos
1. **Área de teste.** Use a Coleção 11 do MapBiomas (`projects/mapbiomas-public/assets/brazil/lulc/collection11/...`, classe 9 = silvicultura) para achar um município ou recorte de Goiás com bastante silvicultura. Mantenha a área pequena (da ordem de um município). Registre a escolha.
2. **Imagem.** Mosaico Sentinel-2 SR harmonizado de um ano recente (estação seca e chuvosa, se couber), com máscara de nuvem (Cloud Score+), bandas e alguns índices. Earth Engine com `ee.Initialize(project='SEU-PROJETO-EARTH-ENGINE')`.
3. **Rótulos provisórios.** Use o MapBiomas só para **sortear** amostras de treino (eucalipto × outras classes). Escreva claramente que concordar com o MapBiomas **não** é acurácia: é só uma referência provisória para o teste.
4. **Curva de aprendizado (a dúvida das amostras).** Treine o Random Forest com N amostras por classe ∈ {25, 50, 100, 200, 400, 800} (ajuste se ficar pesado), 5 repetições por N, avaliando sempre no **mesmo conjunto independente**. Gere a figura: F1 / acurácia do eucalipto × N. Explique onde a curva estabiliza e que isso depende da área, das classes e da confusão entre elas (não há "número ideal" universal). Se der, mostre também o efeito de amostras espacialmente próximas (treino e teste vizinhos inflam a acurácia): compare sorteio aleatório × separação por blocos espaciais.
5. **Validação de verdade (a dúvida de "conferir").** Siga as boas práticas de Olofsson et al. (2014): amostra aleatória estratificada pelo mapa, tamanho da amostra calculado, matriz de confusão, acurácia do usuário e do produtor, **área estimada ajustada com intervalo de confiança**. Monte:
   - um sorteio de ~100 pontos de validação a partir do mapa produzido;
   - para cada ponto, um recorte de imagem (Sentinel-2 cor verdadeira, e um link para imagem de alta resolução, ex.: Google Maps nas coordenadas);
   - uma **página HTML única, offline**, onde a pessoa marca "eucalipto / não eucalipto / não sei" em cada ponto e exporta um CSV;
   - um script que lê esse CSV e calcula as acurácias e a área ajustada.
   Não preencha as marcações como se fossem verdade. Para testar o script, use um CSV de exemplo **claramente marcado como fictício**.
6. **Onde a IA generativa entra.** Na seção final do relatório, seja concreto: o que um assistente faz bem aqui (código no Earth Engine, revisar o desenho amostral, gerar a página de conferência, explicar a matriz de confusão) e o que não pode fazer (dizer se o mapa está certo sem dado de referência). Se quiser, comente a ideia de um modelo com visão fazer uma pré-triagem dos recortes, mas deixe claro que isso não é validação.
7. **Referências.** 5 a 10 trabalhos (amostragem e validação de mapas, tamanho de amostra para Random Forest, mapeamento de silvicultura/eucalipto no Brasil), com DOI conferido.

## Entregas
As de `REGRAS-COMUNS.md`, mais: a figura da curva de aprendizado, o mapa da área de teste (PNG), a página de conferência (`conferencia/index.html`) e o script de acurácia.
