"""从独立运行包启动 API 和静态资源，仅验证运行与产物隔离。"""

from __future__ import annotations

import argparse
from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from runtime_package import verify


class AssetReferences(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.paths: set[str] = set()

    def handle_starttag(self, tag, attributes) -> None:
        values = dict(attributes)
        reference = values.get('src') if tag == 'script' else values.get('href') if tag == 'link' else None
        if reference and urlsplit(reference).path.startswith('/assets/'):
            self.paths.add(urlsplit(reference).path)


class StaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args) -> None:
        pass


def read_url(url: str) -> bytes:
    with urlopen(url, timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(f'运行资源返回 {response.status}：{url}')
        return response.read()


def check_runtime(package: Path, report_dir: Path) -> dict:
    manifest = verify(package)
    report_dir.mkdir(parents=True, exist_ok=True)
    api_directory = package / 'api'
    with tempfile.TemporaryDirectory(prefix='oa-test-runtime-') as temporary:
        scope = Path(temporary)
        environment = {key: value for key, value in os.environ.items() if key.upper() in {
            'PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'HOME', 'LOCALAPPDATA',
        }}
        environment.update(
            APP_ENV='production', DATABASE_URL=f'sqlite+aiosqlite:///{(scope / "runtime.db").as_posix()}',
            UPLOAD_ROOT=str(scope / 'uploads'), SECRET_KEY=secrets.token_hex(48),
            INITIAL_ADMIN_PASSWORD=secrets.token_urlsafe(24), SEED_DEMO_DATA='false',
            PYTHONPATH=str(api_directory), PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1',
        )
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            api_port = reservation.getsockname()[1]
        api_url = f'http://127.0.0.1:{api_port}'
        log_path = report_dir / 'runtime-api.log'
        with log_path.open('wb') as output:
            process = subprocess.Popen(
                [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(api_port)],
                cwd=scope, env=environment, stdout=output, stderr=subprocess.STDOUT,
            )
            try:
                deadline = time.monotonic() + 180
                while True:
                    if process.poll() is not None:
                        raise RuntimeError(f'运行包 API 启动失败，退出码 {process.returncode}，日志：{log_path}')
                    try:
                        health = json.loads(read_url(f'{api_url}/health'))
                        break
                    except (URLError, TimeoutError):
                        if time.monotonic() >= deadline:
                            raise RuntimeError(f'运行包 API 健康检查超时，日志：{log_path}')
                        time.sleep(0.2)
                if health.get('status') != 'ok':
                    raise RuntimeError(f'API 健康状态不正确：{health}')
                import_check = subprocess.run(
                    [sys.executable, '-c',
                     'import app,importlib.util,pathlib; '
                     f'assert pathlib.Path(app.__file__).resolve().is_relative_to(pathlib.Path({str(api_directory)!r})); '
                     'assert importlib.util.find_spec("test_lean_main") is None; '
                     'assert not (pathlib.Path(app.__file__).parent.parent / "tests").exists()'],
                    cwd=scope, env=environment, capture_output=True, encoding='utf-8', check=True,
                )
                (report_dir / 'runtime-import.log').write_text(import_check.stdout + import_check.stderr, encoding='utf-8')
                server = ThreadingHTTPServer(('127.0.0.1', 0), partial(StaticHandler, directory=str(package / 'web')))
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    web_url = f'http://127.0.0.1:{server.server_port}'
                    index = read_url(f'{web_url}/index.html').decode('utf-8')
                    parser = AssetReferences()
                    parser.feed(index)
                    if not parser.paths:
                        raise RuntimeError('前端入口没有正式构建资源')
                    for asset in sorted(parser.paths):
                        if not read_url(web_url + asset):
                            raise RuntimeError(f'前端构建资源为空：{asset}')
                    build_info = json.loads(read_url(f'{web_url}/build-info.json'))
                    if build_info['source_commit'] != manifest['source_commit']:
                        raise RuntimeError('运行页面的提交标记与运行包不一致')
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=5)
                return {'status': 'passed', 'health': health, 'source_commit': manifest['source_commit'], 'static_assets': len(parser.paths)}
            finally:
                if process.poll() is None:
                    if os.name == 'nt':
                        # Windows 虚拟环境启动器会创建子进程，必须回收整棵任务进程树。
                        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, check=True)
                    else:
                        process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--report-dir', type=Path, required=True)
    args = parser.parse_args()
    result = check_runtime(args.package.resolve(), args.report_dir.resolve())
    (args.report_dir / 'runtime-health.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
