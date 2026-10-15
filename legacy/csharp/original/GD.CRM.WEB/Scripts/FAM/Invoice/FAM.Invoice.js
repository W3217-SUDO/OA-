var invoice = {
    InvoiceStatus: {
        D: 1,
        P: 2,
        A: 3,
        Pending: 4,
        Invoiced: 5,
        InvoiceCanceled: 6,
        ApplicaionCanceled: 7,
        R: 8,
    },
    ResetSize: function () {
        //if ($("#divContextList").length > 0) {
        //    $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 18);
        //}
    },
    Invoice: {
        ViewContract: function (contractId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FCM/Contract/ContractView?contractId=" + contractId;
            addtabs(url, '查看合同');
            //window.open(url);
        },
        ViewReceviedPayment: function (caseFeeId) {

            var data = {
                caseFeeId: caseFeeId
            };

            var url = AP_ROOT + AP_PAGE_ID + "/FAM/AR/PaymentList";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);

                $('#paymentListModal').modal({ backdrop: 'static', keyboard: false });
                $('#paymentListModal').on('hidden.bs.modal', function () {
                    $("#paymentListModal").remove();
                });

            });
        },
        View: function (invoiceId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/Invoice/InvoiceView?invoiceId=" + invoiceId;
            addtabs(url, '查看发票申请单');
            //window.open(url);
        },
        Edit: function (invoiceId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/Invoice/InvoiceEdit?invoiceId=" + invoiceId;
            addtabs(url, '编辑发票申请单');
            //window.open(url);
        },
        /*申请撤回*/
        ApplicationCancel: function (invoiceId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/Invoice/ApplicationCancel?invoiceId=" + invoiceId;
            addtabs(url, '撤回发票申请单');
            //window.open(url);
        },
        /*发票作废*/
        InvoiceCancel: function (invoiceId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/Invoice/InvoiceCancel?invoiceId=" + invoiceId;
            addtabs(url, '作废发票申请单');
            //window.open(url);
        },
        Process: function (invoiceId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/InvoiceProcess/Process?invoiceId=" + invoiceId;
            addtabs(url, '处理发票申请单');
            //window.open(url);
        },
        Services: {
            Item: {
                Add: function (e) {
                    var tr = $(e).parent().parent().parent().clone().show();
                    //var index = $($(tr).find("td")[0]).html();

                    var index = $($("#tblInvoiceServiceList tbody tr:last").find("td")[0]).html();

                    $($(tr).find("td")[0]).html(parseInt(index) + 1);

                    $(tr).find("#item_ServiceId").val('');
                    $(tr).find("#item_UnitPrice").val(0);
                    $(tr).find("#item_Amount").val(0);
                    $(tr).find("#item_TaxRate").val(0);
                    $(tr).find("#item_TaxAmount").val(0);

                    $("#tblInvoiceServiceList tbody").append(tr);
                    invoice.ResetSize();
                    return tr;
                },
                Clear: function (e) {
                    $(e).parent().parent().parent().find(":input[type='text']").val('');
                    $(e).parent().parent().parent().find(":input[type='hidden']").val('');
                    $(e).parent().parent().parent().find(":input[type='checkbox']").attr("checked", false);
                },
                Remove: function (e) {
                    $(e).parent().parent().parent().remove();
                    invoice.Invoice.TotalAmountSet();
                    invoice.ResetSize();
                },
            },
        },
        Objects: {
            List: function () {
                var data = {
                    contractId: $("#Contract_ContractBasicInfo_ContractId").val()
                };

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/Contract/ContractObjects", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $.each(response.Data, function (i, c) {
                            var caseTypeName = $.caseType.getCaseTypeName(c.CaseTypeId);
                            var caseOfficeFeeTypeName = c.CaseOfficeFeeTypeId == null ? '' : $.caseFeeType.getCaseFeeTypeName(c.CaseTypeId, c.CaseOfficeFeeTypeId);
                            var tr = "<tr>"
                                + "<td>" + (++i) + "</td>"
                                + "<td>" + caseTypeName + "</td>"
                                + "<td>" + c.CaseName + "</td>"
                                + "<td>" + c.CaseNo + "</td>"
                                + "<td>" + caseOfficeFeeTypeName + "</td>"
                                + "<td>" + (c.CaseOfficeFeeAmount == null ? 0 : c.CaseOfficeFeeAmount) + "</td>"
                                + "<td><input class='form-control'  id='item_CaseOfficeFeeInvoiceAmount' CaseOfficeFeeId=" + c.CaseOfficeFeeId + " onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\" onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" type='text' value='0'>"
                                + "<td>" + (c.CaseNonOfficeFeeAmount == null ? 0 : c.CaseNonOfficeFeeAmount) + "</td>"
                                + "<td><input class='form-control'  id='item_CaseNonOfficeFeeInvoiceAmount' CaseNonOfficeFeeId=" + c.CaseNonOfficeFeeId + " onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\" onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" type='text' value='0'>"
                                + "<td>" + (c.CaseCommissionFeeAmount == null ? 0 : c.CaseCommissionFeeAmount) + "</td>"
                                + "<td><input class='form-control'  id='item_CaseCommissionFeeInvoiceAmount' CaseCommissionFeeId=" + c.CaseCommissionFeeId + " onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\" onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" type='text' value='0'>"
                                + "<td><input id='item_InvoiceApply' name='item_InvoiceApply'  type='checkbox' caseid=" + c.CaseId + " caseno=" + c.CaseNo + " ></td>"
                                + "</tr>";

                            $('#tblInvoiceObjectList>tbody>tr:last').after(tr);
                        });
                        invoice.ResetSize();
                        $.closeLoading();
                    }
                }, true);
            },

            Item: {
                Apply: function (e) {
                    if ($(e).attr("caseFeeTypeId") == "11020050" || $(e).attr("caseFeeTypeId") == "11020065") {
                        $("#Invoice_InvoiceBasic_InvoicePT").val(2);
                    }
                    else if ($(e).attr("caseFeeTypeId") == "11020010"
                        || $(e).attr("caseFeeTypeId") == "11020020"
                        || $(e).attr("caseFeeTypeId") == "11020030"
                        || $(e).attr("caseFeeTypeId") == "11020040") {
                        $("#Invoice_InvoiceBasic_InvoicePT").val(1);
                    }
                    else {
                        $("#Invoice_InvoiceBasic_InvoicePT").val(-1);
                    }
                }
            }
        },

        TotalAmountSet: function () {
            var totalAmount = 0;
            $("input[name='item_CaseFeeInvoiceAmount']").each(
                function () {
                    if ($(this).parent().parent().find("#item_InvoiceApply").prop("checked"))
                    {
                        if ($(this).val() == '') {
                            $(this).val(0);
                        }
                        totalAmount += parseFloat($(this).val());
                    }
                }
            );

            $("#Invoice_InvoiceBasic_InvoiceAmount").html(totalAmount);

            if ($("input[name='item_UnitPrice']").length > 0) {
                $($("input[name='item_UnitPrice']")[0]).val(totalAmount);
            }
            if ($("input[name='item_Amount']").length > 0 ) {
                var quantity = $($("input[name='item_Quantity']")[0]).val();
                if (quantity == '') {
                    quantity = 1;
                }
                $($("input[name='item_Amount']")[0]).val(totalAmount * parseFloat(quantity));
            }

            invoice.Invoice.ServiceTotalAmountSet();
        },

        ServiceTotalAmountSet: function () {
            var totalAmount = 0;
            $("input[name='item_Amount']").each(
                function () {
                    if ($(this).val() == '') {
                        $(this).val(0);
                    }
                    totalAmount += parseFloat($(this).val());
                }
            );
            var invoiceTotalAmount = $("#Invoice_InvoiceBasic_InvoiceAmount").html() == '' ? 0 : parseFloat($("#Invoice_InvoiceBasic_InvoiceAmount").html());
            totalAmount = Math.round(totalAmount * 100) / 100;
            invoiceTotalAmount = Math.round(invoiceTotalAmount * 100) / 100;
            $("#spanServiceTotalAmount").html(Math.round(totalAmount * 100) / 100);
        },

        ServiceAmountSet: function (e) {
            $(e).attr("haschanged", 'T');
            var unitPrice = $(e).parent().parent().find("#item_UnitPrice").val();
            if (unitPrice == '') {
                unitPrice = 0;
            }
            var quantity = $(e).parent().parent().find("#item_Quantity").val();
            if (quantity == '') {
                quantity = 1;
                $(e).parent().parent().find("#item_Quantity").val(1);
            }
            $(e).parent().parent().find("#item_Amount").val(parseFloat(unitPrice) * parseFloat(quantity));
            invoice.Invoice.ServiceTotalAmountSet();
        },

        /*开票申请*/
        Application: {
            CreateUpdate: function (isSubmit) {
                try {

                    var dataIsNOk = false;

                    //if ($("#Invoice_InvoiceBasic_InvoicePT").val() == '-1')
                    //{
                    //    $.showModalMessageBox("请输入开票平台.");
                    //    $("#Invoice_InvoiceBasic_InvoicePT").focus();
                    //    return false;
                    //}

                    if ($("#Invoice_InvoiceBasic_InvoiceName").val() == '') {
                        $.showModalMessageBox("请输入发票抬头.");
                        $("#Invoice_InvoiceBasic_InvoiceName").focus();
                        return false;
                    }

                    if ($("#Invoice_InvoiceBasic_CustomerCompanyCode").val() == '') {
                        $.showModalMessageBox("请输入客户纳税人识别码.");
                        $("#Invoice_InvoiceBasic_CustomerCompanyCode").focus();
                        return false;
                    }

                    if ($("#Invoice_InvoiceBasic_InvoiceType").val() == '2')
                    {
                        if ($("#Invoice_InvoiceBasic_CustomerPhone").val() == "") {
                            $.showModalMessageBox("请输入客户电话.");
                            $("#Invoice_InvoiceBasic_CustomerPhone").focus();
                            return false;
                        }

                        if ($("#Invoice_InvoiceBasic_CustomerBankAccount").val() == "") {
                            $.showModalMessageBox("请输入客户开户账号.");
                            $("#Invoice_InvoiceBasic_CustomerBankAccount").focus();
                            return false;
                        }

                        if ($("#Invoice_InvoiceBasic_CustomerBankName").val() == "") {
                            $.showModalMessageBox("请输入客户开户银行.");
                            $("#Invoice_InvoiceBasic_CustomerBankName").focus();
                            return false;
                        }

                        if ($("#Invoice_InvoiceBasic_CustomerBusinessAddress").val() == "") {
                            $.showModalMessageBox("请输入客户地址.");
                            $("#Invoice_InvoiceBasic_CustomerBusinessAddress").focus();
                            return false;
                        }
                    }

                    var items = $.checkbox.vals("item_InvoiceApply");
                    if (items.length == 0) {
                        $.showModalMessageBox("请选择开票明细.");
                        return false;
                    }

                    var data = {};

                    data["Invoice.InvoiceBasic.InvoiceId"] = $("#Invoice_InvoiceBasic_InvoiceId").val();
                    data["Invoice.InvoiceBasic.InvoiceName"] = $("#Invoice_InvoiceBasic_InvoiceName").val();
                    data["Invoice.InvoiceBasic.InvoiceApplicationNo"] = $("#Invoice_InvoiceBasic_InvoiceApplicationNo").val();
                    data["Invoice.InvoiceBasic.InvoiceApplicationDate"] = $("#Invoice_InvoiceBasic_InvoiceApplicationDate").val();
                    //data["Invoice.InvoiceBasic.ContractId"] = $("#Contract_ContractBasicInfo_ContractId").val();
                    //data["Invoice.InvoiceBasic.ContractNo"] = $("#Contract_ContractBasicInfo_ContractNo").val();
                    data["Invoice.InvoiceBasic.CustomerId"] = $("#Customer_CustomerBasic_CustomerId").val();
                    data["Invoice.InvoiceBasic.CustomerNo"] = $("#Customer_CustomerBasic_CustomerNo").val();
                    data["Invoice.InvoiceBasic.CustomerName"] = $("#Customer_CustomerBasic_CustomerName").val();
                    data["Invoice.InvoiceBasic.InvoiceOverAmount"] = $("#Invoice_InvoiceBasic_InvoiceOverAmount").val();
                    data["Invoice.InvoiceBasic.InvoicedAmount"] = $("#Invoice_InvoiceBasic_InvoicedAmount").val();
                    data["Invoice.InvoiceBasic.Remark"] = $("#Invoice_InvoiceBasic_Remark").val();

                    data["Invoice.InvoiceBasic.CustomerCompanyCode"] = $("#Invoice_InvoiceBasic_CustomerCompanyCode").val();
                    data["Invoice.InvoiceBasic.CustomerPhone"] = $("#Invoice_InvoiceBasic_CustomerPhone").val();
                    data["Invoice.InvoiceBasic.CustomerBankAccount"] = $("#Invoice_InvoiceBasic_CustomerBankAccount").val();
                    data["Invoice.InvoiceBasic.CustomerBankName"] = $("#Invoice_InvoiceBasic_CustomerBankName").val();
                    data["Invoice.InvoiceBasic.CustomerBusinessAddress"] = $("#Invoice_InvoiceBasic_CustomerBusinessAddress").val();

                    data["Invoice.InvoiceBasic.InvoiceType"] = $("#Invoice_InvoiceBasic_InvoiceType").val();
                    data["Invoice.InvoiceBasic.GroupId"] = $("#Invoice_InvoiceBasic_GroupId").val();

                    var serviceTotalAmount = 0;
                    $("#tblInvoiceServiceList>tbody>tr").each(function (j, e) {
                        if ($(e).css("display") != 'none') {

                            if ($(e).find("#item_ServiceName").val() == '') {
                                dataIsNOk = true;
                                $.showModalMessageBox("第" + (j + 1) + "行,请输入服务名称.");
                                return false;
                            }

                            serviceTotalAmount += $(e).find("#item_Amount").val() == '' ? 0 : parseFloat($(e).find("#item_Amount").val());

                            data["Invoice.InvoiceServices[" + j + "].ServiceId"] = $(e).find("#item_ServiceId").val();
                            data["Invoice.InvoiceServices[" + j + "].ServiceName"] = $(e).find("#item_ServiceName").val();
                            data["Invoice.InvoiceServices[" + j + "].ServiceTypeId"] = $(e).find("#item_ServiceTypeId").val();
                            data["Invoice.InvoiceServices[" + j + "].Quantity"] = $(e).find("#item_Quantity").val();
                            data["Invoice.InvoiceServices[" + j + "].UnitPrice"] = $(e).find("#item_UnitPrice").val();
                            data["Invoice.InvoiceServices[" + j + "].Amount"] = $(e).find("#item_Amount").val();
                            data["Invoice.InvoiceServices[" + j + "].TaxRate"] = $(e).find("#item_TaxRate").val();
                            data["Invoice.InvoiceServices[" + j + "].TaxAmount"] = $(e).find("#item_TaxAmount").val();
                        }
                    });

                    var invoicedTotalAmount = 0;
                    var i = 0;
                    $("#tblInvoiceObjectList>tbody>tr").each(function (j, e) {
                        if ($(e).css("display") != 'none' && $(e).find("#item_InvoiceApply").prop('checked') == true) {

                            if (($(e).find("#item_CaseFeeInvoiceAmount").val() == ''
                                || parseFloat($(e).find("#item_CaseFeeInvoiceAmount").val()) == 0) ) {
                            }

                            else {
                                data["Invoice.InvoiceObjects[" + i + "].CaseFeeId"] = $(e).find("#item_CaseFeeInvoiceAmount").attr("CaseFeeId");
                                data["Invoice.InvoiceObjects[" + i + "].CaseFeeSeqId"] = $(e).find("#item_CaseFeeInvoiceAmount").attr("CaseFeeSeqId");
                                data["Invoice.InvoiceObjects[" + i + "].CaseFeeInvoiceAmount"] = $(e).find("#item_CaseFeeInvoiceAmount").val();
                                invoicedTotalAmount += $(e).find("#item_CaseFeeInvoiceAmount").val() == '' ? 0 : parseFloat($(e).find("#item_CaseFeeInvoiceAmount").val());
                                data["Invoice.InvoiceObjects[" + i + "].CaseId"] = $(e).find("#item_InvoiceApply").attr("caseid");
                                data["Invoice.InvoiceObjects[" + i + "].CaseNo"] = $(e).find("#item_InvoiceApply").attr("caseno");
                                data["Invoice.InvoiceObjects[" + i + "].ContractNo"] = $(e).find("#item_InvoiceApply").attr("contractno");
                                data["Invoice.InvoiceObjects[" + i + "].RefContractNo"] = $(e).find("#item_InvoiceApply").attr("refcontractno");
                                data["Invoice.InvoiceObjects[" + i + "].CustomerNo"] = $(e).find("#item_InvoiceApply").attr("customerno");
 
                                i++;
                            }
                        }
                    });
                    if (dataIsNOk) return false;
                    if (serviceTotalAmount == 0) {
                        $.showModalMessageBox("实际开票金额为零.");
                        return false;
                    }
                    //if (serviceTotalAmount < invoicedTotalAmount) {
                    //    $.showModalMessageBox("实际开票金额不允许小于所选案件开票金额.");
                    //    return false;
                    //}
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Invoice/InvoiceCreateUpdate", data, function (response) {
                        if (response.IsSuccess) {
                            $.showModalConfirmDialog("提交成功.", 'invoice.Invoice.Application.CreateUpdateCallBack', true, true);
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {
                }
            },
            CreateUpdateCallBack: function (isSubmit) {
                debugger
                if ($("#Invoice_InvoiceBasic_GroupId").val() == $.lsGroupId.Lawfirm) {
                    window.location = AP_ROOT + "5001006001/FAM/Invoice/InvoiceList";
                } else {
                    window.location = AP_ROOT + "50001006001/FAM/Invoice/InvoiceList";
                }
            },
            Canceled: function () {
                try {
                    var data = {};
                    data["Invoice.InvoiceBasic.InvoiceId"] = $("#Invoice_InvoiceBasic_InvoiceId").val();
                    data["Invoice.InvoiceBasic.ApplicationCancelCause"] = $("#Invoice_InvoiceBasic_ApplicationCancelCause").val();

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Invoice/ApplicationCanceled", data, function (response) {
                        if (response.IsSuccess) {
                            $.showModalConfirmDialog(response.Message, 'invoice.Invoice.Application.CanceledUpdateCallBack', true, true);

                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {

                }
            },
            CanceledUpdateCallBack: function (isSubmit) {

                if ($("#Invoice_InvoiceBasic_GroupId").val() == $.lsGroupId.Lawfirm) {
                    window.location = AP_ROOT + "5001006001/FAM/Invoice/InvoiceList";
                } else {
                    window.location = AP_ROOT + "50001006001/FAM/Invoice/InvoiceList";
                }
            },
        },

        /*开票处理*/
        Invoiced: {
            CreateUpdate: function (isSubmit) {
                try {

                    if ($("#Invoice_InvoiceBasic_InvoiceNo").val() == '') {
                        $.showModalMessageBox("请输入发票号码.");
                        $("#Invoice_InvoiceBasic_InvoiceNo").focus();
                        return false;
                    }
                    var data = {};
                    data["Invoice.InvoiceBasic.InvoiceId"] = $("#Invoice_InvoiceBasic_InvoiceId").val();
                    data["Invoice.InvoiceBasic.InvoiceHolder"] = $("#Invoice_InvoiceBasic_InvoiceHolder").val();
                    data["Invoice.InvoiceBasic.InvoicedOpinion"] = $("#Invoice_InvoiceBasic_InvoicedOpinion").val();
                    data["Invoice.InvoiceBasic.Remark"] = $("#Invoice_InvoiceBasic_Remark").val();
                    data["Invoice.InvoiceBasic.InvoiceName"] = $("#Invoice_InvoiceBasic_InvoiceName").val();
                    data["Invoice.InvoiceBasic.InvoiceNo"] = $("#Invoice_InvoiceBasic_InvoiceNo").val();
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InvoiceProcess/Invoiced", data, function (response) {
                        if (response.IsSuccess) {
                            $.showModalConfirmDialog(response.Message, 'invoice.Invoice.Invoiced.CreateUpdateCallBack', isSubmit, true);

                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {

                }
            },
            CreateUpdateCallBack: function (isSubmit) {
                if ($("#Invoice_InvoiceBasic_GroupId").val() == $.lsGroupId.Lawfirm) {
                    window.location = AP_ROOT + "REDACTED_ARCHIVE_ONLY";
                }
                else {
                    window.location = AP_ROOT + "REDACTED_ARCHIVE_ONLY";
                }
            },

            Rejected: function () {
                try {
                    if ($("#Invoice_InvoiceBasic_InvoicedOpinion").val() == '') {
                        $.showModalMessageBox("请输入驳回原因.");
                        $("#Invoice_InvoiceBasic_InvoicedOpinion").focus();
                        return false;
                    }
                    var data = {};
                    data["Invoice.InvoiceBasic.InvoiceId"] = $("#Invoice_InvoiceBasic_InvoiceId").val();
                    data["Invoice.InvoiceBasic.InvoicedOpinion"] = $("#Invoice_InvoiceBasic_InvoicedOpinion").val();
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InvoiceProcess/Rejected", data, function (response) {
                        if (response.IsSuccess) {
                            $.showModalConfirmDialog(response.Message, 'invoice.Invoice.Invoiced.RejectedUpdateCallBack', true, true);

                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                } catch (e) {

                }
            },
            RejectedUpdateCallBack: function (isSubmit) {
                if ($("#Invoice_InvoiceBasic_GroupId").val() == $.lsGroupId.Lawfirm) {
                    window.location = AP_ROOT + "REDACTED_ARCHIVE_ONLY";
                }
                else {
                    window.location = AP_ROOT + "REDACTED_ARCHIVE_ONLY";
                }
            },

            Canceled: function () {
                try {

                    if ($("#Invoice_InvoiceBasic_InvoiceCancelCause").val() == '') {
                        $.showModalMessageBox("请输入作废原因.");
                        $("#Invoice_InvoiceBasic_InvoiceCancelCause").focus();
                        return false;
                    }
                    var data = {};
                    data["Invoice.InvoiceBasic.InvoiceId"] = $("#Invoice_InvoiceBasic_InvoiceId").val();
                    data["Invoice.InvoiceBasic.InvoiceCancelCause"] = $("#Invoice_InvoiceBasic_InvoiceCancelCause").val();
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Invoice/InvoiceCanceled", data, function (response) {
                        if (response.IsSuccess) {
                            $.showModalConfirmDialog(response.Message, 'invoice.Invoice.Invoiced.CanceledUpdateCallBack', true, true);

                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {

                }
            },
            CanceledUpdateCallBack: function (isSubmit) {
               if ($("#Invoice_InvoiceBasic_GroupId").val() == $.lsGroupId.Lawfirm) {
                    window.location = AP_ROOT + "REDACTED_ARCHIVE_ONLY";
                }
                else {
                    window.location = AP_ROOT + "REDACTED_ARCHIVE_ONLY";
                }
            },
        },

        /*发票号修改*/
        InvoiceNo: {
            Open: function (invoiceId) {
                var data = {
                    invoiceId: invoiceId
                };

                var url = AP_ROOT + AP_PAGE_ID + "/FAM/Invoice/InvoiceNoChange";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);

                    $('#invoiceNoChangeModal').modal({ backdrop: 'static', keyboard: false });
                    $('#invoiceNoChangeModal').on('hidden.bs.modal', function () {
                        $("#invoiceNoChangeModal").remove();
                    });

                });
            },
            Update: function (isSubmit) {
                try {

                    if ($("#Invoice_InvoiceBasic_NewInvoiceNo").val() == '') {
                        $.showModalMessageBox("请输入新发票号码.");
                        $("#Invoice_InvoiceBasic_NewInvoiceNo").focus();
                        return false;
                    }

                    var data =
                    {
                        invoiceId: $("#Invoice_InvoiceBasic_InvoiceId").val(),
                        invoiceNo: $("#Invoice_InvoiceBasic_NewInvoiceNo").val(),
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Invoice/InvoiceNoUpdate", data, function (response) {
                        if (response.IsSuccess) {
                            $.showModalMessageBox("修改成功.");
                            invoice.List.InvoicedList();
                            invoice.Invoice.InvoiceNo.Close();
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {

                }
            },
            UpdateCallBack: function (isSubmit) {
                window.location = AP_ROOT + "REDACTED_ARCHIVE_ONLY";
            },
            /*关闭发票号修改*/
            Close: function () {
                $('#invoiceNoChangeModal').modal('hide');
            },
        },
        /*发票号修改*/
        InvoiceDate: {
            Open: function (invoiceId) {
                var data = {
                    invoiceId: invoiceId
                };

                var url = AP_ROOT + AP_PAGE_ID + "/FAM/Invoice/InvoiceDateChange";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);

                    $('#invoiceDateChangeModal').modal({ backdrop: 'static', keyboard: false });
                    $('#invoiceDateChangeModal').on('hidden.bs.modal', function () {
                        $("#invoiceDateChangeModal").remove();
                    });

                });
            },
            Update: function (isSubmit) {
                try {

                    if ($("#Invoice_InvoiceBasic_InvoiceApplicationDate").val() == '') {
                        $.showModalMessageBox("请输入发票申请日期.");
                        $("#Invoice_InvoiceBasic_InvoiceApplicationDate").focus();
                        return false;
                    }

                    if ($("#Invoice_InvoiceBasic_InvoiceDate").val() == '') {
                        $.showModalMessageBox("请输入发票开票日期.");
                        $("#Invoice_InvoiceBasic_InvoiceDate").focus();
                        return false;
                    }

                    var data =
                    {
                        invoiceId: $("#Invoice_InvoiceBasic_InvoiceId").val(),
                        invoiceApplicationDate: $("#Invoice_InvoiceBasic_InvoiceApplicationDate").val(),
                        invoiceDate: $("#Invoice_InvoiceBasic_InvoiceDate").val(),
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Invoice/InvoiceDateUpdate", data, function (response) {
                        if (response.IsSuccess) {
                            $.showModalMessageBox("修改成功.");
                            invoice.List.InvoicedList();
                            invoice.Invoice.InvoiceDate.Close();
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {

                }
            },
            UpdateCallBack: function (isSubmit) {
                window.location = AP_ROOT + "REDACTED_ARCHIVE_ONLY";
            },
            /*关闭发票号修改*/
            Close: function () {
                $('#invoiceDateChangeModal').modal('hide');
            },
        },

    },
    List: {
        BindMenu: function () {

            $('#invoicegridSection').contextMenu('invoiceMenu', {
                menuStyle: {
                    width: '152px'
                },
                itemStyle: {
                    width: '150px'
                },
                bindings: {
                    'view': function (t, e) {
                        var invoiceId = $(e).find("span").text();
                        if (invoiceId == '') {
                            $.showModalMessageBox("请选择请票单号.");
                            return false;
                        }

                        invoice.Invoice.View(invoiceId);
                    },
                    'edit': function (t, e) {
                        var invoiceId = $(e).find("span").text();
                        if (invoiceId == '') {
                            $.showModalMessageBox("请选择请票单号.");
                            return false;
                        }

                        invoice.Invoice.Edit(invoiceId);

                        return true;
                    },

                    'cancel': function (t, e) {
                        var invoiceId = $(e).find("span").text();
                        if (invoiceId == '') {
                            $.showModalMessageBox("请选择请票单号.");
                            return false;
                        }

                        invoice.Invoice.ApplicationCancel(invoiceId);

                        return true;
                    },

                },
                onContextMenu: function (e) {
                    return true;
                },
                onShowMenu: function (e, menu) {
                    if ($(e.target).parents("tr").find(".invoiceId").hasClass("invoiceId")) {
                        var invoiceId = $(e.target).parents("tr").find(".invoiceId").text();
                        var invoiceStatus = $(e.target).parents("tr").find(".invoiceStatus").text();

                        if (invoiceStatus == invoice.InvoiceStatus.InvoiceCanceled
                            || invoiceStatus == invoice.InvoiceStatus.ApplicaionCanceled
                            || invoiceStatus == invoice.InvoiceStatus.Invoiced) {

                            $('#view', menu).append("<span style='display:none'>" + invoiceId + "</span>");
                            $('#edit,#cancel', menu).remove();
                        }
                        else {
                            $('#view', menu).append("<span style='display:none'>" + invoiceId + "</span>");
                            $('#edit', menu).append("<span style='display:none'>" + invoiceId + "</span>");
                            $('#cancel', menu).append("<span style='display:none'>" + invoiceId + "</span>");
                        }

                    } else {
                        $('#view,#edit,#cancel', menu).remove();
                    }
                    return menu;
                }
            });
        },
        BindInvoicedMenu: function () {

            $('#invoicedgridsection').contextMenu('invoicedMenu', {
                menuStyle: {
                    width: '152px'
                },

                itemStyle: {
                    width: '150px'
                },

                bindings: {
                    'view': function (t, e) {
                        var invoiceId = $(e).find("span").text();
                        if (invoiceId == '') {
                            $.showModalMessageBox("请选择请票单号.");
                            return false;
                        }

                        invoice.Invoice.View(invoiceId);
                    },
                    'cancel': function (t, e) {
                        var invoiceId = $(e).find("span").text();
                        if (invoiceId == '') {
                            $.showModalMessageBox("请选择请票单号.");
                            return false;
                        }

                        invoice.Invoice.InvoiceCancel(invoiceId);

                        return true;
                    },

                    'invoiceno': function (t, e) {
                        var invoiceId = $(e).find("span").text();
                        if (invoiceId == '') {
                            $.showModalMessageBox("请选择请票单号.");
                            return false;
                        }

                        invoice.Invoice.InvoiceNo.Open(invoiceId);

                        return true;
                    },

                    'invoicedatechange': function (t, e) {
                        var invoiceId = $(e).find("span").text();
                        if (invoiceId == '') {
                            $.showModalMessageBox("请选择请票单号.");
                            return false;
                        }

                        invoice.Invoice.InvoiceDate.Open(invoiceId);

                        return true;
                    },


                },
                onContextMenu: function (e) {
                    return true;
                },
                onShowMenu: function (e, menu) {
                    if ($(e.target).parents("tr").find(".invoiceId").hasClass("invoiceId")) {
                        var invoiceId = $(e.target).parents("tr").find(".invoiceId").text();
                        var invoiceStatus = $(e.target).parents("tr").find(".invoiceStatus").text();

                        if (invoiceStatus == invoice.InvoiceStatus.InvoiceCanceled || invoiceStatus == invoice.InvoiceStatus.ApplicaionCanceled) {
                            $('#view', menu).append("<span style='display:none'>" + invoiceId + "</span>");
                            $('#cancel,#invoiceno', menu).remove();
                        }
                        else {
                            $('#view', menu).append("<span style='display:none'>" + invoiceId + "</span>");
                            $('#cancel', menu).append("<span style='display:none'>" + invoiceId + "</span>");
                            $('#invoiceno', menu).append("<span style='display:none'>" + invoiceId + "</span>");
                            $('#invoicedatechange', menu).append("<span style='display:none'>" + invoiceId + "</span>");
                        }

                    } else {
                        $('#view,#cancel,#invoiceno,#invoicedatechange', menu).remove();
                    }
                    return menu;
                }
            });
        },
        InvoiceList: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Invoice/InvoiceList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblInvoiceList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.InvoiceList, function (i, c) {

                            if (c.InvoiceBasic.InvoiceStatus == invoice.InvoiceStatus.InvoiceCanceled
                                || c.InvoiceBasic.InvoiceStatus == invoice.InvoiceStatus.ApplicaionCanceled) {
                                $("tbody", "#tblInvoiceList").addRow(
                                   "<input type='checkbox' id='chkInvoiceId' name='chkInvoiceId'  value=" + c.InvoiceBasic.InvoiceId + ">",
                                   "<a style='color: #039' href='javascript:void(0);' ><span>查看</span></a>",
                                   "<span class='invoiceId' style='display:none'>" + c.InvoiceBasic.InvoiceId + "</span>"
                                    + "<span class='invoiceStatus' style='display:none'>" + c.InvoiceBasic.InvoiceStatus + "</span>"
                                    + "<a style='color: #039' href='javascript:void(0);' ><span style='text-decoration:line-through;'>" + c.InvoiceBasic.InvoiceApplicationNo + "</span></a>",
                                    "<span style='text-decoration:line-through;'>" + c.InvoiceBasic.CustomerName + "</span>",
                                    "<span style='text-decoration:line-through;'>" + c.InvoiceBasic.InvoiceAmount + "</span>",
                                    "<span style='text-decoration:line-through;'>" + c.InvoiceBasic.InvoiceOverAmount + "</span>",
                                    "<span style='text-decoration:line-through;'>" + c.InvoiceBasic.InvoiceNo + "</span>",
                                    "<span style='text-decoration:line-through;'>" + c.InvoiceBasic.InvoiceHolderName + "</span>",
                                    "<span style='text-decoration:line-through;'>" + (c.InvoiceBasic.InvoiceDate == null ? '' : getDate(convertJsonDateToJSDate(c.InvoiceBasic.InvoiceDate))) + "</span>",
                                    "<span style='text-decoration:line-through;'>" + c.InvoiceBasic.InvoiceStatusName + "</span>",
                                    "<span style='text-decoration:line-through;'>" + (c.InvoiceBasic.InvoiceOverAmount > 0 ? '高开' + c.InvoiceBasic.InvoiceOverAmount + "元" : c.InvoiceBasic.Remark) + "</span>"
                                );
                            }
                            else if (c.InvoiceBasic.InvoiceStatus == invoice.InvoiceStatus.Invoiced) {
                                $("tbody", "#tblInvoiceList").addRow(
                                   "<input type='checkbox' id='chkInvoiceId' name='chkInvoiceId'  value=" + c.InvoiceBasic.InvoiceId + ">",
                                    "<a style='color: #039' href='javascript:invoice.Invoice.View(invoiceId)' ><span>查看</span></a>",
                                   "<span class='invoiceId' style='display:none'>" + c.InvoiceBasic.InvoiceId + "</span>"
                                    + "<span class='invoiceStatus' style='display:none'>" + c.InvoiceBasic.InvoiceStatus + "</span>"
                                    + "<a style='color: #039' href='javascript:void(0);' ><span>" + c.InvoiceBasic.InvoiceApplicationNo + "</span></a>",
                                    c.InvoiceBasic.CustomerName,
                                    c.InvoiceBasic.InvoiceAmount,
                                    "<span style='color:red'>" + c.InvoiceBasic.InvoiceOverAmount + "</span>",
                                    c.InvoiceBasic.InvoiceNo,
                                    c.InvoiceBasic.InvoiceHolderName,
                                    c.InvoiceBasic.InvoiceDate == null ? '' : getDate(convertJsonDateToJSDate(c.InvoiceBasic.InvoiceDate)),
                                    c.InvoiceBasic.InvoiceStatusName,
                                    (c.InvoiceBasic.InvoiceOverAmount > 0 ? '高开' + c.InvoiceBasic.InvoiceOverAmount + "元" : c.InvoiceBasic.Remark)
                                );
                            }
                            else {
                                $("tbody", "#tblInvoiceList").addRow(
                                   "<input type='checkbox' id='chkInvoiceId' name='chkInvoiceId'  value=" + c.InvoiceBasic.InvoiceId + ">",
                                  "<a style='color: #039' href='javascript:invoice.Invoice.View(" + c.InvoiceBasic.InvoiceId + ")' ><span>查看</span></a>  "
                                   + "<a style='color: #039' href='javascript:invoice.Invoice.InvoiceCancel(" + c.InvoiceBasic.InvoiceId + ")' ><span>撤回</span></a>", "<span class='invoiceId' style='display:none'>" + c.InvoiceBasic.InvoiceId + "</span>"
                                    + "<span class='invoiceStatus' style='display:none'>" + c.InvoiceBasic.InvoiceStatus + "</span>"
                                  
                                    + "<a style='color: #039' href='javascript:void(0);' ><span>" + c.InvoiceBasic.InvoiceApplicationNo + "</span></a>",
                                    c.InvoiceBasic.CustomerName,
                                    c.InvoiceBasic.InvoiceAmount,
                                    "<span style='color:red'>" + c.InvoiceBasic.InvoiceOverAmount + "</span>",
                                    c.InvoiceBasic.InvoiceNo,
                                    c.InvoiceBasic.InvoiceHolderName,
                                    c.InvoiceBasic.InvoiceDate == null ? '' : getDate(convertJsonDateToJSDate(c.InvoiceBasic.InvoiceDate)),
                                    c.InvoiceBasic.InvoiceStatusName,
                                    (c.InvoiceBasic.InvoiceOverAmount > 0 ? '高开' + c.InvoiceBasic.InvoiceOverAmount + "元" : c.InvoiceBasic.Remark)
                                );
                            }
                        });

                        $("tfoot", "#tblInvoiceList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.invoiceList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: invoice.List.InvoiceList,
                            callBackArgs: null
                        });

                        invoice.List.BindMenu();

                    } else {
                        $("tfoot", "#tblInvoiceList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        PendingList: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Invoice/PendingList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblInvoiceList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.InvoiceList, function (i, c) {

                            $("tbody", "#tblInvoiceList").addRow(
                                "<input type='checkbox' id='chkInvoiceId' name='chkInvoiceId'  value=" + c.InvoiceBasic.InvoiceId + ">",
                                "<a href='javascript:void(0)' onclick='javascript:invoice.Invoice.Process(\"" + c.InvoiceBasic.InvoiceId + "\")'>开票</a> &nbsp; ",
                                "<a href='javascript:void(0)' onclick='javascript:invoice.Invoice.Process(\"" + c.InvoiceBasic.InvoiceId + "\")'>" + c.InvoiceBasic.InvoiceApplicationNo + "</a> &nbsp; ",
                                c.InvoiceBasic.InvoiceApplicantName,
                                c.InvoiceBasic.CustomerName,
                                c.InvoiceBasic.InvoiceAmount,
                                "<span style='color:red'>" + c.InvoiceBasic.InvoiceOverAmount + "</span>",
                                c.InvoiceBasic.InvoiceName,
                                c.InvoiceBasic.Remark
                            );
                        });

                        $("tfoot", "#tblInvoiceList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.invoiceList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: invoice.List.PendingList,
                            callBackArgs: null
                        });


                    } else {
                        $("tfoot", "#tblInvoiceList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        InvoicedList: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Invoice/InvoicedList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblInvoiceList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.InvoiceList, function (i, c) {

                            if (c.InvoiceBasic.InvoiceStatus == invoice.InvoiceStatus.InvoiceCanceled || c.InvoiceBasic.InvoiceStatus == invoice.InvoiceStatus.ApplicaionCanceled) {
                                $("tbody", "#tblInvoiceList").addRow(
                                   "<input type='checkbox' id='chkInvoiceId' name='chkInvoiceId'  value=" + c.InvoiceBasic.InvoiceId + ">",
                                   "<a style='color: #039' href='javascript:invoice.Invoice.View(" + c.InvoiceBasic.InvoiceId + ")' ><span>查看</span></a>  " ,
                                   "<span class='invoiceId' style='display:none'>" + c.InvoiceBasic.InvoiceId + "</span>"
                                    + "<span class='invoiceStatus' style='display:none'>" + c.InvoiceBasic.InvoiceStatus + "</span>"
                                    + "<a style='color: #039' href='javascript:void(0);' ><span style='text-decoration:line-through;'>" + c.InvoiceBasic.InvoiceApplicationNo + "</span></a>",
                                    "<span style='text-decoration:line-through;'>" + c.InvoiceBasic.CustomerName + "</span>",
                                    "<span style='text-decoration:line-through;'>" + c.InvoiceBasic.InvoiceAmount + "</span>",
                                    "<span style='text-decoration:line-through;'>" + c.InvoiceBasic.InvoiceOverAmount + "</span>",
                                     "<span style='text-decoration:line-through;'>" + c.InvoiceBasic.InvoiceName + "</span>",
                                    "<span style='text-decoration:line-through;'>" + c.InvoiceBasic.InvoiceNo + "</span>",
                                     "<span style='text-decoration:line-through;'>" +c.InvoiceBasic.InvoiceApplicantName + "</span>",
                                    "<span style='text-decoration:line-through;'>" + c.InvoiceBasic.InvoiceHolderName + "</span>",
                                    "<span style='text-decoration:line-through;'>" + (c.InvoiceBasic.InvoiceDate == null ? '' : getDate(convertJsonDateToJSDate(c.InvoiceBasic.InvoiceDate))) + "</span>",
                                    "<span style='text-decoration:line-through;'>" + c.InvoiceBasic.InvoiceStatusName + "</span>"
                                );
                            } else {
                                $("tbody", "#tblInvoiceList").addRow(
                                   "<input type='checkbox' id='chkInvoiceId' name='chkInvoiceId'  value=" + c.InvoiceBasic.InvoiceId + ">",
                                   "<a style='color: #039' href='javascript:invoice.Invoice.View(" + c.InvoiceBasic.InvoiceId + ")' ><span>查看</span></a>  "
                                 + "<a style='color: #039' href='javascript:invoice.Invoice.InvoiceCancel(" + c.InvoiceBasic.InvoiceId + ")' ><span>作废</span></a>  "
                                 + "<a style='color: #039' href='javascript:invoice.Invoice.InvoiceNo.Open(" + c.InvoiceBasic.InvoiceId + ")' ><span>修改发票号</span></a>  "
                                 + "<a style='color: #039' href='javascript:invoice.Invoice.InvoiceDate.Open(" + c.InvoiceBasic.InvoiceId + ")' ><span>修改发票日期</span></a>  ",
                                   "<span class='invoiceId' style='display:none'>" + c.InvoiceBasic.InvoiceId + "</span>"
                                    + "<span class='invoiceStatus' style='display:none'>" + c.InvoiceBasic.InvoiceStatus + "</span>"
                                    + "<a style='color: #039' href='javascript:void(0);' ><span>" + c.InvoiceBasic.InvoiceApplicationNo + "</span></a>",
                                    c.InvoiceBasic.CustomerName,
                                    c.InvoiceBasic.InvoiceAmount,
                                    "<span style='color:red'>" + c.InvoiceBasic.InvoiceOverAmount + "</span>",
                                    c.InvoiceBasic.InvoiceName,
                                    c.InvoiceBasic.InvoiceNo,
                                    c.InvoiceBasic.InvoiceApplicantName,
                                    c.InvoiceBasic.InvoiceHolderName,
                                    c.InvoiceBasic.InvoiceDate == null ? '' : getDate(convertJsonDateToJSDate(c.InvoiceBasic.InvoiceDate)),
                                    c.InvoiceBasic.InvoiceStatusName
                                );
                            }
                        });

                        $("tfoot", "#tblInvoiceList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.invoiceList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: invoice.List.InvoicedList,
                            callBackArgs: null
                        });

                        invoice.List.BindInvoicedMenu();

                    } else {
                        $("tfoot", "#tblInvoiceList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        InvoiceListExportToExcel: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InvoiceFileCenter/InvoiceListExportToExcel", function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/FAM/InvoiceFileCenter/InvoiceListExportToExcelDownload?fileName=" + response.Data);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        InvoiceListSelectedExportToExcel: function () {

            var invoiceIds = [];
            $("input[name='chkInvoiceId']:checked").each(
                function (i) { invoiceIds[i] = $(this).val(); }
            );

            if (invoiceIds.length < 1) {
                $.showModalMessageBox("请选择需要导出的发票.");
                return false;
            }

            var data = {
                invoiceIds: invoiceIds,
            };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InvoiceFileCenter/InvoiceListSelectedExportToExcel", data, function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/FAM/InvoiceFileCenter/InvoiceListExportToExcelDownload?fileName=" + response.Data);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        Selected: function (e) {
            if ($(e).prop('checked') == true) {
                $.checkbox.all("chkInvoiceId");
                $.checkbox.all("chkInvoiceAll");

            } else {
                $.checkbox.not("chkInvoiceId");
                $.checkbox.not("chkInvoiceAll");
            }
        },
    },

    getCaseFeeList: function () {
        $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/CaseFee/CaseFeeList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblInvoiceObjectList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.CaseFeeList, function (i, c) {
                        $("tbody", "#tblInvoiceObjectList").addRow(
                            i + 1,
                            c.ContractNo,
                            c.RefContractNo,
                            c.Parent.Basic.CaseName,
                            c.Parent.Basic.CasePhaseName,
                            "<a href='javascript:void(0)' onclick='javascript:$.case.View(\"" + c.CaseNo + "\")'>" + c.CaseNo + "</a>",
                            c.CaseFeeTypeName,
                            c.Amount == null ? 0 : c.Amount,
                            "<a href='javascript:void(0);' onclick='javascript: invoice.Invoice.ViewReceviedPayment(" + c.CaseFeeId + ");'>" + (c.CashedAmount == null ? 0 : c.CashedAmount) + "</a>",
                            c.InvoicedAmount == null ? 0 : c.InvoicedAmount,
                            "<input type='text' class='form-control' style='background-color:yellow;border:0px'  id='item_CaseFeeInvoiceAmount' name='item_CaseFeeInvoiceAmount' casefeeid=" + c.CaseFeeId + " amount=" + c.Amount + " value='" + (c.InvoicedAmount == null ? (c.Amount - 0) : (c.Amount - c.InvoicedAmount)) + "' />",
                            //"<span  id='item_CaseFeeInvoiceOverAmount' name='item_CaseFeeInvoiceOverAmount' style='color:red ' >" + (c.Amount > c.InvoicedAmount ? 0 : (c.InvoicedAmount - c.Amount)) + "</span>",
                            "<input type='checkbox'  id='item_InvoiceApply' name='item_InvoiceApply' customerid='" + c.CustomerId + "' customerno='" + c.CustomerNo + "' contractno='" + c.ContractNo + "' refcontractno='" + c.ContractNo + "' caseFeeId='" + c.CaseFeeId + "' caseFeeTypeId='" + c.CaseFeeTypeId + "' caseId='" + c.CaseId + "' caseNo='" + c.CaseNo + "' value='" + c.CaseNo + "'>"
                        );
                    });
                    $("tfoot", "#tblInvoiceObjectList").show();
                    $(".simple-grid-none-data-wrap").hide();
                    $(".pull-right.page-box.caseFeeList").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: invoice.getCaseFeeList,
                        callBackArgs: null
                    });

                } else {
                    $("tfoot", "#tblInvoiceObjectList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },
    /*文件*/
    File: {

        View: function (invoiceFileId, customerNo, invoiceFileName) {
            if (invoiceFileId == '' || invoiceFileName == '') {
                $.showModalMessageBox("无票据文件.");
                return false;
            }

            var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
            var picfiles = new Array('jpg', 'tif', 'pdf');
            var extName = invoiceFileName.substring(invoiceFileName.lastIndexOf('.') + 1, invoiceFileName.length);

            if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                var path = GV_LS.OfficeOnlineUrl + GV_LS.OnlineUrl + "casefiles/InvoiceFiles/" + customerNo + "/" + invoiceFileName;
                window.open(path);
            }
            else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                var path = GV_LS.OnlineUrl + "casefiles/InvoiceFiles/" + customerNo + "/" + invoiceFileName;
                window.open(path);
            } else {
                invoice.File.Download(invoiceFileId);
            }

            return true;
        },

        Download: function (invoiceFileId) {
            window.open(AP_ROOT + AP_PAGE_ID + "/FAM/InvoiceFile/InvoiceFileDownload?invoiceFileId=" + invoiceFileId);
            return true;
        },

        Delete: function (invoiceFileId) {
            var data = {
                invoiceFileId: invoiceFileId,
            };

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InvoiceFile/Delete", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("删除成功");
                    $('#invoiceFileListModal').modal('hide');
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        Close: function () {
            $('#invoiceFileListModal').modal('hide');
        },

        ViewFile: function (invoiceFileId, caseno, invoiceFileName) {

            var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
            var picfiles = new Array('jpg', 'tif', 'pdf', 'png');
            var extName = invoiceFileName.substring(invoiceFileName.lastIndexOf('.') + 1, invoiceFileName.length);

            if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                var path = GV_LS.OfficeOnlineUrl + GV_LS.OnlineUrl + "casefiles/CaseFeeFiles/" + caseno + "/" + invoiceFileName;
                window.open(path);
            }
            else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                var path = GV_LS.OnlineUrl + "casefiles/CaseFeeFiles/" + caseno + "/" + invoiceFileName;
                window.open(path);
            } else {
                invoice.File.DownloadFile(invoiceFileId);
            }
            return true;
        },

        DownloadFile: function (invoiceFileId) {
            window.open(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFileCenter/InvoiceFileDownload?invoiceFileId=" + invoiceFileId);
            return true;
        },
    },
};

