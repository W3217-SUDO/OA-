function AssociateAvailableUserForTask(div, ctlid, ctlname, func) {

    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;
    this.CallBackFunc = func;

    this.UserName = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") {
            return false;
        }
        var curobj = new Object();
        curobj.keyword = name;

        var data = { userName: name };
        $.ajaxPostMessage(AP_ROOT + AP_PAGE_ID + "/Account/UserCenter/AvailableUsers", data, function (response) {
            if (response.IsSuccess) {
                if (response.Data.length > 0) {
                    var html = '';
                    $.each(response.Data, function (i, c) {
                        html += '<a href="javascript:void(0)" userId=' + c.Item1 + '>' + c.Item2 + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);

                    $(div).find(".i_common_list a").css({
                        "height": $(ctlname).outerHeight(),
                        "line-height": ($(ctlname).outerHeight() - 4) + "px"
                    });

                    $(div).find(".i_common_list a").click(function () {
                        
                        if (func != null) {
                            func($(this).attr("userId"), $(this).text());
                            $(ctlname).val('');
                            $(ctlname).focus();
                        }
                        else {

                            $(ctlid).val($(this).attr("userId"));
                            $(ctlname).val($(this).text());
                        }
                        $(div).hide();
                    });

                    $(div).css({
                        "position": "absolute",
                        "left": $(ctlname).position().left + 2,
                        "top": $(ctlname).position().top + 26,
                        "z-index": 9999
                    }).show();
                }
                else {
                    var html = "";
                    html += '<a href="javascript:void(0)" >没有查询到符合条件的记录.</a>';
                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").css({
                        "height": $(ctlname).outerHeight(),
                        "line-height": ($(ctlname).outerHeight() - 4) + "px"
                    });
                }
            }
            else {

            }
        }, false);

    }

    $(ctlname).bind('keyup', { obj: this }, function (event) {

        if (event.keyCode == 38) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).prev().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).prev().addClass("hover");
                        $(hover).prev().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 40) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).next().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).next().addClass("hover");
                        $(hover).next().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 13) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    $(hover).click();
                }
            }
        } else {
            clearTimeout(event.data.obj.Event);
            event.data.obj.Event = setTimeout(function () { event.data.obj.UserName(event.data.obj); }, 500);
        }
    });

    $(ctlname).bind('blur', { obj: this }, function (event) {
        if ($(this).val() == "" || ($(this).val() == $(this).attr("mod-notice-tip"))) {
            event.data.obj.GlobalName = "";
            $(ctlid).val("");
        }
        if ($(ctlid).val() == "") {
            if ($(this).attr("mod-notice-tip")) {
                $(this).val($(this).attr("mod-notice-tip"));
            } else {
                $(this).val("");
            }
        }
    });

    return this;
}

function AssociateAvailableUserWithOutMeForTask(div, ctlid, ctlname, func) {

    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;
    this.CallBackFunc = func;

    this.UserName = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") {
            return false;
        }
        var curobj = new Object();
        curobj.keyword = name;

        var data = { userName: name };
        $.ajaxPostMessage(AP_ROOT + AP_PAGE_ID + "/Account/UserCenter/AvailableUsersWithOutMe", data, function (response) {
            if (response.IsSuccess) {
                
                if (response.Data.length > 0) {
                    var html = '';
                    $.each(response.Data, function (i, c) {
                        html += '<a href="javascript:void(0)" userId=' + c.Item1 + '>' + c.Item2 + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);

                    $(div).find(".i_common_list a").css({
                        "height": $(ctlname).outerHeight(),
                        "line-height": ($(ctlname).outerHeight() - 4) + "px"
                    });

                    $(div).find(".i_common_list a").click(function () {
                        if (func != null) {
                            func($(this).attr("userId"), $(this).text());
                            $(ctlname).val('');
                            $(ctlname).focus();
                        }
                        else {

                            $(ctlid).val($(this).attr("userId"));
                            $(ctlname).val($(this).text());
                        }
                        $(div).hide();
                    });

                    $(div).css({
                        "position": "absolute",
                        "left": $(ctlname).position().left + 2,
                        "top": $(ctlname).position().top + 26,
                        "z-index": 9999
                    }).show();
                }
                else {
                    var html = "";
                    html += '<a href="javascript:void(0)" >没有查询到符合条件的记录.</a>';
                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").css({
                        "height": $(ctlname).outerHeight(),
                        "line-height": ($(ctlname).outerHeight() - 4) + "px"
                    });
                }
            }
            else {

            }
        }, false);

    }

    $(ctlname).bind('keyup', { obj: this }, function (event) {

        if (event.keyCode == 38) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).prev().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).prev().addClass("hover");
                        $(hover).prev().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 40) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).next().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).next().addClass("hover");
                        $(hover).next().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 13) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    $(hover).click();
                }
            }
        } else {
            clearTimeout(event.data.obj.Event);
            event.data.obj.Event = setTimeout(function () { event.data.obj.UserName(event.data.obj); }, 500);
        }
    });

    $(ctlname).bind('blur', { obj: this }, function (event) {
        if ($(this).val() == "" || ($(this).val() == $(this).attr("mod-notice-tip"))) {
            event.data.obj.GlobalName = "";
            $(ctlid).val("");
        }
        if ($(ctlid).val() == "") {
            if ($(this).attr("mod-notice-tip")) {
                $(this).val($(this).attr("mod-notice-tip"));
            } else {
                $(this).val("");
            }
        }
    });

    return this;
}

