@echo off
title Iniciando Sistema Contuflex
echo Inicializando... Feito por Vicenzo...

:: Inicia o Python em uma janela separada (minimizado)
start /min python app.py

:: Aguarda 3 segundos para o servidor ligar
timeout /t 3 /nobreak >nul

:: Abre o site no navegador padrão
start server_padrao/

exit