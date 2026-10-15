$(document).ready(function () {
    investigation.Investigations.Investigation.Tasks.TaskList();

    $(document).off('click', '#btnInvestigationTaskSearch').on('click', '#btnInvestigationTaskSearch', function () {
        
        investigation.Investigations.Investigation.Tasks.TaskList();
    });

    $(document).off('click', '#btnInvestigationClueCreate').on('click', '#btnInvestigationClueCreate', function () {
        investigation.Investigations.Investigation.Clues.Clue.Create();
    });

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
    
});
