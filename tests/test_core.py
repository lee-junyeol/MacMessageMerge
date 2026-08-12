import unittest

from csv_parser import parse_csv, validate_phone
from message_utils import merge_message


class CsvParserTests(unittest.TestCase):
    def test_utf8_csv(self):
        raw = '이름,전화번호\n김민수,010-1234-5678\n'.encode('utf-8')
        contacts, skipped = parse_csv(raw)
        self.assertEqual(skipped, 0)
        self.assertEqual(contacts[0]['name'], '김민수')
        self.assertEqual(contacts[0]['phone'], '01012345678')

    def test_cp949_csv(self):
        raw = '성명,휴대폰\n이영희,010-2222-3333\n'.encode('cp949')
        contacts, skipped = parse_csv(raw)
        self.assertEqual(skipped, 0)
        self.assertEqual(contacts[0]['name'], '이영희')

    def test_duplicate_phone_is_skipped(self):
        raw = '이름,전화번호\nA,010-1111-2222\nB,01011112222\n'.encode('utf-8')
        contacts, skipped = parse_csv(raw)
        self.assertEqual(len(contacts), 1)
        self.assertEqual(skipped, 1)


class MessageTests(unittest.TestCase):
    def test_merge(self):
        rendered = merge_message('{name}님 / {phone}', {'name': '김민수', 'phone': '01012345678'})
        self.assertEqual(rendered, '김민수님 / 01012345678')

    def test_phone_validation(self):
        ok, normalized = validate_phone('+82 10-1234-5678')
        self.assertTrue(ok)
        self.assertEqual(normalized, '+821012345678')


if __name__ == '__main__':
    unittest.main()
