"""Pure configuration/token contracts; no database, document or OSS writes."""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.parse import urlencode

import jwt
from fastapi import HTTPException
from starlette.requests import Request

from app.config import settings
from app.core.libreoffice_config import editor_configuration
from app.core.libreoffice_files import revision_path
from app.core.libreoffice_security import WOPI_AUDIENCE, WOPI_ISSUER, request_token, session_token


class PersonalOfficeSecurityTest(unittest.TestCase):
    def setUp(self):
        self.configuration = patch.multiple(
            settings, office_editor_enabled=False, office_personal_editor_enabled=True,
            code_server_url='http://127.0.0.1:9980', code_browser_url='https://office.example.com',
            office_wopi_base_url='https://oa.example.com', office_frontend_origin='https://oa.example.com',
            office_trusted_origins=['http://127.0.0.1:9980', 'https://office.example.com', 'https://oa.example.com'],
            office_wopi_token_secret='pure-unit-test-key-not-a-production-secret',
        )
        self.configuration.start()
        self.addCleanup(self.configuration.stop)
        self.session = {'scope': 'personal', 'file_id': 'a' * 32, 'owner_user_id': 1,
                        'user': 'owner', 'attachment_id': 9, 'id': 'b' * 32, 'token_id': 'c' * 32,
                        'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()}

    def request(self, token):
        return Request({'type': 'http', 'method': 'GET', 'path': '/wopi',
                        'query_string': urlencode({'access_token': token}).encode(), 'headers': []})

    def test_personal_enable_does_not_enable_case_editing(self):
        self.assertEqual(editor_configuration(personal=True)['frontend'], 'https://oa.example.com')
        with self.assertRaises(HTTPException) as blocked:
            editor_configuration()
        self.assertEqual(blocked.exception.status_code, 503)

    def test_personal_token_binds_scope_file_owner_without_case_id(self):
        _, claims = request_token(self.request(session_token(self.session)), self.session['id'])
        self.assertEqual(claims['scope'], 'personal')
        self.assertEqual(claims['file_id'], 'a' * 32)
        self.assertEqual(claims['owner_user_id'], 1)
        self.assertNotIn('case_id', claims)
        with self.assertRaises(HTTPException):
            request_token(self.request(session_token(self.session)), 'd' * 32)

    def test_confused_scope_or_tampered_token_is_rejected(self):
        claims = jwt.decode(session_token(self.session), settings.office_wopi_token_secret, algorithms=['HS256'],
                            audience=WOPI_AUDIENCE, issuer=WOPI_ISSUER)
        for changes in ({'case_id': 1}, {'scope': 'unknown'}, {'owner_user_id': '1'}, {'file_id': '../bad'}):
            token = jwt.encode({**claims, **changes}, settings.office_wopi_token_secret, algorithm='HS256')
            with self.subTest(changes=changes), self.assertRaises(HTTPException) as denied:
                request_token(self.request(token), self.session['id'])
            self.assertEqual(denied.exception.status_code, 401)
        wrong_key = jwt.encode(claims, 'another-unit-key-not-a-production-secret', algorithm='HS256')
        with self.assertRaises(HTTPException):
            request_token(self.request(wrong_key), self.session['id'])

    def test_legacy_case_token_remains_supported_when_case_flag_enabled(self):
        case = {**self.session, 'case_id': 4}
        case.pop('scope')
        with patch.object(settings, 'office_editor_enabled', True):
            _, claims = request_token(self.request(session_token(case)), case['id'])
        self.assertEqual(claims['case_id'], 4)
        self.assertNotIn('file_id', claims)

    def test_personal_revision_stays_in_approved_owner_folder(self):
        from types import SimpleNamespace
        session = {**self.session, 'revision_folder': 'ai/personal/Owner--u1'}
        path = revision_path(SimpleNamespace(path='oss://ai-unit-bucket/ai/personal/old.docx'), session, 'e' * 64)
        self.assertEqual(path, 'oss://ai-unit-bucket/ai/personal/Owner--u1/office-versions/' + 'a' * 32 + '/' + 'b' * 32 + '/' + 'e' * 64 + '.docx')

    def test_malformed_legacy_metadata_is_explicitly_blocked(self):
        from app.core.personal_libreoffice import personal_metadata
        good = {'owner_user_id': 1, 'space_id': 2, 'attachment_id': 3, 'case_id': None,
                'name': 'unit.docx', 'stored_name': 'unit', 'path': 'oss://ai-unit-bucket/ai/unit', 'size': 64}
        self.assertEqual(personal_metadata(good), good)
        for data in (None, [], {}, {**good, 'owner_user_id': True}, {**good, 'space_id': {}},
                     {**good, 'attachment_id': None}, {**good, 'case_id': '4'}, {**good, 'versions': {}},
                     {**good, 'libreoffice_sessions': []}, {**good, 'stored_name': None}):
            with self.subTest(data=data), self.assertRaises(HTTPException) as malformed:
                personal_metadata(data)
            self.assertEqual(malformed.exception.status_code, 409)


if __name__ == '__main__':
    unittest.main()
