@echo off
title Iniciando Sistema 
echo Inicializando... Feito por Vicenzo... VzFlex

:: Inicia o Python em uma janela separada (minimizado)
start /min python app.py

:: Aguarda 3 segundos para o servidor ligar
timeout /t 3 /nobreak >nul

:: Abre o site no navegador padrão
start http://127.0.0.1:5000/

exit