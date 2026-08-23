from pathlib import Path
import unittest


SOURCE = Path(__file__).with_name("app") / "main.py"


class SealPersonDisplayRow3Test(unittest.TestCase):
    def test_seal_projection_maps_owner_and_workflow_people_to_display_names(self):
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("async def _seal_record_dict")
        end = source.index("async def _validated_seal_relations", start)
        projection = source[start:end]

        self.assertIn("_record_person_usernames(record)", projection)
        self.assertIn("_user_display_map", projection)
        self.assertIn("_apply_record_person_displays", projection)

    def test_seal_list_preloads_people_for_all_rows(self):
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("async def list_seal_applications")
        end = source.index("async def package_download_seal_files", start)
        endpoint = source[start:end]

        self.assertIn("seal_usernames", endpoint)
        self.assertIn("users_by_username = await _user_display_map", endpoint)
        self.assertIn("await _seal_record_dict(", endpoint)
        self.assertIn("users_by_username", endpoint)
        self.assertIn("attachments_by_record", endpoint)
        self.assertIn("assets_by_id", endpoint)
        self.assertIn("context", endpoint)


if __name__ == "__main__":
    unittest.main()
