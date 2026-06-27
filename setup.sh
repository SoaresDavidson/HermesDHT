#!/bin/bash
# setup.sh
set -e

MEDIA_ROOT="$HOME/media-server"

# 1. Cria a estrutura de pastas do media server no host
mkdir -p "$MEDIA_ROOT"/{downloads/{torrents,incomplete},media/{movies,tv,music}}

# 2. Cria o arquivo .env se não existir
if [ ! -f .env ]; then
  cat > .env <<EOF
PUID=$(id -u)
PGID=$(id -g)
TZ=America/Sao_Paulo
DOWNLOADS_PATH=$MEDIA_ROOT/downloads
MEDIA_PATH=$MEDIA_ROOT/media
LOG_LEVEL=info

# Configurações do Servidor MCP (Prowlarr & qBittorrent)
PROWLARR_URL=http://prowlarr:9696
PROWLARR_API_KEY=
QBITTORRENT_URL=http://qbittorrent:8080
QBITTORRENT_USER=admin
EOF
  echo "Arquivo .env criado com configurações padrão."
fi

# 3. Executa o script Python separado para configurar o qBittorrent
if python3 configure_qbittorrent.py > temp_qbit.txt; then
  # Extrai informações geradas para exibir no terminal
  PASSWORD=$(grep "PASSWORD:" temp_qbit.txt | cut -d':' -f2)
  API_KEY=$(grep "API_KEY:" temp_qbit.txt | cut -d':' -f2)
  rm temp_qbit.txt
  
  echo "qBittorrent configurado no host com sucesso."
  echo "Senha gerada e salva: $PASSWORD"
  echo "API Key gerada e salva: $API_KEY"
else
  echo "Erro ao rodar configure_qbittorrent.py. Verifique se o Python 3 está instalado."
  rm -f temp_qbit.txt
  exit 1
fi

# 4. Executa a configuração do Prowlarr se a API Key já estiver presente no .env
PROWLARR_API_KEY_VAL=$(grep "^PROWLARR_API_KEY=" .env | cut -d'=' -f2-)

if [ -n "$PROWLARR_API_KEY_VAL" ]; then
  echo ""
  echo "PROWLARR_API_KEY encontrada. Executando configuração do Prowlarr..."
  if uv run configure_prowlarr.py; then
    echo "Prowlarr e indexadores configurados com sucesso! ✅"
  else
    echo "Aviso: Ocorreu um erro ao rodar configure_prowlarr.py."
  fi
else
  echo ""
  echo "Aviso: Prowlarr não pôde ser integrado ainda (PROWLARR_API_KEY vazia)."
  echo "Para finalizar a integração:"
  echo "  1. Inicie os containers: docker compose up -d"
  echo "  2. Obtenha a ApiKey em './prowlarr/config/config.xml'"
  echo "  3. Insira no seu arquivo .env como PROWLARR_API_KEY=sua_chave"
  echo "  4. Execute este script de setup novamente (ou rode: uv run configure_prowlarr.py)"
fi

echo ""
echo "Setup processado!"
echo "1. Credenciais do qBittorrent injetadas no .env e qBittorrent.conf."
echo "2. Whitelist de sub-rede do Docker configurada no qBittorrent."
echo "3. Caso não tenha subido os containers, inicie com: docker compose up -d"