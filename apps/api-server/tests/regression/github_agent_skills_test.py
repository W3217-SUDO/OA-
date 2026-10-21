import asyncio
import hashlib
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from zipfile import ZipFile

import httpx
from fastapi import HTTPException

from app.github_agent_skills import DOWNLOAD_LIMIT, github_skill_location, parse_github_skill, preview_github_skill

CONTENT = b'---\nname: test-skill\ndescription: Safe declarative instructions\n---\n# Rules\nOnly summarize visible information.\n'


class GitHubSkillParserTest(unittest.TestCase):
    def test_enable_disable_normalization_preserves_import_digest(self):
        from app.user_agent_skills import custom_skill_public, normalize_custom_skill

        preview = parse_github_skill(CONTENT, github_skill_location('https://github.com/a/b'))
        record = normalize_custom_skill(preview, source=preview['source'])
        for enabled in (False, True):
            record = normalize_custom_skill({**record, 'enabled': enabled}, skill_id=record['id'], source=record['source'])
            self.assertEqual(record['sha256'], preview['sha256'])
            self.assertEqual(custom_skill_public(record)['sha256'], preview['sha256'])
            self.assertEqual(record['enabled'], enabled)
        self.assertNotIn('sha256', normalize_custom_skill({**preview, 'sha256': 'bad'}, source=preview['source']))
        self.assertNotIn('sha256', normalize_custom_skill(preview))

    def test_locations_share_source_and_directory_resolves_skill_file(self):
        canonical = github_skill_location('https://github.com/org/repo/blob/main/skills/test/SKILL.md')
        for url in ('https://raw.githubusercontent.com/org/repo/main/skills/test/SKILL.md',
                    'https://github.com/org/repo/tree/main/skills/test'):
            self.assertEqual(github_skill_location(url), canonical)
        self.assertEqual(github_skill_location('https://github.com/org/repo')['path'], 'SKILL.md')

    def test_invalid_urls_cannot_reach_network(self):
        for url in ('http://github.com/a/b', 'https://github.com.evil/a/b', 'https://github.com:443/a/b',
                    'https://user@github.com/a/b', 'https://127.0.0.1/a/b',
                    'https://github.com/a/b/blob/main/%2e%2e/SKILL.md',
                    'https://github.com/a/b/blob/main/a%2fb/SKILL.md',
                    'https://github.com/a/b/blob/main/SKILL.md?download=1',
                    'https://github.com/a/b/blob/main/test.py'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                github_skill_location(url)

    def test_metadata_and_body_are_preserved_without_execution(self):
        location = github_skill_location('https://github.com/a/b')
        parsed = parse_github_skill(CONTENT, location)
        self.assertEqual(parsed['instruction'], '# Rules\nOnly summarize visible information.')
        self.assertEqual(parsed['source'], location['url'])
        self.assertEqual(len(parsed['sha256']), 64)
        for content in (b'no metadata', b'---\nname: [bad]\ndescription: test\n---\nlong enough body',
                        CONTENT + b'x' * 64001, b'\xff',
                        b'---\nname: !!python/object/apply:os.system ["echo unsafe"]\n---\nbody'):
            with self.subTest(content=content[:30]), self.assertRaises(ValueError):
                parse_github_skill(content, location)


class GitHubSkillDownloadTest(unittest.IsolatedAsyncioTestCase):
    async def test_fixed_skill_directory_download_checks_blob_and_ignores_unrelated_repository_files(self):
        from app.harness_agent.bundle_download import download_directory
        body = b'console.log("isolated resource")\n'
        blob_sha = hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body, usedforsecurity=False).hexdigest()
        location = github_skill_location('https://github.com/a/b/tree/' + 'a' * 40 + '/skills/example')
        calls = []

        def respond(request):
            calls.append(str(request.url))
            self.assertNotIn('authorization', request.headers)
            if request.url.path.endswith('/git/trees/' + 'a' * 40):
                return httpx.Response(200, json={'tree': [{'path': 'skills', 'type': 'tree', 'sha': 'b' * 40},
                    {'path': 'unrelated-large-file.bin', 'type': 'blob', 'size': 100000000}]})
            if request.url.path.endswith('/git/trees/' + 'b' * 40):
                return httpx.Response(200, json={'tree': [{'path': 'example', 'type': 'tree', 'sha': 'c' * 40}]})
            if request.url.path.endswith('/git/trees/' + 'c' * 40):
                return httpx.Response(200, json={'tree': [{'path': 'scripts/query.mjs', 'type': 'blob',
                    'mode': '100644', 'size': len(body), 'sha': blob_sha}]})
            self.assertEqual(request.url.host, 'api.github.com')
            self.assertEqual(request.url.path, '/repos/a/b/git/blobs/' + blob_sha)
            self.assertEqual(request.headers['Accept'], 'application/vnd.github.raw+json')
            return httpx.Response(200, content=body)

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            content = await download_directory(client, 'a/b', 'a' * 40, location)
        with ZipFile(BytesIO(content)) as archive:
            self.assertEqual(archive.namelist(), ['fixed/skills/example/scripts/query.mjs'])
            self.assertEqual(archive.read(archive.namelist()[0]), body)
        self.assertEqual(len(calls), 4)

    async def test_slow_response_has_a_total_deadline(self):
        class SlowStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                for byte in CONTENT:
                    await asyncio.sleep(0.005)
                    yield bytes([byte])

        with patch('app.github_agent_skills.DOWNLOAD_TIMEOUT', 0.02):
            with self.assertRaises(HTTPException) as failed:
                await preview_github_skill('https://github.com/a/b', transport=httpx.MockTransport(
                    lambda request: httpx.Response(200, stream=SlowStream())))
        self.assertEqual(failed.exception.status_code, 502)

    async def test_fixed_contents_target_and_no_redirect_following(self):
        calls = []

        def response(request):
            calls.append(str(request.url))
            self.assertEqual(request.headers['Accept'], 'application/vnd.github.raw+json')
            self.assertNotIn('Authorization', request.headers)
            return httpx.Response(200, content=CONTENT)

        result = await preview_github_skill('https://github.com/a/b', transport=httpx.MockTransport(response))
        self.assertEqual(calls, ['https://api.github.com/repos/a/b/contents/SKILL.md?ref=main'])
        self.assertEqual(result['name'], 'test-skill')
        for status in (302, 404, 429):
            with self.subTest(status=status), self.assertRaises(HTTPException) as caught:
                await preview_github_skill('https://github.com/a/b', transport=httpx.MockTransport(
                    lambda request: httpx.Response(status, headers={'location': 'http://127.0.0.1/secret'})))
            self.assertEqual(caught.exception.status_code, 422)

    async def test_ref_query_and_path_are_encoded_separately(self):
        calls = []

        def response(request):
            calls.append(request.url)
            self.assertEqual(request.url.host, 'api.github.com')
            self.assertEqual(dict(request.url.params), {'ref': 'release+&=1'})
            self.assertEqual(request.url.path, '/repos/org/repo/contents/skills/合同#&/SKILL.md')
            return httpx.Response(200, content=CONTENT)

        result = await preview_github_skill(
            'https://github.com/org/repo/blob/release%2B%26%3D1/skills/%E5%90%88%E5%90%8C%23%26/SKILL.md',
            transport=httpx.MockTransport(response))
        self.assertEqual(len(calls), 1)
        self.assertIn('ref=release%2B%26%3D1', str(calls[0]))
        self.assertIn('/%E5%90%88%E5%90%8C%23%26/', str(calls[0]))
        self.assertEqual(result['ref'], 'release+&=1')
        self.assertNotIn('contents_url', result)

    async def test_size_limit_and_connection_failure(self):
        with self.assertRaises(HTTPException) as large:
            await preview_github_skill('https://github.com/a/b', transport=httpx.MockTransport(
                lambda request: httpx.Response(200, content=b'x' * (DOWNLOAD_LIMIT + 1))))
        self.assertEqual(large.exception.status_code, 422)

        def offline(request):
            raise httpx.ConnectError('offline', request=request)

        with self.assertRaises(HTTPException) as failed:
            await preview_github_skill('https://github.com/a/b', transport=httpx.MockTransport(offline))
        self.assertEqual(failed.exception.status_code, 502)