$(document).ready(function () {

    var invoiceHolder = new AssociateUser(
        $("#divAssociateUserList"),
        $("#Invoice_InvoiceBasic_InvoiceHolder"),
        $("#Invoice_InvoiceBasic_InvoiceHolderName"),
        null
    );

    var businessOwner = new AssociateUser(
        $("#divAssociateUserList"),
        $("#SearchCondition_InvoiceApplicant"),
        $("#SearchCondition_InvoiceApplicantName"),
        null
    );

    //$("#SearchCondition_InvoiceApplicantName").off().on("click", function () {
    //    $("#hidUserId").val("SearchCondition_InvoiceApplicant");
    //    $("#hidUserName").val("SearchCondition_InvoiceApplicantName");
    //    $("#divUserList").css({
    //        "position": "absolute",
    //        "left": $("#SearchCondition_InvoiceApplicantName").position().left + 16,
    //        "top": $("#SearchCondition_InvoiceApplicantName").position().top + 70,
    //        "z-index": 1200
    //    }).toggle();
    //    return false;
    //});

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

    $(document).click(function () {
        $("#divUserList").off().hide();
        $("#divAssociateUserList").off().hide();
        $("#divInvoiceServiceList").off().hide();
        $("#divCaseTypeCheckBoxList").off().hide();
        $("#divCaseFeeTypeCheckBoxList").off().hide();
    });

    $(window).resize(function () {
        invoice.ResetSize();
    });

    $(document).off('click', '.btn_serviceItem_add').on('click', '.btn_serviceItem_add', function () {
        invoice.Invoice.Services.Item.Add(this);
    });

    $(document).off('click', '.btn_serviceItem_remove').on('click', '.btn_serviceItem_remove', function () {
        invoice.Invoice.Services.Item.Remove(this);
    });

    $(document).off('click', '.btn_serviceItem_remove').on('click', '.btn_serviceItem_remove', function () {
        invoice.Invoice.Services.Item.Remove(this);
    });

    $(document).off('click', '#item_InvoiceApply').on('click', '#item_InvoiceApply', function () {
        invoice.Invoice.Objects.Item.Apply(this);
        invoice.Invoice.TotalAmountSet();
    });

    $(document).off('click', '#item_InvoiceAllApply').on('click', '#item_InvoiceAllApply', function () {
        if ($(this).prop('checked') == true) {
            //$.checkbox.all("item_InvoiceApply");
            $.checkbox.all("item_InvoiceAllApply");
            $("input[name='item_InvoiceApply']").each(
                function () { $(this).click(); }
            );

        } else {
            //$.checkbox.not("item_InvoiceApply");
            $.checkbox.not("item_InvoiceAllApply");
            $("input[name='item_InvoiceApply']").each(
               function () { $(this).click(); }
            );
        }
    });

    $(document).off('change', '#item_CaseFeeInvoiceAmount').on('change', '#item_CaseFeeInvoiceAmount', function () {
        if ($(this).val() == '' || !$(this).isMoney()) {
            $(this).val(0);
        }
        debugger
        if (parseFloat($(this).attr("amount")) < parseFloat($(this).val())) {
            $(this).val(0);
            $.showTips('金额不能高于' + parseFloat($(this).attr("amount")), 0, 3)
            return;
        }
        //else {
        //    $(this).parent().parent().find("#item_CaseFeeInvoiceOverAmount").html(parseFloat($(this).val()) - parseFloat($(this).attr("amount")));
        //}
       
        invoice.Invoice.TotalAmountSet();
    });
 
    $(document).off('change', '#item_Quantity').on('change', '#item_Quantity', function () {
        invoice.Invoice.ServiceAmountSet(this);
    });

    $(document).off('change', '#item_UnitPrice').on('change', '#item_UnitPrice', function () {
        if ($(this).val() == '' || !$(this).isMoney()) {
            $(this).val(0);
        }
        invoice.Invoice.ServiceAmountSet(this);
    });

    $(document).off('click', '#btnInvoiceSubmit').on('click', '#btnInvoiceSubmit', function () {
        invoice.Invoice.Application.CreateUpdate(true);
    });

    $(document).off('click', '#btnInvoiced').on('click', '#btnInvoiced', function () {
        invoice.Invoice.Invoiced.CreateUpdate(true);
    });
    
    $(document).off('click', '#btnInvoiceNoChange').on('click', '#btnInvoiceNoChange', function () {
        invoice.Invoice.InvoiceNo.Update(true);
    });

    $(document).off('click', '#btnInvoiceNoChangeCancel,#btnInvoiceNoChangeClose').on('click', '#btnInvoiceNoChangeCancel,#btnInvoiceNoChangeClose', function () {
        invoice.Invoice.InvoiceNo.Close(true);
    });

    $(document).off('click', '#btnInvoiceDateChange').on('click', '#btnInvoiceDateChange', function () {
        invoice.Invoice.InvoiceDate.Update(true);
    });

    $(document).off('click', '#btnInvoiceDateChangeCancel,#btnInvoiceDateChangeClose').on('click', '#btnInvoiceDateChangeCancel,#btnInvoiceDateChangeClose', function () {
        invoice.Invoice.InvoiceDate.Close(true);
    });

    $(document).off('click', '#btnInvoiceCancel').on('click', '#btnInvoiceCancel', function () {
        invoice.Invoice.Invoiced.Canceled();
    });

    $(document).off('click', '#btnApplictionCancel').on('click', '#btnApplictionCancel', function () {
        invoice.Invoice.Application.Canceled();
    });

    $(document).off('click', '#btnRejected').on('click', '#btnRejected', function () {
        invoice.Invoice.Invoiced.Rejected();
    });

    $(document).off('click', '#btnInvoiceFileListCancel,#btnInvoiceFileListClose').on('click', '#btnInvoiceFileListCancel,#btnInvoiceFileListClose', function () {
        invoice.File.Close();
    });

    $(document).off('click', '#btnInvoiceListExportToExcel').on('click', '#btnInvoiceListExportToExcel', function () {
        invoice.List.InvoiceListExportToExcel();
    });

    $(document).off('click', '#btnInvoiceListExportSelectedToExcel').on('click', '#btnInvoiceListExportSelectedToExcel', function () {
        invoice.List.InvoiceListSelectedExportToExcel();
    });

    $("#divInvoiceServiceList").find("li").off().on("click", function () {
        var invoiceServiceName = $(this).find("a").attr("name");
        var invoiceServiceId = $(this).find("a").attr("serviceTypeId");
        $("input[id='item_ServiceName']").each(
             function () {
                 if ($(this).attr("selected") == 'selected')
                 {
                     $(this).val(invoiceServiceName);
                 }
             }
        );
 
        $("#divInvoiceServiceList").hide();
    });

    $(document).off('click', '#item_ServiceName').on('click', '#item_ServiceName', function () {

        $("input[id='item_ServiceName']").each(
            function () {
                $(this).removeAttr("selected");
            }
        );
        $(this).attr("selected", "selected");
        $("#divInvoiceServiceList").off().css({
            "position": "absolute",
            "left": $(this).parents().position().left + 4,
            "top": $(this).parents().position().top + 30,
            "z-index": 1200
        }).show();
        return false;
    });

    $(document).off('click', '#chkInvoiceAll').on('click', '#chkInvoiceAll', function () {
        invoice.List.Selected(this);
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
            "left": $(tirgger).parent().position().left + 22,
            "top": $(tirgger).parent().position().top + 56,
            "z-index": 9999
        }).toggle();

        return false;
    });

});