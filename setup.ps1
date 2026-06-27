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

# Configurações do Servidor MCP (Prowlarr & qBittorrent)
PROWLARR_URL=http://prowlarr:9696
PROWLARR_API_KEY=
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
$apiKey = ""

foreach ($line in $results) {
    if ($line -match "^PASSWORD:(.*)$") {
        $password = $Matches[1]
    }
    if ($line -match "^API_KEY:(.*)$") {
        $apiKey = $Matches[1]
    }
}

Write-Host "qBittorrent configurado com sucesso."
Write-Host "Senha gerada e salva: $password"
Write-Host "API Key gerada e salva: $apiKey"

# 5. Executa a configuração do Prowlarr se a API Key já estiver presente no .env
$prowlarrApiKey = ""
if (Test-Path .env) {
    $envLines = Get-Content .env
    foreach ($envLine in $envLines) {
        if ($envLine -match "^PROWLARR_API_KEY=(.+)$") {
            $prowlarrApiKey = $Matches[1].Trim()
        }
    }
}

if ($prowlarrApiKey -ne "") {
    Write-Host ""
    Write-Host "PROWLARR_API_KEY encontrada. Executando configuração do Prowlarr..."
    
    $hasUv = $false
    try {
        & uv --version | Out-Null
        $hasUv = $true
    } catch {}

    if ($hasUv) {
        & uv run configure_prowlarr.py
    } else {
        Write-Host "Instalando dependências e executando com Python padrão..."
        & $pythonCmd -m pip install requests | Out-Null
        & $pythonCmd configure_prowlarr.py
    }

    if ($LASTEXITCODE -eq 0) {
        Write-Host "Prowlarr e indexadores configurados com sucesso! ✅"
    } else {
        Write-Host "Aviso: Ocorreu um erro ao rodar configure_prowlarr.py."
    }
} else {
    Write-Host ""
    Write-Host "Aviso: Prowlarr não pôde ser integrado ainda (PROWLARR_API_KEY vazia)."
    Write-Host "Para finalizar a integração:"
    Write-Host "  1. Inicie os containers: docker compose up -d"
    Write-Host "  2. Obtenha a ApiKey em './prowlarr/config/config.xml'"
    Write-Host "  3. Insira no seu arquivo .env como PROWLARR_API_KEY=sua_chave"
    Write-Host "  4. Execute este script de setup novamente (ou rode: uv run configure_prowlarr.py)"
}

Write-Host ""
Write-Host "Setup processado!"
Write-Host "1. Credenciais do qBittorrent injetadas no .env e qBittorrent.conf."
Write-Host "2. Whitelist de sub-rede do Docker configurada no qBittorrent."
Write-Host "3. Caso não tenha subido os containers, inicie com: docker compose up -d"