var task = {
    Init: function () {
       
    },
    ResetSize: function () {
        if ($("#divContextList").length > 0) {
            $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 18);
        }
    },
    Tasks :
    {
        Task: {
            Open: function (caseNos) {
                var data = { caseNos: caseNos.join(',') };
                var url = AP_ROOT + AP_PAGE_ID + "/TP/Task/TaskCreate";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(".slide-panel-container").empty();
                    $(".slide-panel-container").append(result);
                    $(".slide-panel-container").addClass("show-panel");
                });
            },
            Close: function () {
                $(".slide-panel-container").empty();
                $(".slide-panel-container").removeClass("show-panel");
                return false;
            },
            CreateUpdate: function () {

                var casenos = [];

                $("a[name='casename']").each(function () {
                    casenos.push($(this).attr("caseno"));
                });

                if (casenos.length == 0) {
                    $.showModalMessageBox("请选择案件.");
                    return false;
                }

                if ($("#Task_TaskTitle").val().trim() == '') {
                    $.showModalMessageBox("请输入任务标题");
                    return false;
                }
                //if ($("#Task_TaskSubTitle").val().trim() == '') {
                //    $.showModalMessageBox("请输入任务副标题");
                //    return false;
                //}
                if ($("#Task.TaskBeginTime").val() == '') {
                    $.showModalMessageBox("请输入任务结束时间");
                    return false;
                }
                if ($("#Task_TaskEndTime").val() == '') {
                    $.showModalMessageBox("请输入任务结束时间");
                    return false;
                }

                var officers = [];
                var officernames = [];

                officers.push($("#Task_Officer").val());
                officernames.push($("#Task_Officer").find("option:selected").text());
 
                if (officers.length == 0) {
                    $.showModalMessageBox("请输入负责人.");
                    return false;
                }

                var associates = [];
                var associatenames = [];

                $("a[name='associatename']").each(function () {
                    associates.push($(this).attr("username"));
                    associatenames.push($(this).attr("userchname"));
                });

                var data = {};
                data["CaseNos"] = casenos.join(",");
 
                data["Task.TaskPriority"] = $('input:radio[name="Task_Priority_Level"]:checked').val();
                data["Task.TaskTitle"] = $("#Task_TaskTitle").val();
                data["Task.TaskSubTitle"] = $("#Task_TaskSubTitle").val();
                data["Task.Officer"] = officers;
                data["Task.Associates"] = associates.join(",");
                data["Task.AssociateNames"] = associatenames.join(",");
                data["Task.TaskBeginTime"] = $("#Task_TaskBeginTime").val();
                data["Task.TaskEndTime"] = $("#Task_TaskEndTime").val();
                data["Task.TaskContent"] = $("#Task_Content").val();
                data["Task.TaskGuid"] = $("#Task_TaskGuid").val();
                data["Task.NodeGuid"] = $("#Task_NodeGuid").val();
                data["Task.MessageGuid"] = $("#Task_MessageGuid").val();
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/Task/CreateUpdate", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("新建任务成功.");
                        task.Tasks.Task.Close();

                        if (caseInfo.CaseTask)
                        {
                            caseInfo.CaseTask.List();
                        }
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },
            View: function (taskId) {

                var data = { taskId: taskId };

                var url = AP_ROOT + AP_PAGE_ID + "/TP/Task/TaskDetail";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(".slide-panel-container").empty();
                    $(".slide-panel-container").append(result);
                    $(".slide-panel-container").addClass("show-panel");
                });

                //var url = AP_ROOT + AP_PAGE_ID + "/TP/Task/TaskDetail?taskId=" + taskId;
                //window.open(url);
            },

            ViewTask: function (e, taskId) {

                $(e).parents("tr").css("background", "yellow");
                $(e).parents("tr").toggleClass("selected_tr");

                var data = { taskId: taskId };

                var url = AP_ROOT + AP_PAGE_ID + "/TP/Task/TaskDetail";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(".slide-panel-container").empty();
                    $(".slide-panel-container").append(result);
                    $(".slide-panel-container").addClass("show-panel");
                });

                //var url = AP_ROOT + AP_PAGE_ID + "/TP/Task/TaskDetail?taskId=" + taskId;
                //window.open(url);
            },
            Finished: function () {
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
            Delete: function () {
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

            Officer: {
                AddIn: function (username, userchname) {

                    var existsUser = false;

                    if ($("a[name='officername']").length > 0)
                    {
                        return false;
                    }

                    $("a[name='officername']").each(function () {
                        if ($(this).attr("username") == username) {
                            existsUser = true;
                            return true;
                        }
                    });

                    //重复

                    if (existsUser) return true;

                    var $tag = $("<span class='tag label label-info'>"
                                    + "<a name='officername' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                    + " username='" + username + "'"
                                    + " userchname='" + userchname + "'"
                                    + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);'   data-original-title=" + userchname + " '>" + userchname + "</a>"
                                    + "<span class='userremove' data-role='remove'></span>"
                                + "</span>");

                    $("#Task_Officer_Input").before($tag);
                    $tag.after(' ');

                },
                Remove: function (e) {
                    $(e).parent().remove();
                },
            },
            Associates: {
                AddIn: function (username, userchname) {

                    var existsUser = false;

                    $("a[name='associatename']").each(function () {
                        if ($(this).attr("username") == username) {
                            existsUser = true;
                            return true;
                        }
                    });

                    //重复

                    if (existsUser) return true;

                    var $tag = $("<span class='tag label label-info'>"
                                    + "<a name='associatename' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                    + " username='" + username + "'"
                                    + " userchname='" + userchname + "'"
                                    + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);'   data-original-title=" + userchname + " '>" + userchname + "</a>"
                                    + "<span class='userremove' data-role='remove'></span>"
                                + "</span>");

                    $("#Task_Associates_Input").before($tag);
                    $tag.after(' ');

                },
                Remove: function (e) {
                    $(e).parent().remove();
                },
            },
            Messages: {
                MarkRead: function () {
                    var data = {
                        taskGuid: $("#Task_TaskGuid").val(),
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/TaskMessage/TaskMeesageMarkRead", data, function (response) {
                        messager.polling(false);
                    }, false);
                },
                List: function () {
                    var data = {
                        taskGuid: $("#Task_TaskGuid").val(),
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/TaskMessage/TaskMeesages", data, function (response) {
                        if (response.IsSuccess) {
                            $("#taskMessags").empty();
                            $("#taskMessags").html(response.Data);
                            //task.Tasks.Task.Messages.MarkRead();

                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    }, false);
                },
                Message: {

                    MarkRead: function (messageGuid) {
                        
                        var data = {
                            taskGuid: $("#Task_TaskGuid").val(),
                            messageGuid: messageGuid
                        };

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/TaskMessage/TaskMeesageMarkRead", data, function (response) {
                            task.Tasks.Task.Messages.List();
                        }, false);
                    },

                    MarkUnRead: function (messageGuid) {
                        var data = {
                            taskGuid: $("#Task_TaskGuid").val(),
                            messageGuid: messageGuid
                        };

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/TaskMessage/TaskMeesageMarkUnRead", data, function (response) {
                            task.Tasks.Task.Messages.List();
                        }, false);
                    },

                    CreateUpdate: function (e) {
                        $(e).attr("disabled", "disabled");
                        var data = {
                            taskGuid: $("#Task_TaskGuid").val(),
                            nodeGuid: $("#Task_NodeGuid").val(),
                            messageGuid: $("#Task_MessageGuid").val(),
                            content: $("#message_content").val(),
                        };
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/TaskMessage/TaskMessageCreate", data, function (response) {
                            if (response.IsSuccess) {
                                $("#message_content").val('');
                                $("#attachments").empty();
                                $("#Task_MessageGuid").val(response.Data.MessageGuid);
                                task.Tasks.Task.Messages.List();
                            } else {
                                $.showModalMessageBox(response.Message);
                            }

                            $(e).removeAttr("disabled");
                        });
                    },
                }
            },
            Files: {
                File: {
                    Open: function (taskGuid) {
                        var data =
                        {
                            taskGuid: taskGuid,
                        };
                        var url = AP_ROOT + AP_PAGE_ID + "/TP/TaskFile/FileUpload";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#taskFileUploadModal').modal({ backdrop: 'static', keyboard: false });
                            $('#taskFileUploadModal').on('hidden.bs.modal', function () {
                                $("#taskFileUploadModal").remove();
                            });
                        });
                    },
                    Close: function () {
                        $('#taskFileUploadModal').modal('hide');
                    },
                    Upload: function (e) {     
                        $('#uploadForm').ajaxSubmit({
                            success: function (response) {
                                if (response.IsSuccess) {
                                    $.showModalMessageBox("上传成功.");
                                    $.each(response.Data, function (i, f) {
                                        $("#attachments").html("<div  class='margin-top'><span>" + f.FileName + "</span> "
                                            + " <a id='attachmentfile' href='javascript:void(0);' onclick='javascript:task.Tasks.Task.Files.File.DeleteFile(this," + f.FileId + ")'>删除</a> "
                                            + " <a id='attachmentfile' href='javascript:void(0);' onclick='javascript:task.Tasks.Task.Files.File.View(" + f.FileId + ',\"' + f.TaskGuid + '\",\"' + f.FileName + "\")'>查看</a> "
                                            + "</div>");
                                    });

                                    $("#attachments").show();
                                    $("#help-block").hide()
                                } else {
                                    $("#help-block").show();
                                }
                            }
                        });

                        
                    },
                    FileUpload: function (e) {
                        if ($("#flTaskFile").val() == '') {
                            $.showModalMessageBox("请选择上传文件.");
                            return false;
                        }
                         
                        $('#uploadForm').ajaxSubmit({
                            success: function (response) {
                                if (response.IsSuccess) {
                                    task.Tasks.Task.Files.List();
                                    task.Tasks.Task.Files.File.Close();
                                } else {
                                    $.showModalMessageBox("上传失败.");
                                }
                            }
                        });
                    },
                    View: function (taskFileId, taskGuid, taskFileName) {

                        if (taskFileId == '' || taskGuid == '' || taskFileName == '') {
                            $.showModalMessageBox("无调查资料文件.");
                            return false;
                        }

                        var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                        var picfiles = new Array('jpg', 'tif', 'pdf');
                        var extName = taskFileName.substring(taskFileName.lastIndexOf('.') + 1, taskFileName.length);

                        if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                            var path = GV_IPR.OfficeOnlineUrl + GV_IPR.OnlineUrl + "CaseFiles/TaskFiles/" + taskGuid + "/" + taskFileName;
                            window.open(path);
                        }
                        else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                            var path = GV_IPR.OnlineUrl + "CaseFiles/TaskFiles/" + taskGuid + "/" + taskFileName;
                            window.open(path);
                        } else {
                            task.Tasks.Task.Files.File.Download(taskFileId);
                        }

                        return true;
                    },
                    Download: function (taskFileId) {
                        window.open(AP_ROOT + AP_PAGE_ID + "/TP/TaskFile/TaskFileDownload?fileId=" + taskFileId);
                        return true;
                    },
                    Delete: function (fileIds, functionCallback) {
                        var data = {
                            fileIds: fileIds,
                        };
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/TaskFile/Delete", data, function (response) {
                            if (response.IsSuccess) {
                                //$(e).parent().remove();
                                setTimeout(functionCallback(), 200);

                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },
                    DeleteFile: function (e, fileId) {
                        var fileIds = new Array();
                        fileIds.push(fileId);
                        var data = {
                            fileIds: fileIds,
                        };
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/TaskFile/Delete", data, function (response) {
                            if (response.IsSuccess) {
                                $(e).parent().remove();
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    }
                },
            },
            TaskNode: {
                Open: function (taskId) {

                    var data = { taskId: $("#Task_TaskId").val() };
                    var url = AP_ROOT + AP_PAGE_ID + "/TP/TaskNode/Create";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(".slide-panel-container").empty();
                        $(".slide-panel-container").append(result);
                        $(".slide-panel-container").addClass("show-panel");
                    });
                },

                ReOpen: function (e) {

                    $(e).attr("disabled", "disabled");
                    var data = { taskId: $("#Task_TaskId").val() };
                    var url = AP_ROOT + AP_PAGE_ID + "/TP/TaskNode/Create";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(".slide-panel-container").empty();
                        $(".slide-panel-container").append(result);
                        $(".slide-panel-container").addClass("show-panel");
                    });
                },

                Checked: function (e) {
                    $(e).attr("disabled", "disabled");

                    var taskIds = new Array();

                    taskIds.push($("#Task_TaskId").val());

                    var data = {
                        taskIds: taskIds,
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/Task/Checked", data, function (response) {
                        if (response.IsSuccess) {
                            task.Tasks.List();
                            task.Tasks.Task.View($("#Task_TaskId").val());
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                },

                Process: function (e) {

                    $(e).attr("disabled", "disabled");

                    var taskIds = new Array();

                    taskIds.push($("#Task_TaskId").val());

                    var data = {
                        taskIds: taskIds,
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/Task/Process", data, function (response) {
                        if (response.IsSuccess) {
                            task.Tasks.Task.View($("#Task_TaskId").val());
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });


                },

                Finished: function (e) {

                    $(e).attr("disabled", "disabled");

                    var taskIds = new Array();
                    taskIds.push($("#Task_TaskId").val());
                    var data = {
                        taskIds: taskIds,
                    };
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/Task/Finished", data, function (response) {
                        if (response.IsSuccess) {
                            task.Tasks.Task.View($("#Task_TaskId").val());
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                },
                Rejected: function (e) {
                    $(e).attr("disabled", "disabled");
                    var taskIds = new Array();
                    taskIds.push($("#Task_TaskId").val());
                    var data = {
                        taskIds: taskIds,
                    };
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/Task/Rejected", data, function (response) {
                        if (response.IsSuccess) {
                            task.Tasks.Task.View($("#Task_TaskId").val());
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                },
                Stoped: function (e) {

                    $(e).attr("disabled", "disabled");

                    var taskIds = new Array();

                    taskIds.push($("#Task_TaskId").val());

                    var data = {
                        taskIds: taskIds,
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/Task/Stoped", data, function (response) {
                        if (response.IsSuccess) {
                            task.Tasks.List();
                            task.Tasks.Task.View($("#Task_TaskId").val());
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                },

                CreateUpdate: function (e) {
 
                    if ($("#Task_NodeBeginTime").val() == '') {
                        $.showModalMessageBox("请输入任务结束时间");
                        return false;
                    }

                    if ($("#Task_NodeEndTime").val() == '') {
                        $.showModalMessageBox("请输入任务结束时间");
                        return false;
                    }

                    var officers = [];
                    var officernames = [];

                    $("a[name='officername']").each(function () {
                        officers.push($(this).attr("username"));
                        officernames.push($(this).attr("userchname"));
                    });

                    if (officers.length == 0) {
                        $.showModalMessageBox("请输入负责人.");
                        return false;
                    }

                    var associates = [];
                    var associatenames = [];

                    $("a[name='associatename']").each(function () {
                        associates.push($(this).attr("username"));
                        associatenames.push($(this).attr("userchname"));
                    });
 
                    var data = {};

                    data["TaskNode.Officer"] = officers.join(",");
                    data["TaskNode.Associates"] = associates.join(",");
                    data["TaskNode.AssociateNames"] = associatenames;
                    data["TaskNode.NodeBeginTime"] = $("#Task_NodeBeginTime").val();
                    data["TaskNode.NodeEndTime"] = $("#Task_NodeEndTime").val();
                    data["TaskNode.NodeContent"] = $("#Task_NodeContent").val();
                    data["TaskNode.TaskGuid"] = $("#Task_TaskGuid").val();
                    data["TaskNode.NodeGuid"] = $("#Task_NodeGuid").val();
                    data["TaskNode.MessageGuid"] = $("#Task_MessageGuid").val();

                    $(e).attr("disabled", "disabled");
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/TaskNode/TaskNodeCreate", data, function (response) {
                        $(e).removeAttr("disabled");
                        if (response.IsSuccess) {
                            task.Tasks.Task.View($("#Task_TaskId").val())
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                },
            },
            TaskStatus: {
                Pending : 1,
                Processing : 2,
                Finished : 3,
                Rejected : 4,
                Stoped : 5,
                Checked: 10
            }
        },
        List: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/TP/Task/TaskSearchList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblTaskList").clearRow();
                    if (response.Data.TotalItemCount > 0) {

                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.TaskList, function (i, t) {
                            var taskStausHtml = '';
                            if (t.TaskStatus == task.Tasks.Task.TaskStatus.Finished || t.TaskStatus == task.Tasks.Task.TaskStatus.Checked)
                            {
                                taskStausHtml = "<div style='text-align: center;width: 100%;height: 100%;background-color:green'><span style='color:white'>" + t.TaskStatusName + "</span></div>";
                            }
                            else if (t.TaskStatus == task.Tasks.Task.TaskStatus.Rejected)
                            {
                                taskStausHtml = "<div style='text-align: center;width: 100%;height: 100%; background-color:red'><span style='color:white'>" + t.TaskStatusName + "</span></div>";
                            }
                            else if (t.TaskStatus == task.Tasks.Task.TaskStatus.Stoped) {
                                taskStausHtml = "<div style='text-align: center;width: 100%;height: 100%; background-color:grey'><span style=''>" + t.TaskStatusName + "</span></div>";
                            }
                            else {
                                taskStausHtml = "<div style='text-align: center'><span style=''>" + t.TaskStatusName + "</span></div>";
                            }

                            $("tbody", "#tblTaskList").addRow(
                                    "<span class='taskId' style='display:none'>" + t.TaskId + "</span><a style='color: #039' href='javascript:void(0);'  onclick='javascript:task.Tasks.Task.ViewTask(this," + t.TaskId + ");' >" + t.TaskNo + "</a>",
                                    "<span class='caseId' style='display:none'>" + t.CaseId + "</span><a style='color: #039' href='javascript:void(0);'  onclick='javascript:$.case.ViewCaseId(this," + t.CaseId + ',\"' + t.CaseNo + "\");' >" + t.CaseNo + "</a>",
                                    t.CustomerName,
                                    taskStausHtml,
                                    t.TaskPriorityName,
                                    t.TaskTitle,
                                    t.TaskBeginTime == null ? '' : getDate(convertJsonDateToJSDate(t.TaskBeginTime)),
                                    t.TaskEndTime == null ? '' : getDate(convertJsonDateToJSDate(t.TaskEndTime)),
                                     
                                    t.TaskRemainingDays == null ? '' : t.TaskRemainingDays + "/天",
                                    t.TaskLastChangeTime == null ? '' : getDateTime(convertJsonDateToJSDate(t.TaskLastChangeTime)),
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
                            callBack: task.Tasks.List,
                            callBackArgs: null
                        });

                    } else {

                        $("tfoot", "#tblTaskList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        SelectedStatus: function (e, status) {
            $("#SearchCondition_TaskStatus").val(status);
            $("#SearchCondition_NodeStatus").val('');

            $("#SearchCondition_PageNo").val(1);
            $("#SearchCondition_PageSize").val(20);
            $.each($(e).parent().parent().find("li"), function (i, li) {
                $(li).removeClass("active")
            }),

            $(e).parent().addClass("active")

            task.Tasks.List();
            task.Tasks.Task.Close();

            

            if (status == task.Tasks.Task.TaskStatus.Checked) {
                var text = '验收日期<span><span class="aps-state-hidden"></span><span data-field="T.ChangeTime" class="aps-widget aps-ani-transition aps-sort aps-state-visible"><i type="up" class="aps-icon aps-ani-transition aps-widget aps-icon-shangjiantou aps-sort-btn aps-sort-btn-up"></i><i type="down" class="aps-icon aps-ani-transition aps-widget aps-icon-xiajiantou aps-sort-btn aps-sort-btn-down" style="top:9px"></i></span></span>';

                $($("#tblTaskList>thead>tr>th")[7]).css("width", "0%");
                $("#tblTaskList>tbody>tr").each(function (j, e) {
                    
                    $($(e).find("td")[7]).css("width", "0%");
                    $($(e).find("td")[7]).css("white-space", "nowrap");
                });

                $($("#tblTaskList>thead>tr>th")[8]).css("width", "0%");
                $("#tblTaskList>tbody>tr").each(function (j, e) {
                    $($(e).find("td")[8]).css("width", "0%");
                    $($(e).find("td")[8]).css("white-space", "nowrap");
                });

                $($("#tblTaskList>thead>tr>th")[9]).html(text);
            }
            else {
                var text = '最后更新时间<span><span class="aps-state-hidden"></span><span data-field="T.ChangeTime" class="aps-widget aps-ani-transition aps-sort aps-state-visible"><i type="up" class="aps-icon aps-ani-transition aps-widget aps-icon-shangjiantou aps-sort-btn aps-sort-btn-up"></i><i type="down" class="aps-icon aps-ani-transition aps-widget aps-icon-xiajiantou aps-sort-btn aps-sort-btn-down" style="top:9px"></i></span></span>';


                $($("#tblTaskList>thead>tr>th")[7]).css("width", "6%");
                $("#tblTaskList>tbody>tr").each(function (j, e) {
                    $($(e).find("td")[7]).css("width", "6%");
                });

                $($("#tblTaskList>thead>tr>th")[8]).css("width", "6%");
                $("#tblTaskList>tbody>tr").each(function (j, e) {
                    $($(e).find("td")[8]).css("width", "6%");
                });

                $($("#tblTaskList>thead>tr>th")[9]).html(text);
            }

        },
        SelectedNodeStatus: function (e, status) {
            $("#SearchCondition_NodeStatus").val(status);
            $("#SearchCondition_TaskStatus").val('');

            $("#SearchCondition_PageNo").val(1);
            $("#SearchCondition_PageSize").val(20);

            $.each($(e).parent().parent().find("li"), function (i, li) {
                $(li).removeClass("active")
            }),

            $(e).parent().addClass("active")

            task.Tasks.List();
            task.Tasks.Task.Close();
        },
    },
};

$(document).ready(function () {

    $(document).off('click', '#flTaskFile').on('change', '#flTaskFile', function () {
        if ($("#flTaskFile").val() == '') {
            $.showModalMessageBox("请选择上传文件.");
            return false;
        }

        task.Tasks.Task.Files.File.Upload();
    });

    $(document).off('click', '#flTaskNodeFile').on('change', '#flTaskNodeFile', function () {
        if ($("#flTaskNodeFile").val() == '') {
            $.showModalMessageBox("请选择上传文件.");
            return false;
        }
        task.Tasks.Task.Files.File.Upload();
    });

    $(document).off('click', '#btnTaskFileUpload').on('click', '#btnTaskFileUpload', function () {
        $("#flTaskFile").trigger("click");
    });

    $(document).off('click', '#btnTaskNodeFileUpload').on('click', '#btnTaskNodeFileUpload', function () {
        $("#flTaskNodeFile").trigger("click");
    });

    $(document).off('click', '.userremove').on('click', '.userremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        $(this).parent().remove();
    });

    $(document).off('click', '#btnTaskCreateUpdate').on('click', '#btnTaskCreateUpdate', function () {
        task.Tasks.Task.CreateUpdate();
    });

    $(document).off('click', '#btnTaskNodeCreate').on('click', '#btnTaskNodeCreate', function () {
        task.Tasks.Task.TaskNode.CreateUpdate(this);
    });

});