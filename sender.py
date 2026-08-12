from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import logging
import os
import platform
import re
import subprocess
import tempfile

BASE_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = BASE_DIR / 'scripts' / 'send_message.applescript'
logger = logging.getLogger('mac-message-merge')


@dataclass
class SendResult:
    success: bool
    message: str
    code: Optional[int] = None

    @property
    def fatal(self) -> bool:
        return self.code in {10001, 10002, 10003, 10004, 10005}


def _extract_error_code(text: str):
    match = re.search(r'\(Code:\s*(-?\d+)\)', text or '')
    return int(match.group(1)) if match else None


def _masked_phone(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)
    if len(digits) < 7:
        return '***'
    return f'{digits[:3]}***{digits[-4:]}'


def send_message(phone: str, message: str) -> SendResult:
    if platform.system() != 'Darwin':
        return SendResult(False, '이 기능은 macOS에서만 동작합니다.')

    phone = ('+' if str(phone).strip().startswith('+') else '') + re.sub(r'\D', '', str(phone))
    masked = _masked_phone(phone)
    logger.info('전송 시작 - 번호: %s, 메시지 길이: %d자', masked, len(message))

    try:
        result = subprocess.run(
            ['osascript', str(SCRIPT_PATH), phone, message],
            capture_output=True,
            text=True,
            timeout=35,
        )
    except FileNotFoundError:
        return SendResult(False, 'osascript를 찾을 수 없습니다. macOS에서 실행해주세요.')
    except subprocess.TimeoutExpired:
        return SendResult(False, 'Messages 응답 시간이 초과되었습니다.')
    except Exception as exc:
        logger.exception('전송 중 예외')
        return SendResult(False, f'전송 중 오류가 발생했습니다: {exc}')

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode == 0 and stdout == 'SUCCESS':
        logger.info('전송 완료 - 번호: %s', masked)
        return SendResult(True, '전송 완료')

    detail = stdout or stderr or f'osascript 종료 코드 {result.returncode}'
    code = _extract_error_code(detail)
    logger.warning('전송 실패 - 번호: %s, code=%s, detail=%s', masked, code, detail)
    return SendResult(False, detail, code)


def _run(command, timeout=8):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return False, '', str(exc)


def diagnostics():
    info = {
        'platform': platform.system(),
        'macos_version': platform.mac_ver()[0] or None,
        'architecture': platform.machine(),
        'script_exists': SCRIPT_PATH.exists(),
        'script_compiles': False,
        'accessibility_enabled': False,
        'messages_accessible': False,
        'messages_running': False,
        'errors': [],
    }

    if platform.system() != 'Darwin':
        info['errors'].append('macOS가 아닙니다.')
        return info

    ok, out, err = _run(['pgrep', '-x', 'Messages'])
    info['messages_running'] = ok

    with tempfile.TemporaryDirectory() as temp_dir:
        compiled = str(Path(temp_dir) / 'send_message.scpt')
        ok, _, err = _run(['osacompile', '-o', compiled, str(SCRIPT_PATH)], timeout=10)
        info['script_compiles'] = ok
        if not ok:
            info['errors'].append(f'AppleScript 문법 검사 실패: {err}')

    ok, out, err = _run([
        'osascript', '-e', 'tell application "System Events" to return UI elements enabled'
    ])
    info['accessibility_enabled'] = ok and out.lower() == 'true'
    if not info['accessibility_enabled']:
        info['errors'].append('손쉬운 사용(UI 자동화) 권한이 필요합니다.')

    ok, out, err = _run([
        'osascript', '-e', 'tell application "Messages" to return name'
    ])
    info['messages_accessible'] = ok
    if not ok:
        info['errors'].append(f'Messages 자동화 접근 실패: {err or out}')

    return info
