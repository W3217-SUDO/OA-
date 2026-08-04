import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import { normalizeCustomerAttachmentItems } from "./src/customerUiBatchI16.mjs"

const pageSource = fs.readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8")
const helperSource = fs.readFileSync(new URL("./src/customerUiBatchI16.mjs", import.meta.url), "utf8")

test("old customer view license thumbnail evidence stays locked", () => {
  // Old system renders the license card with an image that opens the full file.
  // Areas/CRM/Views/Customer/Customer.cshtml:163-175 (#aimgLicense + #imgLicense)
  assert.match(helperSource, /is_license/)
  assert.match(pageSource, /营业执照/)
  assert.match(pageSource, /customerLicenseAttachment/)
  assert.match(pageSource, /查看营业执照/)
  assert.match(pageSource, /下载营业执照/)
  assert.match(pageSource, /上传营业执照/)
  assert.match(pageSource, /viewDocument\(customerLicenseAttachment\)/)
  assert.match(pageSource, /downloadDocument\(customerLicenseAttachment\)/)
})

test("customer attachment normalizer keeps the license flag from local and legacy payloads", () => {
  const local = normalizeCustomerAttachmentItems({ data: { items: [{ id: 5, original_name: "license.jpg", is_license: true }] } })
  assert.equal(local[0].id, 5)
  assert.equal(local[0].original_name, "license.jpg")
  assert.equal(local[0].is_license, true)
  const legacy = normalizeCustomerAttachmentItems({ Data: [{ CustomerFileId: 6, FileName: "old.jpg", IsLicense: true }] })
  assert.equal(legacy[0].id, 6)
  assert.equal(legacy[0].original_name, "old.jpg")
  assert.equal(legacy[0].is_license, true)
})

test("license card is rendered from the attachments collection", () => {
  assert.match(pageSource, /attachments\.find/)
  assert.match(pageSource, /item\.is_license === true/)
  assert.match(pageSource, /item\.IsLicense === true/)
})
