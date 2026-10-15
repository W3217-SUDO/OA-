function AssociateCustomer(div, ctlid, ctlno, ctlname) {
    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;
    this.Customer = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") { return false; }
        var curobj = new Object();
        curobj.keyword = name;
        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CustomerList", curobj, function (response) {

            $(div).find(".i_common_list").empty();
            if (response.IsSuccess) {
                if (response.Data.Customers.length > 0) {
                    var html = "";
                    $.each(response.Data.Customers, function (i, c) {

                        var defaultContactsContacts = c.DefaultContacts == null ? "" : c.DefaultContacts.Contacts;
                        var defaultContactsContactTelphone = c.DefaultContacts == null ? "" : c.DefaultContacts.OfficePhone;
                        var defaultContactsContactEmail = c.DefaultContacts == null ? "" : c.DefaultContacts.Email;
                        var defaultContactsContactAddress = c.DefaultContacts == null ? "" : c.DefaultContacts.ContactAddress;

                        html += '<a href="javascript:void(0)"  customerid=' + c.CustomerBasic.CustomerId
                            + ' customerno=' + c.CustomerBasic.CustomerNo
                            + ' defaultContactsContacts=' + defaultContactsContacts
                            + ' defaultContactsContactTelphone=' + defaultContactsContactTelphone
                            + ' defaultContactsContactEmail=' + defaultContactsContactEmail
                            + ' defaultContactsContactAddress=' + defaultContactsContactAddress
                            + ' >' + c.CustomerBasic.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);

                    $(div).find(".i_common_list a").css({
                        "height": $(ctlname).outerHeight(),
                        "line-height": ($(ctlname).outerHeight() - 4) + "px"
                    });

                    $(div).find(".i_common_list a").click(function () {
                        //$(ctlid).val($(this).attr("customerid"));
                        $(ctlno).val($(this).attr("customerno"));
                        $(ctlname).val($(this).text());


                        $(div).hide();

                    });

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
                $.showModalMessageBox(response.Message);
            }
        }, false);
        $(div).css({
            "position": "absolute",
            "left": $(ctlname).position().left + 0,
            "top": $(ctlname).position().top + 32,
            "width": $(ctlname).outerWidth(),
            "height": $(ctlname).outerHeight(),
            "z-index": 9999
        }).show();
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
            event.data.obj.Event = setTimeout(function () { event.data.obj.Customer(event.data.obj); }, 500);
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
function AssociateAvailableUser(div, ctlid, ctlname, func) {

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
                        investigation.Investigations.Investigation.Tasks.Task.Investigator.AddIn($(this).attr("userId"), $(this).text());
                        $(ctlname).val('');
                        $(ctlname).focus();
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
function AssociateAvailableUserForClue(div, ctlid, ctlname, func) {

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

var investigation = {

    ResetSize: function () {
        //if ($("#divContextList").length > 0) {
        //    $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 12);
        //}
    },
    /**/
    Investigations: {
        Investigation: {
            ToAudit: function () {
                if ($("#Investigation_Basic_Auditor").val() == '') {
                    $.showModalMessageBox("请选择审批人.");
                    return false;
                }
                var data =
                {
                    investigationNo: $("#Investigation_Basic_InvestigationNo").val(),
                    auditor: $("#Investigation_Basic_Auditor").val(),
                };

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/Investigation/ToAudit", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalConfirmDialog("提交成功.", 'investigation.Investigations.Investigation.ToAuditCallBack', true, true);
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },
            ToAuditCallBack: function () {
                window.location = AP_ROOT + "1401001002/CIT/Investigation/List";
            },
            View: function (investigationNo) {
                var data =
                {
                    investigationNo: investigationNo,
                };
                var url = AP_ROOT + AP_PAGE_ID + "/CIT/Investigation/PreView";

                $.openLoading();

                $("<div></div>").load(url, data, function (result) {

                    $.closeLoading();
                    $(".sidebox-content").empty();
                    $(".sidebox-content").append(result);
                    $("#sidebox").show();
                });

            },
            Close: function () {
                $(".sidebox-content").empty();
                $("#sidebox").hide();

                return false;
            },
            Layout: {
                Display: function (e) {
                    if ($(e).hasClass("icon-down")) {
                        $("#divInvestigationBasic").hide();
                        $(e).removeClass("icon-down")
                        $(e).addClass("icon-up")
                    }
                    else if ($(e).hasClass("icon-up")) {
                        $("#divInvestigationBasic").show();
                        $(e).removeClass("icon-up")
                        $(e).addClass("icon-down")
                    }
                },
            },
            Edit: function (investigationNo) {
                var data = {
                    investigationNo: investigationNo,
                };
                var url = AP_ROOT + AP_PAGE_ID + "/CIT/Investigation/Edit";
                //$.openLoading();
                $("<div></div>").load(url, data, function (result) {
                    //$.closeLoading();
                    $(document.body).append(result);
                    $('#investigationModal').modal({ backdrop: 'static', keyboard: false });
                    $('#investigationModal').on('hidden.bs.modal', function () {
                        $("#investigationModal").remove();
                    });
                });
            },
            Hide: function () {
                $('#investigationModal').modal('hide');
            },
            Delete: function (investigationNos) {
                $.showModalConfirmDialog("删除调查任务会连带子任务,线索一起删除,确定删除？", "investigation.Investigations.Investigation.DeleteCallBack", investigationNos);
                return true;
            },
            DeleteCallBack: function (investigationNos) {
                var data = { investigationNos: investigationNos };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/Investigation/Delete", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("删除成功.");
                        investigation.Investigations.List();
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },
            CreateUpdate: function (isSubmit) {
                try {

                    if ($("#Investigation_Basic_IndicterName").val() == '') {
                        $.showModalMessageBox("请输入权利人.");
                        $("#Investigation_Basic_IndicterName").focus();
                        return false;
                    }

                    if ($("#Investigation_Basic_AuthorizationBeginTime").val() == '') {
                        $.showModalMessageBox("请输入授权开始时间.");
                        $("#Investigation_Basic_AuthorizationBeginTime").focus();
                        return false;
                    }

                    if ($("#Investigation_Basic_AuthorizationEndTime").val() == '') {
                        $.showModalMessageBox("请输入授权结束时间.");
                        $("#Investigation_Basic_AuthorizationEndTime").focus();
                        return false;
                    }

                    if ($("#Investigation_Basic_InvestigationScope").val() == 'R' && $("#Investigation_Basic_Province").val() == '') {

                        $.showModalMessageBox("请输入授权区域.");
                        $("#Investigation_Basic_AuthorizationEndTime").focus();
                        return false;
                    }


                    var result = $.compare.dateMsg($("#Investigation_Basic_AuthorizationBeginTime").val(), $("#Investigation_Basic_AuthorizationEndTime").val(), "授权结束时间必须大于开始时间.");
                    if (!result) return false;

                    var data = {};

                    data["Investigation.Basic.InvestigationNo"] = $("#Investigation_Basic_InvestigationNo").val();
                    data["Investigation.Basic.InvestigationGuid"] = $("#Investigation_Basic_InvestigationGuid").val();
                    data["Investigation.Basic.Indicter"] = $("#Investigation_Basic_Indicter").val();
                    data["Investigation.Basic.IndicterName"] = $("#Investigation_Basic_IndicterName").val();
                    data["Investigation.Basic.CaseTypeId"] = $("#Investigation_Basic_CaseTypeId").val();
                    data["Investigation.Basic.NeedToAuditOnCustomer"] = $("#Investigation_Basic_NeedToAuditOnCustomer").val();
                    data["Investigation.Basic.AuthorizationBeginTime"] = $("#Investigation_Basic_AuthorizationBeginTime").val();
                    data["Investigation.Basic.AuthorizationEndTime"] = $("#Investigation_Basic_AuthorizationEndTime").val();
                    data["Investigation.Basic.InvestigationScope"] = $("#Investigation_Basic_InvestigationScope").val();
                    data["Investigation.Basic.City"] = $("#Investigation_Basic_City").val();
                    data["Investigation.Basic.Province"] = $("#Investigation_Basic_Province").val();
                    data["Investigation.Basic.Remark"] = $("#Investigation_Basic_Remark").val();

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/Investigation/CreateUpdate", data, function (response) {
                        if (response.IsSuccess) {
                            if (isSubmit) {
                                window.location = AP_ROOT + AP_PAGE_ID + "/CIT/Investigation/Assigning?investigationNo=" + response.Data;
                            }
                            else {
                                investigation.Investigations.List();
                                investigation.Investigations.Investigation.Hide();
                            }
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {

                }
            },
            CreateUpdateCallBack: function (isSubmit) {
            },
            Tasks: {
                Layout: function () {
                    var data = {
                        investigationNo: $("#Investigation_Basic_InvestigationNo").val(),
                    };
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationTask/TaskList", data, function (response) {
                        if (response.IsSuccess) {
                            $.openLoading();
                            $("#dv_TaskList").empty();
                            $("#dv_TaskList").html(response.Data);
                            investigation.Investigations.Investigation.Tasks.List();
                            $.closeLoading();
                        }
                    }, true);
                },
                List: function () {
                    var data = {
                        investigationNo: $("#Investigation_Basic_InvestigationNo").val(),
                        pageNo: $("#PageNo").val(),
                        pageSize: $("#PageSize").val()
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationTask/InvestigationTasks", data, function (response) {
                        if (response.IsSuccess) {

                            $("tbody", "#tblInvestigationTaskList").clearRow();
                            if (response.Data.TotalItemCount > 0) {
                                $.each(response.Data.InvestigationTasks, function (i, task) {

                                    $("tbody", "#tblInvestigationTaskList").addRow(
                                        "<input type='checkbox' id='chkTaskId' name='chkTaskId' value=" + task.Basic.TaskNo + ">",
                                        task.Basic.TaskNo,
                                        //"<a href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Tasks.Task.View(\"" + task.Basic.TaskNo + "\");'><span>" + task.Basic.TaskNo + "</span></a>",
                                        task.Basic.InvestigatorName,
                                        task.Basic.Province,
                                        task.Basic.BeginTime == null ? '' : getDate(convertJsonDateToJSDate(task.Basic.BeginTime)),
                                        task.Basic.EndTime == null ? '' : getDate(convertJsonDateToJSDate(task.Basic.EndTime)),
                                        "<a style='color:red;' href='javascript:void(0);'><span class='btn_investigationtask_remove glyphicon glyphicon-remove'></span></a>"
                                    );
                                });
                                $("tfoot", "#tblInvestigationTaskList").show();
                                $(".simple-grid-none-data-wrap.none-investigationtask").hide();

                                $(".pull-right.page-box.investigationtask").cPaging({
                                    totalCount: response.Data.TotalItemCount,
                                    pageNo: response.Data.PageNo,
                                    pageSize: response.Data.PageSize,
                                    callBack: investigation.Investigations.Investigation.Tasks.List,
                                    callBackArgs: null
                                });

                            } else {
                                $(".simple-grid-none-data-wrap.none-investigationtask").show();
                                $("tfoot", "#tblInvestigationTaskList").hide();

                            }
                            investigation.ResetSize();
                            //$.closeLoading();
                        }
                    }, null);
                },
                Selected: function (e) {
                    if ($(e).prop('checked') == true) {
                        $.checkbox.all("chkTaskId");
                        $.checkbox.all("chkTaskAll");

                    } else {
                        $.checkbox.not("chkTaskId");
                        $.checkbox.not("chkTaskAll");
                    }
                },
                Task: {
                    View: function (investigationTaskNo) {
                        var data =
                        {
                            investigationTaskNo: investigationTaskNo,
                        };
                        var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationTask/PreView";
                        $.openLoading();
                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(".sidebox-content").empty();
                            $(".sidebox-content").append(result);
                            $("#sidebox").show();
                        });
                    },
                    Edit: function (investigationTaskNo) {
                        var data = {
                            investigationTaskNo: investigationTaskNo,
                        };
                        var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationTask/Edit";
                        $.openLoading();
                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);

                            var investigator = new AssociateAvailableUser(
                                $("#div_userlist"),
                                $("#InvestigationTask_Basic_Investigator_Input"),
                                $("#InvestigationTask_Basic_Investigator_Input"),
                                null
                            );

                            $('#investigationTaskModal').modal({ backdrop: 'static', keyboard: false });
                            $('#investigationTaskModal').on('hidden.bs.modal', function () {
                                $("#investigationTaskModal").remove();
                            });
                        });
                    },
                    Investigator: {
                        AddIn: function (username, userchname) {

                            var existsUser = false;

                            $("a[name='username']").each(function () {
                                if ($(this).attr("username") == username) {
                                    existsUser = true;
                                    return true;
                                }
                            });

                            //重复

                            if (existsUser) return true;

                            var $tag = $("<span class='tag label label-info'>"
                                         + "<a name='username' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                         + " username='" + username + "'"
                                         + " userchname='" + userchname + "'"
                                         + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);'   data-original-title=" + userchname + " '>" + userchname + "</a>"
                                         + "<span class='userremove' data-role='remove'></span>"
                                       + "</span>");

                            $("#InvestigationTask_Basic_Investigator_Input").before($tag);
                            $tag.after(' ');

                        },
                        Remove: function (e) {
                            $(e).parent().remove();
                        },
                    },
                    CreateUpdate: function (functionCallback) {
                        try {

                            var investigators = [];
                            var investigatornames = [];

                            $("a[name='username']").each(function () {
                                investigators.push($(this).attr("username"));
                                investigatornames.push($(this).attr("userchname"));
                            });

                            if (investigators.length == 0) {
                                $.showModalMessageBox("请输入调查员.");
                                $("#InvestigationTask_Basic_Investigator_Input").focus();
                                return false;
                            }


                            if ($("#InvestigationTask_Basic_Province").val() == '') {
                                $.showModalMessageBox("请选择调查区域.");
                                $("#InvestigationTask_Basic_Province").focus();
                                return false;
                            }

                            if ($("#InvestigationTask_Basic_BeginTime").val() == '') {
                                $.showModalMessageBox("请输入调查开始时间.");
                                $("#InvestigationTask_Basic_BeginTime").focus();
                                return false;
                            }

                            if ($("#InvestigationTask_Basic_EndTime").val() == '') {
                                $.showModalMessageBox("请输入调查结束时间.");
                                $("#InvestigationTask_Basic_EndTime").focus();
                                return false;
                            }

                            var result = $.compare.dateMsg($("#InvestigationTask_Basic_BeginTime").val(), $("#InvestigationTask_Basic_EndTime").val(), "调查结束时间必须大于开始时间.");
                            if (!result) return false;

                            var data = {};

                            data["InvestigationTask.Basic.InvestigationNo"] = $("#InvestigationTask_Basic_InvestigationNo").val();
                            data["InvestigationTask.Basic.TaskNo"] = $("#InvestigationTask_Basic_TaskNo").val();
                            data["InvestigationTask.Basic.Investigator"] = investigators.join(",");
                            data["InvestigationTask.Basic.InvestigatorName"] = investigatornames.join(",");
                            data["InvestigationTask.Basic.BeginTime"] = $("#InvestigationTask_Basic_BeginTime").val();
                            data["InvestigationTask.Basic.EndTime"] = $("#InvestigationTask_Basic_EndTime").val();
                            data["InvestigationTask.Basic.City"] = $("#InvestigationTask_Basic_City").val();
                            data["InvestigationTask.Basic.Province"] = $("#InvestigationTask_Basic_Province").val();
                            data["InvestigationTask.Basic.Remark"] = $("#InvestigationTask_Basic_Remark").val();

                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationTask/CreateUpdate", data, function (response) {
                                
                                if (response.IsSuccess) {
                                    if (functionCallback != null) {
                                        setTimeout(functionCallback(), 200);
                                    }
                                    else {

                                    }
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });

                        } catch (e) {
                        }
                    },
                    CreateUpdateCallBack_NextOne: function () {
                        window.location = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationTask/Create?InvestigationNo=" + $("#InvestigationTask_Basic_InvestigationNo").val();
                    },
                    CreateUpdateCallBack_End: function () {
                        window.location = AP_ROOT + AP_PAGE_ID + "/CIT/Investigation/List";
                    },
                    CreateUpdateCallBack_RefreshList: function () {
                        
                        investigation.Investigations.Investigation.Tasks.List();
                        $.showModalMessageBox("修改成功");
                        $('#investigationTaskModal').modal('hide');
                    },
                    Files: {
                        Layout: function () {
                            var data = {
                                investigationId: $("#Contract_ContractBasicInfo_ContractId").val()
                            };

                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFile/ContractFileList", data, function (response) {
                                if (response.IsSuccess) {
                                    $.openLoading();
                                    $("#dv_List").empty();
                                    $("#dv_List").html(response.Data);
                                    investigation.Investigations.Investigation.Tasks.Task.Files.List();
                                    //investigation.ResetSize();
                                    $.closeLoading();
                                }
                            }, true);
                        },
                        List: function () {
                            var data = {
                                investigationGuid: $("#Contract_ContractBasicInfo_ContractGuid").val(),
                            };

                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFile/ContractFiles", data, function (response) {
                                if (response.IsSuccess) {
                                    $.openLoading();

                                    if (response.Data.length > 0) {
                                        $.each(response.Data, function (i, file) {
                                            $("tbody", "#tblContractFileList").addRow(
                                                ++i,
                                                file.UploadUserName,
                                                file.FileName,
                                                file.UploadTime == null ? '' : getDate(convertJsonDateToJSDate(file.UploadTime)),
                                                "<a style='color: #039' href='javascript:void(0);' onclick='javascript:investigation.Contract.Files.File.View(\"" + file.ContractGuid + "\",\"" + file.FileGuid + "\",\"" + file.FileName + "\");'><span>查看</span></a>&nbsp;&nbsp;&nbsp;" +
                                                "<a style='color: #039' href='javascript:void(0);' onclick='javascript:investigation.Contract.Files.File.Download(\"" + file.FileGuid + "\");'><span>下载</span></a>",
                                                "<a style='color:green;' href='javascript:void(0);'><span class='btn_investigationfile_add glyphicon glyphicon-plus'></span></a>    "
                                            );
                                        });
                                        $(".simple-grid-none-data-wrap").hide();
                                    } else {
                                        $(".simple-grid-none-data-wrap").show();
                                    }
                                    investigation.ResetSize();
                                    $.closeLoading();
                                }
                            }, true);
                        },
                        File: {
                            Open: function () {
                                var data =
                                {
                                    investigationGuid: $("#Contract_ContractBasicInfo_ContractGuid").val(),
                                };
                                var url = AP_ROOT + AP_PAGE_ID + "/FCM/ContractFile/ContractFileUpload";
                                $.openLoading();

                                $("<div></div>").load(url, data, function (result) {
                                    $.closeLoading();
                                    $(document.body).append(result);
                                    $('#investigationFileUploadModal').modal({ backdrop: 'static', keyboard: false });
                                    $('#investigationFileUploadModal').on('hidden.bs.modal', function () {
                                        $("#investigationFileUploadModal").remove();
                                    });
                                });
                            },
                            Close: function () {
                                $('#investigationFileUploadModal').modal('hide');
                            },
                            Upload: function (e) {
                                if ($("#flFile").val() == '') {
                                    $.showModalMessageBox("请选择上传文件.");
                                    return false;
                                }

                                $('#uploadForm').ajaxSubmit({
                                    success: function (response) {
                                        $.showModalMessageBox("上传成功.");
                                        if (response.IsSuccess) {
                                            $.each(response.Data, function (i, f) {
                                                $("#attachments").append("<div  class='margin-top'><span>" + f.FileName + "</span> <a id='attachmentfile' href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Tasks.Task.Files.File.Delete(this," + f.FileId + ")'>删除</a></div>");
                                            });
                                            $("#help-block").hide()
                                        } else {
                                            $("#help-block").show();
                                        }
                                    }
                                });
                            },
                            View: function (investigationFileId, investigationNo, investigationFileName) {

                                if (investigationFileId == '' || investigationFileName == '') {
                                    $.showModalMessageBox("无合同文件.");
                                    return false;
                                }

                                var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                                var picfiles = new Array('jpg', 'tif', 'pdf');
                                var extName = investigationFileName.substring(investigationFileName.lastIndexOf('.') + 1, investigationFileName.length);

                                if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                                    var path = GV_IPR.OfficeOnlineUrl + GV_IPR.OnlineUrl + "ContractFiles/ContractFiles/" + investigationNo + "/" + investigationFileName;
                                    window.open(path);
                                }
                                else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                                    var path = GV_IPR.OnlineUrl + "ContractFiles/ContractFiles/" + investigationNo + "/" + investigationFileName;
                                    window.open(path);
                                } else {
                                    investigation.Investigations.Investigation.Tasks.Task.ContractFile.Download(investigationFileId);
                                }

                                return true;
                            },
                            Download: function (investigationFileId) {
                                window.open(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFile/ContractFileDownloadByGuid?investigationFileId=" + investigationFileId);
                                return true;
                            },

                            Delete: function (e, fileId) {
                                var data = {
                                    fileId: fileId,
                                };
                                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationTaskFile/Delete", data, function (response) {
                                    if (response.IsSuccess) {
                                        $(e).parent().remove();
                                    } else {
                                        $.showModalMessageBox(response.Message);
                                    }
                                });
                            }
                        }
                    },
                    List: function () {
                        $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationTask/List", function (response) {
                            if (response.IsSuccess) {
                                $("tbody", "#tblTaskList").clearRow();
                                if (response.Data.TotalItemCount > 0) {
                                    $(".info_inall.layoutfix").show();
                                    $.each(response.Data.InvestigationTasks, function (i, it) {
                                        $("tbody", "#tblTaskList").addRow(
                                            ++i,
                                            "<a href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Tasks.Task.View(\"" + it.Basic.TaskNo + "\");'><span>" + it.Basic.TaskNo + "</span></a>",
                                            it.Basic.IndicterName,
                                            $.lsCaseType.getCaseTypeName(it.Basic.CaseTypeId),
                                            it.Basic.Province,
                                            it.Basic.BeginTime == null ? '' : getDate(convertJsonDateToJSDate(it.Basic.BeginTime)),
                                            it.Basic.EndTime == null ? '' : getDate(convertJsonDateToJSDate(it.Basic.EndTime)),
                                            it.Basic.BusinessOwnerName);
                                    });

                                    $("tfoot", "#tblTaskList").show();
                                    $(".simple-grid-none-data-wrap").hide();

                                    $(".pull-right.page-box.task").cPaging({
                                        totalCount: response.Data.TotalItemCount,
                                        pageNo: response.Data.PageNo,
                                        pageSize: response.Data.PageSize,
                                        callBack: investigation.Investigations.Investigation.Tasks.Task.List,
                                        callBackArgs: null
                                    });
                                } else {
                                    $("tfoot", "#tblTaskList").hide();
                                    $(".simple-grid-none-data-wrap").show();
                                }
                            }
                        });
                    },
                    Delete: function (taskNos) {
                        $.showModalConfirmDialog("确定删除调查子任务？", "investigation.Investigations.Investigation.Tasks.Task.DeleteCallBack", taskNos);
                        return true;
                    },
                    DeleteCallBack: function (taskNos) {
                        var data = {
                            taskNos: taskNos,
                        };
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationTask/Delete", data, function (response) {
                            if (response.IsSuccess) {
                                investigation.Investigations.Investigation.Tasks.TaskList();
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },
                },

                TaskList: function () {
                    $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationTask/List", function (response) {
                        if (response.IsSuccess) {
                            $("tbody", "#tblTaskList").clearRow();
                            if (response.Data.TotalItemCount > 0) {
                                $(".info_inall.layoutfix").show();
                                $.each(response.Data.InvestigationTasks, function (i, it) {
                                    $("tbody", "#tblTaskList").addRow(
                                         "<input type='checkbox' id='chkTaskId' name='chkTaskId' value=" + it.Basic.TaskNo + ">",
                                        "<a href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Tasks.Task.View(\"" + it.Basic.TaskNo + "\");'><span>" + it.Basic.TaskNo + "</span></a>",
                                        it.Basic.IndicterName,
                                        it.Basic.CaseTypeName,
                                        it.Basic.InvestigatorName,
                                        it.Basic.Province,
                                        it.Basic.BeginTime == null ? '' : getDate(convertJsonDateToJSDate(it.Basic.BeginTime)),
                                        it.Basic.EndTime == null ? '' : getDate(convertJsonDateToJSDate(it.Basic.EndTime)),
                                        it.Basic.BusinessOwnerName);
                                });

                                $("tfoot", "#tblTaskList").show();
                                $(".simple-grid-none-data-wrap").hide();

                                $(".pull-right.page-box.task").cPaging({
                                    totalCount: response.Data.TotalItemCount,
                                    pageNo: response.Data.PageNo,
                                    pageSize: response.Data.PageSize,
                                    callBack: investigation.Investigations.Investigation.Tasks.TaskList,
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
            Files: {

                Display: function (e) {

                    if ($(e).hasClass("icon-down")) {
                        $("#divInvestigationFiles").hide();
                        $(e).removeClass("icon-down")
                        $(e).addClass("icon-up")
                    }
                    else if ($(e).hasClass("icon-up")) {
                        $("#divInvestigationFiles").show();
                        $(e).removeClass("icon-up")
                        $(e).addClass("icon-down")
                    }
                },

                Layout: function () {
                    var data = {
                        pageId: AP_PAGE_ID,
                        investigationNo: $("#Investigation_Basic_InvestigationNo").val()
                    };


                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationFile/List", data, function (response) {
                        if (response.IsSuccess) {
                            $.openLoading();
                            $("#dv_List").empty();
                            $("#dv_List").html(response.Data);

                            investigation.Investigations.Investigation.Files.List();
                            $.closeLoading();
                        }
                    }, true);
                },
                List: function () {
                    var data = {
                        investigationGuid: $("#Investigation_Basic_InvestigationGuid").val(),
                        pageNo: $("#PageNo").val(),
                        pageSize: $("#PageSize").val()
                    };
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationFile/InvestigationFiles", data, function (response) {
                        if (response.IsSuccess) {
                            $.openLoading();
                            $("tbody", "#tblInvestigationFileList").clearRow();
                            if (response.Data.TotalItemCount > 0) {
                                $.each(response.Data.InvestigationFiles, function (i, file) {
                                    $("tbody", "#tblInvestigationFileList").addRow(
                                       "<input type='checkbox' id='chkFileId' name='chkFileId' value=" + file.FileId + ">",
                                        file.UploadingUserName,
                                        file.FileName,
                                        file.UploadingTime == null ? '' : getDate(convertJsonDateToJSDate(file.UploadingTime)),
                                        "<a style='color: #039' href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Files.File.View(" + file.FileId + ",\"" + file.InvestigationGuid + "\",\"" + file.FileName + "\");'><span>查看</span></a>&nbsp;&nbsp;&nbsp;" +
                                        "<a style='color: #039' href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Files.File.Download(\"" + file.FileId + "\");'><span>下载</span></a>"
                                    );
                                });
                                $("tfoot", "#tblInvestigationFileList").show();
                                $(".simple-grid-none-data-wrap.none-investigationfile").hide();

                                $(".pull-right.page-box.investigationfile").cPaging({
                                    totalCount: response.Data.TotalItemCount,
                                    pageNo: response.Data.PageNo,
                                    pageSize: response.Data.PageSize,
                                    callBack: investigation.Investigations.Investigation.Files.List,
                                    callBackArgs: null
                                });

                            } else {
                                $(".simple-grid-none-data-wrap.none-investigationfile").show();
                                $("tfoot", "#tblInvestigationFileList").hide();

                            }
                            investigation.ResetSize();
                            $.closeLoading();
                        }
                    }, true);
                },
                Selected: function (e) {
                    if ($(e).prop('checked') == true) {
                        $.checkbox.all("chkFileId");
                        $.checkbox.all("chkFileAll");

                    } else {
                        $.checkbox.not("chkFileId");
                        $.checkbox.not("chkFileAll");
                    }
                },

                File: {
                    Open: function (investigationGuid) {
                        var data =
                        {
                            investigationGuid: investigationGuid,
                        };
                        var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationFile/FileUpload";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#investigationFileUploadModal').modal({ backdrop: 'static', keyboard: false });
                            $('#investigationFileUploadModal').on('hidden.bs.modal', function () {
                                $("#investigationFileUploadModal").remove();
                            });
                        });
                    },
                    Close: function () {
                        $('#investigationFileUploadModal').modal('hide');
                    },
                    Upload: function (e) {
                        if ($("#flInvestigationFile").val() == '') {
                            $.showModalMessageBox("请选择上传文件.");
                            return false;
                        }

                        $('#uploadForm').ajaxSubmit({
                            success: function (response) {
                                if (response.IsSuccess) {
                                    $.showModalMessageBox("上传成功.");
                                    $.each(response.Data, function (i, f) {

                                        $("#attachments").append("<div  class='margin-top'><span>" + f.FileName + "</span> "
                                            + " <a id='attachmentfile' href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Files.File.DeleteFile(this," + f.FileId + ")'>删除</a> "
                                            + " <a id='attachmentfile' href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Files.File.View(" + f.FileId + ',\"' + f.InvestigationGuid + '\",\"' + f.FileName + "\")'>查看</a> "
                                            + "</div>");
                                    });
                                    $("#help-block").hide()
                                } else {
                                    $("#help-block").show();
                                }
                            }
                        });
                    },
                    FileUpload: function (e) {
                        if ($("#flInvestigationFile").val() == '') {
                            $.showModalMessageBox("请选择上传文件.");
                            return false;
                        }

                        $('#uploadForm').ajaxSubmit({
                            success: function (response) {
                                if (response.IsSuccess) {
                                    investigation.Investigations.Investigation.Files.File.Close();
                                    //investigation.Investigations.Investigation.Files.List();
                                } else {
                                    $.showModalMessageBox("上传失败.");
                                }
                            }
                        });
                    },
                    View: function (investigationFileId, investigationGuid, investigationFileName) {

                        if (investigationFileId == '' || investigationGuid == '' || investigationFileName == '') {
                            $.showModalMessageBox("无调查资料文件.");
                            return false;
                        }

                        var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                        var picfiles = new Array('jpg', 'tif', 'pdf');
                        var extName = investigationFileName.substring(investigationFileName.lastIndexOf('.') + 1, investigationFileName.length);

                        if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                            var path = GV_LS.OfficeOnlineUrl + GV_LS.OnlineUrl + "CaseFiles/CIT/Investigation/" + investigationGuid + "/" + investigationFileName;
                            window.open(path);
                        }
                        else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                            var path = GV_LS.OnlineUrl + "CaseFiles/CIT/Investigation/" + investigationGuid + "/" + investigationFileName;
                            window.open(path);
                        } else {
                            investigation.Investigations.Investigation.Files.File.Download(investigationFileId);
                        }

                        return true;
                    },
                    Download: function (investigationFileId) {
                        window.open(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationFile/InvestigationFileDownload?fileId=" + investigationFileId);
                        return true;
                    },
                    Delete: function (fileIds, functionCallback) {
                        var data = {
                            fileIds: fileIds,
                        };
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationFile/Delete", data, function (response) {
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
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationFile/Delete", data, function (response) {
                            if (response.IsSuccess) {
                                $(e).parent().remove();
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    }
                },
            },
            /*线索*/
            Clues: {
                ClueList: function () {
                    $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/List", function (response) {
                        if (response.IsSuccess) {
                            $("tbody", "#tblClueList").clearRow();
                            if (response.Data.TotalItemCount > 0) {
                                $(".info_inall.layoutfix").show();
                                $.each(response.Data.InvestigationClues, function (i, clue) {

                                    var notarialNoList = Array();
                                    var depositAddressList = Array();

                                    var investigatorNames = clue.InvestigationTask.Basic.InvestigatorName;
                                    if (clue.Basic.InvestigatorNames != '') {
                                        investigatorNames += "," + clue.Basic.InvestigatorNames;
                                    }

                                    if (clue.InvestigationClueEvidenceList != null && clue.InvestigationClueEvidenceList.length > 0) {
                                        $.each(clue.InvestigationClueEvidenceList, function (i, evidence) {
                                            if (evidence.Basic.NotarialNo.length > 0) {
                                                notarialNoList.push(evidence.Basic.NotarialNo);
                                            }
                                            if (evidence.Basic.DepositAddress.length > 0) {
                                                depositAddressList.push(evidence.Basic.DepositAddress);
                                            }
                                        });
                                    }

                                    if (AP_PAGE_ID == "1401004001") {
                                        $("tbody", "#tblClueList").addRow(
                                             "<input type='checkbox' id='chkClueId' name='chkClueId' customerNo=" + clue.Investigation.Basic.Indicter + " clueGuid=" + clue.Basic.ClueGuid + " value=" + clue.Basic.ClueNo + ">",
                                             "<a href='javascript:void(0);' onclick='javascript:investigation.InvestigationClueAudit.View(\"" + clue.Basic.ClueNo + "\");'><span>" + clue.Basic.ClueNo + "</span></a>",
                                             investigatorNames,
                                             clue.Basic.InvestigationDate == null ? '' : getDateTime(convertJsonDateToJSDate(clue.Basic.InvestigationDate)),
                                             clue.Basic.BusinessTypeZh,
                                             clue.Basic.StoreName,
                                             clue.Basic.Address == null || clue.Basic.Address == '' ? "<a target='_blank' href='" + clue.Basic.StoreUrl + ";'><span>" + clue.Basic.StoreUrl + "</span></a>" : clue.Basic.Address,
                                             clue.Basic.StatusName,
                                             clue.Investigation.Basic.IndicterName,
                                             clue.Investigation.Basic.CaseTypeName,
                                             clue.Investigation.Basic.BusinessOwnerName,
                                             clue.Investigation.Basic.CoordinatorName,
                                             notarialNoList.join(),
                                             depositAddressList.join()
                                         );
                                    }
                                    else {
                                        $("tbody", "#tblClueList").addRow(
                                             "<input type='checkbox' id='chkClueId' name='chkClueId'  customerNo=" + clue.Investigation.Basic.Indicter + " clueGuid=" + clue.Basic.ClueGuid + " value=" + clue.Basic.ClueNo + ">",
                                             "<a href='javascript:void(0);' onclick='javascript:investigation.InvestigationClue.View(\"" + clue.Basic.ClueNo + "\");'><span>" + clue.Basic.ClueNo + "</span></a>",
                                             investigatorNames,
                                             clue.Basic.InvestigationDate == null ? '' : getDateTime(convertJsonDateToJSDate(clue.Basic.InvestigationDate)),
                                             clue.Basic.BusinessTypeZh,
                                             clue.Basic.StoreName,
                                             clue.Basic.Address == null || clue.Basic.Address == '' ? "<a target='_blank' href='" + clue.Basic.StoreUrl + ";'><span>" + clue.Basic.StoreUrl + "</span></a>" : clue.Basic.Address,
                                             clue.Basic.StatusName,
                                             clue.Investigation.Basic.IndicterName,
                                             clue.Investigation.Basic.CaseTypeName,
                                             clue.Investigation.Basic.BusinessOwnerName,
                                             clue.Investigation.Basic.CoordinatorName,
                                             notarialNoList.join(),
                                             depositAddressList.join()
                                         );
                                    }
                                });
                                $("tfoot", "#tblClueList").show();
                                $(".simple-grid-none-data-wrap").hide();

                                $(".pull-right.page-box.investigationclue").cPaging({
                                    totalCount: response.Data.TotalItemCount,
                                    pageNo: response.Data.PageNo,
                                    pageSize: response.Data.PageSize,
                                    callBack: investigation.Investigations.Investigation.Clues.ClueList,
                                    callBackArgs: null
                                });
                            } else {
                                $("tfoot", "#tblClueList").hide();
                                $(".simple-grid-none-data-wrap").show();
                            }
                        }
                    });
                },
                ExportAllToExcel: function () {

                    $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListAllExportToExcel", function (response) {
                        if (response.IsSuccess) {
                            window.open(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListExportToExcelDownload?fileName=" + response.Data);
                            $.showModalMessageBox("导出成功.");
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                },
                ExportSelectedToExcel: function () {
          
                    var clueGuids = [];
                    $("input[name='chkClueId']:checked").each(
                        function (i) { clueGuids[i] = $(this).attr("clueGuid"); }
                    );

                    
                    if (clueGuids.length < 1) {
                        $.showModalMessageBox("请选择需要导出的线索.");
                        return false;
                    }

                    var data = {
                        investigationClueGuids: clueGuids,
                    };
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListSelectedExportToExcel", data, function (response) {
                        if (response.IsSuccess) {
                            window.open(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListExportToExcelDownload?fileName=" + response.Data);
                            $.showModalMessageBox("导出成功.");
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                },
                ExportAllToExcelForManifest: function () {

                    $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListAllExportToExcelForManifest", function (response) {
                        if (response.IsSuccess) {
                            window.open(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListExportToExcelDownload?fileName=" + response.Data);
                            $.showModalMessageBox("导出成功.");
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                },
                ExportSelectedToExcelForManifest: function () {

                    var clueGuids = [];
                    $("input[name='chkClueId']:checked").each(
                        function (i) { clueGuids[i] = $(this).attr("clueGuid"); }
                    );


                    if (clueGuids.length < 1) {
                        $.showModalMessageBox("请选择需要导出的线索.");
                        return false;
                    }

                    var data = {
                        investigationClueGuids: clueGuids,
                    };
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListSelectedExportToExcelForManifest", data, function (response) {
                        if (response.IsSuccess) {
                            window.open(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListExportToExcelDownload?fileName=" + response.Data);
                            $.showModalMessageBox("导出成功.");
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                },
                Layout: function () {
                    var data = {
                        investigationTaskNo: $("#InvestigationTask_Basic_TaskNo").val(),
                    };
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/ClueList", data, function (response) {
                        if (response.IsSuccess) {
                            $.openLoading();
                            $("#dv_ClueList").empty();
                            $("#dv_ClueList").html(response.Data);
                            investigation.Investigations.Investigation.Clues.List();
                            $.closeLoading();
                        }
                    }, true);
                },
                List: function () {
                    var data = {
                        investigationTaskNo: $("#InvestigationTask_Basic_TaskNo").val(),
                        pageNo: $("#PageNo").val(),
                        pageSize: $("#PageSize").val()
                    };
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClues", data, function (response) {
                        if (response.IsSuccess) {
                            $("tbody", "#tblInvestigationClueList").clearRow();
                            if (response.Data.TotalItemCount > 0) {
                                $.each(response.Data.InvestigationClues, function (i, clue) {
                                    $("tbody", "#tblInvestigationClueList").addRow(
                                        "<input type='checkbox' id='chkClueId' name='chkClueId' value=" + clue.Basic.ClueNo + ">",
                                        clue.Basic.ClueNo,
                                        clue.Basic.InvestigationDate == null ? '' : getDate(convertJsonDateToJSDate(clue.Basic.InvestigationDate)),
                                        clue.Basic.BusinessTypeZh,
                                        clue.Basic.StoreName,
                                        clue.Basic.Address == null || clue.Basic.Address == '' ? "<a target='_blank' href='" + clue.Basic.StoreUrl + ";'><span>" + clue.Basic.StoreUrl + "</span></a>" : clue.Basic.Address,
                                        clue.Basic.StatusName
                                    );
                                });
                                $("tfoot", "#tblInvestigationClueList").show();
                                $(".simple-grid-none-data-wrap.none-investigationclue").hide();
                                $(".pull-right.page-box.investigationclue").cPaging({
                                    totalCount: response.Data.TotalItemCount,
                                    pageNo: response.Data.PageNo,
                                    pageSize: response.Data.PageSize,
                                    callBack: investigation.Investigations.Investigation.Clues.List,
                                    callBackArgs: null
                                });

                            } else {
                                $(".simple-grid-none-data-wrap.none-investigationclue").show();
                                $("tfoot", "#tblInvestigationClueList").hide();
                            }
                            investigation.ResetSize();
                        }
                    });
                },
                Selected: function (e) {
                    if ($(e).prop('checked') == true) {
                        $.checkbox.all("chkClueId");
                        $.checkbox.all("chkClueAll");

                    } else {
                        $.checkbox.not("chkClueId");
                        $.checkbox.not("chkClueAll");
                    }
                },
                Clue: {
                    View: function (investigationClueNo) {
                        var data =
                        {
                            investigationClueNo: investigationClueNo,
                        };
                        var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/Clue";

                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(".sidebox-content").empty();
                            $(".sidebox-content").append(result);
                            $("#sidebox").show();
                        });

                    },
                    Create: function (investigationTaskNo) {
                        var data = {
                            investigationTaskNo: investigationTaskNo
                        };
                        var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/ClueCreate";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            
                            $(".slide-panel-container").empty();
                            $(".slide-panel-container").append(result);
                            $(".slide-panel-container").addClass("show-panel");
                        });
     
                    },
                    GenerateCase: function (investigationClueNos) {

                        var data = {
                            investigationClueNos: investigationClueNos.join(",")
                        };
                        var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/ClueToCase";
                        //var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/ClueGenerateCaseLitigant";
                        //var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/ClueGenerateCaseCourt";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();

                            $(".slide-panel-container").empty();
                            $(".slide-panel-container").append(result);
                            $(".slide-panel-container").addClass("show-panel");
                        });
                    },
                    checkIntputInvestigationClue:function()
                    {
                        if ($("#InvestigationClue_Basic_StoreName").val() == "")
                        {
                            if ($("#InvestigationClue_Basic_BusinessType").val() == "S_FA") {
                                $.showModalMessageBox("请输入工厂名称.");
                                return false;
                            }
                            else {
                                $.showModalMessageBox("请输入店铺名称.");
                                return false;
                            }
                        }

                        if ($("#InvestigationClue_Basic_BusinessType").val() == "E_WL" && $("#InvestigationClue_Basic_StoreUrl").val() == "") {
                            $.showModalMessageBox("请输入网页链接.");
                            return false;
                        }

                        if ($("#InvestigationClue_Basic_BusinessType").val() == "E_EC" && $("#InvestigationClue_Basic_StoreUrl").val() == "") {
                            $.showModalMessageBox("请输入店铺链接.");
                            return false;
                        }

                        if ($("#InvestigationClue_Basic_HasProduct_0").attr("checked") == "checked")
                        {
                            if ($("#InvestigationClue_Product_ProductName").val() == "") {
                                $.showModalMessageBox("请输入产品名称.");
                                return false;
                            }

                            if ($("#InvestigationClue_Basic_BusinessType").val() == "E_EC" && $("#InvestigationClue_Product_ProductUrl").val() == "") {
                                //电商平台需要输入产品链接
                                $.showModalMessageBox("请输入产品链接.");
                                return false;
                            }
                        }

                        
                        if ($("#InvestigationClue_Product_HasProducer_0").attr("checked") == "checked" && $("a[name='producername']").length == 0)
                        {
                            $.showModalMessageBox("请输入生产商信息.");
                            return false;
                        }

                        return true;
                        
                    },
                    getIntputInvestigationClue : function()
                    {
                        var investigationClue = {};
                        investigationClue.ClueGuid = $("#InvestigationClue_Basic_ClueGuid").val();
                        investigationClue.ClueNo = $("#InvestigationClue_Basic_ClueNo").val();

                        investigationClue.InvestigationNo = $("#InvestigationClue_Basic_InvestigationNo").val();
                        investigationClue.InvestigationTaskNo = $("#InvestigationClue_Basic_InvestigationTaskNo").val();
                        investigationClue.BusinessType = $("#InvestigationClue_Basic_BusinessType").val();
                        investigationClue.ChannelType = $("#InvestigationClue_Basic_ChannelType").val();
                        investigationClue.PlatformName = $("#InvestigationClue_Basic_PlatformName").val();
                        investigationClue.StoreName = $("#InvestigationClue_Basic_StoreName").val();
                        investigationClue.StoreUrl = $("#InvestigationClue_Basic_StoreUrl").val();

                        investigationClue.Province = $("#InvestigationClue_Basic_Province option:selected").attr("data-code");

                        if (investigationClue.Province != '' && investigationClue.Province != null)
                        {
                            investigationClue.ProvinceZh = $("#InvestigationClue_Basic_Province option:selected").text();
                        }
                        investigationClue.City = $("#InvestigationClue_Basic_City option:selected").attr("data-code");

                        if (investigationClue.City != '' && investigationClue.City != null) {
                            investigationClue.CityZh = $("#InvestigationClue_Basic_City option:selected").text();
                        }

                        investigationClue.District = $("#InvestigationClue_Basic_Area option:selected").attr("data-code");
                        if (investigationClue.District != '' && investigationClue.District != null) {
                            investigationClue.DistrictZh = $("#InvestigationClue_Basic_District option:selected").text();
                        }

                        investigationClue.HasProduct = $('input:radio[name="InvestigationClue_Basic_HasProduct"]:checked').val();
                        investigationClue.HasTort = $('input:radio[name="InvestigationClue_Basic_HasTort"]:checked').val();
                        investigationClue.InvestigationDate = $("#InvestigationClue_Basic_InvestigationDate").val();
                        investigationClue.Address = $("#InvestigationClue_Basic_Address").val();
                        investigationClue.Remark = $("#InvestigationClue_Basic_Remark").val();

                        var investigationClueProduct = {};
                        //if ($('input:radio[name="InvestigationClue_Basic_HasProduct"]:checked').val() == "true") {
                            
                            investigationClueProduct.ProductId = $("#InvestigationClue_Product_ProductId").val();
                            investigationClueProduct.ProductName = $("#InvestigationClue_Product_ProductName").val();
                            investigationClueProduct.ProductUrl = $("#InvestigationClue_Product_ProductUrl").val();
                            investigationClueProduct.SaleNum = $("#InvestigationClue_Product_SaleNum").val();
                            investigationClueProduct.LotNo = $("#InvestigationClue_Product_LotNo").val();
                            investigationClueProduct.HasProducer = $('input:radio[name="InvestigationClue_Product_HasProducer"]:checked').val();
                        //}                        

                        var investigators = [];
                        var investigatornames = [];

                        $("a[name='investigatorname']").each(function () {
                            investigators.push($(this).attr("username"));
                            investigatornames.push($(this).attr("userchname"));
                        });

                        investigationClue.Investigators = investigators.join(",");
                        investigationClue.InvestigatorNames = investigatornames.join(",");

                        var investigationClueProducerList = [];
          
                        if ($('input:radio[name="InvestigationClue_Product_HasProducer"]:checked').val() == "true") {
                            $("a[name='producername']").each(function () {
                                
                                var producerJson = $(this).attr("producer");
                                var investigationClueProducer = $.parseJSON(producerJson);
                                investigationClueProducerList.push(investigationClueProducer);
                            });
                        }

                        var investigationClueIndicteeList = []; 
                        $("a[name='indicteename']").each(function () {
                            var indicteeJson = $(this).attr("indictee");
                            var investigationClueIndictee = $.parseJSON(indicteeJson);
                            investigationClueIndicteeList.push(investigationClueIndictee);
                        });

                        var data = {
                            investigationClue: investigationClue,
                            investigationClueProduct: investigationClueProduct,
                            investigationClueIndicteeList: investigationClueIndicteeList,
                            investigationClueProducerList: investigationClueProducerList
                        };

                        return data;
                    
                    },
                    CreateInvestigationClue: function (needToAudit) {
                        try {

                            if (!investigation.Investigations.Investigation.Clues.Clue.checkIntputInvestigationClue()) return false;

                            if (needToAudit) {
                                if ($("#InvestigationClue_Basic_BusinessType").val() == "S_ST"
                                    || $("#InvestigationClue_Basic_BusinessType").val() == "S_FA"
                                    || $("#InvestigationClue_Basic_BusinessType").val() == "S_OT") {
                                    if ($("#InvestigationClue_Basic_Province").val() == '- 请选择 -') {
                                        $.showModalMessageBox("请选择调查省份.");
                                        return false;
                                    }
                                    if ($("#InvestigationClue_Basic_City").val() == '- 请选择 -') {
                                        $.showModalMessageBox("请选择调查城市.");
                                        return false;
                                    }
                                    if ($("#InvestigationClue_Basic_District").val() == '- 请选择 -')

                                        if ($("#InvestigationClue_Basic_Province").val() == '110000'
                                             || $("#InvestigationClue_Basic_Province").val() == '120000'
                                             || $("#InvestigationClue_Basic_Province").val() == '310000'
                                             || $("#InvestigationClue_Basic_Province").val() == '500000'
                                             || $("#InvestigationClue_Basic_Province").val() == '810000'
                                             || $("#InvestigationClue_Basic_Province").val() == '820000'
                                            )
                                        {
                                        }
                                        else
                                        {
                                            $.showModalMessageBox("请选择调查区县.");
                                            return false;
                                        }
                                }

                                if ($("a[name='indicteename']").length == 0) {
                                    $.showModalMessageBox("请输入主体信息.");
                                    return false;
                                }
                            }
      
                            var data = investigation.Investigations.Investigation.Clues.Clue.getIntputInvestigationClue();

                            $.ajaxPostJson(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueCreate", JSON.stringify({ request: data, needToAudit: needToAudit }), function (response) {
                                if (response.IsSuccess) {
                                    $.showModalMessageBox((needToAudit ?"提交成功." : "保存成功"));

                                    $('.slide-panel-container').empty();
                                    $('.slide-panel-container').removeClass('show-panel');

                                    investigation.Investigations.Investigation.Clues.ClueList();
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });

                        } catch (e) {

                        }
                    },
                    UpdateInvestigationClue: function (needToAudit) {
                        
                        try {
                            if (!investigation.Investigations.Investigation.Clues.Clue.checkIntputInvestigationClue()) return false;

                            if (needToAudit) {
                                if ($("a[name='indicteename']").length == 0) {
                                    $.showModalMessageBox("请输入主体信息.");
                                    return false;
                                }
                            }
                            var data = investigation.Investigations.Investigation.Clues.Clue.getIntputInvestigationClue();

                            $.ajaxPostJson(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueUpdate", JSON.stringify({ request: data, needToAudit: needToAudit }), function (response) {
                                if (response.IsSuccess) {
                                    $.showModalMessageBox((needToAudit ? "提交成功." : "保存成功"));

                                    $('.slide-panel-container').empty();
                                    $('.slide-panel-container').removeClass('show-panel');
                                    investigation.Investigations.Investigation.Clues.ClueList();
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });

                        } catch (e) {

                        }
                    },
                    Edit: function (investigationClueNo) {
                        var data = {
                            investigationClueNo: investigationClueNo,
                        };
                        var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/ClueEdit";
                        $.openLoading();
                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(".slide-panel-container").empty();
                            $(".slide-panel-container").append(result);
                            $(".slide-panel-container").addClass("show-panel");
                        });
                    },
                    Delete: function (clueNos) {
                        $.showModalConfirmDialog("确定删除调查线索？", "investigation.Investigations.Investigation.Clues.Clue.DeleteCallBack", clueNos);
                        return true;
                    },
                    DeleteCallBack: function (clueNos) {
                        var data = {
                            clueNos: clueNos,
                        };
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/Delete", data, function (response) {
                            if (response.IsSuccess) {
                                investigation.Investigations.Investigation.Clues.ClueList();
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },
                    ToAudit: function (clueNos) {

                        $.showModalConfirmDialog("确定提交审批？", "investigation.Investigations.Investigation.Clues.Clue.ToAuditCallBack", clueNos);
                        return true;
                    },
                    ToAuditCallBack: function (clueNos) {
                        try {
                            var data = { clueNos: clueNos };

                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueAudit/ToAudit", data, function (response) {
                                if (response.IsSuccess) {

                                    $.showModalMessageBox("提交成功.");

                                    try {
                                        investigation.Investigations.Investigation.Clues.ClueList();
                                    }
                                    catch (e) {
                                    }
                                    try {
                                        investigation.Investigations.Investigation.Clues.List();
                                    }
                                    catch (e) {
                                    }

                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });

                        } catch (e) {

                        }
                    },
                    Audits: {
                        Layout: function () {
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractAudit/ViewContractAuditList", null, function (response) {
                                if (response.IsSuccess) {
                                    $.openLoading();
                                    $("#dv_List").empty();
                                    $("#dv_List").html(response.Data);
                                    contract.Contract.Audits.List();
                                    $.closeLoading();
                                }
                            }, true);
                        },
                        List: function () {
                            var data = {
                                contractId: $("#Contract_ContractBasicInfo_ContractId").val()
                            };

                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractAudit/ContractAudits", data, function (response) {
                                if (response.IsSuccess) {
                                    $.openLoading();
                                    $.each(response.Data, function (i, audit) {
                                        $("tbody", "#tblContractAuditList").addRow(
                                            ++i,
                                            audit.AuditorName,
                                            audit.AuditStatusName,
                                            audit.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(audit.AuditDate)),
                                            audit.AuditContent
                                        );
                                    });

                                    contract.ResetSize();
                                    $.closeLoading();
                                }
                            }, true);
                        },
                        Audit: {
                            ToAudit: function (contractId, isDraft) {
                                var data = {};
                                data["ContractId"] = contractId;

                                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/Contract/ToAudit", data, function (response) {
                                    if (response.IsSuccess) {
                                        if (isDraft) {
                                            contract.Sponsor.DraftList();
                                        } else {
                                            contract.Sponsor.RejectedList();
                                        }

                                        $.showModalMessageBox("提交成功.");

                                    } else {
                                        $.showModalMessageBox(response.Message);
                                    }
                                });
                            },
                            ViewAudit: function (contractId, contractNo) {

                                var data =
                                {
                                    contractId: contractId,
                                    contractNo: contractNo
                                };

                                var url = AP_ROOT + AP_PAGE_ID + "/FCM/ContractAudit/ContractAuditList";
                                $.openLoading();

                                $("<div></div>").load(url, data, function (result) {
                                    $.closeLoading();
                                    $(document.body).append(result);
                                    $('#contractAuditListModal').modal({ backdrop: 'static', keyboard: false });
                                    $('#contractAuditListModal').on('hidden.bs.modal', function () {
                                        $("#contractAuditListModal").remove();
                                    });
                                });

                            },
                            AuditClose: function () {
                                $('#contractAuditListModal').modal('hide');
                            },
                            Open: function (contractId, contractNo) {

                                var data =
                                {
                                    contractId: contractId,
                                    contractNo: contractNo
                                };

                                var url = AP_ROOT + AP_PAGE_ID + "/FCM/ContractAudit/ContractAudit";
                                $.openLoading();

                                $("<div></div>").load(url, data, function (result) {
                                    $.closeLoading();
                                    $(document.body).append(result);
                                    $('#contractAuditModal').modal({ backdrop: 'static', keyboard: false });
                                    $('#contractAuditModal').on('hidden.bs.modal', function () {
                                        $("#contractAuditModal").remove();
                                    });
                                });

                            },
                            Close: function () {
                                $('#contractAuditModal').modal('hide');
                            },
                            Approved: function () {

                                if ($("#InvestigationClue_Basic_AuditNeedMergeCase").val() == 'true' && $("#InvestigationClue_Basic_AuditNeedMergeCaseNo").val().trim() == '') {
                                    $.showModalMessageBox("请输入需要补充取证案号.");
                                    return false;
                                };

                                var data = {
                                    clueNo: $("#InvestigationClue_Basic_ClueNo").val(),
                                    auditRemark: $("#InvestigationClue_Basic_AuditRemark").val(),
                                    auditNeedMergeCase: $("#InvestigationClue_Basic_AuditNeedMergeCase").val(),
                                    auditNeedMergeCaseNo: $("#InvestigationClue_Basic_AuditNeedMergeCaseNo").val()
                                };

                                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueAudit/Approved", data, function (response) {
                                    if (response.IsSuccess) {
                                        $.showModalMessageBox("审批成功.");
                                        investigation.Investigations.Investigation.Clues.ClueList();
                                        investigation.InvestigationClueAudit.Close();
                                    } else {
                                        $.showModalMessageBox(response.Message);
                                    }
                                });
                            },

                            CustomerApproved: function () {

                                var data = {
                                    clueNo: $("#InvestigationClue_Basic_ClueNo").val(),
                                    auditRemark: $("#InvestigationClue_Basic_CustomerAuditRemark").val()
                                };

                                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueAudit/CustomerApproved", data, function (response) {
                                    if (response.IsSuccess) {
                                        $.showModalMessageBox("审批成功.");
                                        investigation.Investigations.Investigation.Clues.ClueList();
                                        investigation.InvestigationClueAudit.Close();
                                    } else {
                                        $.showModalMessageBox(response.Message);
                                    }
                                });
                            },

                            Rejected: function () {

                                var data = {
                                    clueNo: $("#InvestigationClue_Basic_ClueNo").val(),
                                    auditRemark: $("#InvestigationClue_Basic_AuditRemark").val(),
                                    auditNeedMergeCase: false,
                                    auditNeedMergeCaseNo: ""
                                };

                                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueAudit/Rejected", data, function (response) {
                                    if (response.IsSuccess) {
                                        $.showModalMessageBox("审批成功.");
                                        investigation.Investigations.Investigation.Clues.ClueList();
                                        investigation.InvestigationClueAudit.Close();
                                    } else {
                                        $.showModalMessageBox(response.Message);
                                    }
                                });
                            },

                            CustomerRejected: function () {

                                var data = {
                                    clueNo: $("#InvestigationClue_Basic_ClueNo").val(),
                                    auditRemark: $("#InvestigationClue_Basic_CustomerAuditRemark").val()
                                };

                                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueAudit/CustomerRejected", data, function (response) {
                                    if (response.IsSuccess) {
                                        $.showModalMessageBox("审批成功.");
                                        investigation.Investigations.Investigation.Clues.ClueList();
                                        investigation.InvestigationClueAudit.Close();
                                    } else {
                                        $.showModalMessageBox(response.Message);
                                    }
                                });
                            },

                            CreateUpdateCallBack: function () {
                                window.location = AP_ROOT + "REDACTED_ARCHIVE_ONLY";
                            },
                        },
                    },
                    Files: {
                        Layout: function () {
                            var data = {
                                investigationClueGuid: $("#InvestigationClue_Basic_ClueGuid").val()
                            };

                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueFile/List", data, function (response) {
                                if (response.IsSuccess) {
                                    $.openLoading();
                                    $("#dv_ClueFileList").empty();
                                    $("#dv_ClueFileList").html(response.Data);
                                    investigation.Investigations.Investigation.Clues.Clue.Files.List();
                                    $.closeLoading();
                                }
                            }, true);
                        },
                        List: function () {
                            var data = {
                                investigationClueGuid: $("#InvestigationClue_Basic_ClueGuid").val(),
                                pageNo: $("#PageNo").val(),
                                pageSize: $("#PageSize").val()
                            };

                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueFile/InvestigationClueFiles", data, function (response) {
                                if (response.IsSuccess) {
                                    $.openLoading();
                                    $("tbody", "#tblInvestigationClueFileList").clearRow();
                                    if (response.Data.TotalItemCount > 0) {
                                        $.each(response.Data.InvestigationClueFiles, function (i, file) {

                                            $("tbody", "#tblInvestigationClueFileList").addRow(
                                               "<input type='checkbox' id='chkFileId' name='chkFileId' value=" + file.FileId + ">",
                                                file.UploadingUserName,
                                                file.FileName,
                                                file.UploadingTime == null ? '' : getDate(convertJsonDateToJSDate(file.UploadingTime)),
                                                "<a style='color: #039' href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Clues.Clue.Files.File.View(" + file.FileId + ",\"" + file.ClueGuid + "\",\"" + file.FileName + "\");'><span>查看</span></a>&nbsp;&nbsp;&nbsp;" +
                                                "<a style='color: #039' href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Clues.Clue.Files.File.Download(\"" + file.FileId + "\");'><span>下载</span></a>"
                                            );
                                        });

                                        $("tfoot", "#tblInvestigationClueFileList").show();
                                        $(".simple-grid-none-data-wrap.none-investigationcluefile").hide();

                                        $(".pull-right.page-box.InvestigationClueFile").cPaging({
                                            totalCount: response.Data.TotalItemCount,
                                            pageNo: response.Data.PageNo,
                                            pageSize: response.Data.PageSize,
                                            callBack: investigation.Investigations.Investigation.Clues.Clue.Files.List,
                                            callBackArgs: null
                                        });

                                    } else {
                                        $(".simple-grid-none-data-wrap.none-investigationcluefile").show();
                                        $("tfoot", "#tblInvestigationClueFileList").hide();

                                    }
                                    investigation.ResetSize();
                                    $.closeLoading();
                                }
                            }, true);
                        },
                        Selected: function (e) {
                            if ($(e).prop('checked') == true) {
                                $.checkbox.all("chkFileId");
                                $.checkbox.all("chkFileAll");

                            } else {
                                $.checkbox.not("chkFileId");
                                $.checkbox.not("chkFileAll");
                            }
                        },

                        File: {
                            Open: function (investigationClueNo) {
                                var data =
                                {
                                    investigationClueNo: investigationClueNo,
                                };
                                var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueFile/FileUpload";
                                $.openLoading();

                                $("<div></div>").load(url, data, function (result) {
                                    $.closeLoading();
                                    $(document.body).append(result);
                                    $('#investigationClueFileModal').modal({ backdrop: 'static', keyboard: false });
                                    $('#investigationClueFileModal').on('hidden.bs.modal', function () {
                                        $("#investigationClueFileModal").remove();
                                    });
                                });
                            },
                            Close: function () {
                                $('#investigationClueFileModal').modal('hide');
                            },
                            Upload: function (e) {

                                if ($("#flInvestigationClueFile").val() == '') {
                                    $.showModalMessageBox("请选择上传文件.");
                                    return false;
                                }

                                $('#investigationClue').ajaxSubmit({
                                    success: function (response) {
                                        $.showModalMessageBox("上传成功.");
                                        if (response.IsSuccess) {
                                            $.each(response.Data, function (i, f) {
                                                investigation.Investigations.Investigation.Clues.Clue.Files.File.AddIn(f);
                                            });
                                            $("#help-block").hide()
                                        } else {
                                            $("#help-block").show();
                                        }
                                    }
                                });
                            },

                            AddIn:function(f)
                            {
                                $("#attachments").append("<div  class='margin-top'><span>" + f.FileName + "</span> "
                                + "<a id='attachmentfile' href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Clues.Clue.Files.File.DeleteFile(this," + f.FileId + ")'>删除</a></div>");
                            },

                            FileUpload: function (e) {
                                if ($("#flClueFile").val() == '') {
                                    $.showModalMessageBox("请选择上传文件.");
                                    return false;
                                }

                                $('#investigationClue').ajaxSubmit({
                                    success: function (response) {
                                        $.showModalMessageBox("上传成功.");
                                        if (response.IsSuccess) {
                                            investigation.Investigations.Investigation.Clues.Clue.Files.File.Close();
                                            investigation.Investigations.Investigation.Files.List();
                                        } else {
                                            $.showModalMessageBox("上传失败.");
                                        }
                                    }
                                });
                            },
                            ClueFileUpload: function (e) {
                                if ($("#flClueFile").val() == '') {
                                    $.showModalMessageBox("请选择上传文件.");
                                    return false;
                                }

                                $('#investigationClue').ajaxSubmit({
                                    success: function (response) {
                                        $.showModalMessageBox("上传成功.");
                                        if (response.IsSuccess) {
                                            investigation.Investigations.Investigation.Clues.Clue.Files.File.Close();
                                            investigation.Investigations.Investigation.Files.List();
                                        } else {
                                            $.showModalMessageBox("上传失败.");
                                        }
                                    }
                                });
                            },
                            View: function (investigationFileId, investigationGuid, investigationFileName) {

                                if (investigationFileId == '' || investigationFileName == '') {
                                    $.showModalMessageBox("无线索文件.");
                                    return false;
                                }

                                var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                                var picfiles = new Array('jpg', 'tif', 'pdf');
                                var extName = investigationFileName.substring(investigationFileName.lastIndexOf('.') + 1, investigationFileName.length);

                                if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                                    var path = GV_LS.OfficeOnlineUrl + GV_LS.OnlineUrl + "CaseFiles/CIT/InvestigationCule/" + investigationGuid + "/" + investigationFileName;
                                    
                                    window.open(path);
                                }
                                else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                                    var path = GV_LS.OnlineUrl + "CaseFiles/CIT/InvestigationClueFiles/" + investigationGuid + "/" + investigationFileName;
                                    window.open(path);
                                } else {
                                    investigation.Investigations.Investigation.Clues.Clue.Files.File.Download(investigationFileId);
                                }

                                return true;
                            },
                            Download: function (investigationFileId) {
                                window.open(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueFile/InvestigationClueFileDownload?investigationFileId=" + investigationFileId);
                                return true;
                            },
                            Delete: function (fileIds, functionCallback) {
                                var data = {
                                    fileIds: fileIds,
                                };
                                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueFile/Delete", data, function (response) {
                                    if (response.IsSuccess) {
                                        $.showModalMessageBox("删除成功.");

                                        if (functionCallback != null) {
                                            setTimeout(functionCallback(), 200);
                                        }
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
                                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueFile/Delete", data, function (response) {
                                    if (response.IsSuccess) {
                                        $(e).parent().remove();
                                    } else {
                                        $.showModalMessageBox(response.Message);
                                    }
                                });
                            }

                        },
                    },
                    Indictees: {
                        Indictee: {
                            Edit:function(e)
                            {
                                var indicteeStr = $(e).attr("indictee");
                                var indictee = $.parseJSON(indicteeStr);
                                investigation.Investigations.Investigation.Clues.Clue.Indictees.Indictee.Create(indictee);
                            },
                            Create: function (indictee) {
                                var data = {
                                };
                                var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueIndictee/Create";
                                $.openLoading();
                                $("<div></div>").load(url, data, function (result) {
                                    $.closeLoading();
                                    $(document.body).append(result);
                                    $('#investigationClueIndicteeModal').modal({ backdrop: 'static', keyboard: false });
                                    $('#investigationClueIndicteeModal').on('hidden.bs.modal', function () {
                                        $("#investigationClueIndicteeModal").remove();
                                    });

                                    $(document).ready(function () {
                                        if (indictee != null) {
                                            
                                            $("#InvestigationClueIndictee_BusinessNatureType").val(indictee.BusinessNatureType);
                                            $("#InvestigationClueIndictee_IndicteeName").val(indictee.IndicteeName);
                                            $("#InvestigationClueIndictee_BusinessNatureSubType").val(indictee.BusinessNatureSubType);
                                            $("#InvestigationClueIndictee_IndicteeLicenseNo").val(indictee.IndicteeLicenseNo);
                                            $("#InvestigationClueIndictee_LegalRepresentative").val(indictee.LegalRepresentative);
                                            
                                            if (indictee.District != '' && indictee.District != null) {
                                                $('#indictee_district').citys({ code: indictee.District });
                                            }
                                            else if (indictee.City != '' && indictee.City != null) {
                                                $('#indictee_district').citys({ code: indictee.City });
                                            }
                                            else if (indictee.Province != '' && indictee.Province != null) {
                                                $('#indictee_district').citys({ code: indictee.Province });
                                            }
                                             
                                            $("#InvestigationClueIndictee_Address").val(indictee.Address);

                                            initBusinessNatureType();
                                        }
                                        else {
                                            $('#indictee_district').citys();
                                        }
                                    });

                                });
                            },
                            CreateUpdate: function (callBackFunc) {

                                var indictee = {};

                                if ($("#InvestigationClueIndictee_IndicteeName").val() == "")
                                {
                                    $.showModalMessageBox("请输入主体名称.");
                                    return false;
                                }

                                if ($("#InvestigationClueIndictee_BusinessNatureType").val() == "P" && $("#InvestigationClueIndictee_IndicteeName").val() == "")
                                {
                                    $.showModalMessageBox("请输入身份证号.");
                                    return false;
                                }
                                else if ($("#InvestigationClueIndictee_BusinessNatureType").val() == "E" && $("#InvestigationClueIndictee_IndicteeName").val() == "") {
                                    $.showModalMessageBox("请输入统一社会信用代码.");
                                }
                                else if ($("#InvestigationClueIndictee_BusinessNatureType").val() == "I" && $("#InvestigationClueIndictee_IndicteeName").val() == "") {
                                    $.showModalMessageBox("请输入 经营者.");
                                }
                        
                                if ($("#InvestigationClueIndictee_Address").val() ==  "") {
                                    $.showModalMessageBox("请输入工商地址.");
                                    return false;
                                }

                                indictee.BusinessNatureType = $("#InvestigationClueIndictee_BusinessNatureType").val();
                                indictee.IndicteeName = $("#InvestigationClueIndictee_IndicteeName").val();
                                indictee.BusinessNatureSubType = $("#InvestigationClueIndictee_BusinessNatureSubType").val();
                                indictee.IndicteeLicenseNo = $("#InvestigationClueIndictee_IndicteeLicenseNo").val();
                                indictee.LegalRepresentative = $("#InvestigationClueIndictee_LegalRepresentative").val();
            
                                indictee.Province = $("#InvestigationClueIndictee_Province option:selected").attr("data-code");

                                if (indictee.Province != '') {
                                    indictee.ProvinceZh = $("#InvestigationClueIndictee_Province option:selected").text();
                                }
                                indictee.City = $("#InvestigationClueIndictee_City option:selected").attr("data-code");

                                if (indictee.City != '') {
                                    indictee.CityZh = $("#InvestigationClueIndictee_City option:selected").text();
                                }

                                indictee.District = $("#InvestigationClueIndictee_District option:selected").attr("data-code");
                                if (indictee.District != '') {
                                    indictee.DistrictZh = $("#InvestigationClueIndictee_District option:selected").text();
                                }

                                indictee.Address = $("#InvestigationClueIndictee_Address").val();
                                if (callBackFunc != null) {
                                    callBackFunc(indictee);
                                }

                                return true;
                            },
                            AddIn: function (indictee) {

                                var existsIndictee = false;

                                if ($("a[name='indicteename']").length > 0) {
                                    $("a[name='indicteename']").each(function () {
                                        if ($(this).attr("indicteename") == indictee.IndicteeName) {
                                            $(this).parent().remove();
                                            return true;
                                        }
                                    });
                                }
 
                                var indicteeStr = JSON.stringify(indictee);
                                var $tag = $("<span class='tag label label-info'>"
                                                + "<a name='indicteename' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                                + "  indicteename='" + indictee.IndicteeName + "'"
                                                + "  indictee='" + indicteeStr + "'"
                                                + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);' onclick=javascript:investigation.Investigations.Investigation.Clues.Clue.Indictees.Indictee.Edit(this);'" + "' >" + indictee.IndicteeName + "</a>"
                                                + "<span class='indicteeremove' data-role='remove'></span>"
                                            + "</span>");

                                $("#InvestigationClue_Indictee_Input").before($tag);
                                $tag.after(' ');
                                $("#InvestigationClue_Indictee_Input").blur();
                                
                                $('#investigationClueIndicteeModal').modal('hide');

                            },
                            Remove: function (e) {
                                $(e).parent().remove();
                            },
                        }
                    },
                    Producers: {
                        Producer: {
                            Edit: function (e) {
                                
                                var producerStr = $(e).attr("producer");
                                var producer = $.parseJSON(producerStr);
                                investigation.Investigations.Investigation.Clues.Clue.Producers.Producer.Create(producer);
                            },

                            Create: function (producer) {
                                
                                var data = {};
                                var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueProducer/Create";
                                $.openLoading();
                                $("<div></div>").load(url, data, function (result) {
                                    
                                    $.closeLoading();
                                    $(document.body).append(result);
                                    $('#investigationClueProducerModal').modal({ backdrop: 'static', keyboard: false });
                                    $('#investigationClueProducerModal').on('hidden.bs.modal', function () {
                                        $("#investigationClueProducerModal").remove();
                                    });

                                    $(document).ready(function () {
                                        if (producer != null) {
                                            $("#InvestigationClueProducer_ProducerName").val(producer.ProducerName);
                                            $("#InvestigationClueProducer_Address").val(producer.Address);

                                            if (producer.District != '' && producer.District !=null) {
                                                $('#producer_district').citys({ code: producer.District });
                                            }
                                            else if (producer.City != '' && producer.City != null) {
                                                $('#producer_district').citys({ code: producer.City });
                                            }
                                            else if (producer.Province != '' && producer.Province != null) {
                                                $('#producer_district').citys({ code: producer.Province });
                                            }
                                        }
                                        else {
                                            $('#indictee_district').citys();
                                        }
                                    });
                                });
                            },

                            CreateUpdate: function (callBackFunc) {

                                if ($("#InvestigationClueProducer_ProducerName").val() == "") {
                                    $.showModalMessageBox("请输入生产商.");
                                    return false;
                                }

                                var producer = {};

                                producer.ProducerName = $("#InvestigationClueProducer_ProducerName").val();

                                producer.Province = $("#InvestigationClueProducer_Province option:selected").attr("data-code");
                                if (producer.Province != '') {
                                    producer.ProvinceZh = $("#InvestigationClueProducer_Province option:selected").text();
                                }
                                producer.City = $("#InvestigationClueProducer_City option:selected").attr("data-code");
                                if (producer.City != '') {
                                    producer.CityZh = $("#InvestigationClueProducer_City option:selected").text();
                                }

                                producer.District = $("#InvestigationClueProducer_District option:selected").attr("data-code");
                                if (producer.District != '') {
                                    producer.DistrictZh = $("#InvestigationClueProducer_District option:selected").text();
                                }
             
                                producer.Address = $("#InvestigationClueProducer_Address").val();

                                if (callBackFunc != null) {
                                    callBackFunc(producer);
                                }

                                return true;
                            },

                            AddIn: function (producer) {

                                if ($("a[name='producername']").length > 0) {
                                    $("a[name='producername']").each(function () {
                                        if ($(this).attr("producername") == producer.ProducerName) {
                                            $(this).parent().remove();
                                            return true;
                                        }
                                    });
                                }

                                var producerStr = JSON.stringify(producer);

                                var $tag = $("<span class='tag label label-info'>"
                                                + "<a name='producername' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                                + " producername='" + producer.ProducerName + "'"
                                                + " producer='" + producerStr + "'"
                                                + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);' onclick=javascript:investigation.Investigations.Investigation.Clues.Clue.Producers.Producer.Edit(this);'" + "' >" + producer.ProducerName + "</a>"
                                                + "<span class='producerremove' data-role='remove'></span>"
                                            + "</span>");

                                $("#InvestigationClue_Producer_Input").before($tag);
                                $tag.after(' ');
                                $("#InvestigationClue_Producer_Input").blur();
                                $('#investigationClueProducerModal').modal('hide');
                            },
                            Remove: function (e) {
                                $(e).parent().remove();
                            },
                        }
                    },
                    Investigators: {
                        Investigator: {
                            AddIn: function (username, userchname) {
                                var existsUser = false;
                                //if ($("a[name='investigatorname']").length > 0) {
                                //    return false;
                                //}

                                $("a[name='investigatorname']").each(function () {
                                    if ($(this).attr("username") == username) {
                                        existsUser = true;
                                        return true;
                                    }
                                });

                                //重复

                                if (existsUser) return true;

                                var $tag = $("<span class='tag label label-info'>"
                                                + "<a name='investigatorname' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                                + " username='" + username + "'"
                                                + " userchname='" + userchname + "'"
                                                + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);'   data-original-title=" + userchname + " '>" + userchname + "</a>"
                                                + "<span class='userremove' data-role='remove'></span>"
                                            + "</span>");

                                $("#InvestigationClue_Investigator_Input").before($tag);
                                $tag.after(' ');

                            },
                            Remove: function (e) {
                                $(e).parent().remove();
                            },
                        }
                    },
                },
            }, 
           
            Evidences: {
                Evidence: {
                    Create: function (investigationClueNo) {
                        var data = {
                            investigationClueNo: investigationClueNo
                        };
                        var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueEvidence/Create";
                        $.openLoading();
                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#investigationClueEvidenceModal').modal({ backdrop: 'static', keyboard: false });
                            $('#investigationClueEvidenceModal').on('hidden.bs.modal', function () {
                                $("#investigationClueEvidenceModal").remove();
                            });
                        });
                    },
                    MultiCreate: function (investigationClueNo) {
                        var data = {
                            investigationClueNo: investigationClueNo
                        };
                        var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueEvidence/MultiCreate";
                        $.openLoading();
                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#investigationClueEvidenceModal').modal({ backdrop: 'static', keyboard: false });
                            $('#investigationClueEvidenceModal').on('hidden.bs.modal', function () {
                                $("#investigationClueEvidenceModal").remove();
                            });
                        });
                    },
                    Edit: function (evidenceGuid) {
                        var data = {
                            evidenceGuid: evidenceGuid
                        };
                        var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueEvidence/Edit";
                        $.openLoading();
                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#investigationClueEvidenceModal').modal({ backdrop: 'static', keyboard: false });
                            $('#investigationClueEvidenceModal').on('hidden.bs.modal', function () {
                                $("#investigationClueEvidenceModal").remove();
                            });
                        });
                    },
                    Delete: function (evidenceGuid) {
                        $.showModalConfirmDialog("确定删除取证信息？", "investigation.Investigations.Investigation.Evidences.Evidence.DeleteCallBack", evidenceGuid);
                        return true;
                    },

                    DeleteCallBack: function (evidenceGuid) {
                        var data = {
                            evidenceGuid: evidenceGuid,
                        };
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueEvidence/Delete", data, function (response) {
                            if (response.IsSuccess) {
                                investigation.Investigations.Investigation.Evidences.List();
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },

                    CreateUpdate: function (isSubmit) {
                        try {

                            if ($("#InvestigationClueEvidence_Basic_NotarialNo").val() == '') {
                                $.showModalMessageBox("请输入证书号码.");
                                $("#InvestigationClueEvidence_Basic_NotarialNo").focus();
                                return false;
                            }

                            //if ($("#InvestigationClueEvidence_Basic_EvidenceDate").val() == '') {
                            //    $.showModalMessageBox("请输入取证时间.");
                            //    $("#InvestigationClueEvidence_Basic_EvidenceDate").focus();
                            //    return false;
                            //}

                            if ($("#InvestigationClueEvidence_Basic_NotaryOrganization").val() == '') {
                                $.showModalMessageBox("请输入取证机构.");
                                $("#InvestigationClueEvidence_Basic_NotaryOrganization").focus();
                                return false;
                            }


                            //if ($("#InvestigationClueEvidence_Basic_DepositAddress").val() == '') {
                            //    $.showModalMessageBox("请输入证物存放地点.");
                            //    $("#InvestigationClueEvidence_Basic_DepositAddress").focus();
                            //    return false;
                            //}

                            //if ($("#InvestigationClueEvidence_Basic_NotarialObtainDate").val() == '') {
                            //    $.showModalMessageBox("请输入落款时间.");
                            //    $("#InvestigationClueEvidence_Basic_NotarialObtainDate").focus();
                            //    return false;
                            //}

                            $.openLoading();
                            $('#investigationClueEvidence').ajaxSubmit({
                                success: function (response) {
                                    $.closeLoading();
                                    if (response.IsSuccess) {
                                        $('#investigationClueEvidenceModal').modal('hide');
                                        $.showModalMessageBox("完成取证.");
                                        investigation.Investigations.Investigation.Evidences.List();
                                        return true;
                                    } else {
                                        $.showModalMessageBox(response.Message);
                                        return false;
                                    }
                                }
                            });

                        } catch (e) {

                        }
                    },
                    MultiCreateUpdate: function (isSubmit) {
                        try {
                       
                            var clueGuids = [];
                            $("input[name='chkClueId']:checked").each(
                                function (i) { clueGuids[i] = $(this).attr("clueguid"); }
                            );
                            
                            if (clueGuids.length < 1) {
                                $.showModalMessageBox("请选择线索.");
                                return false;
                            }

                            if ($("#InvestigationClueEvidence_Basic_EvidenceDate").val() == '') {
                                $.showModalMessageBox("请输入取证时间.");
                                $("#InvestigationClueEvidence_Basic_EvidenceDate").focus();
                                return false;
                            }

                            if ($("#InvestigationClueEvidence_Basic_NotaryOrganization").val() == '') {
                                $.showModalMessageBox("请输入取证机构.");
                                $("#InvestigationClueEvidence_Basic_NotaryOrganization").focus();
                                return false;
                            }

                            var data = {
                                investigationClueGuids: clueGuids,
                                evidenceDate: $("#InvestigationClueEvidence_Basic_EvidenceDate").val(),
                                notaryOrganization: $("#InvestigationClueEvidence_Basic_NotaryOrganization").val(),
                                notarialNo: $("#InvestigationClueEvidence_Basic_NotarialNo").val()
                            };
                            
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueEvidence/MultiCreateUpdate", data, function (response) {
                                if (response.IsSuccess) {
                                    $('#investigationClueEvidenceModal').modal('hide');
                                    $.showModalMessageBox("取证完成,后续请补充证据文件及公证书号.");
                                    investigation.Investigations.Investigation.Evidences.List();
                                    return true;
                                } else {
                                    $.showModalMessageBox(response.Message);
                                    return false;
                                }
                            }, true);

                        } catch (e) {

                        }
                    },
                    AddIn: {
                        FileUpload: function () {
                            if ($("#flZip").val() == '') {
                                $.showModalMessageBox("请选择上传的文件.");
                                return false;
                            }
                            $("#uploadingForm").attr("action", AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueEvidence/InvestigationClueEvidenceAddInFileUpload");

                            $.openLoading();

                            $('#uploadingForm').ajaxSubmit({
                                success: function (response) {
                                    $.closeLoading();
                                    if (response.IsSuccess) {
                                        $.showModalMessageBox("上传成功.");
                                        $("#txtPrimaryFile").val(response.Data.PrimaryFileName);
                                        
                                        investigation.Investigations.Investigation.Evidences.Evidence.AddIn.List(response.Data.InvestigationClues);

                                    } else {
                                        $.showModalMessageBox(response.Message);
                                    }
                                }
                            });
                            return true;
                        },
                        List: function (investigationClues) {
                            $("tbody", "#tblEvidenceList").clearRow();
                            if (investigationClues.length > 0) {
                                $.each(investigationClues, function (i, clue)
                                {
                                    if (clue.InvestigationClueEvidenceList != null && clue.InvestigationClueEvidenceList.length > 0) {
                                        $("tbody", "#tblEvidenceList").addRow(
                                                "<input type='checkbox' id='chkClueId' name='chkClueId'  customerNo=" + clue.Investigation.Basic.Indicter
                                                + " evidenceGuid='" + clue.InvestigationClueEvidenceList[0].Basic.EvidenceGuid
                                                + "' notarialNo='" + clue.InvestigationClueEvidenceList[0].Basic.NotarialNo
                                                + "' depositAddress='" + clue.InvestigationClueEvidenceList[0].Basic.DepositAddress
                                                + "' warehouseNo='" + clue.InvestigationClueEvidenceList[0].Basic.WarehouseNo
                                                + "' storageLocationNo='" + clue.InvestigationClueEvidenceList[0].Basic.StorageLocationNo
                                                + "' warehouseName='" + clue.InvestigationClueEvidenceList[0].Basic.WarehouseName
                                                + "' invoiceno='" + clue.InvestigationClueEvidenceList[0].Basic.InvoiceNo
                                                + "' value=" + clue.Basic.ClueNo + ">",
                                                "<a href='javascript:void(0);' onclick='javascript:investigation.InvestigationClue.View(\"" + clue.Basic.ClueNo + "\");'><span>" + clue.Basic.ClueNo + "</span></a>",
                                                clue.InvestigationTask.Basic.InvestigatorName,
                                                clue.Basic.InvestigationDate == null ? '' : getDate(convertJsonDateToJSDate(clue.Basic.InvestigationDate)),
                                                clue.Basic.BusinessTypeZh,
                                                clue.Basic.StoreName,
                                                clue.Basic.Address,
                                                clue.InvestigationClueEvidenceList[0].Basic.NotarialNo,
                                                clue.InvestigationClueEvidenceList[0].Basic.DepositAddress,
                                                clue.InvestigationClueEvidenceList[0].Basic.InvoiceNo
                                            );
                                    }
                                    else {

                                        $('#tblEvidenceList>tbody>tr:last').after("<tr><td colspan='9'><span id='message'>" + clue.Basic.ClueNo + "_线索未取证.</span></td></tr>");
                                    }
                                });

                            } else {
                                $('#tblEvidenceList>tbody>tr:last').after("<tr><td colspan='9'><span id='message'>文件格式不正确.</span></td></tr>");
                            }
                        },
                        In: function () {
                            var investigationClueGuids = $.checkbox.vals("chkClueId");
                            if (investigationClueGuids.length == 0) {
                                $.showModalMessageBox("请选择取证文件.");
                                return;
                            }

                            var j = 0;
                            var result = true;
                            var evidenceAddIns = new Array();

                            $("#tblEvidenceList tbody tr").each(function (i, e) {
                                if ($(e).css("display") != 'none') {
                                    if ($(e).find("#chkClueId").prop('checked') == true) {
                                        if ($(e).find("#chkClueId").val() == '') {
                                            result = false;
                                            $.showModalMessageBox("第" + (i + 1) + "行，文件错误，请重新选择.");
                                            return false;
                                        }

                                        var evidenceAddIn = {
                                            EvidenceGuid: $(e).find("#chkClueId").attr("evidenceGuid"),
                                            NotarialNo: $(e).find("#chkClueId").attr("notarialno"),
                                            DepositAddress: $(e).find("#chkClueId").attr("depositaddress"),
                                            StorageLocationNo: $(e).find("#chkClueId").attr("storageLocationNo"),
                                            WarehouseNo: $(e).find("#chkClueId").attr("warehouseNo"),
                                            WarehouseName: $(e).find("#chkClueId").attr("warehouseName"),
                                            InvoiceNo: $(e).find("#chkClueId").attr("invoiceno"),
                                        };

                                        evidenceAddIns.push(evidenceAddIn);
                                        j++;
                                    }
                                }
                            });

                            if (result == true) {
                                $.ajaxPostJson(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueEvidence/InvestigationClueEvidenceAddInFileIn", JSON.stringify({ evidenceAddIns: evidenceAddIns, primaryFileName: $("#txtPrimaryFile").val() }), function (response) {
                                    if (response.IsSuccess) {
                                        $.showModalMessageBox("导入成功.");
                                    }
                                    else {
                                        $.showModalMessageBox(response.Message);
                                    }
                                });
                            }
                        },
                    },
                    Files: {
                        Layout: function (evidenceGuid) {
                            var data = {};
                            var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueEvidenceFile/List";
                            $.openLoading();
                            $("<div></div>").load(url, data, function (result) {
                                $.closeLoading();
                                $(document.body).append(result);
                                investigation.Investigations.Investigation.Evidences.Evidence.Files.List(evidenceGuid);

                                $('#investigationClueEvidenceFileModal').modal({ backdrop: 'static', keyboard: false });
                                $('#investigationClueEvidenceFileModal').on('hidden.bs.modal', function () {
                                    $("#investigationClueEvidenceFileModal").remove();
                                });
                            });
                        },
                        List: function (evidenceGuid) {
                            var data = {
                                evidenceGuid: evidenceGuid,
                                pageNo: $("#PageNo").val(),
                                pageSize: $("#PageSize").val()
                            };

                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueEvidenceFile/Files", data, function (response) {
                                if (response.IsSuccess) {
                                    $.openLoading();
                                    $("tbody", "#tblInvestigationClueEvidenceFileList").clearRow();
                                    if (response.Data.TotalItemCount > 0) {
                                        $.each(response.Data.InvestigationClueFiles, function (i, file) {
                                            $("tbody", "#tblInvestigationClueEvidenceFileList").addRow(
                                                file.UploadingUserName,
                                                file.FileTypeName,
                                                file.FileName,
                                                file.UploadingTime == null ? '' : getDate(convertJsonDateToJSDate(file.UploadingTime)),
                                                "<a style='color: #039' href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Evidences.Evidence.Files.File.View(" + file.FileId + ",\"" + file.ClueGuid + "\",\"" + file.FileName + "\");'><span>查看</span></a>&nbsp;&nbsp;&nbsp;" +
                                                "<a style='color: #039' href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Evidences.Evidence.Files.File.Download(\"" + file.FileId + "\");'><span>下载</span></a>&nbsp;&nbsp;&nbsp;" +
                                                "<a style='color: #039' href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Evidences.Evidence.Files.File.Delete(\"" + file.FileId + "\",investigation.Investigations.Investigation.Evidences.Evidence.Files.List);'><span>删除</span></a>"
                                            );
                                        });

                                        $("tfoot", "#tblInvestigationClueEvidenceFileList").show();
                                        $(".simple-grid-none-data-wrap.none-investigationclueevidencefile").hide();

                                        $(".pull-right.page-box.investigationclueevidencefile").cPaging({
                                            totalCount: response.Data.TotalItemCount,
                                            pageNo: response.Data.PageNo,
                                            pageSize: response.Data.PageSize,
                                            callBack: investigation.Investigations.Investigation.Clues.Clue.Files.List,
                                            callBackArgs: null
                                        });

                                    } else {
                                        $(".simple-grid-none-data-wrap.none-investigationclueevidencefile").show();
                                        $("tfoot", "#tblInvestigationClueEvidenceFileList").hide();

                                    }
                                    investigation.ResetSize();
                                    $.closeLoading();
                                }
                            }, true);
                        },

                        FileList: function (investigationClues) {
                            $("tbody", "#tblEvidenceFileList").clearRow();

                            if (investigationClues.length > 0) {
                                $.each(investigationClues, function (i, c) {
                                    $("tbody", "#tblEvidenceFileList").addRow(
                                          "<input type='checkbox' Id='chkInvestigationClueEvidenceId' name='chkInvestigationClueEvidenceId' class='ng-pristine ng-valid' value='" + c.InvestigationClueEvidenceList[0].Basic.EvidenceId + "'>"
                                          + "<span id='EvidenceGuid' style='display:none' >" + c.InvestigationClueEvidenceList[0].Basic.EvidenceGuid + "</span>"
                                          + "<span id='EvidenceFileName' style='display:none' >" + c.InvestigationClueEvidenceList[0].Basic.FileName + "</span>",
                                          c.InvestigationClueEvidenceList[0].Basic.FileName,
                                          c.InvestigationClueEvidenceList[0].Basic.NotarialNo,
                                          c.InvestigationClueEvidenceList[0].Basic.InvoiceNo,
                                          c.InvestigationClueEvidenceList[0].Basic.EvidenceDate == null ? '' : getDate(convertJsonDateToJSDate(c.InvestigationClueEvidenceList[0].Basic.EvidenceDate)),
                                          c.InvestigationClueEvidenceList[0].Basic.NotaryOrganization,
                                          c.InvestigationClueEvidenceList[0].Basic.NotarialObtainDate == null ? '' : getDate(convertJsonDateToJSDate(c.InvestigationClueEvidenceList[0].Basic.NotarialObtainDate)),
                                          "<a href='javascript:void(0);' onclick='javascript:investigation.InvestigationClue.View(\"" + c.Basic.ClueNo + "\");'><span>" + c.Basic.ClueNo + "</span></a>",
                                          c.Basic.BusinessOwnerName,                                  
                                          c.Basic.StoreName,
                                          c.Investigation.Basic.IndicterName
                                      );
                                });

                            } else {
                                $('#tblEvidenceFileList>tbody>tr:last').after("<tr><td colspan='11'><span id='message'>文件未匹配到线索号，请确认上传文件正确.</span></td></tr>");
                            }
                        },

                        File: {
                            Open: function (investigationClueNo) {
                                var data =
                                {
                                    investigationClueNo: investigationClueNo,
                                };
                                var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueFile/FileUpload";
                                $.openLoading();

                                $("<div></div>").load(url, data, function (result) {
                                    $.closeLoading();
                                    $(document.body).append(result);
                                    $('#investigationClueFileModal').modal({ backdrop: 'static', keyboard: false });
                                    $('#investigationClueFileModal').on('hidden.bs.modal', function () {
                                        $("#investigationClueFileModal").remove();
                                    });
                                });
                            },
                            Close: function () {
                                $('#investigationClueFileModal').modal('hide');
                            },
                            Upload: function (e) {
                                if ($("#flClueFile").val() == '') {
                                    $.showModalMessageBox("请选择上传文件.");
                                    return false;
                                }

                                $('#investigationClue').ajaxSubmit({
                                    success: function (response) {
                                        $.showModalMessageBox("上传成功.");
                                        if (response.IsSuccess) {
                                            $.each(response.Data, function (i, f) {
                                                $("#attachments").append("<div  class='margin-top'><span>" + f.FileName + "</span> <a id='attachmentfile' href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Files.File.Delete(this," + f.FileId + ")'>删除</a></div>");
                                            });
                                            $("#help-block").hide()
                                        } else {
                                            $("#help-block").show();
                                        }
                                    }
                                });
                            },
                            FileUpload: function (e) {
                                if ($("#flClueFile").val() == '') {
                                    $.showModalMessageBox("请选择上传文件.");
                                    return false;
                                }

                                $('#investigationClue').ajaxSubmit({
                                    success: function (response) {
                                        $.showModalMessageBox("上传成功.");
                                        if (response.IsSuccess) {
                                            investigation.Investigations.Investigation.Files.List();
                                            investigation.Investigations.Investigation.Files.File.Close();
                                        } else {
                                            $.showModalMessageBox("上传失败.");
                                        }
                                    }
                                });
                            },
                            View: function (investigationFileId, investigationNo, investigationFileName) {

                                if (investigationFileId == '' || investigationFileName == '') {
                                    $.showModalMessageBox("无线索文件.");
                                    return false;
                                }

                                var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                                var picfiles = new Array('jpg', 'tif', 'pdf');
                                var extName = investigationFileName.substring(investigationFileName.lastIndexOf('.') + 1, investigationFileName.length);

                                if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                                    var path = GV_LS.OfficeOnlineUrl + GV_LS.OnlineUrl + "CaseFiles/CIT/InvestigationClueFiles/" + investigationNo + "/" + investigationFileName;
                                    window.open(path);
                                }
                                else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                                    var path = GV_LS.OnlineUrl + "CaseFiles/CIT/InvestigationClueFiles/" + investigationNo + "/" + investigationFileName;
                                    window.open(path);
                                } else {
                                    investigation.Investigations.Investigation.Clues.Clue.Files.File.Download(investigationFileId);
                                }

                                return true;
                            },
                            Download: function (investigationFileId) {
                                window.open(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueEvidenceFile/InvestigationClueEvidenceFileDownload?fileId=" + investigationFileId);
                                return true;
                            },
                            Delete: function (fileIds, functionCallback) {
                                var data = {
                                    fileIds: fileIds,
                                };


                                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueEvidenceFile/Delete", data, function (response) {
                                    if (response.IsSuccess) {
                                        $.showModalMessageBox("删除成功.");


                                        if (functionCallback != null) {
                                            setTimeout(functionCallback(), 200);
                                        }
                                    } else {
                                        $.showModalMessageBox(response.Message);
                                    }
                                });
                            },

                            InUpload: function () {
                                if ($("#flZip").val() == '') {
                                    $.showModalMessageBox("请选择上传的文件.");
                                    return false;
                                }
                                $("#uploadingForm").attr("action", AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueEvidenceFile/InvestigationClueEvidenceFileInUpload");

                                $.openLoading();

                                $('#uploadingForm').ajaxSubmit({
                                    success: function (response) {
                                        $.closeLoading();
                                        if (response.IsSuccess) {
                                            $.showModalMessageBox("上传成功.");
                                            $("#txtPrimaryFile").val(response.Data.PrimaryFileName);
                                            
                                            investigation.Investigations.Investigation.Evidences.Evidence.Files.FileList(response.Data.InvestigationClues);

                                        } else {
                                            $.showModalMessageBox(response.Message);
                                        }
                                    }
                                });
                                return true;
                            },

                            In: function () {
                                var investigationClueEvidenceIds = $.checkbox.vals("chkInvestigationClueEvidenceId");
                                if (investigationClueEvidenceIds.length == 0) {
                                    $.showModalMessageBox("请选择取证文件.");
                                    return;
                                }
                                
                                var j = 0;
                                var result = true;

                                var invoiceId = '';
                                var evidenceFiles = new Array();

                                $("#tblEvidenceFileList tbody tr").each(function (i, e) {

                                    if ($(e).css("display") != 'none') {
                                        if ($(e).find("#chkInvestigationClueEvidenceId").prop('checked') == true) {

                                            if ($(e).find("#chkInvestigationClueEvidenceId").val() == '') {
                                                result = false;
                                                $.showModalMessageBox("第" + (i + 1) + "行，文件错误，请重新选择.");
                                                return false;
                                            }
 
                                            var evidenceFile = {
                                                EvidenceId :  $(e).find("#EvidenceId").text(),
                                                EvidenceGuid: $(e).find("#EvidenceGuid").text(),
                                                FileName : $(e).find("#EvidenceFileName").text()
                                            };

                                            evidenceFiles.push(evidenceFile);
                                            j++;
                                        }
                                    }
                                });

                                
                                //var data = {
                                //    evidenceFiles: evidenceFiles,
                                //    primaryFileName: $("#txtPrimaryFile").val()
                                //};

                                if (evidenceFiles.length == 0)
                                {
                                    $.showModalMessageBox("请选择取证文件.");
                                }

                                if (result == true) {
                                    $.ajaxPostJson(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueEvidenceFile/InvestigationClueEvidenceFileImport", JSON.stringify({ evidenceFiles: evidenceFiles, primaryFileName: $("#txtPrimaryFile").val() }), function (response) {
                                        if (response.IsSuccess) {
                                            $.showModalMessageBox("导入成功.");
                                        }
                                        else {
                                            $.showModalMessageBox(response.Message);
                                        }
                                    });
                                }
                            },
                        },

                        InvoiceFile: {

                            Upload: function () {
                                if ($("#flZip").val() == '') {
                                    $.showModalMessageBox("请选择上传的文件.");
                                    return false;
                                }
                                $("#uploadingForm").attr("action", AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueEvidenceFile/InvestigationClueEvidenceInvoiceFileInUpload");

                                $.openLoading();

                                $('#uploadingForm').ajaxSubmit({
                                    success: function (response) {
                                        $.closeLoading();
                                        if (response.IsSuccess) {
                                            $.showModalMessageBox("上传成功.");
                                            $("#txtPrimaryFile").val(response.Data.PrimaryFileName);

                                            investigation.Investigations.Investigation.Evidences.Evidence.Files.FileList(response.Data.InvestigationClues);

                                        } else {
                                            $.showModalMessageBox(response.Message);
                                        }
                                    }
                                });
                                return true;
                            },

                            In: function () {
                                var investigationClueEvidenceIds = $.checkbox.vals("chkInvestigationClueEvidenceId");
                                if (investigationClueEvidenceIds.length == 0) {
                                    $.showModalMessageBox("请选择取证文件.");
                                    return;
                                }

                                var j = 0;
                                var result = true;

                                var invoiceId = '';
                                var evidenceFiles = new Array();

                                $("#tblEvidenceFileList tbody tr").each(function (i, e) {

                                    if ($(e).css("display") != 'none') {
                                        if ($(e).find("#chkInvestigationClueEvidenceId").prop('checked') == true) {

                                            if ($(e).find("#chkInvestigationClueEvidenceId").val() == '') {
                                                result = false;
                                                $.showModalMessageBox("第" + (i + 1) + "行，文件错误，请重新选择.");
                                                return false;
                                            }

                                            var evidenceFile = {
                                                EvidenceId: $(e).find("#EvidenceId").text(),
                                                EvidenceGuid: $(e).find("#EvidenceGuid").text(),
                                                FileName: $(e).find("#EvidenceFileName").text()
                                            };

                                            evidenceFiles.push(evidenceFile);
                                            j++;
                                        }
                                    }
                                });

                                if (result == true) {
                                    $.ajaxPostJson(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueEvidenceFile/InvestigationClueEvidenceInvoiceFileImport", JSON.stringify({ evidenceFiles: evidenceFiles, primaryFileName: $("#txtPrimaryFile").val() }), function (response) {
                                        if (response.IsSuccess) {
                                            $.showModalMessageBox("导入成功.");
                                        }
                                        else {
                                            $.showModalMessageBox(response.Message);
                                        }
                                    });
                                }
                            },
                        },

                        EvidenceFileList: function () {
                            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueEvidenceFile/GetInvestigationClueEvidenceFileList", function (response) {
                                if (response.IsSuccess) {
                                    $.openLoading();
                                    $("tbody", "#tblClueEvidenceFileList").clearRow();
                                    if (response.Data.TotalItemCount > 0 && $("#tblClueEvidenceFileList").length > 0) {
                                        $.each(response.Data.InvestigationClueFiles, function (i, file) {
                                            $("tbody", "#tblClueEvidenceFileList").addRow(
                                              "<input type='checkbox' id='chkClueId' name='chkClueId' clueGuid=" + file.Evidence.Clue.Basic.ClueGuid + " value=" + file.Evidence.Clue.Basic.ClueNo + ">",
                                               "<a style='color: #039' href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Evidences.Evidence.Files.File.View(" + file.FileId + ",\"" + file.ClueGuid + "\",\"" + file.FileName + "\");'><span>" + file.FileName +"</span></a>",
                                                file.Evidence.Basic.InvoiceNo,
                                                file.Evidence.Basic.NotarialObtainDate == null ? '' : getDate(convertJsonDateToJSDate(file.Evidence.Basic.NotarialObtainDate)),
                                                file.Evidence.Basic.NotaryOrganization,
                                                "<a href='javascript:void(0);' onclick='javascript:investigation.InvestigationClue.View(\"" + file.Evidence.Clue.Basic.ClueNo + "\");'><span>" + file.Evidence.Clue.Basic.ClueNo + "</span></a>",
                                                file.Evidence.Clue.Case == null ? "" : "<a href='javascript:void(0);' onclick='javascript:$.case.View(\"" + file.Evidence.Clue.Case.Basic.CaseNo + "\");'><span>" + file.Evidence.Clue.Case.Basic.CaseNo + "</span></a>",
                                                file.Evidence.Clue.InvestigationTask.Basic.InvestigatorName, //调查员
                                                file.Evidence.Clue.Case == null ? "":file.Evidence.Clue.Case.Basic.CaseAssistantName,//
                                                file.Evidence.Clue.Basic.StoreName,
                                                file.Evidence.Clue.Investigation.Basic.IndicterName, //权力人
                                                file.UploadingUserName,
                                                file.Evidence.Basic.NotarialNo,
                                                file.UploadingTime == null ? '' : getDate(convertJsonDateToJSDate(file.UploadingTime))
                                            );
                                        });
                                        $("tfoot", "#tblClueEvidenceFileList").show();
                                        $(".simple-grid-none-data-wrap").hide();
                                        $(".pull-right.page-box.investigationclueevidencefile").cPaging({
                                            totalCount: response.Data.TotalItemCount,
                                            pageNo: response.Data.PageNo,
                                            pageSize: response.Data.PageSize,
                                            callBack:  investigation.Investigations.Investigation.Evidences.Evidence.Files.EvidenceFileList,
                                            callBackArgs: null
                                        });

                                    } else {
                                        $(".simple-grid-none-data-wrap").show();
                                        $("tfoot", "#tblClueEvidenceFileList").hide();
                                    }
                                    investigation.ResetSize();
                                    $.closeLoading();
                                }
                            }, true);
                        },

                        Selected: function (e) {
                            if ($(e).prop('checked') == true) {
                                $.checkbox.all("chkClueEvidenceGuid");
                                $.checkbox.all("chkClueEvidenceAll");

                            } else {
                                $.checkbox.not("chkClueEvidenceGuid");
                                $.checkbox.not("chkClueEvidenceAll");
                            }
                        },
                    },
                },
                Layout: function () {

                    var data = {
                        investigationClueNo: $("#InvestigationClue_Basic_ClueNo").val(),
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueEvidence/List", data, function (response) {
                        if (response.IsSuccess) {
                            $.openLoading();
                            $("#dv_ClueEvidenceList").empty();
                            $("#dv_ClueEvidenceList").html(response.Data);
                            investigation.Investigations.Investigation.Evidences.List();
                            $.closeLoading();
                        }
                    }, true);
                },
                List: function () {
                    var data = {
                        investigationClueGuid: $("#InvestigationClue_Basic_ClueGuid").val(),
                        pageNo: $("#PageNo").val(),
                        pageSize: $("#PageSize").val()
                    };
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueEvidence/InvestigationClueEvidences", data, function (response) {
                        if (response.IsSuccess) {
                            $.openLoading();
                            $("tbody", "#tblInvestigationClueEvidenceList").clearRow();
                            if (response.Data.TotalItemCount > 0 && $("#tblInvestigationClueEvidenceList").length>0) {
                                $.each(response.Data.InvestigationClueEvidences, function (i, evidence) {
                                    $("tbody", "#tblInvestigationClueEvidenceList").addRow(
                                        "<input type='checkbox' id='chkClueEvidenceGuid' name='chkClueEvidenceGuid' value=" + evidence.Basic.EvidenceGuid + ">",
                                        evidence.Basic.NotarialNo,
                                        evidence.Basic.EvidenceDate == null ? '' : getDate(convertJsonDateToJSDate(evidence.Basic.EvidenceDate)),
                                        evidence.Basic.NotaryOrganization,
                                        evidence.Basic.InvoiceNo,
                                        evidence.Basic.WarehouseName ,
                                        evidence.Basic.DepositAddress,
                                        evidence.Basic.EvidenceStatusName,
                                        "<a style='color: #039' href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Evidences.Evidence.Files.Layout(\"" + evidence.Basic.EvidenceGuid + "\");'><span>查看</span></a>"
                                    );
                                });
                                $("tfoot", "#tblInvestigationClueEvidenceList").show();
                                $(".simple-grid-none-data-wrap.none-investigationclueevidence").hide();
                                $(".pull-right.page-box.investigationclueevidence").cPaging({
                                    totalCount: response.Data.TotalItemCount,
                                    pageNo: response.Data.PageNo,
                                    pageSize: response.Data.PageSize,
                                    callBack: investigation.Investigations.Investigation.Evidences.List,
                                    callBackArgs: null
                                });

                            } else {
                                $(".simple-grid-none-data-wrap.none-investigationclueevidence").show();
                                $("tfoot", "#tblInvestigationClueEvidenceList").hide();
                            }
                            investigation.ResetSize();
                            $.closeLoading();
                        }
                    }, true);
                },
                Selected: function (e) {
                    if ($(e).prop('checked') == true) {
                        $.checkbox.all("chkClueEvidenceId");
                        $.checkbox.all("chkClueEvidenceAll");

                    } else {
                        $.checkbox.not("chkClueEvidenceId");
                        $.checkbox.not("chkClueEvidenceAll");
                    }
                },
            }
        },
        List: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/Investigation/InvestigationList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblInvestigationList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.Investigations, function (i, it) {
                            $("tbody", "#tblInvestigationList").addRow(
                                "<input type='checkbox' id='chkInvestigationId' name='chkInvestigationId' investigationguid='" + it.Basic.InvestigationGuid + "'   value=" + it.Basic.InvestigationNo + ">",
                                "<a href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.View(\"" + it.Basic.InvestigationNo + "\");'><span>" + it.Basic.InvestigationNo + "</span></a>",
                                it.Basic.IndicterName,
                                it.Basic.CaseTypeName,
                                it.Basic.NeedToAuditOnCustomer ? "是" : "否",
                                it.Basic.AuthorizationBeginTime == null ? '' : getDate(convertJsonDateToJSDate(it.Basic.AuthorizationBeginTime)),
                                it.Basic.AuthorizationEndTime == null ? '' : getDate(convertJsonDateToJSDate(it.Basic.AuthorizationEndTime)),
                                it.Basic.InvestigationRegion,
                                it.Basic.BusinessOwnerName,
                                it.Basic.AuditorName);
                        });

                        $("tfoot", "#tblInvestigationList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.investigation").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: investigation.Investigations.List,
                            callBackArgs: null
                        });
                    } else {
                        $("tfoot", "#tblInvestigationList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        Selected: function (e) {
            if ($(e).prop('checked') == true) {
                $.checkbox.all("chkInvestigationId");
                $.checkbox.all("chkInvestigationAll");

            } else {
                $.checkbox.not("chkInvestigationId");
                $.checkbox.not("chkInvestigationAll");
            }
        },
    },

    InvestigationClue: {
        View: function (investigationClueNo) {

            if (investigationClueNo == null || investigationClueNo == '') return;

            var data =
            {
                investigationClueNo: investigationClueNo,
            };
            var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/Clue";

            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(".sidebox-content").empty();
                $(".sidebox-content").append(result);
                $("#sidebox").show();

                //$(".slide-panel-container").empty();
                //$(".slide-panel-container").append(result);
                //$(".slide-panel-container").addClass("show-panel");
            });

        },
        List: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/List", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblClueList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.InvestigationClues, function (i, clue) {
                            $("tbody", "#tblClueList").addRow(
                                "<input type='checkbox' id='chkClueId' name='chkClueId' value=" + clue.Basic.ClueNo + ">",
                                "<a href='javascript:void(0);' onclick='javascript:investigation.InvestigationClue.View(\"" + clue.Basic.ClueNo + "\");'><span>" + clue.Basic.ClueNo + "</span></a>",
                                clue.Basic.InvestigationDate == null ? '' : getDate(convertJsonDateToJSDate(clue.Basic.InvestigationDate)),
                                clue.Basic.Indictee,
                                clue.Basic.InfringementAddress,
                                 clue.Basic.SubjectVerificationType,
                                "状态"
                            );
                        });
                        $("tfoot", "#tblClueList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.investigationclue").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: investigation.InvestigationClue.List,
                            callBackArgs: null
                        });
                    } else {
                        $("tfoot", "#tblClueList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
    },

    InvestigationClueAudit: {

        View: function (investigationClueNo) {
            var data =
            {
                investigationClueNo: investigationClueNo,
            };
            var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueAudit/Audit";

            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(".sidebox-content_audit").empty();
                $(".sidebox-content_audit").append(result);
                $("#sidebox_audit").show();
            });
        },

        CustomerView: function (investigationClueNo) {
            var data =
            {
                investigationClueNo: investigationClueNo,
            };
            var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueAudit/CustomerAudit";

            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(".sidebox-content_audit").empty();
                $(".sidebox-content_audit").append(result);
                $("#sidebox_audit").show();
            });
        },

        Close: function () {
            $(".sidebox-content_audit").empty();
            $("#sidebox_audit").hide();

            return false;
        },

        PendingList: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/List", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblClueList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.InvestigationClues, function (i, clue) {
                            $("tbody", "#tblClueList").addRow(
                                "<input type='checkbox' id='chkClueId' name='chkClueId' value=" + clue.Basic.ClueNo + ">",
                                "<a href='javascript:void(0);' onclick='javascript:investigation.InvestigationClueAudit.View(\"" + clue.Basic.ClueNo + "\");'><span>" + clue.Basic.ClueNo + "</span></a>",
                                clue.Basic.InvestigateTime == null ? '' : getDate(convertJsonDateToJSDate(clue.Basic.InvestigateTime)),
                                clue.Basic.Indictee,
                                clue.Basic.InfringementAddress,
                                clue.Basic.SubjectVerificationType,
                                "状态"
                            );
                        });
                        $("tfoot", "#tblClueList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.investigationclue").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: investigation.InvestigationClueAudit.PendingList,
                            callBackArgs: null
                        });
                    } else {
                        $("tfoot", "#tblClueList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },

        Files: {
            Layout: function () {
                var data = {
                    investigationClueNo: $("#InvestigationClue_Basic_ClueNo").val()
                };

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueFile/List", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_ClueFileList").empty();
                        $("#dv_ClueFileList").html(response.Data);
                        investigation.InvestigationClue.Files.List();
                        $.closeLoading();
                    }
                }, true);
            },
            List: function () {
                var data = {
                    investigationClueNo: $("#InvestigationClue_Basic_ClueNo").val(),
                    pageNo: $("#PageNo").val(),
                    pageSize: $("#PageSize").val()
                };

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueFile/InvestigationClueFiles", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("tbody", "#tblInvestigationClueFileList").clearRow();
                        if (response.Data.TotalItemCount > 0) {
                            $.each(response.Data.InvestigationClueFiles, function (i, file) {
                                $("tbody", "#tblInvestigationClueFileList").addRow(
                                   "<input type='checkbox' id='chkFileId' name='chkFileId' value=" + file.FileId + ">",
                                    file.UploadingUserName,
                                    file.FileName,
                                    file.UploadingTime == null ? '' : getDate(convertJsonDateToJSDate(file.UploadingTime)),
                                    "<a style='color: #039' href='javascript:void(0);' onclick='javascript:investigation.Contract.Files.File.View(\"" + file.InvestigationGuid + "\",\"" + file.InvestigationGuid + "\",\"" + file.FileName + "\");'><span>查看</span></a>&nbsp;&nbsp;&nbsp;" +
                                    "<a style='color: #039' href='javascript:void(0);' onclick='javascript:investigation.Contract.Files.File.Download(\"" + file.InvestigationGuid + "\");'><span>下载</span></a>",
                                    "<a style='color:red;' href='javascript:void(0);'><span class='btn_investigationfile_remove glyphicon glyphicon-remove'></span></a>"
                                );
                            });

                            $("tfoot", "#tblInvestigationClueFileList").show();
                            $(".simple-grid-none-data-wrap.none-investigationcluefile").hide();

                            $(".pull-right.page-box.InvestigationClueFile").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: investigation.InvestigationClue.Files.List,
                                callBackArgs: null
                            });

                        } else {
                            $(".simple-grid-none-data-wrap.none-investigationcluefile").show();
                            $("tfoot", "#tblInvestigationClueFileList").hide();

                        }
                        investigation.ResetSize();
                        $.closeLoading();
                    }
                }, true);
            },
            Selected: function (e) {
                if ($(e).prop('checked') == true) {
                    $.checkbox.all("chkFileId");
                    $.checkbox.all("chkFileAll");

                } else {
                    $.checkbox.not("chkFileId");
                    $.checkbox.not("chkFileAll");
                }
            },
            File: {
                Open: function () {
                    var data =
                    {
                        investigationGuid: $("#Investigation_Basic_InvestigationGuid").val(),
                    };
                    var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationFile/FileUpload";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#investigationFileUploadModal').modal({ backdrop: 'static', keyboard: false });
                        $('#investigationFileUploadModal').on('hidden.bs.modal', function () {
                            $("#investigationFileUploadModal").remove();
                        });
                    });
                },
                Close: function () {
                    $('#investigationFileUploadModal').modal('hide');
                },
                Upload: function (e) {
                    if ($("#flFile").val() == '') {
                        $.showModalMessageBox("请选择上传文件.");
                        return false;
                    }

                    $('#uploadForm').ajaxSubmit({
                        success: function (response) {
                            $.showModalMessageBox("上传成功.");
                            if (response.IsSuccess) {
                                $.each(response.Data, function (i, f) {
                                    $("#attachments").append("<div  class='margin-top'><span>" + f.FileName + "</span> <a id='attachmentfile' href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Files.File.Delete(this," + f.FileId + ")'>删除</a></div>");
                                });
                                $("#help-block").hide()
                            } else {
                                $("#help-block").show();
                            }
                        }
                    });
                },
                FileUpload: function (e) {
                    if ($("#flInvestigationFile").val() == '') {
                        $.showModalMessageBox("请选择上传文件.");
                        return false;
                    }

                    $('#uploadForm').ajaxSubmit({
                        success: function (response) {
                            if (response.IsSuccess) {
                                investigation.Investigations.Investigation.Files.List();
                                investigation.Investigations.Investigation.Files.File.Close();
                            } else {
                                $.showModalMessageBox("上传失败.");
                            }
                        }
                    });
                },
                View: function (investigationFileId, investigationNo, investigationFileName) {

                    if (investigationFileId == '' || investigationFileName == '') {
                        $.showModalMessageBox("无合同文件.");
                        return false;
                    }

                    var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                    var picfiles = new Array('jpg', 'tif', 'pdf');
                    var extName = investigationFileName.substring(investigationFileName.lastIndexOf('.') + 1, investigationFileName.length);

                    if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                        var path = GV_IPR.OfficeOnlineUrl + GV_IPR.OnlineUrl + "ContractFiles/ContractFiles/" + investigationNo + "/" + investigationFileName;
                        window.open(path);
                    }
                    else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                        var path = GV_IPR.OnlineUrl + "ContractFiles/ContractFiles/" + investigationNo + "/" + investigationFileName;
                        window.open(path);
                    } else {
                        investigation.Investigations.Investigation.ContractFile.Download(investigationFileId);
                    }

                    return true;
                },
                Download: function (investigationFileId) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFile/ContractFileDownloadByGuid?investigationFileId=" + investigationFileId);
                    return true;
                },
                Delete: function (fileIds, functionCallback) {
                    var data = {
                        fileIds: fileIds,
                    };
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationFile/Delete", data, function (response) {
                        if (response.IsSuccess) {
                            //$(e).parent().remove();
                            setTimeout(functionCallback(), 200);

                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                }

            },
        },
    },
};

