$(document).ready(function () {
    officialDocument.OfficialDocuments.List();
    $(document).off('click', '#btnOfficialDocumentSearch').on('click', '#btnOfficialDocumentSearch', function () {
        officialDocument.OfficialDocuments.List();
    });
});