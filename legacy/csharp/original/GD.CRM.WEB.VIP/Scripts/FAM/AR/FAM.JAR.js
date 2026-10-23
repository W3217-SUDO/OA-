var payment = {
    ResetSize: function() {
        if ($("#divContextList").length > 0) {
            $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 22);
        }
    },

    Payment: {
        ViewContract: function(contractId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FCM/Contract/ContractView?contractId=" + contractId;
            window.open(url);
        },

        Create: function (contractId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/JAR/PaymentCreate?contractId=" + contractId;
            window.open(url,'ContractPaymentCreate');
        },
        View: function(paymentId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/JAR/PaymentView?paymentId=" + paymentId;
            window.open(url);
        },
        Edit: function(paymentId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/JAR/PaymentEdit?paymentId=" + paymentId;
            window.open(url);
        },

        TotalAmountSet: function() {
            var totalAmount = 0;
            $("input[name='item_CaseOfficeFeeCashAmount']").each(
                function() {
                    if ($(this).val() == '' || !$(this).isMoney()) {
                        $(this).val(0);
                    }
                    totalAmount += parseFloat($(this).val());
                }
            );
            $("input[name='item_CaseNonOfficeFeeCashAmount']").each(
                function() {
                    if ($(this).val() == '' || !$(this).isMoney()) {
                        $(this).val(0);
                    }
                    totalAmount += parseFloat($(this).val());
                }
            );
            $("input[name='item_CaseCommissionFeeCashAmount']").each(
                function() {
                    if ($(this).val() == '' || !$(this).isMoney()) {
                        $(this).val(0);
                    }
                    totalAmount += parseFloat($(this).val());
                }
            );

            var totalAmount = totalAmount + ($("#Payment_PaymentBasic_PrePaidAmount").val() == '' ? 0 : parseFloat($("#Payment_PaymentBasic_PrePaidAmount").val()));
           // $("#Payment_PaymentBasic_CashedAmount").val(totalAmount);
            totalAmount = Math.round(totalAmount * 100) / 100;

            $("input[name='Payment.PaymentBasic.CashedAmount']").each(
                function () {
                    $(this).val(totalAmount);
                }
            );

            //$("#Payment_PaymentBasic_TotalAmount").val(totalAmount);
        },

        Appliction: {
            CreateUpdate: function(isSubmit) {
                try {

                    if ($("#Payment_PaymentBasic_PaymentModeName").val() == '') {
                        $.showModalMessageBox("请输入回款方式.");
                        return false;
                    }

                    if ($("#Payment_PaymentBasic_InvoiceNo").val() == '') {
                        $.showModalMessageBox("请输入单据号.");
                        return false;
                    }

                    //if ($("#Payment_PaymentBasic_CashedAmount").val() == '' || parseFloat($("#Payment_PaymentBasic_CashedAmount").val()) == 0) {
                    //    $.showModalMessageBox("回款金额不能为零.");
                    //    return false;
                    //}

                    var data = {};

                    data["Payment.PaymentBasic.PaymentId"] = $("#Payment_PaymentBasic_PaymentId").val();
                    data["Payment.PaymentBasic.CustomerId"] = $("#Customer_CustomerBasic_CustomerId").val();
                    data["Payment.PaymentBasic.CustomerNo"] = $("#Customer_CustomerBasic_CustomerNo").val();
                    data["Payment.PaymentBasic.ContractId"] = $("#Contract_ContractBasicInfo_ContractId").val();
                    data["Payment.PaymentBasic.ContractNo"] = $("#Contract_ContractBasicInfo_ContractNo").val();
                    data["Payment.PaymentBasic.BusinessOwner"] = $("#Contract_ContractBasicInfo_BusinessOwner").val();
                    data["Payment.PaymentBasic.PaymentModeName"] = $("#Payment_PaymentBasic_PaymentModeName").val();
                    data["Payment.PaymentBasic.SequenceNo"] = $("#Payment_PaymentBasic_SequenceNo").val();
                    data["Payment.PaymentBasic.PayerName"] = $("#Payment_PaymentBasic_PayerName").val();
                    data["Payment.PaymentBasic.InputDate"] = $("#Payment_PaymentBasic_InputDate").val();
                    data["Payment.PaymentBasic.InvoiceNo"] = $("#Payment_PaymentBasic_InvoiceNo").val();
                    data["Payment.PaymentBasic.CashedAmount"] = $("#Payment_PaymentBasic_CashedAmount").val();
                    data["Payment.PaymentBasic.CashedDate"] = $("#Payment_PaymentBasic_CashedDate").val();

                    data["Payment.PaymentBasic.PrePaidAmount"] = $("#Payment_PaymentBasic_PrePaidAmount").val();

                    data["Payment.PaymentBasic.Remark"] = $("#Payment_PaymentBasic_Remark").val();
                    data["Payment.PaymentType.PaymentTypeId"] = $("#Payment_PaymentType_PaymentTypeId").val();

                    var i = 0;
                    $("#tblARObjectList>tbody>tr").each(function (j, e) {
                        if ($(e).css("display") != 'none') {

                            data["Payment.PaymentObjects[" + i + "].CaseOfficeFeeId"] = $(e).find("#item_CaseOfficeFeeCashAmount").attr("CaseOfficeFeeId");
                            data["Payment.PaymentObjects[" + i + "].CaseOfficeFeeSeqId"] = $(e).find("#item_CaseOfficeFeeCashAmount").attr("CaseOfficeFeeSeqId");
                            data["Payment.PaymentObjects[" + i + "].CaseOfficeFeeCashAmount"] = $(e).find("#item_CaseOfficeFeeCashAmount").val();
                            data["Payment.PaymentObjects[" + i + "].CaseNonOfficeFeeId"] = $(e).find("#item_CaseNonOfficeFeeCashAmount").attr("casenonofficefeeid");
                            data["Payment.PaymentObjects[" + i + "].CaseNonOfficeFeeSeqId"] = $(e).find("#item_CaseNonOfficeFeeCashAmount").attr("casenonofficefeeseqid");
                            data["Payment.PaymentObjects[" + i + "].CaseNonOfficeFeeCashAmount"] = $(e).find("#item_CaseNonOfficeFeeCashAmount").val();
                            data["Payment.PaymentObjects[" + i + "].CaseCommissionFeeId"] = $(e).find("#item_CaseCommissionFeeCashAmount").attr("casecommissionfeeid");
                            data["Payment.PaymentObjects[" + i + "].CaseCommissionFeeSeqId"] = $(e).find("#item_CaseCommissionFeeCashAmount").attr("casecommissionfeeseqid");
                            data["Payment.PaymentObjects[" + i + "].CaseCommissionFeeCashAmount"] = $(e).find("#item_CaseCommissionFeeCashAmount").val();

                            if(parseFloat($(e).find("#item_CaseOfficeFeeCashAmount").attr("caseofficefeecashedamount")) != parseFloat($(e).find("#item_CaseOfficeFeeCashAmount").val())) {
                                data["Payment.PaymentObjects[" + i + "].IsChanged"] = true;
                            }

                            if (parseFloat($(e).find("#item_CaseNonOfficeFeeCashAmount").attr("casenonofficefeecashedamount")) != parseFloat($(e).find("#item_CaseNonOfficeFeeCashAmount").val())) {
                                data["Payment.PaymentObjects[" + i + "].IsChanged"] = true;
                            }

                            if (parseFloat($(e).find("#item_CaseCommissionFeeCashAmount").attr("casecommissionfeecashedamount")) != parseFloat($(e).find("#item_CaseCommissionFeeCashAmount").val())) {
                                data["Payment.PaymentObjects[" + i + "].IsChanged"] = true;
                            }

                            data["Payment.PaymentObjects[" + i + "].CaseId"] = $(e).find("#item_PaymentApply").attr("CaseId");
                            data["Payment.PaymentObjects[" + i + "].CaseNo"] = $(e).find("#item_PaymentApply").attr("CaseNo");

                            i++;
                        }
                    });
 
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/JAR/PaymentCreateUpdate", data, function(response) {
                        if (response.IsSuccess) {
                            $.showModalConfirmDialog("提交成功", 'payment.Payment.Appliction.CreateUpdateCallBack', true, true);
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {

                }
            },
            CreateUpdateCallBack: function(isSubmit) {
                if (isSubmit) {
                    window.location = AP_ROOT +  "/5001002003/FAM/JAR/PaymentList";
                } else {
                    window.location = AP_ROOT + "/5001002003/FAM/JAR/PaymentList";
                }
            },
       },

        Objects: {
            ObjectItem: {
                Apply: function (e) {
                    var caseOfficeFeeCashAmount = $(e).parents("tr").find("#item_CaseOfficeFeeCashAmount");
                    var caseNonOfficeFeeCashAmount = $(e).parents("tr").find("#item_CaseNonOfficeFeeCashAmount");
                    var caseCommissionFeeCashAmount = $(e).parents("tr").find("#item_CaseCommissionFeeCashAmount");
                    if ($(e).prop("checked") == true) {
                        $(caseOfficeFeeCashAmount).val($(caseOfficeFeeCashAmount).attr("caseofficefeeopencashamount") == undefined ? "0" : $(caseOfficeFeeCashAmount).attr("caseofficefeeopencashamount"));
                        $(caseNonOfficeFeeCashAmount).val($(caseNonOfficeFeeCashAmount).attr("casenonofficefeeopencashamount") == undefined ? "0" : $(caseNonOfficeFeeCashAmount).attr("casenonofficefeeopencashamount"));
                        $(caseCommissionFeeCashAmount).val($(caseCommissionFeeCashAmount).attr("casecommissionfeeopencashamount") == undefined ? "0" : $(caseCommissionFeeCashAmount).attr("casecommissionfeeopencashamount"));
                    } else {
                        $(caseOfficeFeeCashAmount).val(0);
                        $(caseNonOfficeFeeCashAmount).val(0);
                        $(caseCommissionFeeCashAmount).val(0);
                    }
                }
            }
        },

        //生成单据号
        GenerateInvoiceNo : function()
        {
            var date = new Date().Format("yyMMdd");
            var r = parseInt(Math.random() * (99999 - 10000 + 1) + 10000, 10);

            return date + "-" + r;
        },

        PaymentType: {
            Open: function () {

                var url = AP_ROOT + AP_PAGE_ID + "/FAM/PaymentType/PaymentTypeList";
                $.openLoading();

                $("<div></div>").load(url, null, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#paymentTypeModal').modal({ backdrop: 'static', keyboard: false });
                    $('#paymentTypeModal').on('hidden.bs.modal', function () {
                        $("#paymentTypeModal").remove();
                    });

                    payment.Payment.PaymentType.List();
                });
            },
            List: function () {

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/PaymentType/PaymentTypes", null, function (response) {
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
                    $("#Payment_PaymentType_PaymentTypeId").val($(e).val());
                    $("#Payment_PaymentType_PaymentTypeName").val($(e).attr("paymenttypername"));
                    $("#Payment_PaymentType_OrganizationName").val($(e).attr("organizationname"));
                    $("#Payment_PaymentType_Account").val($(e).attr("account"));
                }

                payment.Payment.PaymentType.Close();
            }
        },
    },

    List: {
      PaymentList: function() {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/JAR/PaymentList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                            $.each(response.Data.PaymentList, function (i, c) {
                            if ($("#SearchCondition_PageId").val() == '5001002002') 
                            {
                                $("tbody", "#tblPaymentList").addRow(
                                    "<a href='javascript:void(0)' onclick='javascript:payment.Payment.View(\"" + c.PaymentBasic.PaymentId + "\")'>查看</a> &nbsp; " ,
                                    c.PaymentBasic.InvoiceNo,
                                   "<a href='javascript:void(0)' onclick='javascript:payment.Payment.ViewContract(\"" + c.PaymentBasic.ContractId + "\")'>" +  c.PaymentBasic.ContractNo + "</a> &nbsp; ",
                                   c.PaymentBasic.CustomerName,
                                    c.PaymentBasic.PayerName,
                                    c.PaymentBasic.BusinessOwnerName,
                                    c.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.CashedDate)),
                                    c.PaymentBasic.CashedAmount,
                                    c.PaymentBasic.CaseOfficeFeeCashedAmount,
                                    c.PaymentBasic.CaseNonOfficeFeeCashedAmount,
                                    c.PaymentBasic.CaseCommissionFeeCashedAmount,
                                    c.PaymentBasic.PaymentModeName );
                            }
                            else {
                                $("tbody", "#tblPaymentList").addRow(
                                    "<a href='javascript:void(0)' onclick='javascript:payment.Payment.View(\"" + c.PaymentBasic.PaymentId + "\")'>查看</a> &nbsp; " +
                                    "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Edit(\"" + c.PaymentBasic.PaymentId + "\")'>编辑</a> &nbsp; ",
                                      c.PaymentBasic.InvoiceNo,
                                   "<a href='javascript:void(0)' onclick='javascript:payment.Payment.ViewContract(\"" + c.PaymentBasic.ContractId + "\")'>" + c.PaymentBasic.ContractNo + "</a> &nbsp; ",
                                   c.PaymentBasic.CustomerName,
                                    c.PaymentBasic.PayerName,
                                    c.PaymentBasic.BusinessOwnerName,
                                    c.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.CashedDate)),
                                    c.PaymentBasic.CashedAmount,
                                    c.PaymentBasic.CaseOfficeFeeCashedAmount,
                                    c.PaymentBasic.CaseNonOfficeFeeCashedAmount,
                                    c.PaymentBasic.CaseCommissionFeeCashedAmount,
                                    c.PaymentBasic.PaymentModeName);
                            }
                            });

                            $("tbody", "#tblPaymentList").addRow(
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            response.Data.TotalCashedAmount,
                            "",
                            "",
                            "",
                            "");

                        $("tfoot", "#tblPaymentList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.paymentList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: payment.List.PaymentList,
                            callBackArgs: null
                        });
                    } else {
                        $("tfoot", "#tblPaymentList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
      },
      PaymentListExportToExcel: function () {
          $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/JARFileCenter/PaymentListExportToExcel", function (response) {
              if (response.IsSuccess) {
                  window.open(AP_ROOT + AP_PAGE_ID + "/FAM/JARFileCenter/PaymentListExportToExcelDownload?fileName=" + response.Data);
                  $.showModalMessageBox("导出成功.");
              } else {
                  $.showModalMessageBox(response.Message);
              }
          });
      },
    }
}

