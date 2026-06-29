# HermesDHT

Stack Docker para busca e download de datasets/modelos do Hugging Face e ISOs via qBittorrent, com servidor MCP para integração com Claude.

## Serviços

| Serviço | Porta | Descrição |
| :--- | :---: | :--- |
| **qBittorrent** | `8080` | Cliente BitTorrent (Web UI) |

> Porta `6881` (TCP/UDP) exposta para tráfego BitTorrent peer-to-peer.

## Setup

```bash
./setup.sh
```

O script faz tudo automaticamente: cria pastas, gera `.env`, configura o qBittorrent, sobe os containers e executa o build da imagem do servidor MCP.

**Caminho de downloads** — editável no `.env`:
```env
DOWNLOADS_PATH=${sua_pasta_pessoal}/media-server/downloads
```

## Servidor MCP

O `mcp_server/` expõe ferramentas para o Claude interagir com a stack e com o Hugging Face:

| Ferramenta | Descrição |
| :--- | :--- |
| `buscar_datasets_hf` | Busca datasets no catálogo do Hugging Face |
| `baixar_torrent_hf` | Obtém o .torrent do Hugging Face via hf-torrent e envia ao qBittorrent |
| `baixar_iso` | Envia magnet link ou link .torrent genérico para o qBittorrent |
| `listar_downloads` | Lista torrents em andamento |
| `pausar_download` | Pausa torrent por hash |
| `deletar_download` | Remove torrent (opcionalmente com dados) |

Configure via variáveis de ambiente (veja `.env`) ou rode localmente com `uv run mcp_server/server.py`.
