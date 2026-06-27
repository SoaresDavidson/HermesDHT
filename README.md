# HermesDHT 🎬🍿

HermesDHT é uma stack completa de gerenciamento e download de mídia automatizada baseada em Docker.

## 🚀 Serviços e Rotas

Abaixo está a lista de todos os servidores configurados no projeto com suas respectivas portas e links de acesso local:

| Serviço | Porta no Host | Rota de Acesso Local | Descrição |
| :--- | :---: | :--- | :--- |
| **qBittorrent** | `8080` | [http://localhost:8080](http://localhost:8080) | Cliente de Torrent para download dos arquivos (Web UI). |
| **Radarr** | `7878` | [http://localhost:7878](http://localhost:7878) | Gerenciador e organizador de filmes. |
| **Prowlarr** | `9696` | [http://localhost:9696](http://localhost:9696) | Gerenciador de indexadores (trackers Torrent/Usenet). |
| **Bazarr** | `6767` | [http://localhost:6767](http://localhost:6767) | Gerenciador de download automático de legendas. |
| **FlareSolverr** | `8191` | [http://localhost:8191](http://localhost:8191) | Proxy para contornar proteção Cloudflare (integração interna com Prowlarr). |

*Nota: A porta `6881` (TCP/UDP) também está aberta no host para comunicação ponto a ponto do protocolo BitTorrent (qBittorrent).*

---

## 📂 Estrutura de Diretórios e Permissões

Os serviços compartilham volumes mapeados para garantir o funcionamento correto de links físicos (*hardlinks*) e evitar movimentação desnecessária de arquivos grandes entre partições:

- **Downloads:** Caminho definido em `DOWNLOADS_PATH` (mapeado como `/data/downloads` nos containers).
- **Mídia:** Caminho definido em `MEDIA_PATH` (mapeado como `/data/media` nos containers).

### ⚠️ Importante: Permissões de Escrita e Usuários (UID/GID)

Para evitar erros de **"Permission denied"** ao mover ou ler arquivos (especialmente se usar pastas externas montadas em `/mnt/`):
* O script de setup configura as variáveis `PUID` e `PGID` no `.env` utilizando o ID do seu usuário atual (`id -u` e `id -g`).
* Garanta que o usuário do host que está rodando a stack seja o dono das pastas mapeadas em seu disco:
  ```bash
  sudo chown -R $USER:$USER /caminho/para/suas/pastas
  ```

---

## 🛠️ Como Iniciar a Stack

1. **Configuração Automática:**
   Execute o script correspondente ao seu sistema operacional no terminal para criar a estrutura padrão de pastas no seu diretório home (`~/media-server`), gerar o arquivo `.env` com as configurações locais, e configurar automaticamente o qBittorrent com chaves/senhas criptografadas e whitelist da rede Docker:
   
   * **Linux / macOS (Bash):**
     ```bash
     chmod +x setup.sh
     ./setup.sh
     ```
   * **Windows (PowerShell):**
     ```powershell
     ./setup.ps1
     ```

2. **Ajuste Opcional de Caminhos:**
   Caso queira armazenar sua mídia em outro local (como `/mnt/hd_externo/`), edite o arquivo `.env` gerado antes de iniciar a stack:
   ```env
   DOWNLOADS_PATH=/mnt/hd_externo/downloads
   MEDIA_PATH=/mnt/hd_externo/media
   ```

3. **Subir a Stack:**
   Inicie todos os serviços em segundo plano:
   ```bash
   docker compose up -d
   ```

4. **Configuração Automática do Prowlarr:**
   Após os containers estarem rodando:
   * Abra o arquivo `./prowlarr/config/config.xml` para pegar a chave `<ApiKey>...</ApiKey>`.
   * Insira essa chave no seu arquivo `.env` como `PROWLARR_API_KEY=sua_chave`.
   * Execute o script de configuração do Prowlarr para associar automaticamente o qBittorrent e cadastrar o indexador LinuxTracker:
     ```bash
     uv run configure_prowlarr.py
     ```

5. **Verificar o Status:**
   Para acompanhar a inicialização e logs dos containers:
   ```bash
   docker compose ps
   docker compose logs -f
   ```
