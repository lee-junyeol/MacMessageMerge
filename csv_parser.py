import csv
import re
from io import StringIO

NAME_HEADERS = ('이름', '성명', 'name')
PHONE_HEADERS = ('전화번호', '휴대폰', '핸드폰', '연락처', '전화', 'phone', 'mobile', 'tel')
SUPPORTED_ENCODINGS = ('utf-8-sig', 'cp949', 'euc-kr')


def decode_csv(raw: bytes) -> str:
    for encoding in SUPPORTED_ENCODINGS:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError('CSV 인코딩을 읽을 수 없습니다. UTF-8 또는 CP949로 저장해주세요.')


def normalize_header(value: str) -> str:
    return re.sub(r'\s+', '', str(value or '')).lower()


def find_column_index(headers, keywords):
    normalized = [normalize_header(header) for header in headers]
    for index, header in enumerate(normalized):
        if any(keyword in header for keyword in keywords):
            return index
    return None


def normalize_phone(phone: str) -> str:
    value = str(phone or '').strip()
    if value.startswith('+'):
        return '+' + re.sub(r'\D', '', value[1:])
    return re.sub(r'\D', '', value)


def validate_phone(phone: str):
    normalized = normalize_phone(phone)
    digits = re.sub(r'\D', '', normalized)
    if len(digits) < 10 or len(digits) > 15:
        return False, '전화번호는 국가번호를 포함해 10~15자리 숫자여야 합니다.'
    return True, normalized


def parse_csv(raw: bytes):
    content = decode_csv(raw).lstrip('\ufeff')
    if not content.strip():
        return [], 0

    try:
        dialect = csv.Sniffer().sniff(content[:4096], delimiters=',;\t')
    except csv.Error:
        dialect = csv.excel

    rows = list(csv.reader(StringIO(content), dialect))
    if not rows:
        return [], 0

    first_row = rows[0]
    name_idx = find_column_index(first_row, NAME_HEADERS)
    phone_idx = find_column_index(first_row, PHONE_HEADERS)
    has_header = name_idx is not None or phone_idx is not None

    name_idx = 0 if name_idx is None else name_idx
    phone_idx = 1 if phone_idx is None else phone_idx
    data_rows = rows[1:] if has_header else rows

    contacts = []
    skipped = 0
    seen = set()

    for row in data_rows:
        if max(name_idx, phone_idx) >= len(row):
            skipped += 1
            continue

        name = str(row[name_idx]).strip()
        phone_raw = str(row[phone_idx]).strip()
        valid, phone_or_error = validate_phone(phone_raw)
        if not name or not valid:
            skipped += 1
            continue

        canonical = re.sub(r'\D', '', phone_or_error)
        if canonical in seen:
            skipped += 1
            continue
        seen.add(canonical)

        contacts.append({'name': name, 'phone': phone_or_error})

    return contacts, skipped
