var invoice = {

    /*申请开票*/
    Application : {
        List: function () {
            $("#postForm").ajaxPost(AP_ROOT + "FAM/Invoice/CaseFees", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblCaseFeeList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.CaseFeeList, function(i, c) {
                            $("tbody", "#tblCaseFeeList").addRow(
                                "<input type='checkbox' name='chkCaseFeeId' class='ng-pristine ng-valid' customerid='" + c.CustomerId + "' value='" + c.CaseFeeId + "'>",
                                c.CaseNo,
                                c.CaseRequestNo,
                                c.ContractNo,
                                c.CustomerName,
                                c.CaseFeeTypeName,
                                c.Amount,
                                c.InvoicedAmount,
                                parseFloat(c.InvoicedAmount) > c.Amount ? "<span style='color:red'>" + (parseFloat(c.InvoicedAmount) - parseFloat(c.Amount)) + "</span>" : "0",
                                c.InformDate == null ? '' : getDate(convertJsonDateToJSDate(c.InformDate)),
                                c.RequestUserName,
                                c.CashedAmount,
                                c.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.CashedDate))
                            );
                        });

                        $("tfoot", "#tblCaseFeeList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.caseFeeList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: invoice.Application.List,
                            callBackArgs: null
                        });

                    } else {
                        $("tfoot", "#tblCaseFeeList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        InvoiceList: function () {
            $("#postForm").ajaxPost(AP_ROOT + "FAM/Invoice/InvoiceList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblInvoiceList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.InvoiceList, function (i, c) {

                            var invoiceFileId = c.InvoiceFile == null ? '' : c.InvoiceFile.FileId;
                            var invoiceFileName = c.InvoiceFile == null ? '' : c.InvoiceFile.FileName;

                            $("tbody", "#tblInvoiceList").addRow(
                                c.InvoiceBasic.CustomerName,
                                c.InvoiceBasic.InvoiceAmount,
                                c.InvoiceBasic.CustomerCompanyCode,
                                c.InvoiceBasic.CustomerPhone,
                                c.InvoiceBasic.CustomerBankName,
                                c.InvoiceBasic.CustomerBankAccount,
                                c.InvoiceBasic.InvoiceDate == null ? '' : getDate(convertJsonDateToJSDate(c.InvoiceBasic.InvoiceDate)),
                                c.InvoiceBasic.InvoiceApplicantName,
                                c.InvoiceBasic.InvoiceStatusName,
                                "<a href='javascript:void(0)' onclick='javascript:invoice.Processor.View(\"" + c.InvoiceBasic.InvoiceId + "\",\"" + null + "\")'>发票信息</a> &nbsp; "+
                                "<a href='javascript:void(0)' onclick='javascript:invoice.Auditor.Audit.ViewAudit(\"" + c.InvoiceBasic.InvoiceId + "\")'>审批信息</a> &nbsp; " +
                                "<a href='javascript:void(0)' onclick='javascript:invoice.File.View(\"" + invoiceFileId + "\",\"" + c.InvoiceBasic.CustomerNo + "\",\"" + invoiceFileName + "\")'>发票文件</a> &nbsp;"
                                );
                        });

                        $("tfoot", "#tblInvoiceList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.invoiceList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: invoice.Application.InvoiceList,
                            callBackArgs: null
                        });


                    } else {
                        $("tfoot", "#tblInvoiceList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        Selected: function (e) {

            if ($(e).attr("checked") == "checked") {
                $.checkbox.all("chkCaseFeeId");
            } else {
                $.checkbox.not("chkCaseFeeId");
            }
        },
        Open: function () {

            var customerIds = new Array();

            $("input[name='chkCaseFeeId']:checked").each(
                function () {
                    if ($.inArray($(this).attr("customerid"), customerIds) > -1) {
                    } else {
                        customerIds.push($(this).attr("customerid"));
                    }
                }
            );
            if (customerIds.length > 1) {
                $.showModalMessageBox("客户不一致,不允许开票");
                return false;
            }

            var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
            if (caseFeeIds.length == 0) {
                $.showModalMessageBox("请选择需要开票的应收账款.");
                return false;
            }

            var url = AP_ROOT + "FAM/Invoice/Create";
            var data = {
                customerId: customerIds[0],
                caseFeeIds: caseFeeIds
            };

            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#invoiceModal').modal({ backdrop: 'static', keyboard: false });
                $('#invoiceModal').on('hidden.bs.modal', function () {
                    $("#invoiceModal").remove();
                });
            });
        },
        Close: function () {
            $('#invoiceModal').modal('hide');
        },
        Create: function () {

            var data = {};

            var dataIsNOk = false;

            if ($("#Invoice_InvoiceBasic_CustomerName").val() == '') {
                $.showModalMessageBox("请输入客户名称.");
                return false;
            }
            if ($("#Invoice_InvoiceBasic_CustomerCompanyCode").val() == '') {
                $.showModalMessageBox("请输入客户纳税人识别码.");
                return false;
            }
            if ($("#Invoice_InvoiceBasic_CustomerBankName").val() == '') {
                $.showModalMessageBox("请输入客户开户银行.");
                return false;
            }
            if ($("#Invoice_InvoiceBasic_CustomerBankAccount").val() == '') {
                $.showModalMessageBox("请输入客户开户账号.");
                return false;
            }
            if ($("#Invoice_InvoiceBasic_InvoiceDate").val() == '') {
                $.showModalMessageBox("请输入票据日期.");
                return false;
            }

            if ($("#Invoice_InvoiceBasic_DeliveryMode").val() == '2') {

                if ($("#Invoice_InvoiceBasic_DeliveryRecipients").val() == '') {
                    $.showModalMessageBox("请输入收件人");
                    return false;
                }
                if ($("#Invoice_InvoiceBasic_DeliveryAddress").val() == '') {
                    $.showModalMessageBox("请输入收件地址");
                    return false;
                }

                if ($("#Invoice_InvoiceBasic_DeliveryPhone").val() == '') {
                    $.showModalMessageBox("请输入收件电话");
                    return false;
                }
            }
            
            data["InvoiceBasic.CustomerId"] = $("#Invoice_InvoiceBasic_CustomerId").val();
            data["InvoiceBasic.CustomerNo"] = $("#Invoice_InvoiceBasic_CustomerNo").val();
            data["InvoiceBasic.CustomerName"] = $("#Invoice_InvoiceBasic_CustomerName").val();
            data["InvoiceBasic.CustomerBusinessAddress"] = $("#Invoice_InvoiceBasic_CustomerBusinessAddress").val();
            data["InvoiceBasic.CustomerCompanyCode"] = $("#Invoice_InvoiceBasic_CustomerCompanyCode").val();
            data["InvoiceBasic.CustomerPhone"] = $("#Invoice_InvoiceBasic_CustomerPhone").val();
            data["InvoiceBasic.CustomerBankName"] = $("#Invoice_InvoiceBasic_CustomerBankName").val();
            data["InvoiceBasic.CustomerBankAccount"] = $("#Invoice_InvoiceBasic_CustomerBankAccount").val();
            data["InvoiceBasic.InvoiceDate"] = $("#Invoice_InvoiceBasic_InvoiceDate").val();
            data["InvoiceBasic.DeliveryMode"] = $("#Invoice_InvoiceBasic_DeliveryMode").val();
            data["InvoiceBasic.DeliveryRecipients"] = $("#Invoice_InvoiceBasic_DeliveryRecipients").val();
            data["InvoiceBasic.DeliveryAddress"] = $("#Invoice_InvoiceBasic_DeliveryAddress").val();
            data["InvoiceBasic.DeliveryPhone"] = $("#Invoice_InvoiceBasic_DeliveryPhone").val();
            data["InvoiceBasic.Remark"] = $("#Invoice_InvoiceBasic_Remark").val();
            
            $("#tblInvoiceCaseFeeList>tbody>tr").each(function (j, e) {

                if ($(e).find("#item_InvoiceAmount").val() == '') {
                    dataIsNOk = true;
                    $.showModalMessageBox("第" + (j + 1) + "行，输入开票金额.");
                    return false;
                }

                data["CaseFeeList[" + j + "].CaseFeeId"] = $(e).find("#item_InvoiceAmount").attr("casefeeid");
                data["CaseFeeList[" + j + "].InvoiceAmount"] = $(e).find("#item_InvoiceAmount").val();

                i++;

            });

            if (dataIsNOk) return false;

            $.ajaxPost(AP_ROOT + "FAM/Invoice/InvoiceCreate", data, function (response) {
            //$("#invoiceForm").ajaxPost(AP_ROOT + "FAM/Invoice/InvoiceCreate", function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("开票申请成功.");
                    invoice.Application.List();
                    invoice.Application.Close();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },
        Edit: function () {

            if ($("#Invoice_InvoiceBasic_CustomerName").val() == '') {
                $.showModalMessageBox("请输入客户名称.");
                return false;
            }
            if ($("#Invoice_InvoiceBasic_CustomerCompanyCode").val() == '') {
                $.showModalMessageBox("请输入客户纳税人识别码.");
                return false;
            }
            if ($("#Invoice_InvoiceBasic_CustomerBankName").val() == '') {
                $.showModalMessageBox("请输入客户开户银行.");
                return false;
            }
            if ($("#Invoice_InvoiceBasic_CustomerBankAccount").val() == '') {
                $.showModalMessageBox("请输入客户开户账号.");
                return false;
            }

            if ($("#Invoice_InvoiceBasic_InvoiceNo").val() == '') {
                $.showModalMessageBox("请输入票据号.");
                return false;
            }

            if ($("#Invoice_InvoiceBasic_InvoiceDate").val() == '') {
                $.showModalMessageBox("请输入票据日期.");
                return false;
            }

            if ($("#Invoice_InvoiceBasic_DeliveryMode").val() == '2') {

                if ($("#Invoice_InvoiceBasic_DeliveryRecipients").val() == '') {
                    $.showModalMessageBox("请输入收件人");
                    return false;
                }
                if ($("#Invoice_InvoiceBasic_DeliveryAddress").val() == '') {
                    $.showModalMessageBox("请输入收件地址");
                    return false;
                }

                if ($("#Invoice_InvoiceBasic_DeliveryPhone").val() == '') {
                    $.showModalMessageBox("请输入收件电话");
                    return false;
                }
            }

            $("#invoiceForm").ajaxPost(AP_ROOT + "FAM/Invoice/Invoiced", function (response) {
                if (response.IsSuccess) {
                    invoice.Processor.List.PendingList();
                    invoice.Processor.Close();
                    $.showModalMessageBox("开票成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },
    },

    /*开票*/
    Processor: {
        Open: function (invoiceId, viewMode,auditId) {
            var url = AP_ROOT + "FAM/Invoice/InvoiceAudit";
            var data = {
                invoiceId: invoiceId,
                auditId : auditId,
                viewMode: viewMode
            };

            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#invoiceViewModal').modal({ backdrop: 'static', keyboard: false });
                $('#invoiceViewModal').on('hidden.bs.modal', function () {
                    $("#invoiceViewModal").remove();
                });
            });
        },

        View: function (invoiceId, viewMode, auditId) {
            var url = AP_ROOT + "FAM/Invoice/View";
            var data = {
                invoiceId: invoiceId,
                auditId: auditId,
                viewMode: viewMode
            };

            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#invoiceViewModal').modal({ backdrop: 'static', keyboard: false });
                $('#invoiceViewModal').on('hidden.bs.modal', function () {
                    $("#invoiceViewModal").remove();
                });
            });
        },

        Close: function () {
            $('#invoiceViewModal').modal('hide');
        },

        List: {
            /*待开票*/
            PendingList: function () {
                $("#postForm").ajaxPost(AP_ROOT + "FAM/InvoiceProcess/PendingList", function (response) {
                    if (response.IsSuccess) {
                        $("tbody", "#tblInvoiceList").clearRow();
                        if (response.Data.TotalItemCount > 0) {
                            $(".info_inall.layoutfix").show();
                            $.each(response.Data.InvoiceList, function(i, c) {

                                $("tbody", "#tblInvoiceList").addRow(
                                   "<span style='width: 130px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerName + "</span>",
                                    c.InvoiceBasic.InvoiceAmount,
                                   "<span style='width: 80%; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerCompanyCode + "</span>",
                                    c.InvoiceBasic.CustomerPhone,
                                    "<span style='width: 80%; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerBankName + "</span>",
                                     "<span style='width: 80%; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerBankAccount + "</span>",
                                    c.InvoiceBasic.InvoiceDate == null ? '' : getDate(convertJsonDateToJSDate(c.InvoiceBasic.InvoiceDate)),
                                    c.InvoiceBasic.InvoiceApplicantName,
                                    "<a href='javascript:void(0)' onclick='javascript:invoice.Processor.Open(\"" + c.InvoiceBasic.InvoiceId + "\",\"Invoiced\")'>开票</a> &nbsp; "
                                    );

                            });

                            $("tfoot", "#tblInvoiceList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.invoiceList").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: invoice.Processor.List.PendingList,
                                callBackArgs: null
                            });

                        } else {
                            $("tfoot", "#tblInvoiceList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                    }
                });
            },

            /*已开票*/
            InvoicedList: function() {
                $("#postForm").ajaxPost(AP_ROOT + "FAM/InvoiceProcess/InvoicedList", function (response) {
                    if (response.IsSuccess) {
                        $("tbody", "#tblInvoiceList").clearRow();
                        if (response.Data.TotalItemCount > 0) {
                            $(".info_inall.layoutfix").show();
                            $.each(response.Data.InvoiceList, function (i, c) {

                                var invoiceFileId = c.InvoiceFile == null ? '' : c.InvoiceFile.FileId;
                                var invoiceFileName = c.InvoiceFile == null ? '' : c.InvoiceFile.FileName;

                                $("tbody", "#tblInvoiceList").addRow(
                                   "<span style='width: 130px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerName + "</span>",
                                    c.InvoiceBasic.InvoiceAmount,
                                   "<span style='width: 80%; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerCompanyCode + "</span>",
                                    c.InvoiceBasic.CustomerPhone,
                                    "<span style='width: 80%; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerBankName + "</span>",
                                    "<span style='width: 80%; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerBankAccount + "</span>",
                                    c.InvoiceBasic.InvoiceDate == null ? '' : getDate(convertJsonDateToJSDate(c.InvoiceBasic.InvoiceDate)),
                                    c.InvoiceBasic.InvoiceApplicantName,
                                    "<a href='javascript:void(0)' onclick='javascript:invoice.Processor.View(\"" + c.InvoiceBasic.InvoiceId +"\",\"" + null + "\")'>发票信息</a> &nbsp; "+
                                    "<a href='javascript:void(0)' onclick='javascript:invoice.File.View(\"" + invoiceFileId + "\",\"" + c.InvoiceBasic.CustomerNo + "\",\"" + invoiceFileName + "\")'>发票文件</a> &nbsp;"

                                    );
                            });

                            $("tfoot", "#tblInvoiceList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.invoiceList").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: invoice.Processor.List.InvoicedList,
                                callBackArgs: null
                            });


                        } else {
                            $("tfoot", "#tblInvoiceList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                    }
                });
            },
        },

        Confirm: {
            Open: function() {
                var url = AP_ROOT + "FAM/Invoice/InvoiceConfirm";
                var data = {
                    invoiceId: $("#Invoice_InvoiceBasic_InvoiceId").val()
                };

                $.openLoading();

                $("<div></div>").load(url, data, function(result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#invoiceConfirmModal').modal({ backdrop: 'static', keyboard: false });
                    $('#invoiceConfirmModal').on('hidden.bs.modal', function() {
                        $("#invoiceConfirmModal").remove();
                    });
                });
            },

            Close: function() {
                $('#invoiceConfirmModal').modal('hide');
            },
        },

        Create: function () {
            if ($("#InvoiceNo").val() == '') {
                $.showModalMessageBox("请输入票据编号.");
                return false;
            }

            //if ($("#InvoiceAmount").val() == '') {
            //    $.showModalMessageBox("请输入票据金额.");
            //    return false;
            //}

            if ($("#CashedDate").val() == '') {
                $.showModalMessageBox("请输入票据日期.");
                return false;
            }

            if ($("#flInvoiceFile").val() == '') {
                $.showModalMessageBox("请选择上传文件.");
                return false;
            }

            $.openLoading();
            $('#invoiceConfirm').ajaxSubmit({
                success: function (response) {
                    $.closeLoading();
                    if (response.IsSuccess) {
                        $.showModalMessageBox("票据确认成功.");
                        invoice.Processor.Confirm.Close();
                        invoice.Processor.Close();
                        invoice.Processor.List.PendingList();
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                }
            });
        }
    },

    /*审批*/
    Auditor: {
        List: {
            PendingList: function() {
                $("#postForm").ajaxPost(AP_ROOT + "FAM/InvoiceAudit/PendingList", function (response) {
                    if (response.IsSuccess) {
                        $("tbody", "#tblInvoiceList").clearRow();
                        if (response.Data.TotalItemCount > 0) {
                            $(".info_inall.layoutfix").show();
                            $.each(response.Data.InvoiceList, function (i, c) {

                                var auditId = c.InvoiceAudit == null ? '' : c.InvoiceAudit.AuditId;

                                $("tbody", "#tblInvoiceList").addRow(
                                   "<span style='width: 130px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerName + "</span>",
                                    c.InvoiceBasic.InvoiceAmount,
                                   "<span style='width: 80%; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerCompanyCode + "</span>",
                                    c.InvoiceBasic.CustomerPhone,
                                    "<span style='width: 80%; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerBankName + "</span>",
                                     "<span style='width: 80%; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerBankAccount + "</span>",
                                    c.InvoiceBasic.InvoiceDate == null ? '' : getDate(convertJsonDateToJSDate(c.InvoiceBasic.InvoiceDate)),
                                    c.InvoiceBasic.InvoiceApplicantName,
                                    c.InvoiceBasic.InvoiceStatusName,
                                    c.InvoiceAudit == null ? '' : c.InvoiceAudit.AuditorName,
                                    "<a href='javascript:void(0)' onclick='javascript:invoice.Auditor.Audit.ViewAudit(\"" + c.InvoiceBasic.InvoiceId + "\")'>审批信息</a> &nbsp; " +
                                    "<a href='javascript:void(0)' onclick='javascript:invoice.Processor.Open(\"" + c.InvoiceBasic.InvoiceId + "\",\"Audit\",\"" + auditId + "\")'>审批</a> &nbsp; "
                                    );
                            });

                            $("tfoot", "#tblInvoiceList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.invoiceList").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: invoice.Auditor.List.PendingList,
                                callBackArgs: null
                            });
                        } else {
                            $("tfoot", "#tblInvoiceList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                    }
                });
            },

            ApprovedList: function () {
                $("#postForm").ajaxPost(AP_ROOT + "FAM/InvoiceAudit/ApprovedList", function (response) {
                    if (response.IsSuccess) {
                        $("tbody", "#tblInvoiceList").clearRow();
                        if (response.Data.TotalItemCount > 0) {
                            $(".info_inall.layoutfix").show();
                            $.each(response.Data.InvoiceList, function (i, c) {

                                $("tbody", "#tblInvoiceList").addRow(
                                   "<span style='width: 130px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerName + "</span>",
                                    c.InvoiceBasic.InvoiceAmount,
                                   "<span style='width: 80%; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerCompanyCode + "</span>",
                                    c.InvoiceBasic.CustomerPhone,
                                    "<span style='width: 80%; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerBankName + "</span>",
                                     "<span style='width: 80%; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerBankAccount + "</span>",
                                    c.InvoiceBasic.InvoiceDate == null ? '' : getDate(convertJsonDateToJSDate(c.InvoiceBasic.InvoiceDate)),
                                    c.InvoiceBasic.InvoiceApplicantName,
                                    c.InvoiceBasic.InvoiceStatusName,
                                    c.InvoiceAudit == null ? '' : c.InvoiceAudit.AuditorName,
                                    "<a href='javascript:void(0)' onclick='javascript:invoice.Auditor.Audit.ViewAudit(\"" + c.InvoiceBasic.InvoiceId + "\")'>审批信息</a> &nbsp; "
                                    );
                            });

                            $("tfoot", "#tblInvoiceList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.invoiceList").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: invoice.Auditor.List.PendingList,
                                callBackArgs: null
                            });
                        } else {
                            $("tfoot", "#tblInvoiceList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                    }
                });
            },

            RejectedList: function () {
                $("#postForm").ajaxPost(AP_ROOT + "FAM/InvoiceAudit/RejectedList", function (response) {
                    if (response.IsSuccess) {
                        $("tbody", "#tblInvoiceList").clearRow();
                        if (response.Data.TotalItemCount > 0) {
                            $(".info_inall.layoutfix").show();
                            $.each(response.Data.InvoiceList, function (i, c) {

                                $("tbody", "#tblInvoiceList").addRow(
                                   "<span style='width: 130px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerName + "</span>",
                                    c.InvoiceBasic.InvoiceAmount,
                                   "<span style='width: 80%; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerCompanyCode + "</span>",
                                    c.InvoiceBasic.CustomerPhone,
                                    "<span style='width: 80%; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerBankName + "</span>",
                                     "<span style='width: 80%; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.InvoiceBasic.CustomerBankAccount + "</span>",
                                    c.InvoiceBasic.InvoiceDate == null ? '' : getDate(convertJsonDateToJSDate(c.InvoiceBasic.InvoiceDate)),
                                    c.InvoiceBasic.InvoiceApplicantName,
                                    c.InvoiceBasic.InvoiceStatusName,
                                    c.InvoiceAudit == null ? '' : c.InvoiceAudit.AuditorName,
                                    "<a href='javascript:void(0)' onclick='javascript:invoice.Auditor.Audit.ViewAudit(\"" + c.InvoiceBasic.InvoiceId + "\")'>审批信息</a> &nbsp; "
                                    );
                            });

                            $("tfoot", "#tblInvoiceList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.invoiceList").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: invoice.Auditor.List.PendingList,
                                callBackArgs: null
                            });
                        } else {
                            $("tfoot", "#tblInvoiceList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                    }
                });
            }
        },

        Audit: {
            Open: function () {
                var url = AP_ROOT + "FAM/InvoiceAudit/InvoiceAudit";

                if ($("#AuditId").val() == '') {
                    $.showModalMessageBox("无对应的审批信息.");
                }

                var data = {
                    invoiceId: $("#Invoice_InvoiceBasic_InvoiceId").val(),
                    auditId: $("#AuditId").val()
                };

                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#invoiceAuditModal').modal({ backdrop: 'static', keyboard: false });
                    $('#invoiceAuditModal').on('hidden.bs.modal', function () {
                        $("#invoiceAuditModal").remove();
                    });
                });
            },

            Close: function () {
                $('#invoiceAuditModal').modal('hide');
            },

            CreateUpdate: function (auditStatus) {
                if ($("#InvoiceAudit_AuditContent").val() == '') {
                    $.showModalMessageBox("请输入审批内容");
                    return false;
                }

                var data = {};

                data["InvoiceAudit.AuditId"] = $("#AuditId").val();
                data["InvoiceAudit.InvoiceId"] = $("#InvoiceId").val();
                data["InvoiceAudit.AuditContent"] = $("#InvoiceAudit_AuditContent").val();
                data["InvoiceAudit.AuditStatus"] = auditStatus;

                $.ajaxPost(AP_ROOT + "FAM/InvoiceAudit/InvoiceAuditCreate", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("审批成功.");
                        invoice.Auditor.Audit.Close();

                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },

            Approved: function () {
                invoice.Auditor.Audit.CreateUpdate('A');
            },

            Rejected: function () {
                invoice.Auditor.Audit.CreateUpdate('R');
            },

            ViewAudit: function (invoiceId) {
                var data =
                {
                    invoiceId: invoiceId,
                };

                var url = AP_ROOT + "FAM/InvoiceAudit/InvoiceAuditList";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#invoiceAuditListModal').modal({ backdrop: 'static', keyboard: false });
                    $('#invoiceAuditListModal').on('hidden.bs.modal', function () {
                        $("#invoiceAuditListModal").remove();
                    });
                });
            },

            ViewAuditClose: function () {
                $('#invoiceAuditListModal').modal('hide');
            },
        }
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
                var path = GV_IPR.OfficeOnlineUrl + GV_IPR.OnlineUrl + "casefiles/InvoiceFiles/" + customerNo + "/" + invoiceFileName;
                window.open(path);
            }
            else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                var path = GV_IPR.OnlineUrl + "casefiles/InvoiceFiles/" + customerNo + "/" + invoiceFileName;
                window.open(path);
            } else {
                invoice.File.Download(invoiceFileId);
            }

            return true;
        },

        Download: function (invoiceFileId) {
            window.open(AP_ROOT + "FAM/InvoiceFile/InvoiceFileDownload?invoiceFileId=" + invoiceFileId);
            return true;
        },

        Close: function () {
            $('#invoiceFileListModal').modal('hide');
        },

        ViewFile: function (caseFeeId,caseno, caseFileName) {
 
            var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
            var picfiles = new Array('jpg', 'tif', 'pdf');
            var extName = caseFileName.substring(caseFileName.lastIndexOf('.') + 1, caseFileName.length);

            if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                var path = GV_IPR.OfficeOnlineUrl + GV_IPR.IPROnlineUrl + "CaseFeeFiles/" + caseno + "/" + caseFileName;
                window.open(path);
            }
            else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                var path = GV_IPR.IPROnlineUrl + "CaseFeeFiles/" + caseno + "/" + caseFileName;
                window.open(path);
            } else {
                invoice.File.DownloadFile(caseFeeId);
            }
            return true;
        },

        DownloadFile: function (caseFeeId) {
            window.open(AP_ROOT + "IPR/CaseFileCenter/CaseFeeFileDownload?caseFeeId=" + caseFeeId);
            return true;
        },
    },
}

