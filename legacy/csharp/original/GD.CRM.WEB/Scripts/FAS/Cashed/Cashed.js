function AssociateCustomer(div, ctlid, ctlname) {
    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;

    this.Customer = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") { return false; }
        var curobj = new Object();
        curobj.keyword = name;
        $.ajaxPost(AP_ROOT + "CRM/Customer/CustomerList", curobj, function (response) {
            $(div).find(".i_common_list").empty();
            if (response.IsSuccess) {
                if (response.Data) {
                    var html = "";
                    $.each(response.Data.Customers, function (i, c) {
                        html += '<a href="javascript:void(0)" customerno=' + c.CustomerNo + ' >' + c.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").click(function () {
                        $(ctlid).val($(this).attr("customerno"));
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
            "top": $(ctlname).position().top + 110,
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

var gl = {
    Init: function () {
        gl.Cashed.List();
        gl.CashUnsettled.List();
    },

    ResetSize: function () {

        if ($("#divLeftContextList").length > 0) {
            $("#divLeftContextList").css("height", $(window).height() - $("#divLeftContextList").offset().top - 18);
        }
        if ($("#divRightContextList").length > 0) {
            $("#divRightContextList").css("height", $(window).height() - $("#divRightContextList").offset().top - 18);
        }
    },
 
    /*到账信息*/
    Cashed: {
        Init: function () {
            gl.Cashed.List();
        },

        List: function () {
            var data = {
                CustomerNo: $("#CashedSearchCondition_CustomerNo").val(),
                ContractNo: $("#CashedSearchCondition_ContractNo").val(),
                CashedDateStart: $("#CashedSearchCondition_CashedDateStart").val(),
                CashedDateEnd: $("#CashedSearchCondition_CashedDateEnd").val(),
                PageNo: $("#CashedSearchCondition_PageNo").val(),
                PageSize: $("#CashedSearchCondition_PageSize").val()
            };

            $.ajaxPost(AP_ROOT + "FAM/Cashed/CashedList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $("#dv_Left_List").empty();
                    $("#dv_Left_List").html(response.Data);

                    $(".pull-right.page-box.cashedlist").cPaging({
                        totalCount: parseInt($("#CashedSearchCondition_TotalCount").val()),
                        pageNo: parseInt($("#CashedSearchCondition_PageNo").val()),
                        pageSize: parseInt($("#CashedSearchCondition_PageSize").val()),
                        callBack: gl.Cashed.List,
                        callBackArgs: null
                    });

                    var totalCount = parseInt($("#CashedSearchCondition_TotalCount").val());

                    gl.ResetSize();

                    if (totalCount > 0) {
                        $("tfoot", "#tblCashedList").show();
                        $(".simple-grid-none-data-wrap.cashedlist").hide();
                    } else {
                        $("tfoot", "#tblCashedList").hide();
                        $(".simple-grid-none-data-wrap.cashedlist").show();
                    }
                    $.closeLoading();
                }

            }, true);
        },

        Apply: function () {
            /*到账分配*/
            var cashedIds = $.checkbox.vals("chkCashedId");
            if (cashedIds.length >1) {
                $.showModalMessageBox("只允许同时一条到账信息分配.");
                return false;
            }
            
            var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
            if (caseFeeIds.length == 0) {
                $.showModalMessageBox("请选择未确认的费用信息.");
                return false;
            }

            var data = {
                cashedId: cashedIds[0],
                caseFeeIds: caseFeeIds
            };

            $.ajaxPost(AP_ROOT + "FAM/Cashed/CashedApply", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("分配成功.");
                    gl.Cashed.List();
                    gl.CashUnsettled.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

    },


    /*未确认费用信息*/
    CashUnsettled: {
        Init: function () {
            gl.CashUnsettled.List();
        },

        List: function () {
            var data = {
                CustomerNo: $("#CashedSearchCondition_CustomerNo").val(),
                ContractNo: $("#CashUnsettledSearchCondition_ContractNo").val(),
                CaseNo: $("#CashUnsettledSearchCondition_CaseNo").val(),
                CaseFeeTypeId: $("#CashUnsettledSearchCondition_CaseFeeTypeId").val(),
                PageNo: $("#CashUnsettledSearchCondition_PageNo").val(),
                PageSize: $("#CashUnsettledSearchCondition_PageSize").val()
            };

            $.ajaxPost(AP_ROOT + "FAM/Cashed/CashUnsettledList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $("#dv_Right_List").empty();
                    $("#dv_Right_List").html(response.Data);

                    $(".pull-right.page-box.cashUnsettledList").cPaging({
                        totalCount: parseInt($("#CashUnsettledSearchCondition_TotalCount").val()),
                        pageNo: parseInt($("#CashUnsettledSearchCondition_PageNo").val()),
                        pageSize: parseInt($("#CashUnsettledSearchCondition_PageSize").val()),
                        callBack: gl.CashUnsettled.List,
                        callBackArgs: null
                    });

                    var totalCount = parseInt($("#CashUnsettledSearchCondition_TotalCount").val());

                    gl.ResetSize();

                    if (totalCount > 0) {
                        $("tfoot", "#tblCashUnsettledList").show();
                        $(".simple-grid-none-data-wrap.cashUnsettledList").hide();
                    } else {
                        $("tfoot", "#tblCashUnsettledList").hide();
                        $(".simple-grid-none-data-wrap.cashUnsettledList").show();
                    }
                    $.closeLoading();
                }

            }, true);
        },
    },
};
 
$(document).ready(function() {

    var customter = new AssociateCustomer(
     $("#div_customer"),
     $("#CashedSearchCondition_CustomerNo"),
     $("#CashedSearchCondition_CustomerName")
    );

    $(window).resize(function () {
        gl.ResetSize();
    });

    $(document).click(function() {

    });

    $(function() {
        $('.viewFramework-product-body').slimScroll({
            height: '100%'
        });
    });

    $("#btnCashedRegister").click(function () {
        gl.CashedRegister.Open();
    });

    $("#btnCashedRegisterCancel,#btnCashedRegisterClose").die().live("click", function() {
        gl.CashedRegister.Close();
    });

    $("#btnCashedListSearch").die().live("click", function () {
        gl.Cashed.List();
    });

    $("#btnCashUnsettledListSearch").die().live("click", function () {
        gl.CashUnsettled.List();
    });

    $("#btnCashedFeeApply").die().live("click", function () {
        gl.Cashed.Apply();
    });

    gl.Init();
});