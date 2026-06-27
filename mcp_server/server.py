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
mcp = FastMCP("ProwlarrQbit")

# Configurações obtidas das Variáveis de Ambiente (com fallbacks locais)
PROWLARR_URL = os.environ.get("PROWLARR_URL", "http://localhost:9696").rstrip("/")
PROWLARR_API_KEY = os.environ.get("PROWLARR_API_KEY", "3da31a823cf84de699f63292341889f0")
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

def prowlarr_request(method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    headers = {"X-Api-Key": PROWLARR_API_KEY}
    url = f"{PROWLARR_URL}{path}"
    try:
        resp = requests.request(method, url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Erro na requisição Prowlarr ({method} {path}): {str(e)}")
        raise RuntimeError(f"Erro na API do Prowlarr: {str(e)}")

@mcp.tool()
def buscar_distro(query: str) -> str:
    """
    Busca torrents de distros Linux ou outros arquivos no Prowlarr através dos indexadores ativos.

    Args:
        query: O termo de busca (ex: 'ubuntu 24.04', 'debian netinst').
    """
    logger.info(f"Executando buscar_distro para query: {query}")
    try:
        results = prowlarr_request("GET", "/api/v1/search", {"query": query})
        if not results:
            return f"Nenhum resultado encontrado no Prowlarr para '{query}'."
        
        # Filtra os 15 principais resultados e formata como tabela Markdown
        markdown = f"### Resultados de Busca no Prowlarr para '{query}':\n\n"
        markdown += "| # | Título | Tamanho | Seeders | Peers | Indexador | Link (URL/Magnet) |\n"
        markdown += "|---|--------|---------|---------|-------|-----------|--------------------|\n"
        
        for idx, item in enumerate(results[:15], start=1):
            title = item.get("title", "N/A")
            size_bytes = item.get("size", 0)
            size_gb = size_bytes / (1024 ** 3)
            seeders = item.get("seeders", 0)
            peers = item.get("peers", 0)
            indexer = item.get("indexer", "N/A")
            magnet_url = item.get("magnetUrl", "") or item.get("downloadUrl", "") or item.get("guid", "")
            
            # Corta títulos muito longos para manter o layout da tabela legível
            if len(title) > 60:
                title = title[:57] + "..."
                
            markdown += f"| {idx} | {title} | {size_gb:.2f} GB | {seeders} | {peers} | {indexer} | `{magnet_url}` |\n"
            
        return markdown
    except Exception as e:
        return f"Erro ao realizar a busca no Prowlarr: {str(e)}"

@mcp.tool()
def listar_indexers() -> str:
    """
    Lista todos os indexadores cadastrados no Prowlarr e seus status de atividade.
    """
    logger.info("Executando listar_indexers")
    try:
        indexers = prowlarr_request("GET", "/api/v1/indexer")
        if not indexers:
            return "Nenhum indexador cadastrado no Prowlarr."
        
        markdown = "### Indexadores no Prowlarr:\n\n"
        markdown += "| ID | Nome | Protocolo | Status |\n"
        markdown += "|----|------|-----------|--------|\n"
        
        for ind in indexers:
            idx_id = ind.get("id", "N/A")
            name = ind.get("name", "N/A")
            protocol = ind.get("protocol", "N/A")
            enabled = "Ativo ✅" if ind.get("enable", False) else "Inativo ❌"
            
            markdown += f"| {idx_id} | {name} | {protocol} | {enabled} |\n"
            
        return markdown
    except Exception as e:
        return f"Erro ao listar indexadores do Prowlarr: {str(e)}"

@mcp.tool()
def baixar_iso(magnet: str) -> str:
    """
    Adiciona um link magnet ou URL de torrent de uma ISO no qBittorrent para download.

    Args:
        magnet: O link magnet completo ou URL direta do arquivo .torrent.
    """
    logger.info(f"Executando baixar_iso para: {magnet[:60]}...")
    
    # Corrige problemas de loopback no Docker:
    # Se for uma URL HTTP/HTTPS de torrent vinda do Prowlarr local, o qBittorrent (rodando dentro de seu container)
    # não conseguirá baixar de 'localhost:9696'. Precisamos reescrever para o nome do serviço interno do Docker ('http://prowlarr:9696').
    resolved_magnet = magnet
    if resolved_magnet.startswith("http"):
        # 1. Tenta substituir com base na variável PROWLARR_URL configurada externamente
        if PROWLARR_URL in resolved_magnet:
            resolved_magnet = resolved_magnet.replace(PROWLARR_URL, "http://prowlarr:9696")
        
        # 2. Tenta substituição direta de localhost/127.0.0.1
        for local_host in ["localhost:9696", "127.0.0.1:9696"]:
            if local_host in resolved_magnet:
                resolved_magnet = resolved_magnet.replace(local_host, "prowlarr:9696")
                
        logger.info(f"URL de download reescrita para rede interna: {resolved_magnet[:60]}...")

    try:
        resp = qbit.request("POST", "/api/v2/torrents/add", data={"urls": resolved_magnet})
        # 200 = adicionado imediatamente; 202 = aceito como pendente (qBittorrent 5.x com URL de .torrent)
        if resp.status_code in (200, 202):
            return "Sucesso: O download da ISO foi enviado e iniciado no qBittorrent!"
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

if __name__ == "__main__":
    mcp.run(transport="stdio")
