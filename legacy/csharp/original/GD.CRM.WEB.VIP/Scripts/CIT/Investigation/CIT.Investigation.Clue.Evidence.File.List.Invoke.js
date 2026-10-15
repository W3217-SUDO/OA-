$(document).ready(function () {
    investigation.Investigations.Investigation.Evidences.Evidence.Files.EvidenceFileList();
    $(document).off('click', '#btnInvestigationClueEvidenceSearch').on('click', '#btnInvestigationClueEvidenceSearch', function () {
        investigation.Investigations.Investigation.Evidences.Evidence.Files.EvidenceFileList();
    });
});