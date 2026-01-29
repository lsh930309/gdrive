# -*- coding: utf-8 -*-
"""
Config Manager - 설정 저장/불러오기 모듈
Google Drive 연결 정보를 JSON 파일로 관리
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Optional
from pathlib import Path


@dataclass
class ConnectionConfig:
    """연결 설정 데이터 클래스"""
    drive_letter: str = "G:"
    volume_name: str = "Google Drive"
    auto_mount: bool = False
    theme: str = "auto"  # "auto", "light", "dark"
    dir_cache_time: str = "30m"
    poll_interval: str = "10s"


class ConfigManager:
    """설정 관리 클래스"""
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # 기본: 사용자 AppData 디렉토리
            appdata = os.environ.get('APPDATA', '')
            self.config_dir = Path(appdata) / "GDriveMounter"
        
        self.config_file = self.config_dir / "config.json"
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """설정 디렉토리 생성"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, config: ConnectionConfig) -> bool:
        """설정 저장"""
        try:
            data = asdict(config)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"설정 저장 실패: {e}")
            return False
    
    def load(self) -> ConnectionConfig:
        """설정 불러오기"""
        if not self.config_file.exists():
            return ConnectionConfig()

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 기존 설정 파일 호환성: 제거된 필드 무시
            data.pop('cache_mode', None)
            data.pop('cache_size', None)
            data.pop('cache_dir', None)

            # 누락된 필드는 기본값 사용
            return ConnectionConfig(**data)
        except Exception as e:
            print(f"설정 불러오기 실패: {e}")
            return ConnectionConfig()
    
    def delete(self) -> bool:
        """설정 파일 삭제"""
        try:
            if self.config_file.exists():
                self.config_file.unlink()
            return True
        except Exception:
            return False
    
    def get_config_path(self) -> str:
        """설정 파일 경로 반환"""
        return str(self.config_file)
