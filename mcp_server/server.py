# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp>=1.0.0",
#     "requests>=2.31.0",
# ]
# ///

import os
import sys
import logging
from typing import Optional, Any, Dict
import requests
from mcp.server.fastmcp import FastMCP

# Configura o logging para a saída de erro padrão (sys.stderr)
# Isso é CRÍTICO porque a comunicação MCP usa stdin/stdout. Qualquer print no stdout corrompe o protocolo.
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("ProwlarrQbitMCP")

# Inicializa o Servidor FastMCP
mcp = FastMCP("HermesDHT")

# Configurações obtidas das Variáveis de Ambiente (com fallbacks locais)
QBITTORRENT_URL = os.environ.get("QBITTORRENT_URL", "http://localhost:8080").rstrip("/")
QBITTORRENT_USER = os.environ.get("QBITTORRENT_USER", "admin")
QBITTORRENT_PASS = os.environ.get("QBITTORRENT_PASS", "123456")  # Deve ser preenchido se houver senha ativa

class QbitClient:
    def __init__(self, url: str, user: str, password: str):
        self.url = url
        self.user = user
        self.password = password
        self.session = requests.Session()
        self.authenticated = False

    def login(self) -> bool:
        if self.authenticated:
            return True
        try:
            logger.info("Tentando autenticar no qBittorrent...")
            resp = self.session.post(
                f"{self.url}/api/v2/auth/login",
                data={"username": self.user, "password": self.password},
                timeout=10
            )
            # qBittorrent retorna HTTP 200 com "Ok." (versões antigas) ou 204 (versões 5.x+)
            if resp.status_code == 204 or (resp.status_code == 200 and "Ok" in resp.text):
                self.authenticated = True
                logger.info("Autenticado com sucesso no qBittorrent.")
                return True
            else:
                logger.error(f"Falha na autenticação do qBittorrent: Status={resp.status_code}, Body={resp.text}")
                return False
        except Exception as e:
            logger.error(f"Erro durante login no qBittorrent: {str(e)}")
            return False

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        if not self.authenticated:
            self.login()
        
        url = f"{self.url}{path}"
        try:
            resp = self.session.request(method, url, timeout=15, **kwargs)
            # Se receber 403 (Forbidden), tenta re-autenticar uma vez
            if resp.status_code == 403:
                logger.warning("Recebido status 403. Tentando login novamente...")
                self.authenticated = False
                if self.login():
                    resp = self.session.request(method, url, timeout=15, **kwargs)
            return resp
        except Exception as e:
            logger.error(f"Erro na requisição qBittorrent ({method} {path}): {str(e)}")
            raise

qbit = QbitClient(QBITTORRENT_URL, QBITTORRENT_USER, QBITTORRENT_PASS)

@mcp.tool()
def baixar_iso(magnet: str) -> str:
    """
    Adiciona um link magnet ou URL de torrent no qBittorrent para download.

    Args:
        magnet: O link magnet completo ou URL direta do arquivo .torrent.
    """
    logger.info(f"Executando baixar_iso para: {magnet[:60]}...")
    try:
        resp = qbit.request("POST", "/api/v2/torrents/add", data={"urls": magnet})
        # 200 = adicionado imediatamente; 202 = aceito como pendente (qBittorrent 5.x com URL de .torrent)
        if resp.status_code in (200, 202):
            return "Sucesso: O download foi enviado e iniciado no qBittorrent!"
        else:
            return f"Erro ao enviar download para o qBittorrent: Código={resp.status_code}, Detalhe={resp.text}"
    except Exception as e:
        return f"Falha na comunicação com o qBittorrent: {str(e)}"

@mcp.tool()
def listar_downloads() -> str:
    """
    Exibe uma lista detalhada de todos os torrents ativos e finalizados no qBittorrent, mostrando progresso e velocidade.
    """
    logger.info("Executando listar_downloads")
    try:
        resp = qbit.request("GET", "/api/v2/torrents/info")
        if resp.status_code != 200:
            return f"Erro ao obter lista de torrents: Código={resp.status_code}, Detalhe={resp.text}"
            
        torrents = resp.json()
        if not torrents:
            return "Nenhum torrent cadastrado no qBittorrent no momento."
            
        markdown = "### Downloads no qBittorrent:\n\n"
        markdown += "| Nome | Progresso | Tamanho | Velocidade DL | Status | Hash (ID) |\n"
        markdown += "|------|-----------|---------|---------------|--------|-----------|\n"
        
        for t in torrents:
            name = t.get("name", "N/A")
            progress = t.get("progress", 0.0) * 100
            size_bytes = t.get("size", 0)
            size_gb = size_bytes / (1024 ** 3)
            dl_speed = t.get("dlspeed", 0)
            dl_speed_kb = dl_speed / 1024
            state = t.get("state", "unknown")
            torrent_hash = t.get("hash", "N/A")
            
            if len(name) > 40:
                name = name[:37] + "..."
                
            markdown += f"| {name} | {progress:.1f}% | {size_gb:.2f} GB | {dl_speed_kb:.1f} KB/s | {state} | `{torrent_hash}` |\n"
            
        return markdown
    except Exception as e:
        return f"Erro ao processar a lista de downloads: {str(e)}"

