var caseFileImport = {

    List: function (data) {
        $("tbody", "#tblCaseList").clearRow();
        if (data.length > 0) {
            var j = 0;
            $.each(data, function (i, c) {
                if (!c.HasError) {
                    $("tbody", "#tblCaseList").addRow(
                        "<input type='checkbox' Id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' value='" + c.CaseId + "'>",
                        "<span id='CustomFileName' >" + c.CustomFileName + "</span><span id = 'CaseTypeId' style='display:none'>" + c.CaseTypeId + "</span><span style='display:none' id='CaseNo'>" + c.CaseNo + "</span><span id = 'CaseFeeItemId' style='display:none'>" + c.CaseFeeItemId + "</span>",
                        "<a href='" + AP_ROOT + "IPR/Case/CreateUpdate?caseId=" +c.CaseId  + "' target='_blank'>" + c.CaseNo + "</a>",
                       "<span id='CaseTypeId' >" + $.caseType.getCaseTypeName(c.CaseTypeId) + "</span>",
                        "<span id='CaseRequestNo' >" + c.CaseRequestNo + "</span>",
                        "<span id='CaseFeeType' >" + $.caseFeeType.getCaseFeeTypeName(c.CaseTypeId, c.CaseFeeTypeId) + "</span>" + "<span id = 'CaseFeeTypeId' style='display:none'>" + c.CaseFeeTypeId + "</span>",
                         "<input  class='BillNo' id='BillNo' type='text' style='width:100px' value='" + c.BillNo + "'/>",
                         "<input readonly class='BillAmount' id='BillAmount' type='text' style='width:100px' value='" + c.BillAmount + "'/>",
                         "<input id='BillDate' class='input_time' style='width:80px'  onfocus=\"WdatePicker({doubleCalendar:true,dateFmt:'yyyy-MM-dd'})\" required='true' type='text' value='" + (c.BillDate == null ? '' : getDate(convertJsonDateToJSDate(c.BillDate))) + "'>",
                        "<input id='GainedDate' class='input_time' style='width:80px'  onfocus=\"WdatePicker({doubleCalendar:true,dateFmt:'yyyy-MM-dd'})\" required='true' type='text' value='" + getDate(convertJsonDateToJSDate(c.GainedDate)) + "'>"
                        
                    );
                    j++;
                } else {
                    $('#tblCaseList>tbody>tr:last').after("<tr><td colspan='11'><span id='message' >" + c.CustomFileName + "," + c.Message +  "</span></td></tr>");
                }
            });

        } else {
            $('#tblCaseList>tbody>tr:last').after("<tr><td colspan='11'><span id='message'>文件不匹配上传规则，请确认上传文件正确.</span></td></tr>");
        }
    },

    BatchUpload: function () {
        if ($("#flZip").val() == '') {
            $.showModalMessageBox("请选择上传的文件.");
            return false;
        }
        $("#uploadingForm").attr("action", AP_ROOT + "IPR/Case/CaseFeeFileCustomImportUploading");

        $.openLoading();

        $('#uploadingForm').ajaxSubmit({
            success: function (response) {
                $.closeLoading();
                if (response.IsSuccess) {
                    $.showModalMessageBox("上传成功.");
                    caseFileImport.List(response.Data);
                } else {
                    $.showModalMessageBox(response.Message);
                }
            } 
        });
        return true;
    },

    BatchImport: function () {
        var caseIds = $.checkbox.vals("chkCaseId");
        if (caseIds.length == 0) {
            $.showModalMessageBox("请选择导入的案件.");
            return;
        }
        var data = {};
        var j = 0;

        var result = true;

        $("#tblCaseList tbody tr").each(function (i, e) {
            if ($(e).css("display") != 'none') {
                if ($(e).find("#chkCaseId").attr('checked') == 'checked') {
                    data["CustomFileCaseFees[" + j + "].CaseId"] = $(e).find("#chkCaseId").val();
                    data["CustomFileCaseFees[" + j + "].CaseFeeItemId"] = $(e).find("#CaseFeeItemId").text();
                    data["CustomFileCaseFees[" + j + "].CaseNo"] = $(e).find("#CaseNo").text();
                    data["CustomFileCaseFees[" + j + "].CaseTypeId"] = $(e).find("#CaseTypeId").text();
                    data["CustomFileCaseFees[" + j + "].CaseFeeTypeId"] = $(e).find("#CaseFeeTypeId").text();
                    data["CustomFileCaseFees[" + j + "].BillNo"] = $(e).find("#BillNo").val();
                    data["CustomFileCaseFees[" + j + "].BillAmount"] = $(e).find("#BillAmount").val();
                    data["CustomFileCaseFees[" + j + "].BillDate"] = $(e).find("#BillDate").val();
                    data["CustomFileCaseFees[" + j + "].GainedDate"] = $(e).find("#GainedDate").val();
                    data["CustomFileCaseFees[" + j + "].CustomFileName"] = $(e).find("#CustomFileName").text();

                    if ($(e).find("#chkCaseId").val() == '') {
                        result = false;
                        $.showModalMessageBox("第" + (j + 1) + "行，文件格式错误，请重新选择.");
                        return false;
                    }

                    if ($(e).find("#BillNo").val() == '') {
                        result = false;
                        $.showModalMessageBox("第" + (j + 1) + "行，请输入票据编号.");
                        return false;
                    }

                    if ($(e).find("#BillAmount").val() == '') {
                        result = false;
                        $.showModalMessageBox("第" + (j + 1) + "行，请输入票据金额.");
                        return false;
                    }

                    if ($(e).find("#BillDate").val() == '') {
                        result = false;
                        $.showModalMessageBox("第" + (j + 1) + "行，请输入票据日期.");
                        return false;
                    }

                    j++;
                }
            }
        });

        if (result == true) {
            $.ajaxPost(AP_ROOT + "IPR/Case/CaseFeeFileCustomImport", data, function (response) {
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
        if ($(e).attr("checked") == "checked") {
            $.checkbox.all("chkCaseId");
        }
        else {
            $.checkbox.not("chkCaseId");
        }
    },
}

$(document).ready(function () {

    $("#btnFileUpload").click(function () {
        caseFileImport.BatchUpload();
    });

    $("#btnImport").click(function () {
        caseFileImport.BatchImport();
    });

    $("#flZip").change(function () {
        $("#txtFilePath").val($("#flZip").val());
    });

    $("#chkCaseAll").die().live("click", function () {
        caseFileImport.Selected(this);
    });

    $(".CaseOfficer,.CaseFeeResponseUser").die().live("click", function () {
        var tirgger = this;
        var parent = this.parentElement;
        $("#divUserList").css({
            "position": "absolute",
            "left": $(tirgger).position().left - 8,
            "top": $(tirgger).position().top + 32
        }).toggle();
        $("#hidUserName").val($(tirgger).attr("id")); //名称
        $("#hidUserId").val($(parent).find(":hidden").attr("id"));//Id
        return false;
    });

    $(".CaseFeeTypeName").die().live("click", function () {
        var tirgger = this;
        var caseTypeId = $($(this).parent()).parent().find("#CaseTypeId").text();
        $(".divCaseFeeTypeList").html($.caseFeeType.getCaseFeeTypeListHtml(caseTypeId));

        $("#divCaseFeeTypeList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 100,
            "top": $(tirgger).position().top + 32
        }).toggle();

        $("#hidCaseFeeTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFeeTypeId").val($(parent).find(":hidden").attr("id"));//Id
    });

    $("#divCaseFeeTypeList").find("li").die().live("click", function () {
        var caseFeeTypeId = $(this).find("a").attr("id");
        var caseFeeTypeName = $(this).find("a").text();
        var currentSelectedControlId = $("#hidCaseFeeTypeId").val();
        var currentSelectedControlName = $("#hidCaseFeeTypeName").val();
        $("#" + currentSelectedControlId).val(caseFeeTypeId);
        $("#" + currentSelectedControlName).val(caseFeeTypeName);
        $("#divCaseFeeTypeList").hide();
    });

    $("#divUserList").find("li").die().live("click", function () {
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        var currentSelectedControlId = $("#hidUserId").val();
        var currentSelectedControlName = $("#hidUserName").val();
        $("#" + currentSelectedControlId).val(userId);
        $("#" + currentSelectedControlName).val(userName);
        $("#divUserList").hide();
    });

});