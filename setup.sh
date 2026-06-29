#!/bin/bash
# setup.sh
set -e

MEDIA_ROOT="$HOME/media-server"

# 1. Cria a estrutura de pastas do media server no host
mkdir -p "$MEDIA_ROOT"/downloads/{torrents,incomplete}

# 2. Cria o arquivo .env se não existir
if [ ! -f .env ]; then
  cat > .env <<EOF
PUID=$(id -u)
PGID=$(id -g)
TZ=America/Sao_Paulo
DOWNLOADS_PATH=$MEDIA_ROOT/downloads
LOG_LEVEL=info

# Configurações do Servidor MCP (qBittorrent)
QBITTORRENT_URL=http://qbittorrent:8080
QBITTORRENT_USER=admin
EOF
  echo "Arquivo .env criado com configurações padrão."
fi

# 3. Executa o script Python separado para configurar o qBittorrent
if python3 configure_qbittorrent.py > temp_qbit.txt; then
  # Extrai informações geradas para exibir no terminal
  PASSWORD=$(grep "PASSWORD:" temp_qbit.txt | cut -d':' -f2)
  rm temp_qbit.txt
  
  echo "qBittorrent configurado no host com sucesso."
  echo "Senha gerada e salva: $PASSWORD"
else
  echo "Erro ao rodar configure_qbittorrent.py. Verifique se o Python 3 está instalado."
  rm -f temp_qbit.txt
  exit 1
fi

# 4. Sobe os containers
echo ""
echo "Subindo containers..."
docker compose up -d

# 5. Builda a imagem Docker do servidor MCP
echo ""
echo "Buildando imagem Docker do servidor MCP..."
if docker build -t mcp-qbittorrent-hf ./mcp_server/; then
  echo "Imagem mcp-qbittorrent-hf buildada com sucesso! ✅"
else
  echo "Erro ao buildar a imagem MCP. Verifique o Dockerfile em mcp_server/."
  exit 1
fi

echo ""
echo "Setup concluído!"
echo "  qBittorrent: http://localhost:8080"