@mcp.tool()
def pausar_download(hash: str) -> str:
    """
    Pausa um download específico no qBittorrent.

    Args:
        hash: O hash identificador (ID) do torrent a ser pausado.
    """
    logger.info(f"Executando pausar_download para o hash: {hash}")
    try:
        resp = qbit.request("POST", "/api/v2/torrents/pause", data={"hashes": hash})
        if resp.status_code == 200:
            return f"Sucesso: O torrent `{hash}` foi pausado."
        else:
            return f"Erro ao pausar torrent `{hash}`: Código={resp.status_code}"
    except Exception as e:
        return f"Erro na operação de pausa: {str(e)}"

@mcp.tool()
def deletar_download(hash: str, deletar_dados: bool = False) -> str:
    """
    Remove um torrent do qBittorrent, com a opção de excluir ou manter os arquivos baixados no disco.

    Args:
        hash: O hash identificador (ID) do torrent a ser removido.
        deletar_dados: Se True, remove permanentemente os arquivos do disco. Se False, apenas remove o torrent do cliente.
    """
    logger.info(f"Executando deletar_download para o hash: {hash} (excluir arquivos={deletar_dados})")
    try:
        resp = qbit.request(
            "POST", 
            "/api/v2/torrents/delete", 
            data={"hashes": hash, "deleteFiles": "true" if deletar_dados else "false"}
        )
        if resp.status_code == 200:
            msg = f"Sucesso: O torrent `{hash}` foi removido do qBittorrent"
            if deletar_dados:
                msg += " e todos os seus arquivos foram excluídos do disco permanentemente."
            else:
                msg += " (os arquivos locais foram mantidos)."
            return msg
        else:
            return f"Erro ao excluir torrent `{hash}`: Código={resp.status_code}"
    except Exception as e:
        return f"Erro na operação de exclusão: {str(e)}"

