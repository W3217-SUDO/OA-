var caseInfo = {
    View: function (caseNo) {
        var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + caseNo;
        window.open(url);
    },
}

var caseFee = {
    ReceiptOcr: {

        List: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/InvoiceFile/GetCaseOfficeFeeMetaFileList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblCaseFeeList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.CaseFiles, function (i, f) {
                            $.each(f.Results, function (i, r) {
                                var tr = '';
                                if (r.MatchedCase != null) {
                                    tr = "<tr>"
                                        + "<td><input type='checkbox' Id='chkParentCaseId' name='chkParentCaseId' class='ng-pristine ng-valid' value='" + r.ApplicationNo  + "' ><span>" + r.ApplicationNo + "</span></td>"
                                        + "<td>" + r.MatchedCase.CaseBasicInfo.CaseNo + "</td>"
                                        + "<td>" + r.MatchedCase.CaseBasicInfo.CustomerName + "</td>"
                                        + "<td>" + r.InvoiceNo + "</td>"
                                        + "<td>" + r.InvoicedDate + "</td>"
                                        + "<td>" + r.WordResult + "</td>"
                                        + "<td></td>"
                                        + "<td></td>"
                                        + "<td rowsplan='2'>" + f.FileName + "</td>"
                                    + "</tr>";
                                }
                                else {
                                    tr = "<tr>"
                                        + "<td><input type='checkbox' Id='chkParentCaseId' name='chkParentCaseId' class='ng-pristine ng-valid' value='" + r.ApplicationNo + "'><span>" + r.ApplicationNo + "</span></td>"
                                        + "<td></td>"
                                        + "<td></td>"
                                        + "<td>" + r.InvoiceNo + "</td>"
                                        + "<td>" + r.InvoicedDate + "</td>"
                                        + "<td>" + r.WordResult + "</td>"
                                        + "<td></td>"
                                        + "<td></td>"
                                        + "<td rowsplan='2'>" + f.FileName + "</td>"
                                    + "</tr>";
                                }

                                $('#tblCaseFeeList>tbody>tr:last').after(tr);

                                $.each(r.CaseFeeResults, function (j, cr) {

                                    if (cr.MatchedCaseFee != null) {

                                        var message = '';

                                        if (cr.Errors != null && cr.Errors.length > 0) {
                                            $.each(cr.Errors, function (m, err) {
                                                message += (m + 1) + ". " + err + "<br>";
                                            });
                                        }

                                        var tr = "<tr>"
                                                    + "<td><input type='checkbox' Id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' caseFeeId = " + cr.MatchedCaseFee.CaseFeeId + " value='" + r.ApplicationNo + "'>&nbsp;&nbsp;" + (j + 1) + "</td>"
                                                    + "<td colspan='4' style='color:red;text-align:left'>" + message + "</td>"
                                                    + "<td>" + cr.MatchedWords + "</td>"
                                                    + "<td>" + cr.MatchedCaseFee.CaseFeeTypeName + "</td>"
                                                    + "<td>" + cr.MatchedCaseFee.Amount + "</td>"
                                                    + "<td></td>"
                                               + "</tr>";

                                        $('#tblCaseFeeList>tbody>tr:last').after(tr);
                                    }
                                    else {

                                        var message = '';

                                        if (cr.Errors != null && cr.Errors.length > 0) {
                                            $.each(cr.Errors, function (m, err) {
                                                message += (m + 1) + ". " + err + "<br>";
                                            });
                                        }

                                        var tr = "<tr>"
                                                + "<td><input type='checkbox' Id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' caseFeeId='0' value='" + r.ApplicationNo + "'>&nbsp;&nbsp;" + (j + 1) + "</td>"
                                                + "<td colspan='4' style='color:red;text-align:left'>" + message + "</td>"
                                                + "<td>" + cr.MatchedWords + "</td>"
                                                + "<td></td>"
                                                + "<td></td>"
                                                + "<td></td>"
                                           + "</tr>";

                                        $('#tblCaseFeeList>tbody>tr:last').after(tr);
                                    }
                                });
                            });
                        });

                        $("tfoot", "#tblCaseFeeList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.caseFeeList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: caseFee.ReceiptOcr.List,
                            callBackArgs: null
                        });
                        //caseFileSearch.BindMenu();
                    } else {
                        $("tfoot", "#tblCaseFileList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },

        ListLayout: function (data) {
            $("tbody", "#tblCaseFeeList").clearRow();
            if (data.OcrInvoiceFiles.length > 0) {
                var j = 0;
                $.each(data.OcrInvoiceFiles, function (i, f) {
                    $.each(f.Results, function (i, r) {

                        var tr = '';
                        if (r.MatchedCase != null) {
                            tr = "<tr>"
                                + "<td><input type='checkbox' Id='chkParentCaseId' name='chkParentCaseId' class='ng-pristine ng-valid' ><span>" + r.ApplicationNo + "</span></td>"
                                + "<td>" + r.MatchedCase.CaseBasicInfo.CaseNo + "</td>"
                                + "<td>" + r.MatchedCase.CaseBasicInfo.CustomerName + "</td>"
                                + "<td>" + r.InvoiceNo + "</td>"
                                + "<td>" + r.InvoicedDate + "</td>"
                                + "<td>" + r.WordResult + "</td>"
                                + "<td></td>"
                                + "<td></td>"
                                + "<td rowsplan='2'>" + f.FileName + "</td>"
                            + "</tr>";
                        }
                        else {
                            tr = "<tr>"
                                + "<td><input type='checkbox' Id='chkParentCaseId' name='chkParentCaseId' class='ng-pristine ng-valid' ><span>" + r.ApplicationNo + "</span></td>"
                                + "<td></td>"
                                + "<td></td>"
                                + "<td>" + r.InvoiceNo + "</td>"
                                + "<td>" + r.InvoicedDate + "</td>"
                                + "<td>" + r.WordResult + "</td>"
                                + "<td></td>"
                                + "<td></td>"
                                + "<td rowsplan='2'>" + f.FileName + "</td>"
                            + "</tr>";
                        }

                        $('#tblCaseFeeList>tbody>tr:last').after(tr);

                        $.each(r.CaseFeeResults, function (j, cr) {

                            if (cr.MatchedCaseFee != null) {

                                var message = '';

                                if (cr.Errors != null && cr.Errors.length > 0) {
                                    $.each(cr.Errors, function (m, err) {
                                        message += (m + 1) + ". " + err + "<br>";
                                    });
                                }

                                var tr = "<tr>"
                                            + "<td><input type='checkbox' Id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' value='" + cr.CaseFeeId + "'>&nbsp;&nbsp;" + (j + 1) + "</td>"
                                            + "<td colspan='4' style='color:red;text-align:left'>" + message + "</td>"
                                            + "<td>" + cr.MatchedWords + "</td>"
                                            + "<td>" + cr.MatchedCaseFee.CaseFeeTypeName + "</td>"
                                            + "<td>" + cr.MatchedCaseFee.Amount + "</td>"
                                            + "<td></td>"
                                       + "</tr>";
 
                                $('#tblCaseFeeList>tbody>tr:last').after(tr);
                            }
                            else {

                                var message = '';

                                if (cr.Errors != null && cr.Errors.length > 0) {
                                    $.each(cr.Errors, function (m, err) {
                                        message += (m + 1) + ". " + err + "<br>";
                                    });
                                }

                                var tr = "<tr>"
                                        + "<td><input type='checkbox' Id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' >&nbsp;&nbsp;" + (j + 1) + "</td>"
                                        + "<td colspan='4' style='color:red;text-align:left'>" + message + "</td>"
                                        + "<td>" + cr.MatchedWords + "</td>"
                                        + "<td></td>"
                                        + "<td></td>"
                                        + "<td></td>"
                                   + "</tr>";

                                $('#tblCaseFeeList>tbody>tr:last').after(tr);
                            }
                        });
                    });
                });

            } else {
                $('#tblCaseFeeList>tbody>tr:last').after("<tr><td colspan='11'><span id='message'>文件不匹配上传规则，请确认上传文件正确.</span></td></tr>");
            }
        },
        Upload: function () {
            if ($("#flZip").val() == '') {
                $.showModalMessageBox("请选择上传的文件.");
                return false;
            }
            $("#uploadingForm").attr("action", AP_ROOT + AP_PAGE_ID + "/Legal/InvoiceFile/ReceiptOcrFileUpload");

            $.openLoading();

            $('#uploadingForm').ajaxSubmit({
                success: function (response) {

                    $.closeLoading();
                    if (response.IsSuccess) {
                        $.showModalMessageBox("上传成功.");
                        $("#SearchCondition_MetaFileGuid").val(response.Data);
                        caseFee.ReceiptOcr.List();
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                }
            });
            return true;
        },
        Import: function () {
            var caseIds = $.checkbox.vals("chkCaseId");
            if (caseIds.length == 0) {
                $.showModalMessageBox("请选择需要导入专利票据的费用.");
                return;
            }

            var selectedIds = new Array();
            var result = true;

            $("#tblCaseFeeList tbody tr").each(function (i, e) {
                if ($(e).css("display") != 'none') {
                    if ($(e).find("#chkCaseId").attr('checked') == 'checked') {
                        var caseFeeId = $(e).find("#chkCaseId").attr("casefeeid");
                        if (caseFeeId > 0) {
                            selectedIds.push(caseFeeId);
                        }
                    }
                }
            });

            var metaFileGuid = $("#SearchCondition_MetaFileGuid").val();

            var data =
            {
                metaFileGuid: metaFileGuid,
                selectedIds: selectedIds
            };

            if (result == true) {
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/InvoiceFile/ReceiptOcrFileImport", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("导入成功.");
                    }
                    else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            }
        },

        Selected: function (e) {

            var n = 'chkCaseId';
            if ($(e).prop("checked") == true) {

                $("input[name=" + n + "]").each(
                    function () {
                        if ($(this).val() == $(e).val()) {
                            $(this).attr("checked", "checked");
                        }
                    }
                );
            } else {
                $("input[name=" + n + "]").each(
                    function () {
                        if ($(this).val() == $(e).val()) {
                            $(this).removeAttr("checked");
                        }
                    }
                );
            }
        },

        SelectedAll: function (e) {
            if ($(e).prop("checked") == true) {
                $.checkbox.all("chkCaseId");
                $.checkbox.all("chkParentCaseId");
            } else {
                $.checkbox.not("chkCaseId");
                $.checkbox.not("chkParentCaseId");
            }
        },

        SelectedParent: function (e) {

            var n = 'chkParentCaseId';
            if ($(e).prop("checked") == true) {

                $("input[name=" + n + "]").each(
                    function () {
                        if ($(this).val() == $(e).val()) {
                            $(this).attr("checked", "checked");
                        }
                    }
                );
            } else {
                $("input[name=" + n + "]").each(
                    function () {
                        if ($(this).val() == $(e).val()) {
                            $(this).removeAttr("checked");
                        }
                    }
                );
            }
        },
    },

    Receipt: {
        List: function (data) {
            $("tbody", "#tblCaseFeeList").clearRow();
            if (data.length > 0) {
                var j = 0;
                $.each(data, function (i, c) {
                    if (!c.HasError) {
                        $("tbody", "#tblCaseFeeList").addRow(
                            "<input type='checkbox' Id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' value='" + c.CaseId + "'>",
                            "<span  id='CustomFileName' >" + c.CustomFileName + "</span><span id = 'CaseTypeId' style='display:none'>" + c.CaseTypeId + "</span><span style='display:none' id='CaseNo'>" + c.CaseNo + "</span><span id = 'CaseFeeId' style='display:none'>" + c.CaseFeeId + "</span>",
                            "<span id='CaseFeeStatus' >" + (c.CaseFeeStatus == "1" ? "已导入" : "未导入") + "</span>",
                            "<a href='javascript:void(0);' onclick='javascript:caseInfo.View(" + c.CaseId + ", " + c.CaseNo + ")'>" + c.CaseNo + "</a>",
                            "<span id='CaseTypeId' >" + $.caseType.getCaseTypeName(c.CaseTypeId) + "</span>",
                            "<span id='CaseRequestNo' >" + c.CaseRequestNo + "</span>",
                            "<span id='CaseFeeType' >" + $.caseFeeType.getCaseFeeTypeNameById(c.CaseFeeTypeId) + "</span>" + "<span id = 'CaseOfficeFeeTypeId' style='display:none'>" + c.CaseFeeTypeId + "</span>",
                            "<span id='InvoiceNo' >" + c.InvoiceNo + "</span>",
                            "<span id='InvoiceAmount' >" + c.InvoiceAmount + "</span>",
                            "<span id='InvoiceDate' >" + (c.InvoiceDate == null ? '' : getDate(convertJsonDateToJSDate(c.InvoiceDate))) + "</span>"
                        );
                        j++;
                    } else {
                        $('#tblCaseFeeList>tbody>tr:last').after("<tr><td colspan='11'><span id='message' >" + c.CustomFileName + "," + c.Message + "</span></td></tr>");
                    }
                });

            } else {
                $('#tblCaseFeeList>tbody>tr:last').after("<tr><td colspan='11'><span id='message'>文件不匹配上传规则，请确认上传文件正确.</span></td></tr>");
            }
        },
        Upload: function () {
            if ($("#flZip").val() == '') {
                $.showModalMessageBox("请选择上传的文件.");
                return false;
            }
            $("#uploadingForm").attr("action", AP_ROOT + AP_PAGE_ID + "/Legal/InvoiceFile/ReceiptCustomizedFileUpload");

            $.openLoading();

            $('#uploadingForm').ajaxSubmit({
                success: function (response) {
                    $.closeLoading();
                    if (response.IsSuccess) {
                        $.showModalMessageBox("上传成功.");
                        caseFee.Receipt.List(response.Data);
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                }
            });
            return true;
        },
        Import: function () {
            var caseIds = $.checkbox.vals("chkCaseId");
            if (caseIds.length == 0) {
                $.showModalMessageBox("请选择导入的案件费用.");
                return;
            }
            var data = {};
            var j = 0;

            var result = true;

            $("#tblCaseFeeList tbody tr").each(function (i, e) {
                if ($(e).css("display") != 'none') {
                    if ($(e).find("#chkCaseId").attr('checked') == 'checked') {
                        data["CustomFileCaseFees[" + j + "].CaseId"] = $(e).find("#chkCaseId").val();
                        data["CustomFileCaseFees[" + j + "].CaseFeeId"] = $(e).find("#CaseFeeId").text();
                        data["CustomFileCaseFees[" + j + "].CaseNo"] = $(e).find("#CaseNo").text();
                        data["CustomFileCaseFees[" + j + "].CaseTypeId"] = $(e).find("#CaseTypeId").text();
                        data["CustomFileCaseFees[" + j + "].CaseOfficeFeeTypeId"] = $(e).find("#CaseOfficeFeeTypeId").text();
                        data["CustomFileCaseFees[" + j + "].InvoiceNo"] = $(e).find("#InvoiceNo").text();
                        data["CustomFileCaseFees[" + j + "].InvoiceAmount"] = $(e).find("#InvoiceAmount").text();
                        data["CustomFileCaseFees[" + j + "].InvoiceDate"] = $(e).find("#InvoiceDate").text();
                        data["CustomFileCaseFees[" + j + "].CustomFileName"] = $(e).find("#CustomFileName").text();

                        if ($(e).find("#chkCaseId").val() == '') {
                            result = false;
                            $.showModalMessageBox("第" + (j + 1) + "行，文件格式错误，请重新选择.");
                            return false;
                        }

                        j++;
                    }
                }
            });

            if (result == true) {
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/InvoiceFile/ReceiptCustomizedFileImport", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("导入成功.");
                    }
                    else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            }
        },
    },

    InvoiceFile: {
        List: function (totalAmount, data) {
            $("tbody", "#tblCaseFeeList").clearRow();
            if (data.length > 0) {

                $("tbody", "#tblCaseFeeList").addRow(
                '',
                "",
                "",
                '',
                '',
                '',
                totalAmount,
                "",
                '',
                '');

                $.each(data, function (i, invoice) {
                    $.each(invoice.CaseFees, function (j, f) {
                        $("tbody", "#tblCaseFeeList").addRow(
                            "<input type='checkbox' Id='chkCaseFeeId' name='chkCaseFeeId' class='ng-pristine ng-valid' value='" + f.CaseFeeId + "'>"
                          + "<span id='InvoiceId' style='display:none' >" + invoice.InvoiceBasic.InvoiceId + "</span>"
                          + "<span id='CaseId' style='display:none' >" + f.CaseId + "</span>"
                          + "<span id='CaseNo' style='display:none' >" + f.CaseNo + "</span>",
                            "<span id='InvoiceFileName' >" + invoice.InvoiceBasic.FileName + "</span>",
                            "<a href='javascript:void(0);' onclick='javascript:caseInfo.View(\"" + f.CaseNo + "\");'>" + f.CaseNo + "</a>",
                            $.lsCaseType.getCaseTypeName(f.CaseTypeId),
                            invoice.InvoiceBasic.InvoiceApplicantName,
                            f.CaseFeeTypeName,
                            f.Amount,
                            "<span id='InvoiceNo' >" + invoice.InvoiceBasic.InvoiceNo + "</span>",
                            invoice.InvoiceBasic.InvoiceAmount,
                            (invoice.InvoiceBasic.InvoiceDate == null ? '' : getDate(convertJsonDateToJSDate(invoice.InvoiceBasic.InvoiceDate)))
                        );
                    });
                });

            } else {
                $('#tblCaseFeeList>tbody>tr:last').after("<tr><td colspan='10'><span id='message'>文件未匹配到票据号，请确认上传文件正确.</span></td></tr>");
            }
        },
        Upload: function () {
            if ($("#flZip").val() == '') {
                $.showModalMessageBox("请选择上传的文件.");
                return false;
            }
            $("#uploadingForm").attr("action", AP_ROOT + AP_PAGE_ID + "/Legal/InvoiceFile/InvoiceCustomizedFileUpload");

            $.openLoading();

            $('#uploadingForm').ajaxSubmit({
                success: function (response) {
                    $.closeLoading();
                    if (response.IsSuccess) {
                        $.showModalMessageBox("上传成功.");
                        $("#txtPrimaryFile").val(response.Data.PrimaryFileName);
                        caseFee.InvoiceFile.List(response.Data.TotalAmount, response.Data.Invoices);

                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                }
            });
            return true;
        },
        Import: function () {
            var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
            if (caseFeeIds.length == 0) {
                $.showModalMessageBox("请选择导入的案件费用.");
                return;
            }
            var data = {};

            data["PrimaryFileName"] = $("#txtPrimaryFile").val();

            var j = 0;
            var result = true;

            var invoiceId = '';
            $("#tblCaseFeeList tbody tr").each(function (i, e) {

                if ($(e).css("display") != 'none') {
                    if ($(e).find("#chkCaseFeeId").prop('checked') == true) {

                        if ($(e).find("#chkCaseFeeId").val() == '') {
                            result = false;
                            $.showModalMessageBox("第" + (i + 1) + "行，文件格式错误，请重新选择.");
                            return false;
                        }

                        data["Invoices[" + j + "].InvoiceBasic.InvoiceId"] = $(e).find("#InvoiceId").text();
                        data["Invoices[" + j + "].InvoiceBasic.InvoiceNo"] = $(e).find("#InvoiceNo").text();
                        data["Invoices[" + j + "].InvoiceBasic.FileName"] = $(e).find("#InvoiceFileName").text();
                        data["Invoices[" + j + "].CaseFees[" + 0 + "].CaseFeeId"] = $(e).find("#chkCaseFeeId").val();
                        data["Invoices[" + j + "].CaseFees[" + 0 + "].CaseId"] = $(e).find("#CaseId").text();
                        data["Invoices[" + j + "].CaseFees[" + 0 + "].CaseNo"] = $(e).find("#CaseNo").text();

                        j++;
                    }
                }
            });

            if (result == true) {
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/InvoiceFile/InvoiceCustomizedFileImport", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("导入成功.");
                    }
                    else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            }
        },
    },

    ContractInvoiceFile: {

        Selected: function (e) {
            if ($(e).prop("checked") == true) {
                $.checkbox.all("chkInvoiceId");
            }
            else {
                $.checkbox.not("chkInvoiceId");
            }
        },

        List: function (data) {
            $("tbody", "#tblInvoiceList").clearRow();
            if (data.length > 0) {
                $.each(data, function (i, c) {
                    $("tbody", "#tblInvoiceList").addRow(
                          "<input type='checkbox' Id='chkInvoiceId' name='chkInvoiceId' class='ng-pristine ng-valid' value='" + c.InvoiceBasic.InvoiceId + "'>"
                          + "<span id='InvoiceId' style='display:none' >" + c.InvoiceBasic.InvoiceId + "</span>"
                          + "<span id='InvoiceFileName' style='display:none' >" + c.InvoiceBasic.FileName + "</span>",
                          c.InvoiceBasic.InvoiceApplicationNo,
                          c.InvoiceBasic.ContractNo,
                          c.InvoiceBasic.CustomerName,
                          c.InvoiceBasic.InvoiceAmount,
                          "<span style='color:red'>" + c.InvoiceBasic.InvoiceOverAmount + "</span>",
                         "<span id='InvoiceNo' >" + c.InvoiceBasic.InvoiceNo + "</span>",
                          c.InvoiceBasic.InvoiceHolderName,
                          c.InvoiceBasic.InvoiceDate == null ? '' : getDate(convertJsonDateToJSDate(c.InvoiceBasic.InvoiceDate)),
                          c.InvoiceBasic.InvoiceStatusName,
                          (c.InvoiceBasic.InvoiceOverAmount > 0 ? '高开' + c.InvoiceBasic.InvoiceOverAmount + "元" : c.InvoiceBasic.Remark)
                      );
                });

            } else {
                $('#tblInvoiceList>tbody>tr:last').after("<tr><td colspan='11'><span id='message'>文件未匹配到票据号或未匹配到合同费用，请确认上传文件正确.</span></td></tr>");
            }
        },
        Upload: function () {
            if ($("#flZip").val() == '') {
                $.showModalMessageBox("请选择上传的文件.");
                return false;
            }
            $("#uploadingForm").attr("action", AP_ROOT + AP_PAGE_ID + "/Legal/InvoiceFile/ContractInvoiceCustomizedFileUpload");

            $.openLoading();

            $('#uploadingForm').ajaxSubmit({
                success: function (response) {
                    $.closeLoading();
                    if (response.IsSuccess) {
                        $.showModalMessageBox("上传成功.");
                        $("#txtPrimaryFile").val(response.Data.PrimaryFileName);
                        caseFee.ContractInvoiceFile.List(response.Data.Invoices);

                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                }
            });
            return true;
        },
        Import: function () {
            var invoiceIds = $.checkbox.vals("chkInvoiceId");
            if (invoiceIds.length == 0) {
                $.showModalMessageBox("请选择合同.");
                return;
            }
            var data = {};

            data["PrimaryFileName"] = $("#txtPrimaryFile").val();

            var j = 0;
            var result = true;

            var invoiceId = '';
            $("#tblInvoiceList tbody tr").each(function (i, e) {

                if ($(e).css("display") != 'none') {
                    if ($(e).find("#chkInvoiceId").attr('checked') == 'checked') {

                        if ($(e).find("#chkInvoiceId").val() == '') {
                            result = false;
                            $.showModalMessageBox("第" + (i + 1) + "行，文件格式错误，请重新选择.");
                            return false;
                        }

                        data["Invoices[" + j + "].InvoiceBasic.InvoiceId"] = $(e).find("#InvoiceId").text();
                        data["Invoices[" + j + "].InvoiceBasic.InvoiceNo"] = $(e).find("#InvoiceNo").text();
                        data["Invoices[" + j + "].InvoiceBasic.FileName"] = $(e).find("#InvoiceFileName").text();

                        j++;
                    }
                }
            });

            if (result == true) {
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/InvoiceFile/ContractInvoiceCustomizedFileImport", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("导入成功.");
                    }
                    else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            }
        },
    },

    Selected: function (e) {
        if ($(e).prop("checked") == true) {
            $.checkbox.all("chkCaseFeeId");
        }
        else {
            $.checkbox.not("chkCaseFeeId");
        }
    },


}

$(document).ready(function () {

    $("#btnInvoiceFileUpload").click(function () {
        caseFee.InvoiceFile.Upload();
    });

    $("#btnInvoiceImport").click(function () {
        caseFee.InvoiceFile.Import();
    });

    $("#flZip").change(function () {
        $("#txtFilePath").val($("#flZip").val());
    });

    $("#chkCaseAll").off().on("click", function () {
        caseFee.Selected(this);
    });

    $("#chkInvoiceAll").off().on("click", function () {
        caseFee.ContractInvoiceFile.Selected(this);
    });

    $("#chkCaseIdAll").off().on("click", function () {
        caseFee.ReceiptOcr.SelectedAll(this);
    });

    $("#chkCaseId").off().on("click", function () {
        caseFee.ReceiptOcr.SelectedParent(this);
    });

    $("#chkParentCaseId").off().on("click", function () {
        caseFee.ReceiptOcr.Selected(this);
    });
});