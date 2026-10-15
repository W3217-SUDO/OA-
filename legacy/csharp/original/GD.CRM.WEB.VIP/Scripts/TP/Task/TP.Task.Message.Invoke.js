$(document).ready(function () {
    task.Task.Messages.List();

    setInterval("task.Task.Messages.List()", 10000 * 1);//10秒刷新1次

});