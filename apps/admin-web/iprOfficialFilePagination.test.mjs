import { readFileSync } from "node:fs";

const source = readFileSync(new URL("./src/IprOfficialFilePage.tsx", import.meta.url), "utf8");
for (const marker of [
  "[page,setPage]=useState(1)",
  "page:nextPage,page_size:20",
  "current:page,pageSize:20",
  "onChange:(next)=>{setPage(next);void load(next)}",
]) {
  if (!source.includes(marker)) throw new Error(`missing official file pagination marker: ${marker}`);
}
console.log("ipr official file pagination: PASS");
