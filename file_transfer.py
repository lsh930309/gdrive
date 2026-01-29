# -*- coding: utf-8 -*-
"""
File Transfer - rclone copy 래퍼 모듈
빠른 파일 업로드/다운로드 기능 제공
"""

import subprocess
import re
from typing import Optional, Callable
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal


class FileTransfer:
    """rclone copy 래퍼 클래스"""

    # rclone 리모트 이름
    REMOTE_NAME = "gdrive"

    def __init__(self, rclone_path: str, config_path: str):
        self.rclone_path = rclone_path
        self.config_path = config_path

    def upload(
        self,
        local_path: str,
        remote_path: str,
        progress_callback: Optional[Callable] = None
    ) -> tuple[bool, str]:
        """
        로컬 파일/폴더를 Google Drive로 업로드

        Args:
            local_path: 로컬 경로
            remote_path: 원격 경로 (예: "folder/subfolder")
            progress_callback: 진행률 콜백 함수

        Returns:
            (성공 여부, 메시지)
        """
        if not Path(local_path).exists():
            return False, f"경로를 찾을 수 없습니다: {local_path}"

        # rclone copy 명령 구성
        cmd = [
            self.rclone_path, "copy",
            local_path,
            f"{self.REMOTE_NAME}:{remote_path}",
            "--config", self.config_path,
            # 성능 최적화 옵션
            "--transfers=8",
            "--checkers=16",
            "--drive-chunk-size=64M",
            "--progress",
            "--stats=1s"
        ]

        try:
            if progress_callback:
                progress_callback("업로드 시작...", 0, "")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # 진행률 파싱
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                if progress_callback:
                    self._parse_progress(line, progress_callback)

            process.wait()

            if process.returncode == 0:
                return True, "업로드 완료"
            else:
                return False, f"업로드 실패 (코드: {process.returncode})"

        except Exception as e:
            return False, f"업로드 오류: {str(e)}"

    def download(
        self,
        remote_path: str,
        local_path: str,
        progress_callback: Optional[Callable] = None
    ) -> tuple[bool, str]:
        """
        Google Drive에서 로컬로 다운로드

        Args:
            remote_path: 원격 경로
            local_path: 로컬 경로
            progress_callback: 진행률 콜백 함수

        Returns:
            (성공 여부, 메시지)
        """
        # 로컬 디렉토리 생성
        Path(local_path).mkdir(parents=True, exist_ok=True)

        # rclone copy 명령 구성
        cmd = [
            self.rclone_path, "copy",
            f"{self.REMOTE_NAME}:{remote_path}",
            local_path,
            "--config", self.config_path,
            # 성능 최적화 옵션
            "--transfers=8",
            "--checkers=16",
            "--drive-chunk-size=64M",
            "--progress",
            "--stats=1s"
        ]

        try:
            if progress_callback:
                progress_callback("다운로드 시작...", 0, "")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # 진행률 파싱
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                if progress_callback:
                    self._parse_progress(line, progress_callback)

            process.wait()

            if process.returncode == 0:
                return True, "다운로드 완료"
            else:
                return False, f"다운로드 실패 (코드: {process.returncode})"

        except Exception as e:
            return False, f"다운로드 오류: {str(e)}"

    def _parse_progress(self, line: str, callback: Callable):
        """
        rclone 진행률 출력 파싱

        rclone 출력 예시:
        Transferred:   	    1.234 MiB / 10 MiB, 12%, 1.5 MiB/s, ETA 5s
        """
        try:
            # "Transferred:" 라인 찾기
            if "Transferred:" in line:
                # 퍼센트 추출
                percent_match = re.search(r'(\d+)%', line)
                if percent_match:
                    percent = int(percent_match.group(1))
                else:
                    percent = 0

                # 통계 정보 추출
                stats = line.strip()

                callback(f"전송 중... {percent}%", percent, stats)
        except Exception:
            pass


class TransferThread(QThread):
    """백그라운드 파일 전송 스레드"""

    # 시그널 정의
    progress = pyqtSignal(str, int, str)  # (메시지, 퍼센트, 통계)
    finished = pyqtSignal(bool, str)  # (성공 여부, 메시지)

    def __init__(
        self,
        transfer: FileTransfer,
        direction: str,
        source: str,
        destination: str
    ):
        super().__init__()
        self.transfer = transfer
        self.direction = direction  # "upload" or "download"
        self.source = source
        self.destination = destination

    def run(self):
        """스레드 실행"""
        def progress_callback(message: str, percent: int, stats: str):
            self.progress.emit(message, percent, stats)

        if self.direction == "upload":
            success, message = self.transfer.upload(
                self.source,
                self.destination,
                progress_callback
            )
        else:  # download
            success, message = self.transfer.download(
                self.source,
                self.destination,
                progress_callback
            )

        self.finished.emit(success, message)
