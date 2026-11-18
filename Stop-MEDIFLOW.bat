@echo off
title Stop MEDIFLOW
echo Stopping MEDIFLOW production containers...
cd /d "%~dp0"
docker compose -f docker-compose.prod.yaml --env-file .env.prod stop
echo MEDIFLOW containers stopped (your data volumes are preserved).
pause
