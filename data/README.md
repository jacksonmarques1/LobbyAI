# Avaliações brasileiras da Steam

A base usada é o *Steam Brazilian Portuguese Games Reviews Dataset*, de Larissa F. S. Britto e Luciano D. S. Pacífico (UFRPE, SBGames 2020). O estudo informa que os autores coletaram as avaliações pela API da Steam. O voto do próprio jogador determina a classe. O arquivo positivo contém recomendações e o negativo contém votos contrários.

- [Artigo original](https://www.sbgames.org/proceedings2020/ComputacaoShort/209781.pdf)
- [Recorte utilizado, com versão fixada](https://github.com/lucasvbalves/nlp-pt-br-datasets/tree/7d98f85588b2dac37658ea717054cb244b0ba87b/steam-reviews-portuguese-master)
- Consulta em 25 de novembro de 2026. O recorte tem 1.000 linhas em cada um dos dois arquivos de texto, cerca de 5 MB no total.

**Campos usados.** Cada linha contém o texto de uma avaliação. O nome do arquivo de origem indica o voto. O leitor monta as colunas `texto`, `voto` (0 ou 1) e `id` (arquivo e número da linha para conferência). Somente `texto` entra no modelo.

**Condições de uso.** A documentação do recorte pede a citação do artigo. Não há licença explícita de redistribuição nos arquivos consultados. Por isso este projeto referencia a fonte e deixa os textos brutos fora do Git. Ao executar `python train.py`, o programa baixa os arquivos públicos originais para `data/raw/` e verifica o SHA-256. A aba de demonstração também pode baixá-los na primeira abertura. Os arquivos ficam disponíveis localmente para as próximas execuções.
