import { readFileSync } from "node:fs";

const source = readFileSync(new URL("./src/IprOfficialFilePage.tsx", import.meta.url), "utf8");
for (const marker of [
  'api.delete(`/ipr/official-files/${detail.id}`)',
  '删除官文？',
  'onConfirm={deleteOfficial}',
  '删除',
]) {
  if (!source.includes(marker)) throw new Error(`missing official-file deletion marker: ${marker}`);
}
console.log("ipr official-file deletion UI: PASS");
