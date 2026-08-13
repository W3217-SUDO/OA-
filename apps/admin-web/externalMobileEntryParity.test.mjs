import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const app = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");
const main = fs.readFileSync(new URL("./src/main.tsx", import.meta.url), "utf8");
const html = fs.readFileSync(new URL("./index.html", import.meta.url), "utf8");
const manifest = JSON.parse(fs.readFileSync(new URL("./public/manifest.webmanifest", import.meta.url), "utf8"));

test("external mobile entry is installable", () => {
  assert.match(app, /beforeinstallprompt/);
  assert.match(app, /安装到手机桌面/);
  assert.match(app, /DownloadOutlined/);
  assert.match(main, /serviceWorker\.register\('\/service-worker\.js'\)/);
  assert.match(html, /rel="manifest" href="\/manifest\.webmanifest"/);
  assert.equal(manifest.display, "standalone");
  assert.equal(manifest.start_url, "/");
});
