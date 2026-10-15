var staff = {
    Init: function () {
       
        $("#divStaffExperience").hide();
    },
    ResetSize: function () {
        if ($("#divContextList").length > 0) {
            $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 18);
        }
    },
    Staff: {
        View: function (staffId) {
            var url =   AP_ROOT + AP_PAGE_ID  + "/HR/Staff/View?staffId=" + staffId;
            //window.open(url);
            addtabs(url, "员工查看");
        },
        Edit: function (staffId) {
            var url =   AP_ROOT + AP_PAGE_ID  +"/HR/Staff/CreateUpdate?staffId=" + staffId;
            //window.open(url);
            addtabs(url, "员工编辑");
        },
        Delete: function () {
            var staffNames = $.checkbox.vals("chkStaffId");
            if (staffNames.length == 0) {
                $.showTips("请选择需要删除的员工.", 0, 3);
                return false;
            }
            $.showModalConfirmDialog("确定删除？", "staff.Staff.DeleteCallBack", staffNames);
            return true;
           
        },
        DeleteCallBack: function (staffNames) {
            var data = {
                staffNames: staffNames,
            };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "//HR/Staff/Delete", data, function (response) {
                if (response.IsSuccess) {
                    $.showTips("员工已删除.", 0, 3);
                    staff.Staff.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        CreateUpdate: function () {

            if ($("#Staff_StaffBasic_StaffNo").val() == '') {
                $.showModalMessageBox("请输入员工号.");
                return false;
            }

            if ($("#Staff_StaffBasic_StaffName").val() == '') {
                $.showModalMessageBox("请输入员工姓名.");
                return false;
            }

            if ($("#Staff_StaffBasic_StaffChName").val() == '') {
                $.showModalMessageBox("请输入员工中文姓名.");
                return false;
            }

            if ($("#Staff_StaffBasic_RoleId").val() == '') {
                $.showModalMessageBox("请选择角色.");
                return false;
            }
            
            if ($("#Staff_StaffBasic_CompanyId").val() == '') {
                $.showModalMessageBox("请选择公司.");
                return false;
            }

            if ($("#Staff_StaffBasic_DepartmentId").val() == '') {
                $.showModalMessageBox("请选择部门.");
                return false;
            }

            if ($("#Staff_StaffBasic_StaffTitleId").val() == '') {
                $.showModalMessageBox("请选择职务.");
                return false;
            }

            if ($("#Staff_StaffBasic_AccessLevel").val() == '') {
                $.showModalMessageBox("请选择数据访问级别.");
                return false;
            }

            if ($("#Staff_StaffBasic_OrgPassword").val() == '') {
                $.showModalMessageBox("请输入密码.");
                return false;
            }

            $("#staffForm").ajaxPost(  AP_ROOT + AP_PAGE_ID  +"/HR/Staff/StaffCreateUpdate", function (response) {
                if (response.IsSuccess) {
                    $('#Staff_StaffBasic_StaffId').val(response.Data.StaffBasic.StaffId);
                    $.showModalMessageBox("保存成功.");
                }
                else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },
        ResetPassword: function (staffId) {

            var data = {
                staffId: staffId
            };

			$.ajaxPost(  AP_ROOT + AP_PAGE_ID  +"/HR/Staff/ResetPassword", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("设定成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        List: {
            BindMenu: function () {

                $('#staffgridSection').contextMenu('staffMenu', {
                    menuStyle: {
                        width: '152px'
                    },

                    itemStyle: {
                        width: '150px'
                    },

                    bindings: {
                        'view': function (t, e) {
                            var staffId = $(e).find("span").text();
                            if (staffId == '') {
                                $.showModalMessageBox("请选择查看的客户.");
                                return false;
                            }

                            staff.Staff.View(staffId);
                        },
                        'edit': function (t, e) {
                            var staffId = $(e).find("span").text();
                            if (staffId == '') {
                                $.showModalMessageBox("请选择编辑的客户.");
                                return false;
                            }

                            staff.Staff.Edit(staffId);
 
                            return true;
                        },

                        'createcontract': function (t, e) {
                            var staffId = $(e).find("span").text();
                            if (staffId == '') {
                                $.showModalMessageBox("请选择客户.");
                                return false;
                            }

                            window.open(  AP_ROOT + AP_PAGE_ID  +"HR/ContractDraft/Draft?staffId=" + staffId);

                            return true;
                        },
                    },
                    onContextMenu: function (e) {
                        return true;
                    },
                    onShowMenu: function (e, menu) {
                        if ($(e.target).parents("tr").find(".staffId").hasClass("staffId")) {
                            var staffId = $(e.target).parents("tr").find(".staffId").text();
                            $('#view', menu).append("<span style='display:none'>" + staffId + "</span>");
                            $('#edit', menu).append("<span style='display:none'>" + staffId + "</span>");
                            $('#createcontract', menu).append("<span style='display:none'>" + staffId + "</span>");
                         } else {
                            $('#view,#edit,#createcontract', menu).remove();
                        }
                        return menu;
                    }
                });
            },
            StaffList: function()
            {
                $("#postForm").ajaxPost(  AP_ROOT + AP_PAGE_ID  +"/HR/Staff/StaffList", function (response) {
                    if (response.IsSuccess) {
                        $("tbody", "#tblStaffList").clearRow();
                        if (response.Data.TotalItemCount > 0) {
                            $(".info_inall.layoutfix").show();
                            $.each(response.Data.StaffList, function (i, s) {
                                $("tbody", "#tblStaffList").addRow(
                                    "<input type='checkbox' id='chkStaffId' name='chkStaffId'  value=" + s.StaffBasic.StaffName + ">",
                                    s.StaffBasic.StaffId,
                                    s.StaffBasic.StaffNo,
                                    s.StaffBasic.StaffName,
                                    s.StaffBasic.StaffChName,
                                    s.StaffBasic.DepartmentName,
                                    s.StaffBasic.CompanyName,
                                    s.StaffBasic.Email,
                                    s.StaffBasic.MobilePhone,
                                    s.StaffBasic.OfficePhone,
                                    s.StaffBasic.IsActived ? "是":"否",
                                    "<a href='javascript:void(0)' onclick='javascript:staff.Staff.Edit(" + s.StaffBasic.StaffId + ")'>修改</a>&nbsp; &nbsp;&nbsp;<a href='javascript:void(0)' onclick='javascript:staff.Staff.ResetPassword(" + s.StaffBasic.StaffId + "REDACTED_ARCHIVE_ONLY");
                            });
                            $("tfoot", "#tblStaffList").show();
                            $(".simple-grid-none-data-wrap").hide();
                            $(".pull-right.page-box.stafflist").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: staff.Staff.List.StaffList,
                                callBackArgs: null
                            });

                        } else {

                            $("tfoot", "#tblStaffList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                    }
                });
            },
        },
        Files: {
            Layout: function () {
                var data = {
                    staffId: $("#Staff_StaffBasic_StaffGuid").val()
                };

                $.ajaxPost(  AP_ROOT + AP_PAGE_ID  +"/HR/Staff/StaffFileList", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_List").empty();
                        $("#dv_List").html(response.Data);
                        staff.Staff.Files.List();
                        staff.ResetSize();
                        $.closeLoading();
                    }
                }, true);
            },

            List: function () {
                var data = {
                    staffGuid: $("#Staff_StaffBasic_StaffGuid").val(),
                };

                $.ajaxPost(  AP_ROOT + AP_PAGE_ID  +"/HR/Staff/StaffFiles", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("tbody", "#tblStaffFileList").clearRow();
                        if (response.Data.length > 0) {
                            $.each(response.Data, function (i, file) {
                                $("tbody", "#tblStaffFileList").addRow(
                                    ++i,
                                    file.UploadUserName,
                                    file.FileName,
                                    file.UploadTime == null ? '' : getDate(convertJsonDateToJSDate(file.UploadTime)),
                                    "<a style='color: #039' href='javascript:void(0);' onclick='javascript:staff.Staff.Files.File.View(\"" + file.FileGuid + "\",\"" + file.StaffGuid + "\",\"" + file.FileName + "\");'><span>查看</span></a>&nbsp;&nbsp;&nbsp;" +
                                    "<a style='color: #039' href='javascript:void(0);' onclick='javascript:staff.Staff.Files.File.Download(\"" + file.FileGuid + "\");'><span>下载</span></a>",
                                    "<a style='color:green;' href='javascript:void(0);'><span class='btn_stafffile_add glyphicon glyphicon-plus'></span></a>    " +
                                    "<a style='color:red;' href='javascript:void(0);' onclick='javascript:staff.Staff.Files.File.Delete(\"" + file.FileId + "\");'><span class='btn_stafffile_remove glyphicon glyphicon-remove'></span></a>"
                                );
                            });
                            $(".simple-grid-none-data-wrap").hide();
                        } else {
                            $(".simple-grid-none-data-wrap").show();
                        }
                        staff.ResetSize();
                        $.closeLoading();
                    }
                }, true);
            },
            File: {
                Open: function () {
                    var data =
                    {
                        staffGuid: $("#Staff_StaffBasic_StaffGuid").val(),
                    };
                    var url =   AP_ROOT + AP_PAGE_ID  +"/HR/Staff/StaffFileUpload";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#staffFileUploadModal').modal({ backdrop: 'static', keyboard: false });
                        $('#staffFileUploadModal').on('hidden.bs.modal', function () {
                            $("#staffFileUploadModal").remove();
                        });
                    });
                },
                Close: function () {
                    $('#staffFileUploadModal').modal('hide');
                },
                Upload: function () {

                    if ($("#flStaffFile").val() == '') {
                        $.showModalMessageBox("请选择上传文件.");
                        return false;
                    }

                    $('#uploadForm').ajaxSubmit({
                        success: function (response) {
                            $.showModalMessageBox("上传成功.");
                            staff.Staff.Files.File.Close();
                            staff.Staff.Files.Layout();
                        }
                    });
                },
                View: function (staffFileId, staffNo, staffFileName) {

                    if (staffFileId == '' || staffFileName == '') {
                        $.showModalMessageBox("无客户文件.");
                        return false;
                    }

                    var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                    var picfiles = new Array('jpg', 'tif', 'pdf');
                    var extName = staffFileName.substring(staffFileName.lastIndexOf('.') + 1, staffFileName.length);

                    if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                        var path = GV_IPR.OfficeOnlineUrl + GV_IPR.OnlineUrl + "StaffFiles/StaffFiles/" + staffNo + "/" + staffFileName;
                        window.open(path);
                    }
                    else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                        var path = GV_IPR.OnlineUrl + "StaffFiles/StaffFiles/" + staffNo + "/" + staffFileName;
                        window.open(path);
                    } else {
                        staff.Staff.StaffFile.Download(staffFileId);
                    }

                    return true;
                },
                Download: function (staffFileId) {
                    window.open(  AP_ROOT + AP_PAGE_ID  +"/HR/Staff/StaffFileDownloadByGuid?staffFileGuid=" + staffFileId);
                    return true;
                },
                Delete: function (fileId) {
                    var data = {
                        fileId: fileId,
                    };

                    $.ajaxPost(  AP_ROOT + AP_PAGE_ID  +"/HR/Staff/StaffFileDelete", data, function (response) {
                        if (response.IsSuccess) {
                            staff.Staff.Files.List();
                        }
                    }, true);
                },
            }
        },
        Events: {
            Layout: function () {

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/HR/Staff/StaffEventList", null, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_List").empty();
                        $("#dv_List").html(response.Data);
                        staff.Staff.Events.List();
                        $.closeLoading();
                    }
                }, true);
            },
            List: function () {
                var data = {
                    staffGuid: $("#Staff_StaffBasic_StaffGuid").val()
                };

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/HR/Staff/StaffEvents", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        if (response.Data.length > 0) {
                            $.each(response.Data, function (i, event) {
                                $("tbody", "#tblStaffEventList").addRow(
                                    ++i,
                                    event.Content,
                                    event.OperatorName,
                                    event.OperateTime == null ? '' : getDate(convertJsonDateToJSDate(event.OperateTime)),
                                    "<a style='color:green;' href='javascript:void(0);'><span class='btn_staffevent_add glyphicon glyphicon-plus'></span></a>    "+
                                    "<a style='color:red;' href='javascript:void(0);' onclick='javascript:staff.Staff.Events.Event.Delete(\"" + event.EventId + "\");'><span class='btn_stafffile_remove glyphicon glyphicon-remove'></span></a>"
                                );
                            });
                            $(".simple-grid-none-data-wrap").hide();
                        } else {
                            $(".simple-grid-none-data-wrap").show();
                        }
                        staff.ResetSize();
                        $.closeLoading();
                    }
                }, true);
            },
            Event: {
                Open: function () {

                    var url = AP_ROOT + AP_PAGE_ID + "/HR/Staff/StaffEvent";
                    $.openLoading();

                    $("<div></div>").load(url, null, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#staffEventModal').modal({ backdrop: 'static', keyboard: false });
                        $('#staffEventModal').on('hidden.bs.modal', function () {
                            $("#staffEventModal").remove();
                        });
                    });
                },
                Close: function () {
                    $('#staffEventModal').modal('hide');
                },
                Create: function () {
                    if ($("#StaffEvent_Content").val() == '') {
                        $.showModalMessageBox("请输入事项内容.");
                        return false;
                    }

                    var data = {
                        staffGuid: $("#Staff_StaffBasic_StaffGuid").val(),
                        content: $("#StaffEvent_Content").val(),
                    }

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/HR/Staff/StaffEventCreate", data, function (response) {
                        if (response.IsSuccess) {
                            $('#staffEventModal').modal('hide');
                            staff.Staff.Events.Layout();
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                },

                Delete: function (eventId) {
                    var data = {
                        eventId: eventId,
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/HR/Staff/StaffEventDelete", data, function (response) {
                        if (response.IsSuccess) {
                            staff.Staff.Events.Layout();
                        }
                    }, true);
                },
            },
        },
        OffWorkDay: {
            BindMenu: function () {

                $('#staffContactsGridSection').contextMenu('contactsMenu', {
                    menuStyle: {
                        width: '152px'
                    },

                    itemStyle: {
                        width: '150px'
                    },

                    bindings: {
                        'create': function (t, e) {
                            staff.Staff.OffWorkDay.Open();
                            return true;
                        },
                    },
                    onContextMenu: function (e) {
                        return true;
                    },
                    onShowMenu: function (e, menu) {
                        return menu;
                    }
                });
            },
            List: function (isView) {
                var data = {
                    isView : isView,
                    staffId: $("#Staff_StaffBasic_StaffId").val(),
                    pageNo: $("#PageNo").val(),
                    pageSize: $("#PageSize").val()
                };


                $.ajaxPost(  AP_ROOT + AP_PAGE_ID  +"/HR/Staff/OffWorkDayList", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_List").empty();
                        $("#dv_List").html(response.Data);

                        $(".pull-right.page-box.contacts").cPaging({
                            totalCount: parseInt($("#SearchCondition_TotalCount").val()),
                            pageNo: parseInt($("#SearchCondition_PageNo").val()),
                            pageSize: parseInt($("#SearchCondition_PageSize").val()),
                            callBack: staff.Staff.OffWorkDay.List,
                            callBackArgs: null
                        });

                        var totalCount = parseInt($("#SearchCondition_TotalCount").val());

                        staff.ResetSize();

                        if (totalCount > 0) {
                            $("tfoot", "#tblOffWorkDayList").show();
                            $(".simple-grid-none-data-wrap").hide();
                        } else {
                            $("tfoot", "#tblOffWorkDayList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }

                        staff.Staff.OffWorkDay.BindMenu();

                        $.closeLoading();
                    }
                }, true);
            },
            Open: function () {
                if ($("#Staff_StaffBasic_StaffId").val() == "") {
                    $.showModalMessageBox("请先保存员工基本资料.");
                    return false;
                }
                var data =
                {
                    staffId: $("#Staff_StaffBasic_StaffId").val(),
                };

                var url =   AP_ROOT + AP_PAGE_ID  +"/HR/Staff/OffWorkDay";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);

                    $('#offWorkDayModal').modal({ backdrop: 'static', keyboard: false });
                    $('#offWorkDayModal').on('hidden.bs.modal', function () {
                        $("#offWorkDayModal").remove();
                    });
                });
            },
            /*查看客户*/
            View: function (contactsId) {

                if ($("#Staff_StaffBasic_StaffId").val() == "") {
                    $.showModalMessageBox("请先保存客户基本资料.");
                    return false;
                }

                var data =
                {
                    staffId: $("#Staff_StaffBasic_StaffId").val(),
                    staffNo: $("#Staff_StaffBasic_StaffNo").val(),
                    contactsId: contactsId
                };

                var url =   AP_ROOT + AP_PAGE_ID  +"/HR/OffWorkDay/View";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);

                    $('#staffContactsModal').modal({ backdrop: 'static', keyboard: false });
                    $('#staffContactsModal').on('hidden.bs.modal', function () {
                        $("#staffContactsModal").remove();
                    });
                });
            },
            CreateUpdate: function () {

                if ($("#OffWorkDay_OffWorkBeginDate").val() == '') {
                    $.showModalMessageBox("请输入请假开始时间.");
                    return false;
                }

                if ($("#OffWorkDay_OffWorkEndDate").val() == '') {
                    $.showModalMessageBox("请输入请假结束时间.");
                    return false;
                }

                if ($("#OffWorkDay_OffWorkHours").val() == '') {
                    $.showModalMessageBox("请输入请假小时数.");
                    return false;
                }

                if ($("#OffWorkDay_OffWorkDayType").val() == '') {
                    $.showModalMessageBox("请输入请假类型.");
                    return false;
                }

                $("#offWorkDayForm").ajaxPost(  AP_ROOT + AP_PAGE_ID  +"/HR/Staff/OffWorkDayCreateUpdate", function (response) {
                    if (response.IsSuccess) {
                        $('#offWorkDayModal').modal('hide');
                        staff.Staff.OffWorkDay.List();
                        $.showModalMessageBox("保存成功.");
                    }
                    else {
                        $.showModalMessageBox(response.Message);
                    }
                });

                return true;
            },
            Close: function () {
                $('#offWorkDayModal').modal('hide');
            },
            Delete: function (seqId) {
                var data = {
                    seqId: seqId,
                };

                $.ajaxPost(  AP_ROOT + AP_PAGE_ID  +"/HR/Staff/OffWorkDayDelete", data, function (response) {
                    if (response.IsSuccess) {
                        staff.Staff.OffWorkDay.List(false);
                    }
                }, true);
            },
        },
        Performance: {
            List: function (isView) {
                var data = {
                    isView: isView,
                    staffName: $("#Staff_StaffBasic_StaffName").val(),
                    pageNo: $("#PageNo").val(),
                    pageSize: $("#PageSize").val()
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/HR/Staff/PerformanceList", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_List").empty();
                        $("#dv_List").html(response.Data);
                        $(".pull-right.page-box.performance").cPaging({
                            totalCount: parseInt($("#SearchCondition_TotalCount").val()),
                            pageNo: parseInt($("#SearchCondition_PageNo").val()),
                            pageSize: parseInt($("#SearchCondition_PageSize").val()),
                            callBack: staff.Staff.Performance.List,
                            callBackArgs: null
                        });
                        var totalCount = parseInt($("#SearchCondition_TotalCount").val());
                        staff.ResetSize();
                        if (totalCount > 0) {
                            $("tfoot", "#tblPerformanceList").show();
                            $(".simple-grid-none-data-wrap").hide();
                        } else {
                            $("tfoot", "#tblPerformanceList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                        $.closeLoading();
                    }
                }, true);
            },
            Create: function () {
                if ($("#Staff_StaffBasic_StaffId").val() == "") {
                    $.showModalMessageBox("请先保存员工基本资料.");
                    return false;
                }
                var data =
                {
                    staffName: $("#Staff_StaffBasic_StaffName").val()
                };
                var url = AP_ROOT + AP_PAGE_ID + "/HR/Staff/Performance";
                $.openLoading();
                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#performanceModal').modal({ backdrop: 'static', keyboard: false });
                    $('#performanceModal').on('hidden.bs.modal', function () {
                        $("#performanceModal").remove();
                    });
                });
            },
            Edit: function (settingId) {
                var data =
                {
                    settingId: settingId,
                };
                debugger
                var url = AP_ROOT + AP_PAGE_ID + "/HR/Staff/Performance";
                $.openLoading();
                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#performanceModal').modal({ backdrop: 'static', keyboard: false });
                    $('#performanceModal').on('hidden.bs.modal', function () {
                        $("#performanceModal").remove();
                    });
                });
            },
            View: function (settingId) {
                var data =
                {
                    settingId: settingId
                };
                var url = AP_ROOT + AP_PAGE_ID + "/HR/Performance/View";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#performanceModal').modal({ backdrop: 'static', keyboard: false });
                    $('#performanceModal').on('hidden.bs.modal', function () {
                        $("#performanceModal").remove();
                    });
                });
            },
            CreateUpdate: function () {
                if ($("#Performance_AnnualFrom").val() == '') {
                    $.showModalMessageBox("请输入开始时间.");
                    return false;
                }
                if ($("#Performance_AnnualEnd").val() == '') {
                    $.showModalMessageBox("请输入结束时间.");
                    return false;
                }
                if ($("#Performance_KtRate").val() == '' || !$("#Performance_KtRate").isMoney()) {
                    $.showModalMessageBox("请输入开庭提成.");
                    return false;
                }
                if ($("#Performance_WsRate").val() == '' || !$("#Performance_WsRate").isMoney()) {
                    $.showModalMessageBox("请输入文书提成.");
                    return false;
                }
                if ($("#Performance_AyRate").val() == '' || !$("#Performance_AyRate").isMoney()) {
                    $.showModalMessageBox("请输入案源提成.");
                    return false;
                }
                if ($("#Performance_TcRate").val() == '' || !$("#Performance_TcRate").isMoney()) {
                    $.showModalMessageBox("请输入案源提成.");
                    return false;
                }
                if ($("#Performance_PgRate").val() == '' || !$("#Performance_PgRate").isMoney()) {
                    $.showModalMessageBox("请输入品管提成.");
                    return false;
                }
                if ($("#Performance_PgRate").val() == '' || !$("#Performance_PgRate").isMoney()) {
                    $.showModalMessageBox("请输入基本工资.");
                    return false;
                }
                $("#performanceForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/HR/Staff/PerformanceCreateUpdate", function (response) {
                    if (response.IsSuccess) {
                        $('#performanceModal').modal('hide');
                        staff.Staff.Performance.List();
                        $.showModalMessageBox("保存成功.");
                    }
                    else {
                        $.showModalMessageBox(response.Message);
                    }
                });
                return true;
            },
            Close: function () {
                $('#performanceModal').modal('hide');
            },
            Delete: function (settingId) {
                var data = {
                    settingId: settingId,
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/HR/Staff/PerformanceDelete", data, function (response) {
                    if (response.IsSuccess) {
                        staff.Staff.Performance.List(false);
                    }
                }, true);
            },
        },
        Selected: function (e) {
            if ($(e).prop('checked') == true) {
                $.checkbox.all("chkStaffId");
                $.checkbox.all("chkStaffAll");

            } else {
                $.checkbox.not("chkStaffId");
                $.checkbox.not("chkStaffAll");
            }
        },
    },
};

