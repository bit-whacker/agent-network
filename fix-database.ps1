# Database Container Troubleshooting Script

Write-Host "🔍 Diagnosing database container issue..." -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker status..." -ForegroundColor Yellow
$dockerRunning = docker ps 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker is not running!" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and try again." -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Docker is running" -ForegroundColor Green
Write-Host ""

# Check port 5432
Write-Host "Checking if port 5432 is in use..." -ForegroundColor Yellow
$port5432 = Get-NetTCPConnection -LocalPort 5432 -ErrorAction SilentlyContinue
if ($port5432) {
    Write-Host "⚠️  Port 5432 is already in use!" -ForegroundColor Yellow
    Write-Host "   Likely your local PostgreSQL is running" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "SOLUTIONS:" -ForegroundColor Cyan
    Write-Host "1. Stop local PostgreSQL:" -ForegroundColor White
    Write-Host "   net stop postgresql-x64-*" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. OR use your local PostgreSQL instead:" -ForegroundColor White
    Write-Host "   See USE_LOCAL_POSTGRES.md for instructions" -ForegroundColor Gray
    Write-Host ""
    
    $choice = Read-Host "Try to stop local PostgreSQL? (y/n)"
    if ($choice -eq 'y') {
        Write-Host "Stopping PostgreSQL services..." -ForegroundColor Yellow
        Get-Service postgresql* | Stop-Service -Force -ErrorAction SilentlyContinue
        Write-Host "✅ PostgreSQL services stopped" -ForegroundColor Green
    }
} else {
    Write-Host "✅ Port 5432 is available" -ForegroundColor Green
}
Write-Host ""

# View database container logs
Write-Host "Checking database container logs..." -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════" -ForegroundColor Gray
docker-compose logs db 2>&1 | Select-Object -Last 20
Write-Host "═══════════════════════════════════════" -ForegroundColor Gray
Write-Host ""

# Try to restart
Write-Host "Would you like to:" -ForegroundColor Cyan
Write-Host "1. Try fresh restart (recommended)" -ForegroundColor White
Write-Host "2. Use local PostgreSQL instead" -ForegroundColor White
Write-Host "3. Exit and troubleshoot manually" -ForegroundColor White
$choice = Read-Host "Enter choice (1/2/3)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "🔄 Performing fresh restart..." -ForegroundColor Yellow
        docker-compose down -v
        Start-Sleep -Seconds 3
        docker-compose up -d
        Start-Sleep -Seconds 10
        
        Write-Host ""
        Write-Host "Checking status..." -ForegroundColor Yellow
        docker-compose ps
        
        $healthy = docker-compose ps db 2>&1 | Select-String "healthy"
        if ($healthy) {
            Write-Host "✅ Database is now running!" -ForegroundColor Green
            Write-Host ""
            Write-Host "Initializing database..." -ForegroundColor Yellow
            docker-compose exec -T backend python backend/init_db.py
            Write-Host ""
            Write-Host "✅ All set! Access your app at http://localhost:3000" -ForegroundColor Green
        } else {
            Write-Host "❌ Database still not starting" -ForegroundColor Red
            Write-Host "View logs above for specific error" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Recommended: Use local PostgreSQL instead" -ForegroundColor Cyan
            Write-Host "See: USE_LOCAL_POSTGRES.md" -ForegroundColor Gray
        }
    }
    "2" {
        Write-Host ""
        Write-Host "Setting up to use local PostgreSQL..." -ForegroundColor Yellow
        
        if (Test-Path docker-compose-local-db.yml) {
            Copy-Item docker-compose.yml docker-compose-with-db.yml -Force
            Copy-Item docker-compose-local-db.yml docker-compose.yml -Force
            Write-Host "✅ Switched to local PostgreSQL configuration" -ForegroundColor Green
            Write-Host ""
            Write-Host "Next steps:" -ForegroundColor Cyan
            Write-Host "1. Read USE_LOCAL_POSTGRES.md for complete setup" -ForegroundColor White
            Write-Host "2. Update .env with your PostgreSQL password" -ForegroundColor White
            Write-Host "3. Run: docker-compose up -d" -ForegroundColor White
        } else {
            Write-Host "❌ docker-compose-local-db.yml not found" -ForegroundColor Red
            Write-Host "Please download the updated package" -ForegroundColor Yellow
        }
    }
    "3" {
        Write-Host ""
        Write-Host "For manual troubleshooting:" -ForegroundColor Cyan
        Write-Host "- Read DOCKER_TROUBLESHOOTING.md" -ForegroundColor White
        Write-Host "- Read USE_LOCAL_POSTGRES.md" -ForegroundColor White
        Write-Host "- Check logs: docker-compose logs db" -ForegroundColor White
    }
}
