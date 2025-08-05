import sys
import os
import json
import datetime
import time
import winreg
import psutil
import ctypes
from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QMessageBox, QSystemTrayIcon, QMenu)
from PySide6.QtGui import QAction, QPixmap, QPainter, QBrush, QPen, QColor
from PySide6.QtGui import QIcon, QFont
from PySide6.QtCore import Qt, QTimer, QDateTime, QCoreApplication

# 水瓶UI组件
class WaterBottleWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_water = 0
        self.daily_limit = 3000
        self.setMinimumSize(200, 300)
        self.setMaximumSize(200, 300)

    def set_values(self, current_water, daily_limit):
        self.current_water = current_water
        self.daily_limit = daily_limit
        self.update()  # 触发重绘

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 获取窗口尺寸
        width = self.width()
        height = self.height()

        # 水瓶参数
        bottle_width = width * 0.6
        bottle_height = height * 0.8
        bottle_x = (width - bottle_width) / 2
        bottle_y = height * 0.1

        # 绘制水瓶轮廓
        pen = QPen(Qt.black, 2)
        painter.setPen(pen)
        painter.drawRoundedRect(bottle_x, bottle_y, bottle_width, bottle_height, 10, 10)

        # 绘制水瓶瓶颈
        neck_width = bottle_width * 0.4
        neck_height = height * 0.1
        neck_x = (width - neck_width) / 2
        neck_y = bottle_y - neck_height
        painter.drawRect(neck_x, neck_y, neck_width, neck_height)

        # 计算水量高度
        water_percentage = min(self.current_water / self.daily_limit, 1.0)
        water_height = bottle_height * water_percentage
        water_y = bottle_y + bottle_height - water_height

        # 绘制水
        water_brush = QBrush(QColor(51, 153, 255, 180))  # 半透明蓝色
        painter.setBrush(water_brush)
        painter.drawRoundedRect(bottle_x + 2, water_y, bottle_width - 4, water_height - 2, 8, 8)

        # 绘制水量文本
        font = QFont("SimHei", 10)
        painter.setFont(font)
        water_text = f"{self.current_water}ml / {self.daily_limit}ml"
        text_rect = painter.boundingRect(0, 0, width, 20, Qt.AlignCenter, water_text)
        painter.drawText(0, height - 20, width, 20, Qt.AlignCenter, water_text)

# 移除已弃用的高DPI缩放设置
# QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

class WaterReminderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("喝水提醒")
        self.setGeometry(100, 100, 400, 300)

        # 设置窗口图标
        icon_path = os.path.abspath(r'ico\icon.ico')
        
        # 检查图标文件是否存在
        if not os.path.exists(icon_path):
            QMessageBox.critical(self, '错误', f'图标文件不存在: {icon_path}')
            # 创建一个红色图标作为备用
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.red)
            self.setWindowIcon(QIcon(pixmap))
        else:
            # 尝试加载图标
            icon = QIcon(icon_path)
            if icon.isNull():
                QMessageBox.critical(self, '错误', f'无法加载图标文件: {icon_path}')
                # 创建一个红色图标作为备用
                pixmap = QPixmap(32, 32)
                pixmap.fill(Qt.red)
                self.setWindowIcon(QIcon(pixmap))
            else:
                self.setWindowIcon(icon)

        # 加载配置
        self.config = self.load_config()
        self.daily_limit = self.config.get('daily_limit', 3000)
        self.drink_amount = self.config.get('drink_amount', 300)

        # 初始化今日喝水量
        self.today_drunk = 0
        self.today = datetime.date.today()
        self.load_drinking_history()

        # 创建UI
        self.init_ui()

        # 设置定时提醒
        self.set_reminder()

        # 初始化系统托盘
        self.init_system_tray()

    def load_config(self):
        """加载配置文件，如果不存在则创建默认配置"""
        try:
            # 获取程序所在目录的绝对路径
            app_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(app_dir, 'config.json')

            # 确保目录存在
            os.makedirs(app_dir, exist_ok=True)

            # 如果配置文件不存在，创建默认配置
            if not os.path.exists(config_path):
                default_config = {
                    "daily_limit": 3000,
                    "drink_amount": 300,
                    "reminder_interval": 30
                }
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
                print(f'配置文件已创建: {config_path}')
                # QMessageBox.information(self, '配置创建', f'配置文件已创建: {config_path}')
                return default_config
            else:
                # 加载现有配置
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 确保配置有所有必要的键
                    required_keys = ['daily_limit', 'drink_amount', 'reminder_interval']
                    for key in required_keys:
                        if key not in config:
                            config[key] = 3000 if key == 'daily_limit' else 300 if key == 'drink_amount' else 30
                    # 保存更新后的配置
                    with open(config_path, 'w', encoding='utf-8') as f_update:
                        json.dump(config, f_update, ensure_ascii=False, indent=2)
                    return config
        except Exception as e:
            print(f'加载或创建配置文件失败: {str(e)}')
            # QMessageBox.critical(self, '配置错误', f'加载或创建配置文件失败: {str(e)}')
            # 返回默认配置以确保程序可以运行
            return {
                "daily_limit": 3000,
                "drink_amount": 300,
                "reminder_interval": 30
            }

    def load_drinking_history(self):
        """加载今日喝水记录"""
        history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'drinking_history.json')
        if os.path.exists(history_path):
            with open(history_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if str(self.today) in data:
                    self.today_drunk = data[str(self.today)]

    def save_drinking_history(self):
        """保存今日喝水记录"""
        history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'drinking_history.json')
        data = {}
        if os.path.exists(history_path):
            with open(history_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        data[str(self.today)] = self.today_drunk
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def init_ui(self):
        """初始化UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(20)

        # 标题
        title_label = QLabel("喝水提醒")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # 水瓶UI组件
        self.water_bottle = WaterBottleWidget()
        self.water_bottle.set_values(self.today_drunk, self.daily_limit)
        main_layout.addWidget(self.water_bottle, alignment=Qt.AlignCenter)

        # 今日喝水量
        self.water_label = QLabel(f"今日已喝水: {self.today_drunk}ml / {self.daily_limit}ml")
        self.water_label.setAlignment(Qt.AlignCenter)
        self.water_label.setFont(QFont("SimHei", 12))
        main_layout.addWidget(self.water_label)

        # 喝水按钮
        self.drink_button = QPushButton(f"喝了{self.drink_amount}ml")
        self.drink_button.setFont(QFont("SimHei", 12))
        self.drink_button.setMinimumHeight(40)
        self.drink_button.clicked.connect(self.record_drink)
        main_layout.addWidget(self.drink_button)

        # 清空记录按钮
        self.clear_button = QPushButton("清空今日记录")
        self.clear_button.setFont(QFont("SimHei", 12))
        self.clear_button.setMinimumHeight(40)
        self.clear_button.clicked.connect(self.clear_today_history)
        main_layout.addWidget(self.clear_button)

        # 进度显示
        progress_layout = QHBoxLayout()
        self.progress_label = QLabel("进度:")
        self.progress_label.setFont(QFont("SimHei", 12))
        self.progress_value = QLabel(f"{int(self.today_drunk/self.daily_limit*100)}%")
        self.progress_value.setFont(QFont("SimHei", 12))
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_value)
        main_layout.addLayout(progress_layout)

        # 状态信息
        self.status_label = QLabel("下一次提醒: " + self.get_next_reminder_time())
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("SimHei", 10))
        main_layout.addWidget(self.status_label)

    def get_next_reminder_time(self):
        """获取下一次提醒时间"""
        now = datetime.datetime.now()
        next_hour = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
        return next_hour.strftime("%H:%M")

    def set_reminder(self):
        """设置定时提醒"""
        now = datetime.datetime.now()
        next_reminder = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
        seconds_until_reminder = (next_reminder - now).total_seconds()

        # 设置定时器
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.show_reminder)
        self.timer.start(int(seconds_until_reminder * 1000))

        # 更新状态标签
        self.status_label.setText("下一次提醒: " + next_reminder.strftime("%H:%M"))

    def show_reminder(self):
        """显示提醒对话框"""
        # 获取Windows用户名
        import getpass
        username = getpass.getuser()

        msg_box = QMessageBox()
        msg_box.setWindowTitle("喝水提醒")
        msg_box.setText(f"{username}，该喝水啦！\n今日已喝水: {self.today_drunk}ml / {self.daily_limit}ml")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.addButton(QPushButton(f"喝了{self.drink_amount}ml"), QMessageBox.YesRole)
        msg_box.addButton(QPushButton("稍后提醒"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("忽略"), QMessageBox.RejectRole)

        # 确保中文显示正常
        font = QFont("SimHei", 10)
        msg_box.setFont(font)

        # 显示对话框并获取用户选择
        result = msg_box.exec()

        if result == QMessageBox.YesRole:
            self.record_drink()
        elif result == QMessageBox.NoRole:
            # 10分钟后再次提醒
            self.timer.start(10 * 60 * 1000)
            next_reminder = datetime.datetime.now() + datetime.timedelta(minutes=10)
            self.status_label.setText("下一次提醒: " + next_reminder.strftime("%H:%M"))
            return

        # 设置下一次整点提醒
        self.set_reminder()

    def record_drink(self):
        """记录喝水量"""
        # 检查是否跨天
        if datetime.date.today() != self.today:
            self.today = datetime.date.today()
            self.today_drunk = 0

        self.today_drunk += self.drink_amount
        if self.today_drunk > self.daily_limit:
            self.today_drunk = self.daily_limit

        # 更新UI
        self.water_label.setText(f"今日已喝水: {self.today_drunk}ml / {self.daily_limit}ml")
        self.progress_value.setText(f"{int(self.today_drunk/self.daily_limit*100)}%")
        self.water_bottle.set_values(self.today_drunk, self.daily_limit)

        # 保存记录
        self.save_drinking_history()

        # 显示提示
        # 直接设置通知图标
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("记录成功")
        msg_box.setText(f"已记录{self.drink_amount}ml饮水量")
        
        # 使用与主窗口相同的图标路径
        icon_path = os.path.abspath(r'ico\icon.ico')
        if os.path.exists(icon_path) and not QIcon(icon_path).isNull():
            msg_box.setWindowIcon(QIcon(icon_path))
            # 同时设置消息框的图标
            msg_box.setIconPixmap(QPixmap(icon_path).scaled(32, 32))
        else:
            # 使用红色备用图标
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.red)
            msg_box.setWindowIcon(QIcon(pixmap))
            msg_box.setIconPixmap(pixmap)
            
        msg_box.exec()

    def init_system_tray(self):
        # 检查系统是否支持托盘
        if not QSystemTrayIcon.isSystemTrayAvailable():            return

        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        # 使用ico目录下的icon.ico - 使用绝对路径
        icon_path = os.path.abspath('ico\\icon.ico')
        
        # 检查图标文件是否存在
        if not os.path.exists(icon_path):
            QMessageBox.critical(self, '错误', f'图标文件不存在: {icon_path}')
            # 创建一个红色图标作为备用
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.red)
            self.tray_icon.setIcon(QIcon(pixmap))
        else:
            # 尝试加载图标
            icon = QIcon(icon_path)
            if icon.isNull():
                QMessageBox.critical(self, '错误', f'无法加载图标文件: {icon_path}')
                # 创建一个红色图标作为备用
                pixmap = QPixmap(32, 32)
                pixmap.fill(Qt.red)
                self.tray_icon.setIcon(QIcon(pixmap))
            else:
                self.tray_icon.setIcon(icon)
                
        self.tray_icon.setToolTip('喝水提醒')

        # 创建右键菜单
        tray_menu = QMenu(self)

        # 快捷喝水动作
        quick_drink_action = QAction('快捷喝水(300ml)', self)
        quick_drink_action.triggered.connect(self.record_drink)
        tray_menu.addAction(quick_drink_action)

        # 删除存档动作
        delete_history_action = QAction('删除存档', self)
        delete_history_action.triggered.connect(self.clear_today_history)
        tray_menu.addAction(delete_history_action)

        # 开机自启动动作
        self.startup_action = QAction('开机自启动', self)
        self.startup_action.setCheckable(True)
        self.startup_action.setChecked(self.is_startup_enabled())
        self.startup_action.triggered.connect(self.toggle_startup)
        tray_menu.addAction(self.startup_action)

        # 退出程序动作
        exit_action = QAction('退出程序', self)
        exit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(exit_action)

        # 设置托盘菜单
        self.tray_icon.setContextMenu(tray_menu)

        # 连接托盘点击事件
        self.tray_icon.activated.connect(self.on_tray_activated)

        # 显示托盘图标
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        # 左键点击显示/隐藏窗口
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()

    def closeEvent(self, event):
        # 重写关闭事件，最小化到托盘
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            '喝水提醒',
            '程序已最小化到托盘',
            QSystemTrayIcon.Information,
            2000
        )

    def is_startup_enabled(self):
        # 检查是否启用了开机自启动
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, 'WaterReminder')
            winreg.CloseKey(key)
            return value == sys.executable
        except (FileNotFoundError, OSError):
            return False

    def toggle_startup(self, checked):
        # 切换开机自启动状态
        try:
            if checked:
                # 添加到开机自启动
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, 'WaterReminder', 0, winreg.REG_SZ, sys.executable)
                winreg.CloseKey(key)
                QMessageBox.information(self, '操作成功', '已启用开机自启动')
            else:
                # 移除开机自启动
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(key, 'WaterReminder')
                winreg.CloseKey(key)
                QMessageBox.information(self, '操作成功', '已禁用开机自启动')
        except OSError as e:
            QMessageBox.critical(self, '操作失败', f'无法修改开机自启动设置: {str(e)}')

    def quit_application(self):
        # 退出程序
        reply = QMessageBox.question(self, '确认退出', '确定要退出程序吗？',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            QApplication.quit()

    def clear_today_history(self):
        """清空今日喝水记录"""
        # 确认对话框
        reply = QMessageBox.question(self, '确认清空', '确定要清空今日喝水记录吗？',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 重置今日喝水量
            self.today_drunk = 0
            
            # 更新UI
            self.water_label.setText(f"今日已喝水: {self.today_drunk}ml / {self.daily_limit}ml")
            self.progress_value.setText(f"{int(self.today_drunk/self.daily_limit*100)}%")
            self.water_bottle.set_values(self.today_drunk, self.daily_limit)
            
            # 更新历史记录
            self.save_drinking_history()
            
            # 显示提示
            QMessageBox.information(self, "操作成功", "今日喝水记录已清空")

def check_if_already_running():
    """检查程序是否已经在运行"""
    # 获取当前进程ID
    current_pid = os.getpid()
    # 获取当前进程名称
    current_process_name = psutil.Process(current_pid).name()

    # 遍历所有进程
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            proc_info = proc.info
            # 跳过当前进程
            if proc_info['pid'] == current_pid:
                continue
            # 检查进程名称是否相同
            if proc_info['name'] == current_process_name or proc_info['name'] == 'WaterReminder.exe':
                # 尝试获取窗口并激活
                try:
                    # 使用Windows API激活窗口
                    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 9)  # SW_RESTORE
                    ctypes.windll.user32.SetForegroundWindow(ctypes.windll.kernel32.GetConsoleWindow())
                except:
                    pass
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

if __name__ == "__main__":
    # 检查程序是否已经在运行
    if check_if_already_running():
        sys.exit(0)

    # 允许中文显示
    QCoreApplication.setApplicationName("喝水提醒")
    app = QApplication(sys.argv)
    # 设置应用程序样式
    app.setStyle('Fusion')
    window = WaterReminderApp()
    window.show()
    sys.exit(app.exec())