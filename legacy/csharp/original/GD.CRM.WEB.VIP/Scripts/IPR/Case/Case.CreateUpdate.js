function AssociateCustomer(div, ctlid, ctlno, ctlname) {
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
                        html += '<a href="javascript:void(0)" customerid=' + c.CustomerBasic.CustomerId + ' customerno=' + c.CustomerBasic.CustomerNo + ' >' + c.CustomerBasic.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").click(function () {
                        $(ctlid).val($(this).attr("customerid"));
                        $(ctlno).val($(this).attr("customerno"));
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
            "left": $(ctlname).position().left + 2,
            "top": $(ctlname).position().top + 28,
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
        //        if (event.data.obj.GlobalName != "") {
        //            $(this).val(event.data.obj.GlobalName);
        //            $(ctlid).val(event.data.obj.GlobalID);
        //        }
    });

    return this;
}

var cases = {

    Init: function () {
        cases.List();
    },

    /*案件列表*/
    List: function () {
        var data = {
        };

        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/MultiCaseList", data, function (response) {
            if (response.IsSuccess) {
                $.openLoading();
                $("#dv_List").empty();
                $("#dv_List").html(response.Data);

                cases.ResetSize();
                $.closeLoading();
            }
        }, true);
    },

    ResetSize: function () {
        if ($("#divContextList").length > 0) {
            $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 22);
        }
    },

    CreateUpdate: function () {
        var data = {};

        if ($("#CustomerNo").val() == '') {
            $.showModalMessageBox("请选择客户.");
            return false;
        }

        $("#tblCaseList>tbody>tr").each(function (i, e) {


            data["Cases[" + i + "].CaseBasicInfo.Customer"] = $("#CustomerId").val();
            data["Cases[" + i + "].CaseBasicInfo.CustomerId"] = $("#CustomerId").val();
            
            data["Cases[" + i + "].CaseBasicInfo.Customer"] = $("#CustomerId").val();
 
            data["Cases[" + i + "].CaseBasicInfo.CaseTypeId"] = $(e).find("#item_CaseBasicInfo_CaseTypeId").val();
            data["Cases[" + i + "].CaseBasicInfo.CasePhaseId"] = $(e).find("#item_CaseBasicInfo_CasePhaseId").val();

            data["Cases[" + i + "].CaseBasicInfo.CaseRegisterDate"] = $(e).find("#item_CaseBasicInfo_CaseRegisterDate").val();
            data["Cases[" + i + "].CaseBasicInfo.Deadline"] = $(e).find("#item_CaseBasicInfo_Deadline").val();
        });
 
        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/MultiCaseCreateUpdate", data, function (response) {
            if (response.IsSuccess) {
                $("#tblCaseList>tbody>tr").each(function (i, e) {
                    $(e).find("#item_CaseBasicInfo_CaseNo").val(response.Data[i]);
                });

                $("#btnCaseCreateUpdate").attr("disabled", "true");
                $("#btnCaseCreateNew").removeAttr("disabled");

                $.showModalMessageBox("批量创建案件成功.");
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    Case: {

        Init: function () {
         },

        ObjectItem: {
            Add: function () {
                var tr = $($('#tblCaseList>tbody>tr')[0]).clone().show();

                $("#tblCaseList").append(tr);
                return tr;
            },
            Clear: function (e) {
                $(e).parents("tr").find(":input[type='text']").val('');
                $(e).parents("tr").find(":input[type='hidden']").val('');
                $(e).parents("tr").find(":input[type='checkbox']").attr("checked", false);
            },
            Remove: function (e) {
                $(e).parents("tr").remove();
            }
        },

        getCaseBasicCallBack: function (response, trigger) {

            if (typeof (response) == "undefined" || response == null) {
                return false;
            }

            if (typeof (trigger) == "undefined" || trigger == null) {
                return false;
            }

            $(trigger).parents("tr").find("#item_CaseId").val(response.Data.CaseBasicInfo.CaseId);
            $(trigger).parents("tr").find("#item_CaseNo").val(response.Data.CaseBasicInfo.CaseNo);
            $(trigger).parents("tr").find("#item_CaseRequestNo").val(response.Data.CaseBasicInfo.CaseRequestNo);

            if (response.Data.CaseBasicInfo.CaseRequestDate == null) {
                $(trigger).parents("tr").find("#item_CaseRequestDate").val('');
            } else {
                $(trigger).parents("tr").find("#item_CaseRequestDate").val(getDate(convertJsonDateToJSDate(response.Data.CaseBasicInfo.CaseRequestDate)));
            }

            if (response.Data.CaseBasicInfo.CustomerId != null
                && response.Data.CaseBasicInfo.CustomerId != ''
                && $("#Ar_CustomerId").val() != ''
                && $("#Ar_CustomerId").val() != response.Data.CaseBasicInfo.CustomerId) {
                $.showModalMessageBox("输入的案号,不属该客户下的案件,请重新输入.", null, true);
                return false;
            }
        },

    },
};


$(document).ready(function () {

    var customter = new AssociateCustomer(
     $("#div_customer"),
     $("#CustomerId"),
     $("#CustomerNo"),
     $("#CustomerName")
    );

    $("#btnCaseCreateUpdate").removeAttr("disabled");
    $("#btnCaseCreateNew").attr("disabled", "true");

    $(window).resize(function () {
        cases.ResetSize();
    });

    $(document).click(function () {

    });

    $(function () {
        $('.viewFramework-product-body').slimScroll({
            height: '100%'
        });
    });

    $(".btn_ar_add").off().on("click", function () {
        cases.Case.ObjectItem.Add();
    });

    $(".btn_ar_remove").off().on("click", function () {
        cases.Case.ObjectItem.Remove(this);
    });
 
    $("#btnCaseCreateUpdate").off().on("click", function () {
        cases.CreateUpdate();
    });

    $("#btnCaseCreateNew").off().on("click", function () {
        window.location.reload();
    });
    
     cases.Init();
});