class GitHubSkillInstallContractTest(unittest.IsolatedAsyncioTestCase):
    async def test_imported_skill_selection_respects_owner_and_enabled_state(self):
        from app.core.permissions import _agent_skill_for_identity
        from app.user_agent_skills import normalize_custom_skill

        preview = parse_github_skill(CONTENT, github_skill_location('https://github.com/a/b'))
        record = normalize_custom_skill(preview, source=preview['source'])

        async def store(username, db):
            return None, [record] if username == 'owner' else []

        with patch('app.core.documents._user_agent_skill_store', side_effect=store):
            selected = await _agent_skill_for_identity(record['id'], {'username': 'owner'}, object())
            self.assertIn(preview['instruction'], selected.instruction)
            with self.assertRaises(HTTPException) as other:
                await _agent_skill_for_identity(record['id'], {'username': 'other'}, object())
            self.assertEqual(other.exception.status_code, 404)
            record['enabled'] = False
            with self.assertRaises(HTTPException) as disabled:
                await _agent_skill_for_identity(record['id'], {'username': 'owner'}, object())
            self.assertEqual(disabled.exception.status_code, 409)

    async def test_install_uses_identity_and_rejects_changed_preview(self):
        from app.areas.personal_agent.router import GitHubSkillInstallInput, github_skill_install

        preview = parse_github_skill(CONTENT, github_skill_location('https://github.com/a/b'))
        identity = {'username': 'isolated-owner', 'role': 'user'}
        db = AsyncMock()
        with patch('app.github_agent_skills.preview_github_skill', AsyncMock(return_value=preview)), \
                patch('app.harness_agent.bundles.install_bundle', AsyncMock(return_value={'id': 'a' * 64, 'commit': 'b' * 40, 'files': {'SKILL.md': preview['sha256']}})), \
                patch('app.core.documents._user_agent_skill_store', AsyncMock(return_value=(None, []))) as store, \
                patch('app.core.documents._save_user_agent_skills', AsyncMock()) as save:
            result = await github_skill_install(GitHubSkillInstallInput(url=preview['url'], sha256=preview['sha256']), identity, db)
            self.assertEqual(result['source'], preview['url'])
            self.assertEqual(store.await_count, 2)
            store.assert_awaited_with('isolated-owner', db)
            saved = save.await_args.args
            self.assertEqual(saved[0], 'isolated-owner')
            self.assertEqual(saved[1][0]['sha256'], preview['sha256'])
            self.assertEqual(saved[2], identity)
            save.reset_mock()
            with self.assertRaises(HTTPException) as changed:
                await github_skill_install(GitHubSkillInstallInput(url=preview['url'], sha256='0' * 64), identity, db)
            self.assertEqual(changed.exception.status_code, 409)
            save.assert_not_awaited()

    async def test_same_source_is_idempotent_and_different_content_blocks_overwrite(self):
        from app.areas.personal_agent.router import GitHubSkillInstallInput, github_skill_install
        from app.user_agent_skills import normalize_custom_skill

        preview = parse_github_skill(CONTENT, github_skill_location('https://github.com/a/b'))
        existing = {**normalize_custom_skill(preview, source=preview['source']), 'sha256': preview['sha256'],
                    'bundle': {'id': 'a' * 64, 'commit': 'b' * 40, 'files': {'SKILL.md': preview['sha256']}}}
        with patch('app.github_agent_skills.preview_github_skill', AsyncMock(return_value=preview)), \
                patch('app.core.documents._user_agent_skill_store', AsyncMock(return_value=(None, [existing]))), \
                patch('app.core.documents._save_user_agent_skills', AsyncMock()) as save:
            body = GitHubSkillInstallInput(url=preview['url'], sha256=preview['sha256'])
            result = await github_skill_install(body, {'username': 'isolated-owner'}, object())
            self.assertEqual(result['id'], existing['id'])
            existing['instruction'] += '\nLocal edits that must not be overwritten.'
            with self.assertRaises(HTTPException) as edited:
                await github_skill_install(body, {'username': 'isolated-owner'}, object())
            self.assertEqual(edited.exception.status_code, 409)
            existing['instruction'] = preview['instruction']
            existing['sha256'] = '0' * 64
            with self.assertRaises(HTTPException) as conflict:
                await github_skill_install(body, {'username': 'isolated-owner'}, object())
            self.assertEqual(conflict.exception.status_code, 409)
            save.assert_not_awaited()


