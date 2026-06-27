# Usamos a imagem oficial do Astral UV baseada em Alpine (ultra-leve)
FROM ghcr.io/astral-sh/uv:python3.12-alpine

# Evita a gravação de arquivos .pyc e força flush imediato no stdout/stderr (crítico para stdio)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copia o script do servidor
COPY server.py .

# Instala as dependências do script diretamente no sistema usando o uv (rápido e limpo)
RUN uv pip install --system --no-cache mcp requests

# Executa o Python no modo unbuffered (-u) para garantir fluxo constante do stdio
ENTRYPOINT ["python", "-u", "server.py"]
