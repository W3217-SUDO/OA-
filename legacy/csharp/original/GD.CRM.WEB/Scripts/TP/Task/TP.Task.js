var caseInfo = {
    View: function (caseId, caseNo) {
        var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + caseNo;
        window.open(url);
    },
}

var task = {
    Init: function () {
       
    },
    ResetSize: function () {
        if ($("#divContextList").length > 0) {
            $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 18);
        }
    },

    Task: {
        View: function (taskId) {
            var url = AP_ROOT + AP_PAGE_ID + "/TP/Task/TaskDetail?taskId=" + taskId;
            window.open(url);
        },
        Finished : function()
        {
            var taskIds = new Array();
            taskIds.push($("#Task_TaskId").val());
            var data = {
                taskIds: taskIds,
            };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/Task/Finished", data, function (response) {
                if (response.IsSuccess) {
                    window.location.reload();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        Process: function () {
            var taskIds = new Array();

            taskIds.push($("#Task_TaskId").val());

            var data = {
                taskIds: taskIds,
            };

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/Task/Process", data, function (response) {
                if (response.IsSuccess) {
                    window.location.reload();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        Rejected: function () {
            var taskIds = new Array();

            taskIds.push($("#Task_TaskId").val());

            var data = {
                taskIds: taskIds,
            };

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/Task/Rejected", data, function (response) {
                if (response.IsSuccess) {
                    window.location.reload();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        Checked: function () {
            var taskIds = new Array();

            taskIds.push($("#Task_TaskId").val());

            var data = {
                taskIds: taskIds,
            };

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/Task/Checked", data, function (response) {
                if (response.IsSuccess) {
                    window.location.reload();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        ReOpen: function () {
            var taskIds = new Array();

            taskIds.push($("#Task_TaskId").val());

            var data = {
                taskIds: taskIds,
            };

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/Task/ReOpen", data, function (response) {
                if (response.IsSuccess) {
                    window.location.reload();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        Delete : function () {
            var taskIds = new Array();

            taskIds.push($("#Task_TaskId").val());

            var data = {
                taskIds: taskIds,
            };

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/Task/TaskDelete", data, function (response) {
                if (response.IsSuccess) {
                    window.location.reload();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        List: {
            BindMenu: function () {

                $('#customergridSection').contextMenu('customerMenu', {
                    menuStyle: {
                        width: '152px'
                    },

                    itemStyle: {
                        width: '150px'
                    },

                    bindings: {
                        'view': function (t, e) {
                            var customerId = $(e).find("span").text();
                            if (customerId == '') {
                                $.showModalMessageBox("请选择查看的客户.");
                                return false;
                            }

                            customer.Customer.View(customerId);
                        },
                        'edit': function (t, e) {
                            var customerId = $(e).find("span").text();
                            if (customerId == '') {
                                $.showModalMessageBox("请选择编辑的客户.");
                                return false;
                            }

                            customer.Customer.Edit(customerId);
 
                            return true;
                        },
                        'createcontract': function (t, e) {
                            var customerId = $(e).find("span").text();
                            if (customerId == '') {
                                $.showModalMessageBox("请选择客户.");
                                return false;
                            }

                            window.open( AP_ROOT + AP_PAGE_ID + "/FCM/ContractDraft/Draft?customerId=" + customerId);

                            return true;
                        },

                        'assigning': function (t, e) {
                            var customerId = $(e).find("span").text();
                            if (customerId == '') {
                                $.showModalMessageBox("请选择需要分配的客户.");
                                return false;
                            }

                            customer.Customer.Assignment.Open(customerId);

                            return true;
                        },

                        'sharing': function (t, e) {
                            var customerId = $(e).find("span").text();
                            if (customerId == '') {
                                $.showModalMessageBox("请选择需要分享的客户.");
                                return false;
                            }

                            customer.Customer.Share.Open(customerId);

                            return true;
                        },

                        'delete': function (t, e) {
                            var customerId = $(e).find("span").text();
                            if (customerId == '') {
                                $.showModalMessageBox("请选择需要删除的客户.");
                                return false;
                            }

                            customer.Customer.Delete(customerId);

                            return true;
                        },

                        'restore': function (t, e) {
                            var customerId = $(e).find("span").text();
                            if (customerId == '') {
                                $.showModalMessageBox("请选择需要恢复的客户.");
                                return false;
                            }

                            customer.Customer.Restore(customerId);

                            return true;
                        },

                        'inopen': function (t, e) {
                            var customerId = $(e).find("span").text();
                            if (customerId == '') {
                                $.showModalMessageBox("请选择需要进入公海的客户.");
                                return false;
                            }

                            customer.Customer.InOpen(customerId);

                            return true;
                        },

                        'inclose': function (t, e) {
                            var customerId = $(e).find("span").text();
                            if (customerId == '') {
                                $.showModalMessageBox("请选择需要进入拾回的客户.");
                                return false;
                            }

                            customer.Customer.InClose(customerId);

                            return true;
                        },

                    },
                    onContextMenu: function (e) {
                        return true;
                    },
                    onShowMenu: function (e, menu) {
                        if ($(e.target).parents("tr").find(".customerId").hasClass("customerId")) {
                            var customerId = $(e.target).parents("tr").find(".customerId").text();
                            $('#view', menu).append("<span style='display:none'>" + customerId + "</span>");
                            $('#edit', menu).append("<span style='display:none'>" + customerId + "</span>");
                            $('#createcontract', menu).append("<span style='display:none'>" + customerId + "</span>");
                            $('#assigning', menu).append("<span style='display:none'>" + customerId + "</span>");
                            $('#sharing', menu).append("<span style='display:none'>" + customerId + "</span>");
                            $('#delete', menu).append("<span style='display:none'>" + customerId + "</span>");
                            $('#restore', menu).append("<span style='display:none'>" + customerId + "</span>");
                            $('#inopen', menu).append("<span style='display:none'>" + customerId + "</span>");
                            $('#inclose', menu).append("<span style='display:none'>" + customerId + "</span>");

                         } else {
                            $('#view,#edit,#createcontract,#assigning,#sharing,#delete,#restore,#inopen,#inclose', menu).remove();
                        }
                        return menu;
                    }
                });
            },
            SelectedStatus: function (e,status) {
                $("#SearchCondition_TaskStatus").val(status);

                $.each($(e).parent().parent().find("li"), function (i, li) {
                    $(li).removeClass("active")
                }),

                $(e).parent().addClass("active")

                task.Task.List.TaskList();
            },
            TaskList: function ()
            {
                $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/Task/TaskSearchList", function (response) {
                    if (response.IsSuccess) {
                        $("tbody", "#tblTaskList").clearRow();
                        if (response.Data.TotalItemCount > 0) {

                            $(".info_inall.layoutfix").show();
                            $.each(response.Data.TaskList, function (i, t) {

                                $("tbody", "#tblTaskList").addRow(
                                       "<span class='taskId' style='display:none'>" + t.TaskId + "</span><a style='color: #039' href='javascript:void(0);'  onclick='javascript:task.Task.View(" + t.TaskId + ");' >" + t.TaskNo + "</a>",
                                       "<span class='caseId' style='display:none'>" + t.CaseId + "</span><a style='color: #039' href='javascript:void(0);'  onclick='javascript:caseInfo.View(" + t.CaseId + ',\"' + t.CaseNo + "\");' >" + t.CaseNo + "</a>",
                                        t.CustomerName,
                                        t.TaskStatusName,
                                        t.TaskPriorityName,
                                        t.TaskTitle,
                                        t.TaskBeginTime == null ? '' : getDate(convertJsonDateToJSDate(t.TaskBeginTime)),
                                        t.TaskEndTime == null ? '' : getDate(convertJsonDateToJSDate(t.TaskEndTime)),
                                        t.TaskRemainingDays == null ?  '' : t.TaskRemainingDays + "/天",
                                        t.InitiatorName,
                                        t.OfficerName                                      
                                    );
                            });

                            $("tfoot", "#tblTaskList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.task").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: task.Task.List.TaskList,
                                callBackArgs: null
                            });

                        } else {

                            $("tfoot", "#tblTaskList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                    }
                });
            },
        },

        Messages: {

            MarkRead: function () {
                var data = {
                    taskId: $("#Task_TaskId").val(),
                };

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/TaskMessage/TaskMeesageMarkRead", data, function (response) {

                },false);
            },

             List: function ()
             {
                 var data = {
                     taskId: $("#Task_TaskId").val(),
                 };
                
                 $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/TaskMessage/TaskMeesages", data, function (response) {
                     if (response.IsSuccess) {
                         $("#taskMessags").empty();
                         $("#taskMessags").html(response.Data);
                         task.Task.Messages.MarkRead();

                     } else {
                         $.showModalMessageBox(response.Message);
                     }
                 },false);
             },

             Message: {
                 CreateUpdate: function () {
                     var data = {
                         taskId: $("#Task_TaskId").val(),
                         content: $("#message_content").val(),
                     };

                     $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/TaskMessage/TaskMessageCreate", data, function (response) {
                         if (response.IsSuccess) {
                             $("#message_content").val('');
                             debugger
                             task.Task.Messages.List();
                         } else {
                             $.showModalMessageBox(response.Message);
                         }
                     });
                 },
             }
         }
    },
};

$(document).ready(function () {

    //键盘enter事件
    document.onkeypress = function () {
        if (event.keyCode == 13) {
            task.Task.List.TaskList();
        }
    }

    $(document).click(function () {
     });

    $(window).resize(function () {
        task.ResetSize();
    });

    $(document).off('click', '#btnTaskSearch').on('click', '#btnTaskSearch', function () {
        task.Task.List.TaskList();
    });

    $(document).off('click', '#btnMessageCreate').on('click', '#btnMessageCreate', function () {
        task.Task.Messages.Message.CreateUpdate();
    });

});