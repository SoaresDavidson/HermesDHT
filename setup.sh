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

# 4. Sobe os containers
echo ""
echo "Subindo containers..."
docker compose up -d

# 5. Extrai a ApiKey do Prowlarr automaticamente (aguarda o config.xml ser gerado)
PROWLARR_CONFIG="./prowlarr/config/config.xml"
echo "Aguardando Prowlarr gerar o arquivo de configuração..."
for i in $(seq 1 20); do
  if [ -f "$PROWLARR_CONFIG" ] && grep -q "<ApiKey>" "$PROWLARR_CONFIG"; then
    break
  fi
  sleep 3
done

if [ ! -f "$PROWLARR_CONFIG" ] || ! grep -q "<ApiKey>" "$PROWLARR_CONFIG"; then
  echo "Erro: Prowlarr não gerou o config.xml a tempo. Verifique os logs com: docker compose logs prowlarr"
  exit 1
fi

PROWLARR_API_KEY_VAL=$(grep -oP '(?<=<ApiKey>)[^<]+' "$PROWLARR_CONFIG")

if [ -z "$PROWLARR_API_KEY_VAL" ]; then
  echo "Erro: Não foi possível extrair a ApiKey do Prowlarr."
  exit 1
fi

# Atualiza o .env com a chave extraída (substitui se já existir, adiciona se não)
if grep -q "^PROWLARR_API_KEY=" .env; then
  sed -i "s/^PROWLARR_API_KEY=.*/PROWLARR_API_KEY=$PROWLARR_API_KEY_VAL/" .env
else
  echo "PROWLARR_API_KEY=$PROWLARR_API_KEY_VAL" >> .env
fi
echo "PROWLARR_API_KEY extraída e salva no .env. ✅"

# 6. Configura o Prowlarr via API
echo "Executando configuração do Prowlarr..."
if uv run configure_prowlarr.py; then
  echo "Prowlarr configurado com sucesso! ✅"
else
  echo "Aviso: Ocorreu um erro ao rodar configure_prowlarr.py."
fi

# 7. Builda a imagem Docker do servidor MCP
echo ""
echo "Buildando imagem Docker do servidor MCP..."
if docker build -t mcp-prowlarr-qbit ./mcp_server/; then
  echo "Imagem mcp-prowlarr-qbit buildada com sucesso! ✅"
else
  echo "Erro ao buildar a imagem MCP. Verifique o Dockerfile em mcp_server/."
  exit 1
fi

echo ""
echo "Setup concluído!"
echo "  qBittorrent: http://localhost:8080"
echo "  Prowlarr:    http://localhost:9696"