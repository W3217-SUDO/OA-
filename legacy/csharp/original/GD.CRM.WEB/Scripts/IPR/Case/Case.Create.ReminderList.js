var caseReminder = {
    BindMenu: function () {
        $('div.product-nav-list').contextMenu('caseReminderMenu', {
            bindings: {
                'create': function (t, e) {
                    caseReminder.Open();
                },
                'modify': function (t, e) {
                    var reminderTypeId = $(e).find("span").html();
                    if (reminderTypeId == '') {
                        $.showModalMessageBox("请选中配置项修改.");
                        return false;
                    }
                    caseReminder.Open(reminderTypeId);
                },
                'delete': function (t, e) {
                    var reminderTypeId = $(e).find("span").html();
                    caseReminder.Delete(reminderTypeId);
                }
            },
            onContextMenu: function (e) {
                return true;
            },
            onShowMenu: function (e, menu) {
                if ($(e.target).parents("a").find(".nav-icon").hasClass("nav-icon")) {
                    var reminderTypeId = $(e.target).parents("a").find("#item_ReminderTypeId").val();
                   
                    $('#modify', menu).append("<span style='display:none'>" + reminderTypeId + "</span>");
                    $('#delete', menu).append("<span style='display:none'>" + reminderTypeId + "</span>");
                }
                else {
                    $('#modify,#delete', menu).remove();
                }
                return menu;
            }
        });
    },

    Open: function (caseSearchId) {
        var data = {
            caseSearchId: caseSearchId
        };
         
        var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/BizCaseSearchCondition";
        $.openLoading();
        $('.casesearch').load(url, data, function (result) {
            $.closeLoading();
            $('#caseSearchModal').modal({ backdrop: 'static', keyboard: false });
        });
    }

}
$(document).ready(function () {
    $(".J-drop-menu").each(function () {
        $(this).children("a").each(function () {
            $(this).click(function () {
                $("a", ".top-level").each(function () {
                    $(this).removeClass("active");
                });
                $(this).addClass("active");
                if ($(this).find("span").hasClass("icon-arrow-down")) {
                    $(this).find("span").attr("class", "icon-arrow-right");
                }
                else if ($(this).find("span").hasClass("icon-arrow-right")) {
                    $(this).find("span").attr("class", "icon-arrow-down");

                    $("#hidCaseReminderTypeId").val($("#item_ReminderTypeId", this).val());

                    var data = {
                        caseReminderTypeId: $("#item_ReminderTypeId", this).val()
                    }
                    var tigger = $(this.parentElement);
                    $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/GetCasesByReminderType", data, function (response) {
                        if (!response.IsSuccess) {
                            $.showModalMessageBox(response.Message);
                            return false;
                        }
                        if (response.Data == null) {
                            return false;
                        }
                        var html = "";

                        $.each(response.Data, function (i, c) {
                            var deadlinestyle = 'deadline-leftdays-normal';
                            if (c.CaseBasicInfo.DeadlineLeftDays <5 ) {
                                deadlinestyle = 'deadline-leftdays-warning-red';
                            }
                            else if (c.CaseBasicInfo.DeadlineLeftDays < 10) {
                                deadlinestyle = 'deadline-leftdays-warning';
                            }  
                            else if (c.CaseBasicInfo.DeadlineLeftDays >= 10) {
                                deadlinestyle = 'deadline-leftdays-normal';
                            }

                            html += "<li><div><a href='javascript:void(0);'><span style='display:none'>" + c.CaseBasicInfo.CaseId + "</span><div class='nav-icon'></div><div class='nav-text-indent'>" + c.CaseBasicInfo.CaseNo + "</div></a><div class='nav-extend'><span class='ng-isolate-scope'><span id='spanCaseBasicInfoCaseId_" + c.CaseBasicInfo.CaseId + "' class='" + deadlinestyle + " ng-scope ng-binding'>" + c.CaseBasicInfo.DeadlineLeftDays + "</span></span></div></div></li>";

                        });

                        $("ul", tigger).empty();
                        $("ul", tigger).css("display", "block");
                        $("ul", tigger).html(html);

                        $("ul", tigger).each(function () {
                            $("a", this).each(function () {
                                $(this).click(function () {

                                    var caseListSelectedTypeId = 1;

                                    if ($("#liARCaseFeeList").attr("class") == 'active') {
                                        caseListSelectedTypeId = 2;
                                    }
                                    else if ($("#liAPCaseFeeList").attr("class") == 'active') {
                                        caseListSelectedTypeId = 3;
                                    }
                                    else if ($("#liCaseAssistedFeeList").attr("class") == 'active') {
                                        caseListSelectedTypeId = 4;
                                    }
                                    else if ($("#liCaseCustomerContactsList").attr("class") == 'active') {
                                        caseListSelectedTypeId = 5;
                                    }
                                    else if ($("#liCaseLogList").attr("class") == 'active') {
                                        caseListSelectedTypeId = 6;
                                    }
                                    else if ($("#liCaseTaskList").attr("class") == 'active') {
                                        caseListSelectedTypeId = 7;
                                    }
                                    else {
                                        caseListSelectedTypeId = 1;
                                    }

                                    var caseId = {
                                        caseId: $("span", this).html(),
                                        caseListSelectedTypeId : caseListSelectedTypeId
                                    }
                                    $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseInfo", caseId, function (response) {
                                        $(".viewFramework-product-body").html("");
                                        if (!response.IsSuccess) {
                                            $.showModalMessageBox(response.Message);
                                            return false;
                                        }
                                        if (response.Data == null) {
                                            return false;
                                        }
                                        $(".viewFramework-product-body").html(response.Data);
                                    });

                                    $("a", ".top-level").each(function () {
                                        $(this).removeClass("active");
                                    });

                                    $(this).addClass("active");
                                });
                            });
                        });
                    });
                };
                $(this.parentElement).find("ul").each(function () {
                    if ($(this).css("display") == "none") {
                        $(this).css("display", "block");
                    }
                    else {
                        $(this).css("display", "none");
                    };
                });
            });
        });
    });

    $("#btnCaseList").off().on("click", function () {
        var reminderTypeId = $("#hidCaseReminderTypeId").val();
        this.href =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseList?reminderTypeId=" + reminderTypeId;
    });
    
    //caseReminder.BindMenu();
});