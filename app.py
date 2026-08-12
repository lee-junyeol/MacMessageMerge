from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
import os

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException
from waitress import serve

from csv_parser import parse_csv, validate_phone
from message_utils import merge_message
from sender import diagnostics, send_message

APP_NAME = 'MacMessageMerge'
APP_VERSION = '1.0.0'
HOST = '127.0.0.1'
PORT = int(os.environ.get('PORT', '5001'))
MAX_FILE_SIZE = 2 * 1024 * 1024
MAX_RECIPIENTS = 300
MAX_MESSAGE_CHARS = 2000
ALLOWED_ORIGINS = {f'http://{HOST}:{PORT}', f'http://localhost:{PORT}'}

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE


def configure_logging():
    log_dir = Path.home() / 'Library' / 'Logs' / APP_NAME
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(log_dir / 'app.log', maxBytes=256_000, backupCount=3)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    logging.getLogger('mac-message-merge').addHandler(handler)
    logging.getLogger('mac-message-merge').setLevel(logging.INFO)


@app.before_request
def restrict_cross_origin_mutations():
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        origin = request.headers.get('Origin')
        if origin and origin not in ALLOWED_ORIGINS:
            return jsonify({'success': False, 'message': '허용되지 않은 요청 출처입니다.'}), 403


@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; style-src 'self'; script-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
    )
    return response


@app.errorhandler(413)
def too_large(_error):
    return jsonify({'success': False, 'message': 'CSV 파일은 2MB를 초과할 수 없습니다.'}), 413


@app.errorhandler(Exception)
def api_error(error):
    if request.path.startswith('/api/'):
        if isinstance(error, HTTPException):
            return jsonify({'success': False, 'message': error.description}), error.code
        app.logger.exception('처리되지 않은 API 오류')
        return jsonify({'success': False, 'message': '서버 오류가 발생했습니다. 로그를 확인해주세요.'}), 500
    raise error


@app.get('/')
def index():
    return render_template('index.html', app_name=APP_NAME, app_version=APP_VERSION)


@app.get('/api/health')
def health():
    return jsonify({'success': True, 'app': APP_NAME, 'version': APP_VERSION})


@app.get('/api/diagnostics')
def run_diagnostics():
    result = diagnostics()
    result['ready'] = not result['errors']
    result['success'] = True
    result['send_mode'] = '수신자마다 Command-N으로 새 메시지 작성'
    return jsonify(result)


@app.post('/api/parse-csv')
def parse_contacts_csv():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'CSV 파일을 선택해주세요.'}), 400

    file = request.files['file']
    if not file.filename or not file.filename.lower().endswith('.csv'):
        return jsonify({'success': False, 'message': 'CSV 파일만 사용할 수 있습니다.'}), 400

    raw = file.read()
    if not raw:
        return jsonify({'success': False, 'message': '빈 CSV 파일입니다.'}), 400

    try:
        contacts, skipped = parse_csv(raw)
    except ValueError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400

    if not contacts:
        return jsonify({'success': False, 'message': '유효한 이름/전화번호를 찾지 못했습니다.'}), 400
    if len(contacts) > MAX_RECIPIENTS:
        return jsonify({
            'success': False,
            'message': f'한 번에 최대 {MAX_RECIPIENTS}명까지 불러올 수 있습니다.'
        }), 400

    return jsonify({'success': True, 'contacts': contacts, 'skipped': skipped, 'count': len(contacts)})


@app.post('/api/send')
def send():
    data = request.get_json(silent=True) or {}
    recipients = data.get('recipients') or []
    template = str(data.get('message') or '')

    if not template.strip():
        return jsonify({'success': False, 'message': '메시지 내용을 입력해주세요.'}), 400
    if len(template) > MAX_MESSAGE_CHARS:
        return jsonify({'success': False, 'message': f'메시지는 {MAX_MESSAGE_CHARS}자 이하로 입력해주세요.'}), 400
    if not recipients:
        return jsonify({'success': False, 'message': '수신자를 한 명 이상 추가해주세요.'}), 400
    if len(recipients) > MAX_RECIPIENTS:
        return jsonify({'success': False, 'message': f'한 번에 최대 {MAX_RECIPIENTS}명까지 전송할 수 있습니다.'}), 400

    results = []
    stopped_early = False

    for index, recipient in enumerate(recipients):
        name = str(recipient.get('name') or '').strip()
        phone = str(recipient.get('phone') or '').strip()
        valid, phone_or_error = validate_phone(phone)
        if not valid:
            results.append({'name': name, 'phone': phone, 'success': False, 'message': phone_or_error})
            continue

        rendered = merge_message(template, {'name': name, 'phone': phone_or_error})
        result = send_message(phone_or_error, rendered)
        results.append({
            'name': name,
            'phone': phone_or_error,
            'success': result.success,
            'message': result.message,
        })

        if not result.success and result.fatal:
            stopped_early = True
            remaining = recipients[index + 1:]
            for item in remaining:
                results.append({
                    'name': str(item.get('name') or '').strip(),
                    'phone': str(item.get('phone') or '').strip(),
                    'success': False,
                    'message': '시스템/UI 오류로 전송을 중단했습니다.'
                })
            break

    success_count = sum(1 for item in results if item['success'])
    return jsonify({
        'success': True,
        'results': results,
        'success_count': success_count,
        'failure_count': len(results) - success_count,
        'stopped_early': stopped_early,
    })


if __name__ == '__main__':
    configure_logging()
    print(f'{APP_NAME} {APP_VERSION}')
    print(f'http://{HOST}:{PORT}')
    print('이 서버는 127.0.0.1에만 바인딩됩니다. 종료: Ctrl+C')
    serve(app, host=HOST, port=PORT, threads=4)
