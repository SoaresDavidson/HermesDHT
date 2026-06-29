# setup.ps1
# Script de setup para Windows (PowerShell)

$MEDIA_ROOT = "$env:USERPROFILE\media-server"
# Docker requer forward slashes nos caminhos do .env
$MEDIA_ROOT_DOCKER = $MEDIA_ROOT.Replace("\", "/")

# 1. Cria a estrutura de pastas do media server no host
$paths = @(
    "$MEDIA_ROOT\downloads\torrents",
    "$MEDIA_ROOT\downloads\incomplete"
)
foreach ($path in $paths) {
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Force -Path $path | Out-Null
    }
}

# 2. Cria o arquivo .env se não existir
if (-not (Test-Path .env)) {
    $envContent = @"
PUID=1000
PGID=1000
TZ=America/Sao_Paulo
DOWNLOADS_PATH=$MEDIA_ROOT_DOCKER/downloads
LOG_LEVEL=info

# Configurações do Servidor MCP (qBittorrent)
QBITTORRENT_URL=http://qbittorrent:8080
QBITTORRENT_USER=admin
"@
    Set-Content -Path .env -Value $envContent -Encoding utf8
    Write-Host "Arquivo .env criado com configurações padrão."
}

# 3. Verifica se 'python' ou 'python3' está disponível no Windows
$pythonCmd = "python"
try {
    & python --version | Out-Null
} catch {
    try {
        & python3 --version | Out-Null
        $pythonCmd = "python3"
    } catch {
        Write-Error "Python não foi encontrado no sistema. Por favor, instale o Python 3."
        exit 1
    }
}

# 4. Executa o script Python separado para configurar o qBittorrent
$results = & $pythonCmd configure_qbittorrent.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Erro ao rodar configure_qbittorrent.py. Verifique se o Python 3 está instalado corretamente."
    exit 1
}
$password = ""

foreach ($line in $results) {
    if ($line -match "^PASSWORD:(.*)$") {
        $password = $Matches[1]
    }
}

Write-Host "qBittorrent configurado com sucesso."
Write-Host "Senha gerada e salva: $password"

# 5. Configuração processada. qBittorrent configurado.

Write-Host ""
Write-Host "Setup processado!"
Write-Host "1. Credenciais do qBittorrent injetadas no .env e qBittorrent.conf."
Write-Host "2. Whitelist de sub-rede do Docker configurada no qBittorrent."
Write-Host "3. Caso não tenha subido os containers, inicie com: docker compose up -d"
