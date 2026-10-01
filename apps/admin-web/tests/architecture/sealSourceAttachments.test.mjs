import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";
import React from "react";
import { act, create } from "react-test-renderer";
import ts from "typescript";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function loadHook(api, errors) {
  const source = fs.readFileSync(new URL("../../src/seal/useSealSourceAttachments.ts", import.meta.url), "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
  }).outputText;
  const module = { exports: {} };
  const dependencies = {
    react: React,
    antd: { message: { error: (value) => errors.push(value) } },
    "../api": { api },
    "../sealWorkflowPolicy": {
      sealFilePagination: { defaultPageSize: 2 },
      sealAttachmentListFailureMessage: (status) => `附件读取失败 ${status}`,
    },
  };
  vm.runInNewContext(output, {
    module, exports: module.exports,
    require: (name) => dependencies[name],
  }, { filename: "useSealSourceAttachments.ts" });
  return module.exports.useSealSourceAttachments;
}

test("source attachments load, deduplicate pages, select all and clear form selection", async () => {
  const requests = [];
  const errors = [];
  const pages = {
    1: { items: [{ id: 1 }, { id: 2 }], page: 1, page_size: 2, total: 3 },
    2: { items: [{ id: 2 }, { id: 3 }], page: 2, page_size: 2, total: 3 },
  };
  const api = { get: async (url, { params }) => {
    requests.push([url, params.record_id, params.page]);
    return { data: pages[params.page] };
  } };
  const values = { source_attachment_ids: [1, 99] };
  const createForm = {
    getFieldValue: (name) => values[name],
    setFieldValue: (name, value) => { values[name] = value; },
  };
  const useSealSourceAttachments = loadHook(api, errors);
  let current;
  let renderer;
  function Harness(props) {
    current = useSealSourceAttachments(props);
    return null;
  }
  try {
    await act(async () => {
      renderer = create(React.createElement(Harness, { createOpen: true, sourceRecordId: 12, createForm }));
    });
    assert.deepEqual(requests, [["/attachments", 12, 1]]);
    assert.deepEqual(Array.from(current.attachments, (item) => item.id), [1, 2]);
    assert.deepEqual([...values.source_attachment_ids], [1]);
    await act(async () => { await current.loadMore(); });
    assert.deepEqual(Array.from(current.attachments, (item) => item.id), [1, 2, 3]);
    assert.deepEqual(requests.at(-1), ["/attachments", 12, 2]);
    await act(async () => { await current.selectAll(); });
    assert.deepEqual([...values.source_attachment_ids], [1, 2, 3]);
    assert.equal(current.total, 3);
    await act(async () => { current.reset({ clearSelection: true }); });
    assert.equal(current.attachments.length, 0);
    assert.deepEqual([...values.source_attachment_ids], []);
    assert.deepEqual(errors, []);
  } finally {
    if (renderer) await act(async () => { renderer.unmount(); });
  }
});

test("source attachment request failure exposes the server detail without retaining stale files", async () => {
  const errors = [];
  const api = { get: async () => { throw { response: { status: 403, data: { detail: "无权查看来源文件" } } }; } };
  const createForm = { getFieldValue: () => [], setFieldValue: () => {} };
  const useSealSourceAttachments = loadHook(api, errors);
  let current;
  let renderer;
  function Harness(props) {
    current = useSealSourceAttachments(props);
    return null;
  }
  try {
    await act(async () => {
      renderer = create(React.createElement(Harness, { createOpen: true, sourceRecordId: 42, createForm }));
    });
    assert.deepEqual(errors, ["无权查看来源文件"]);
    assert.equal(current.attachments.length, 0);
    assert.equal(current.loading, false);
  } finally {
    if (renderer) await act(async () => { renderer.unmount(); });
  }
});
