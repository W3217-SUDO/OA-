$(document).ready(function () {
    investigation.Investigations.Investigation.Clues.ClueList();
    $(document).off('click', '#btnInvestigationClueSearch').on('click', '#btnInvestigationClueSearch', function () {
        investigation.Investigations.Investigation.Clues.ClueList();
    });
});