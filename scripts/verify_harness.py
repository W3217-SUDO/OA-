"""在独立临时目录与端口验证智能体宿主启动，不打开浏览器。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', required=True)
    parser.add_argument('--report-dir', type=Path, required=True)
    args = parser.parse_args()
    report_dir = args.report_dir.resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='oa-test-harness-') as temporary:
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        environment = os.environ.copy()
        environment['DSH_HOME'] = temporary
        environment['DSH_PORT'] = str(port)
        log_path = report_dir / 'harness-startup.log'
        with log_path.open('wb') as output:
            process = subprocess.Popen(
                [args.node, str(ROOT / 'apps/deepseek-harness-host/scripts/start.mjs')],
                cwd=ROOT / 'apps/deepseek-harness-host', env=environment,
                stdout=output, stderr=subprocess.STDOUT,
            )
            try:
                deadline = time.monotonic() + 120
                while True:
                    if process.poll() is not None:
                        raise RuntimeError(f'智能体宿主启动失败，退出码 {process.returncode}，日志：{log_path}')
                    try:
                        with urlopen(f'http://127.0.0.1:{port}/', timeout=5) as response:
                            document = response.read().decode('utf-8')
                            if response.status != 200 or '<html' not in document.lower():
                                raise RuntimeError('智能体宿主没有返回有效入口页面')
                        break
                    except (URLError, TimeoutError):
                        if time.monotonic() >= deadline:
                            raise RuntimeError(f'智能体宿主启动超时，日志：{log_path}')
                        time.sleep(0.2)
                result = {'status': 'passed', 'node': subprocess.check_output([args.node, '--version'], encoding='utf-8').strip(), 'port': port}
                (report_dir / 'harness-health.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
                print(json.dumps(result))
            finally:
                if process.poll() is None:
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, check=True)
                    else:
                        process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == '__main__':
    main()