$(document).ready(function () {

    $("#divUserList").find("li").off().on("click", function (e) {
        var currentSelectedControl = $("#hidUserName").val();
        var currentSelectedIdControl = $("#hidUserId").val();
        if ($(this).attr("id") == 'btnClear') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        $("#" + currentSelectedControl).val(userName);
        $("#" + currentSelectedIdControl).val(userId);
        $("#divUserList").hide();
        return false;
    });

    $(document).click(function () {
        $("#divUserList").off().hide();
        $("#divAssociateUserList").off().hide();
    });

    $(window).resize(function () {
        staff.ResetSize();
    });

    $(document).off('click', '#spanStaffExperience').on('click', '#spanStaffExperience', function () {
        if ($(this).hasClass("icon-down")) {
            $("#divStaffExperience").hide();
            $(this).removeClass("icon-down")
            $(this).addClass("icon-up")
        }
        else if ($(this).hasClass("icon-up")) {
            $("#divStaffExperience").show();
            $(this).removeClass("icon-up")
            $(this).addClass("icon-down")
        }
        staff.ResetSize();
    });

    $(document).off('click', '#spanStaffBasic').on('click', '#spanStaffBasic', function () {
          if ($(this).hasClass("icon-down")) {
            $("#divStaffBasic").hide();
            $(this).removeClass("icon-down")
            $(this).addClass("icon-up")
        }
        else if ($(this).hasClass("icon-up")) {
            $("#divStaffBasic").show();
            $(this).removeClass("icon-up")
            $(this).addClass("icon-down")
        }
        staff.ResetSize();
    });

    $(document).off('click', '#btnStaffCreateUpdate').on('click', '#btnStaffCreateUpdate', function () {
        staff.Staff.CreateUpdate();
    });

    $(document).off('click', '#btnOffWorkDayCreate').on('click', '#btnOffWorkDayCreate', function () {
        staff.Staff.OffWorkDay.Open();
    });

    $(document).off('click', '#btnOffWorkDayCancel,#btnOffWorkDayClose').on('click', '#btnOffWorkDayCancel,#btnOffWorkDayClose', function () {
        staff.Staff.OffWorkDay.Close();
    });

    $(document).off('click', '#btnOffWorkDayCreateUpdate').on('click', '#btnOffWorkDayCreateUpdate', function () {
        staff.Staff.OffWorkDay.CreateUpdate();
    });

    $(document).off('click', '#btnStaffFileCreate').on('click', '#btnStaffFileCreate', function () {
        staff.Staff.Files.File.Open();
    });

    $(document).off('click', '#btnStaffFileUploadCancel,#btnStaffFileUploadClose').on('click', '#btnStaffFileUploadCancel,#btnStaffFileUploadClose', function () {
        staff.Staff.Files.File.Close();
    });

    $(document).off('click', '#txtStaffFile').on('click', '#txtStaffFile', function () {
        $("#txtStaffFilePath").val($("#txtStaffFile").val());
    });

    $(document).off('click', '#btnStaffFileUpload').on('click', '#btnStaffFileUpload', function () {
        staff.Staff.Files.File.Upload();
    });

    $(document).off('click', '#btnStaffSearch').on('click', '#btnStaffSearch', function () {
        staff.Staff.List.StaffList();
    });

    $(document).off('click', '#btnPerformanceCreateUpdate').on('click', '#btnPerformanceCreateUpdate', function () {
        staff.Staff.Performance.CreateUpdate();
    });
    
 
});