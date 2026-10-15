var payment = {
    PaymentTypeId : {
        OfficeFee: 1,
        CommissionFee: 3
    },
    PaymentStatus: {
        D: 0,
        P: 1,
        IA: 2,
        Approved: 3,
        R: 4,
        ApplicaionCanceled: 5,
        Packing: 6,
        Paid: 7,
    },
    PageId: {
        PageId_5001003001: 5001003001,
        PageId_5001003002: 5001003002,
        PageId_5001003003: 5001003003,
        PageId_5001003004: 5001003004,
        PageId_5001003005: 5001003005,
        PageId_5001003006: 5001003006,
    },
    ResetSize: function () {
        $('#divContextList').slimScroll({
            height: '100%'
        });
        if ($("#divContextList").length > 0) {
            $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 22);

        }

        if ($("#divList").length > 0) {
            $("#divList").css("height", $(window).height() - $("#divList").offset().top - 12);
        }
    },
    Payment: {
        ViewContract: function(contractId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FCM/Contract/ContractView?contractId=" + contractId;
            addtabs(url, "查看合同");
            //window.open(url);
        },
        View: function(paymentId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/AP/PaymentView?paymentId=" + paymentId;
            addtabs(url, "查看请款单");
            //window.open(url);
        },
        Edit: function(paymentId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/AP/PaymentEdit?paymentId=" + paymentId;
            addtabs(url, "编辑请款单");
            //window.open(url);
        },

        /*申请撤回*/
        Cancel: function(paymentId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/AP/PaymentCancel?paymentId=" + paymentId;
            addtabs(url, "撤回请款单");
            //window.open(url);
        },

        /*审核*/
        Audit: function(paymentId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/AP/PaymentAudit?paymentId=" + paymentId;
            addtabs(url, "审核请款单");
            //window.open(url);
        },

        /*回滚*/
        Rollback: function (paymentId) {
            var data = {};
            data["PaymentId"] = paymentId;
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/FAM/Payment/PaymentRollback", data, function (response) {
                if (response.IsSuccess) {
                    payment.List.PaymentList();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        /**/
        Application: {
            CreateUpdate: function(isSubmit) {
                try {

                    if ($("#Payment_PaymentType_PaymentTypeId").val() == '') {
                        $.showModalMessageBox("请选择付款单位.");
                        return false;
                    }
 
                    payment.Payment.TotalAmountSet();

                    if ($("#Payment_PaymentBasic_PaidAmount").val() == '' || parseFloat($("#Payment_PaymentBasic_PaidAmount").val()) == 0 ) {
                        $.showModalMessageBox("付款金额不能为零.");
                        return false;
                    }

                    var data = {};

                    data["Payment.PaymentBasic.PaymentId"] = $("#Payment_PaymentBasic_PaymentId").val();
                    data["Payment.PaymentBasic.CustomerId"] = $("#Customer_CustomerBasic_CustomerId").val();
                    data["Payment.PaymentBasic.CustomerNo"] = $("#Customer_CustomerBasic_CustomerNo").val();
                    data["Payment.PaymentBasic.ContractId"] = $("#Contract_ContractBasicInfo_ContractId").val();
                    data["Payment.PaymentBasic.ContractNo"] = $("#Contract_ContractBasicInfo_ContractNo").val();
                    data["Payment.PaymentBasic.ApplicationNo"] = $("#Payment_PaymentBasic_ApplicationNo").val();
                    data["Payment.PaymentBasic.PayerName"] = $("#Payment_PaymentBasic_PayerName").val();
                    data["Payment.PaymentBasic.ApplicationDate"] = $("#Payment_PaymentBasic_ApplicationDate").val();
                    data["Payment.PaymentBasic.PaidAmount"] = $("#Payment_PaymentBasic_PaidAmount").val();
                    data["Payment.PaymentBasic.Remark"] = $("#Payment_PaymentBasic_Remark").val();
                    data["Payment.PaymentType.PaymentTypeId"] = $("#Payment_PaymentType_PaymentTypeId").val();
                    data["Payment.PaymentType.CaseFeeTypeId"] = $("#Payment_PaymentType_CaseFeeTypeId").val();

                    var i = 0;
                    $("#tblAPObjectList>tbody>tr").each(function (j, e) {

                        if ($(e).css("display") != 'none' && $(e).find("#item_PaymentApply").prop("checked") == true) {
                            
                            //官费
                            data["Payment.PaymentObjects[" + i + "].CaseFeeId"] = $(e).find("#item_CaseFeePayAmount").attr("CaseFeeId");
                            data["Payment.PaymentObjects[" + i + "].CaseFeeSeqId"] = $(e).find("#item_CaseFeePayAmount").attr("CaseFeeSeqId");
                            data["Payment.PaymentObjects[" + i + "].CaseFeePaidAmount"] = $(e).find("#item_CaseFeePayAmount").val();
                            data["Payment.PaymentObjects[" + i + "].CaseFeePrePaidAmount"] = $(e).find("#item_CaseFeePayAmount").attr("CaseFeePrePaidAmount");
  
                            if (parseFloat($(e).find("#item_CaseFeePayAmount").attr("caseofficefeepaidamount")) != parseFloat($(e).find("#item_CaseFeePayAmount").val())) {
                                data["Payment.PaymentObjects[" + i + "].IsChanged"] = true;
                            }

                            data["Payment.PaymentObjects[" + i + "].CaseId"] = $(e).find("#item_PaymentApply").attr("CaseId");
                            data["Payment.PaymentObjects[" + i + "].CaseNo"] = $(e).find("#item_PaymentApply").attr("CaseNo");
                            //data["Payment.PaymentObjects[" + i + "].CaseNo"] = $(e).find("#item_PaymentApply").val();

                            i++;
                        }
                    });

                    if (i == 0)
                    {
                        $.showModalMessageBox("无费用,不能申请付款.");
                        return false;
                    }

                    $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/FAM/Payment/PaymentCreateUpdate", data, function (response) {
                        if (response.IsSuccess) {

                            $.showModalConfirmDialog("提交成功", "payment.Payment.Application.CreateUpdateCallBack", response.Data.PaymentId);

                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {

                }
            },
            CreateUpdateCallBack: function (paymentId) {
                window.location = AP_ROOT + "5001003005/FAM/AP/PaymentView?paymentId=" + paymentId;
            },
            /*审批*/
            Audit: function(approved) {
                try {

                    var data = { "approved": approved };

                    data["Audit.PaymentId"] = $("#Payment_PaymentBasic_PaymentId").val();
                    data["Audit.AuditId"] = $("#Audit_AuditId").val();
                    data["Audit.AuditContent"] = $("#Audit_AuditContent").val();

                    $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/FAM/PaymentAudit/PaymentAuditCreate", data, function(response) {
                        if (response.IsSuccess) {
                            $.showModalConfirmDialog("审批成功.", 'payment.Payment.Application.AuditedCallBack', true, true);
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {

                }
            },
            AuditedCallBack: function (isSubmit) {
                window.location = AP_ROOT + "REDACTED_ARCHIVE_ONLY";
            },
            Canceled: function() {
                try {

                    if ($("#Payment_PaymentBasic_CancelCause").val() == '') {
                        $.showModalMessageBox("请输入撤回原因.");
                        $("#Payment_PaymentBasic_CancelCause").focus();
                        return false;
                    }

                    var data = {};

                    data["Payment.PaymentBasic.PaymentId"] = $("#Payment_PaymentBasic_PaymentId").val();
                    data["Payment.PaymentBasic.CancelCause"] = $("#Payment_PaymentBasic_CancelCause").val();

                    $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/FAM/Payment/PaymentCanceled", data, function(response) {
                        if (response.IsSuccess) {
                            $.showModalConfirmDialog(response.Message, 'payment.Payment.Application.CanceledCallBack', true, true);

                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {

                }
            },
            CanceledCallBack: function(isSubmit) {
                window.location = AP_ROOT + "5001003001/FAM/AP/PaymentList";
            },
        },

        TotalAmountSet: function() {
            var totalAmount = 0;
            $("input[name='item_CaseFeePayAmount']").each(
                function() {
                    if ($(this).val() == '') {
                        $(this).val(0);
                    }
                    totalAmount += parseFloat($(this).val());
                }
            );

            $("#Payment_PaymentBasic_PaidAmount").val(totalAmount);
        },

        Packing: {
            CreateUpdate: function (packingNo) {

                try {

                    var data = {
                        PackingNo: packingNo
                    };

                    $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/FAM/PaymentPacking/PackingOnNo", data, function(response) {
                        if (response.IsSuccess) {
                            window.open(AP_ROOT + AP_PAGE_ID + "/FAM/AP/PaymentPackingPrintToWordOnNo?packingNo=" + packingNo);
                            //window.location = AP_ROOT + AP_PAGE_ID + "/FAM/AP/PaymentPackingPrintOnNo?packingNo=" + packingNo;
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {
                }
            },
            CreateUpdateCallBack: function(packingId) {
                window.location = AP_ROOT + AP_PAGE_ID + "/FAM/AP/PaymentPackingPrint?packingId=" + packingId;
            },
            Verification: {
                Open: function(packingNo) {

                    var data = {
                        packingNo: packingNo
                    };

                    var url =  AP_ROOT + AP_PAGE_ID + "/FAM/AP/PaymentPackingVerify";
                    $.openLoading();

                    $("<div></div>").load(url, data, function(result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#packingVerifyModal').modal({ backdrop: 'static', keyboard: false });
                        $('#packingVerifyModal').on('hidden.bs.modal', function() {
                            $("#packingVerifyModal").remove();
                        });
                    });
                },
                Verify: function() {
                    try {
                        debugger
                        if ($("#Packing_PaymentPackingBasic_InvoiceNo").val() == '') {
                            $.showModalMessageBox("请输入付款单据号.");
                            $("#Packing_PaymentPackingBasic_InvoiceNo").focus();
                            return false;
                        }

                        if ($("#Packing_PaymentPackingBasic_PaidDate").val() == '') {
                            $.showModalMessageBox("请输入付款日期.");
                            $("#Packing_PaymentPackingBasic_PaidDate").focus();
                            return false;
                        }

                        if ($("#flInvoiceFile").val() == "") {
                            $.showModalMessageBox("请选择付款凭证文件.");
                            return false;
                        }

                        $.openLoading();
                        $('#paymentPackingForm').ajaxSubmit({
                            success: function (response) {
                                $.closeLoading();
                                if (response.IsSuccess) {
                                    $.showModalMessageBox("核销成功.");
                                    payment.Payment.Packing.Verification.Close();
                                    payment.List.PaymentList()
                                } else {
                                    $.showModalMessageBox(response.Message);
                                    return false;
                                }
                            }
                        });

                        //$("#paymentPackingForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/FAM/PaymentPacking/Validate", function(response) {
                        //    if (response.IsSuccess) {
                        //        $.showModalMessageBox("核销成功.");
                        //        payment.Payment.Packing.Verification.Close();
                        //        payment.List.PaymentList();
                        //    } else {
                        //        $.showModalMessageBox(response.Message);
                        //    }
                        //});

                    } catch (e) {

                    }
                },
                Close: function() {
                    $('#packingVerifyModal').modal('hide');
                }
            },
            View: function (packageNo) {
                var url = AP_ROOT + "5001003005/FAM/AP/PaymentList?packageNo=" + packageNo;
                addtabs(url, packageNo);
                //window.open(url);
            },
            Print: function (packingId) {
                var url = AP_ROOT + AP_PAGE_ID + "/FAM/AP/PaymentPackingPrint?packingId=" + packingId;
                addtabs(url, "打印请款单");
                //window.open(url);
            },
            PrintOnNo: function (packingNo) {
                var url = AP_ROOT + AP_PAGE_ID + "/FAM/AP/PaymentPackingPrintOnNo?packingNo=" + packingNo;
                addtabs(url, packingNo);
                //window.open(url);
            },
        },

        Objects: {
            ObjectItem: {
                Apply: function (e)
                {
                    var caseFeePayAmount = $(e).parents("tr").find("#item_CaseFeePayAmount");
                    if ($("#Payment_PaymentType_PaymentTypeId").val() == '') {
                        $(caseFeePayAmount).val(0);
                        $.showModalMessageBox("请选择收款单位.");
                        return false;
                    }  
                    
                    if ($(e).prop("checked") == true) {
                        $(caseFeePayAmount).val($(caseFeePayAmount).attr("casefeeopenpayamount") == undefined ? "0" : $(caseFeePayAmount).attr("casefeeopenpayamount"));
                    } else {
                        $(caseFeePayAmount).val(0);
                    }
                },

                CaseAmountSet: function (e) {

                    if ($(e).val() == '' || !$(e).isMoney()) {
                        $(e).val(0);
                    }

                    if (parseFloat($(e).val()) > parseFloat($(e).attr("casefeeopenpayamount"))) {
                        $(e).val(0);
                    }

                    var casefeeamount = parseFloat($(e).attr("casefeeamount")); //金额
                    var casefeepayamount = parseFloat($(e).val());   //本次支付金额
                    var casefeepaidamount = parseFloat($(e).attr("casefeepaidamount")); //已付款金额
                    var casefeecashedamount = parseFloat($(e).attr("casefeecashedamount")); //到账金额
                    var casefeeprepaidtotalamount = parseFloat($(e).attr("casefeeprepaidtotalamount")); //累计预付款金额

                    var casefeeprepaidamount = 0;

                    if ((casefeepayamount + casefeeprepaidtotalamount) > casefeecashedamount) {
                        //本次付款金额加之前垫付总金额 大于 到账金额
                        casefeeprepaidamount = casefeepayamount - casefeecashedamount;

                        var paymentAmount = (casefeeprepaidamount + casefeeprepaidtotalamount);
                        paymentAmount = Math.round(paymentAmount * 100) / 100;

                        //$(e).parent().parent().find("#item_PaymentRemark").html("费用累计垫付" + (paymentAmount) + "元");

                        $(e).attr("casefeeprepaidamount", casefeeprepaidamount);

                    }
                    else if (casefeeprepaidtotalamount > 0) {
                       // $(e).parent().parent().find("#item_PaymentRemark").html("费用累计垫付" + casefeeprepaidtotalamount + "元");

                        $(e).attr("casefeeprepaidamount", 0);
                    }
                    else {

                        //$(e).parent().parent().find("#item_PaymentRemark").html('');
                        $(e).attr("casefeeprepaidamount", 0);
                    }

                },

                CaseOfficeAmountSet : function (e)
                {

                    if ($(e).val() == '' || !$(e).isMoney()) {
                        $(e).val(0);
                    }

                    if (parseFloat($(e).val()) > parseFloat($(e).attr("caseofficefeeopenpayamount"))) {
                        $(e).val(0);
                    }

                    var caseofficefeeamount = parseFloat($(e).attr("caseofficefeeamount")); //金额
                    var caseofficefeepayamount = parseFloat($(e).val());   //本次支付金额
                    var caseofficefeepaidamount = parseFloat($(e).attr("caseofficefeepaidamount")); //已付款金额
                    var caseofficefeecashedamount = parseFloat($(e).attr("caseofficefeecashedamount")); //到账金额
                    var caseofficefeeprepaidtotalamount = parseFloat($(e).attr("caseofficefeeprepaidtotalamount")); //累计预付款金额

                    var caseofficefeeprepaidamount = 0;

                    if ((caseofficefeepayamount + caseofficefeeprepaidtotalamount) > caseofficefeecashedamount) {
                        //本次付款金额加之前垫付总金额 大于 到账金额
                        caseofficefeeprepaidamount = caseofficefeepayamount - caseofficefeecashedamount;

                        var paymentAmount = (caseofficefeeprepaidamount + caseofficefeeprepaidtotalamount);
                        paymentAmount = Math.round(paymentAmount * 100) / 100;

                        //$(e).parent().parent().find("#item_PaymentRemark").html("官费累计垫付" + (paymentAmount) + "元");

                        $(e).attr("caseofficefeeprepaidamount", caseofficefeeprepaidamount);

                    }
                    else if (caseofficefeeprepaidtotalamount > 0) {
                        //$(e).parent().parent().find("#item_PaymentRemark").html("官费累计垫付" + caseofficefeeprepaidtotalamount + "元");

                        $(e).attr("caseofficefeeprepaidamount", 0);
                    }
                    else {

                        //$(e).parent().parent().find("#item_PaymentRemark").html('');
                        $(e).attr("caseofficefeeprepaidamount", 0);
                    }

                },

                CaseCommissionAmountSet: function (e)
                {
                    if ($(e).val() == '' || !$(e).isMoney()) {
                        $(e).val(0);
                    }

                    if (parseFloat($(e).val()) > parseFloat($(e).attr("casecommissionfeeopenpayamount"))) {
                        $(e).val(0);
                    }

                    var casecommissionfeeamount = parseFloat($(e).attr("casecommissionfeeamount")); //金额
                    var casecommissionfeepayamount = parseFloat($(e).val());   //本次支付金额
                    var casecommissionfeepaidamount = parseFloat($(e).attr("casecommissionfeepaidamount")); //已付款金额
                    var casecommissionfeecashedamount = parseFloat($(e).attr("casecommissionfeecashedamount")); //到账金额
                    var casecommissionfeeprepaidtotalamount = parseFloat($(e).attr("casecommissionfeeprepaidtotalamount")); //累计预付款金额

                    var casecommissionfeeprepaidamount = 0;

                    if ((casecommissionfeepayamount + casecommissionfeeprepaidtotalamount) > casecommissionfeecashedamount) {
                        //本次付款金额加之前垫付总金额 大于 到账金额
                        casecommissionfeeprepaidamount = casecommissionfeepayamount - casecommissionfeecashedamount;

                        casecommissionfeeprepaidamount = Math.round(casecommissionfeeprepaidamount * 100) / 100;

                        var paymentAmount = (casecommissionfeeprepaidamount + casecommissionfeeprepaidtotalamount);
                        paymentAmount = Math.round(paymentAmount * 100) / 100;

                        //$(e).parents().parents().find("#item_PaymentRemark").html("其他费用累计垫付" + (paymentAmount) + "元");

                        $(e).attr("casecommissionfeeprepaidamount", casecommissionfeeprepaidamount);

                    }
                    else if (casecommissionfeeprepaidtotalamount > 0) {
                        //$(e).parents().parents().find("#item_PaymentRemark").html("其他费用累计垫付" + casecommissionfeeprepaidtotalamount + "元");

                        $(e).attr("casecommissionfeeprepaidamount", 0);
                    }
                    else {

                       // $(e).parents().parents().find("#item_PaymentRemark").html('');
                        $(e).attr("casecommissionfeeprepaidamount", 0);
                    }
                }
            },

            Clear: function () {
               
                $("input[name='item_CaseOfficeFeePayAmount']").each(
                    function () {
                        //$(this).val(0);
                        if ($("#Payment_PaymentType_CaseFeeTypeId").val() == payment.PaymentTypeId.OfficeFee) {
                            //$(this).parent().parent().find("#item_PaymentRemark").html('');
                            var caseofficefeeprepaidtotalamount = parseFloat($(this).attr("caseofficefeeprepaidtotalamount"));
                            if (caseofficefeeprepaidtotalamount > 0)
                            {
                                //$(this).parent().parent().find("#item_PaymentRemark").html("官费累计垫付" + caseofficefeeprepaidtotalamount + "元");
                            }
                        }
                    }
                );

                $("input[name='item_CaseCommissionFeePayAmount']").each(
                    function () {
                        //$(this).val();

                        if ($("#Payment_PaymentType_CaseFeeTypeId").val() == payment.PaymentTypeId.CommissionFee) {
                            //$(this).parent().parent().find("#item_PaymentRemark").html('');
                            var casecommissionfeeprepaidtotalamount = parseFloat($(this).attr("casecommissionfeeprepaidtotalamount"));
                            if(casecommissionfeeprepaidtotalamount>0)
                            {
                               // $(this).parent().parent().find("#item_PaymentRemark").html("其他费用累计垫付" + casecommissionfeeprepaidtotalamount + "元");
                            }
                        }
                    }
                );

                $("#Payment_PaymentBasic_PaidAmount").val(0);
            }
        },

        PaymentType: {
            Open: function () {

                var url = AP_ROOT + AP_PAGE_ID + "/FAM/PaymentType/PaymentTypeList";
                $.openLoading();

                $("<div></div>").load(url, null, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    payment.Payment.PaymentType.List();

                    $('#paymentTypeListModal').modal({ backdrop: 'static', keyboard: false });
                    $('#paymentTypeListModal').on('hidden.bs.modal', function () {
                        $("#paymentTypeListModal").remove();
                    });
                });
            },
            List: function () {
                $("#paymentTypeListForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/PaymentType/PaymentTypes", function (response) {
                    
                    if (response.IsSuccess) {
                        $("tbody", "#tblPaymentTypeList").clearRow();
                        if (response.Data.TotalItemCount > 0) {
                            $(".info_inall.layoutfix").show();
                            $.each(response.Data.PaymentTypeList, function (i, p) {
                                $("tbody", "#tblPaymentTypeList").addRow(
                                    "<input type='checkbox' name='chkPaymentTypeId' value='" + p.PaymentTypeId + "'paymentTyperName='" + p.PaymentTypeName + "'caseFeeTypeId='" + p.CaseFeeTypeId + "'organizationName='" + p.OrganizationName + "'accountbank='" + p.AccountBank + "'account='" + p.Account + "'>",
                                    p.CaseFeeTypeIdName,
                                    p.OrganizationName,
                                    p.AccountBank,
                                    p.Account);
                            });

                            $("tfoot", "#tblPaymentTypeList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.paymenttype").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: payment.Payment.PaymentType.List,
                                callBackArgs: null
                            });

                        } else {
                            $("tfoot", "#tblPaymentTypeList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                    }
                });
            },
            Select: function (e) {
                if ($(e).prop("checked") == true) {
                    $("input[name='chkPaymentTypeId']").removeAttr("checked");
                    $(e).attr("checked", "checked");
                }
            },
            Close: function () {
                $('#paymentTypeListModal').modal('hide');
            },
            Selected: function () {
                var e = $("input[name=chkPaymentTypeId]:checked");

                if ($(e).length > 0) {

                    $("#Payment_PaymentType_PaymentTypeId").val($(e).val());
                    $("#Payment_PaymentType_CaseFeeTypeId").val($(e).attr("caseFeeTypeId"));
                    $("#Payment_PaymentType_PaymentTypeName").val($(e).attr("paymenttypername"));
                    $("#Payment_PaymentType_OrganizationName").val($(e).attr("organizationname"));
                    $("#Payment_PaymentType_Account").val($(e).attr("account"));
                    $("#Payment_PaymentType_AccountBank").val($(e).attr("accountbank"));

                    $("#Payment_PaymentType_OrganizationName").html($(e).attr("organizationname"));
                    $("#Payment_PaymentType_Account").html($(e).attr("account"));
                    $("#Payment_PaymentType_AccountBank").html($(e).attr("accountbank"));

                }
                payment.Payment.Objects.Clear();
                payment.Payment.PaymentType.Close();
            },

            ObjectItem: {

                Open: function (paymentTypeId) {

                    var url = AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/PaymentType";
                    var data = {
                        paymentTypeId: paymentTypeId
                    };
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {

                        $.closeLoading();
                        $(document.body).append(result);

                        $('#paymentTypeModal').modal({ backdrop: 'static', keyboard: false });
                        $('#paymentTypeModal').on('hidden.bs.modal', function () {
                            $("#paymentTypeModal").remove();
                        });
                    });
                },

                Close: function () {
                    $('#paymentTypeModal').modal('hide');
                },

                CreateUpdate: function () {

                    if ($("#PaymentType_OrganizationName").val() == '') {
                        $.showModalMessageBox("请输入收款单位.");
                        return false;
                    }

                    //if ($("#PaymentType_PaymentTypeName").val() == '') {
                    //    $.showModalMessageBox("请输入类型名称.");
                    //    return false;
                    //}

                    var data = {};

                    data["PaymentType.PaymentTypeId"] = $("#PaymentType_PaymentTypeId").val();
                    data["PaymentType.CaseFeeTypeId"] = $("#PaymentType_CaseFeeTypeId").val();
                    data["PaymentType.PaymentTypeName"] = $("#PaymentType_CaseFeeTypeId").find("option:selected").text();
                    data["PaymentType.OrganizationName"] = $("#PaymentType_OrganizationName").val();
                    data["PaymentType.AccountBank"] = $("#PaymentType_AccountBank").val();
                    data["PaymentType.Account"] = $("#PaymentType_Account").val();

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/PaymentTypeCreateUpdate", data, function (response) {
                        if (response.IsSuccess) {
                            //$.showModalMessageBox("保存成功.");
                            payment.Payment.PaymentType.ObjectItem.Close();
                            payment.Payment.PaymentType.List();
                        }
                        else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                },
            }
        },
    },
    List: {
        BindMenu: function () {
            $('#paymentgridSection').contextMenu('paymentMenu', {
                menuStyle: {
                    width: '152px'
                },

                itemStyle: {
                    width: '150px'
                },

                bindings: {
                    'view': function (t, e) {
                        var paymentId = $(e).find("span").text();
                        if (paymentId == '') {
                            $.showModalMessageBox("请选择请款单号.");
                            return false;
                        }

                        payment.Payment.View(paymentId);
                    },
                    'edit': function (t, e) {
                        var paymentId = $(e).find("span").text();
                        if (paymentId == '') {
                            $.showModalMessageBox("请选择请款单号.");
                            return false;
                        }

                        payment.Payment.Edit(paymentId);

                        return true;
                    },
                    'cancel': function (t, e) {
                        var paymentId = $(e).find("span").text();
                        if (paymentId == '') {
                            $.showModalMessageBox("请选择请款单号.");
                            return false;
                        }

                        payment.Payment.Cancel(paymentId);

                        return true;
                    },
                    'rollback': function (t, e) {
                        var paymentId = $(e).find("span").text();
                        if (paymentId == '') {
                            $.showModalMessageBox("请选择请款单号.");
                            return false;
                        }

                        $.showModalConfirmDialog("确定回滚到待提交状态？", "payment.Payment.Rollback", paymentId);

                        return true;
                    },
 
                },
                onContextMenu: function (e) {
                    return true;
                },
                onShowMenu: function (e, menu) {
                    if ($(e.target).parents("tr").find(".paymentId").hasClass("paymentId")) {
                        var paymentId = $(e.target).parents("tr").find(".paymentId").text();
                        var paymentStatus = $(e.target).parents("tr").find(".paymentStatus").text();

                        if (paymentStatus == payment.PaymentStatus.P || paymentStatus == payment.PaymentStatus.D || paymentStatus == payment.PaymentStatus.R) {
                            $('#view', menu).append("<span style='display:none'>" + paymentId + "</span>");
                            $('#edit', menu).append("<span style='display:none'>" + paymentId + "</span>");
                            $('#cancel', menu).append("<span style='display:none'>" + paymentId + "</span>");
                            $('#rollback', menu).remove();
                        }
                        else if (paymentStatus == payment.PaymentStatus.Paid || paymentStatus == payment.PaymentStatus.ApplicaionCanceled) {
                            $('#view', menu).append("<span style='display:none'>" + paymentId + "</span>");
                            $('#edit,#cancel,#rollback', menu).remove();
                        }
                        else {
                            $('#view', menu).append("<span style='display:none'>" + paymentId + "</span>");
                            $('#rollback', menu).append("<span style='display:none'>" + paymentId + "</span>");
                            $('#edit,#cancel', menu).remove();
                        }

                    } else {
                        $('#view,#edit,#rollback,#cancel', menu).remove();
                    }
                    return menu;
                }
            });
        },
        PaymentList: function () {
            $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/FAM/Payment/PaymentList", function(response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        var totalAmount = 0;

                        $("tbody", "#tblPaymentList").addRow(
                              "",
                              "",
                              "",
                              "",
                              response.Data.TotalPaidAmount.toFixed(2),
                              "",
                              "",
                              "",
                              "",
                              ""
                          );

                        $.each(response.Data.PaymentList, function (i, c) {
                            totalAmount += c.PaymentBasic.PaidAmount;
                             

                            var operation = "";
                            if ($("#SearchCondition_PageId").val() == payment.PageId.PageId_5001003001  ) {
                                operation = "<a href='javascript:void(0)' onclick='javascript:payment.Payment.View(\"" + c.PaymentBasic.PaymentId + "\")'>查看</a> &nbsp; ";
                            } else if ($("#SearchCondition_PageId").val() == payment.PageId.PageId_5001003003) {
                                operation = "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Packing.PrintOnNo(\"" + c.PaymentBasic.PackageNo + "\")'>打印</a> &nbsp; ";
                            }
                            else if ($("#SearchCondition_PageId").val() == payment.PageId.PageId_5001003004) {
                                operation = "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Packing.PrintOnNo(\"" + c.PaymentBasic.PackageNo + "\")'>打印</a> &nbsp; ";
                            }
                            else if ($("#SearchCondition_PageId").val() == payment.PageId.PageId_5001003005) {
                                operation = "<a href='javascript:void(0)' onclick='javascript:payment.Payment.View(\"" + c.PaymentBasic.PaymentId + "\")'>查看</a> &nbsp; ";
                            }
                            else if ($("#SearchCondition_PageId").val() == payment.PageId.PageId_5001003006) {
                                operation = "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Packing.Verification.Open(\"" + c.PaymentBasic.PackageNo + "\")'>核销</a> &nbsp; ";
                            }

                            $("tbody", "#tblPaymentList").addRow(

                                operation,

                                "<span class='paymentId' style='display:none'>" + c.PaymentBasic.PaymentId + "</span>"
                               + "<span class='paymentStatus' style='display:none'>" + c.PaymentBasic.PaymentStatus + "</span>"
                               + "<a style='color: #039' href='javascript:void(0);' >" + c.PaymentBasic.ApplicationNo + "</a>",
                               c.PaymentBasic.PaymentStatusName,
                               c.PaymentBasic.ApplicationDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.ApplicationDate)),
                               c.PaymentBasic.PaidAmount,
                               "<a href='javascript:void(0)' onclick='javascript:c.View(\"" + c.PaymentBasic.FirstCaseNo + "\")'>" + c.PaymentBasic.FirstCaseNo + "</a> &nbsp; ",
                               c.PaymentBasic.FirstCasePhaseName,
                               "<a href='javascript:void(0)' onclick='javascript:payment.Payment.ViewContract(\"" + c.PaymentBasic.ContractId + "\")'>" + c.PaymentBasic.ContractNo + "</a> &nbsp;",
                               c.PaymentBasic.PaymentDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.PaymentDate)),
                               c.PaymentBasic.ApplicantName,
                               c.PaymentBasic.BusinessOwnerName,
                               c.PaymentBasic.PayerName
                            );
                        });

                        $("tbody", "#tblPaymentList").addRow(
                            "",
                            "",
                            "",
                            "",
                             totalAmount.toFixed(2),
                            "",
                            "",
                            "",
                            "",
                            ""
                        );

                        $("tfoot", "#tblPaymentList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.paymentList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: payment.List.PaymentList,
                            callBackArgs: null
                        });

                        payment.List.BindMenu();

                    } else {
                        $("tfoot", "#tblPaymentList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        PendingPaymentList: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Payment/PaymentList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.PaymentList, function (i, c) {
                            $("tbody", "#tblPaymentList").addRow(
                               "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Packing.PrintOnNo(\"" + c.PaymentBasic.PackageNo + "\")'>打印</a> &nbsp; ",
                                "<span class='paymentId' style='display:none'>" + c.PaymentBasic.PaymentId + "</span>"
                               + "<span class='paymentStatus' style='display:none'>" + c.PaymentBasic.PaymentStatus + "</span>"
                               + "<a style='color: #039' href='javascript:void(0);' >" + c.PaymentBasic.ApplicationNo + "</a>",
                               c.PaymentBasic.PaymentStatusName,
                               c.PaymentBasic.ApplicationDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.ApplicationDate)),
                                c.PaymentBasic.PaidAmount,
                                "<a href='javascript:void(0)' onclick='javascript:payment.Payment.ViewContract(\"" + c.PaymentBasic.ContractId + "\")'>" + c.PaymentBasic.ContractNo + "</a> &nbsp;",
                                c.PaymentBasic.ContractName,
                                c.PaymentBasic.PaymentDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.PaymentDate)),
                                c.PaymentBasic.ApplicantName,
                                c.PaymentBasic.PayerName,
                                c.PaymentBasic.CustomerName
                            );
                        });

                        $("tfoot", "#tblPaymentList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.paymentList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: payment.List.PaymentList,
                            callBackArgs: null
                        });

                        payment.List.BindMenu();

                    } else {
                        $("tfoot", "#tblPaymentList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        PendingList: function() {
            $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/FAM/PaymentAudit/PendingList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        var totalAmount = 0;
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.PaymentList, function (i, c) {
                            totalAmount += c.PaymentBasic.PaidAmount;
                            //var caseNo = c.PaymentBasic.CaseNos == null ? "" : c.PaymentBasic.CaseNos[0];
                            //var casePhaseName = c.PaymentBasic.CaseNos == null ? "" : c.PaymentBasic.CaseNos[0];
                            //var feeTypeName = c.PaymentBasic.CaseFeeTypeNames == null ? "" : c.PaymentBasic.CaseFeeTypeNames[0];
                            $("tbody", "#tblPaymentList").addRow(
                                "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Audit(\"" + c.PaymentBasic.PaymentId + "\")'>" + c.PaymentBasic.ApplicationNo + "</a> &nbsp; ",
                                c.PaymentBasic.FirstCaseFeeTypeName,
                                c.PaymentType.OrganizationName,
                                c.PaymentBasic.ApplicantName,
                                c.PaymentBasic.PaidAmount,
                                "<a href='javascript:void(0)' onclick='javascript:c.View(\"" + c.PaymentBasic.FirstCaseNo + "\")'>" + c.PaymentBasic.FirstCaseNo + "</a> &nbsp; ",
                                c.PaymentBasic.FirstCasePhaseName,
                                "<a href='javascript:void(0)' onclick='javascript:payment.Payment.ViewContract(\"" + c.PaymentBasic.ContractId + "\")'>" + c.PaymentBasic.ContractNo + "</a> &nbsp; ",
                                c.PaymentBasic.ContractName,
                                c.PaymentBasic.ApplicationDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.ApplicationDate)),
                                c.PaymentBasic.PaymentStatusName
                            );
                        });

                        $("tbody", "#tblPaymentList").addRow(
                            "",
                            "",
                            "",
                            "",
                             totalAmount.toFixed(2),
                            "",
                            "",
                            "",
                            "",
                            ""
                        );

                        $("tfoot", "#tblPaymentList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.paymentList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: payment.List.PendingList,
                            callBackArgs: null
                        });
                    } else {
                        $("tfoot", "#tblPaymentList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        PendingPackingList: function() {
            $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/FAM/PaymentPacking/PendingList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentPackingList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.PaymentPackingList, function (i, c) {
                            $("tbody", "#tblPaymentPackingList").addRow(
                                "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Packing.CreateUpdate(\"" + c.PaymentPackingBasic.PackingId + "\")'>打包提交</a> &nbsp; ",
                                c.PaymentPackingBasic.PackageNo,
                                c.PaymentObjects.length,
                                c.PaymentPackingBasic.PackingAmount,
                                c.PaymentPackingBasic.PaymentType.CaseFeeTypeIdName,
                                c.PaymentPackingBasic.PaymentType.PaymentTypeName,
                                c.PaymentPackingBasic.PaymentType.OrganizationName,
                                c.PaymentPackingBasic.PaymentType.Account
                            );
                        });

                        $("tfoot", "#tblPaymentPackingList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.paymentPackingList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: payment.List.PendingPackingList,
                            callBackArgs: null
                        });


                    } else {
                        $("tfoot", "#tblPaymentPackingList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        PackingList: function () {
            $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/FAM/PaymentPacking/PackingList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentPackingList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.PaymentPackingList, function (i, c) {
                            var operation = "";
                            if ($("#SearchCondition_PageId").val() == payment.PageId.PageId_5001003003) {
                                operation = "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Packing.Print(\"" + c.PaymentPackingBasic.PackingId + "\")'>提交</a> &nbsp; ";
                            } else if ($("#SearchCondition_PageId").val() == payment.PageId.PageId_5001003004) {
                                operation = "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Packing.Print(\"" + c.PaymentPackingBasic.PackingId + "\")'>查看-打印</a> &nbsp; ";
                            }
                            else if ($("#SearchCondition_PageId").val() == payment.PageId.PageId_5001003006) {
                                operation = "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Packing.Verification.Open(\"" + c.PaymentPackingBasic.PackingId + "\")'>核销</a> &nbsp; ";
                            }

                            $("tbody", "#tblPaymentPackingList").addRow(
                                operation,
                                "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Packing.View(\"" + c.PaymentPackingBasic.PackageNo + "\")'>" + c.PaymentPackingBasic.PackageNo + "</a> &nbsp; ",
                                c.PaymentObjects.length,
                                c.PaymentPackingBasic.PackingAmount,
                                c.PaymentPackingBasic.PackingStatusName,
                                c.PaymentPackingBasic.PaidDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentPackingBasic.PaidDate)),
                                c.PaymentPackingBasic.PaymentType.PaymentTypeName,
                                c.PaymentPackingBasic.PaymentType.PaymentTypeName,
                                c.PaymentPackingBasic.PaymentType.OrganizationName,
                                c.PaymentPackingBasic.PaymentType.Account
                            );
                        });

                        $("tfoot", "#tblPaymentPackingList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.paymentPackingList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: payment.List.PackingList,
                            callBackArgs: null
                        });
                    } else {
                        $("tfoot", "#tblPaymentPackingList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
    }
};

