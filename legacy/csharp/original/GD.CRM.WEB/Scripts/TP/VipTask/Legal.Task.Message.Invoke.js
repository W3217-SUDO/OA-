$(document).ready(function () {
    task.Tasks.Task.Messages.List();
    //setInterval("task.Tasks.Task.Messages.List()", 10000 * 1);//10秒刷新1次
    $(document).off('click', '#btnMessageCreate').on('click', '#btnMessageCreate', function () {
        task.Tasks.Task.Messages.Message.CreateUpdate(this);
    });

});