var internalFee = {

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
        $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/InternalFeeList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblInternalFeeList").clearRow();
                if (response.Data.TotalItemCount > 0) {

                    var totalItemAmount = 0;
                    $(".info_inall.layoutfix").show();
                    $("tbody", "#tblInternalFeeList").addRow(
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
                         "",
                         ""
                     );


                    $.each(response.Data.InternalFeeList, function (i, c) {

                        totalItemAmount += c.Amount;

                        $("tbody", "#tblInternalFeeList").addRow(
                            "<input type='checkbox' name='chkInternalFeeId'  value='" + c.InternalFeeId + "'>",
                            "<a href='javascript:void(0)' onclick='javascript:internalFee.Open(\"" + c.CaseNo + "\")'>" + c.CaseNo + "</a>",
                            c.Parent.Basic.CustomerName,
                            c.Parent.Basic.CaseLawyerName,
                            c.Parent.Basic.CaseAssistantName,
                            c.Parent.Basic.BusinessOwnerName,
                            c.Parent.Basic.InvestigatorName,
                            c.ActualPaidDate == null ? '' : getDate(convertJsonDateToJSDate(c.ActualPaidDate)),
                            c.FeeTypeName,
                            c.Amount == null ? 0 : c.Amount,
                            c.PaymentObjectName,
                            (c.ActualPaidAmount == c.Amount) ? "已付" : "未付"
                        );
                    });

                    $("tbody", "#tblInternalFeeList").addRow(
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
                     "",
                     ""
                    );


                    $("tfoot", "#tblInternalFeeList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.internalFeeList").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: internalFee.List,
                        callBackArgs: null
                    });

                } else {
                    $("tfoot", "#tblInternalFeeList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    Selected: function(e) {

        if ($(e).prop("checked") == true) {
            $.checkbox.all("chkInternalFeeId");
        } else {
            $.checkbox.not("chkInternalFeeId");
        }
    },

    ExportAllToExcel: function () {

        $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/InternalFeeListAllExportToExcel", function (response) {
            if (response.IsSuccess) {
                window.open(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/InternalFeeListExportToExcelDownload?fileName=" + response.Data);
                $.showModalMessageBox("导出成功.");
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    ExportSelectedToExcel: function () {

        var internalFeeIds = [];
        $("input[name='chkInternalFeeId']:checked").each(
            function (i) { internalFeeIds[i] = $(this).val(); }
        );

        if (internalFeeIds.length < 1) {
            $.showModalMessageBox("请选择需要导出的费用.");
            return false;
        }

        var data = {
            internalFeeIds: internalFeeIds,
        };
        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/InternalFeeListSelectedExportToExcel", data, function (response) {
            if (response.IsSuccess) {
                window.open(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/InternalFeeListExportToExcelDownload?fileName=" + response.Data);
                $.showModalMessageBox("导出成功.");
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    InvoiceFile:
    {
        /*批量导入open*/
        Open: function () {

            var internalFeeIds = $.checkbox.vals("chkCaseFeeId");
            if (internalFeeIds.length == 0) {
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
                internalFeeIds: internalFeeIds,
            };
 

            var url = AP_ROOT + AP_PAGE_ID + "/Legal/InvoiceFile/CaseFeeInvoiceConfirm";
            $.openLoading();

            $("<div></div>").load(url, data, function(result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#internalFeeInvoiceConfirmModal').modal({ backdrop: 'static', keyboard: false });
                $('#internalFeeInvoiceConfirmModal').on('hidden.bs.modal', function () {
                    $("#internalFeeInvoiceConfirmModal").remove();
                });
            });
        },

        /*批量导入关闭*/
        Close: function() {
            $('#internalFeeInvoiceConfirmModal').modal('hide');
        },

        /*批量导入*/
        Confirm: function () {

            var internalFeeIds = $.checkbox.vals("chkCaseFeeId");
            if (internalFeeIds.length == 0) {
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

            $("#internalFeeListIds").val(internalFeeIds.join(","));
              

            $('#internalFeeInvoiceConfirm').ajaxSubmit({
                success: function(response) {
                    $.closeLoading();
                    if (response.IsSuccess) {
                        $.showModalMessageBox("票据确认成功.");
                        $('#internalFeeInvoiceConfirmModal').modal('hide');
                        internalFee.List();
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
        $("#divCaseFeeTypeCheckBoxList").off().hide();
        $("#divUserList").off().hide();
    });

    $(document).off('click', '#chkInternalFeeAll').on('click', '#chkInternalFeeAll', function () {
        internalFee.Selected(this);
    });

    $(document).off('click', '#btnSearch').on('click', '#btnSearch', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(15);

        internalFee.List();
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
        internalFee.InvoiceFile.Close();
    });

    $(document).off('click', '#btnCaseFeeInvoiceConfirmCreate').on('click', '#btnCaseFeeInvoiceConfirmCreate', function () {
        internalFee.InvoiceFile.Confirm();
    });

    $(document).off('click', '#btnCaseFeeInvoiceConfirm').on('click', '#btnCaseFeeInvoiceConfirm', function () {
        internalFee.InvoiceFile.Open();
    });

    $(document).off('click', '#flInvoiceFile').on('change', '#flInvoiceFile', function () {
         $("#txtInvoiceFilePath").val($("#flInvoiceFile").val());
    });

    $(document).off('click', '#SearchCondition_CasePhaseName').on('click', '#SearchCondition_CasePhaseName', function () {
        var tirgger = this;
        var html = $.lsCasePhase.getCasePhaseCheckBoxListHtml();
        $(".divcaseconditioncasephases").html(html);
        $("#hidCasePhaseId").val("SearchCondition_CasePhaseId");
        $("#hidCasePhaseName").val("SearchCondition_CasePhaseName");

        $("#divCasePhaseCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left + 16,
            "top": $(tirgger).parent().position().top + 25,
            "z-index": 9999
        }).toggle();

        return false;
    });

    $(document).off('click', '#divCasePhaseCheckBoxList ul li').on('click', '#divCasePhaseCheckBoxList ul li', function (e) {

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
            if ($(this).prop("checked") == true) {
                casePhaseNames += $(this).attr("casephasename") + ",";
                casePhaseIds += $(this).attr("casephaseid") + ",";
            }
        });

        $("#" + currentSelectedControl).val(casePhaseNames.substring(0, casePhaseNames.length - 1));
        $("#" + currentSelectedIdControl).val(casePhaseIds.substring(0, casePhaseIds.length - 1));

        e.stopPropagation();

        return true;
    });

    $(document).off('click', '#SearchCondition_CaseTypeName').on('click', '#SearchCondition_CaseTypeName', function () {
        var tirgger = this;
        var html = $.lsCaseType.getCaseTypeCheckBoxListHtml();
        $(".divcaseconditioncasetypes").html(html);
        $("#hidCaseTypeId").val("SearchCondition_CaseTypeId");
        $("#hidCaseTypeName").val($(tirgger).attr("id"));
        $("#divCaseTypeCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left + 16,
            "top": $(tirgger).parent().position().top + 25,
            "z-index": 9999
        }).toggle();

        return false;
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

    $(document).off('click', '#SearchCondition_FeeTypeName').on('click', '#SearchCondition_FeeTypeName', function () {
          var tirgger = this;
          var html = $.lsCaseFeeType.getCaseInternalFeeTypeCheckBoxListHtml();
        $(".divcaseconditioncasefeetypes").html(html);
        $("#hidCaseFeeTypeId").val("SearchCondition_FeeTypeId");
        $("#hidCaseFeeTypeName").val($(tirgger).attr("id"));
        $("#divCaseFeeTypeCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left + 16,
            "top": $(tirgger).parent().position().top + 25,
            "z-index": 9999
        }).toggle();

        return false;
    });

    $(document).off('click', '#btnSearchClear').on('click', '#btnSearchClear', function () {
        $("#SearchCondition_CustomerName").val('');
        $("#SearchCondition_ContractNo").val('');
        $("#SearchCondition_CaseNo").val('');
        $("#SearchCondition_CaseTypeName").val('');
        $("#SearchCondition_CaseTypeId").val('');
        $("#SearchCondition_CasePhaseName").val('');
        $("#SearchCondition_CasePhaseId").val('');
        $("#SearchCondition_FeeTypeName").val('');
        $("#SearchCondition_FeeTypeId").val('');
    });

    $(document).off('click', '#btnInternalFeeExportAll').on('click', '#btnInternalFeeExportAll', function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(2000);
        internalFee.ExportAllToExcel();
    });

    $(document).off('click', '#btnInternalFeeExportSelected').on('click', '#btnInternalFeeExportSelected', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);
        internalFee.ExportSelectedToExcel();
    });

    internalFee.ResetSize();

    $(window).resize(function () {
        internalFee.ResetSize();
    });


});


