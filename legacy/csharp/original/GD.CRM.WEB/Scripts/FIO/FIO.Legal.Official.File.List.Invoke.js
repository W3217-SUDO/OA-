$(document).ready(function() {
    officialFile.List();
    officialFile.ResetSize();
    $(window).resize(function () {
        officialFile.ResetSize();
    })
    $(document).off('click', '#btnCaseFileInformDateChanged').on('click', '#btnCaseFileInformDateChanged', function () {
        if($("#CaseFile_InformDate").val() == '')
        {
            $.showTips('请输入收文日期.', 0, 3);
            return false;
        }
        var caseFileIds = $("#CaseFileIds").val();
        var informDate = $("#CaseFile_InformDate").val();
        c.Cases.Case.CaseFiles.CaseFile.InformDate.Change(caseFileIds, informDate, officialFile.List);
    });

    $(document).off('click', '#btnCaseFileSearch').on('click', '#btnCaseFileSearch', function () {
          officialFile.List();
    });
    
    $(document).off('click', '#btnInformDateChange').on('click', '#btnInformDateChange', function () {
        if ($.checkbox.vals('chkCaseId').length == 0) {
            $.showTips('请选择案件.', 0, 3);
            return false;
        }
        var caseFileIds = [];
        $("input[name=chkCaseId]:checked").each(
            function () {
                caseFileIds.push($(this).attr("caseFileId"));
            }
        );
        c.Cases.Case.CaseFiles.CaseFile.InformDate.Open(caseFileIds);
    });

    $(document).off('click', '#btnFileUpload').on('click', '#btnFileUpload', function () {
        officialFile.MetaFile.Open();
    });
});