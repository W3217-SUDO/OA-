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
        PageId_5001004001: 5001004001,
        PageId_5001004002: 5001004002,
        PageId_5001004003: 5001004003,
        PageId_5001004004: 5001004004,
        PageId_5001004005: 5001004005,
        PageId_5001004006: 5001004006,
        PageId_5001004012: 5001004012,
        PageId_5001004013: 5001004013
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
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentView?paymentId=" + paymentId;
            addtabs(url, "查看请款单");
            //window.open(url);
        },
        Edit: function(paymentId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentEdit?paymentId=" + paymentId;
            addtabs(url, "编辑请款单");

            //window.open(url);
        },

        /*申请撤回*/
        Cancel: function(paymentId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentCancel?paymentId=" + paymentId;
            addtabs(url, "作废请款单");
            //window.open(url);
        },

        Audit: {
            SingleAudit: function (paymentId) {
                //debugger
                var paymentIds = new Array();
                paymentIds.push(paymentId);
                payment.Payment.Audit.MultiAudit(paymentIds);
            },

            MultiAudit: function (paymentIds) {
                if (paymentIds == null || paymentIds.length == 0) {
                    $.showModalMessageBox("请选择审批项.");
                    return false;
                }

                var data =
                {
                    paymentIds: paymentIds.join(",")
                };

                var url = AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/MultiAudit";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(".slide-panel-container").empty();
                    $(".slide-panel-container").append(result);
                    $(".slide-panel-container").addClass("show-panel");
                    //c.Cases.Case.InternalFees.InternalFee.Objects.List(caseNos);
                });
            },
        },

        ///*审核*/
        //Audit: function(paymentId) {
        //    var url = AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentAudit?paymentId=" + paymentId;
        //    window.open(url);
        //},

        /*回滚*/
        Rollback: function (paymentId) {
            var data = {};
            data["PaymentId"] = paymentId;
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentRollback", data, function (response) {
                if (response.IsSuccess) {
                    payment.List.PaymentList();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        Application: {
            CreateUpdate: function(isSubmit) {
                try {

                    //payment.Payment.TotalAmountSet();

                    //if ($("#Payment_PaymentBasic_PaidAmount").val() == '' || parseFloat($("#Payment_PaymentBasic_PaidAmount").val()) == 0 ) {
                    //    $.showModalMessageBox("付款金额不能为零.");
                    //    return false;
                    //}

                    var data = {};

                    data["Payment.PaymentBasic.CaseId"] = $("#Case_Basic_CaseId").val();
                    data["Payment.PaymentBasic.CaseNo"] = $("#Case_Basic_CaseNo").val();
                    data["Payment.PaymentBasic.PaymentId"] = $("#Payment_PaymentBasic_PaymentId").val();
                    data["Payment.PaymentBasic.CustomerId"] = $("#Customer_CustomerBasic_CustomerId").val();
                    data["Payment.PaymentBasic.CustomerNo"] = $("#Customer_CustomerBasic_CustomerNo").val();
                    data["Payment.PaymentBasic.ContractId"] = $("#Contract_ContractBasicInfo_ContractId").val();
                    data["Payment.PaymentBasic.ContractNo"] = $("#Contract_ContractBasicInfo_ContractNo").val();
                    data["Payment.PaymentBasic.ApplicationNo"] = $("#Payment_PaymentBasic_ApplicationNo").val();
                    data["Payment.PaymentBasic.PayerName"] = $("#Payment_PaymentBasic_PayerName").val();
                    data["Payment.PaymentBasic.ApplicationDate"] = $("#Payment_PaymentBasic_ApplicationDate").val();
                    //data["Payment.PaymentBasic.PaidAmount"] = $("#Payment_PaymentBasic_PaidAmount").val();
                    data["Payment.PaymentBasic.Remark"] = $("#Payment_PaymentBasic_Remark").val();
 
                    var i = 0;
                    $("#tblAPObjectList>tbody>tr").each(function(j, e) {
                        if ($(e).css("display") != 'none') {
                            
                            data["Payment.PaymentObjects[" + i + "].InternalFeeId"] = $(e).find("#item_InternalFeePayAmount").attr("InternalFeeId");
                            data["Payment.PaymentObjects[" + i + "].InternalFeeSeqId"] = $(e).find("#item_InternalFeePayAmount").attr("InternalFeeSeqId");
                            data["Payment.PaymentObjects[" + i + "].InternalFeePaidAmount"] = $(e).find("#item_InternalFeePayAmount").val();
                            data["Payment.PaymentObjects[" + i + "].InternalFeePrePaidAmount"] = $(e).find("#item_InternalFeePayAmount").attr("InternalFeePrePaidAmount");
  
                            if (parseFloat($(e).find("#item_InternalFeePayAmount").attr("caseofficefeepaidamount")) != parseFloat($(e).find("#item_InternalFeePayAmount").val())) {
                                data["Payment.PaymentObjects[" + i + "].IsChanged"] = true;
                            }

                            data["Payment.PaymentObjects[" + i + "].CaseId"] = $("#Case_Basic_CaseId").val();
                            data["Payment.PaymentObjects[" + i + "].CaseNo"] = $("#Case_Basic_CaseNo").val();

                            i++;
                        }
                    });

                    if (i == 0)
                    {
                        $.showModalMessageBox("无费用,不能申请付款.");
                        return false;
                    }

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentCreateUpdate", data, function (response) {
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
                var url = AP_ROOT + "5001004005/FAM/InternalFee/PaymentView?paymentId=" + paymentId;
                addtabs(url, "查看请款单");
                //window.location = AP_ROOT + "5001004005/FAM/InternalFee/PaymentView?paymentId=" + paymentId;
            },
            /*审批*/
            Audit: function(approved) {
                try {

                    var data = {
                        paymentIds : $("#PaymentIds").val().split(","),
                        approved: approved,
                        auditContent: $("#Audit_AuditContent").val()
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentAuditCreate", data, function (response) {
                        if (response.IsSuccess) {
                            $.showModalMessageBox("审批成功");
                            payment.List.PendingList();
                            $('.slide-panel-container').empty();
                            $('.slide-panel-container').removeClass('show-panel');
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

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentCanceled", data, function (response) {
                        if (response.IsSuccess) {
                            $.showModalConfirmDialog(response.Message, 'payment.Payment.Application.CanceledCallBack', true, true);

                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {

                }
            },
            CanceledCallBack: function (isSubmit) {

                window.location = AP_ROOT + "REDACTED_ARCHIVE_ONLY";
            },
        },

        TotalAmountSet: function() {
            var totalAmount = 0;
            $("input[name='item_InternalFeePayAmount']").each(
                function() {
                    if ($(this).val() == '') {
                        $(this).val(0);
                    }
                    totalAmount += parseFloat($(this).val());
                }
            );
 

            $("#Payment_PaymentBasic_PaidAmount").val(totalAmount);
        },

        Objects: {

            ObjectItem: {
                Apply: function (e)
                {
  
                },

                CaseAmountSet: function (e) {

                    if ($(e).val() == '' || !$(e).isMoney()) {
                        $(e).val(0);
                    }

                    if (parseFloat($(e).val()) > parseFloat($(e).attr("internalfeeopenpayamount"))) {
                        $(e).val(0);
                    }

                    var internalfeeamount = parseFloat($(e).attr("internalfeeamount")); //金额
                    var internalfeepayamount = parseFloat($(e).val());   //本次支付金额
                    var internalfeepaidamount = parseFloat($(e).attr("internalfeepaidamount")); //已付款金额
                    var internalfeecashedamount = parseFloat($(e).attr("internalfeecashedamount")); //到账金额
                    var internalfeeprepaidtotalamount = parseFloat($(e).attr("internalfeeprepaidtotalamount")); //累计预付款金额

                    var internalfeeprepaidamount = 0;

                    if ((internalfeepayamount + internalfeeprepaidtotalamount) > internalfeecashedamount) {
                        //本次付款金额加之前垫付总金额 大于 到账金额
                        internalfeeprepaidamount = internalfeepayamount - internalfeecashedamount;

                        var paymentAmount = (internalfeeprepaidamount + internalfeeprepaidtotalamount);
                        paymentAmount = Math.round(paymentAmount * 100) / 100;

                        $(e).attr("internalfeeprepaidamount", internalfeeprepaidamount);

                    }
                    else if (internalfeeprepaidtotalamount > 0) {

                        $(e).attr("internalfeeprepaidamount", 0);
                    }
                    else {

                        $(e).attr("internalfeeprepaidamount", 0);
                    }
                },
 
            },
            Clear: function () {
                $("#item_InternalFeePayAmount").val(0);
            },
            Packing: {

                CreateUpdate: function (paymentObjectIds) {

                    try {

                        var data = {
                            paymentObjectIds: paymentObjectIds
                        };

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/Packing", data, function (response) {
                            if (response.IsSuccess) {
                                //window.open(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentPackingPrintToWordOnNo?packingNo=" + packingNo);
                                window.location = AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentPackingPrintOnNo?packingNo=" + response.Data;
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });

                    }
                    catch (e) {
                    }
                },
                CreateUpdateCallBack: function (packingNo) {
                    window.location = AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentPackingPrintOnNo?packingNo=" + packingNo;
                },
                Verification: {
                    Open: function (packingNo) {

                        var data = {
                            packingNo: packingNo
                        };

                        var url = AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentPackingVerify";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#packingVerifyModal').modal({ backdrop: 'static', keyboard: false });
                            $('#packingVerifyModal').on('hidden.bs.modal', function () {
                                $("#packingVerifyModal").remove();
                            });
                        });
                    },
                    Verify: function () {
                        try {

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

                            $("#paymentPackingForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/Validate", function (response) {
                                if (response.IsSuccess) {
                                    $.showModalMessageBox("核销成功.");
                                    payment.Payment.Objects.Packing.Verification.Close();
                                    payment.List.PackingList();
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });

                        } catch (e) {

                        }
                    },
                    Close: function () {
                        $('#packingVerifyModal').modal('hide');
                    }
                },
                View: function (packageNo) {
                    var url = AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentPackingPrint?packingNo=" + packageNo;
                    addtabs(url, packageNo);
                    //window.open(url);
                },

                /*确认已付款*/
                ClosePacking: function (packingNo) {

                    try {

                        var data = {
                            packingNo: packingNo
                        };

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/ClosePacking", data, function (response) {
                            if (response.IsSuccess) {
                                window.open(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentPackingPrintToWordOnNo?packingNo=" + packingNo);
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });

                    }
                    catch (e) {
                    }

                    var url = AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentPackingPrintOnNo?packingNo=" + packingNo;
                    window.open(url);
                },

                PrintOnNo: function (packingNo) {
                    var url = AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentPackingPrintOnNo?packingNo=" + packingNo;
                    window.open(url);
                },

                Print: function (packingNo) {
                    var url = AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentPackingPrintToWordOnNo?packingNo=" + packingNo;
                    window.open(url);
                },
            },
            Selected: function (e) {
                if ($(e).prop('checked') == true) {
                    $.checkbox.all("chkPaymentObjectId");
                    $.checkbox.all("chkPaymentAll");

                } else {
                    $.checkbox.not("chkPaymentObjectId");
                    $.checkbox.not("chkPaymentAll");
                }
            },
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

        Selected: function (e) {
            if ($(e).prop('checked') == true) {
                $.checkbox.all("chkPaymentId");
                $.checkbox.all("chkPaymentAll");

            } else {
                $.checkbox.not("chkPaymentId");
                $.checkbox.not("chkPaymentAll");
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
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        var totalAmount = 0;
                        $.each(response.Data.PaymentList, function (i, c) {
                            var operation = "";
                            if ($("#SearchCondition_PageId").val() == payment.PageId.PageId_5001004001  ) {
                                operation = "<a href='javascript:void(0)' onclick='javascript:payment.Payment.View(\"" + c.PaymentBasic.PaymentId + "\")'>查看</a> &nbsp; ";
                            } else if ($("#SearchCondition_PageId").val() == payment.PageId.PageId_5001004003) {
                                operation = "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Packing.PrintOnNo(\"" + c.PaymentBasic.PackageNo + "\")'>打印</a> &nbsp; ";
                            }
                            else if ($("#SearchCondition_PageId").val() == payment.PageId.PageId_5001004004) {
                                operation = "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Packing.Verification.Open(\"" + c.PaymentBasic.PackageNo + "\")'>核销</a> &nbsp; ";
                            }
                            else if ($("#SearchCondition_PageId").val() == payment.PageId.PageId_5001004005) {
                                operation = "<a href='javascript:void(0)' onclick='javascript:payment.Payment.View(\"" + c.PaymentBasic.PaymentId + "\")'>查看</a> &nbsp; ";
                            }
                            else if ($("#SearchCondition_PageId").val() == payment.PageId.PageId_5001004012 ) {
                                operation = "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Cancel(\"" + c.PaymentBasic.PaymentId + "\")'>作废</a> &nbsp; ";
                            }
                            else if ($("#SearchCondition_PageId").val() == payment.PageId.PageId_5001004013) {
                                operation = "<a href='javascript:void(0)' onclick='javascript:payment.Payment.View(\"" + c.PaymentBasic.PaymentId + "\")'>查看</a> &nbsp; ";
                            }
                            
             
                            totalAmount += c.PaymentBasic.PaidAmount;
                            $("tbody", "#tblPaymentList").addRow(
                                operation,
                                "<span class='paymentId' style='display:none'>" + c.PaymentBasic.PaymentId + "</span>"
                               + "<span class='paymentStatus' style='display:none'>" + c.PaymentBasic.PaymentStatus + "</span>"
                               + "<a style='color: #039' href='javascript:void(0);' >" + c.PaymentBasic.ApplicationNo + "</a>",
                               c.PaymentBasic.PaymentStatusName,
                               c.PaymentBasic.ApplicationDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.ApplicationDate)),
                               (c.Audit == null || c.Audit.AuditDate == null) ? '' : getDate(convertJsonDateToJSDate(c.Audit.AuditDate)),
                               c.PaymentBasic.PaidAmount.toFixed(2),
                               "<a href='javascript:void(0)' onclick='javascript:c.View(\"" + c.PaymentBasic.CaseNo + "\")'>" + c.PaymentBasic.CaseNo + "</a> &nbsp;",
                               c.PaymentBasic.CasePhaseName,
                               c.PaymentBasic.CaseName,
                               c.PaymentBasic.PaymentDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.PaymentDate)),
                               c.PaymentBasic.ApplicantName
                               
                            );
                        });

                        $("tbody", "#tblPaymentList").addRow(
                            "",
                            "",
                            "",
                            "",
                            "",
                            totalAmount.toFixed(2),
                            "",
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
        PendingList: function() {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PendingList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                       
                        var totalAmount = 0.00;
                        $.each(response.Data.PaymentList, function (i, c) {
                            totalAmount = parseFloat(totalAmount) + parseFloat(c.PaymentBasic.PaidAmount);
                            $("tbody", "#tblPaymentList").addRow(
                                "<input type='checkbox' id='chkPaymentId' name='chkPaymentId'  value=" + c.PaymentBasic.PaymentId + ">",
                                "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Audit.SingleAudit(\"" + c.PaymentBasic.PaymentId + "\")'>审批</a> &nbsp; ",
                                "<span class='paymentId' style='display:none'>" + c.PaymentBasic.PaymentId + "</span>"
                               + "<span class='paymentStatus' style='display:none'>" + c.PaymentBasic.PaymentStatus + "</span>"
                               + "<a style='color: #039' href='javascript:void(0);' >" + c.PaymentBasic.ApplicationNo + "</a>",
                               c.PaymentBasic.PaymentStatusName,
                               c.PaymentBasic.ApplicationDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.ApplicationDate)),
                               c.PaymentBasic.PaidAmount.toFixed(2),
                               "<a href='javascript:void(0)' onclick='javascript:c.View(\"" + c.PaymentBasic.CaseNo + "\")'>" + c.PaymentBasic.CaseNo + "</a> &nbsp;",
                               c.PaymentBasic.CasePhaseName,
                               c.PaymentBasic.CaseName,
                               c.PaymentBasic.ApplicantName,
                               c.PaymentBasic.CustomerName
                            );
                        });

                        $("tbody", "#tblPaymentList").addRow(
                            "",
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
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PackingList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentPackingList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        var totalAmount = 0;

                        $("tbody", "#tblPaymentPackingList").addRow(
                            "",
                            "",
                            "",
                            response.Data.TotalPaidAmount.toFixed(2),
                            "",
                            "",
                            "",
                            ""
                        );
                        
                        $.each(response.Data.PaymentPackingList, function (i, c) {

                            var operation = "";
                            totalAmount += c.PaymentPackingBasic.PackingAmount;


                            if ($("#SearchCondition_PageId").val() == payment.PageId.PageId_5001004006) {
                                operation = "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Objects.Packing.View(\"" + c.PaymentPackingBasic.PackageNo + "\")'>查看</a> &nbsp; ";
                            }  
                            else if ($("#SearchCondition_PageId").val() == payment.PageId.PageId_5001004004) {
                                operation = "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Objects.Packing.Verification.Open(\"" + c.PaymentPackingBasic.PackageNo + "\")'>核销</a> &nbsp; ";
                            }

                            //debugger
                            $("tbody", "#tblPaymentPackingList").addRow(
                                operation,
                                "<a href='javascript:void(0)' onclick='javascript:payment.Payment.Objects.Packing.View(\"" + c.PaymentPackingBasic.PackageNo + "\")'>" + c.PaymentPackingBasic.PackageNo + "</a> &nbsp; ",
                                (c.PaymentItemObjects != null && c.PaymentItemObjects.length > 0) ? c.PaymentItemObjects[0].PaymentObjectName : '',
                                c.PaymentPackingBasic.PackingAmount,
                                c.PaymentPackingBasic.PackingStatusName,
                                c.PaymentPackingBasic.PaidDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentPackingBasic.PaidDate)),
                                c.PaymentPackingBasic.InvoiceNo,
                                c.PaymentPackingBasic.Remark
                            );
                        });

                        $("tbody", "#tblPaymentPackingList").addRow(
                            "",
                            "",
                            "",
                            totalAmount.toFixed(2),
                            "",
                            "",
                            "",
                            ""                           
                        );

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
        PaymentObjectList: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/PaymentObjectList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentObjectList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        var totalAmount = 0;
                        $.each(response.Data.PaymentList, function (i, c) {
                            $.each(c.PaymentObjects, function (i, paymentObject) {
                                totalAmount += paymentObject.InternalFeePaidAmount;
                                var operation = "";
                                $("tbody", "#tblPaymentObjectList").addRow(
                                  "<input type='checkbox' id='chkPaymentObjectId' name='chkPaymentObjectId' paymentObject=" + paymentObject.PaymentObject + " value="   + paymentObject.InternalFeeSeqId + ">",
                                   paymentObject.PaymentObjectStatusName,
                                   c.PaymentBasic.ApplicantName,
                                   c.PaymentBasic.ApplicationDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.ApplicationDate)),
                                   (c.Audit == null || c.Audit.AuditDate == null) ?  '' : getDate(convertJsonDateToJSDate(c.Audit.AuditDate)),
                                   paymentObject.PaymentObjectName,
                                   $.lsCaseFeeType.getCaseFeeTypeName(paymentObject.InternalFeeTypeId),
                                   paymentObject.BaseAmount.toFixed(2),
                                   paymentObject.PerformanceAmount.toFixed(2),
                                   paymentObject.InternalFeePaidAmount == paymentObject.PerformanceAmount ? paymentObject.InternalFeePaidAmount.toFixed(2) : "<span style='color:red'>" + paymentObject.InternalFeePaidAmount.toFixed(2) + "</span>",
                                   "<a href='javascript:void(0)' onclick='javascript:c.View(\"" + c.PaymentBasic.CaseNo + "\")'>" + c.PaymentBasic.CaseNo + "</a> &nbsp;",
                                   c.PaymentBasic.CasePhaseName,
                                   c.PaymentBasic.CaseName,
                                   c.PaymentBasic.PaymentDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.PaymentDate)),
                                   c.PaymentBasic.ContractName
                                );
                            });
                        });
                        $("tbody", "#tblPaymentObjectList").addRow(
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            totalAmount.toFixed(2),
                            "",
                            "",
                            "",
                            ""
                        );
                        $("tfoot", "#tblPaymentObjectList").show();
                        $(".simple-grid-none-data-wrap").hide();
                        $(".pull-right.page-box.paymentObjectList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: payment.List.PaymentObjectList,
                            callBackArgs: null
                        });
                        payment.List.BindMenu();

                    } else {
                        $("tfoot", "#tblPaymentObjectList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
    }
};

