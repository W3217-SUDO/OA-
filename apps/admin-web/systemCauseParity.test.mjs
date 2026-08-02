import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"

const source = fs.readFileSync(
  new URL("./src/SystemCenterPage.tsx", import.meta.url),
  "utf8",
)
const queryStart = source.indexOf('<div className="system-query">')
const queryEnd = source.indexOf("<Table", queryStart)
const queryBlock = source.slice(queryStart, queryEnd)

test("cause query uses the legacy parent-cause label", () => {
  assert.notEqual(queryStart, -1)
  assert.ok(queryEnd > queryStart)
  assert.match(
    queryBlock,
    /<span>\{category === "cause" \? "上级案由Id" : "上级代码"\}<\/span>/,
  )
  assert.doesNotMatch(queryBlock, /<span>上级代码<\/span>/)
})
