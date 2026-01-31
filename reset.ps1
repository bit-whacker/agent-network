# Reset and Restart Script - Fixes Database Schema Error

Write-Host "🔄 Resetting database with fixed schema..." -ForegroundColor Cyan
Write-Host ""

# Stop all containers
Write-Host "Stopping containers..." -ForegroundColor Yellow
docker-compose down -v

Write-Host "✅ Containers stopped and volumes removed" -ForegroundColor Green
Write-Host ""

# Wait a moment
Start-Sleep -Seconds 2

# Start containers
Write-Host "Starting containers with fixed schema..." -ForegroundColor Yellow
docker-compose up -d

Write-Host ""
Write-Host "Waiting for database to initialize (15 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Check status
Write-Host ""
Write-Host "Checking container status..." -ForegroundColor Yellow
docker-compose ps

Write-Host ""

# Check if database is healthy
$dbStatus = docker-compose ps db 2>&1
if ($dbStatus -match "healthy" -or $dbStatus -match "running") {
    Write-Host "✅ Database container is running!" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "Initializing database..." -ForegroundColor Yellow
    docker-compose exec -T backend python backend/init_db.py
    
    Write-Host ""
    Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "✅ Application is ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📱 Frontend: http://localhost:3000" -ForegroundColor Cyan
    Write-Host "🔧 API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
} else {
    Write-Host "⚠️  Database container may still be starting..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "View logs to check:" -ForegroundColor Yellow
    Write-Host "  docker-compose logs db" -ForegroundColor Gray
    Write-Host ""
    Write-Host "If still having issues, try:" -ForegroundColor Yellow
    Write-Host "  .\fix-database.ps1" -ForegroundColor Gray
}

Write-Host ""
Write-Host "To view logs: docker-compose logs -f" -ForegroundColor Gray
Write-Host "To stop: docker-compose down" -ForegroundColor Gray
