@echo off
setlocal enabledelayedexpansion

:: Configuration section
set "script_dir=%~dp0"
set "base_dir=%script_dir%.."
for %%A in ("%base_dir%") do set "base_dir=%%~fA"
set "venv_dir=%base_dir%\.venv"
set "req_file=%base_dir%\requirements.txt"
set "flag_file=%script_dir%.setup_completed"
set "app_module=src"
set "PYTHONPATH=%base_dir%;%PYTHONPATH%"

:: Check for existing setup
if exist "%flag_file%" (
    echo Existing setup detected. Launching application...
    call :execute
    call :cleanup
    exit /b 0
)

:: Validate Python installation
set "py_cmd=python"
where python >nul 2>&1 || (
    where python3 >nul 2>&1 && set "py_cmd=python3" || (
        echo Error: Python not found in PATH
        exit /b 1
    )
)

:: Verify Python version
%py_cmd% -c "import sys; exit(0) if sys.version_info >= (3,11) else exit(1)" || (
    echo Error: Python 3.11+ required
    exit /b 1
)

:: Validate requirements.txt exists
if not exist "%req_file%" (
    echo Error: requirements.txt not found in project root
    exit /b 1
)

:: Setup process
echo Initializing new setup...
echo Creating virtual environment...
if not exist "%venv_dir%" (
    %py_cmd% -m venv "%venv_dir%" || (
        echo Failed to create virtual environment
        exit /b 1
    )
) else (
    echo Found an environment, skipping creation 
)

call "%venv_dir%\Scripts\activate.bat"
:: TODO: fails if not Scripts dir found in venv
echo Installing dependencies...
echo Upgrading pip...
python -m pip install --upgrade pip --quiet
python -m pip install -r "%req_file%" || (
    echo Failed to install requirements
    exit /b 1
)

:: Create setup completion flag
echo. > "%flag_file%"
echo Setup completed successfully. Created verification flag.

:: Launch application

:execute
call "%venv_dir%\Scripts\activate.bat" && (
    cd /d "%base_dir%"
    python -m "%app_module%"
    call "%venv_dir%\Scripts\deactivate"
)
exit /b 0

:: Cleanup
:cleanup
call "%venv_dir%\Scripts\deactivate"

echo.
set /p "clear=Clear screen? [y/N]: "
if /i "!clear!"=="y" cls
endlocal