var c = {
    View: function (caseNo) {
        $.case.View(caseNo);
    },
};

$(document).ready(function () {

    var applicant = new AssociateUser(
        $("#divAssociateUserList"),
        $("#SearchCondition_Applicant"),
        $("#SearchCondition_ApplicantName"),
        null
    );

    var businessOwner = new AssociateUser(
    $("#divAssociateBusinessOwnerList"),
    $("#SearchCondition_BusinessOwner"),
    $("#SearchCondition_BusinessOwnerName"),
    null
);

    $(document).click(function () {
        $("#divUserList").off().on();
        $("#divAssociateUserList").off().on();
        $("#divCasePhaseCheckBoxList").off().hide();
        $("#divCaseTypeCheckBoxList").off().hide();
        $("#divCaseFeeTypeCheckBoxList").off().hide();
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

    $(window).resize(function () {
        payment.ResetSize();
    });

    payment.ResetSize();

    payment.Payment.TotalAmountSet();

    $(function () {

    });

    $(document).off('click', '#lblPaymentType').on('click', '#lblPaymentType', function () {
        payment.Payment.PaymentType.Open();
    });

    $(document).off('click', '#btnPaymentTypeSelected').on('click', '#btnPaymentTypeSelected', function () {
        payment.Payment.PaymentType.Selected();
    });

    $(document).off('click', '#btnPaymentTypeSearch').on('click', '#btnPaymentTypeSearch', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(10);
        payment.Payment.PaymentType.List();
    });

    $("input[name='chkPaymentTypeId']").off().on("click", function () {
        payment.Payment.PaymentType.Select(this);
    });

    $(document).off('click', '#item_PaymentApply').on('click', '#item_PaymentApply', function () {
   // $("input[name='item_PaymentApply']").off().on("click", function () {

        if ($("#Payment_PaymentType_PaymentTypeId").val() == '') {
            $.showModalMessageBox("请选择收款单位.");
            return false;
        }

        payment.Payment.Objects.ObjectItem.Apply(this);

        var trigger = $(this).parents("tr").find("#item_CaseFeePayAmount");
        payment.Payment.Objects.ObjectItem.CaseAmountSet(trigger);

        //if ($("#Payment_PaymentType_CaseFeeTypeId").val() == payment.PaymentTypeId.OfficeFee) {
        //    var trigger = $(this).parents("tr").find("#item_CaseOfficeFeePayAmount");
        //    payment.Payment.Objects.ObjectItem.CaseOfficeAmountSet(trigger);
        //} else if ($("#Payment_PaymentType_CaseFeeTypeId").val() == payment.PaymentTypeId.CommissionFee) {
        //    var trigger = $(this).parents("tr").find("#item_CaseCommissionFeePayAmount");
        //    payment.Payment.Objects.ObjectItem.CaseCommissionAmountSet(trigger);
        //}

        payment.Payment.TotalAmountSet();
    });

    $(document).off('click', '#btnPaymentApply').on('click', '#btnPaymentApply', function () {
        payment.Payment.Application.CreateUpdate(true);
    });

    $(document).off('click', '#item_PaymentAllApply').on('click', '#item_PaymentAllApply', function () {
        if ($(this).prop("checked") == true) {
            if ($("#Payment_PaymentType_PaymentTypeId").val() == '') {
                $.showModalMessageBox("请选择付款单位.");
                return false;
            }

            $("input[name='item_PaymentApply']").each(
                function (i,e) {
                    $(e).attr("checked", "checked");
                    $(e).click();
                    $(e).attr("checked", "checked");
                }
            );
        }
        else {
            $("input[name='item_PaymentApply']").each(
                function (i,e) {
                    $(e).removeAttr("checked");
                    $(e).click();
                    $(e).removeAttr("checked");
                }
            );
        }
    });

    $(document).off('click', '#item_CaseFeePayAmount').on('change', '#item_CaseFeePayAmount', function () {
        if ($("#Payment_PaymentType_PaymentTypeId").val() == '') {
            $(this).val(0);
            $.showModalMessageBox("请选择付款单位.");
            return false;
        }
        //else if ($("#Payment_PaymentType_CaseFeeTypeId").val() == payment.PaymentTypeId.CommissionFee) {
        //    $(this).val(0);
        //    $.showModalMessageBox("选择支付其他费用，则不能支付官费.");
        //    return false;
        //}
        payment.Payment.Objects.ObjectItem.CaseAmountSet(this);
        payment.Payment.TotalAmountSet();

    });

    $(document).off('click', '#btnPaymentApplicationApproved').on('click', '#btnPaymentApplicationApproved', function () {
        payment.Payment.Application.Audit(true);
    });

    $(document).off('click', '#btnPaymentApplicationRejected').on('click', '#btnPaymentApplicationRejected', function () {
        payment.Payment.Application.Audit(false);
    });

    $(document).off('click', '#btnPaymentApplicationCancel').on('click', '#btnPaymentApplicationCancel', function () {
        payment.Payment.Application.Canceled(true);
    });

    $(document).off('click', '#btnPackingVerify').on('click', '#btnPackingVerify', function () {
        payment.Payment.Packing.Verification.Verify();
    });

    $(document).off('click', '#btnPackingVerifyCancel,#btnPackingVerifyClose').on('click', '#btnPackingVerifyCancel,#btnPackingVerifyClose', function () {
        payment.Payment.Packing.Verification.Close(true);
    });

    $(document).off('click', '#btnPaymentApplyPrint').on('click', '#btnPaymentApplyPrint', function () {
        var packageNo = $("#Packing_PaymentPackingBasic_PackageNo").val();
        payment.Payment.Packing.CreateUpdate(packageNo);
    });

    $(document).off('click', '#btnPaymentPrint').on('click', '#btnPaymentPrint', function () {
        
        var packageNo = $("#Packing_PaymentPackingBasic_PackageNo").val();
        window.open(AP_ROOT + AP_PAGE_ID + "/FAM/AP/PaymentPackingPrintToWordOnNo?packingNo=" + packageNo);
    });

    $(document).off('click', '#btnExportToWord').on('click', '#btnExportToWord', function () {
        var packingId = $("#Packing_PaymentPackingBasic_PackingId").val();
        window.open(AP_ROOT + AP_PAGE_ID + "/FAM/AP/PaymentPackingPrintToWord?packingId=" + packingId);
    });

    $(document).off('click', '#btnPaymentType').on('click', '#btnPaymentType', function () {
        payment.Payment.PaymentType.ObjectItem.CreateUpdate();
    });

    $(document).off('click', '#btnPaymentTypeCreate').on('click', '#btnPaymentTypeCreate', function () {
        payment.Payment.PaymentType.ObjectItem.Open();
    });

    $(document).off('click', '#btnPaymentTypeClose').on('click', '#btnPaymentTypeClose', function () {
        payment.Payment.PaymentType.ObjectItem.Close();
    });

    $(document).off('click', '#btnPaymentTypeCancel').on('click', '#btnPaymentTypeCancel', function () {
        payment.Payment.PaymentType.ObjectItem.Close();
    });

    $(document).off('click', '#divCaseFeeTypeCheckBoxList ul li').on('click', '#divCaseFeeTypeCheckBoxList ul li', function (e) {

        if ($(e.target).is("lable")) {
            e.stopPropagation();
            return false;
        }

        var currentSelectedControl = $("#hidCaseFeeTypeName").val();
        var currentSelectedIdControl = $("#hidCaseFeeTypeId").val();

        if ($(this).attr("id") == 'btnAllUnSelected') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }
        else if ($(this).attr("id") == 'btnAllSelected') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }

        $("#" + currentSelectedControl).val('');
        $("#" + currentSelectedIdControl).val('');

        var caseFeeTypeNames = '';
        var caseFeeTypeIds = '';

        $("#divCaseFeeTypeCheckBoxList").find("input:checkbox").each(function () {
            if ($(this).prop("checked") == true) {
                caseFeeTypeNames += $(this).attr("casefeetypename") + ",";
                caseFeeTypeIds += $(this).attr("casefeetypeid") + ",";
            }
        });

        $("#" + currentSelectedControl).val(caseFeeTypeNames.substring(0, caseFeeTypeNames.length - 1));
        $("#" + currentSelectedIdControl).val(caseFeeTypeIds.substring(0, caseFeeTypeIds.length - 1));

        e.stopPropagation();

        return true;
    });

    $(document).off('click', '#SearchCondition_CaseFeeTypeName').on('click', '#SearchCondition_CaseFeeTypeName', function () {
        var tirgger = this;
        var html = $.lsCaseFeeType.getCaseFeeTypeCheckBoxListHtml();
        $(".divcaseconditioncasefeetypes").html(html);
        $("#hidCaseFeeTypeId").val("SearchCondition_CaseFeeTypeId");
        $("#hidCaseFeeTypeName").val($(tirgger).attr("id"));
        $("#divCaseFeeTypeCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left + 16,
            "top": $(tirgger).parent().position().top + 25,
            "z-index": 9999
        }).toggle();

        return false;
    });

    $(document).off('click', '#flInvoiceFile').on('change', '#flInvoiceFile', function (e) {
        $("#txtInvoiceFilePath").val($("#flInvoiceFile").val());
    });
    
});