class FullSkillBundleTest(unittest.TestCase):
    def test_market_text_digest_preserves_original_bom_and_crlf_bytes(self):
        from app.harness_agent.bundles import _unpack, read_resource
        location = github_skill_location('https://github.com/a/b/tree/main/skills/example')
        source_text = CONTENT.decode()
        original = b'\xef\xbb\xbf' + CONTENT.replace(b'\n', b'\r\n')
        content = BytesIO()
        with ZipFile(content, 'w') as archive:
            archive.writestr('repo-fixed/skills/example/SKILL.md', original)
        with tempfile.TemporaryDirectory() as temporary, patch('app.harness_agent.bundles.storage_root', return_value=Path(temporary)):
            bundle = _unpack(content.getvalue(), location, hashlib.sha256(source_text.encode()).hexdigest(), source_text)
            self.assertEqual(read_resource(bundle, 'SKILL.md'), original)
            with self.assertRaises(HTTPException):
                _unpack(content.getvalue(), location, hashlib.sha256(source_text.encode()).hexdigest(), source_text + 'changed')

    def archive(self, extra):
        content = BytesIO()
        with ZipFile(content, 'w') as archive:
            archive.writestr('repo-fixed/skills/example/SKILL.md', CONTENT)
            for path, data in extra.items():
                archive.writestr('repo-fixed/skills/example/' + path, data)
        return content.getvalue()

    def test_fixed_directory_keeps_resources_and_rejects_tampering(self):
        from app.harness_agent.bundles import _unpack, read_resource
        from app.user_agent_skills import normalize_custom_skill, custom_skill_agent
        location = github_skill_location('https://github.com/a/b/tree/main/skills/example')
        digest = hashlib.sha256(CONTENT).hexdigest()
        with tempfile.TemporaryDirectory() as temporary, patch('app.harness_agent.bundles.storage_root', return_value=Path(temporary)):
            bundle = _unpack(self.archive({'references/rules.md': b'authorized reference'}), location, digest)
            bundle['commit'] = 'a' * 40
            self.assertEqual(read_resource(bundle, 'references/rules.md'), b'authorized reference')
            preview = parse_github_skill(CONTENT, location)
            record = normalize_custom_skill({**preview, 'bundle': bundle}, source=preview['source'])
            self.assertEqual(custom_skill_agent(record).bundle, bundle)
            self.assertNotIn('bundle', custom_skill_agent(record).public_dict())
            (Path(temporary) / bundle['id'] / 'references/rules.md').write_bytes(b'changed')
            with self.assertRaises(HTTPException) as failure:
                read_resource(bundle, 'references/rules.md')
            self.assertEqual(failure.exception.status_code, 409)

    def test_archive_escape_and_changed_preview_block_installation(self):
        from app.harness_agent.bundles import _unpack
        location = github_skill_location('https://github.com/a/b/tree/main/skills/example')
        with tempfile.TemporaryDirectory() as temporary, patch('app.harness_agent.bundles.storage_root', return_value=Path(temporary)):
            with self.assertRaises(ValueError):
                _unpack(self.archive({'../outside.md': b'blocked'}), location, hashlib.sha256(CONTENT).hexdigest())
            with self.assertRaises(HTTPException) as changed:
                _unpack(self.archive({}), location, '0' * 64)
            self.assertEqual(changed.exception.status_code, 409)
            self.assertEqual(list(Path(temporary).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
