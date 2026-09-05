@echo off
title Obsidian BookEngine Pro - Bestseller Studio
chcp 65001 > nul
cd /d "%~dp0"
echo =================================================================
echo  Obsidian BookEngine Pro 를 시작합니다...
echo  일반인의 원고 집필 고통을 해소하고 출판 품질을 완성합니다.
echo =================================================================
python server.py
pause
