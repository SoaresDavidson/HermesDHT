# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.31.0",
# ]
# ///

import os
import re
import sys
import time
import requests

def load_env():
    env_vars = {}
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                match = re.match(r"^([^=\s]+)\s*=\s*(.*)$", line)
                if match:
                    env_vars[match.group(1).strip()] = match.group(2).strip()
    return env_vars

def main():
    print("Iniciando configuração do Prowlarr...")
    env = load_env()
    
    prowlarr_url = env.get("PROWLARR_URL", "http://localhost:9696").rstrip("/")
    prowlarr_api_key = env.get("PROWLARR_API_KEY")
    qbit_pass = env.get("QBITTORRENT_PASS")
    qbit_user = env.get("QBITTORRENT_USER", "admin")
    qbit_api_key = env.get("QBITTORRENT_API_KEY")

    if not prowlarr_api_key:
        print("Erro: PROWLARR_API_KEY não encontrada no .env.")
        print("Certifique-se de iniciar a stack docker e colar a API Key no arquivo .env antes de rodar este script.")
        sys.exit(1)
        
    if not qbit_pass and not qbit_api_key:
        print("Erro: Nem QBITTORRENT_PASS nem QBITTORRENT_API_KEY foram encontrados no .env.")
        sys.exit(1)

    # Se o script rodar no host mas a URL do .env apontar para a rede interna do docker ('http://prowlarr'),
    # nós traduzimos a URL para 'localhost' para conseguir fazer as chamadas HTTP a partir do host.
    api_url = prowlarr_url
    if "prowlarr" in api_url and "localhost" not in api_url and "127.0.0.1" not in api_url:
        api_url = "http://localhost:9696"
        print(f"Traduzindo URL interna '{prowlarr_url}' para URL externa '{api_url}' para execução local.")

    headers = {
        "X-Api-Key": prowlarr_api_key,
        "Content-Type": "application/json"
    }

    # 1. Espera o Prowlarr ficar online
    max_retries = 10
    connected = False
    for i in range(max_retries):
        try:
            resp = requests.get(f"{api_url}/api/v1/system/status", headers=headers, timeout=5)
            if resp.status_code == 200:
                print("Prowlarr está online e pronto para configuração.")
                connected = True
                break
        except Exception:
            pass
        print(f"Aguardando Prowlarr responder em {api_url}... (Tentativa {i+1}/{max_retries})")
        time.sleep(3)
        
    if not connected:
        print(f"Erro: Não foi possível conectar ao Prowlarr em {api_url}. Verifique se os containers estão rodando.")
        sys.exit(1)

    # 2. Configura o Download Client (qBittorrent)
    print("Configurando o download client (qBittorrent) no Prowlarr...")
    try:
        # Busca clients existentes
        resp = requests.get(f"{api_url}/api/v1/downloadclient", headers=headers, timeout=10)
        resp.raise_for_status()
        clients = resp.json()
        
        qbit_client = None
        for client in clients:
            if client.get("implementation") == "QBittorrent" or client.get("name") == "qBittorrent":
                qbit_client = client
                break
                
        if qbit_client:
            # Atualiza existente: pegamos o objeto inteiro e alteramos apenas os campos necessários
            client_id = qbit_client["id"]
            print(f"qBittorrent já configurado (ID: {client_id}). Atualizando dados...")
            qbit_client["enable"] = True
            for field in qbit_client["fields"]:
                if field["name"] == "host":
                    field["value"] = "qbittorrent"
                elif field["name"] == "port":
                    field["value"] = 8080
                elif field["name"] == "apiKey":
                    field["value"] = qbit_api_key if qbit_api_key else ""
                elif field["name"] == "username":
                    field["value"] = "" if qbit_api_key else qbit_user
                elif field["name"] == "password":
                    field["value"] = "" if qbit_api_key else qbit_pass
                elif field["name"] == "category":
                    field["value"] = "prowlarr"
            
            resp = requests.put(f"{api_url}/api/v1/downloadclient/{client_id}", headers=headers, json=qbit_client, timeout=10)
        else:
            # Cria novo: Busca o schema para obter todos os campos padrão obrigatórios
            print("Adicionando novo download client qBittorrent com base no schema oficial...")
            schema_resp = requests.get(f"{api_url}/api/v1/downloadclient/schema", headers=headers, timeout=10)
            schema_resp.raise_for_status()
            schemas = schema_resp.json()
            
            qbit_schema = next((s for s in schemas if s.get("implementation") == "QBittorrent"), None)
            if not qbit_schema:
                raise RuntimeError("Não foi possível encontrar o esquema do qBittorrent no Prowlarr.")
                
            qbit_schema["name"] = "qBittorrent"
            qbit_schema["enable"] = True
            for field in qbit_schema["fields"]:
                if field["name"] == "host":
                    field["value"] = "qbittorrent"
                elif field["name"] == "port":
                    field["value"] = 8080
                elif field["name"] == "apiKey":
                    field["value"] = qbit_api_key if qbit_api_key else ""
                elif field["name"] == "username":
                    field["value"] = "" if qbit_api_key else qbit_user
                elif field["name"] == "password":
                    field["value"] = "" if qbit_api_key else qbit_pass
                elif field["name"] == "category":
                    field["value"] = "prowlarr"
                    
            resp = requests.post(f"{api_url}/api/v1/downloadclient", headers=headers, json=qbit_schema, timeout=10)
            
        if resp.status_code >= 400:
            print(f"Erro detalhado da API Prowlarr: {resp.text}")
        resp.raise_for_status()
        print("qBittorrent configurado com sucesso no Prowlarr! ✅")
        
    except Exception as e:
        print(f"Erro ao configurar download client qBittorrent: {str(e)}")

    # 3. Configura o Indexer (LinuxTracker)
    print("Configurando o indexador LinuxTracker no Prowlarr...")
    try:
        # Busca indexadores cadastrados
        resp = requests.get(f"{api_url}/api/v1/indexer", headers=headers, timeout=10)
        resp.raise_for_status()
        indexers = resp.json()
        
        lt_indexer = None
        for ind in indexers:
            if ind.get("name") == "LinuxTracker" or "linuxtracker" in ind.get("sortName", "").lower():
                lt_indexer = ind
                break
                
        if lt_indexer:
            indexer_id = lt_indexer["id"]
            print(f"LinuxTracker já configurado (ID: {indexer_id}). Atualizando dados...")
            lt_indexer["enable"] = True
            for field in lt_indexer["fields"]:
                if field["name"] == "definitionFile":
                    field["value"] = "linuxtracker"
                elif field["name"] == "baseUrl":
                    field["value"] = "https://linuxtracker.org/"

            resp = requests.put(f"{api_url}/api/v1/indexer/{indexer_id}", headers=headers, json=lt_indexer, timeout=10)
        else:
            print("Adicionando novo indexador LinuxTracker com base no schema oficial...")
            # A API do Prowlarr não suporta filtro por ?definition= — busca todos os schemas
            # e localiza o linuxtracker pelo campo definitionFile
            schema_resp = requests.get(f"{api_url}/api/v1/indexer/schema", headers=headers, timeout=10)
            schema_resp.raise_for_status()
            schemas = schema_resp.json()

            indexer_schema = None
            for s in schemas:
                for field in s.get("fields", []):
                    if field.get("name") == "definitionFile" and field.get("value") == "linuxtracker":
                        indexer_schema = s
                        break
                if indexer_schema:
                    break

            if not indexer_schema:
                raise RuntimeError("Não foi possível encontrar o schema do LinuxTracker no Prowlarr.")

            indexer_schema["name"] = "LinuxTracker"
            indexer_schema["enable"] = True
            indexer_schema["priority"] = 25
            for field in indexer_schema["fields"]:
                if field["name"] == "definitionFile":
                    field["value"] = "linuxtracker"
                elif field["name"] == "baseUrl":
                    field["value"] = "https://linuxtracker.org/"
                    
            resp = requests.post(f"{api_url}/api/v1/indexer", headers=headers, json=indexer_schema, timeout=10)
            
        resp.raise_for_status()
        print("LinuxTracker configurado com sucesso no Prowlarr! ✅")
        
    except Exception as e:
        print(f"Erro ao configurar indexador LinuxTracker: {str(e)}")

if __name__ == "__main__":
    main()
