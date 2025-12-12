# Restart container and clear test cache
# 
# WHEN TO USE THIS SCRIPT:    .\restart_tests.ps1
# - Tests are hanging/not exiting (background threads issue)
# - Tests are running old cached files
# - Python bytecode cache is causing issues
# - You want a completely fresh start
#
# NORMAL USAGE:
# Just run: docker-compose exec app pytest
# The tests directory is mounted, so changes are automatically synced.

Write-Host "Stopping container..."
docker-compose stop app 2>&1 | Out-Null

Write-Host "Removing container to clear cache..."
docker-compose rm -f app 2>&1 | Out-Null

Write-Host "Starting container with fresh mount..."
docker-compose up -d app 2>&1 | Out-Null
Start-Sleep -Seconds 8

Write-Host "Clearing Python cache..."
docker-compose exec -T app find /app/tests -name "*.pyc" -delete 2>&1 | Out-Null
docker-compose exec -T app find /app/tests -name "__pycache__" -type d -exec rm -rf {} + 2>&1 | Out-Null

Write-Host ""
Write-Host "Container restarted and cache cleared. Ready to run tests."
Write-Host ""
Write-Host "Run tests with: docker-compose exec app pytest"

