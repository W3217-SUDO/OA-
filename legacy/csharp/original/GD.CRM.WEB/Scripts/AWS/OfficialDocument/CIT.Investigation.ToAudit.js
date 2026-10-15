$(document).ready(function () {
    $("#Investigation_Basic_Auditor").chosen({
        width: '100%',
        disable_search: false,
        search_contains: true
    });
})

$(document).off('click', '#btnInvestigationToAudit').on('click', '#btnInvestigationToAudit', function () {
    investigation.Investigations.Investigation.ToAudit();
});