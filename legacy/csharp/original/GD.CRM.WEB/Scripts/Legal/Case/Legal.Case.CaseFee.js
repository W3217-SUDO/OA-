var caseFee = {
    ResetSize: function () {
        if ($("#divList").length > 0) {
            $("#divList").css("height", $(window).height() - $("#divList").offset().top - 12);
        }
    },
    Open: function(caseNo) {
        var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + caseNo;
        addtabs(url, caseNo);
       //window.open(url);
    },
    List: function () {
        $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/AR/CaseFeeList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseFeeList").clearRow();
                if (response.Data.TotalItemCount > 0) {

                    var totalItemAmount = 0;
                    var totalItemCashedAmount = 0;

                    $(".info_inall.layoutfix").show();
                    $("tbody", "#tblCaseFeeList").addRow(
                         "",
                         "",
                         "",
                         "",
                         "",
                         "",
                         "",
                         "",
                         "",
                         response.Data.TotalAmount.toFixed(2),
                         "",
                         "",
                         response.Data.TotalCashedAmount.toFixed(2),
                         ""
                     );


                    $.each(response.Data.CaseFeeList, function (i, c) {

                        totalItemAmount += c.Amount;
                        totalItemCashedAmount += c.CashedAmount;

                        $("tbody", "#tblCaseFeeList").addRow(
                            "<input type='checkbox' name='chkCaseFeeId' customerid='" + + c.CustomerId + "' value='" + c.CaseFeeId + "'>",
                            "<a href='javascript:void(0)' onclick='javascript:caseFee.Open(\"" + c.CaseNo + "\")'>" + c.CaseNo + "</a>",
                            c.CustomerName,
                            c.Parent.Basic.CourtLawyerName,
                            c.Parent.Basic.CaseAssistantName,
                            c.Parent.Basic.BusinessOwnerName,
                            c.Parent.Basic.CoordinatorName,
                            c.Parent.Basic.InvestigatorName,
                            c.CaseFeeTypeName,
                            c.Amount == null ? 0 : c.Amount,
                            c.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.CashedDate)),
                            c.ReceivedPayerName,
                            c.CashedAmount == null ? 0 : c.CashedAmount,
                            c.ContractNo
                        );
                    });

                    $("tbody", "#tblCaseFeeList").addRow(
                     "",
                     "",
                     "",
                     "",
                     "",
                     "",
                     "",
                     "",
                     "",
                     totalItemAmount.toFixed(2),
                     "",
                     "",
                     totalItemCashedAmount.toFixed(2),
                     ""
                    );


                    $("tfoot", "#tblCaseFeeList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.caseFeeList").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: caseFee.List,
                        callBackArgs: null
                    });

                } else {
                    $("tfoot", "#tblCaseFeeList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },
    CaseFeeList: function () {
        $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/CaseFee/CaseFeeList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseFeeList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    if (response.Data.CaseFeeList.length > 10) {
                        $(".divdropdown").removeClass("dropdown");
                        $(".divdropdown").addClass("dropup");
                    }
                    else {
                        $(".divdropdown").removeClass("dropup");
                        $(".divdropdown").addClass("dropdown");
                    }
                    var totalItemAmount = 0;
                    var totalItemCashedAmount = 0;
                    var totalItemPaidAmount = 0;
                    var totalRefundAmount = 0;
                    var totalRefundedAmount = 0;
                    $(".info_inall.layoutfix").show();
                    $("tbody", "#tblCaseFeeList").addRow(
                         "",
                         "",
                         "",
                         "",
                         "",
                         "",
                         "",
                         "",
                         response.Data.TotalAmount.toFixed(2),
                         response.Data.TotalRefundAmount.toFixed(2),
                         response.Data.TotalRefundedAmount.toFixed(2),
                         "",
                         response.Data.TotalCashedAmount.toFixed(2),
                         "",
                         response.Data.TotalPaidAmount.toFixed(2),
                         "",
                         "",
                         ""
                     );
                    $.each(response.Data.CaseFeeList, function (i, c) {
                        totalItemAmount += c.Amount;
                        totalItemCashedAmount += c.CashedAmount;
                        totalItemPaidAmount += c.PaidAmount;
                        totalRefundAmount += c.RefundAmount;
                        totalRefundedAmount += c.RefundedAmount;
                        $("tbody", "#tblCaseFeeList").addRow(
                            "<input type='checkbox' name='chkCaseId' customerid='" + c.CustomerId + "' caseFeeId='" + c.CaseFeeId + "' value='" + c.CaseNo + "'>",
                            "<a href='javascript:void(0)' onclick='javascript:caseFee.Open(\"" + c.CaseNo + "\")'>" + c.CaseNo + "</a>",
                            c.CustomerName,
                            c.Parent.Basic.CasePhaseName,
                            c.Parent.Basic.CaseAssistantName,
                            c.Parent.Basic.CourtLawyerName,
                            c.Parent.Basic.OfficialNo,
                            c.CaseFeeTypeName,
                            c.Amount == null ? 0 : c.Amount.toFixed(2),
                            (c.RefundAmount == null ? 0 : c.RefundAmount).toFixed(2),
                            (c.RefundedAmount == null ? 0 : c.RefundedAmount).toFixed(2),
                            c.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.CashedDate)),
                            c.CashedAmount == null ? 0 : c.CashedAmount.toFixed(2),
                            c.PaidDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaidDate)),
                            c.PaidAmount == null ? 0 : c.PaidAmount.toFixed(2),
                            c.Parent.Basic.OfficialCourtName,
                            c.PaymentStatusName,
                            c.ContractNo
                        );
                    });
                    $("tbody", "#tblCaseFeeList").addRow(
                     "",
                     "",
                     "",
                     "",
                     "",
                     "",
                     "",
                     "",
                     totalItemAmount.toFixed(2),
                     totalRefundAmount.toFixed(2),
                     totalRefundedAmount.toFixed(2),
                     "",
                     totalItemCashedAmount.toFixed(2),
                     "",
                     totalItemPaidAmount.toFixed(2),
                     "",
                     "",
                     ""
                    );
                    $("tfoot", "#tblCaseFeeList").show();
                    $(".simple-grid-none-data-wrap").hide();
                    $(".pull-right.page-box.caseFeeList").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: caseFee.CaseFeeList,
                        callBackArgs: null
                    });
                } else {
                    $("tfoot", "#tblCaseFeeList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },
    PendingSettlementCaseFeeList: function () {
        $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/CaseFee/CaseFeeList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseFeeList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    if (response.Data.CaseFeeList.length > 10) {
                        $(".divdropdown").removeClass("dropdown");
                        $(".divdropdown").addClass("dropup");
                    }
                    else {
                        $(".divdropdown").removeClass("dropup");
                        $(".divdropdown").addClass("dropdown");
                    }
                    var totalItemAmount = 0;
                    var totalItemCashedAmount = 0;
                    var totalItemPaidAmount = 0;
                    var totalRefundAmount = 0;
                    var totalRefundedAmount = 0;
                    $(".info_inall.layoutfix").show();
                    //$("tbody", "#tblCaseFeeList").addRow(
                    //     "",
                    //     "",
                    //     "",
                    //     "",
                    //     "",
                    //     "",
                    //     "",
                    //     "",
                    //     "",
                    //     response.Data.TotalAmount.toFixed(2),
                    //     "",
                    //     response.Data.TotalCashedAmount.toFixed(2),
                    //     "",
                    //     "",
                    //     ""
                    // );
                    $.each(response.Data.CaseFeeList, function (i, c) {
                        totalItemAmount += c.Amount;
                        totalItemCashedAmount += c.CashedAmount;
                        totalItemPaidAmount += c.PaidAmount;
                        totalRefundAmount += c.RefundAmount;
                        totalRefundedAmount += c.RefundedAmount;
                        $("tbody", "#tblCaseFeeList").addRow(
                            "<input type='checkbox' name='chkCaseId' customerid='" + c.CustomerId + "' caseFeeId='" + c.CaseFeeId + "' value='" + c.CaseNo + "'>",
                            "<a href='javascript:void(0)' onclick='javascript:caseFee.Open(\"" + c.CaseNo + "\")'>" + c.CaseNo + "</a>",
                            c.Parent.Basic.AppellantNames,
                            c.Parent.Basic.AppelleeNames,
                            c.Amount == null ? 0 : c.Amount.toFixed(2),
                            c.ReceivedPayerName,
                            c.ReceivedPaymentAmount == null ? 0 : c.ReceivedPaymentAmount.toFixed(2),
                            c.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.CashedDate)),
                            c.ReceivedPaymentSettlementStatusName,
                            c.Parent.Basic.CasePhaseName,
                            c.Parent.Basic.BusinessOwnerName,
                            c.Parent.Basic.CourtLawyerName,
                            c.Parent.Basic.CaseAssistantName,
                            c.Parent.Basic.InvestigatorName,
                            c.Parent.Basic.CoordinatorName
                        );
                    });
                    //$("tbody", "#tblCaseFeeList").addRow(
                    // "",
                    // "",
                    // "",
                    // "",
                    // "",
                    // "",
                    // "",
                    // "",
                    // "",
                    // totalItemAmount.toFixed(2),
                    // "",
                    // totalItemCashedAmount.toFixed(2),
                    // "",
                    // "",
                    // ""
                    //);
                    $("tfoot", "#tblCaseFeeList").show();
                    $(".simple-grid-none-data-wrap").hide();
                    $(".pull-right.page-box.caseFeeList").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: caseFee.PendingSettlementCaseFeeList,
                        callBackArgs: null
                    });
                } else {
                    $("tfoot", "#tblCaseFeeList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },
    RefundList: function () {
        $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/CaseFee/CaseFeeList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseFeeList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    if (response.Data.CaseFeeList.length > 10) {
                        $(".divdropdown").removeClass("dropdown");
                        $(".divdropdown").addClass("dropup");
                    }
                    else {
                        $(".divdropdown").removeClass("dropup");
                        $(".divdropdown").addClass("dropdown");
                    }
                    var totalItemAmount = 0;
                    var totalItemCashedAmount = 0;
                    var totalItemPaidAmount = 0;
                    var totalRefundAmount = 0;
                    var totalRefundedAmount = 0;
                    $(".info_inall.layoutfix").show();
                    $("tbody", "#tblCaseFeeList").addRow(
                         "",
                         "",
                         "",
                         "",
                         "",
                         "",
                         "",
                         "",
                         response.Data.TotalAmount.toFixed(2),
                         response.Data.TotalRefundAmount.toFixed(2),
                         "",
                         "",
                         "",
                         "",
                         "",
                         ""
                     );
                    $.each(response.Data.CaseFeeList, function (i, c) {
                        totalItemAmount += c.Amount;
                        totalItemCashedAmount += c.CashedAmount;
                        totalItemPaidAmount += c.PaidAmount;
                        totalRefundAmount += c.RefundAmount;
                        totalRefundedAmount += c.RefundedAmount;

                        var courtName = '';
                        if (c.CaseFeeTypeId == 11010020) {
                            courtName = c.Parent.Basic.FirstIntanceCourtName;
                        }
                        else if (c.CaseFeeTypeId == 11010030) {
                            courtName = c.Parent.Basic.SecondIntanceCourtName;
                        }
                        else if (c.CaseFeeTypeId == 11010040) {
                            courtName = c.Parent.Basic.LastIntanceCourtName;
                        }
                        else {
                            courtName = c.Parent.Basic.OfficialCourtName;
                        }
                        $("tbody", "#tblCaseFeeList").addRow(
                            "<input type='checkbox' name='chkCaseId' customerid='" + c.CustomerId + "' caseFeeId='" + c.CaseFeeId + "' value='" + c.CaseNo + "'>",
                            "<a href='javascript:void(0)' onclick='javascript:c.Cases.Case.View(\"" + c.CaseNo + "\")'>" + c.CaseNo + "</a>",
                            c.Parent.Basic.AppellantNames,
                            c.Parent.Basic.AppelleeNames,
                            c.Parent.Basic.CasePhaseName,
                            c.Parent.Basic.CaseAssistantName,
                            c.Parent.Basic.CourtLawyerName,
                            c.CaseFeeTypeName,
                            c.Amount == null ? 0 : c.Amount.toFixed(2),
                            (c.RefundAmount == null ? 0 : c.RefundAmount).toFixed(2),
                            c.RefundCreateTime == null ? '' : getDate(convertJsonDateToJSDate(c.RefundCreateTime)),
                            courtName,
                            c.RefundStatusName,
                            c.RefundGapDays,
                            "<a href='javascript:void(0)' onclick='javascript:c.Cases.Case.CaseLogs.LogList(\"" + c.CaseNo + "\")'>日志</a>"
                        );
                    });
                    $("tbody", "#tblCaseFeeList").addRow(
                     "",
                     "",
                     "",
                     "",
                     "",
                     "",
                     "",
                     "",
                     totalItemAmount.toFixed(2),
                     totalRefundAmount.toFixed(2),
                     "",
                     "",
                     "",
                     "",
                     "",
                     "",
                     ""
                    );
                    $("tfoot", "#tblCaseFeeList").show();
                    $(".simple-grid-none-data-wrap").hide();
                    $(".pull-right.page-box.caseFeeList").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: caseFee.RefundList,
                        callBackArgs: null
                    });
                } else {
                    $("tfoot", "#tblCaseFeeList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },
    ExportAllToExcel: function () {

        $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/CaseFee/CaseFeeListAllExportToExcel", function (response) {
            if (response.IsSuccess) {
                window.open(AP_ROOT + AP_PAGE_ID + "/FAM/CaseFee/CaseFeeListExportToExcelDownload?fileName=" + response.Data);
                $.showModalMessageBox("导出成功.");
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },
    ExportSelectedToExcel: function () {

        var caseFeeIds = [];
        $("input[name='chkCaseId']:checked").each(
            function (i) { caseFeeIds[i] = $(this).attr("caseFeeId"); }
        );

        if (caseFeeIds.length < 1) {
            $.showModalMessageBox("请选择需要导出的费用.");
            return false;
        }

        var data = {
            caseFeeIds: caseFeeIds,
        };
        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/CaseFee/CaseFeeListSelectedExportToExcel", data, function (response) {
            if (response.IsSuccess) {
                window.open(AP_ROOT + AP_PAGE_ID + "/FAM/CaseFee/CaseFeeListExportToExcelDownload?fileName=" + response.Data);
                $.showModalMessageBox("导出成功.");
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    Settlemented: function () {
        var caseFeeIds = [];
        $("input[name='chkCaseId']:checked").each(
            function (i) { caseFeeIds[i] = $(this).attr("caseFeeId"); }
        );
        if (caseFeeIds.length < 1) {
            $.showModalMessageBox("请选择案件费用.");
            return false;
        }
        var data = {
            caseFeeIds: caseFeeIds,
        };
        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/CaseFee/CaseFeeListSelectedSettlemented", data, function (response) {
            if (response.IsSuccess) {
                caseFee.PendingSettlementCaseFeeList();
                $.showModalMessageBox("标识成功.");
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    Selected: function(e) {

        if ($(e).prop("checked") == true) {
            $.checkbox.all("chkCaseId");
        } else {
            $.checkbox.not("chkCaseId");
        }
    },
    InvoiceFile:
    {
        /*批量导入open*/
        Open: function () {

            var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
            if (caseFeeIds.length == 0) {
                $.showModalMessageBox("请选择费用记录.");
                return false;
            }

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
                $.showModalMessageBox("客户不一致.");
                return false;
            }

            var data =
            {
                caseFeeIds: caseFeeIds,
            };
 

            var url = AP_ROOT + AP_PAGE_ID + "/Legal/InvoiceFile/CaseFeeInvoiceConfirm";
            $.openLoading();

            $("<div></div>").load(url, data, function(result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseFeeInvoiceConfirmModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseFeeInvoiceConfirmModal').on('hidden.bs.modal', function () {
                    $("#caseFeeInvoiceConfirmModal").remove();
                });
            });
        },
        /*批量导入关闭*/
        Close: function() {
            $('#caseFeeInvoiceConfirmModal').modal('hide');
        },
        /*批量导入*/
        Confirm: function () {

            var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
            if (caseFeeIds.length == 0) {
                $.showModalMessageBox("请选择费用记录.");
                return false;
            }


            if ($("#Invoice_InvoiceNo").val() == '') {
                $.showModalMessageBox("请输入票据编号.");
                return false;
            }

            if ($("#Invoice_InvoiceDate").val() == '') {
                $.showModalMessageBox("请输入票据日期.");
                return false;
            }

            if ($("#flInvoiceFile").val() == '') {
                $.showModalMessageBox("请选择上传文件.");
                return false;
            }

            $.openLoading();

            $("#caseFeeListIds").val(caseFeeIds.join(","));
              

            $('#caseFeeInvoiceConfirm').ajaxSubmit({
                success: function(response) {
                    $.closeLoading();
                    if (response.IsSuccess) {
                        $.showModalMessageBox("票据确认成功.");
                        $('#caseFeeInvoiceConfirmModal').modal('hide');
                        caseFee.List();
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                }
            });
        },
    },
}

$(document).ready(function () {
    $(document).click(function (e) {
        $("#divCasePhaseCheckBoxList").off().hide();
        $("#divCaseTypeCheckBoxList").off().hide();
        //$("#divCaseFeeTypeCheckBoxList").off().hide();
        $("#divUserList").off().hide();
    });
    $(document).off('click', '#chkCaseAll').on('click', '#chkCaseAll', function () {
        caseFee.Selected(this);
    });
    $(document).off('click', '#btnSearch').on('click', '#btnSearch', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(15);

        caseFee.List();
    });

    $(document).off('click', '#btnRefundCaseFeeSearch').on('click', '#btnRefundCaseFeeSearch', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(15);
        caseFee.RefundList();
    });
    $("#divUsers").find("li").off().on("click", function () {
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        var currentSelectedControl = $("#hidUserName").val();
        var currentSelectedIdControl = $("#hidUserId").val();
        $("#" + currentSelectedControl).val(userName);
        $("#" + currentSelectedIdControl).val(userId);
        $("#divUsers").hide();
    });
    $(document).off('click', '#btnCaseFeeInvoiceConfirmCancel,#btnCaseFeeInvoiceConfirmClose').on('click', '#btnCaseFeeInvoiceConfirmCancel,#btnCaseFeeInvoiceConfirmClose', function () {
        caseFee.InvoiceFile.Close();
    });
    $(document).off('click', '#btnCaseFeeInvoiceConfirmCreate').on('click', '#btnCaseFeeInvoiceConfirmCreate', function () {
        caseFee.InvoiceFile.Confirm();
    });
    $(document).off('click', '#btnCaseFeeInvoiceConfirm').on('click', '#btnCaseFeeInvoiceConfirm', function () {
        caseFee.InvoiceFile.Open();
    });
    $(document).off('click', '#flInvoiceFile').on('change', '#flInvoiceFile', function () {
         $("#txtInvoiceFilePath").val($("#flInvoiceFile").val());
    });
    $(document).off('click', '#btnSearchClear').on('click', '#btnSearchClear', function () {
        $("#SearchCondition_CustomerName").val('');
        $("#SearchCondition_ContractNo").val('');
        $("#SearchCondition_CaseNo").val('');
        $("#SearchCondition_CaseTypeName").val('');
        $("#SearchCondition_CaseTypeId").val('');
        $("#SearchCondition_CasePhaseName").val('');
        $("#SearchCondition_CasePhaseId").val('');
        $("#SearchCondition_CaseFeeTypeName").val('');
        $("#SearchCondition_CaseFeeTypeId").val('');
    });
    $(document).off('click', '#btnCaseFeeExportSelected').on('click', '#btnCaseFeeExportSelected', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(200);

        caseFee.ExportSelectedToExcel();
    });
    $(document).off('click', '#btnCaseFeeExportAll').on('click', '#btnCaseFeeExportAll', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(200);

        caseFee.ExportAllToExcel();
    });
    caseFee.ResetSize();
    $(window).resize(function () {
        caseFee.ResetSize();
    });
});


