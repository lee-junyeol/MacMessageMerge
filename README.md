# MacMessageMerge

macOS **Messages** 앱을 이용해 여러 수신자에게 개인화된 메시지를 순차 전송하는 로컬 웹앱입니다.

CSV에서 이름과 전화번호를 불러오고, 메시지 안의 `{name}`과 `{phone}`을 수신자별 값으로 치환합니다. 각 수신자마다 Messages에서 **Command-N(새 메시지)** 으로 새 작성 화면을 연 뒤 전송합니다.

> **중요:** 이 프로젝트는 GitHub Pages, Vercel, Render 같은 웹 서버에 배포해서 사용하는 앱이 아닙니다. GitHub는 **소스 코드와 릴리즈 파일을 배포하는 곳**이고, 실제 프로그램은 Messages가 설치된 **사용자의 Mac에서 로컬로 실행**해야 합니다.

## 주요 기능

- CSV 대량 수신자 불러오기
- UTF-8 / UTF-8 BOM / CP949 / EUC-KR CSV 지원
- 이름/전화번호 헤더 자동 인식
- `{name}`, `{phone}` 개인화 변수
- 수신자마다 항상 Command-N으로 새 메시지 작성
- 클립보드 대신 Accessibility `AXValue`에 본문을 직접 입력
- AppleScript 문법, Messages 접근, 손쉬운 사용 권한 진단
- 연락처/CSV/메시지 내용을 디스크에 저장하지 않음
- 외부 CDN이나 외부 API 없이 완전 로컬 실행
- Waitress를 `127.0.0.1`에만 바인딩

## 시스템 요구사항

- macOS
- Python **3.9 이상**
- macOS 기본 **Messages** 앱
- iMessage 사용 시 Apple Account 로그인
- SMS/MMS/RCS 사용 시 iPhone과 Mac에서 같은 Apple Account를 사용하고 iPhone의 **문자 메시지 전달(Text Message Forwarding)** 설정 필요

### macOS 호환성 정책

이 프로젝트는 Messages의 Accessibility UI를 자동화하므로 macOS 업데이트에 따라 UI 구조가 달라지면 수정이 필요할 수 있습니다.

| macOS | 프로젝트 지원 정책 | 비고 |
|---|---|---|
| macOS Tahoe 26 | **주 지원 대상** | 현재 Messages UI 계열을 기준으로 유지 권장 |
| macOS Sequoia 15 | 제한적 지원 | 동작 가능하나 릴리즈별 검증 필요 |
| macOS Sonoma 14 이하 | 미지원 | UI 구조 차이로 보장하지 않음 |

새 macOS 버전으로 업데이트한 직후에는 먼저 **연동 확인**과 본인 번호 1건 테스트를 권장합니다.

현재 Mac 버전 확인:

```bash
sw_vers
```

## 설치

### 1. 저장소 받기

```bash
git clone https://github.com/lee-junyeol/MacMessageMerge.git
cd MacMessageMerge
```

또는 GitHub Releases에서 소스 ZIP을 받아 압축을 풉니다.

### 2. 실행 권한 부여

```bash
chmod +x run.sh
```

### 3. 실행

```bash
./run.sh
```

처음 실행할 때 `.venv` 가상환경을 만들고 필요한 Python 패키지를 설치합니다. 이후에는 브라우저가 자동으로 다음 주소를 엽니다.

```text
http://127.0.0.1:5001
```

종료하려면 실행 중인 터미널에서 `Ctrl+C`를 누릅니다.

## macOS 권한 설정

이 앱은 Messages 화면을 직접 조작하므로 macOS 권한이 필요합니다.

1. **시스템 설정 → 개인정보 보호 및 보안 → 손쉬운 사용**
2. Terminal, iTerm 또는 이 앱을 실행한 프로그램의 접근 허용
3. **시스템 설정 → 개인정보 보호 및 보안 → 자동화**에서 Messages/System Events 제어 요청이 표시되면 허용
4. 웹앱의 **연동 확인** 버튼을 눌러 상태 확인

권한을 바꾼 뒤에는 터미널과 앱을 완전히 종료했다가 다시 실행하는 편이 안전합니다.

## Messages 설정

프로그램은 발신 번호나 이메일을 AppleScript에서 강제로 지정하지 않습니다. 새 메시지의 발신 ID는 Messages/iMessage의 **새로운 대화 시작(Start New Conversations From)** 설정을 따릅니다.

SMS/MMS/RCS까지 Mac에서 보내려면 iPhone에서 문자 메시지 전달을 켜야 합니다.

## CSV 형식

기본 형식:

```csv
이름,전화번호
김민수,010-1234-5678
이영희,010-2345-6789
```

인식 가능한 이름 헤더 예:

```text
이름, 성명, name
```

인식 가능한 전화번호 헤더 예:

```text
전화번호, 휴대폰, 핸드폰, 연락처, 전화, phone, mobile, tel
```

헤더가 없으면 첫 번째 열을 이름, 두 번째 열을 전화번호로 읽습니다. 한 번에 최대 300명까지 처리합니다.

## 개인화 메시지

```text
{name}님, 안녕하세요.
안내드릴 내용이 있어 연락드립니다.
```

김민수에게는:

```text
김민수님, 안녕하세요.
안내드릴 내용이 있어 연락드립니다.
```

사용 가능한 변수:

- `{name}` — 수신자 이름
- `{phone}` — 수신자 전화번호

## 전송 방식

수신자마다 다음 순서로 동작합니다.