$(document).ready(function () {

    $(window).resize(function () {
        investigation.ResetSize();
    });

    $(document).click(function () {
        $("#divCaseInfringementWayCheckBoxList").off().hide();
        $("#divCaseDetermineThewayCheckBoxList").off().hide();
    });

    var customter = new AssociateCustomer(
        $("#div_customer"),
        $("#Investigation_Basic_Indicter"),
        $("#Investigation_Basic_Indicter"),
        $("#Investigation_Basic_IndicterName"),
        null
    );

    var investigator = new AssociateAvailableUser(
        $("#div_userlist"),
        $("#InvestigationTask_Basic_Investigator_Input"),
        $("#InvestigationTask_Basic_Investigator_Input"),
        null
    );

    $(document).off('click', '#InvestigationClueEvidence_Basic_InfringementWay').on('click', '#InvestigationClueEvidence_Basic_InfringementWay', function () {
        var tirgger = this;
        var html = $.lsCaseInfringementWay.getCaseInfringementWayCheckBoxListHtml();
        $(".divCaseInfringementWay").html(html);
        $("#hidInfringementWayName").val($(tirgger).attr("id"));
        $("#divCaseInfringementWayCheckBoxList").css({
            "position": "absolute",
            "left": $(this).position().left + 2,
            "top": $(this).position().top + 28,
            "z-index": 1200
        }).show();

        return false;
    });

    $(document).off('click', '#divCaseInfringementWayCheckBoxList li').on('click', '#divCaseInfringementWayCheckBoxList', function (e) {

        if ($(e.target).is("lable")) {
            e.stopPropagation();
            return false;
        }

        var currentSelectedControl = $("#hidInfringementWayName").val();

        if ($(this).attr("id") == 'btnAllUnSelected') {
            $("#" + currentSelectedControl).val('');
            return false;
        } else if ($(this).attr("id") == 'btnAllSelected') {
            $("#" + currentSelectedControl).val('');
            return false;
        }

        $("#" + currentSelectedControl).val('');
        $("#" + currentSelectedControl).val('');

        var caseInfringementWays = '';

        $("#divCaseInfringementWayCheckBoxList").find("input:checkbox").each(function (i, tigger) {
            if ($(tigger).prop("checked") == true) {
                caseInfringementWays += $(tigger).attr("infringementwayname") + ";";
            }
        });

        $("#" + currentSelectedControl).val(caseInfringementWays.substring(0, caseInfringementWays.length - 1));

        e.stopPropagation();

        return true;
    });

    $(document).off('click', '#InvestigationClue_Basic_SubjectVerificationType').on('click', '#InvestigationClue_Basic_SubjectVerificationType', function () {
        var tirgger = this;
        var html = $.lsCaseDetermineTheway.getCaseDetermineThewayCheckBoxListHtml();
        $(".divCaseDetermineTheway").html(html);
        $("#hidDetermineThewayName").val($(tirgger).attr("id"));
        $("#divCaseDetermineThewayCheckBoxList").css({
            "position": "absolute",
            "left": $(this).position().left + 2,
            "top": $(this).position().top + 28,
            "z-index": 1200
        }).show();

        return false;
    });

    $(document).off('click', '#divCaseDetermineThewayCheckBoxList li').on('click', '#divCaseDetermineThewayCheckBoxList', function (e) {

        if ($(e.target).is("lable")) {
            e.stopPropagation();
            return false;
        }

        var currentSelectedControl = $("#hidDetermineThewayName").val();

        if ($(this).attr("id") == 'btnAllUnSelected') {
            $("#" + currentSelectedControl).val('');
            return false;
        } else if ($(this).attr("id") == 'btnAllSelected') {
            $("#" + currentSelectedControl).val('');
            return false;
        }

        $("#" + currentSelectedControl).val('');
        $("#" + currentSelectedControl).val('');

        var caseDetermineTheways = '';

        $("#divCaseDetermineThewayCheckBoxList").find("input:checkbox").each(function (i, tigger) {
            if ($(tigger).prop("checked") == true) {
                caseDetermineTheways += $(this).attr("determineThewayname") + ";";
            }
        });

        $("#" + currentSelectedControl).val(caseDetermineTheways.substring(0, caseDetermineTheways.length - 1));

        e.stopPropagation();

        return true;
    });

    $(document).off('click', '#Investigation_Basic_Province').on('click', '#Investigation_Basic_Province', function () {
        //appendCity(this, 'duoxuan');
        var url = AP_ROOT + AP_PAGE_ID + "/BAS/CityChosen/CityChosen";
        $.openLoading();

        var data = {
        };

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);
            $('#cityChosenModal').modal({ backdrop: 'static', keyboard: false });
            $('#cityChosenModal').on('hidden.bs.modal', function () {
                $("#cityChosenModal").remove();
            });

            $(document).ready(function () {
                $(function () {
                    //------生成地区
                    GetRegionPlug();
                    SetChecked($("#Investigation_Basic_City").val().split(","));
                });

                //------选择后确定按钮
                $(document).off('click', '#btnCityChosen').on('click', '#btnCityChosen', function () {
                    var citys = GetChecked().join(",");//已选择的城市名
                    var areas = new Array();

                    $(".bigarea").each(function (i, e) {
                        if ($(e).prop("checked") == true) {
                            areas.push($(e).attr("data-name"));
                        }
                    })
                    $("#Investigation_Basic_Province").val(areas);//显示在页面
                    $("#Investigation_Basic_City").val(citys);//存入隐藏的input
                    $('#cityChosenModal').modal('hide');//完后隐藏模态框
                })
            });

        });

    });

    $(document).off('click', '#InvestigationTask_Basic_Province').on('click', '#InvestigationTask_Basic_Province', function () {
        //appendCity(this, 'duoxuan');
        var url = AP_ROOT + AP_PAGE_ID + "/BAS/CityChosen/CityChosen";
        $.openLoading();

        var data = {
        };

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);
            $('#cityChosenModal').modal({ backdrop: 'static', keyboard: false });
            $('#cityChosenModal').on('hidden.bs.modal', function () {
                $("#cityChosenModal").remove();
            });

            $(document).ready(function () {
                $(function () {
                    //------生成地区
                    GetRegionPlug();

                    if ($("#Investigation_Basic_InvestigationScope") == "R") {
                        DisabledCity($("#Investigation_Basic_City").val().split(","));
                    }
                });

                //------选择后确定按钮
                $(document).off('click', '#btnCityChosen').on('click', '#btnCityChosen', function () {
                    var citys = GetChecked().join(",");//已选择的城市名
                    var areas = new Array();

                    $(".bigarea").each(function (i, e) {
                        if ($(e).prop("checked") == true) {
                            areas.push($(e).attr("data-name"));
                        }
                    })

                    $("#InvestigationTask_Basic_Province").val(areas);//显示在页面
                    $("#InvestigationTask_Basic_City").val(areas);//存入隐藏的input
                    $('#cityChosenModal').modal('hide');//完后隐藏模态框
                })
            });

        });
    });

    //$("#flInvestigationFile").off().on("change", function () {
    //    investigation.Investigations.Investigation.Files.File.Upload();
    //});

    $(document).off('change', '#flInvestigationTaskFile').on('change', '#flInvestigationTaskFile', function () {
        $("#txtInvestigationFilePath").val($("#flInvestigationTaskFile").val());
    });

    $(document).off('change', '#flInvestigationFile').on('change', '#flInvestigationFile', function () {
        investigation.Investigations.Investigation.Files.File.Upload();
    });

    $(document).off('click', '#btnFileUpload').on('click', '#btnFileUpload', function () {
        $("#flInvestigationFile").trigger("click");
    });

    $(document).off('change', '#flInvestigationClueFile').on('change', '#flInvestigationClueFile', function () {
        investigation.Investigations.Investigation.Clues.Clue.Files.File.Upload();
    });

    $(document).off('click', '#btnInvestigationClueFile_Upload').on('click', '#btnInvestigationClueFile_Upload', function () {

        $("#flInvestigationClueFile").trigger("click");
    });

    $(document).off('click', '#btnInvestigationSearch').on('click', '#btnInvestigationSearch', function () {
        investigation.Investigations.List();
    });

    $(document).off('click', '#btnInvestigationCreateUpdate').on('click', '#btnInvestigationCreateUpdate', function () {
        investigation.Investigations.Investigation.CreateUpdate(true);
    });

    $(document).off('click', '#btnInvestigationTaskCreateUpdate').on('click', '#btnInvestigationTaskCreateUpdate', function () {
        investigation.Investigations.Investigation.Tasks.Task.CreateUpdate(investigation.Investigations.Investigation.Tasks.Task.CreateUpdateCallBack_End);
    });

    $(document).off('click', '#btnInvestigationTaskCreateOtherOne').on('click', '#btnInvestigationTaskCreateOtherOne', function () {
        investigation.Investigations.Investigation.Tasks.Task.CreateUpdate(investigation.Investigations.Investigation.Tasks.Task.CreateUpdateCallBack_NextOne);
    });

    $(document).off('click', '.userremove').on('click', '.userremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        investigation.Investigations.Investigation.Tasks.Task.Investigator.Remove(this);
    });

    $(document).off('click', '.indicteeremove').on('click', '.indicteeremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        investigation.Investigations.Investigation.Clues.Clue.Indictees.Indictee.Remove(this);
    });

    $(document).off('click', '.producerremove').on('click', '.producerremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        investigation.Investigations.Investigation.Clues.Clue.Producers.Producer.Remove(this);
    });

    $(document).off('click', '.btn_indicter_add').on('click', '.btn_indicter_add', function () {
        $.customer.Open(this);
    });

    $(document).off('click', '.btn_investigationfile_remove').on('click', '.btn_investigationfile_remove', function () {
        var fileId = $(this).parents("tr").find("#chkFileId").val();
        var fileIds = [];
        fileIds.push(fileId);
        investigation.Investigations.Investigation.Files.File.Delete(fileIds, investigation.Investigations.Investigation.Files.List);
    });

    $(document).off('click', '#chkFileAll').on('click', '#chkFileAll', function () {
        investigation.Investigations.Investigation.Files.Selected(this);
    });

    $(document).off('click', '#btnInvestigationTaskCreate').on('click', '#btnInvestigationTaskCreate', function () {

        var investigationNo = $("#Investigation_Basic_InvestigationNo").val();
        var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationTask/Create?InvestigationNo=" + investigationNo;
        window.open(url, 'InvestigationTask');
    });

    $(document).off('click', '.investigationTaskCreate').on('click', '.investigationTaskCreate', function () {

        var investigationNo = $("#Investigation_Basic_InvestigationNo").val();
        var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationTask/Create?InvestigationNo=" + investigationNo;
        window.open(url, 'InvestigationTask');
    });

    $(document).off('click', '.investigationTaskEdit').on('click', '.investigationTaskEdit', function () {


        /*列表选中修改*/
        var taskNos = $.checkbox.vals("chkTaskId");
        if (taskNos.length == 0) {
            $.showModalMessageBox("请选择调查子任务.");
            return false;
        }

        if (taskNos.length > 1) {
            $.showModalMessageBox("只能选择一个子任务进行修改.");
            return false;
        }

        var taskNo = taskNos[0];
        investigation.Investigations.Investigation.Tasks.Task.Edit(taskNo);
    });

    $(document).off('click', '#btnInvestigationListDelete').on('click', '#btnInvestigationListDelete', function () {
        /*列表选中修改*/
        var investigationNos = $.checkbox.vals("chkInvestigationId");
        if (investigationNos.length == 0) {
            $.showModalMessageBox("请选择调查任务.");
            return false;
        }
        investigation.Investigations.Investigation.Delete(investigationNos);
    });

    $(document).off('click', '#btnInvestigationFileUploading').on('click', '#btnInvestigationFileUploading', function () {
        investigation.Investigations.Investigation.Files.File.FileUpload();
    });

    $(document).off('click', '#btnInvestigationFileUploadCancel,#btnInvestigationFileUploadClose').on('click', '#btnInvestigationFileUploadCancel,#btnInvestigationFileUploadClose', function () {
        investigation.Investigations.Investigation.Files.File.Close();
    });

    $(document).off('click', '#chkTaskAll').on('click', '#chkTaskAll', function () {
        investigation.Investigations.Investigation.Tasks.Selected(this);
    });

    $(document).off('click', '#btninvestigationTaskDelete').on('click', '#btninvestigationTaskDelete', function () {

        var taskNos = $.checkbox.vals("chkTaskId");
        if (taskNos.length == 0) {
            $.showModalMessageBox("请选择需要删除的任务.");
            return false;
        }

        investigation.Investigations.Investigation.Tasks.Task.Delete(taskNos);
    });

    $(document).off('click', '.btn_investigationtask_remove').on('click', '.btn_investigationtask_remove', function () {
        var taskId = $(this).parents("tr").find("#chkTaskId").val();
        var taskNos = [];
        taskNos.push(taskId);
        investigation.Investigations.Investigation.Tasks.Task.Delete(taskNos);
    });

    $(document).off('click', '#btnInvestigationClueFileUpload').on('click', '#btnInvestigationClueFileUpload', function () {
        var clueNo = $("#InvestigationClue_Basic_ClueNo").val();
        investigation.Investigations.Investigation.Clues.Clue.Files.File.FileUpload(clueNo);
    });

    $(document).off('click', '#btnInvestigationClueAuditSearch').on('click', '#btnInvestigationClueAuditSearch', function () {
        investigation.Investigations.Investigation.Clues.ClueList();
    });

    $(document).off('click', '#chkClueAll').on('click', '#chkClueAll', function () {
        investigation.Investigations.Investigation.Clues.Selected(this);
    });

    $(document).off('click', '#btnInvestigationTaskClueCreate').on('click', '#btnInvestigationTaskClueCreate', function () {
        var taskNo = $("#InvestigationTask_Basic_TaskNo").val();
        investigation.Investigations.Investigation.Clues.Clue.Create(taskNo);
    });

    $(document).off('click', '#btnInvestigationClueEdit').on('click', '#btnInvestigationClueEdit', function () {
        var clueNos = $.checkbox.vals("chkClueId");
        if (clueNos.length == 0) {
            $.showModalMessageBox("请选择线索.");
            return false;
        }

        if (clueNos.length > 1) {
            $.showModalMessageBox("只能选择一个线索.");
            return false;
        }

        investigation.Investigations.Investigation.Clues.Clue.Edit(clueNos[0]);
    });

    $(document).off('click', '#btnInvestigationTaskListClueCreate').on('click', '#btnInvestigationTaskListClueCreate', function () {
        var taskNos = $.checkbox.vals("chkTaskId");
        if (taskNos.length == 0) {
            $.showModalMessageBox("请选择调查任务.");
            return false;
        }

        if (taskNos.length > 1) {
            $.showModalMessageBox("只能一个调查任务创建线索.");
            return false;
        }

        investigation.Investigations.Investigation.Clues.Clue.Create(taskNos[0]);
    });

    $(document).off('click', '#btnInvestigationClueDelete').on('click', '#btnInvestigationClueDelete', function () {

        var clueNos = $.checkbox.vals("chkClueId");
        if (clueNos.length == 0) {
            $.showModalMessageBox("请选择需要删除的线索.");
            return false;
        }

        investigation.Investigations.Investigation.Clues.Clue.Delete(clueNos);
    });

    $(document).off('click', '#btnInvestigationClueExportAll').on('click', '#btnInvestigationClueExportAll', function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(2000);
        investigation.Investigations.Investigation.Clues.ExportAllToExcel();
    });

    $(document).off('click', '#btnInvestigationClueExportSelected').on('click', '#btnInvestigationClueExportSelected', function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);
        investigation.Investigations.Investigation.Clues.ExportSelectedToExcel();
    });

    $(document).off('click', '#btnInvestigationClueExportAllForManifest').on('click', '#btnInvestigationClueExportAllForManifest', function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(2000);
        investigation.Investigations.Investigation.Clues.ExportAllToExcelForManifest();
    });

    $(document).off('click', '#btnInvestigationClueExportSelectedForManifest').on('click', '#btnInvestigationClueExportSelectedForManifest', function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);
        investigation.Investigations.Investigation.Clues.ExportSelectedToExcelForManifest();
    });

    $(document).off('click', '#btnInvestigationClueFileCreate').on('click', '#btnInvestigationClueFileCreate', function () {

        var clueNos = $.checkbox.vals("chkClueId");
        if (clueNos.length == 0) {
            $.showModalMessageBox("请选择线索.");
            return false;
        }

        if (clueNos.length > 1) {
            $.showModalMessageBox("只能选一个线索增加文件.");
            return false;
        }

        investigation.Investigations.Investigation.Clues.Clue.Files.File.Open(clueNos[0]);
    });

    $(document).off('click', '#btnInvestigationClueFileDelete').on('click', '#btnInvestigationClueFileDelete', function () {

        var fileIds = $.checkbox.vals("chkFileId");
        if (fileIds.length == 0) {
            $.showModalMessageBox("请选择文件.");
            return false;
        }

        investigation.Investigations.Investigation.Clues.Clue.Files.File.Delete(fileIds, investigation.Investigations.Investigation.Clues.Clue.Files.List);
    });

    $(document).off('click', '#btnInvestigationClueToAudit').on('click', '#btnInvestigationClueToAudit', function () {

        var clueNos = $.checkbox.vals("chkClueId");
        if (clueNos.length == 0) {
            $.showModalMessageBox("请选择线索.");
            return false;
        }

        investigation.Investigations.Investigation.Clues.Clue.ToAudit(clueNos);
    });

    $(document).off('click', '#btnInvestigationClueAudit').on('click', '#btnInvestigationClueAudit', function () {

        var clueNos = $.checkbox.vals("chkClueId");
        if (clueNos.length == 0) {
            $.showModalMessageBox("请选择线索.");
            return false;
        }

        if (clueNos.length > 1) {
            $.showModalMessageBox("只能选一个线索.");
            return false;
        }

        investigation.InvestigationClueAudit.View(clueNos[0]);
    });

    $(document).off('click', '#btnInvestigationClueCustomerAudit').on('click', '#btnInvestigationClueCustomerAudit', function () {

        var clueNos = $.checkbox.vals("chkClueId");
        if (clueNos.length == 0) {
            $.showModalMessageBox("请选择线索.");
            return false;
        }

        if (clueNos.length > 1) {
            $.showModalMessageBox("只能选一个线索.");
            return false;
        }

        investigation.InvestigationClueAudit.CustomerView(clueNos[0]);
    });


    $(document).off('click', '#btnInvestigationClueAuditApproved').on('click', '#btnInvestigationClueAuditApproved', function () {
        investigation.Investigations.Investigation.Clues.Clue.Audits.Audit.Approved();
    });

    $(document).off('click', '#btnInvestigationClueCustomerAuditApproved').on('click', '#btnInvestigationClueCustomerAuditApproved', function () {
        investigation.Investigations.Investigation.Clues.Clue.Audits.Audit.CustomerApproved();
    });


    $(document).off('click', '#btnInvestigationClueCustomerAuditRejected').on('click', '#btnInvestigationClueCustomerAuditRejected', function () {
        investigation.Investigations.Investigation.Clues.Clue.Audits.Audit.CustomerRejected();
    });

    $(document).off('click', '#btnInvestigationClueTaskEvidence').on('click', '#btnInvestigationClueTaskEvidence', function () {

        var clueNos = $.checkbox.vals("chkClueId");
        if (clueNos.length == 0) {
            $.showModalMessageBox("请选择线索.");
            return false;
        }

        if (clueNos.length > 1) {
            $.showModalMessageBox("只能选一个线索.");
            return false;
        }

        investigation.Investigations.Investigation.Evidences.Evidence.Create(clueNos[0]);
    });

    $(document).off('click', '#btnInvestigationClueTaskEvidenceMultiCreate').on('click', '#btnInvestigationClueTaskEvidenceMultiCreate', function () {

        var clueNos = $.checkbox.vals("chkClueId");
        if (clueNos.length == 0) {
            $.showModalMessageBox("请选择线索.");
            return false;
        }

        //if (clueNos.length > 1) {
        //    $.showModalMessageBox("只能选一个线索.");
        //    return false;
        //}

        investigation.Investigations.Investigation.Evidences.Evidence.MultiCreate(clueNos[0]);
    });

    $(document).off('click', '#btnInvestigationClueEvidenceEdit').on('click', '#btnInvestigationClueEvidenceEdit', function () {

        var clueEvidenceNos = $.checkbox.vals("chkClueEvidenceGuid");
        if (clueEvidenceNos.length == 0) {
            $.showModalMessageBox("请选择取证信息.");
            return false;
        }

        if (clueEvidenceNos.length > 1) {
            $.showModalMessageBox("只能选一个取证信息.");
            return false;
        }

        investigation.Investigations.Investigation.Evidences.Evidence.Edit(clueEvidenceNos[0]);
    });

    $(document).off('click', '#btnInvestigationClueEvidenceDelete').on('click', '#btnInvestigationClueEvidenceDelete', function () {

        var clueEvidenceNos = $.checkbox.vals("chkClueEvidenceGuid");
        if (clueEvidenceNos.length == 0) {
            $.showModalMessageBox("请选择取证信息.");
            return false;
        }

        if (clueEvidenceNos.length > 1) {
            $.showModalMessageBox("只能选一个取证信息.");
            return false;
        }

        investigation.Investigations.Investigation.Evidences.Evidence.Delete(clueEvidenceNos[0]);
    });


    $(document).off('change', '#Investigation_Basic_InvestigationScope').on('change', '#Investigation_Basic_InvestigationScope', function () {

        if ($('#Investigation_Basic_InvestigationScope').val() == 'R') {
            $(".investigationScope").show();
        }
        else {
            $(".investigationScope").hide();
        }
    });

    $(document).off('click', '#InvestigationClue_Indictee_Input').on('click', '#InvestigationClue_Indictee_Input', function () {
        investigation.Investigations.Investigation.Clues.Clue.Indictees.Indictee.Create();
    });

    $(document).off('click', '#InvestigationClue_Producer_Input').on('click', '#InvestigationClue_Producer_Input', function () {
        investigation.Investigations.Investigation.Clues.Clue.Producers.Producer.Create();
    });

    $(document).off('click', '#btnInvestigationClueIndicteeCreateUpdate').on('click', '#btnInvestigationClueIndicteeCreateUpdate', function () {
        investigation.Investigations.Investigation.Clues.Clue.Indictees.Indictee.CreateUpdate(investigation.Investigations.Investigation.Clues.Clue.Indictees.Indictee.AddIn);
    });

    $(document).off('click', '#btnInvestigationClueProducerCreateUpdate').on('click', '#btnInvestigationClueProducerCreateUpdate', function () {
        investigation.Investigations.Investigation.Clues.Clue.Producers.Producer.CreateUpdate(investigation.Investigations.Investigation.Clues.Clue.Producers.Producer.AddIn);
    });

    $(document).off('click', '#btnInvestigationClueCreateUpdate').on('click', '#btnInvestigationClueCreateUpdate', function () {
        investigation.Investigations.Investigation.Clues.Clue.CreateInvestigationClue(false);
    });

    $(document).off('click', '#btnInvestigationClueCreateAndAudit').on('click', '#btnInvestigationClueCreateAndAudit', function () {
        investigation.Investigations.Investigation.Clues.Clue.CreateInvestigationClue(true);
    });

    $(document).off('click', '#btnInvestigationClueUpdateAndAudit').on('click', '#btnInvestigationClueUpdateAndAudit', function () {
        investigation.Investigations.Investigation.Clues.Clue.UpdateInvestigationClue(true);
    });

    $(document).off('click', '#btnInvestigationClueUpdate').on('click', '#btnInvestigationClueUpdate', function () {

        
        investigation.Investigations.Investigation.Clues.Clue.UpdateInvestigationClue(false);
    });

    $(document).off('click', '#btnInvestigationClueGenerateCase').on('click', '#btnInvestigationClueGenerateCase', function () {

        var clueNos = $.checkbox.vals("chkClueId");
        if (clueNos.length == 0) {
            $.showModalMessageBox("请选择线索.");
            return false;
        }

        var customerNos = new Array();

        $("input[name='chkClueId']:checked").each(
            function () {
                if ($.inArray($(this).attr("customerNo"), customerNos) > -1) {
                } else {
                    customerNos.push($(this).attr("customerNo"));
                }
            }
        );

        if (customerNos.length > 1) {
            $.showModalMessageBox("客户不一致.");
            return false;
        }
        
        investigation.Investigations.Investigation.Clues.Clue.GenerateCase(clueNos);
    });

    $(document).off('click', '#InvestigationClue_Basic_AuditNeedMergeCase').on('change', '#InvestigationClue_Basic_AuditNeedMergeCase', function () {
        if ($("#InvestigationClue_Basic_AuditNeedMergeCase").val() == 'true') {
            $("#auditNeedMergeCaseNo").show();
        }
        else {
            $("#auditNeedMergeCaseNo").hide();
        }
    });

    $(document).off('click', '#InvestigationClueEvidence_Basic_DepositAddress').on('click', '#InvestigationClueEvidence_Basic_DepositAddress', function () {
        var tirgger = this;
        var html = $.warehouse.getwarehouseListTreeHtml();

        $("#divWarehouseCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left ,
            "top": $(tirgger).parent().position().top + 29,
            "z-index": 9999
        }).toggle();

        return false;
    });

    $(document).off('click', '#btnStorageLocationSelected').on('click', '#btnStorageLocationSelected', function () {
        var treeObj = $.fn.zTree.getZTreeObj("warehouseTree");
        var nodes = treeObj.getCheckedNodes(true);
        if (nodes.length > 0) {
            var node = nodes[0];
            if (node.typeId == $.warehouse.type.warehouse) {
                $.showModalMessageBox("请选择具体库位.");
                return;
            }
            else {
                $("#InvestigationClueEvidence_Basic_StorageLocationNo").val(node.id);
                $("#InvestigationClueEvidence_Basic_WarehouseNo").val(node.pId);
                $("#InvestigationClueEvidence_Basic_DepositAddress").val(node.name);
                $("#InvestigationClueEvidence_Basic_StorageLocationName").val(node.name);
                $('#divWarehouseCheckBoxList').hide();
            }
        }
        else {
            $.showModalMessageBox("请选择库位.");
        }
    });

    $(document).off('click', '#InvestigationClueEvidence_Basic_NotaryOrganization').on('click', '#InvestigationClueEvidence_Basic_NotaryOrganization', function () {
        var tirgger = this;
        var html = $.notaryOffice.getNotaryOfficeListHtml();
        $(".divNotaryOffices").html(html);
        $("#hidNotaryOfficeId").val("InvestigationClueEvidence_Basic_NotaryOfficeId");
        $("#hidNotaryOfficeName").val($(tirgger).attr("id"));
        $("#hidNotaryOfficeTemplateName").val("InvestigationClueEvidence_Basic_NotarialNo");

        $("#divNotaryOfficeList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 100,
            "top": $(tirgger).position().top + 28
        }).toggle();

        return false;
    });

    $(document).off('click', '#divNotaryOfficeList ul li').on('click', '#divNotaryOfficeList ul li', function (i, e) {
        var notaryOfficeId = $(this).find("a").attr("notaryOfficeId");
        var notaryOfficeName = $(this).find("a").text();
        var templateNotarialNo = $(this).find("a").attr("templateName");
        var currentSelectedControl = $("#hidNotaryOfficeName").val();
        var currentSelectedIdControl = $("#hidNotaryOfficeId").val();
        var currentSelectedTemplateNameControl = $("#hidNotaryOfficeTemplateName").val();
        $("#" + currentSelectedControl).val(notaryOfficeName);
        $("#" + currentSelectedTemplateNameControl).val(templateNotarialNo);
        //$("#" + currentSelectedIdControl).val(notaryOfficeId);

        $("#divNotaryOfficeList").hide();
    });

    $(document).off('click', '#chkClueEvidenceAll').on('click', '#chkClueEvidenceAll', function () {
        investigation.Investigations.Investigation.Evidences.Evidence.Files.Selected(this);
    });
});