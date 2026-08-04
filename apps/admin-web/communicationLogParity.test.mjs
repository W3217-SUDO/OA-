import test from "node:test"
import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"

const page = await readFile(new URL("./src/CommunicationLogPage.tsx", import.meta.url), "utf8")
const style = await readFile(new URL("./src/communication-log.css", import.meta.url), "utf8")

test("communication log supports attachment upload, download and delete", () => {
  assert.match(page, /communication-attachments/)
  assert.match(page, /Upload showUploadList=\{false\}/)
  assert.match(page, /支持任意普通文件，单个不超过 20MB；如需上传文件夹，请先压缩为 ZIP。/)
  assert.match(page, /api\.post\(`\/communications\/\$\{communicationId\}\/attachments`/)
  assert.match(page, /api\.delete\(`\/communications\/\$\{editing\.id\}\/attachments\/\$\{attachment\.id\}`/)
  assert.match(page, /downloadAttachment\(attachment\)/)
})

test("communication log exposes a view action and separates customer id from name", () => {
  assert.match(page, /<Button type="link" onClick=\{\(\)=>startView\(row\)\}>查看<\/Button>/)
  assert.match(page, /title:'客户ID'[\s\S]*?width:160/)
  assert.match(page, /title:'客户名称'[\s\S]*?width:260/)
  assert.match(style, /\.communication-panel \.communication-customer-id,\s*\.communication-panel \.communication-customer-name/)
  assert.match(style, /\.communication-panel \.communication-customer-id\{justify-content:center;font-variant-numeric:tabular-nums\}/)
  assert.match(style, /\.communication-panel \.communication-customer-name\{justify-content:flex-start\}/)
})