$(document).ready(function () {

    $(document).click(function (e) {
        $("#divCasePhaseCheckBoxList").die().hide();
        $("#divCaseFeeTypeCheckBoxList").die().hide();
        $("#divUserList").die().hide();
    });
 
    $("#chkCaseFeeAll").die().live("click", function () {
        invoice.Application.Selected(this);
    });

    $("#btnSearch").click(function () {

        $("#CaseFeeSearchCondition_PageNo").val(1);
        $("#CaseFeeSearchCondition_PageSize").val(40);

        invoice.Application.List();
    });

    $("#btnInvPendingSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        invoice.Processor.List.PendingList();
    });

    $("#btnInvInvoicedSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        invoice.Processor.List.InvoicedList();
    });

    $("#btnInvoiceAuditSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        if ($("#SearchCondition_InvoiceStatus").val() == 'P') {
            invoice.Auditor.List.PendingList();
        }
        else if ($("#SearchCondition_InvoiceStatus").val() == 'A') {
            invoice.Auditor.List.ApprovedList();
        }
        else if ($("#SearchCondition_InvoiceStatus").val() == 'R') {
            invoice.Auditor.List.RejectedList();
        }
    });

    $("#btnInvoiceListSearch").click(function() {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        invoice.Application.InvoiceList();

    });

    $("#CaseFeeSearchCondition_CasePhaseName").die().live("click", function () {
        var tirgger = this;
        var html = $.casePhase.getCasePhaseCheckBoxListHtml();
        $(".divcaseconditioncasephases").html(html);
        $("#hidCasePhaseId").val("SearchCondition_CasePhaseId");
        $("#hidCasePhaseName").val($(tirgger).attr("id"));
        $("#divCasePhaseCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 15,
            "top": $(tirgger).position().top + 110
        }).toggle();

        return false;
    });

    $("#btnInvoiceCancel,#btnInvoiceClose").die().live("click", function () {
        invoice.Application.Close();
    });

    $("#btnInvoiceCreate").die().live("click", function () {
        invoice.Application.Create();
    });

    $("#btnInvoiceViewCancel,#btnInvoiceViewClose").die().live("click", function () {
        invoice.Processor.Close();
    });

    $("#btnInvoiceViewCreate").die().live("click", function () {
        invoice.Processor.Confirm.Open();
    });

    $("#btnInvoiceViewEdit").die().live("click", function () {
        invoice.Application.Edit();
    });

    $("#btnInvoiceConfirmCancel,#btnInvoiceConfirmClose").die().live("click", function () {
        invoice.Processor.Confirm.Close();
    });
    
    $("#btnInvoiceConfirmCreate").die().live("click", function () {
        invoice.Processor.Create();
    });

    $("#btnInvoiceConfirmCancel,#btnInvoiceConfirmClose").die().live("click", function () {
        invoice.Processor.Confirm.Close();
    });

    $("#btnInvoiceViewAudit").click(function () {
        invoice.Auditor.Audit.Open();
    });

    $("#btnInvoiceAuditApproved").die().live("click", function () {
        invoice.Auditor.Audit.Approved();
    });

    $("#btnInvoiceAuditRejected").die().live("click", function () {
        invoice.Auditor.Audit.Rejected();
    });

    $("#btnInvoiceAuditCancel,#btnInvoiceAuditClose").die().live("click", function () {
        invoice.Auditor.Audit.Close();
    });

    $("#btnInvoiceAuditListCancel,#btnInvoiceAuditListClose").die().live("click", function () {
        invoice.Auditor.Audit.ViewAuditClose();
    });

    $("#btnInvoiceApply").die().live("click", function () {
        invoice.Application.Open();
    });

    $("#divCasePhaseCheckBoxList").find("li").die().live("click", function (e) {

        if ($(e.target).is("lable")) {
            e.stopPropagation();
            return false;
        }

        var currentSelectedControl = $("#hidCasePhaseName").val();
        var currentSelectedIdControl = $("#hidCasePhaseId").val();

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

        var casePhaseNames = '';
        var casePhaseIds = '';

        $("#divCasePhaseCheckBoxList").find("input:checkbox").each(function () {
            if ($(this).attr("checked") == 'checked') {
                casePhaseNames += $(this).attr("casephasename") + ",";
                casePhaseIds += $(this).attr("casephaseid") + ",";
            }
        });

        $("#" + currentSelectedControl).val(casePhaseNames.substring(0, casePhaseNames.length - 1));
        $("#" + currentSelectedIdControl).val(casePhaseIds.substring(0, casePhaseIds.length - 1));

        e.stopPropagation();

        return true;
    });

    $("#flInvoiceFile").die().live("change", function () {
        $("#txtInvoiceFilePath").val($("#flInvoiceFile").val());
    });

    $("#divCaseFeeTypeCheckBoxList").find("li").die().live("click", function (e) {

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
            if ($(this).attr("checked") == 'checked') {
                caseFeeTypeNames += $(this).attr("casefeetypename") + ",";
                caseFeeTypeIds += $(this).attr("casefeetypeid") + ",";
            }
        });

        $("#" + currentSelectedControl).val(caseFeeTypeNames.substring(0, caseFeeTypeNames.length - 1));
        $("#" + currentSelectedIdControl).val(caseFeeTypeIds.substring(0, caseFeeTypeIds.length - 1));

        e.stopPropagation();

        return true;
    });

    $("#CaseFeeSearchCondition_CaseFeeTypeName").die().live("click", function () {
        var tirgger = this;
        var html = $.caseFeeType.getCaseFeeTypeCheckBoxListHtml();
        $(".divcaseconditioncasefeetypes").html(html);
        $("#hidCaseFeeTypeId").val("CaseFeeSearchCondition_CaseFeeTypeId");
        $("#hidCaseFeeTypeName").val($(tirgger).attr("id"));
        $("#divCaseFeeTypeCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 15,
            "top": $(tirgger).position().top + 110
        }).toggle();

        return false;
    });

    $("#divCaseTypeCheckBoxList").find("li").die().live("click", function (e) {

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
            if ($(this).attr("checked") == 'checked') {
                caseTypeNames += $(this).attr("casetypename") + ",";
                caseTypeIds += $(this).attr("casetypeid") + ",";
            }
        });

        $("#" + currentSelectedControl).val(caseTypeNames.substring(0, caseTypeNames.length - 1));
        $("#" + currentSelectedIdControl).val(caseTypeIds.substring(0, caseTypeIds.length - 1));

        e.stopPropagation();

        return true;
    });

    $("#CaseFeeSearchCondition_CaseTypeName").die().live("click", function () {
        var tirgger = this;
        var html = $.caseType.getCaseTypeCheckBoxListHtml();
        $(".divcaseconditioncasetypes").html(html);
        $("#hidCaseTypeId").val("CaseFeeSearchCondition_CaseTypeId");
        $("#hidCaseTypeName").val($(tirgger).attr("id"));
        $("#divCaseTypeCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 15,
            "top": $(tirgger).position().top + 110
        }).toggle();

        return false;
    });

    $("#item_InvoiceAmount").die().live("blur", function () {

        var totalInvoiceAmount = 0;
        var casetypeid = $(this).attr("casetypeid");
        var invoicedAmount = $(this).attr("invoicedamount");
        var casefeeamount = $(this).attr("casefeeamount");
        var itemFalseAmount = $(this).parents("tr").find("#item_FalseAmount");

        var falseAmount = parseFloat(invoicedAmount) + parseFloat($(this).val()) - parseFloat(casefeeamount);
        if (falseAmount > 0) {
            $(itemFalseAmount).text(falseAmount); 
            $(itemFalseAmount).attr("style","color:red");
        } else {
            $(itemFalseAmount).text(0); 
            $(itemFalseAmount).removeAttr("style");
        }

        $("#tblInvoiceCaseFeeList>tbody>tr").each(function (j, e) {
            if ($(e).find("#item_InvoiceAmount").attr("casetypeid") == casetypeid) {
                totalInvoiceAmount += $(e).find("#item_InvoiceAmount").val() == '' ? 0 : parseFloat($(e).find("#item_InvoiceAmount").val());
            }
        });

        $("#caseType_" + $(this).attr("casetypeid")).text(totalInvoiceAmount);

        return false;
    });

    $("#btnInvoiceFileListCancel,#btnInvoiceFileListClose").die().live("click", function () {
        invoice.File.Close();
    });
    
});




