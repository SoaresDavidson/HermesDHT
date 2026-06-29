# Usamos a imagem oficial do Astral UV baseada em Alpine (ultra-leve)
FROM ghcr.io/astral-sh/uv:python3.12-alpine

# Evita a gravação de arquivos .pyc e força flush imediato no stdout/stderr (crítico para stdio)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copia o script do servidor
COPY server.py .

# Instala o aria2 (opcional: necessário apenas se você quiser que este container baixe os dados do modelo via P2P, não necessário se quiser apenas extrair o .torrent para o qBittorrent)
# RUN apk add --no-cache aria2

# Instala as dependências do script diretamente no sistema usando o uv (rápido e limpo)
# E aplica um patch no hf_torrent para contornar o bug de importação obsoleta da huggingface_hub
RUN uv pip install --system --no-cache mcp requests hf-torrent huggingface-hub && \
    find /usr/ -name "utils.py" | grep "hf_torrent/utils.py" | xargs sed -i 's/from huggingface_hub.file_download import http_get, _chmod_and_replace/from huggingface_hub.file_download import http_get/g'

# Executa o Python no modo unbuffered (-u) para garantir fluxo constante do stdio
ENTRYPOINT ["python", "-u", "server.py"]
