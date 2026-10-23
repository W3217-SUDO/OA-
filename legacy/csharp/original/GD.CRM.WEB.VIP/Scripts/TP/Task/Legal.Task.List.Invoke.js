$(document).ready(function () {
    task.Tasks.List();
    
    if ($("#TaskId").val() != '')
    {
        task.Tasks.Task.View($("#TaskId").val());
    }

    $(document).off('click', '#btnTaskSearch').on('click', '#btnTaskSearch', function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        task.Tasks.List();
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
        task.Tasks.List();
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
        task.Tasks.List();
    });


    $(document).off('click', '#btnTaskMessageAllRead').on('click', '#btnTaskMessageAllRead', function () {

        var taskGuids = [];
        $("input[name='chkTaskId']:checked").each(
            function (i) { taskGuids[i] = $(this).attr('taskguid'); }
        );
        if (taskGuids.length < 1) {
            //$.showModalMessageBox("请选择任务.");
            $.showTips("请选择任务.", 0, 3);
            return false;
        }

        task.Tasks.Task.Messages.MarkRead(taskGuids);
    });


});