# Prowlarr & qBittorrent MCP Server 🚀

Este diretório contém o servidor **Model Context Protocol (MCP)** escrito em Python utilizando o SDK oficial do MCP e a ferramenta `uv`. 

Este servidor permite que clientes de IA (como **Claude Desktop**, **Cursor**, **Windsurf**, etc.) se comuniquem diretamente com a sua stack do HermesDHT para buscar arquivos (ex: distros Linux) e gerenciar downloads no cliente de torrent.

---

## 🛠️ Requisitos

Você precisará de:
1. **Python 3.10+** instalado no sistema.
2. **uv** (gerenciador rápido de dependências para Python) instalado.

---

## 📋 Ferramentas Expostas pelo Servidor

O servidor expõe as seguintes ferramentas para o cliente de IA:

*   **`buscar_distro(query)`**: Realiza buscas de torrents/ISOs no Prowlarr.
*   **`listar_indexers()`**: Mostra quais indexadores (trackers) estão ativos no Prowlarr.
*   **`baixar_iso(magnet)`**: Envia um magnet link ou link de arquivo torrent para começar o download no qBittorrent.
*   **`listar_downloads()`**: Exibe o progresso de todos os downloads ativos e concluídos no qBittorrent.
*   **`pausar_download(hash)`**: Pausa um download no qBittorrent pelo ID/hash do torrent.
*   **`deletar_download(hash, deletar_dados)`**: Exclui um torrent do qBittorrent (e opcionalmente remove seus arquivos locais).

---

## 🚀 Como Executar

### Opção 1: Rodar diretamente com o `uv` (Recomendado)

O script utiliza metadados da PEP 723, o que significa que o `uv` cuidará de todas as dependências automaticamente em um ambiente isolado.

Defina as variáveis de ambiente necessárias e execute:

```bash
# Definindo as credenciais e endereços
export PROWLARR_URL="http://localhost:9696"
export PROWLARR_API_KEY="3da31a823cf84de699f63292341889f0"
export QBITTORRENT_URL="http://localhost:8080"
export QBITTORRENT_USER="admin"
export QBITTORRENT_PASS="SUA_SENHA_DEFINIDA_DO_QBITTORRENT"  # altere para a sua senha!

# Rodar o servidor via stdio
uv run server.py
```

---

## 💻 Integração com Editores e Clientes

### Claude Desktop

Para integrar este servidor de ferramentas com o app oficial do Claude Desktop, adicione a configuração abaixo no seu arquivo de configurações (`~/.config/Claude/claude_desktop_config.json` no Linux):

```json
{
  "mcpServers": {
    "prowlarr-qbit": {
      "command": "uv",
      "args": [
        "run",
        "/home/davi/Projetos/HermesDHT/mcp_server/server.py"
      ],
      "env": {
        "PROWLARR_URL": "http://localhost:9696",
        "PROWLARR_API_KEY": "3da31a823cf84de699f63292341889f0",
        "QBITTORRENT_URL": "http://localhost:8080",
        "QBITTORRENT_USER": "admin",
        "QBITTORRENT_PASS": "SUA_SENHA_DEFINIDA_DO_QBITTORRENT"
      }
    }
  }
}
```

> [!TIP]
> Se o Claude Desktop reclamar que o comando `uv` não foi encontrado, forneça o caminho absoluto dele no campo `"command"` (por exemplo, `"/home/davi/.local/bin/uv"` ou `"/usr/bin/uv"`). Você pode descobrir esse caminho rodando `which uv` no seu terminal.
