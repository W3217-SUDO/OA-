var contractPayment = {

    ResetSize: function() {
        if ($("#divContextList").length > 0) {
            $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 22);
        }
    },

    Appliction: {
        CreateUpdate: function(isSubmit) {
            try {

                var dataIsNOk = false;

                if ($("#Application_PaymentType_PaymentTypeId").val() == '') {
                    $.showModalMessageBox("请选择付款类型.");
                    return false;
                }

                var data = {};

                data["Application.ApplicationBasic.ContractId"] = $("#Contract_ContractBasicInfo_ContractId").val();
                data["Application.ApplicationBasic.ContractNo"] = $("#Contract_ContractBasicInfo_ContractNo").val();
                data["Application.ApplicationBasic.ApplicationNo"] = $("#Application_ApplicationBasic_ApplicationNo").val();
                data["Application.ApplicationBasic.CustomerName"] = $("#Application_ApplicationBasic_CustomerName").val();
                data["Application.ApplicationBasic.ApplicationDate"] = $("#Application_ApplicationBasic_ApplicationDate").val();
                data["Application.ApplicationBasic.PaidAmount"] = $("#Application_ApplicationBasic_PaidAmount").val();
                data["Application.ApplicationBasic.Remark"] = $("#Application_ApplicationBasic_Remark").val();
                data["Application.PaymentType.PaymentTypeId"] = $("#Application_PaymentType_PaymentTypeId").val();

                var i = 0;
                $("#tblContractObjectList>tbody>tr").each(function(j, e) {
                    if ($(e).css("display") != 'none') {

                        if ($('#Application_PaymentType_PaymentTypeId').val() == '1') {
                            //官费
                            data["Application.ObjectList[" + i + "].CaseFeeId"] = $(e).find("#item_CaseOfficeFeePaidAmount").attr("CaseOfficeFeeId");
                            data["Application.ObjectList[" + i + "].CaseFeeTypeId"] = $(e).find("#item_CaseOfficeFeePaidAmount").attr("CaseOfficeFeeTypeId");
                            data["Application.ObjectList[" + i + "].PaidAmount"] = $(e).find("#item_CaseOfficeFeePaidAmount ").val();

                        }
                        else if ($('#Application_PaymentType_PaymentTypeId').val() == '2') {
                            //其他费用
                            data["Application.ObjectList[" + i + "].CaseFeeId"] = $(e).find("#item_CaseNonOfficeFeePaidAmount").attr("CaseNonOfficeFeeId");
                            data["Application.ObjectList[" + i + "].CaseFeeTypeId"] = $(e).find("#item_CaseNonOfficeFeePaidAmount").attr("CaseNonOfficeFeeTypeId");
                            data["Application.ObjectList[" + i + "].PaidAmount"] = $(e).find("#item_CaseNonOfficeFeePaidAmount ").val();

                        }

                        data["Application.ObjectList[" + i + "].CaseId"] = $(e).find("#item_PaymentApply").attr("CaseId");
                        data["Application.ObjectList[" + i + "].CaseNo"] = $(e).find("#item_PaymentApply").attr("CaseNo");

                        //data["Contract.CaseFeeList[" + i + "].Remark"] = $(e).find("#item_Remark").val();

                        i++;
                    }
                });

                if (dataIsNOk) return false;

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/FCM/ContractPayment/ApplicationCreate", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("提交成功.");
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });

            } catch (e) {

            }
        },
        CreateUpdateCallBack: function(isSubmit) {
            if (isSubmit) {
                window.location = AP_ROOT + "4001002/FCM/Contract/ContractList";
            } else {
                window.location = AP_ROOT + "4001002/FCM/Contract/ContractList";
            }
        },
    },

    Objects: {
        Layout: function() {
            var data = {
                contractId: $("#Contract_ContractBasicInfo_ContractId").val()
            };

            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/FCM/ContractPayment/ContractObjectList", data, function(response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $("#dv_List").empty();
                    $("#dv_List").html(response.Data);
                    contractPayment.Objects.List();
                    $.closeLoading();
                }
            }, true);
        },

        List: function() {
            var data = {
                contractId: $("#Contract_ContractBasicInfo_ContractId").val()
            };

            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/FCM/ContractPayment/ContractObjects", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $.each(response.Data, function(i, c) {
                        var caseTypeName = $.caseType.getCaseTypeName(c.CaseTypeId);
                        var caseOfficeFeeTypeName = c.CaseOfficeFeeTypeId == null ? '/' : $.caseFeeType.getCaseFeeTypeName(c.CaseTypeId, c.CaseOfficeFeeTypeId);
                        var tr = "<tr>"
                                + "<td>" + (++i) + "</td>"
                                + "<td>" + caseTypeName + "</td>"
                                + "<td>" + c.CaseName + "</td>"
                                + "<td>" + c.CaseNo + "</td>"
                                + "<td>" + c.CaseRequestNo + "</td>"
                                + "<td>" + caseOfficeFeeTypeName + "</td>"
                                + "<td>" + (c.CaseOfficeFeeAmount == null ? 0 : c.CaseOfficeFeeAmount) + "</td>"
                                + "<td><input class='item_CaseOfficeFeePaidAmount form-control'  id='item_CaseOfficeFeePaidAmount' CaseOfficeFeeId=" + c.CaseOfficeFeeId + " CaseOfficeFeeTypeId=" + c.CaseOfficeFeeTypeId + " CaseOfficeFeeAmount=" + (c.CaseOfficeFeeAmount == null ? 0 : c.CaseOfficeFeeAmount) + " onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\" onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" type='text' value='0'>"
                                + "<td>" + (c.CaseNonOfficeFeeAmount == null ? 0 : c.CaseNonOfficeFeeAmount) + "</td>"
                                + "<td><input class='item_CaseNonOfficeFeePaidAmount form-control'  id='item_CaseNonOfficeFeePaidAmount' CaseNonOfficeFeeId=" + c.CaseNonOfficeFeeId + " CaseNonOfficeFeeTypeId=" + c.CaseNonOfficeFeeTypeId + " CaseNonOfficeFeeAmount=" + (c.CaseNonOfficeFeeAmount == null ? 0 : c.CaseNonOfficeFeeAmount) + " onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\" onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" type='text' value='0'>"
                                + "<td><input id='item_PaymentApply' name='item_PaymentApplyOne'  type='checkbox' caseid=" + c.CaseId + " caseno=" + c.CaseNo + " ></td>"
                                + "</tr>";
                        
                        $('#tblContractObjectList>tbody>tr:last').after(tr);
                    });

                    contractPayment.ResetSize();
                    $.closeLoading();
                }
            }, true);
        },

        ObjectItem: {
            Apply: function (e) {
                var caseOfficeFeeAmount = $(e).parents("tr").find("#item_CaseOfficeFeePaidAmount");
                var caseNonOfficeFeeAmount = $(e).parents("tr").find("#item_CaseNonOfficeFeePaidAmount");
                if ($(e).prop("checked") == true) {
                    $(caseOfficeFeeAmount).val($(caseOfficeFeeAmount).attr("caseofficefeeamount"));
                    $(caseNonOfficeFeeAmount).val($(caseNonOfficeFeeAmount).attr("casenonofficefeeamount"));
                } else {
                    $(caseOfficeFeeAmount).val(0);
                    $(caseNonOfficeFeeAmount).val(0);
                }
            }
        }
    },

    PaymentType: {
        Open: function () {

            var url =  AP_ROOT + AP_PAGE_ID + "/FCM/ContractPayment/PaymentTypeList";
            $.openLoading();

            $("<div></div>").load(url, null, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#paymentTypeModal').modal({ backdrop: 'static', keyboard: false });
                $('#paymentTypeModal').on('hidden.bs.modal', function () {
                    $("#paymentTypeModal").remove();
                });

                contractPayment.PaymentType.List();
            });
        },

        List: function () {
 
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/FCM/ContractPayment/PaymentTypes", null, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $.each(response.Data, function (i, p) {
                        $("tbody", "#tblPaymentTypeList").addRow(
                            "<input type='checkbox' name='chkPaymentTypeId' value='" + p.PaymentTypeId + "'paymentTyperName='" + p.PaymentTypeName + "'organizationName='" + p.OrganizationName + "'account='" + p.Account + "'>",
                            p.PaymentTypeName,
                            p.OrganizationName,
                            p.Account);
                    });

                    $.closeLoading();
                }
            }, true);
        },

        Select: function (e) {
            if ($(e).prop("checked") == true) {
                $("input[name='chkPaymentTypeId']").removeAttr("checked");
                $(e).attr("checked", "checked");
            } 
        },

        Close: function () {
            $('#paymentTypeModal').modal('hide');
        },

        Selected: function () {

            var e = $("input[name=chkPaymentTypeId]:checked");

            if ($(e).length > 0) {
                $("#Application_PaymentType_PaymentTypeId").val($(e).val());
                $("#Application_PaymentType_PaymentTypeName").val($(e).attr("paymenttypername"));
                $("#Application_PaymentType_OrganizationName").val($(e).attr("organizationname"));
                $("#Application_PaymentType_Account").val($(e).attr("account"));
            }

            contractPayment.PaymentType.Close();
        }
    }
}

$(document).ready(function () {
    $(window).resize(function () {
        contractPayment.ResetSize();
    });

    $("#lblPaymentType").off().on("click", function () {
        contractPayment.PaymentType.Open();
    });

    $("#btnPaymentTypeCancel,#btnPaymentTypeClose").off().on("click", function () {
        contractPayment.PaymentType.Close();
    });
    
    $("#btnPaymentTypeSelected").off().on("click", function () {
        contractPayment.PaymentType.Selected();
    });

    $("input[name='chkPaymentTypeId']").off().on("click", function () {
        contractPayment.PaymentType.Select(this);
    });

    $("input[name='item_PaymentApplyOne']").off().on("click", function () {
        contractPayment.Objects.ObjectItem.Apply(this);
    });

    $("#btnPaymentApply").off().on("click", function () {
        contractPayment.Appliction.CreateUpdate(true);
    });

    contractPayment.Objects.Layout();
});