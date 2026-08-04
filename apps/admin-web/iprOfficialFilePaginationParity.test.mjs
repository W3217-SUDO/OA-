import assert from "node:assert/strict";
import fs from "node:fs";

const page = fs.readFileSync(new URL("./src/IprOfficialFilePage.tsx", import.meta.url), "utf8");

assert.match(
  page,
  /\[pageSize,setPageSize\]=useState\(15\)/,
  "Official-file pagination should keep the legacy default page size of 15.",
);

assert.match(
  page,
  /const load=async\(nextPage=page,nextPageSize=pageSize\)=>[\s\S]*?page_size:nextPageSize/,
  "Official-file requests should send the selected page size to the existing server endpoint.",
);

assert.match(
  page,
  /pagination=\{\{current:page,pageSize,total,[\s\S]*?showSizeChanger:true[\s\S]*?onChange:\(next,nextPageSize\)=>\{setPage\(next\);setPageSize\(nextPageSize\);void load\(next,nextPageSize\)\}\}\}/,
  "Official-file tables should expose server pagination and request the changed page size.",
);

console.log("ipr official file pagination parity: PASS");
