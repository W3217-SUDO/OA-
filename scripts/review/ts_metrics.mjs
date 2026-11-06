// 前端复杂度、函数长度、未被引用的导出。只用项目已有的 typescript，不加新依赖。
// 用法：node ts_metrics.mjs <前端目录>，结果以 JSON 输出到 stdout。
import {readdirSync, readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import path from 'node:path';

const web = path.resolve(process.argv[2]);
const ts = createRequire(path.join(web, 'package.json'))('typescript');
const MAX_COMPLEXITY = 15;
const MAX_FUNCTION_LINES = 200;

function collect(directory) {
  return readdirSync(directory, {withFileTypes: true}).flatMap(entry => {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) return collect(target);
    return /\.tsx?$/.test(entry.name) && !entry.name.endsWith('.d.ts') ? [target] : [];
  });
}

const BRANCHES = new Set([
  ts.SyntaxKind.IfStatement, ts.SyntaxKind.ForStatement, ts.SyntaxKind.ForInStatement, ts.SyntaxKind.ForOfStatement,
  ts.SyntaxKind.WhileStatement, ts.SyntaxKind.DoStatement, ts.SyntaxKind.CaseClause, ts.SyntaxKind.CatchClause,
  ts.SyntaxKind.ConditionalExpression,
]);
const LOGICAL = new Set([ts.SyntaxKind.AmpersandAmpersandToken, ts.SyntaxKind.BarBarToken, ts.SyntaxKind.QuestionQuestionToken]);
const isFunction = node => ts.isFunctionDeclaration(node) || ts.isFunctionExpression(node) || ts.isArrowFunction(node) || ts.isMethodDeclaration(node);

function complexity(fn) {
  let total = 1;
  const visit = node => {
    if (node !== fn && isFunction(node)) return; // 内层函数单独计
    if (BRANCHES.has(node.kind) || (ts.isBinaryExpression(node) && LOGICAL.has(node.operatorToken.kind))) total += 1;
    ts.forEachChild(node, visit);
  };
  visit(fn);
  return total;
}

function functionName(node) {
  if (node.name) return node.name.getText();
  if (node.parent && ts.isVariableDeclaration(node.parent)) return node.parent.name.getText();
  return '匿名函数';
}

const issues = [];
const exportsByFile = [];
const sources = new Map();
for (const file of collect(path.join(web, 'src'))) {
  const text = readFileSync(file, 'utf8');
  const relative = path.relative(web, file).split(path.sep).join('/');
  sources.set(relative, text);
  const source = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, file.endsWith('x') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const lineOf = node => source.getLineAndCharacterOfPosition(node.getStart()).line + 1;
  const visit = node => {
    if (isFunction(node) && node.body) {
      const name = functionName(node);
      const value = complexity(node);
      if (value > MAX_COMPLEXITY) issues.push({file: relative, line: lineOf(node), rule: 'TS-COMPLEXITY', message: `${name} 复杂度 ${value}，超过 ${MAX_COMPLEXITY}`});
      const lines = source.getLineAndCharacterOfPosition(node.end).line - source.getLineAndCharacterOfPosition(node.getStart()).line + 1;
      if (lines > MAX_FUNCTION_LINES) issues.push({file: relative, line: lineOf(node), rule: 'TS-LENGTH', message: `${name} 有 ${lines} 行，超过 ${MAX_FUNCTION_LINES}`});
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
  for (const statement of source.statements) {
    const exported = statement.modifiers?.some(item => item.kind === ts.SyntaxKind.ExportKeyword);
    if (!exported || statement.modifiers?.some(item => item.kind === ts.SyntaxKind.DefaultKeyword)) continue;
    const names = ts.isVariableStatement(statement)
      ? statement.declarationList.declarations.map(item => item.name.getText())
      : statement.name ? [statement.name.getText()] : [];
    for (const name of names) exportsByFile.push({file: relative, line: lineOf(statement), name});
  }
}
// 粗略但够用：别的文件（含前端测试）里完全没出现这个名字，才算没人用。
const words = new Map();
const addWords = (file, text) => {
  for (const word of new Set(text.match(/[A-Za-z_$][\w$]*/g) || [])) {
    if (!words.has(word)) words.set(word, new Set());
    words.get(word).add(file);
  }
};
for (const [file, text] of sources) addWords(file, text);
for (const entry of readdirSync(path.join(web, 'tests'), {withFileTypes: true, recursive: true})) {
  if (entry.isFile() && /\.(mjs|ts|tsx)$/.test(entry.name)) {
    const target = path.join(entry.parentPath, entry.name);
    addWords(path.relative(web, target), readFileSync(target, 'utf8'));
  }
}
for (const item of exportsByFile) {
  const users = words.get(item.name) || new Set();
  if ([...users].every(file => file === item.file)) issues.push({file: item.file, line: item.line, rule: 'TS-UNUSED-EXPORT', message: `导出的 ${item.name} 没有其他文件使用`});
}
process.stdout.write(JSON.stringify(issues));
