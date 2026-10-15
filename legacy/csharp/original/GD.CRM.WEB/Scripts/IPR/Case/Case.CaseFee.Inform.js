/*批量下费用通知*/

function AssociateCustomer(div, ctlid, ctlname) {
    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;

    this.Customer = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") { return false; }
        var curobj = new Object();
        curobj.keyword = name;
        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CustomerList", curobj, function (response) {
            $(div).find(".i_common_list").empty();
            if (response.IsSuccess) {
                if (response.Data) {
                    var html = "";
                    $.each(response.Data.Customers, function (i, c) {
                        html += '<a href="javascript:void(0)" customerid=' + c.CustomerBasic.CustomerId + ' >' + c.CustomerBasic.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").click(function () {
                        $(ctlid).val($(this).attr("customerId"));
                        $(ctlname).val($(this).text());
                        $(div).hide();
                    });
                }
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        }, false);

        $(div).css({
            "position": "absolute",
            "left": $(ctlname).position().left + 15,
            "top": $(ctlname).position().top + 110
        }).toggle();
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
        //        if (event.data.obj.GlobalName != "") {
        //            $(this).val(event.data.obj.GlobalName);
        //            $(ctlid).val(event.data.obj.GlobalID);
        //        }
    });

    return this;
}

var caseFeeInform = {
    Close: function() {
        $('#caseFeeInformModal').modal('hide');
    },

    getCaseBasicCallBack: function (response, trigger) {

        if (typeof (response) == "undefined" || response == null) {
            return false;
        }

        if (typeof (trigger) == "undefined" || trigger == null) {
            return false;
        }

        $(trigger).parents("tr").find("#item_CaseNo").val(response.Data.CaseBasicInfo.CaseNo);
        $(trigger).parents("tr").find("#item_CaseRequestNo").val(response.Data.CaseBasicInfo.CaseRequestNo);
    },

CaseFeeItem: {
        Add: function () {
            var tr = null;
            $("#tblCaseFeeItemList").find("tr").each(function () {
                if ($(this).css("display") == "none") {
                    tr = $(this).clone().show();
                }
            });
            $("#tblCaseFeeItemList").append(tr);
            return tr;
        },
        Clear: function (e) {
            $(e).parents("tr").find(":input[type='text']").val('');
            $(e).parents("tr").find(":input[type='checkbox']").attr("checked", false);
        },
        Remove: function (e) {
            $(e).parents("tr").remove();
        }
    }
}

$(document).ready(function () {

    $(document).click(function (e) {});

    $("#btnCaseFeeInformCancel,#btnCaseFeeInformClose").off().on("click", function () {
        caseFeeInform.Close();
    });

    $("#btnCaseFeeInform").off().on("click", function () {
        //caseFeeList.CaseFeeListBillConfirmCreate();
    });

    $("#btnCaseFeeInformAddItem").off().on("click", function () {
        caseFeeInform.CaseFeeItem.Add();
    });

    $(".btn_clear").off().on("click", function () {
        caseFeeInform.CaseFeeItem.Clear(this);
    });

    $(".btn_remove").off().on("click", function () {
        caseFeeInform.CaseFeeItem.Remove(this);
    });

    $(".CaseFeeInform_CaseNo").off().on("keypress", function () {
        if (event.keyCode == 13) {
            if ($(this).val() == '') return false;
            $.case.getCaseBasicByCaseNo($(this), $(this).val(), caseFeeInform.getCaseBasicCallBack);
        }
    });

    $(".CaseFeeInform_CaseRequestNo").off().on("keypress", function () {
        if (event.keyCode == 13) {
            if ($(this).val() == '') return false;
            $.case.getCaseBasicByCaseRequestNo($(this), $(this).val(), caseFeeInform.getCaseBasicCallBack);
        }
    });
});


