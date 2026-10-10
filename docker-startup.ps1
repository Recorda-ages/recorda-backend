# Interrompe a execução se houver algum erro crítico
$ErrorActionPreference = "Stop"

Write-Host "=== 1. Removendo todos os containers existentes ==-" -ForegroundColor Cyan
$containers = docker ps -a -q
if ($containers) {
    docker stop $containers
    docker rm $containers
    Write-Host "Containers removidos com sucesso!" -ForegroundColor Green
} else {
    Write-Host "Nenhum container encontrado." -ForegroundColor Yellow
}

Write-Host "`n=== 2. Removendo imagens do Docker (mantendo python:3.13-slim e postgres:16-alpine) ===" -ForegroundColor Cyan

# Pega o ID de todas as imagens, exceto as que queremos proteger
$images = docker images --format "{{.ID}} {{.Repository}}:{{.Tag}}" | 
          Where-Object { 
              $_ -notmatch "python:3.13-slim" -and 
              $_ -notmatch "postgres:16-alpine" 
          } | 
          ForEach-Object { $_.Split(" ")[0] }

if ($images) {
    # Remove apenas as imagens filtradas
    docker rmi -f $images
    Write-Host "Imagens antigas removidas com sucesso (protegidas mantidas)!" -ForegroundColor Green
} else {
    Write-Host "Nenhuma imagem adicional para remover." -ForegroundColor Yellow
}

Write-Host "`n=== 3. Realizando o Build da nova imagem (Dockerfile) ==-" -ForegroundColor Cyan
# Substitua 'seu-nome-de-imagem:latest' pelo nome desejado para a sua imagem
docker build -t seu-nome-de-imagem:latest .
Write-Host "Build concluído com sucesso!" -ForegroundColor Green

Write-Host "`n=== 4. Subindo os serviços com o Docker Compose ==-" -ForegroundColor Cyan
# Se o seu arquivo usar outro nome, adicione o parâmetro -f nome-do-compose.yml
docker compose up -d --build
Write-Host "Docker Compose iniciado com sucesso!" -ForegroundColor Green

Write-Host "`nProcesso concluído com êxito!" -ForegroundColor Magenta