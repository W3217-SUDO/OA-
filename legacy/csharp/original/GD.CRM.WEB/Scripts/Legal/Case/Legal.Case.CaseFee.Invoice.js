var caseFee = {
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
                    $(".info_inall.layoutfix").show();
                    
                    $.each(response.Data.CaseFeeList, function(i, c) {
                        
                        $("tbody", "#tblCaseFeeList").addRow(
                            "<input type='checkbox' name='chkCaseFeeId' customerid='" + + c.CustomerId + "' value='" + c.CaseFeeId + "'>",
                            "<a href='javascript:void(0)' onclick='javascript:caseFee.Open(\"" + c.CaseNo + "\")'>" + c.CaseNo + "</a>",
                            c.CaseRequestNo,
                            c.CustomerName,
                            c.CaseFeeTypeName,
                            c.Amount == null ? 0 : c.Amount,
                            c.RequestUserName,
                            c.InformDate == null ? '' : getDate(convertJsonDateToJSDate(c.InformDate)),
                            c.CashedAmount == null ? 0 : c.CashedAmount,
                            c.PaidAmount == null ? 0 : c.PaidAmount,
                            c.InvoicedAmount == null ? 0 : c.InvoicedAmount);
                    });

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

    Selected: function(e) {

        if ($(e).prop("checked") == true) {
            $.checkbox.all("chkCaseFeeId");
        } else {
            $.checkbox.not("chkCaseFeeId");
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

            //if (customerIds.length > 1) {
            //    $.showModalMessageBox("客户不一致.");
            //    return false;
            //}

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
        $("#divCaseFeeTypeCheckBoxList").off().hide();
        $("#divUserList").off().hide();
    });

    $(document).off('click', '#chkCaseFeeAll').on('click', '#chkCaseFeeAll', function () {
        caseFee.Selected(this);
    });

    $(document).off('click', '#btnSearch').on('click', '#btnSearch', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(100);

        caseFee.List();
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

});


