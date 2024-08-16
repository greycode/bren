@echo off
setlocal enabledelayedexpansion

REM 检查 Python 是否安装
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not installed or not in the PATH. Please install Python and try again.
    exit /b 1
)

REM 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"

REM 构建完整的 Python 脚本路径
set "PYTHON_SCRIPT=%SCRIPT_DIR%bren.py"

REM 检查 Python 脚本是否存在
if not exist "%PYTHON_SCRIPT%" (
    echo Python script not found: %PYTHON_SCRIPT%
    exit /b 1
)

REM 将所有参数传递给 Python 脚本
python "%PYTHON_SCRIPT%" %*

REM 检查 Python 脚本的返回值
if %errorlevel% neq 0 (
    echo An error occurred while running the Python script.
    exit /b %errorlevel%
)

endlocal