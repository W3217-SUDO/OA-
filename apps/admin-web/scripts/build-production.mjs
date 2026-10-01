import { createHash } from 'node:crypto';
import { existsSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function collectFiles(directory, prefix) {
  if (!existsSync(directory)) return [];
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const absolute = path.join(directory, entry.name);
    const relative = `${prefix}/${entry.name}`;
    if (entry.isSymbolicLink()) throw new Error(`构建输入不能是符号链接：${relative}`);
    return entry.isDirectory() ? collectFiles(absolute, relative) : [relative];
  });
}

function sourceHashes() {
  const inputs = [
    ...collectFiles(path.join(frontend, 'src'), 'src'),
    ...collectFiles(path.join(frontend, 'public'), 'public'),
    'scripts/build-production.mjs',
    ...readdirSync(frontend).filter((name) =>
      /^(package(?:-lock)?\.json|index\.html|tsconfig.*\.json|vite\.config\.ts)$/.test(name)),
  ].sort();
  return Object.fromEntries(inputs.map((relative) => {
    const absolute = path.join(frontend, ...relative.split('/'));
    if (!statSync(absolute).isFile()) throw new Error(`构建输入不是文件：${relative}`);
    return [relative, createHash('sha256').update(readFileSync(absolute)).digest('hex')];
  }));
}

function execute(relative, args) {
  const executable = path.join(frontend, 'node_modules', relative);
  const result = spawnSync(process.execPath, [executable, ...args], { cwd: frontend, stdio: 'inherit' });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`生产构建失败：${relative}，退出码 ${result.status}`);
}

let sourceCommit = process.env.SOURCE_COMMIT;
if (!sourceCommit) {
  const commit = spawnSync('git', ['rev-parse', 'HEAD'], { cwd: frontend, encoding: 'utf8' });
  if (commit.error) throw commit.error;
  if (commit.status !== 0) throw new Error('无法确定构建源码提交，请设置 SOURCE_COMMIT');
  sourceCommit = commit.stdout.trim();
}
if (!/^[0-9a-f]{40}$/.test(sourceCommit)) throw new Error('SOURCE_COMMIT 必须是完整源码提交号');
const before = sourceHashes();
execute('typescript/bin/tsc', ['-b']);
execute('vite/bin/vite.js', ['build']);
const after = sourceHashes();
if (JSON.stringify(before) !== JSON.stringify(after)) throw new Error('构建期间源码发生变化，请重新构建');
const info = {
  format: 1,
  version: JSON.parse(readFileSync(path.join(frontend, 'package.json'), 'utf8')).version,
  source_commit: sourceCommit,
  source_files: after,
};
writeFileSync(path.join(frontend, 'dist', 'build-info.json'), `${JSON.stringify(info, null, 2)}\n`, 'utf8');
