@echo off
chcp 65001 >nul

:: 检查是否安装了PyInstaller
pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 正在安装PyInstaller...
    pip install pyinstaller
    if %ERRORLEVEL% NEQ 0 (
        echo 安装PyInstaller失败，请手动安装后重试
        pause
        exit /b 1
    )
)

:: 使用绝对路径指定图标
set "ICON_PATH=%~dp0ico\icon.ico"

echo 正在打包应用程序...
echo 图标路径: %ICON_PATH%
pyinstaller --onefile --windowed --icon="%ICON_PATH%" --name=WaterReminder main.py
if %ERRORLEVEL% NEQ 0 (
    echo 打包失败，请检查错误信息
    pause
    exit /b 1
)

:: 复制配置文件
echo 正在复制配置文件...
copy /Y config.json dist\ >nul
if %ERRORLEVEL% NEQ 0 (
    echo 复制配置文件失败
    pause
    exit /b 1
)

echo 打包完成！可执行文件位于dist目录
pause