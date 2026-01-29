# -*- coding: utf-8 -*-
"""
Autostart Manager - Windows 자동 시작 관리 모듈
시작 프로그램 등록/해제 및 자동 마운트 스크립트 생성
"""

import os
import sys
import winreg
from pathlib import Path
from typing import Optional


class AutostartManager:
    """Windows 자동 시작 관리 클래스"""
    
    APP_NAME = "GDriveMounter"
    REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    def __init__(self):
        self.app_dir = Path(__file__).parent
        self.startup_script = self.app_dir / "run_mount.bat"
        self.python_script = self.app_dir / "auto_mount.pyw"
    
    def create_startup_script(self, config_path: str) -> bool:
        """자동 시작 배치 스크립트 생성"""
        try:
            python_exe = sys.executable
            script_path = self.app_dir / "auto_mount.pyw"
            
            # Python 스크립트 생성 (백그라운드 실행용 .pyw)
            pyw_content = f'''# -*- coding: utf-8 -*-
"""자동 마운트 스크립트 - 백그라운드 실행"""
import sys
import os
sys.path.insert(0, r"{self.app_dir}")

from config_manager import ConfigManager
from gdrive_mounter import GDriveMounter, MountConfig

def main():
    # 설정 불러오기
    config_mgr = ConfigManager()
    config = config_mgr.load()
    
    if not config.auto_mount:
        return
    
    # 마운터 초기화
    mounter = GDriveMounter()
    
    # 인증 확인
    if not mounter.is_authenticated():
        return
    
    # 마운트 설정 생성
    mount_config = MountConfig(
        drive_letter=config.drive_letter,
        volume_name=config.volume_name,
        cache_size=config.cache_size,
        cache_dir=config.cache_dir,
        dir_cache_time=config.dir_cache_time,
        poll_interval=config.poll_interval
    )
    
    # 마운트 실행
    mounter.mount(mount_config, config.cache_mode)

if __name__ == "__main__":
    main()
'''
            
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(pyw_content)
            
            # 배치 파일 생성 (pythonw.exe로 백그라운드 실행)
            pythonw_exe = python_exe.replace('python.exe', 'pythonw.exe')
            if not os.path.exists(pythonw_exe):
                pythonw_exe = python_exe
            
            bat_content = f'''@echo off
start "" "{pythonw_exe}" "{script_path}"
'''
            
            with open(self.startup_script, 'w', encoding='utf-8') as f:
                f.write(bat_content)
            
            return True
        except Exception as e:
            print(f"스크립트 생성 실패: {e}")
            return False
    
    def register_autostart(self) -> tuple[bool, str]:
        """Windows 시작 프로그램에 등록"""
        try:
            if not self.startup_script.exists():
                return False, "시작 스크립트가 없습니다. 먼저 설정을 저장하세요."
            
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REGISTRY_PATH,
                0,
                winreg.KEY_SET_VALUE
            )
            
            winreg.SetValueEx(
                key,
                self.APP_NAME,
                0,
                winreg.REG_SZ,
                str(self.startup_script)
            )
            
            winreg.CloseKey(key)
            return True, "자동 시작이 등록되었습니다."
            
        except WindowsError as e:
            return False, f"레지스트리 등록 실패: {e}"
        except Exception as e:
            return False, f"자동 시작 등록 실패: {e}"
    
    def unregister_autostart(self) -> tuple[bool, str]:
        """Windows 시작 프로그램에서 제거"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REGISTRY_PATH,
                0,
                winreg.KEY_SET_VALUE
            )
            
            try:
                winreg.DeleteValue(key, self.APP_NAME)
            except FileNotFoundError:
                pass  # 이미 없음
            
            winreg.CloseKey(key)
            return True, "자동 시작이 해제되었습니다."
            
        except WindowsError as e:
            return False, f"레지스트리 삭제 실패: {e}"
        except Exception as e:
            return False, f"자동 시작 해제 실패: {e}"
    
    def is_registered(self) -> bool:
        """자동 시작 등록 여부 확인"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REGISTRY_PATH,
                0,
                winreg.KEY_READ
            )
            
            try:
                value, _ = winreg.QueryValueEx(key, self.APP_NAME)
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
                
        except Exception:
            return False
    
    def cleanup_scripts(self) -> bool:
        """생성된 스크립트 파일 삭제"""
        try:
            if self.startup_script.exists():
                self.startup_script.unlink()
            if self.python_script.exists():
                self.python_script.unlink()
            return True
        except Exception:
            return False
