# -*- coding: utf-8 -*-
"""
Google Drive Mounter GUI - Google Drive 드라이브 마운트 도구
rclone을 사용한 간편한 Google Drive 마운트 GUI
"""

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QGroupBox, QFormLayout, QTextEdit, QMessageBox,
    QFrame, QListWidget, QFileDialog, QTabWidget, QRadioButton,
    QProgressBar, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from gdrive_mounter import (GDriveMounter, MountConfig, get_rclone_version,
                            is_winfsp_installed, check_and_install_winfsp)
from config_manager import ConfigManager, ConnectionConfig
from autostart_manager import AutostartManager
from file_transfer import FileTransfer, TransferThread


def is_dark_mode() -> bool:
    """Windows OS 다크 모드 설정 감지"""
    try:
        import winreg
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(
            registry,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        # 0 = 다크 모드, 1 = 라이트 모드
        return value == 0
    except Exception:
        # 기본값: 다크 모드
        return True


def get_theme_stylesheet(theme_setting: str) -> str:
    """
    테마 설정에 따른 스타일시트 반환

    Args:
        theme_setting: "auto", "light", "dark"

    Returns:
        스타일시트 문자열
    """
    if theme_setting == "auto":
        use_dark = is_dark_mode()
    elif theme_setting == "dark":
        use_dark = True
    else:  # "light"
        use_dark = False

    if use_dark:
        return _get_dark_stylesheet()
    else:
        return _get_light_stylesheet()


def _get_light_stylesheet() -> str:
    """라이트 모드 스타일시트"""
    return """
        QMainWindow {
            background-color: #f5f5f5;
        }
        QWidget {
            font-family: "Segoe UI", "맑은 고딕", sans-serif;
            font-size: 10pt;
            color: #1e1e1e;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #d4d4d4;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 10px;
            background-color: #ffffff;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: #0078d4;
        }
        QLineEdit, QSpinBox, QComboBox {
            min-height: 32px;
            padding: 8px;
            border: 1px solid #d4d4d4;
            border-radius: 6px;
            background-color: #ffffff;
            color: #1e1e1e;
            selection-background-color: #0078d4;
        }
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
            border-color: #0078d4;
        }
        QPushButton {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            background-color: #e0e0e0;
            color: #1e1e1e;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #d0d0d0;
        }
        QPushButton:pressed {
            background-color: #c0c0c0;
        }
        QPushButton:disabled {
            background-color: #f0f0f0;
            color: #a0a0a0;
        }
        QPushButton#primaryButton {
            background-color: #0078d4;
            color: #ffffff;
        }
        QPushButton#primaryButton:hover {
            background-color: #106ebe;
        }
        QPushButton#loginButton {
            background-color: #107c10;
            color: #ffffff;
        }
        QPushButton#loginButton:hover {
            background-color: #0e6b0e;
        }
        QPushButton#warningButton {
            background-color: #d13438;
            color: #ffffff;
        }
        QPushButton#warningButton:hover {
            background-color: #a52a2a;
        }
        QRadioButton, QCheckBox {
            spacing: 8px;
        }
        QRadioButton::indicator, QCheckBox::indicator {
            width: 18px;
            height: 18px;
        }
        QTextEdit {
            border: 1px solid #d4d4d4;
            border-radius: 6px;
            background-color: #ffffff;
            color: #1e1e1e;
            font-family: "Consolas", "D2Coding", monospace;
            font-size: 9pt;
        }
        #statusFrame {
            background-color: #ffffff;
            border: 1px solid #d4d4d4;
            border-radius: 6px;
            padding: 10px;
        }
        #statusLabel {
            font-weight: bold;
        }
        #authStatusLabel {
            font-weight: bold;
            font-size: 11pt;
        }
        QComboBox::drop-down {
            border: none;
            width: 30px;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #1e1e1e;
        }
        QComboBox QAbstractItemView {
            background-color: #ffffff;
            border: 1px solid #d4d4d4;
            selection-background-color: #0078d4;
            selection-color: #ffffff;
        }
        QListWidget {
            background-color: #ffffff;
            border: 1px solid #d4d4d4;
            border-radius: 6px;
            color: #1e1e1e;
        }
        QListWidget::item:selected {
            background-color: #0078d4;
            color: #ffffff;
        }
    """


def _get_dark_stylesheet() -> str:
    """다크 모드 스타일시트 (Catppuccin Mocha)"""
    return """
        QMainWindow {
            background-color: #1e1e2e;
        }
        QWidget {
            font-family: "Segoe UI", "맑은 고딕", sans-serif;
            font-size: 10pt;
            color: #cdd6f4;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #45475a;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 10px;
            background-color: #313244;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: #89b4fa;
        }
        QLineEdit, QSpinBox, QComboBox {
            min-height: 32px;
            padding: 8px;
            border: 1px solid #45475a;
            border-radius: 6px;
            background-color: #1e1e2e;
            color: #cdd6f4;
            selection-background-color: #89b4fa;
        }
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
            border-color: #89b4fa;
        }
        QPushButton {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            background-color: #45475a;
            color: #cdd6f4;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #585b70;
        }
        QPushButton:pressed {
            background-color: #313244;
        }
        QPushButton:disabled {
            background-color: #313244;
            color: #6c7086;
        }
        QPushButton#primaryButton {
            background-color: #89b4fa;
            color: #1e1e2e;
        }
        QPushButton#primaryButton:hover {
            background-color: #b4befe;
        }
        QPushButton#loginButton {
            background-color: #a6e3a1;
            color: #1e1e2e;
        }
        QPushButton#loginButton:hover {
            background-color: #94e2d5;
        }
        QPushButton#warningButton {
            background-color: #f38ba8;
            color: #1e1e2e;
        }
        QPushButton#warningButton:hover {
            background-color: #eba0ac;
        }
        QRadioButton, QCheckBox {
            spacing: 8px;
        }
        QRadioButton::indicator, QCheckBox::indicator {
            width: 18px;
            height: 18px;
        }
        QTextEdit {
            border: 1px solid #45475a;
            border-radius: 6px;
            background-color: #1e1e2e;
            color: #a6adc8;
            font-family: "Consolas", "D2Coding", monospace;
            font-size: 9pt;
        }
        #statusFrame {
            background-color: #313244;
            border-radius: 6px;
            padding: 10px;
        }
        #statusLabel {
            font-weight: bold;
        }
        #authStatusLabel {
            font-weight: bold;
            font-size: 11pt;
        }
        QComboBox::drop-down {
            border: none;
            width: 30px;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #cdd6f4;
        }
        QComboBox QAbstractItemView {
            background-color: #1e1e2e;
            border: 1px solid #45475a;
            selection-background-color: #89b4fa;
            selection-color: #1e1e2e;
        }
        QListWidget {
            background-color: #1e1e2e;
            border: 1px solid #45475a;
            border-radius: 6px;
            color: #cdd6f4;
        }
        QListWidget::item:selected {
            background-color: #89b4fa;
            color: #1e1e2e;
        }
    """


class AuthThread(QThread):
    """Google 인증을 위한 백그라운드 스레드"""
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)
    
    def __init__(self, mounter: GDriveMounter):
        super().__init__()
        self.mounter = mounter
    
    def run(self):
        success, message = self.mounter.authenticate_interactive(
            progress_callback=lambda msg: self.progress.emit(msg)
        )
        self.finished.emit(success, message)


