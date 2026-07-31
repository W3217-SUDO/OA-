import re
from pathlib import Path


ROOT = Path(__file__).parents[1]
SOURCE = (ROOT / "apps/admin-web/src/CommunicationLogPage.tsx").read_text(encoding="utf-8")
STYLES = (ROOT / "apps/admin-web/src/communication-log.css").read_text(encoding="utf-8")


def require(fragment: str, description: str, *, source: str = SOURCE) -> None:
    if fragment not in source:
        raise AssertionError(f"Missing {description}: {fragment}")


require("Descriptions", "read-only detail component")
require("const [viewing,setViewing]=useState<Communication|null>(null)", "separate viewing state")
require("const startView=(row:Communication)=>setViewing(row)", "read-only view entry point")
require("const startEdit=(row:Communication)=>{", "separate edit entry point")
require(">查看</Button>", "view action")
require(">编辑</Button>", "edit action")
require('title="查看沟通记录"', "view modal title")
require("open={Boolean(viewing)}", "view modal open state")
require("footer={<Button onClick={()=>setViewing(null)}>关闭</Button>}", "view-only modal footer")
require("tableLayout=\"fixed\"", "fixed table layout")
require("scroll={{x:1445}}", "horizontal scroll width")
require("className=\"communication-customer-id\"", "customer ID layout class")
require("className=\"communication-customer-name\"", "customer name layout class")
require("onClick={()=>openCustomer(viewing.customer_record_id,viewing.customer_name)}", "customer navigation in read-only view")

view_modal_match = re.search(
    r'<Modal open=\{Boolean\(viewing\)\}.*?</Modal>',
    SOURCE,
    flags=re.DOTALL,
)
if not view_modal_match:
    raise AssertionError("Missing complete read-only communication modal")
view_modal = view_modal_match.group(0)
for forbidden in ("<Form", "<Input", "<Select", "<DatePicker", "onOk=", "保存", "编辑", "删除", "<Popconfirm"):
    if forbidden in view_modal:
        raise AssertionError(f"Read-only communication modal contains forbidden control: {forbidden}")

for title, minimum in (("客户ID", 160), ("客户名称", 260)):
    match = re.search(rf"title:'{title}'.*?width:(\d+)", SOURCE)
    if not match or int(match.group(1)) < minimum:
        raise AssertionError(f"{title} must keep a readable explicit width of at least {minimum}px")

for selector in (".communication-customer-id", ".communication-customer-name"):
    require(selector, f"{selector} style", source=STYLES)
for declaration in ("max-width:100%", "overflow:hidden", "text-overflow:ellipsis", "white-space:nowrap"):
    require(declaration, f"customer cell {declaration} guard", source=STYLES)

print("COMMUNICATION_LOG_VIEW_OK: fixed non-overlapping customer columns and a control-free read-only modal")
