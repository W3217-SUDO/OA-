import {readdirSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
function collect(directory) {
  return readdirSync(directory, {withFileTypes: true}).flatMap(entry => {
    if (entry.isSymbolicLink()) throw new Error(`测试目录不能是符号链接：${entry.name}`);
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) return entry.name === 'integration' ? [] : collect(target);
    return /\.test\.(?:mjs|ts)$/.test(entry.name) ? [target] : [];
  });
}
const files = collect(path.join(frontend, 'tests')).sort();
if (!files.length) throw new Error('没有找到前端独立测试');
const result = spawnSync(process.execPath, ['--experimental-strip-types', '--test', ...process.argv.slice(2), ...files], {cwd: frontend, stdio: 'inherit'});
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