class MainWindow(QMainWindow):
    """메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        
        self.mounter = GDriveMounter()
        self.config_manager = ConfigManager()
        self.autostart_manager = AutostartManager()
        self.auth_thread: AuthThread = None
        self.file_transfer = FileTransfer(
            self.mounter.rclone_path,
            self.mounter.rclone_config_path
        )
        self.transfer_thread: TransferThread = None
        
        self.init_ui()
        self.load_config()
        self.detect_existing_mount()  # 기존 마운트 감지
        self.update_status()
        self.update_auth_status()
        
        # 상태 체크 타이머
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)  # 5초마다 상태 체크
    
    def detect_existing_mount(self):
        """이미 마운트된 rclone 드라이브 감지"""
        mounted = self.mounter.find_mounted_drives()
        if mounted:
            # 첫 번째 마운트된 드라이브를 현재 드라이브로 설정
            self.mounter.current_drive = mounted[0][0]
            self.log(f"ℹ️ 기존 마운트 감지: {mounted[0][0]} (PID: {mounted[0][1]})")
    
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("Google Drive Mounter - 클라우드 드라이브 마운트")
        self.setFixedSize(900, 600)
        
        # 메인 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 탭 위젯 생성
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # 탭 1: 마운트
        self.mount_tab = QWidget()
        self.tab_widget.addTab(self.mount_tab, "드라이브 마운트")
        self.init_mount_tab()

        # 탭 2: 파일 전송
        self.transfer_tab = QWidget()
        self.tab_widget.addTab(self.transfer_tab, "파일 전송")
        self.init_transfer_tab()

        # 스타일 설정 (초기 테마는 나중에 load_config에서 설정됨)
        pass

    def init_mount_tab(self):
        """마운트 탭 초기화"""
        mount_layout = QHBoxLayout(self.mount_tab)
        mount_layout.setSpacing(15)
        mount_layout.setContentsMargins(10, 10, 10, 10)

        # === 왼쪽 패널 ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(15)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Google 계정 인증 그룹
        auth_group = QGroupBox("Google 계정")
        auth_layout = QVBoxLayout()
        auth_layout.setSpacing(10)
        
        # 인증 상태 표시
        auth_status_layout = QHBoxLayout()
        self.auth_status_label = QLabel("⚪ 연결 안됨")
        self.auth_status_label.setObjectName("authStatusLabel")
        self.account_info_label = QLabel("")
        self.account_info_label.setStyleSheet("color: #a6adc8;")
        auth_status_layout.addWidget(self.auth_status_label)
        auth_status_layout.addWidget(self.account_info_label)
        auth_status_layout.addStretch()
        auth_layout.addLayout(auth_status_layout)
        
        # 인증 버튼
        auth_btn_layout = QHBoxLayout()
        self.login_btn = QPushButton("🔐 Google 로그인")
        self.login_btn.setObjectName("loginButton")
        self.login_btn.clicked.connect(self.do_login)
        
        self.logout_btn = QPushButton("연결 해제")
        self.logout_btn.clicked.connect(self.do_logout)
        self.logout_btn.setEnabled(False)
        
        auth_btn_layout.addWidget(self.login_btn)
        auth_btn_layout.addWidget(self.logout_btn)
        auth_btn_layout.addStretch()
        auth_layout.addLayout(auth_btn_layout)
        
        auth_group.setLayout(auth_layout)
        left_layout.addWidget(auth_group)

        # 드라이브 설정 그룹
        drive_group = QGroupBox("드라이브 설정")
        drive_layout = QFormLayout()
        drive_layout.setSpacing(10)
        drive_layout.setVerticalSpacing(15)
        drive_layout.setContentsMargins(15, 20, 15, 15)
        
        # 드라이브 문자
        self.drive_combo = QComboBox()
        self.refresh_available_drives()
        drive_layout.addRow("드라이브 문자:", self.drive_combo)
        
        # 드라이브 이름
        self.volume_name_input = QLineEdit()
        self.volume_name_input.setText("Google Drive")
        self.volume_name_input.setPlaceholderText("탐색기에 표시될 이름")
        drive_layout.addRow("드라이브 이름:", self.volume_name_input)

        # 테마 선택
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["자동 (시스템 설정)", "라이트 모드", "다크 모드"])
        self.theme_combo.currentTextChanged.connect(self.apply_theme)
        drive_layout.addRow("테마:", self.theme_combo)

        drive_group.setLayout(drive_layout)
        left_layout.addWidget(drive_group)

        # 자동 시작
        autostart_widget = QWidget()
        autostart_layout = QHBoxLayout(autostart_widget)
        autostart_layout.setContentsMargins(0, 5, 0, 5)
        
        self.autostart_check = QCheckBox("Windows 시작 시 자동 마운트")
        autostart_layout.addWidget(self.autostart_check)
        autostart_layout.addStretch()

        left_layout.addWidget(autostart_widget)
        left_layout.addStretch()

        # === 오른쪽 패널 ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 상태 표시
        status_frame = QFrame()
        status_frame.setObjectName("statusFrame")
        status_layout = QHBoxLayout(status_frame)
        
        status_label = QLabel("마운트 상태:")
        self.status_display = QLabel("연결 안됨")
        self.status_display.setObjectName("statusLabel")
        
        status_layout.addWidget(status_label)
        status_layout.addWidget(self.status_display)
        status_layout.addStretch()

        right_layout.addWidget(status_frame)

        # 활성 연결 관리
        active_group = QGroupBox("활성 연결")
        active_layout = QVBoxLayout()
        active_layout.setSpacing(8)
        
        # 마운트된 드라이브 목록
        self.mounted_list = QListWidget()
        self.mounted_list.setMaximumHeight(80)
        active_layout.addWidget(self.mounted_list)

        # 해제 버튼 영역
        unmount_btn_layout = QHBoxLayout()
        self.unmount_selected_btn = QPushButton("선택 해제")
        self.unmount_selected_btn.clicked.connect(self.unmount_selected)
        self.unmount_all_btn = QPushButton("전체 해제")
        self.unmount_all_btn.setObjectName("warningButton")
        self.unmount_all_btn.clicked.connect(self.unmount_all)
        unmount_btn_layout.addWidget(self.unmount_selected_btn)
        unmount_btn_layout.addWidget(self.unmount_all_btn)
        unmount_btn_layout.addStretch()
        active_layout.addLayout(unmount_btn_layout)
        
        active_group.setLayout(active_layout)
        right_layout.addWidget(active_group)

        # 버튼 영역
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setSpacing(10)
        
        self.save_btn = QPushButton("설정 저장")
        self.save_btn.clicked.connect(self.save_config)
        
        self.mount_btn = QPushButton("마운트")
        self.mount_btn.setObjectName("primaryButton")
        self.mount_btn.clicked.connect(self.toggle_mount)
        
        self.refresh_btn = QPushButton("드라이브 새로고침")
        self.refresh_btn.clicked.connect(self.refresh_available_drives)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.mount_btn)

        right_layout.addWidget(button_widget)

        # 로그 영역
        log_group = QGroupBox("로그")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)

        # 패널 추가
        mount_layout.addWidget(left_panel, 1)
        mount_layout.addWidget(right_panel, 1)

        # rclone 버전 표시
        version = get_rclone_version(self.mounter.rclone_path)
        if version:
            self.log(f"rclone 준비됨: {version}")
        else:
            self.log("⚠️ rclone을 찾을 수 없습니다!")
    
    def apply_theme(self):
        """테마 적용"""
        theme_text = self.theme_combo.currentText()
        theme_map = {
            "자동 (시스템 설정)": "auto",
            "라이트 모드": "light",
            "다크 모드": "dark"
        }
        theme_setting = theme_map.get(theme_text, "auto")
        stylesheet = get_theme_stylesheet(theme_setting)
        self.setStyleSheet(stylesheet)

    def init_transfer_tab(self):
        """파일 전송 탭 초기화"""
        transfer_layout = QVBoxLayout(self.transfer_tab)
        transfer_layout.setSpacing(15)
        transfer_layout.setContentsMargins(10, 10, 10, 10)

        # === 마운트 상태 및 언마운트 ===
        mount_status_group = QGroupBox("현재 마운트 상태")
        mount_status_layout = QVBoxLayout()

        # 마운트된 드라이브 목록 (읽기 전용)
        self.transfer_mounted_list = QListWidget()
        self.transfer_mounted_list.setMaximumHeight(80)
        mount_status_layout.addWidget(self.transfer_mounted_list)

        # 빠른 언마운트 버튼
        quick_unmount_layout = QHBoxLayout()
        self.quick_unmount_btn = QPushButton("선택된 드라이브 언마운트")
        self.quick_unmount_btn.clicked.connect(self.quick_unmount_drive)
        quick_unmount_layout.addWidget(self.quick_unmount_btn)
        quick_unmount_layout.addStretch()
        mount_status_layout.addLayout(quick_unmount_layout)

        mount_status_group.setLayout(mount_status_layout)
        transfer_layout.addWidget(mount_status_group)

        # === 전송 설정 ===
        transfer_settings_group = QGroupBox("파일 전송")
        transfer_settings_layout = QVBoxLayout()

        # 방향 선택
        direction_layout = QHBoxLayout()
        direction_layout.addWidget(QLabel("전송 방향:"))
        self.upload_radio = QRadioButton("업로드 (로컬 → 드라이브)")
        self.download_radio = QRadioButton("다운로드 (드라이브 → 로컬)")
        self.upload_radio.setChecked(True)
        self.upload_radio.toggled.connect(self.on_direction_changed)
        direction_layout.addWidget(self.upload_radio)
        direction_layout.addWidget(self.download_radio)
        direction_layout.addStretch()
        transfer_settings_layout.addLayout(direction_layout)

        # 소스 경로
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("소스:"))
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("소스 경로")
        self.source_browse_btn = QPushButton("찾아보기")
        self.source_browse_btn.clicked.connect(self.browse_source)
        source_layout.addWidget(self.source_input, 1)
        source_layout.addWidget(self.source_browse_btn)
        transfer_settings_layout.addLayout(source_layout)

        # 대상 경로
        dest_layout = QHBoxLayout()
        dest_layout.addWidget(QLabel("대상:"))
        self.dest_input = QLineEdit()
        self.dest_input.setPlaceholderText("대상 경로")
        self.dest_browse_btn = QPushButton("찾아보기")
        self.dest_browse_btn.clicked.connect(self.browse_dest)
        dest_layout.addWidget(self.dest_input, 1)
        dest_layout.addWidget(self.dest_browse_btn)
        transfer_settings_layout.addLayout(dest_layout)

        transfer_settings_group.setLayout(transfer_settings_layout)
        transfer_layout.addWidget(transfer_settings_group)

        # === 진행률 ===
        progress_group = QGroupBox("전송 진행률")
        progress_layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)

        self.transfer_stats_label = QLabel("준비됨")
        self.transfer_stats_label.setWordWrap(True)
        progress_layout.addWidget(self.transfer_stats_label)

        progress_group.setLayout(progress_layout)
        transfer_layout.addWidget(progress_group)

        # === 버튼 ===
        transfer_btn_layout = QHBoxLayout()
        self.start_transfer_btn = QPushButton("전송 시작")
        self.start_transfer_btn.setObjectName("primaryButton")
        self.start_transfer_btn.clicked.connect(self.start_transfer)
        self.cancel_transfer_btn = QPushButton("취소")
        self.cancel_transfer_btn.setEnabled(False)
        self.cancel_transfer_btn.clicked.connect(self.cancel_transfer)
        transfer_btn_layout.addStretch()
        transfer_btn_layout.addWidget(self.start_transfer_btn)
        transfer_btn_layout.addWidget(self.cancel_transfer_btn)
        transfer_layout.addLayout(transfer_btn_layout)

        transfer_layout.addStretch()

    def log(self, message: str):
        """로그 메시지 추가"""
        self.log_text.append(message)
        # 스크롤을 맨 아래로
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def refresh_available_drives(self):
        """사용 가능한 드라이브 목록 갱신"""
        current = self.drive_combo.currentText()
        self.drive_combo.clear()
        
        available = self.mounter.get_available_drives()
        self.drive_combo.addItems(available)
        
        # 이전 선택 복원 시도
        index = self.drive_combo.findText(current)
        if index >= 0:
            self.drive_combo.setCurrentIndex(index)
    
    def update_auth_status(self):
        """인증 상태 UI 업데이트"""
        if self.mounter.is_authenticated():
            self.auth_status_label.setText("🟢 연결됨")
            self.auth_status_label.setStyleSheet("color: #a6e3a1; font-weight: bold;")
            
            # 계정 정보 표시
            info = self.mounter.get_account_info()
            if info:
                self.account_info_label.setText(f"({info})")
            
            self.login_btn.setEnabled(False)
            self.logout_btn.setEnabled(True)
            self.mount_btn.setEnabled(True)
        else:
            self.auth_status_label.setText("⚪ 연결 안됨")
            self.auth_status_label.setStyleSheet("color: #a6adc8; font-weight: bold;")
            self.account_info_label.setText("")
            
            self.login_btn.setEnabled(True)
            self.logout_btn.setEnabled(False)
            self.mount_btn.setEnabled(False)
    
    def do_login(self):
        """Google 로그인 실행"""
        self.log("Google 로그인 시작...")
        self.login_btn.setEnabled(False)
        self.login_btn.setText("로그인 중...")
        
        # 백그라운드 스레드에서 인증 실행
        self.auth_thread = AuthThread(self.mounter)
        self.auth_thread.progress.connect(self.log)
        self.auth_thread.finished.connect(self.on_auth_finished)
        self.auth_thread.start()
    
    def on_auth_finished(self, success: bool, message: str):
        """인증 완료 콜백"""
        self.login_btn.setText("🔐 Google 로그인")
        
        if success:
            self.log(f"✓ {message}")
        else:
            self.log(f"✗ {message}")
            self.login_btn.setEnabled(True)
        
        self.update_auth_status()
    
    def do_logout(self):
        """Google 연결 해제"""
        reply = QMessageBox.question(
            self, "연결 해제 확인",
            "Google Drive 연결을 해제하시겠습니까?\n\n"
            "마운트된 드라이브가 있다면 먼저 해제됩니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 마운트 해제
        if self.mounter.is_mounted():
            self.do_unmount()
        
        # 로그아웃
        success, message = self.mounter.logout()
        
        if success:
            self.log(f"✓ {message}")
        else:
            self.log(f"✗ {message}")
        
        self.update_auth_status()
    
    def load_config(self):
        """저장된 설정 불러오기"""
        config = self.config_manager.load()

        # 드라이브 문자 설정
        index = self.drive_combo.findText(config.drive_letter)
        if index >= 0:
            self.drive_combo.setCurrentIndex(index)

        self.volume_name_input.setText(config.volume_name)
        self.autostart_check.setChecked(config.auto_mount)

        # 테마 설정
        theme_map = {
            "auto": "자동 (시스템 설정)",
            "light": "라이트 모드",
            "dark": "다크 모드"
        }
        theme_text = theme_map.get(config.theme, "자동 (시스템 설정)")
        theme_index = self.theme_combo.findText(theme_text)
        if theme_index >= 0:
            self.theme_combo.setCurrentIndex(theme_index)

        # 테마 적용
        self.apply_theme()

        self.log("설정을 불러왔습니다.")
    
    def save_config(self):
        """현재 설정 저장"""
        # 테마 설정 변환
        theme_text = self.theme_combo.currentText()
        theme_map = {
            "자동 (시스템 설정)": "auto",
            "라이트 모드": "light",
            "다크 모드": "dark"
        }
        theme_value = theme_map.get(theme_text, "auto")

        config = ConnectionConfig(
            drive_letter=self.drive_combo.currentText(),
            volume_name=self.volume_name_input.text().strip() or "Google Drive",
            auto_mount=self.autostart_check.isChecked(),
            theme=theme_value
        )
        
        if self.config_manager.save(config):
            self.log("✓ 설정이 저장되었습니다.")
            
            # 자동 시작 설정
            if config.auto_mount:
                self.autostart_manager.create_startup_script(
                    self.config_manager.get_config_path()
                )
                success, msg = self.autostart_manager.register_autostart()
                self.log(f"{'✓' if success else '✗'} {msg}")
            else:
                success, msg = self.autostart_manager.unregister_autostart()
                if success:
                    self.log("✓ 자동 시작이 해제되었습니다.")
        else:
            self.log("✗ 설정 저장에 실패했습니다.")
    
    def toggle_mount(self):
        """마운트/언마운트 토글"""
        if self.mounter.is_mounted():
            self.do_unmount()
        else:
            self.do_mount()
    
    def do_mount(self):
        """마운트 실행"""
        # WinFsp 확인
        if not is_winfsp_installed():
            self.log("⚠️ WinFsp가 설치되어 있지 않습니다.")
            
            reply = QMessageBox.question(
                self, "WinFsp 필요",
                "rclone 마운트에 필요한 WinFsp가 설치되어 있지 않습니다.\n\n"
                "winget을 사용하여 자동으로 설치하시겠습니까?\n"
                "(관리자 권한이 필요할 수 있습니다)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.log("WinFsp 설치 시도 중...")
                self.mount_btn.setEnabled(False)
                QApplication.processEvents()  # UI 업데이트
                
                success, message = check_and_install_winfsp(
                    auto_install=True,
                    progress_callback=self.log
                )
                
                self.mount_btn.setEnabled(True)
                
                if success:
                    self.log(f"✓ {message}")
                else:
                    self.log(f"✗ {message}")
                    QMessageBox.warning(
                        self, "WinFsp 설치 실패",
                        f"{message}\n\n수동 설치: https://winfsp.dev/rel/"
                    )
                    return
            else:
                QMessageBox.information(
                    self, "WinFsp 필요",
                    "WinFsp를 수동으로 설치한 후 다시 시도해주세요.\n\n"
                    "다운로드: https://winfsp.dev/rel/"
                )
                return
        
        # 인증 확인
        if not self.mounter.is_authenticated():
            QMessageBox.warning(self, "로그인 필요", "먼저 Google 로그인이 필요합니다.")
            return

        # 마운트 설정 생성
        mount_config = MountConfig(
            drive_letter=self.drive_combo.currentText(),
            volume_name=self.volume_name_input.text().strip() or "Google Drive"
        )

        self.log(f"마운트 시도 중... ({mount_config.drive_letter})")
        self.mount_btn.setEnabled(False)

        # 마운트 실행
        success, message = self.mounter.mount(mount_config)
        
        if success:
            self.log(f"✓ {message}")
            self.update_status()
        else:
            self.log(f"✗ {message}")
        
        self.mount_btn.setEnabled(True)
    
    def do_unmount(self):
        """언마운트 실행"""
        self.log("언마운트 중...")
        self.mount_btn.setEnabled(False)
        
        success, message = self.mounter.unmount()
        
        if success:
            self.log(f"✓ {message}")
        else:
            self.log(f"✗ {message}")
        
        self.update_status()
        self.mount_btn.setEnabled(True)
        self.refresh_available_drives()
    
    def refresh_mounted_list(self):
        """마운트된 드라이브 목록 갱신"""
        self.mounted_list.clear()
        mounted = self.mounter.find_mounted_drives()

        if not mounted:
            self.mounted_list.addItem("(마운트된 드라이브 없음)")
            self.unmount_selected_btn.setEnabled(False)
            self.unmount_all_btn.setEnabled(False)
        else:
            for drive, pid in mounted:
                self.mounted_list.addItem(f"{drive} (PID: {pid})")
            self.unmount_selected_btn.setEnabled(True)
            self.unmount_all_btn.setEnabled(True)

        # 파일 전송 탭의 목록도 갱신
        self.refresh_transfer_mounted_list()
    
    def unmount_selected(self):
        """선택된 드라이브 언마운트"""
        item = self.mounted_list.currentItem()
        if not item or item.text().startswith("("):
            self.log("⚠️ 해제할 드라이브를 선택하세요.")
            return
        
        drive = item.text().split()[0]  # "Z: (PID: 1234)" -> "Z:"
        self.log(f"드라이브 {drive} 해제 중...")
        
        success, msg = self.mounter.unmount(drive)
        self.log(f"{'✓' if success else '✗'} {msg}")
        
        self.refresh_mounted_list()
        self.update_status()
        self.refresh_available_drives()
    
    def unmount_all(self):
        """모든 rclone 마운트 해제 (롤백)"""
        mounted = self.mounter.find_mounted_drives()
        
        if not mounted:
            self.log("⚠️ 해제할 마운트가 없습니다.")
            return
        
        reply = QMessageBox.question(
            self, "전체 해제 확인",
            f"현재 {len(mounted)}개의 드라이브가 마운트되어 있습니다.\n"
            f"모두 해제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.log(f"전체 해제 시작 ({len(mounted)}개 드라이브)...")
        
        for drive, _ in mounted:
            success, msg = self.mounter.unmount(drive)
            self.log(f"  {'✓' if success else '✗'} {msg}")
        
        self.mounter.current_drive = None
        self.refresh_mounted_list()
        self.update_status()
        self.refresh_available_drives()
        self.log("✅ 전체 해제 완료")
        
        # 자동 시작도 함께 해제할지 묻기
        if self.autostart_check.isChecked():
            reply2 = QMessageBox.question(
                self, "자동 시작 해제",
                "자동 마운트 설정도 함께 해제하시겠습니까?\n"
                "(해제하지 않으면 PC 재부팅 시 다시 마운트됩니다)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply2 == QMessageBox.StandardButton.Yes:
                success, msg = self.autostart_manager.unregister_autostart()
                self.autostart_check.setChecked(False)
                self.log(f"{'✓' if success else '✗'} {msg}")
    
    def update_status(self):
        """상태 업데이트"""
        # 현재 선택된 드라이브 또는 마운트된 드라이브 확인
        current_drive = self.mounter.current_drive
        selected_drive = self.drive_combo.currentText()
        
        # 현재 드라이브가 마운트되어 있는지 확인
        if current_drive and self.mounter.is_mounted(current_drive):
            self.status_display.setText(f"🟢 마운트됨 ({current_drive})")
            self.status_display.setStyleSheet("color: #a6e3a1; font-weight: bold;")
            self.mount_btn.setText("언마운트")
            self.mount_btn.setObjectName("warningButton")
            # 스타일시트 재적용하여 objectName 변경 반영
            self.mount_btn.style().unpolish(self.mount_btn)
            self.mount_btn.style().polish(self.mount_btn)
        elif selected_drive and self.mounter.is_mounted(selected_drive):
            # 선택된 드라이브가 마운트되어 있음
            self.mounter.current_drive = selected_drive
            self.status_display.setText(f"🟢 마운트됨 ({selected_drive})")
            self.status_display.setStyleSheet("color: #a6e3a1; font-weight: bold;")
            self.mount_btn.setText("언마운트")
            self.mount_btn.setObjectName("warningButton")
            # 스타일시트 재적용하여 objectName 변경 반영
            self.mount_btn.style().unpolish(self.mount_btn)
            self.mount_btn.style().polish(self.mount_btn)
        else:
            self.status_display.setText("⚪ 연결 안됨")
            self.status_display.setStyleSheet("color: #a6adc8; font-weight: bold;")
            self.mount_btn.setText("마운트")
            self.mount_btn.setObjectName("primaryButton")
            # 스타일시트 재적용하여 objectName 변경 반영
            self.mount_btn.style().unpolish(self.mount_btn)
            self.mount_btn.style().polish(self.mount_btn)
        
        # 활성 연결 목록 갱신
        self.refresh_mounted_list()
    
    def on_direction_changed(self):
        """전송 방향 변경 이벤트"""
        if self.upload_radio.isChecked():
            self.source_input.setPlaceholderText("로컬 파일/폴더 경로")
            self.dest_input.setPlaceholderText("드라이브 경로 (예: folder/subfolder)")
        else:
            self.source_input.setPlaceholderText("드라이브 경로 (예: folder/subfolder)")
            self.dest_input.setPlaceholderText("로컬 폴더 경로")

    def browse_source(self):
        """소스 경로 선택"""
        if self.upload_radio.isChecked():
            # 업로드: 로컬 파일/폴더 선택
            path = QFileDialog.getExistingDirectory(
                self, "소스 폴더 선택",
                self.source_input.text() or ""
            )
            if path:
                self.source_input.setText(path)
        else:
            # 다운로드: 드라이브 경로는 직접 입력
            QMessageBox.information(
                self, "드라이브 경로",
                "드라이브 경로는 직접 입력해주세요.\n예: MyFolder/SubFolder"
            )

    def browse_dest(self):
        """대상 경로 선택"""
        if self.download_radio.isChecked():
            # 다운로드: 로컬 폴더 선택
            path = QFileDialog.getExistingDirectory(
                self, "대상 폴더 선택",
                self.dest_input.text() or ""
            )
            if path:
                self.dest_input.setText(path)
        else:
            # 업로드: 드라이브 경로는 직접 입력
            QMessageBox.information(
                self, "드라이브 경로",
                "드라이브 경로는 직접 입력해주세요.\n예: MyFolder/SubFolder"
            )

    def quick_unmount_drive(self):
        """파일 전송 탭에서 빠른 언마운트"""
        item = self.transfer_mounted_list.currentItem()
        if not item or item.text().startswith("("):
            QMessageBox.warning(self, "선택 필요", "언마운트할 드라이브를 선택하세요.")
            return

        drive = item.text().split()[0]  # "Z: (PID: 1234)" -> "Z:"
        self.log(f"드라이브 {drive} 해제 중...")

        success, msg = self.mounter.unmount(drive)
        self.log(f"{'✓' if success else '✗'} {msg}")

        self.refresh_transfer_mounted_list()
        self.update_status()
        self.refresh_available_drives()

    def refresh_transfer_mounted_list(self):
        """파일 전송 탭의 마운트 목록 갱신"""
        self.transfer_mounted_list.clear()
        mounted = self.mounter.find_mounted_drives()

        if not mounted:
            self.transfer_mounted_list.addItem("(마운트된 드라이브 없음)")
            self.quick_unmount_btn.setEnabled(False)
        else:
            for drive, pid in mounted:
                self.transfer_mounted_list.addItem(f"{drive} (PID: {pid})")
            self.quick_unmount_btn.setEnabled(True)

    def start_transfer(self):
        """파일 전송 시작"""
        # 인증 확인
        if not self.mounter.is_authenticated():
            QMessageBox.warning(self, "로그인 필요", "먼저 Google 로그인이 필요합니다.")
            return

        source = self.source_input.text().strip()
        dest = self.dest_input.text().strip()

        if not source or not dest:
            QMessageBox.warning(self, "입력 필요", "소스와 대상 경로를 모두 입력하세요.")
            return

        direction = "upload" if self.upload_radio.isChecked() else "download"

        # UI 상태 변경
        self.start_transfer_btn.setEnabled(False)
        self.cancel_transfer_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.transfer_stats_label.setText("전송 준비 중...")

        # 전송 스레드 시작
        self.transfer_thread = TransferThread(
            self.file_transfer,
            direction,
            source,
            dest
        )
        self.transfer_thread.progress.connect(self.on_transfer_progress)
        self.transfer_thread.finished.connect(self.on_transfer_finished)
        self.transfer_thread.start()

        self.log(f"파일 전송 시작: {direction} - {source} → {dest}")

    def cancel_transfer(self):
        """파일 전송 취소"""
        if self.transfer_thread and self.transfer_thread.isRunning():
            self.transfer_thread.terminate()
            self.transfer_thread.wait()
            self.on_transfer_finished(False, "전송이 취소되었습니다.")

    def on_transfer_progress(self, message: str, percent: int, stats: str):
        """전송 진행률 업데이트"""
        self.progress_bar.setValue(percent)
        self.transfer_stats_label.setText(stats)

    def on_transfer_finished(self, success: bool, message: str):
        """전송 완료"""
        self.start_transfer_btn.setEnabled(True)
        self.cancel_transfer_btn.setEnabled(False)

        if success:
            self.progress_bar.setValue(100)
            self.transfer_stats_label.setText("전송 완료!")
            self.log(f"✓ {message}")
            QMessageBox.information(self, "전송 완료", message)
        else:
            self.transfer_stats_label.setText("전송 실패")
            self.log(f"✗ {message}")
            QMessageBox.warning(self, "전송 실패", message)

    def closeEvent(self, event):
        """창 닫기 이벤트 - 마운트 유지한 채 종료"""
        # 전송 중이면 취소
        if self.transfer_thread and self.transfer_thread.isRunning():
            reply = QMessageBox.question(
                self, "전송 진행 중",
                "파일 전송이 진행 중입니다. 취소하고 종료하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.transfer_thread.terminate()
                self.transfer_thread.wait()
                event.accept()
            else:
                event.ignore()
                return

        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
