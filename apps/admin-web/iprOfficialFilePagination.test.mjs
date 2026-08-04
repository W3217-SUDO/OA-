import { readFileSync } from "node:fs";

const source = readFileSync(new URL("./src/IprOfficialFilePage.tsx", import.meta.url), "utf8");
for (const marker of [
  "[page,setPage]=useState(1)",
  "[pageSize,setPageSize]=useState(15)",
  "page:nextPage,page_size:nextPageSize",
  "current:page,pageSize,total",
  "showSizeChanger:true",
  "showQuickJumper:true",
  "onChange:(next,nextPageSize)=>{setPage(next);setPageSize(nextPageSize);void load(next,nextPageSize)}",
]) {
  if (!source.includes(marker)) throw new Error(`missing official file pagination marker: ${marker}`);
}
console.log("ipr official file pagination: PASS");
