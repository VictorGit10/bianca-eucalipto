# Segunda rodada de correções (31/10/2026)

As regras de `REGRAS-COMUNS.md` continuam valendo. Foram achados problemas por duas conferências independentes (`CONFERENCIA-MINIMAX.md` e uma análise de outra IA), confirmados no código. Critério: **servir ao que a pesquisadora pediu no `CONTEXTO.md`** — quantas amostras usar no RF para mapear eucalipto **em Goiás**, e se/como a IA pode ajudar a conferir se a classificação está satisfatória.

Ao terminar, acrescente ao `RELATORIO.md` uma seção **"Correções de 31/10 (2ª rodada)"** e atualize README, CLAUDE.md/AGENTS.md e figuras.

## 1. Cores do mapa (importante)
`04_mapa.py`: o `ListedColormap` tem 6 cores para 5 classes (`+ ["#ffffff"]`) com `vmin=-0.5, vmax=4.5`. Pastagem sai sem amarelo e mosaico/água sai branco. Use exatamente uma cor por classe (com `BoundaryNorm`) e `set_bad` para sem-dado. Regere `figuras/mapa_area.png` a partir dos `.tif` locais e **confira olhando a figura** que cada classe tem a cor da legenda.

## 2. Erro padrão da acurácia do produtor (importante)
`olofsson.py`, função `_pa`: a variância não segue a fórmula do estimador. Use o estimador de razão de Stehman (2014, *Int. J. Remote Sens.*, "Estimating area and map accuracy for stratified random sampling when the strata are different from the map classes") ou a equação de Olofsson et al. (2014) para PA. Com o exemplo fictício atual, o valor certo é ~0,097 para eucalipto e ~0,019 para não eucalipto (o código dá 0,107 e 0,035). Uma forma vetorial (método delta) que vale para classe de 1 ou de vários estratos, com `c = (j_de_i == j)` e `pa = p_jj / p_j[j]`: `var = sum((c - pa)**2 * W**2 * (m[:,j]/n) * (1 - m[:,j]/n) / (n-1))`, `se = sqrt(var) / p_j[j]`. Confira, não confie.
Corrija também `_ua` para a classe que junta vários estratos (`nao_alvo`): hoje soma contagens brutas sem pesar pela área do estrato; o certo é a média das acurácias de cada estrato ponderada por `W` (no exemplo, ~0,879 em vez de 0,889).
Escreva um teste que reproduz um exemplo numérico publicado (Olofsson et al. 2014 traz um; confira os números do artigo) e regere `dados/acuracia_resultado.json`. Confira também, no mesmo teste, a acurácia global, a do usuário e a área.

## 3. O que a acurácia global mede
Deixe claro (relatório, README e saída do `06_acuracia.py`) que a acurácia global do script é **eucalipto × não eucalipto** (é o que interessa para o mapa de eucalipto), e que não é comparável à acurácia de 5 classes da curva de aprendizado.

## 4. Robustez do `06_acuracia.py`
Se um estrato ficar sem ponto numa política (ex.: todos "não sei"), o script deve avisar qual estrato e qual política e seguir com as outras, sem traceback. Teste com um CSV fictício assim.

## 5. Página de conferência
O texto fala de um "círculo pequeno no meio da imagem" que não existe. Desenhe o marcador do pixel central por CSS sobre a imagem, sem mudar os recortes: o recorte tem 700 m em 240 px (~2,9 m/px), então o pixel de 20 m do mapa é um quadrado de ~7 × 7 px no centro. Uma tecla ou botão mostra/oculta o marcador. Confira. Defina "borda" no texto (3 × 3 com classes diferentes) onde ela aparece.

## 6. Ressalva sobre a referência
A marcação na imagem S2 de 10 m (a mesma do mapa) mede concordância com o que se vê nessa imagem. Na página e no relatório, oriente: nos pontos duvidosos, abrir o link de alta resolução e, se possível, outra data (plantio jovem/colhido confunde com pastagem). Registre que ~1 ponto pode coincidir com pixel de treino e o efeito disso.

## 7. De Rio Verde para Goiás
A dúvida dela é para o estado. No relatório e no README, uma seção curta e concreta: repetir a curva de aprendizado em 2–3 regiões de Goiás com silvicultura diferente (usar `dados/silvicultura_por_municipio.csv` para sugerir quais), sortear treino por região, o mapa estadual e a validação de Olofsson no estado (o `05_desenho_validacao.py` calcula o tamanho de amostra; mostre o número para o estado com as áreas do MapBiomas, se der para obter sem download grande). Não precisa rodar o mapa estadual.

## 8. Higiene
- `CLAUDE.md` não deve ter o nome de usuário do Windows nem caminho absoluto.
- 62,7 MB: diga que é o tamanho local, não o tráfego.
- O `08_resumo.py` imprime todos os números que o relatório cita.
- A chave (`dados/pontos_chave.csv`) na mesma pasta da página: diga no README para não abrir antes de marcar (ou mova para `dados/chave/`).

## Não mexa
Curva de aprendizado, sorteio dos pontos, controle e página (fora o item 5).