@mcp.tool()
def buscar_datasets_hf(query: str, limit: int = 10) -> str:
    """
    Busca datasets no catálogo oficial do Hugging Face.

    Args:
        query: O termo de busca (ex: 'imdb', 'wikipedia').
        limit: O número máximo de resultados (padrão 10).
    """
    logger.info(f"Executando buscar_datasets_hf para query: {query}")
    try:
        url = "https://huggingface.co/api/datasets"
        params = {
            "search": query,
            "sort": "downloads",
            "limit": limit
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        datasets = resp.json()
        
        if not datasets:
            return f"Nenhum dataset encontrado no Hugging Face para '{query}'."
            
        markdown = f"### Datasets no Hugging Face para '{query}':\n\n"
        markdown += "| # | ID | Downloads | Likes | Descrição |\n"
        markdown += "|---|----|-----------|-------|-----------|\n"
        
        for idx, item in enumerate(datasets, start=1):
            ds_id = item.get("id", "N/A")
            downloads = item.get("downloads", 0)
            likes = item.get("likes", 0)
            description = item.get("description", "Sem descrição.")
            
            # Limpa e encurta a descrição
            description = description.replace("\n", " ").replace("\t", " ").strip()
            if len(description) > 80:
                description = description[:77] + "..."
                
            markdown += f"| {idx} | `{ds_id}` | {downloads:,} | {likes:,} | {description} |\n"
            
        return markdown
    except Exception as e:
        return f"Erro ao realizar a busca no Hugging Face: {str(e)}"

@mcp.tool()
def baixar_torrent_hf(repo: str) -> str:
    """
    Obtém o arquivo .torrent de um dataset/modelo do Hugging Face usando hf-torrent
    e o envia automaticamente para download no qBittorrent.

    Args:
        repo: O identificador do repositório (ex: 'gpt2', 'stanfordnlp/imdb').
    """
    logger.info(f"Executando baixar_torrent_hf para o repositório: {repo}")
    try:
        from hf_torrent.download import main as download_main
        import os
        
        # Registra a lista de arquivos atual para detectar o novo .torrent gerado
        before_files = set(os.listdir("."))
        
        logger.info("Iniciando download do arquivo .torrent via hf-torrent...")
        # Baixa apenas o arquivo torrent no diretório atual
        download_main(repo, "~/.cache/hf-torrent/downloads", "hf-torrent-models", get_torrent=True)
        
        after_files = set(os.listdir("."))
        new_files = after_files - before_files
        torrent_file = None
        for f in new_files:
            if f.endswith(".torrent"):
                torrent_file = f
                break
                
        # Fallback de busca caso o arquivo já existisse
        if not torrent_file:
            from hf_torrent.utils import convert_repo_name
            prefix = convert_repo_name(repo)
            for f in os.listdir("."):
                if f.startswith(prefix) and f.endswith(".torrent"):
                    torrent_file = f
                    break
                    
        if not torrent_file:
            return f"Erro: Não foi possível obter o arquivo .torrent para o repositório '{repo}'."
            
        logger.info(f"Arquivo torrent encontrado: {torrent_file}. Enviando para o qBittorrent...")
        
        # Faz o upload do arquivo torrent para a API do qBittorrent
        with open(torrent_file, "rb") as f:
            files = {"torrents": f}
            resp = qbit.request("POST", "/api/v2/torrents/add", files=files)
            
        # Remove o arquivo temporário local
        try:
            os.remove(torrent_file)
        except Exception:
            pass
            
        if resp.status_code in (200, 202):
            return f"Sucesso: O torrent do dataset/modelo `{repo}` foi enviado e iniciado no qBittorrent!"
        else:
            return f"Erro ao enviar o torrent para o qBittorrent: Código={resp.status_code}, Detalhes={resp.text}"
            
    except Exception as e:
        return f"Falha na operação de download do torrent do Hugging Face: {str(e)}"

@mcp.tool()
def listar_torrents_hf(query: str = "") -> str:
    """
    Lista os modelos/datasets do Hugging Face que já possuem arquivos torrent
    disponíveis no repositório hf-torrent-store.

    Args:
        query: Opcional. Termo para filtrar a lista de repositórios (ex: 'llama', 'stable').
    """
    logger.info(f"Executando listar_torrents_hf com filtro: {query}")
    try:
        # Busca a árvore de arquivos recursivamente da API do GitHub
        url = "https://api.github.com/repos/Lyken17/hf-torrent-store/git/trees/master?recursive=1"
        headers = {"User-Agent": "HermesDHT-MCP"}
        resp = requests.get(url, headers=headers, timeout=15)
        
        if resp.status_code == 403:
            return (
                "Aviso: Limite de requisições à API do GitHub atingido (Rate Limit).\n"
                "Você pode consultar a lista de torrents disponíveis acessando diretamente: "
                "https://github.com/Lyken17/hf-torrent-store"
            )
            
        resp.raise_for_status()
        tree_data = resp.json()
        
        # Filtra os caminhos dos arquivos de metadados principais (_all.torrent)
        repos = []
        for item in tree_data.get("tree", []):
            path = item.get("path", "")
            if path.endswith("/_all.torrent"):
                repo_name = path[:-13] # Remove "/_all.torrent"
                repos.append(repo_name)
                
        # Remove duplicados e ordena alfabeticamente
        repos = sorted(list(set(repos)))
        
        # Aplica o filtro de busca se houver
        if query:
            query_lower = query.lower()
            repos = [r for r in repos if query_lower in r.lower()]
            
        if not repos:
            if query:
                return f"Nenhum repositório com torrent ativo encontrado para o filtro '{query}'."
            return "Nenhum repositório com torrent encontrado."
            
        # Formata os resultados como Markdown
        markdown = f"### Repositórios com Torrent Ativos no hf-torrent-store"
        if query:
            markdown += f" (Filtrado por '{query}')"
        markdown += f":\n\n"
        
        # Exibe os primeiros 100 resultados e avisa se houver mais
        max_display = 100
        for repo in repos[:max_display]:
            markdown += f"*   `{repo}`\n"
            
        if len(repos) > max_display:
            markdown += f"\n*... e mais {len(repos) - max_display} repositórios. Seja mais específico na busca!*"
            
        return markdown
        
    except Exception as e:
        return f"Erro ao obter lista de torrents do hf-torrent-store: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