1. Messages 활성화
2. `Command-N`으로 새 메시지 작성
3. 전화번호 입력 및 확정
4. Accessibility UI에서 실제 본문 입력 영역 탐색
5. `AXValue`에 Unicode 본문 직접 설정
6. 입력된 본문을 다시 읽어 검증
7. Return으로 전송

본문을 검증할 수 없거나 작성 영역을 찾지 못하면 해당 상황에서 전송을 중단합니다. 잘못된 곳에 본문을 입력하거나 파일 형태의 클립보드 데이터가 전송되는 것을 피하기 위한 동작입니다.

## 개인정보와 보안

- CSV 파일은 메모리에서만 파싱하며 저장하지 않습니다.
- 연락처 목록은 브라우저를 새로 열면 초기화됩니다.
- 메시지 본문은 로그에 저장하지 않습니다.
- 로그에는 마스킹된 번호와 메시지 길이 같은 진단 정보만 기록합니다.
- 웹 서버는 `127.0.0.1`에만 열립니다.
- 앱은 외부 HTTP API를 호출하지 않습니다.

로그 위치:

```text
~/Library/Logs/MacMessageMerge/app.log
```

## 문제 해결

### 연동 확인에서 손쉬운 사용 권한이 필요하다고 나옴

**시스템 설정 → 개인정보 보호 및 보안 → 손쉬운 사용**에서 현재 앱을 실행한 Terminal/iTerm을 허용하세요.

### Messages 자동화 접근 실패

**시스템 설정 → 개인정보 보호 및 보안 → 자동화**를 확인하고, Terminal/iTerm의 Messages 제어를 허용하세요.

### AppleScript 문법 검사 실패

GitHub Issue를 열 때 다음 정보를 함께 적어주세요. 개인정보는 제거해야 합니다.

```bash
sw_vers
uname -m
```

그리고 웹앱의 **연동 확인** 결과에서 전화번호나 메시지 내용 없이 오류 문구만 첨부하세요.

### 메시지 입력칸을 찾지 못함 (Code 10002)

macOS Messages의 Accessibility UI 구조가 프로젝트가 예상한 형태와 다른 경우입니다. macOS 버전과 오류 로그를 확인해 `scripts/send_message.applescript`의 입력영역 탐색 로직을 조정해야 합니다.

### SMS/MMS/RCS가 Mac에서 보내지지 않음

iPhone과 Mac의 Apple Account가 같은지, iPhone에서 iMessage와 **문자 메시지 전달**이 켜져 있는지 확인하세요.

## 테스트

AppleScript를 제외한 CSV/개인화 핵심 로직 테스트:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

AppleScript 문법은 macOS에서 다음 명령으로 확인할 수 있습니다.

```bash
osacompile -o /tmp/MacMessageMerge.scpt scripts/send_message.applescript
```

웹앱의 **연동 확인** 버튼도 같은 문법 검사를 수행합니다.

## 업데이트

Git으로 설치했다면:

```bash
git pull
./run.sh
```

`requirements.txt`가 변경되면 `run.sh`이 필요한 패키지를 다시 설치합니다.

## GitHub에 올리기

새 저장소를 만든 뒤:

```bash
git init
git add .
git commit -m "Initial release"
git branch -M main
git remote add origin https://github.com/lee-junyeol/MacMessageMerge.git
git push -u origin main
```

공개 배포 시에는 **GitHub Releases**에서 버전 태그(`v1.0.0`)를 만들고 소스 ZIP을 배포하는 방식을 권장합니다.

> GitHub Pages에는 정적 안내 페이지를 만들 수는 있지만, 이 앱 자체를 Pages에서 실행해 Messages를 제어할 수는 없습니다.

## 프로젝트 구조

```text
MacMessageMerge/
├── app.py
├── sender.py
├── csv_parser.py
├── message_utils.py
├── requirements.txt
├── run.sh
├── scripts/
│   └── send_message.applescript
├── templates/
│   └── index.html
├── static/
│   ├── css/style.css
│   └── js/app.js
├── tests/
│   └── test_core.py
├── sample_contacts.csv
├── CHANGELOG.md
├── SECURITY.md
├── LICENSE
└── .gitignore
```

## 제한사항

- Apple이 제공하는 공식 대량 메시지 API를 사용하는 앱이 아니라 **macOS UI 자동화**입니다.
- macOS/Messages 업데이트로 UI 구조가 바뀌면 전송 로직 수정이 필요할 수 있습니다.
- 같은 상대와의 메시지는 Messages가 기존 대화 기록과 한 스레드로 표시할 수 있습니다. 이 앱이 보장하는 것은 매 전송 시 새 작성 동작을 시작하는 것입니다.
- 실제 전송 경로(iMessage/SMS/MMS/RCS), 요금, 이동통신사 정책은 Messages와 사용자의 Apple/통신사 설정에 따릅니다.
- 수신 동의를 받은 대상에게만 사용하고, 스팸·괴롭힘·무단 광고 발송에 사용하지 마세요.

## 라이선스

MIT License. `LICENSE` 참고.

## 참고

- Apple Messages User Guide — Send a message on Mac: https://support.apple.com/guide/messages/send-messages-icht35827/mac
- Apple Messages User Guide — Keyboard shortcuts: https://support.apple.com/guide/messages/keyboard-shortcuts-ichtc78b3bff/mac
- Apple Support — Set up Messages on Mac / Text Message Forwarding: https://support.apple.com/guide/messages/set-up-messages-on-mac-ichte16154fb/mac
- Apple Support — Accessibility permission: https://support.apple.com/guide/mac-help/allow-accessibility-apps-to-access-your-mac-mh43185/mac
