# HermesDHT

Stack Docker para busca e download de ISOs Linux via Prowlarr + qBittorrent, com servidor MCP para integração com Claude.

## Serviços

| Serviço | Porta | Descrição |
| :--- | :---: | :--- |
| **qBittorrent** | `8080` | Cliente BitTorrent (Web UI) |
| **Prowlarr** | `9696` | Gerenciador de indexadores/trackers |
| **FlareSolverr** | — | Proxy anti-Cloudflare (interno) |

> Porta `6881` (TCP/UDP) exposta para tráfego BitTorrent peer-to-peer.

## Setup

```bash
./setup.sh
```

O script faz tudo automaticamente: cria pastas, gera `.env`, configura qBittorrent, sobe os containers, extrai a ApiKey do Prowlarr e executa a configuração completa.

**Caminhos de mídia** — editáveis no `.env` antes do passo 2:
```env
DOWNLOADS_PATH=/mnt/hd_externo/downloads
MEDIA_PATH=/mnt/hd_externo/media
```

## Servidor MCP

O `mcp_server/` expõe ferramentas para o Claude interagir com a stack:

| Ferramenta | Descrição |
| :--- | :--- |
| `buscar_distro` | Pesquisa ISOs de distros no Prowlarr |
| `listar_indexers` | Lista indexadores ativos |
| `baixar_iso` | Envia magnet link para o qBittorrent |
| `listar_downloads` | Lista torrents em andamento |
| `pausar_download` | Pausa torrent por hash |
| `deletar_download` | Remove torrent (opcionalmente com dados) |

Configure via variáveis de ambiente (veja `.env`) ou rode localmente com `uv run mcp_server/server.py`.
