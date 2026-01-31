# Windows PowerShell startup script for Agent Network

Write-Host "🚀 Starting Agent Network Application..." -ForegroundColor Cyan
Write-Host ""

# Check if .env file exists
if (-not (Test-Path .env)) {
    Write-Host "⚠️  No .env file found. Creating from template..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host ""
    Write-Host "⚠️  IMPORTANT: Edit .env and add your ANTHROPIC_API_KEY" -ForegroundColor Yellow
    Write-Host "   Get your API key from: https://console.anthropic.com/" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter after you've added your API key to .env"
}

# Start Docker containers
Write-Host "📦 Starting Docker containers..." -ForegroundColor Green
docker-compose up -d

# Wait for database
Write-Host "⏳ Waiting for database to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Initialize database
Write-Host "🗄️  Initializing database..." -ForegroundColor Green
docker-compose exec -T backend python backend/init_db.py

Write-Host ""
Write-Host "✅ Application started successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📱 Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host "🔧 API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "To stop: docker-compose down" -ForegroundColor Yellow
Write-Host "To view logs: docker-compose logs -f" -ForegroundColor Yellow