var c = {
    View: function (caseNo) {
        var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + caseNo;
        addtabs(url, caseNo);
        //window.open(url);
    },
};

$(document).ready(function () {

    var applicant = new AssociateUser(
        $("#divAssociateUserList"),
        $("#SearchCondition_Applicant"),
        $("#SearchCondition_ApplicantName"),
        null
    );

    var paymentObject = new AssociateUser(
        $("#divAssociateUserList"),
        $("#SearchCondition_PaymentObject"),
        $("#SearchCondition_PaymentObjectName"),
        null
    );

    //$("#SearchCondition_ApplicantName").off().on("click", function () {
    //    $("#hidUserId").val("SearchCondition_Applicant");
    //    $("#hidUserName").val("SearchCondition_ApplicantName");
    //    $("#divUserList").css({
    //        "position": "absolute",
    //        "left": $("#SearchCondition_ApplicantName").position().left + 16,
    //        "top": $("#SearchCondition_ApplicantName").position().top + 70,
    //        "z-index": 1200
    //    }).toggle();
    //    return false;
    //});

    $(document).click(function () {
        //$("#divCasePhaseCheckBoxList").off().hide();
        //$("#divCaseTypeCheckBoxList").off().hide();
        //$("#divCaseFeeTypeCheckBoxList").off().hide();
        $("#divUserList").off().on();
        $("#divAssociateUserList").off().on();
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
    
    $(document).off('click', '#btnPaymentApplyPrint').on('click', '#btnPaymentApplyPrint', function () {
        var packageNo = $("#Packing_PaymentPackingBasic_PackageNo").val();
        payment.Payment.Objects.Packing.ClosePacking(packageNo);
    });

    $(document).off('click', '#btnPaymentPrint').on('click', '#btnPaymentPrint', function () {
        var packageNo = $("#Packing_PaymentPackingBasic_PackageNo").val();
        payment.Payment.Objects.Packing.Print(packageNo);
    });

    $(document).off('click', '#btnPackingVerify').on('click', '#btnPackingVerify', function () {
        payment.Payment.Objects.Packing.Verification.Verify();
    });

    $(document).off('click', '#btnPackingVerifyCancel,#btnPackingVerifyClose').on('click', '#btnPackingVerifyCancel,#btnPackingVerifyClose', function () {
        payment.Payment.Objects.Packing.Verification.Close(true);
    });

    $(document).off('click', '#divCaseTypeCheckBoxList ul li').on('click', '#divCaseTypeCheckBoxList ul li', function (e) {

        if ($(e.target).is("lable")) {
            e.stopPropagation();
            return false;
        }

        var currentSelectedControl = $("#hidCaseTypeName").val();
        var currentSelectedIdControl = $("#hidCaseTypeId").val();

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

        var caseTypeNames = '';
        var caseTypeIds = '';

        $("#divCaseTypeCheckBoxList").find("input:checkbox").each(function () {

            if ($(this).prop("checked") == true) {
                caseTypeNames += $(this).attr("casetypename") + ",";
                caseTypeIds += $(this).attr("casetypeid") + ",";
            }

        });

        $("#" + currentSelectedControl).val(caseTypeNames.substring(0, caseTypeNames.length - 1));
        $("#" + currentSelectedIdControl).val(caseTypeIds.substring(0, caseTypeIds.length - 1));

        e.stopPropagation();

        return true;
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

        var internalFeeTypeNames = '';
        var internalFeeTypeIds = '';

        $("#divCaseFeeTypeCheckBoxList").find("input:checkbox").each(function () {
            if ($(this).prop("checked") == true) {
                internalFeeTypeNames += $(this).attr("casefeetypename") + ",";
                internalFeeTypeIds += $(this).attr("casefeetypeid") + ",";
            }
        });

        $("#" + currentSelectedControl).val(internalFeeTypeNames.substring(0, internalFeeTypeNames.length - 1));
        $("#" + currentSelectedIdControl).val(internalFeeTypeIds.substring(0, internalFeeTypeIds.length - 1));

        e.stopPropagation();

        return true;
    });

    //$(document).off('click', '#SearchCondition_FeeTypeName').on('click', '#SearchCondition_FeeTypeName', function () {
    //    var tirgger = this;
    //    var html = $.lsCaseFeeType.getCaseInternalFeeTypeCheckBoxListHtml();
    //    $(".divcaseconditioncasefeetypes").html(html);
    //    $("#hidCaseFeeTypeId").val("SearchCondition_FeeTypeId");
    //    $("#hidCaseFeeTypeName").val($(tirgger).attr("id"));
    //    $("#divCaseFeeTypeCheckBoxList").css({
    //        "position": "absolute",
    //        "left": $(tirgger).parent().position().left + 16,
    //        "top": $(tirgger).parent().position().top + 25,
    //        "z-index": 9999
    //    }).toggle();

    //    return false;
    //});

    //$(document).off('click', '#SearchCondition_CaseTypeName').on('click', '#SearchCondition_CaseTypeName', function () {
    //    var tirgger = this;
    //    var html = $.lsCaseType.getCaseTypeCheckBoxListHtml();
    //    $(".divcaseconditioncasetypes").html(html);
    //    $("#hidCaseTypeId").val("SearchCondition_CaseTypeId");
    //    $("#hidCaseTypeName").val($(tirgger).attr("id"));
    //    $("#divCaseTypeCheckBoxList").css({
    //        "position": "absolute",
    //        "left": $(tirgger).parent().position().left + 16,
    //        "top": $(tirgger).parent().position().top + 25,
    //        "z-index": 9999
    //    }).toggle();

    //    return false;
    //});

    $(document).off('click', '#btnInternalFeeExportAll').on('click', '#btnInternalFeeExportAll', function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(2000);
        investigation.Investigations.Investigation.Clues.ExportAllToExcel();
    });

    $(document).off('click', '#SearchCondition_FeeTypeName').on('click', '#SearchCondition_FeeTypeName', function () {
        var tirgger = this;
        var html = $.lsCaseFeeType.getCaseFeeTypeListTreeHtml();
        $("#divCaseFeeTypeCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left + 9,
            "top": $(tirgger).parent().position().top + 25,
            "z-index": 9999
        }).toggle();

        return false;
    });

    $(document).off('click', '#btnCaseFeeTypeCancel').on('click', '#btnCaseFeeTypeCancel', function () {
        $("#divCaseFeeTypeCheckBoxList").off().hide();
    });

    $(document).off('click', '#btnCaseFeeTypeSelected').on('click', '#btnCaseFeeTypeSelected', function () {

        var treeObj = $.fn.zTree.getZTreeObj("caseFeeTypeTree");
        var nodes = treeObj.getCheckedNodes(true);

        var feeTypeIds = new Array();
        var feeTypeNames = new Array();

        if (nodes.length > 0) {
            $.each(nodes, function (j, node) {
                feeTypeIds.push(node.id);
                feeTypeNames.push(node.name);
            });
            $("#SearchCondition_FeeTypeId").val(feeTypeIds.join(','));
            $("#SearchCondition_FeeTypeName").val(feeTypeNames.join(','));
        }
        else {
            $("#SearchCondition_FeeTypeId").val('');
            $("#SearchCondition_FeeTypeName").val('');
        }

        $("#divCaseFeeTypeCheckBoxList").off().hide();

        //payment.List.PaymentList();
    });

    $(document).off('click', '#SearchCondition_CasePhaseName').on('click', '#SearchCondition_CasePhaseName', function () {

        var tirgger = this;

        //if ($("#SearchCondition_CaseTypeId").val() == "") {
        //    $.showTips("请选择案件类型.", 0, 3);
        //    return false;
        //};
        //var html = $.lsCasePhase.getcasePhaseListTreeHtml($("#SearchCondition_CaseTypeId").val());

        //var html = $.lsCasePhase.getcasePhaseListTreeHtml('110');

        var html = $.lsCasePhase.getAllCasePhaseListTreeHtml();

        $("#divCasePhaseCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left + 9,
            "top": $(tirgger).parent().position().top + 25,
            "z-index": 9999
        }).toggle();

        return false;
    });

    $(document).off('click', '#btnCasePhaseSelected').on('click', '#btnCasePhaseSelected', function () {

        var treeObj = $.fn.zTree.getZTreeObj("casePhaseTree");
        var nodes = treeObj.getCheckedNodes(true);

        var phaseIds = new Array();
        var phaseNames = new Array();

        if (nodes.length > 0) {
            $.each(nodes, function (j, node) {
                phaseIds.push(node.id);
                phaseNames.push(node.name);
            });
            $("#SearchCondition_CasePhaseId").val(phaseIds.join(','));
            $("#SearchCondition_CasePhaseName").val(phaseNames.join(','));
        }
        else {
            $("#SearchCondition_CasePhaseId").val('');
            $("#SearchCondition_CasePhaseName").val('');
        }

        $("#divCasePhaseCheckBoxList").off().hide();

        //payment.List.PaymentList();
    });

    $(document).off('click', '#btnCasePhaseCancel').on('click', '#btnCasePhaseCancel', function () {
        $("#divCasePhaseCheckBoxList").off().hide();
    });
    

});