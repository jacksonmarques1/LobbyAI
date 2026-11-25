# Catálogo de descoberta

A seleção editorial reúne oito jogos de PC. Cada ficha usa o Steam App ID como chave. Os indicadores da vitrine são independentes do corpus usado para treinar o modelo de texto.

| Campo | Origem | Interpretação |
| --- | --- | --- |
| Título, gênero, modo e descrição curta | Curadoria do LobbyAI | Indicam estilo e motivo para conhecer o jogo. Jogos que aceitam várias modalidades têm uma modalidade principal no filtro. |
| `players.count` | [Steam Web API](https://partner.steamgames.com/doc/webapi/ISteamUserStats#GetNumberOfCurrentPlayers) | Pessoas jogando simultaneamente na Steam no instante consultado. |
| `reviews.positive` e `reviews.negative` | [SteamSpy](https://steamspy.com/api.php) | Totais de votos acumulados informados pela fonte. A página calcula a porcentagem positiva sobre a soma dos dois. |
| `consultado` | Coletor local | Data e hora UTC da consulta a cada fonte; a interface exibe em horário de Manaus. |
| Capas e arte panorâmica | CDN da Steam por App ID | As imagens promocionais e marcas pertencem aos respectivos titulares. |
| Twitch | Busca pelo nome do jogo | Abre a busca na plataforma. Canais, audiência e transmissão ao vivo são consultados lá. |

Execute `python catalogo.py` para atualizar `data/catalogo.json`. Se uma fonte falhar, a última leitura daquele indicador continua com seu horário original. Sem votos disponíveis, a ficha informa a ausência. O aplicativo lê os dados salvos e pode abrir mesmo durante uma indisponibilidade das APIs.

O ranking compara apenas os títulos do catálogo, pela contagem de jogadores. “Fora do radar” seleciona a metade com menor atividade entre os oito jogos, considerando apenas títulos com votos disponíveis, e ordena a seleção pela proporção de recomendações. Os dados descrevem uma coleta pontual. Analisar crescimento semanal exigiria armazenar séries históricas.

As imagens WebP em `static/art/` permitem abrir a vitrine offline. Se a cópia local estiver ausente, o navegador tenta o endereço da capa registrado no JSON. A família Barlow Condensed acompanha o projeto com a licença OFL em `static/fonts/`.
