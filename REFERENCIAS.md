# Referencias conferidas

Todas as referencias abaixo foram conferidas em `https://api.crossref.org/works/<doi>`
em 31/10/2026 (script: `python codigo/verificar_referencias.py`). Nenhuma foi escrita
de memoria: o script compara o titulo da tabela com o titulo devolvido pelo Crossref.

| # | Referencia | DOI | Por que esta aqui |
|---|---|---|---|
| 1 | Olofsson, P., Foody, G., Herold, M., Stehman, S., Woodcock, C., Wulder, M. (2014). Good practices for estimating area and assessing accuracy of land change. *Remote Sensing of Environment* 148:42-57. | 10.1016/j.rse.2014.02.015 | Base do desenho de validacao do passo 05 e 06: amostra estratificada pelo mapa, matriz de confusao, acuracia do usuario e do produtor, area ajustada com intervalo de confianca. |
| 2 | Olofsson, P., Foody, G., Stehman, S., Woodcock, C. (2013). Making better use of accuracy data in land change studies: Estimating accuracy and area and quantifying uncertainty using stratified estimation. *Remote Sensing of Environment* 129:122-131. | 10.1016/j.rse.2012.10.031 | De onde vem a formula do estimador de area com variancia usada em `codigo/olofsson.py`. |
| 3 | Stehman, S., Foody, G. (2019). Key issues in rigorous accuracy assessment of land cover products. *Remote Sensing of Environment* 231:111199. | 10.1016/j.rse.2019.05.018 | Por que "concordar com o MapBiomas" nao e acuracia e por que a amostra de validacao precisa ser probabilistica. |
| 4 | Belgiu, M., Dragut, L. (2016). Random forest in remote sensing: A review of applications and future directions. *ISPRS Journal of Photogrammetry and Remote Sensing* 114:24-31. | 10.1016/j.isprsjprs.2016.01.011 | Referencia geral do Random Forest em sensoriamento remoto (o algoritmo que a pesquisadora ja usa). |
| 5 | Pelletier, C., Valero, S., Inglada, J., Champion, N., Dedieu, G. (2016). Assessing the robustness of Random Forests to map land cover with high resolution satellite image time series over large areas. *Remote Sensing of Environment* 187:156-168. | 10.1016/j.rse.2016.10.010 | Mostra que o efeito do tamanho da amostra de treino depende do numero de classes e da confusao entre elas - o mesmo padrao da curva de aprendizado do passo 03. |
| 6 | Millard, K., Richardson, M. (2015). On the Importance of Training Data Sample Selection in Random Forest Image Classification: A Case Study in Peatland Ecosystem Mapping. *Remote Sensing* 7:8489-8515. | 10.3390/rs70708489 | Sobre como a forma de sortear as amostras de treino muda o resultado - sustenta a comparacao entre sorteio aleatorio e por blocos. |
| 7 | Roberts, D., Bahn, V., Ciuti, S., Boyce, M., Elith, J., Guillera-Arroita, G. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography* 40:913-929. | 10.1111/ecog.02881 | Justifica separar treino e teste por blocos espaciais (validacao cruzada espacial) em vez de sortear pixels vizinhos. |
| 8 | Souza, C., Shimbo, J., Rosa, M., Parente, L., Alencar, A., Rudorff, B. (2020). Reconstructing Three Decades of Land Use and Land Cover Changes in Brazilian Biomes with Landsat Archive and Earth Engine. *Remote Sensing* 12:2735. | 10.3390/rs12172735 | Descreve a metodologia do MapBiomas, de onde vieram os rotulos provisorios e a classe 9 (silvicultura). |
| 9 | Carneiro, G., Ferreira, M., Volotao, C. (2020). Multi-source remote sensing data improves the classification accuracy of natural forests and eucalyptus plantations. *Revista Brasileira de Cartografia* 72:110-125. | 10.14393/rbcv72n1-50477 | Caso brasileiro de classificacao de florestas nativas e plantios de eucalipto - a mesma confusao que aparece no mapa deste teste. |
| 10 | Oliveira, G., Araujo, F. (2021). Location of planted forest influencing the wood commercialization in the state of Goias, Brazil. *FLORESTA* 51:320. | 10.5380/rf.v51i2.65087 | Contexto da silvicultura em Goias, o estado do recorte de teste (onde estao os plantios e como se distribuem). |

## Como conferir

```
python codigo/verificar_referencias.py
```

O script le este arquivo, pega cada DOI, consulta o Crossref e compara o titulo.
Se algum DOI nao existir ou o titulo nao bater, ele avisa e o item deve sair do texto.
