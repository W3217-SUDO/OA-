from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
CASE_PAGE = ROOT / "apps" / "admin-web" / "src" / "CaseCenterPage.tsx"
API_MAIN = ROOT / "apps" / "api-server" / "app" / "main.py"


class CaseClueInlineWorkspaceRow32Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.page = CASE_PAGE.read_text(encoding="utf-8")
        cls.api = API_MAIN.read_text(encoding="utf-8")

    def test_case_clue_link_stays_in_case_and_loads_workspace(self) -> None:
        start = self.page.index("const openRelatedClue = async")
        end = self.page.index("const selectedCaseClueEvidence", start)
        handler = self.page[start:end]
        self.assertIn("/investigations/clues/${id}/workspace", handler)
        self.assertIn("setViewingCaseClue(data)", handler)
        self.assertNotIn("onNavigate", handler)
        self.assertNotIn("rememberInvestigationDetailTarget", handler)

    def test_inline_workspace_matches_legacy_information_and_edit_fields(self) -> None:
        self.assertIn('data-testid="case-clue-context-panel"', self.page)
        self.assertIn('aria-label="案件内线索信息"', self.page)
        self.assertIn("{renderCaseClueWorkspace()}", self.page)
        self.assertNotIn('width={980}\n        open={Boolean(viewingCaseClue)}', self.page)
        for label in ("线索信息", "线索文件", "取证信息", "取证机构", "公证书号", "取证时间", "发票号", "仓库", "库位", "状态", "文件"):
            self.assertIn(label, self.page)
        self.assertIn("rowSelection={{", self.page)
        self.assertIn("openCaseClueEvidenceEditor", self.page)
        self.assertIn("deleteCaseClueEvidence", self.page)

    def test_inline_workspace_is_rendered_inside_case_detail_workbench(self) -> None:
        workbench_start = self.page.index('<div className="case-detail-workbench">')
        inline_render = self.page.index("{renderCaseClueWorkspace()}", workbench_start)
        case_drawer_end = self.page.index("</Drawer>", workbench_start)
        self.assertLess(inline_render, case_drawer_end)

    def test_edit_uses_scoped_existing_evidence_endpoint(self) -> None:
        self.assertIn("api.put(`/investigations/evidence/${editingCaseClueEvidence.id}`", self.page)
        self.assertIn('@app.put(f"{settings.api_prefix}/investigations/evidence/{{evidence_id}}")', self.api)
        self.assertIn("await _require_record_owner_or_manager(item, identity, db)", self.api)
        self.assertIn('@app.get(f"{settings.api_prefix}/investigations/clues/{{clue_id}}/workspace")', self.api)
        self.assertIn("*(await _record_scope_conditions(identity, db))", self.api)


if __name__ == "__main__":
    unittest.main()
