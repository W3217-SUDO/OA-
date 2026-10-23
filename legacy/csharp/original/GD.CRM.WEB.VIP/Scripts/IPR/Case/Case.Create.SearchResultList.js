$(document).ready(function () {
    //$(".J-drop-menu").each(function () {
    //    $(this).children("a").each(function () {
    //        $(this).click(function () {
    //            $("a", ".top-level").each(function () {
    //                $(this).removeClass("active");
    //            });
    //            $(this).addClass("active");
    //            if ($(this).find("span").hasClass("icon-arrow-down")) {
    //                $(this).find("span").attr("class", "icon-arrow-right");
    //            }
    //            else if ($(this).find("span").hasClass("icon-arrow-right")) {
    //                $(this).find("span").attr("class", "icon-arrow-down");
 
    //            };
    //            $(this.parentElement).find("ul").each(function () {
    //                if ($(this).css("display") == "none") {
    //                    $(this).css("display", "block");
    //                }
    //                else {
    //                    $(this).css("display", "none");
    //                };
    //            });
    //        });
    //    });
    //});


    $("ul", ".J-drop-menu").each(function () {
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
                    caseListSelectedTypeId: caseListSelectedTypeId
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