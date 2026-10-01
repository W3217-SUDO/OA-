import {readFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawn} from 'node:child_process';

if (Number(process.versions.node.split('.')[0]) !== 22) throw new Error('DeepSeek Harness 要求 Node.js 22，请先切换 Node 版本');
const hostRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const port = Number(process.env.DSH_PORT ?? 3081);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('DSH_PORT 必须在 1 到 65535 之间');
const packageRoot = path.join(hostRoot, 'node_modules', '@deepseek-ai', 'dsh');
const manifest = JSON.parse(readFileSync(path.join(packageRoot, 'package.json'), 'utf8'));
const binary = typeof manifest.bin === 'string' ? manifest.bin : manifest.bin?.dsh;
if (!binary) throw new Error('已安装的 DeepSeek Harness 没有 dsh 启动入口');
const executable = path.resolve(packageRoot, binary);
if (path.relative(packageRoot, executable).startsWith('..')) throw new Error('DeepSeek Harness 启动入口路径无效');
const child = spawn(process.execPath, [executable, 'web', '--host', '127.0.0.1', '--port', String(port), '--no-open', ...process.argv.slice(2)], {
  cwd: hostRoot, stdio: 'inherit', env: process.env,
});
child.on('error', (error) => { throw error; });
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => { child.kill(signal); });
}
child.on('exit', (code, signal) => {
  process.exitCode = code ?? (signal === 'SIGINT' ? 130 : signal === 'SIGTERM' ? 143 : 1);
});
