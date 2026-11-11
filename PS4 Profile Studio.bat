@echo off
setlocal
cd /d "%~dp0"

rem --- check Python ---------------------------------------------------------
where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found in PATH.
    echo Install Python 3 from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during setup.
    pause
    exit /b 1
)

rem --- check Pillow ---------------------------------------------------------
python -c "import PIL" >nul 2>nul
if errorlevel 1 (
    echo Pillow is not installed. Installing it now...
    python -m pip install --user Pillow
    if errorlevel 1 (
        echo.
        echo Could not install Pillow automatically.
        echo Run this in a terminal:  python -m pip install Pillow
        pause
        exit /b 1
    )
)

rem --- check PySide6 (Qt) ---------------------------------------------------
python -c "import PySide6" >nul 2>nul
if errorlevel 1 (
    echo Qt for Python PySide6 is not installed. Installing it now...
    python -m pip install --user PySide6-Essentials
    if errorlevel 1 (
        echo.
        echo Could not install PySide6 automatically.
        echo Run this in a terminal:  python -m pip install PySide6-Essentials
        pause
        exit /b 1
    )
)

rem --- launch without a console window --------------------------------------
where pythonw >nul 2>nul
if errorlevel 1 (
    start "" python "profile_studio.py" %*
) else (
    start "" pythonw "profile_studio.py" %*
)

exit /b 0
