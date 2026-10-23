$(document).ready(function () {
    //investigation.ResetSize();
    investigation.Investigations.Investigation.Files.Layout();
    investigation.Investigations.Investigation.Tasks.Layout();

    $(document).off('click', '#btnInvestigationEdit').on('click', '#btnInvestigationEdit', function () {
        investigation.Investigations.Investigation.Edit($("#Investigation_Basic_InvestigationNo").val());
    });

    $(document).off('click', '#btnInvestigationTaskDelete').on('click', '#btnInvestigationTaskDelete', function () {
        /*列表选中修改*/
        var taskNos = $.checkbox.vals("chkTaskId");
        if (taskNos.length == 0) {
            $.showModalMessageBox("请选择调查子任务.");
            return false;
        }

        investigation.Investigations.Investigation.Tasks.Task.Delete(taskNos);
    });

    $(document).off('click', '#btnInvestigationFileRefresh').on('click', '#btnInvestigationFileRefresh', function () {
        investigation.Investigations.Investigation.Files.List();
    });

    $(document).off('click', '#btnInvestigationFileUpload').on('click', '#btnInvestigationFileUpload', function () {
        investigation.Investigations.Investigation.Files.File.Open($("#Investigation_Basic_InvestigationGuid").val());
    });

    $(document).off('click', '#btnInvestigationFileDelete').on('click', '#btnInvestigationFileDelete', function () {

        var fileIds = $.checkbox.vals("chkFileId");
        if (fileIds.length == 0) {
            $.showModalMessageBox("请选择需要删除的文件.");
            return false;
        }
        investigation.Investigations.Investigation.Files.File.Delete(fileIds, investigation.Investigations.Investigation.Files.List);
    });
});