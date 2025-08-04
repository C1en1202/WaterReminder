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

:: 打包应用程序
echo 正在打包应用程序...
pyinstaller --onefile --windowed --icon=ico\icon.ico --name=WaterReminder main.py
if %ERRORLEVEL% NEQ 0 (
    echo 打包失败，请检查错误信息
    pause
    exit /b 1
)

:: 复制配置文件到dist目录
if exist dist ( 
    copy config.json dist\ >nul
    echo 配置文件已复制到dist目录
)

:: 完成提示
echo 打包完成！可执行文件位于dist目录中
pause