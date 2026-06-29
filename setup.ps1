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

# 5. Sobe os containers
Write-Host ""
Write-Host "Subindo containers..."
& docker compose up -d

# 6. Extrai a ApiKey do Prowlarr automaticamente (aguarda o config.xml ser gerado)
$prowlarrConfig = "./prowlarr/config/config.xml"
Write-Host "Aguardando Prowlarr gerar o arquivo de configuração..."
$found = $false
$prowlarrApiKeyVal = ""

for ($i = 1; $i -le 20; $i++) {
    if (Test-Path $prowlarrConfig) {
        $content = Get-Content $prowlarrConfig -Raw
        if ($content -match "<ApiKey>([^<]+)</ApiKey>") {
            $found = $true
            $prowlarrApiKeyVal = $Matches[1].Trim()
            break
        }
    }
    Start-Sleep -Seconds 3
}

if (-not $found) {
    Write-Error "Erro: Prowlarr não gerou o config.xml a tempo. Verifique os logs com: docker compose logs prowlarr"
    exit 1
}

# Atualiza o .env com a chave extraída
$envPath = ".env"
$envLines = Get-Content $envPath
$updated = $false
$newLines = @()
foreach ($line in $envLines) {
    if ($line -match "^PROWLARR_API_KEY=") {
        $newLines += "PROWLARR_API_KEY=$prowlarrApiKeyVal"
        $updated = $true
    } else {
        $newLines += $line
    }
}
if (-not $updated) {
    $newLines += "PROWLARR_API_KEY=$prowlarrApiKeyVal"
}
Set-Content -Path $envPath -Value $newLines -Encoding utf8
Write-Host "PROWLARR_API_KEY extraída e salva no .env. ✅"

# 7. Configura o Prowlarr via API
Write-Host "Executando configuração do Prowlarr..."
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
    Write-Host "Prowlarr configurado com sucesso! ✅"
} else {
    Write-Host "Aviso: Ocorreu um erro ao rodar configure_prowlarr.py."
}

# 8. Builda a imagem Docker do servidor MCP
Write-Host ""
Write-Host "Buildando imagem Docker do servidor MCP..."
& docker build -t mcp-prowlarr-qbit ./mcp_server/
if ($LASTEXITCODE -eq 0) {
    Write-Host "Imagem mcp-prowlarr-qbit buildada com sucesso! ✅"
} else {
    Write-Error "Erro ao buildar a imagem MCP. Verifique o Dockerfile em mcp_server/."
    exit 1
}

Write-Host ""
Write-Host "Setup concluído!"
Write-Host "  qBittorrent: http://localhost:8080"
Write-Host "  Prowlarr:    http://localhost:9696"
