
var cashedRegister = {
    Init: function () {
        cashedRegister.bindEvent();
    },

    bindEvent: function () {
        this.Customer = function (trigger) {
            var ctlname = $(trigger);
            //var div = ;
            var ctlid = $(trigger).parents("tr").find(".item_CustomerId");

            var name = ctlname.val();
            if ($.trim(name) == "") { return false; }
            var curobj = new Object();
            curobj.keyword = name;
            $.ajaxPost(AP_ROOT + "CRM/Customer/CustomerList", curobj, function (response) {
                $("#div_customer").find(".i_common_list").empty();
                if (response.IsSuccess) {
                    if (response.Data) {
                        var html = "";
                        $.each(response.Data.Customers, function (i, c) {
                            html += '<a href="javascript:void(0)" customerid=' + c.CustomerId + ' customerno=' + c.CustomerNo + ' >' + c.CustomerName + '</a>';
                        });

                        $("#div_customer").find(".i_common_list").html(html);
                        $("#div_customer").find(".i_common_list a").click(function () {

                            $(ctlid).parents("tr").find("#item_CustomerNo").val($(this).attr("customerno"));
                            $(ctlid).parents("tr").find("#item_CustomerId").val($(this).attr("customerid"));
                            $(ctlname).val($(this).text());

                            $("#div_customer").hide();
                        });
                    }
                }
                else {
                    $.showModalMessageBox(response.Message);
                }
            }, false);

            $("#div_customer").css({
                "position": "absolute",
                "left": $(trigger).position().left + 12,
                "top": $(trigger).position().top + 115,
                "z-index": 9999
            }).show();
        }
        $(".item_CustomerName").die().bind('keyup', { obj: this }, function (event) {
            var trigger = $(this);
            var div = $("#divCustomer");
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
                event.data.obj.Event = setTimeout(function () { event.data.obj.Customer(trigger); }, 500);
            }
        });
        $(".item_CustomerName").die().bind('blur', { obj: this }, function (event) {

            var ctlid = $(this).parents("tr").find(".item_CustomerId");
            var ctlno = $(this).parents("tr").find(".item_CustomerNo");

            if ($(this).val() == "" || ($(this).val() == $(this).attr("mod-notice-tip"))) {
                $(ctlid).val("");
                $(ctlno).val("");
            }
            if ($(ctlid).val() == "") {
                if ($(this).attr("mod-notice-tip")) {
                    $(this).val($(this).attr("mod-notice-tip"));
                } else {
                    $(this).val("");
                }
            }

        });
    },

    Item: {
        Add: function () {
            var tr = $($('#tblCashedFeeItemList>tbody>tr')[0]).clone().show();
            $(tr).find(":input[type='text']").val('');
            $(tr).find(":input[type='hidden']").val('');
            $(tr).find(":input[type='checkbox']").attr("checked", false);
            $("#tblCashedFeeItemList").append(tr);
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

    Create: function () {

        var data = {};

        $("#tblCashedFeeItemList>tbody>tr").each(function(i, e) {
            data["CashedList[" + i + "].CustomerId"] = $(e).find("#item_CustomerId").val();
            data["CashedList[" + i + "].CustomerNo"] = $(e).find("#item_CustomerNo").val();
            data["CashedList[" + i + "].CashedDate"] = $(e).find("#item_CashedDate").val();
            data["CashedList[" + i + "].Amount"] =  $(e).find("#item_Amount").val();
            data["CashedList[" + i + "].PaymentMode"] =  $(e).find("#item_PaymentMode").val();
            data["CashedList[" + i + "].BillNo"] = $(e).find("#item_BillNo").val();
            data["CashedList[" + i + "].Remark"] = $(e).find("#item_Remark").val();

        });

        $.ajaxPost(AP_ROOT + "FAM/Cashed/CashedRegister", data, function (response) {
            if (response.IsSuccess) {
                $('#cashedRegisterModal').modal('hide');
                $.showModalMessageBox("保存成功.");
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    Close: function() {
        $('#cashedRegisterModal').modal('hide');
    }
};

$(document).ready(function() {

    $(document).click(function() {

    });

    $(function() {
        $('.viewFramework-product-body').slimScroll({
            height: '100%'
        });
    });

    $("#btnCashedRegisterCreate").click(function () {
        cashedRegister.Create();
    });

    $(".btn_cashed_add").die().live("click", function () {
        cashedRegister.Item.Add();
        cashedRegister.bindEvent();
    });

    $(".btn_cashed_remove").die().live("click", function () {
        cashedRegister.Item.Remove(this);
    });

    $("#btnCashedRegisterCancel,#btnCashedRegisterClose").die().live("click", function() {
        cashedRegister.Close();
    });

    $(".item_ContractNo").die().live("keypress", function () {
        if (event.keyCode == 13) {
            if ($(this).val() == '') return false;
            //$.case.getContract($(this), $(this).val(), ar.ARObject.getCaseBasicCallBack);
        }
    });

    cashedRegister.Init();
});