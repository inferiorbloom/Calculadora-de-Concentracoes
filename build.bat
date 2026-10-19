@echo off
setlocal

set ROOT=%~dp0
set PYTHON=%ROOT%.venv\Scripts\python.exe

if not exist "%PYTHON%" (
    echo Python virtual environment not found.
    exit /b 1
)

rem 1) Executavel (PyInstaller)
"%PYTHON%" -m PyInstaller --noconfirm --clean calculadora.spec
if errorlevel 1 (
    echo.
    echo Falha no PyInstaller: o instalador nao foi gerado.
    exit /b 1
)

echo.
echo Executavel gerado em: %ROOT%dist\CalculadoraConcentracoes\CalculadoraConcentracoes.exe

rem 2) Instalador (Inno Setup), se estiver instalado
set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not defined ISCC (
    echo.
    echo Inno Setup 6 nao encontrado: so o executavel foi gerado.
    echo Para o instalador, abra instalador.iss no Inno Setup Compiler e clique em Compile.
    exit /b 0
)

"%ISCC%" /Q "%ROOT%instalador.iss"
if errorlevel 1 (
    echo.
    echo Falha ao compilar o instalador.
    exit /b 1
)

echo.
echo Build concluido.
echo Instalador gerado em: %ROOT%instalador\
endlocal
