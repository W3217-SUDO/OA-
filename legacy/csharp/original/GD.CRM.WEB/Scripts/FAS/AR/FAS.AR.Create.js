
function AssociateCustomer(div, ctlid,ctlno, ctlname) {
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
                        html += '<a href="javascript:void(0)" customerid=' + c.CustomerId +' customerno=' + c.CustomerNo + ' >' + c.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").click(function () {
                        $(ctlid).val($(this).attr("customerid"));
                        $(ctlno).val($(this).attr("customerno"));
                        $(ctlname).val($(this).text());
                        $(div).hide();

                        ar.Contract.List($(ctlid).val());
                    });
                }
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        }, false);

        $(div).css({
            "position": "absolute",
            "left": $(ctlname).position().left + 8,
            "top": $(ctlname).position().top + 42,
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

var ar = {
    Init: function () {

        ar.ARObject.List();
    },

    ResetSize: function () {
        if ($("#divContextList").length > 0) {
            $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 22);
        }
    },
 
    CreateUpdate: function () {
        var data = {};

        var dataIsNOk = false;

        if ($("#Ar_CustomerNo").val() == '') {
            $.showModalMessageBox("请选择客户.");
            return false;
        }

        if ($("#Ar_ContractNo").val() == '' && $("#Ar_ContractNo").val() == '-1') {
            $.showModalMessageBox("请选择合同.");
            return false;
        }

        var caseIds = $.checkbox.vals("chkCaseId");
        if (caseIds.length == 0) {
            $.showModalMessageBox("请选择应收账款.");
            return false;
        }

        var i = 0;
        $("#tblARObjectList>tbody>tr").each(function (j, e) {
            if ($(e).css("display") != 'none' && $(e).find("#chkCaseId").attr("checked") == 'checked') {
                if ($(e).find("#chkCaseId").val() != 'null') {

                    data["ArObjects[" + i + "].CaseId"] = $(e).find("#chkCaseId").val();
                    data["ArObjects[" + i + "].CaseNo"] = $(e).find("#item_CaseNo").val();

                    data["ArObjects[" + i + "].CustomerId"] = $("#Ar_CustomerId").val();
                    data["ArObjects[" + i + "].CustomerNo"] = $("#Ar_CustomerNo").val();

                    data["ArObjects[" + i + "].ContractId"] = $("#Ar_ContractNo").val();
                    data["ArObjects[" + i + "].ContractNo"] = $("#Ar_ContractNo option:selected").attr("contractno");


                    data["ArObjects[" + i + "].CaseOfficeFeeTypeId"] = $(e).find("#item_CaseOfficeFeeTypeId").val();
                    data["ArObjects[" + i + "].CaseOfficeFeeAmount"] = $(e).find("#item_CaseOfficeFeeAmount").val();

                    if ($(e).find("#item_CaseOfficeFeeTypeId").val() == '-1' &&  $(e).find("#item_CaseNonOfficeFeeTypeId").val() == '-1') {
                        dataIsNOk = true;
                        $.showModalMessageBox("第" + (j) + "行,请选择官费或代理费.");
                        return false;
                    }

                    if (data["ArObjects[" + i + "].CaseOfficeFeeTypeId"] != '-1' && data["ArObjects[" + i + "].CaseOfficeFeeAmount"] == '') {
                        dataIsNOk = true;
                        $.showModalMessageBox("第" + (j) + "行，输入官费金额.");
                        return false;
                    }

                    if (data["ArObjects[" + i + "].CaseOfficeFeeTypeId"] == '3') {
                        //年费时需要
                        data["ArObjects[" + i + "].AnnualYear"] = $(e).find("#item_CaseFeeAnnualYear").val();
                        data["ArObjects[" + i + "].AnnualFrom"] = $(e).find("#item_CaseFeeAnnualYear option:selected").attr("annualfrom");
                        data["ArObjects[" + i + "].AnnualEnd"] = $(e).find("#item_CaseFeeAnnualYear option:selected").attr("annualend");
                        data["ArObjects[" + i + "].IsFirstYear"] = $(e).find("#item_IsFirstYear").attr("checked") == "checked";
                    }

                    data["ArObjects[" + i + "].CaseNonOfficeFeeTypeId"] = $(e).find("#item_CaseNonOfficeFeeTypeId").val();
                    data["ArObjects[" + i + "].CaseNonOfficeFeeAmount"] = $(e).find("#item_CaseNonOfficeFeeAmount").val();

                    if (data["ArObjects[" + i + "].CaseNonOfficeFeeTypeId"] != '-1' && data["ArObjects[" + i + "].CaseNonOfficeFeeAmount"] == '') {
                        dataIsNOk = true;
                        $.showModalMessageBox("第" + (j) + "行，输入代理费金额.");
                        return false;
                    }

                    //data["ArObjects[" + i + "].CommissionFeeAmount"] = $(e).find("#item_CaseNonOfficeFeeAmount").val();
                    data["ArObjects[" + i + "].Remark"] = $(e).find("#item_Remark").val();

                    if (data["ArObjects[" + i + "].CaseId"] == 'null') {
                        dataIsNOk = true;
                        $.showModalMessageBox("第" + (j) + "行，输入正确的案号或申请号.");
                        return false;
                    }

                    if (data["ArObjects[" + i + "].CaseOfficeFeeTypeId"] == '') {
                        dataIsNOk = true;
                        $.showModalMessageBox("第" + (j) + "行，请选择官费类型.");
                        return false;
                    }

                    if (data["ArObjects[" + i + "].CaseNonOfficeFeeTypeId"] == '') {
                        dataIsNOk = true;
                        $.showModalMessageBox("第" + (j) + "行，请选择代理费类型.");
                        return false;
                    }

                    i++;
                }
            }
        });

        if (dataIsNOk) return false;

        $.ajaxPost(AP_ROOT + "FCM/Contract/Create", data, function (response) {
            if (response.IsSuccess) {

                //$("#btnARCreateUpdate").attr("disabled", "true");
                //$("#btnARCreateNew").removeAttr("disabled");

                $.showModalMessageBox("提交成功.");
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    Contract: {
        List: function (customerId) {
            var data = {
                customerId: customerId,
            };

            $.ajaxPost(AP_ROOT + "FCM/Contract/GetBasicContractListByCustomerId", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    if (response.Data.length > 0) {
                        var selected = $("#Ar_ContractNo");
                        $(selected).empty();
                        $(selected).removeAttr("disabled");

                        $(selected).append('<option value=-1 contractno=-1>' + "请选择" + '</option>');

                        $.each(response.Data, function (i, c) {
                            $(selected).append('<option value=\"' + c.ContractBasicInfo.ContractId + '\" contractno=\"' + c.ContractBasicInfo.ContractNo + '\">' + c.ContractBasicInfo.ContractNo + '_' + c.ContractBasicInfo.ContractName + '</option>');
                        });
                    }

                    $.closeLoading();
                }
            }, true);
        }
    },

    ARObject: {

        Init: function () {
            ar.ARObject.List();
        },

        ObjectItem: {
            Add: function (e) {

                var tr = $($(e).parents("tr")).clone().show();

                //var tr = $($('#tblARObjectList>tbody>tr')[1]).clone().show();

                //$(tr).find(":input[type='text']").val('');
                //$(tr).find(":input[type='hidden']").val('');
                //$(tr).find(":input[type='checkbox']").attr("checked", false);
                //$(tr).find("#item_CaseFeeAnnualYear").empty();
                //$(tr).find("#item_CaseFeeAnnualYear").append("<option value='-1'>无</option>");
                //$(tr).find("#item_CaseFeeAnnualYear").attr("disabled", "disabled");
                //$(tr).find("#item_IsFirstYear").attr("disabled", "disabled");
                
                //$($("td", tr)[0]).html("<input type='hidden' value='' id='hidCaseFeeItem_FeeTypeId" + $("#tblCaseFeeItemList>tbody>tr").length + "' /><input class='CaseFeeItem_FeeTypeName form-control' sytle='text-align:center;width:100px' id='CaseFeeItem_FeeTypeName" + $("#tblCaseFeeItemList>tbody>tr").length + "' readonly type='text' value='' />");
                $("#tblARObjectList").append(tr);
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

        /*案件费用通知*/
        OpenARObjectCaseFee: function (caseId) {
            if (parseInt(caseId) == 0) {
                $.showModalMessageBox("请录入正确案件编号或申请号.");
                return false;
            }
            var data =
            {
                caseId: caseId,
            };
            var url = AP_ROOT + "FAM/AR/ARObjectCaseFee";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#ARObjectCaseFeeModal').modal({ backdrop: 'static', keyboard: false });
                $('#ARObjectCaseFeeModal').on('hidden.bs.modal', function () {
                    $("#ARObjectCaseFeeModal").remove();
                });
            });
        },
        CloseARObjectCaseFee: function () {
            $('#ARObjectCaseFeeModal').modal('hide');
        },
        CreateUpdateARObjectCaseFee: function() {

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

            if (response.Data.CaseBasicInfo.FirstApplicantId != null
                && response.Data.CaseBasicInfo.FirstApplicantId != ''
                && $("#Ar_CustomerId").val() != ''
                && $("#Ar_CustomerId").val() != response.Data.CaseBasicInfo.FirstApplicantId) {
                $.showModalMessageBox("输入的案号,不属该客户下的案件,请重新输入.",null,true);
                return false;
            }
        },

        /*费用列表*/
        List: function () {
            var data = {
                customerId: $("#Ar_CustomerId").val(),
                contractId: $("#Ar_ContractNo").val(),
            };

            $.ajaxPost(AP_ROOT + "FAM/AR/ARObjects", data, function (response) {
                if (response.IsSuccess) {

                    $.openLoading();

                    $("#tblARObjectList tbody tr").each(function (i, e) {
                        if ($(e).css("display") != 'none') {
                            if ($(e).find("#chkCaseId").attr('checked') != 'checked') {
                                $(e).remove();
                            }
                            if ($(e).find("#chkCaseId").val() == 'null') {
                                $(e).remove();
                            }
                        }
                    });

                    $.each(response.Data, function (i, c) {
                        $("tbody", "#tblARObjectList").addRow(
                            "<input type='checkbox' id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' value='" + c.CaseId + "'>",
                            "<input class='item_CaseNo form-control' id='item_CaseNo'  type='text' value='" + (c.CaseNo == null ? '' : c.CaseNo) + "'>",
                            "<input class='item_CaseRequestNo form-control' id='item_CaseRequestNo' type='text' value='" + (c.CaseRequestNo == null ? '' : c.CaseRequestNo) + "'>",
                            "<input class='item_CaseRequestDate form-control' id='item_CaseRequestDate'  readonly='True' type='text' value='" + (c.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseRequestDate))) + "'>",
                            "<select class='form-control'  id='item_CaseOfficeFeeTypeId'><option value='-1'>请选择</option></select>",
                            "<input class='item_CaseOfficeFeeAmount form-control'  id='item_CaseOfficeFeeAmount'  onafterpaste='this.value=this.value.replace(/\D/g,'')' onkeyup='javascript:this.value=this.value.replace(/\D/g,'')' type='text' value=''>",
                            "<select class='form-control' id='item_CaseFeeAnnualYear' disabled='disabled'><option value='-1'>无</option></select>",
                            "<input class='item_IsFirstYear' disabled='disabled' id='item_IsFirstYear' style='height: 20px;width: 20px ' type='checkbox' value='true'>",
                            "<select class='form-control'  id='item_CaseNonOfficeFeeTypeId'><option value='-1'>请选择</option></select>",
                            "<input class='item_CaseNonOfficeFeeAmount form-control'  id='item_CaseNonOfficeFeeAmount'  onafterpaste='this.value=this.value.replace(/\D/g,'')' onkeyup='javascript:this.value=this.value.replace(/\D/g,'')' type='text' value=''>",
                            "<input class='item_Remark form-control' id='item_Remark'  type='text' value=''>",
                            "<input type='button' value='新增' class='btn_ar_add'><input type='button' value='移除' class='btn_ar_remove'>" 
                        );
                    });

                    $("#tblARObjectList tbody tr").each(function (i, e) {
                        if ($(e).find("#item_CaseOfficeFeeTypeId option").length == 1) {
                            $.each(GV_IPR.CaseFeeTypes, function (j, f) {
                                if (f.TypeId == '1') {
                                    $(e).find("#item_CaseOfficeFeeTypeId").append('<option value=' + f.FeeTypeId + '>' + f.FeeTypeName + '</option>');
                                }
                            });
                        }

                        if ($(e).find("#item_CaseNonOfficeFeeTypeId option").length == 1) {
                            $.each(GV_IPR.CaseFeeTypes, function (j, f) {
                                if (f.TypeId == '2') {
                                    $(e).find("#item_CaseNonOfficeFeeTypeId").append('<option value=' + f.FeeTypeId + '>' + f.FeeTypeName + '</option>');
                                }
                            });
                        }
                    });

                    ar.ResetSize();
                    $.closeLoading();
                }
            }, true);
        },

        InitCaseOfficeFeeType: function (e) {

            if ($(e).val() == "3" && $(e).parents("tr").find("#item_CaseRequestDate").val() == '') {
                return false;
            }

            var selected = $(e).parents("tr").find("#item_CaseFeeAnnualYear");
            var caseRequestDateStr = $(e).parents("tr").find("#item_CaseRequestDate").val();

            $(selected).empty();
            $(selected).removeAttr("disabled");
            $($(e).parents("tr").find("#item_IsFirstYear")).removeAttr("disabled");
            if ($(e).val() == "3") {
                if (caseRequestDateStr != '') {
                    $(selected).removeAttr("disabled");
                    var caseRequestDate = new Date(caseRequestDateStr);
                    for (var i = 1; i <= 20; i++) {
                        $(selected).append('<option value=' + i + ' annualfrom=' + caseRequestDate.addYears(i - 1).Format("yyyy-MM-dd") + ' annualend=' + caseRequestDate.addYears(i).addDays(-1).Format("yyyy-MM-dd") + '>第' + i + '年度 ' + caseRequestDate.addYears(i - 1).Format("yyyy-MM-dd") + '~' + caseRequestDate.addYears(i).addDays(-1).Format("yyyy-MM-dd") + '</option>');
                    }
                }
            } else {
                $($(e).parents("tr").find("#item_IsFirstYear")).attr("disabled", "disabled");
                $(selected).attr("disabled", "disabled");
                $(selected).append('<option value=-1>无</option>');
            }
        },

        Selected: function (e) {
            if ($(e).attr("checked") == "checked") {
                $.checkbox.all("chkCaseId");
            } else {
                $.checkbox.not("chkCaseId");
            }
        },

    },
};
 

$(document).ready(function() {

    var customter = new AssociateCustomer(
     $("#div_customer"),
     $("#Ar_CustomerId"),
     $("#Ar_CustomerNo"),
     $("#Ar_CustomerName")
    );

    $("#btnARCreateUpdate").removeAttr("disabled");
    $("#btnARCreateNew").attr("disabled", "true");

 
    $(window).resize(function() {
        ar.ResetSize();
    });

    $(document).click(function() {
 
    });

    $(function() {
        $('.viewFramework-product-body').slimScroll({
            height: '100%'
        });
    });

    $(".btn_ar_add").die().live("click", function () {
        ar.ARObject.ObjectItem.Add(this);
    });

    $(".btn_ar_remove").die().live("click", function () {
        ar.ARObject.ObjectItem.Remove(this);
    });

    $(".item_CaseNo").die().live("click", function () {
        ar.ARObject.ObjectItem.Remove(this);
    });

    $(".item_CaseNo").die().live("keypress", function () {
        if (event.keyCode == 13) {
            if ($(this).val() == '') return false;
            $.case.getCaseBasicByCaseNo($(this), $(this).val(), ar.ARObject.getCaseBasicCallBack);
            event.stopPropagation();

            return false;
        }
    });

    $(".item_CaseRequestNo").die().live("keypress", function () {
        if (event.keyCode == 13) {
            if ($(this).val() == '') return false;
            $.case.getCaseBasicByCaseRequestNo($(this), $(this).val(), ar.ARObject.getCaseBasicCallBack);
            return true;
        }
    });

    $(".item_CaseFeeAmount").die().live("click", function () {
        ar.ARObject.OpenARObjectCaseFee(34);
    });

    $("#btnARObjectCaseFee").die().live("click", function () {
        ar.ARObject.CreateUpdateARObjectCaseFee();
    });

    $("#btnARCreateUpdate").die().live("click", function () {
        ar.CreateUpdate();
    });

    $("#btnARObjectCaseFeeCancel,#btnARObjectCaseFeeClose").die().live("click", function () {
        ar.ARObject.CloseARObjectCaseFee();
    });

    $("#btnARObjectCaseFeeCancel,#btnARObjectCaseFeeClose").die().live("click", function () {
        ar.ARObject.CloseARObjectCaseFee();
    });

    $("#item_CaseOfficeFeeTypeId").die().live("change", function () {
        ar.ARObject.InitCaseOfficeFeeType(this);
    });

    $(".item_CaseNonOfficeFeeTypeId").die().live("change", function () {
        ar.ARObject.InitCaseNonOfficeFeeType();
    });

    $("#Ar_ContractNo").die().live("change", function () {
        ar.ARObject.List();

        $("#btnARCreateUpdate").removeAttr("disabled");

    });

    $("#btnARCreateNew").die().live("click", function () {
        window.location.reload();
    });

    $("#chkCaseIdAll").die().live("click", function () {
        ar.ARObject.Selected(this);
    });

    ar.Init();
});