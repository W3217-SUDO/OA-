import assert from 'node:assert/strict';
import test from 'node:test';
import {build} from 'esbuild';
import Module, {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

async function load(api) {
  const result = await build({entryPoints:[fileURLToPath(new URL('../src/seal/sealRequests.ts', import.meta.url))], bundle:true, write:false, platform:'node', format:'cjs', packages:'external', plugins:[{name:'isolated-seal-api', setup(builder) {
    builder.onResolve({filter:/\/api$/}, () => ({path:'api', namespace:'test'}));
    builder.onLoad({filter:/.*/, namespace:'test'}, () => ({contents:'export const api=globalThis.__sealRequestApi;'}));
  }}]});
  const module = new Module(fileURLToPath(import.meta.url));
  module.require = createRequire(import.meta.url);
  globalThis.__sealRequestApi = api;
  try { module._compile(result.outputFiles[0].text, fileURLToPath(import.meta.url)); return module.exports; }
  finally { delete globalThis.__sealRequestApi; }
}

test('用印下载保留二进制文件，拒绝损坏或非文件的 JSON 响应', async () => {
  let response = {data:new Blob(['ZIP'], {type:'application/zip'})};
  const {postSealBlob} = await load({post:async () => response});
  assert.equal(await postSealBlob('/test', {}, {responseType:'blob'}), response);
  response = {data:new Blob(['{invalid'], {type:'application/json'})};
  await assert.rejects(postSealBlob('/test', {}, {responseType:'blob'}), error => error.message === '服务器返回的下载信息格式无效' && error.cause instanceof SyntaxError);
  response = {data:new Blob(['{"IsSuccess":false,"Message":"附件打包失败"}'], {type:'application/json'})};
  await assert.rejects(postSealBlob('/test', {}, {responseType:'blob'}), /附件打包失败/);
  response = {data:new Blob(['{"IsSuccess":true}'], {type:'application/json'})};
  await assert.rejects(postSealBlob('/test', {}, {responseType:'blob'}), /没有返回可下载的文件/);
});

test('用印业务失败保留原响应，成功结果与调用参数保持原样', async () => {
  const calls = [];
  let response = {data:{id:1}};
  const request = async (...args) => { calls.push(args); return response; };
  const {postSeal, patchSeal, deleteSeal} = await load({post:request, patch:request, delete:request});
  assert.equal(await postSeal('/post', {id:1}), response);
  assert.equal(await patchSeal('/patch', {id:1}), response);
  assert.equal(await deleteSeal('/delete'), response);
  assert.deepEqual(calls, [['/post',{id:1}],['/patch',{id:1}],['/delete']]);
  response = {data:{IsSuccess:false, Message:'保存失败', detail:'原始业务错误'}};
  await assert.rejects(postSeal('/post'), error => error.message === '原始业务错误' && error.response.data === response.data);
});
