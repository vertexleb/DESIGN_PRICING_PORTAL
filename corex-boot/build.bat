@echo off
rem Double-click friendly wrapper around build.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" %*
