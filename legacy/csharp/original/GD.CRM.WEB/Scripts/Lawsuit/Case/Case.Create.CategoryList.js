var caseCategory = {
    BindMenu: function() {
        $('div.product-nav-list').contextMenu('caseCategoryMenu', {
            bindings: {
                'create': function(t, e) {
                    caseCategory.Open();
                },
                'modify': function(t, e) {
                    var categoryTypeId = $(e).find("span").html();
                    if (categoryTypeId == undefined) {
                        $.showModalMessageBox("请选中配置项修改.");
                    } else {
                        caseCategory.Open(categoryTypeId);
                    }
                },
                'delete': function(t, e) {
                    var categoryTypeId = $(e).find("span").html();
                    if (categoryTypeId == undefined) {
                        $.showModalMessageBox("请选中配置项修改.");
                    } else {
                        caseCategory.Delete(categoryTypeId);
                    }
                }
            },
            onContextMenu: function(e) {
                return true;
            },
            onShowMenu: function(e, menu) {
                if ($(e.target).parents("a").find(".nav-icon").hasClass("nav-icon")) {
                    var categoryTypeId = $(e.target).parents("a").find("#item_CategoryTypeId").val();
                    if (categoryTypeId == undefined) {
                        $('#modify', menu).remove();
                        $('#delete', menu).remove();
                    } else {
                        $('#modify', menu).append("<span style='display:none'>" + categoryTypeId + "</span>");
                        $('#delete', menu).append("<span style='display:none'>" + categoryTypeId + "</span>");
                    }
                } else {
                    $('#modify', menu).remove();
                    $('#modify', menu).remove();
                }
                return menu;
            }
        });
    },

    Open: function(caseSearchId) {
        var data = {
            searchConditionId: caseSearchId
        };

        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/GetCaseSearchCondition", data, function(response) {
            if (response.IsSuccess) {
                searchCondition.Init();
                searchCondition.InitCaseSearchCondition($.parseJSON(response.Data));
                $(".caseadvancedsearch").css('display', 'block');
                $('#caseSearchModal').modal({ backdrop: 'static', keyboard: false });
            }
        });
    }
}
$(document).ready(function () {

    $("#btnCaseList").off().on("click", function () {
        var categoryTypeId = $("#hidCaseCategoryTypeId").val();
        this.href =  AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/CaseList?categoryTypeId=" + categoryTypeId;
    });

    $(".J-drop-menu").each(function () {
        $(this).children("a").each(function () {
            $(this).click(function () {
                $("a", ".top-level").each(function () {
                    $(this).removeClass("active");
                });
                $(this).addClass("active");
                if ($(this).find("span").hasClass("icon-arrow-right")) {
                    $(this).find("span").attr("class", "icon-arrow-down");
                }
                else if ($(this).find("span").hasClass("icon-arrow-down")) {
                    $(this).find("span").attr("class", "icon-arrow-right");

                    $("#hidCaseCategoryTypeId").val($("#item_CategoryTypeId", this).val());

                    var data = {
                        caseCategoryTypeId: $("#item_CategoryTypeId", this).val()
                    }
                    var tigger = $(this.parentElement);
                    $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/GetCasesByCategoryType", data, function (response) {
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
                            if (c.CaseBasicInfo.DeadlineLeftDays < 5) {
                                deadlinestyle = 'deadline-leftdays-warning-red';
                            }
                            else if (c.CaseBasicInfo.DeadlineLeftDays < 10) {
                                deadlinestyle = 'deadline-leftdays-warning';
                            }
                            else if (c.CaseBasicInfo.DeadlineLeftDays >= 10) {
                                deadlinestyle = 'deadline-leftdays-normal';
                            }

                            if (c.CaseBasicInfo.CasePhaseId == 97 || c.CaseBasicInfo.CasePhaseId == 98 || c.CaseBasicInfo.CasePhaseId == 99) {

                                deadlinestyle = 'deadline-leftdays-warning-green';
                                html += "<li><div><a href='javascript:void(0);'><span style='display:none'>" + c.CaseBasicInfo.CaseId + "</span><div class='nav-icon'></div><div class='nav-text-indent'>" + c.CaseBasicInfo.CaseNo + "</div></a><div class='nav-extend'><span class='ng-isolate-scope'><span id='spanCaseBasicInfoCaseId_" + c.CaseBasicInfo.CaseId + "' class='" + deadlinestyle + " ng-scope ng-binding'>" + 0 + "</span></span></div></div></li>";
                            }
                            else {

                                html += "<li><div><a href='javascript:void(0);'><span style='display:none'>" + c.CaseBasicInfo.CaseId + "</span><div class='nav-icon'></div><div class='nav-text-indent'>" + c.CaseBasicInfo.CaseNo + "</div></a><div class='nav-extend'><span class='ng-isolate-scope'><span id='spanCaseBasicInfoCaseId_" + c.CaseBasicInfo.CaseId + "' class='" + deadlinestyle + " ng-scope ng-binding'>" + c.CaseBasicInfo.DeadlineLeftDays + "</span></span></div></div></li>";
                            }

                        });

                        $("ul", tigger).empty();
                        $("ul", tigger).css("display", "block");
                        $("ul", tigger).html(html);

                        $("ul", tigger).each(function () {
                            $("a", this).each(function () {
                                $(this).click(function () {
                                    var caseId = {
                                        caseId: $("span", this).html()
                                    }
                                    $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/CaseInfo", caseId, function (response) {
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

    //caseCategory.BindMenu();
});