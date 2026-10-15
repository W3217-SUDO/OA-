var caseFile = {

    List: function (data) {
        $("tbody", "#tblCaseFileList").clearRow();
        if (data.length > 0) {
            var j = 0;
            $.each(data, function (i, c) {
                if (!c.HasError) {
                    $("tbody", "#tblCaseFileList").addRow(
                        "<input type='checkbox' Id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' value='" + c.CaseId + "'>",
                        "<span id='CustomFileName' >" + c.FileName + "</span>",
                        "<span id='CaseFileTypeName' >" + $.lsCaseFileType.getCaseFileTypeName(c.CaseTypeId, c.CaseFileTypeId) + "</span>" + "<span id = 'CaseFileTypeId' style='display:none'>" + c.CaseFileTypeId + "</span>",
                        "<input id='UploadingTime' class='input_time'  style='width:100%'   onfocus=\"WdatePicker({doubleCalendar:true,dateFmt:'yyyy-MM-dd'})\" required='true' type='text' value='" + getDate(convertJsonDateToJSDate(c.UploadingTime)) + "'>",
                        "<span id='CaseNo'  >" + c.CaseNo + "</span>",
                        "<span id='CaseTypeId' >" + $.lsCaseType.getCaseTypeName(c.CaseTypeId) + "</span>",
                        "<span id='CaseName' >" + c.CaseName + "</span>",
                        "<span id='CustomerName' >" + c.CustomerName + "</span>"
                    );
                    j++;
                } else {
                    $("tbody", "#tblCaseFileList").addRow(
                        "<input type='checkbox' Id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' value=''>",
                        "<span id='CustomFileName' >" + c.FileName + "</span>",
                        "<input id='CaseFileTypeName' class='' style='width:100%'  type='text' value=''>",
                        "<input id='UploadingTime' class='input_time' style='width:100%'  onfocus=\"WdatePicker({doubleCalendar:true,dateFmt:'yyyy-MM-dd'})\" required='true' type='text' value='" + getDate(convertJsonDateToJSDate(c.UploadingTime)) + "'>",
                        "<span id='CaseNo' ></span>",
                        "<span id='CaseTypeId'></span>"
                    );
                    j++;
                }
            });

        } else {
            $('#tblCaseFileList>tbody>tr:last').after("<tr><td colspan='11'><span id='message' >未找到文件，请确认上传文件正确.</span></td></tr>");
        }
    },

    Upload: function () {
        if ($("#flZip").val() == '') {
            $.showModalMessageBox("请选择上传的文件.");
            return false;
        }
        $("#uploadingForm").attr("action", AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseFile/CaseCustomizedFileUpload");

        $.openLoading();

        $('#uploadingForm').ajaxSubmit({
            success: function (response) {
                $.closeLoading();
                if (response.IsSuccess) {
                    $.showModalMessageBox("上传成功.");
                    caseFile.List(response.Data);
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
            $.showModalMessageBox("请选择导入的案件.");
            return;
        }
        var data = {};
        var j = 0;

        var result = true;

        $("#tblCaseFileList tbody tr").each(function (i, e) {
            if ($(e).css("display") != 'none') {
                if ($(e).find("#chkCaseId").attr('checked') == 'checked') {

                    data["CustomFileCases[" + j + "].CaseId"] = $(e).find("#chkCaseId").val();
                   
                    data["CustomFileCases[" + j + "].CaseNo"] = $(e).find("#CaseNo").text();
                    data["CustomFileCases[" + j + "].CaseRequestNo"] = $(e).find("#CaseRequestNo").text();
                    data["CustomFileCases[" + j + "].CaseFileTypeId"] = $(e).find("#CaseFileTypeId").text();
                    data["CustomFileCases[" + j + "].CaseOfficeFeeTypeId"] = $(e).find("#CaseOfficeFeeTypeId").text();
                    data["CustomFileCases[" + j + "].CaseOfficer"] = $(e).find("#CaseOfficerId" + j).val();
                    data["CustomFileCases[" + j + "].CaseFeeResponseUser"] = $(e).find("#CaseFeeResponseUserId" + j).val();
                    data["CustomFileCases[" + j + "].CaseOfficeFeeAmount"] = $(e).find("#CaseOfficeFeeAmount").val();
                    data["CustomFileCases[" + j + "].UploadingTime"] = $(e).find("#UploadingTime").val();
                    data["CustomFileCases[" + j + "].CustomFileName"] = $(e).find("#CustomFileName").text();

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
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/CaseFile/CaseCustomFileImport", data, function (response) {
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

    $(document).click(function () {
        $("#divUsers").hide();
        $("#divCaseFeeTypeList").hide();
    });

    $("#btnFileUpload").click(function () {
        caseFile.Upload();
    });

    $("#btnImport").click(function () {
        caseFile.Import();
    });

    $("#flZip").change(function () {
        $("#txtFilePath").val($("#flZip").val());
    });

    $("#chkCaseAll").die().live("click", function () {
        caseFile.Selected(this);
    });

    $(".CaseOfficer,.CaseFeeResponseUser").die().live("click", function () {
        var tirgger = this;
        var parent = this.parentElement;
        $("#divUsers").css({
            "position": "absolute",
            "left": $(tirgger).position().left,
            "top": $(tirgger).position().top + 150
        }).toggle();
        $("#hidUserName").val($(tirgger).attr("id")); //名称
        $("#hidUserId").val($(parent).find(":hidden").attr("id"));//Id
        return false;
    });

    $("#divUsers").find("li").die().live("click", function () {
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        var currentSelectedControlId = $("#hidUserId").val();
        var currentSelectedControlName = $("#hidUserName").val();
        $("#" + currentSelectedControlId).val(userId);
        $("#" + currentSelectedControlName).val(userName);
        $("#divUserList").hide();
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



});