# Catálogo de descoberta

A seleção editorial de jogos de PC é combinada com até oito demos indie da listagem da Steam na atualização. Cada ficha usa o Steam App ID como chave. Os indicadores da vitrine são independentes do corpus usado para treinar o modelo de texto.

| Campo | Origem | Interpretação |
| --- | --- | --- |
| Título, gênero, modo e descrição curta | Curadoria do LobbyAI | Indicam estilo e motivo para conhecer o jogo. O App ID identifica a ficha. Para descobertas automáticas, a descrição e o gênero vêm da Steam. |
| `players.count` | [Steam Web API](https://partner.steamgames.com/doc/webapi/ISteamUserStats#GetNumberOfCurrentPlayers) | Pessoas jogando simultaneamente na Steam no instante consultado. |
| `reviews.positive` e `reviews.negative` | [SteamSpy](https://steamspy.com/api.php) | Totais de votos acumulados informados pela fonte. A página calcula a porcentagem positiva sobre a soma dos dois. |
| `consultado` | Coletor local | Data e hora UTC da consulta a cada fonte; a interface exibe em horário de Manaus. |
| Capas e arte panorâmica | CDN da Steam por App ID | As imagens promocionais e marcas pertencem aos respectivos titulares. |
| Twitch | Busca pelo nome do jogo | Abre a busca na plataforma. Canais, audiência e transmissão ao vivo são consultados lá. |

Execute `python catalogo.py` para atualizar `data/catalogo.json`. Se uma fonte falhar, a última leitura daquele indicador continua com seu horário original. Sem votos disponíveis, a ficha informa a ausência. O aplicativo lê os dados salvos e pode abrir mesmo durante uma indisponibilidade das APIs.

O ranking compara apenas os títulos do catálogo, pela contagem de jogadores. “Fora do radar” seleciona a metade com menor atividade entre os jogos do catálogo, considerando apenas títulos com votos disponíveis, e ordena a seleção pela proporção de recomendações. Os dados descrevem uma coleta pontual. Analisar crescimento semanal exigiria armazenar séries históricas.

As imagens WebP em `static/art/` permitem abrir a vitrine offline. Se a cópia local estiver ausente, o navegador tenta o endereço da capa registrado no JSON. A família Barlow Condensed acompanha o projeto com a licença OFL em `static/fonts/`.


### Filtros e novas descobertas

O coletor consulta a ficha da loja para o Brasil. O gênero Steam 23 identifica indie. A propriedade `is_free` indica se o jogo completo é gratuito. Os modos solo, cooperativo, local e online vêm das categorias da loja. Uma demo aparece quando a ficha lista um App ID de demonstração ou quando uma demo na busca confirma o vínculo com o jogo completo. Os filtros são cumulativos. A modalidade da demonstração pode diferir da modalidade do jogo principal.

O arquivo `data/selecao.json` amplia a curadoria original. A cada execução de `python catalogo.py`, a busca da Steam é consultada por demonstrações indie, em ordem de lançamento. O coletor confere o tipo, o vínculo com o título principal e a plataforma Windows da demo. Se a busca ficar indisponível, o coletor mantém a seleção anterior do radar. Os destaques das coleções mudam por dia no horário de Manaus. Os números de votos e jogadores da ficha referem-se ao jogo principal.

[Busca de demos na Steam](https://store.steampowered.com/search/?category1=10&tags=492&sort_by=Released_DESC)
