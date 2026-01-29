# -*- coding: utf-8 -*-
"""
Google Drive Mounter - rclone 래퍼 모듈
Google Drive를 Windows 드라이브로 마운트하는 기능 제공
"""

import subprocess
import os
import json
import webbrowser
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class MountConfig:
    """마운트 설정 데이터 클래스"""
    drive_letter: str
    volume_name: str
    # 성능 최적화 설정
    dir_cache_time: str = "30m"       # 디렉토리 캐시 시간
    poll_interval: str = "10s"        # 변경 감지 주기


class GDriveMounter:
    """rclone을 사용한 Google Drive 마운트 관리 클래스 (독립 프로세스 방식)"""
    
    # 독립 프로세스 생성을 위한 플래그
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    CREATE_NO_WINDOW = 0x08000000
    
    # rclone 리모트 이름
    REMOTE_NAME = "gdrive"
    
    def __init__(self):
        # rclone 실행 파일 경로
        self.rclone_path = self._find_rclone()
        self.current_drive: Optional[str] = None
        self.rclone_config_path = self._get_config_path()
        
    def _find_rclone(self) -> str:
        """rclone 실행 파일 경로 찾기"""
        # 현재 디렉토리 기준 rclone 경로
        base_dir = Path(__file__).parent
        rclone_dir = base_dir / "rclone-v1.72.1-windows-amd64"
        rclone_exe = rclone_dir / "rclone.exe"
        
        if rclone_exe.exists():
            return str(rclone_exe)
        
        # 시스템 PATH에서 찾기
        return "rclone"
    
    def _get_config_path(self) -> str:
        """rclone 설정 파일 경로 반환"""
        appdata = os.environ.get('APPDATA', '')
        config_dir = Path(appdata) / "GDriveMounter"
        config_dir.mkdir(parents=True, exist_ok=True)
        return str(config_dir / "rclone.conf")
    
    def get_available_drives(self) -> list[str]:
        """사용 가능한 드라이브 문자 목록 반환"""
        import string
        used_drives = set()
        
        for letter in string.ascii_uppercase:
            drive = f"{letter}:"
            if os.path.exists(drive):
                used_drives.add(letter)
        
        # D-Z 중 사용 가능한 드라이브 (G를 우선 추천)
        available = []
        priority = ['G']  # Google Drive는 G: 드라이브 권장
        
        for letter in priority:
            if letter not in used_drives:
                available.append(f"{letter}:")
        
        for letter in string.ascii_uppercase[3:]:  # D부터 시작
            if letter not in used_drives and letter not in priority:
                available.append(f"{letter}:")
        
        return available
    
    def _find_rclone_process_for_drive(self, drive_letter: str) -> Optional[int]:
        """특정 드라이브에 마운트된 rclone 프로세스 PID 찾기"""
        try:
            # PowerShell로 rclone 프로세스 찾기
            ps_cmd = (
                "Get-CimInstance Win32_Process -Filter \"name='rclone.exe'\" | "
                "Select-Object ProcessId, CommandLine | ConvertTo-Csv -NoTypeInformation"
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    # 해당 드라이브 문자가 포함된 라인 찾기
                    if drive_letter.upper() in line.upper() or drive_letter.lower() in line.lower():
                        # CSV 형식: "ProcessId","CommandLine"
                        parts = line.strip().split('","')
                        if len(parts) >= 1:
                            try:
                                pid_str = parts[0].strip('"')
                                return int(pid_str)
                            except ValueError:
                                continue
        except Exception:
            pass
        return None
    
    def is_authenticated(self) -> bool:
        """Google Drive 인증 여부 확인"""
        if not os.path.exists(self.rclone_config_path):
            return False
        
        try:
            result = subprocess.run(
                [self.rclone_path, "listremotes", "--config", self.rclone_config_path],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return f"{self.REMOTE_NAME}:" in result.stdout
        except Exception:
            return False
    
    def get_account_info(self) -> Optional[str]:
        """연결된 Google 계정 정보 가져오기"""
        if not self.is_authenticated():
            return None
        
        try:
            result = subprocess.run(
                [self.rclone_path, "about", f"{self.REMOTE_NAME}:", 
                 "--config", self.rclone_config_path, "--json"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                total = data.get('total', 0)
                used = data.get('used', 0)
                # 용량 정보 반환
                total_gb = total / (1024**3)
                used_gb = used / (1024**3)
                return f"사용: {used_gb:.1f}GB / {total_gb:.1f}GB"
        except Exception:
            pass
        return "연결됨"
    
    def authenticate(self, progress_callback=None) -> tuple[bool, str]:
        """
        Google Drive 인증 수행
        브라우저를 통해 OAuth 인증 진행
        
        Returns:
            (성공 여부, 메시지)
        """
        def log(msg):
            if progress_callback:
                progress_callback(msg)
        
        log("Google 로그인 페이지를 여는 중...")
        
        try:
            # rclone config 명령으로 새 리모트 생성
            # 자동 설정을 위한 명령 구성
            config_commands = [
                self.rclone_path, "config", "create",
                self.REMOTE_NAME, "drive",
                "--config", self.rclone_config_path
            ]
            
            log("브라우저에서 Google 계정으로 로그인해주세요...")
            
            result = subprocess.run(
                config_commands,
                capture_output=True,
                text=True,
                timeout=300  # 5분 타임아웃
            )
            
            if result.returncode == 0:
                log("인증 설정 완료!")
                return True, "Google Drive 인증이 완료되었습니다."
            else:
                error = result.stderr or result.stdout or "알 수 없는 오류"
                return False, f"인증 실패: {error}"
                
        except subprocess.TimeoutExpired:
            return False, "인증 시간이 초과되었습니다. 다시 시도해주세요."
        except Exception as e:
            return False, f"인증 오류: {str(e)}"
    
    def authenticate_interactive(self, progress_callback=None) -> tuple[bool, str]:
        """
        Google Drive 인증 수행 (대화형)
        브라우저를 통해 OAuth 인증 진행
        
        Returns:
            (성공 여부, 메시지)
        """
        def log(msg):
            if progress_callback:
                progress_callback(msg)
        
        log("Google 로그인을 시작합니다...")
        
        try:
            # rclone authorize 명령으로 토큰 획득
            log("브라우저에서 Google 계정으로 로그인해주세요...")
            
            # 먼저 authorize로 토큰 획득
            auth_process = subprocess.Popen(
                [self.rclone_path, "authorize", "drive"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # 토큰 출력 대기 (최대 5분)
            token_json = None
            output_lines = []
            
            import time
            start_time = time.time()
            while time.time() - start_time < 300:
                line = auth_process.stdout.readline()
                if not line:
                    if auth_process.poll() is not None:
                        break
                    time.sleep(0.1)
                    continue
                
                output_lines.append(line)
                
                # 토큰 JSON 찾기
                if '{"access_token"' in line or '"access_token":' in line:
                    # 토큰 라인 추출
                    for l in output_lines:
                        if l.strip().startswith('{') and 'access_token' in l:
                            token_json = l.strip()
                            break
                    if token_json:
                        break
                
                # "Paste the following" 메시지 감지
                if "Paste the following" in line:
                    # 다음 라인이 토큰
                    token_line = auth_process.stdout.readline()
                    if token_line and token_line.strip().startswith('{'):
                        token_json = token_line.strip()
                        break
            
            auth_process.terminate()
            
            if token_json:
                # 토큰으로 리모트 설정 생성
                result = subprocess.run(
                    [
                        self.rclone_path, "config", "create",
                        self.REMOTE_NAME, "drive",
                        "token", token_json,
                        "--config", self.rclone_config_path
                    ],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if result.returncode == 0 or self.is_authenticated():
                    log("✓ 인증 완료!")
                    return True, "Google Drive 인증이 완료되었습니다."
                else:
                    return False, f"설정 생성 실패: {result.stderr}"
            else:
                # authorize 실패 시 간단한 config create 시도
                log("자동 인증을 시도합니다...")
                result = subprocess.run(
                    [
                        self.rclone_path, "config", "create",
                        self.REMOTE_NAME, "drive",
                        "--config", self.rclone_config_path
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if self.is_authenticated():
                    return True, "Google Drive 인증이 완료되었습니다."
                
                return False, "인증에 실패했습니다. 다시 시도해주세요."
                
        except subprocess.TimeoutExpired:
            return False, "인증 시간이 초과되었습니다."
        except Exception as e:
            return False, f"인증 오류: {str(e)}"
    
    def logout(self) -> tuple[bool, str]:
        """Google Drive 연결 해제 (리모트 삭제)"""
        try:
            result = subprocess.run(
                [
                    self.rclone_path, "config", "delete",
                    self.REMOTE_NAME,
                    "--config", self.rclone_config_path
                ],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode == 0 or not self.is_authenticated():
                return True, "Google Drive 연결이 해제되었습니다."
            return False, f"연결 해제 실패: {result.stderr}"
        except Exception as e:
            return False, f"연결 해제 오류: {str(e)}"
    
    def mount(self, config: MountConfig) -> tuple[bool, str]:
        """
        Google Drive 마운트 실행 (독립 프로세스로 실행)

        Args:
            config: 마운트 설정

        Returns:
            (성공 여부, 메시지)
        """
        # 인증 확인
        if not self.is_authenticated():
            return False, "먼저 Google 로그인이 필요합니다."

        # 드라이브가 이미 사용 중인지 확인
        if os.path.exists(config.drive_letter):
            # 이미 rclone으로 마운트된 것인지 확인
            pid = self._find_rclone_process_for_drive(config.drive_letter)
            if pid:
                self.current_drive = config.drive_letter
                return False, f"드라이브 {config.drive_letter}는 이미 rclone으로 마운트되어 있습니다. (PID: {pid})"
            return False, f"드라이브 {config.drive_letter}가 이미 사용 중입니다."

        # rclone mount 명령 구성 (Google Drive 최적화, VFS 캐시 없음)
        cmd = [
            self.rclone_path, "mount",
            f"{self.REMOTE_NAME}:", config.drive_letter,
            "--config", self.rclone_config_path,
            # VFS 캐시 설정 (즉시 업로드 방식)
            "--vfs-cache-mode=off",
            # Google Drive 최적화
            "--buffer-size=0",
            "--drive-pacer-min-sleep=10ms",
            "--drive-pacer-burst=200",
            f"--dir-cache-time={config.dir_cache_time}",
            f"--poll-interval={config.poll_interval}",
            # 기타 설정
            "--network-mode",
            f"--volname={config.volume_name}",
            "--vfs-read-ahead=128M",
        ]
        
        try:
            # 완전히 독립된 프로세스로 실행 (GUI 종료해도 유지됨)
            creation_flags = (
                self.DETACHED_PROCESS | 
                self.CREATE_NEW_PROCESS_GROUP | 
                self.CREATE_NO_WINDOW
            )
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                creationflags=creation_flags,
                close_fds=True
            )
            
            self.current_drive = config.drive_letter
            
            # 잠시 대기 후 드라이브 마운트 확인
            import time
            time.sleep(3)
            
            if os.path.exists(config.drive_letter):
                return True, f"드라이브 {config.drive_letter}에 마운트되었습니다. (GUI를 닫아도 유지됩니다)"
            
            # 프로세스 오류 확인
            if process.poll() is not None:
                try:
                    stderr = process.stderr.read().decode('utf-8', errors='replace') if process.stderr else ""
                    return False, f"마운트 실패: {stderr}"
                except:
                    return False, "마운트 실패: 알 수 없는 오류"
            
            # 드라이브가 아직 안 보이지만 프로세스는 실행 중
            return True, f"드라이브 {config.drive_letter} 마운트 진행 중... (잠시 후 탐색기에서 확인하세요)"
            
        except FileNotFoundError:
            return False, f"rclone을 찾을 수 없습니다: {self.rclone_path}"
        except Exception as e:
            return False, f"마운트 오류: {str(e)}"
    
    def unmount(self, drive_letter: Optional[str] = None) -> tuple[bool, str]:
        """마운트 해제 (rclone 프로세스 종료)"""
        drive = drive_letter or self.current_drive
        
        if not drive:
            return False, "언마운트할 드라이브를 지정해주세요."
        
        # 해당 드라이브의 rclone 프로세스 찾기
        pid = self._find_rclone_process_for_drive(drive)
        
        if not pid:
            # 드라이브가 존재하지 않으면 이미 언마운트된 것
            if not os.path.exists(drive):
                self.current_drive = None
                return True, f"드라이브 {drive}는 이미 언마운트되어 있습니다."
            return False, f"드라이브 {drive}에 대한 rclone 프로세스를 찾을 수 없습니다."
        
        try:
            # taskkill로 프로세스 종료
            result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                self.current_drive = None
                return True, f"드라이브 {drive} 마운트가 해제되었습니다. (PID: {pid})"
            else:
                return False, f"언마운트 실패: {result.stderr or result.stdout}"
                
        except Exception as e:
            return False, f"언마운트 오류: {str(e)}"
    
    def is_mounted(self, drive_letter: Optional[str] = None) -> bool:
        """마운트 상태 확인"""
        drive = drive_letter or self.current_drive
        if not drive:
            return False
        
        # 드라이브가 존재하고 rclone 프로세스가 있는지 확인
        return os.path.exists(drive) and self._find_rclone_process_for_drive(drive) is not None
    
    def get_mount_info(self) -> Optional[str]:
        """현재 마운트된 드라이브 정보 반환"""
        if self.current_drive and self.is_mounted(self.current_drive):
            return self.current_drive
        return None
    
    def find_mounted_drives(self) -> list[tuple[str, int]]:
        """현재 rclone으로 마운트된 모든 드라이브 찾기"""
        mounted = []
        try:
            # PowerShell로 rclone 프로세스 찾기
            ps_cmd = (
                "Get-CimInstance Win32_Process -Filter \"name='rclone.exe'\" | "
                "Select-Object ProcessId, CommandLine | ConvertTo-Csv -NoTypeInformation"
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                import string
                for letter in string.ascii_uppercase[3:]:  # D부터
                    drive = f"{letter}:"
                    for line in result.stdout.split('\n'):
                        if drive in line and self.REMOTE_NAME in line:
                            # CSV 형식: "ProcessId","CommandLine"
                            parts = line.strip().split('","')
                            if len(parts) >= 1:
                                try:
                                    pid_str = parts[0].strip('"')
                                    pid = int(pid_str)
                                    mounted.append((drive, pid))
                                    break
                                except ValueError:
                                    continue
        except Exception:
            pass
        return mounted


def get_rclone_version(rclone_path: str) -> Optional[str]:
    """rclone 버전 확인"""
    try:
        result = subprocess.run(
            [rclone_path, "version"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode == 0:
            # 첫 번째 줄에서 버전 추출
            first_line = result.stdout.split('\n')[0]
            return first_line
        return None
    except Exception:
        return None


def is_winfsp_installed() -> bool:
    """WinFsp 설치 여부 확인"""
    # 방법 1: WinFsp DLL 확인
    winfsp_paths = [
        r"C:\Program Files (x86)\WinFsp\bin\winfsp-x64.dll",
        r"C:\Program Files\WinFsp\bin\winfsp-x64.dll",
    ]
    
    for path in winfsp_paths:
        if os.path.exists(path):
            return True
    
    # 방법 2: 레지스트리 확인
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WinFsp",
            0,
            winreg.KEY_READ
        )
        winreg.CloseKey(key)
        return True
    except (FileNotFoundError, WindowsError):
        pass
    
    return False


def install_winfsp_with_winget(progress_callback=None) -> tuple[bool, str]:
    """
    winget을 사용하여 WinFsp 설치
    
    Args:
        progress_callback: 진행 상황 콜백 함수 (메시지를 받음)
    
    Returns:
        (성공 여부, 메시지)
    """
    def log(msg):
        if progress_callback:
            progress_callback(msg)
    
    # winget 사용 가능 여부 확인
    try:
        result = subprocess.run(
            ["winget", "--version"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode != 0:
            return False, "winget을 찾을 수 없습니다. Windows 10 1709 이상이 필요합니다."
    except FileNotFoundError:
        return False, "winget이 설치되어 있지 않습니다."
    
    log("WinFsp 설치 중... (관리자 권한이 필요할 수 있습니다)")
    
    try:
        # winget으로 WinFsp 설치
        result = subprocess.run(
            [
                "winget", "install", 
                "WinFsp.WinFsp",
                "--accept-package-agreements",
                "--accept-source-agreements",
                "--silent"
            ],
            capture_output=True,
            text=True,
            timeout=300  # 5분 타임아웃
        )
        
        if result.returncode == 0:
            log("WinFsp 설치 완료!")
            return True, "WinFsp가 성공적으로 설치되었습니다."
        else:
            error_msg = result.stderr or result.stdout or "알 수 없는 오류"
            
            # 이미 설치된 경우
            if "already installed" in error_msg.lower() or result.returncode == -1978335189:
                return True, "WinFsp가 이미 설치되어 있습니다."
            
            # 관리자 권한 필요
            if "administrator" in error_msg.lower() or "elevation" in error_msg.lower():
                return False, "관리자 권한이 필요합니다. 관리자 권한으로 프로그램을 다시 실행하거나, 수동으로 WinFsp를 설치해주세요."
            
            return False, f"WinFsp 설치 실패: {error_msg}"
            
    except subprocess.TimeoutExpired:
        return False, "WinFsp 설치 시간이 초과되었습니다."
    except Exception as e:
        return False, f"WinFsp 설치 오류: {str(e)}"


def check_and_install_winfsp(auto_install: bool = True, 
                              progress_callback=None) -> tuple[bool, str]:
    """
    WinFsp 확인 및 필요 시 설치
    
    Args:
        auto_install: True면 자동 설치 시도
        progress_callback: 진행 상황 콜백 함수
    
    Returns:
        (WinFsp 사용 가능 여부, 메시지)
    """
    if is_winfsp_installed():
        return True, "WinFsp가 설치되어 있습니다."
    
    if not auto_install:
        return False, "WinFsp가 설치되어 있지 않습니다. https://winfsp.dev/rel/ 에서 설치해주세요."
    
    # 자동 설치 시도
    return install_winfsp_with_winget(progress_callback)