var contract = {
    List: {
        ContractList: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/Contract/List", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.ContractList, function (i, c) {
                            $("tbody", "#tblContractList").addRow(
                                "<a href='javascript:void(0);' onclick='javascript:payment.Payment.Create(" + c.ContractBasicInfo.ContractId + ")'>新增回款</a>&nbsp;&nbsp;",
                                c.ContractBasicInfo.ContractNo,
                                c.ContractBasicInfo.ContractName,
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.TotalAmount,
                                c.ContractBasicInfo.CashedAmount,
                                c.ContractBasicInfo.ARAmount,
                                c.ContractBasicInfo.BusinessOwnerName,
                                c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                                c.ContractBasicInfo.CustomerNo,
                                c.ContractBasicInfo.CustomerName
                            );
                        });

                        $("tfoot", "#tblContractList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.contractList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: contract.List.ContractList,
                            callBackArgs: null
                        });


                    } else {
                        $("tfoot", "#tblContractList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
    }
}

$(document).ready(function () {
    $(window).resize(function () {
        payment.ResetSize();
    });

    payment.ResetSize();

    $(document).click(function () {
        $("#divUserList").off().hide();
        $("#divPaymentTypeList").off().hide();
        $("#divAssociateUserList").off().hide();
    });

    var businessOwner = new AssociateUser(
        $("#divAssociateUserList"),
        $("#SearchCondition_BusinessOwner"),
        $("#SearchCondition_BusinessOwnerName"),
        null
    );

    $("#SearchCondition_BusinessOwnerName").off().on("click", function () {
        $("#hidUserId").val("SearchCondition_BusinessOwner");
        $("#hidUserName").val("SearchCondition_BusinessOwnerName");
        $("#divUserList").css({
            "position": "absolute",
            "left": $("#SearchCondition_BusinessOwnerName").position().left + 16,
            "top": $("#SearchCondition_BusinessOwnerName").position().top + 70,
            "z-index": 1200
        }).toggle();
        return false;
    });

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

    $("#divPaymentTypeList").find("li").off().on("click", function () {
        var paymentTypeName = $(this).find("a").attr("name");
        var currentSelectedControl = $("#hidPaymentTypeName").val();
        $("#" + currentSelectedControl).val(paymentTypeName);
        $("#divPaymentTypeList").hide();
    });

    $("#Payment_PaymentBasic_PaymentModeName").off().on("click", function () {
        $("#hidPaymentTypeName").val("Payment_PaymentBasic_PaymentModeName");
        $("#divPaymentTypeList").off().css({
            "position": "absolute",
            "left": $("#Payment_PaymentBasic_PaymentModeName").position().left + 1,
            "top": $("#Payment_PaymentBasic_PaymentModeName").position().top + 28,
            "z-index": 1200
        }).show();
        return false;
    });

    $("#lblPaymentType").off().on("click", function () {
        payment.Payment.PaymentType.Open();
    });

    $("#lblInvoiceNo").off().on("click", function () {

        if ($("#Payment_PaymentBasic_InvoiceNo").val() == '')
        {
            var invoiceNo = payment.Payment.GenerateInvoiceNo();
            $("#Payment_PaymentBasic_InvoiceNo").val(invoiceNo);
        }
    });

    $("#btnPaymentTypeCancel,#btnPaymentTypeClose").off().on("click", function () {
        payment.Payment.PaymentType.Close();
    });
    
    $("#btnPaymentTypeSelected").off().on("click", function () {
        payment.Payment.PaymentType.Selected();
    });

    $("input[name='chkPaymentTypeId']").off().on("click", function () {
        payment.Payment.PaymentType.Select(this);
    });

    $("input[name='item_PaymentApply']").off().on("click", function () {
        payment.Payment.Objects.ObjectItem.Apply(this);
        payment.Payment.TotalAmountSet();
    });

    $("#Payment_PaymentBasic_PrePaidAmount").off().on("change", function () {

        if ($(this).val() == '') {
            $(this).val(0);
        }

        var prePaidAmount = parseFloat($("#Customer_CustomerBasic_PrePaidAmount").attr("prepaidamount")) + parseFloat($("#Payment_PaymentBasic_PrePaidAmount").val());
        $("#Customer_CustomerBasic_PrePaidAmount").val(prePaidAmount);

        payment.Payment.TotalAmountSet();
    });

    $("#btnPaymentApply").off().on("click", function () {
        payment.Payment.Appliction.CreateUpdate(true);
    });

    $("#item_PaymentAllApply").off().on("click", function () {
        if ($(this).prop("checked") == true) {
            $("input[name='item_PaymentApply']").each(
                function (i, e) {
                    $(e).attr("checked", "checked");
                    $(e).click();
                    $(e).attr("checked", "checked");
                }
            );
        }
        else {
            $("input[name='item_PaymentApply']").each(
                function (i, e) {
                    $(e).removeAttr("checked");
                    $(e).click();
                    $(e).removeAttr("checked");
                }
            );
        }
    });

    $("#item_CaseOfficeFeeCashAmount").off().on("change", function () {
        if (parseFloat($(this).val()) > parseFloat($(this).attr("caseofficefeeopencashamount"))) {
            $(this).val(0);
        }

        payment.Payment.TotalAmountSet();
    });

    $("#item_CaseNonOfficeFeeCashAmount").off().on("change", function () {
        if (parseFloat($(this).val()) > parseFloat($(this).attr("casenonofficefeeopencashamount"))) {
            $(this).val(0);
        }
        payment.Payment.TotalAmountSet();
    });

    $("#item_CaseCommissionFeeCashAmount").off().on("change", function () {
        if (parseFloat($(this).val()) > parseFloat($(this).attr("casecommissionfeeopencashamount"))) {
            $(this).val(0);
        }
        payment.Payment.TotalAmountSet();
    });
 
    $("#btnPaymentListSearch").off().on("click", function () {
        payment.List.PaymentList();
    });

    $("#btnContractListSearch").off().on("click", function () {
        contract.List.ContractList();
    });

    $("#btnPaymentListExportToExcel").click(function () {
        payment.List.PaymentListExportToExcel();
    });
    
});