$(document).ready(function () {
    officialDocument.OfficialDocuments.List();
    $(document).off('click', '#btnOfficialDocumentSearch').on('click', '#btnOfficialDocumentSearch', function () {
        officialDocument.OfficialDocuments.List();
    });
    $(document).off('click', '#btnOfficialDocumentRollback').on('click', '#btnOfficialDocumentRollback', function () {
        officialDocument.OfficialDocuments.OfficialDocument.Rollback();
    });

    $(document).off('click', '.aps-icon-shangjiantou').on('click', '.aps-icon-shangjiantou', function () {
        var sorting = $(this).parent().attr("data-field");
        if (sorting != null && sorting != '') {
            $(".aps-sort").each(function (i, e) {
                $(e).removeClass("aps-asc");
                $(e).removeClass("aps-desc");
            });

            $(this).parent().addClass("aps-asc");
            $("#SearchCondition_Sorting").val(sorting + " asc");
        }
        officialDocument.OfficialDocuments.List();
    });
    $(document).off('click', '.aps-icon-xiajiantou').on('click', '.aps-icon-xiajiantou', function () {
        var sorting = $(this).parent().attr("data-field");
        if (sorting != null && sorting != '') {
            $(".aps-sort").each(function (i, e) {
                $(e).removeClass("aps-asc");
                $(e).removeClass("aps-desc");
            });
            $(this).parent().addClass("aps-desc");
            $("#SearchCondition_Sorting").val(sorting + " desc");
        }
        officialDocument.OfficialDocuments.List();
    });
});