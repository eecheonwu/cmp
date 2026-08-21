@echo off
REM CMP Docker Development Quick Start Script for Windows

echo ========================================
echo CMP Docker Development Environment
echo ========================================
echo.

echo Starting all services...
docker-compose up -d

echo.
echo Waiting for services to be ready...
timeout /t 30 /nobreak >nul

echo.
echo Checking service status...
docker-compose ps

echo.
echo ========================================
echo Services are starting up!
echo ========================================
echo.
echo Backend API:    http://localhost:8000
echo API Docs:       http://localhost:8000/docs
echo Frontend:       http://localhost:5173
echo Adminer (DB):   http://localhost:8080
echo LocalStack:     http://localhost:4566
echo.
echo To view logs:   docker-compose logs -f
echo To stop:        docker-compose down
echo ========================================