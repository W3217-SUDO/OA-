import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("top bar restores the legacy fullscreen workspace control", () => {
  assert.match(source, /FullscreenOutlined/, "the shell should import a recognizable fullscreen icon");
  assert.match(source, /document\.documentElement\.requestFullscreen\?\.\(\)/, "entering fullscreen should target the whole workspace");
  assert.match(source, /document\.exitFullscreen\?\.\(\)/, "the same control should leave fullscreen");
  assert.match(source, /document\.addEventListener\("fullscreenchange"/, "the icon state should follow browser fullscreen changes");
});
