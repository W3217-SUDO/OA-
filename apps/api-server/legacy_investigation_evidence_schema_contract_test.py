"""Regression guard for the legacy investigation evidence projections."""

import unittest

from app.database import Base
from app.models import (
    LegacyInvestigationClueEvidence,
    LegacyInvestigationClueEvidenceFile,
    LegacyInvestigationClueFile,
)


class LegacyInvestigationEvidenceSchemaContractTest(unittest.TestCase):
    def test_all_legacy_evidence_tables_and_columns_are_projected(self):
        self.assertIn("Legal_Investigation_Clue_Evidence", Base.metadata.tables)
        self.assertIn("Legal_Investigation_Clue_Evidence_File", Base.metadata.tables)
        self.assertIn("Legal_Investigation_Clue_File", Base.metadata.tables)
        self.assertEqual(len(LegacyInvestigationClueEvidence.__table__.columns), 24)
        self.assertEqual(len(LegacyInvestigationClueEvidenceFile.__table__.columns), 15)
        self.assertEqual(len(LegacyInvestigationClueFile.__table__.columns), 14)

    def test_guid_soft_links_and_legacy_lengths_are_preserved(self):
        evidence = LegacyInvestigationClueEvidence.__table__.c
        evidence_file = LegacyInvestigationClueEvidenceFile.__table__.c
        clue_file = LegacyInvestigationClueFile.__table__.c
        self.assertTrue(evidence.EvidenceId.primary_key)
        self.assertEqual(evidence.ClueGuid.type.length, 50)
        self.assertEqual(evidence.NotaryOrganization.type.length, 200)
        self.assertEqual(evidence.EvidenceAddress.type.length, 1000)
        self.assertEqual(evidence.Remark.type.length, 2000)
        self.assertTrue(evidence_file.FileId.primary_key)
        self.assertEqual(evidence_file.EvidenceGuid.type.length, 50)
        self.assertEqual(evidence_file.FullPath.type.length, 500)
        self.assertTrue(clue_file.FileId.primary_key)
        self.assertEqual(clue_file.ClueGuid.type.length, 50)
        self.assertEqual(clue_file.FullPath.type.length, 500)


if __name__ == "__main__":
    unittest.main()
