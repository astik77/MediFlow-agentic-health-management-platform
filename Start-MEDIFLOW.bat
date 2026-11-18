@echo off
title MEDIFLOW Launcher
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\start-mediflow.ps1"
if errorlevel 1 (
  echo.
  echo Something went wrong starting MEDIFLOW. See messages above.
  pause
)
