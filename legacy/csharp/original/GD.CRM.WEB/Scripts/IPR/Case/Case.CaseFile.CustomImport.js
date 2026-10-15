var caseFileImport = {

    BulidTreeView: function (result) {
        $('#treeview').treeview({
            data: result, // 数据源
            showCheckbox: false, //是否显示复选框
            highlightSelected: false, //是否高亮选中
            //nodeIcon: 'glyphicon glyphicon-user',    //节点上的图标
            nodeIcon: '',
            emptyIcon: 'icon expand-icon glyphicon glyphicon-minus', //没有子节点的节点图标
            multiSelect: false, //多选
            onNodeChecked: function (event, data) {

                if (data.parentId != null) {
                    $('#treeview').treeview('checkNode', [data.parentId, { silent: true }]);
                }
                if (data.nodes != null) {
                    $.each(data.nodes, function (i, c) {
                        $('#treeview').treeview('checkNode', [c.nodeId, { silent: true }]);
                    });
                }
            },
            onNodeUnchecked: function (event, data) {
                if (data.nodes != null) {
                    $.each(data.nodes, function (i, c) {
                        $('#treeview').treeview('uncheckNode', [c.nodeId, { silent: true }]);
                    });
                }
            },
            onNodeSelected: function (event, data) {
            }
        });
    },

    List: function (data) {
        $("tbody", "#tblCaseList").clearRow();
        if (data.length > 0) {
            var j = 0;
            $.each(data, function (i, c) {

                if (!c.HasError) {
                    $("tbody", "#tblCaseList").addRow(
                        "<input type='checkbox' Id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' value='" + c.CaseId + "'>" + "<span>" + (j + 1) + "</span>",
                        "<span id='CustomFileName' >" + c.CustomFileName + "</span><span id = 'CaseTypeId' style='display:none'>" + c.CaseTypeId + "</span><span id = 'CaseOfficeFeeTypeId' style='display:none'>" + c.CaseFeeTypeId + "</span>",
                        "<span id='CaseNo'  >" + c.CaseNo + "</span>",
                       "<span id='CaseTypeId' >" + $.caseType.getCaseTypeName(c.CaseTypeId) + "</span>",
                        "<span id='CaseRequestNo' >" + c.CaseRequestNo + "</span>",
                        "<span id='CaseFileTypeName' >" + $.caseFileType.getCaseFileTypeNameById(c.CaseFileTypeId) + "</span>" + "<span id = 'CaseFileTypeId' style='display:none'>" + c.CaseFileTypeId + "</span>",
                        "<input id='UploadingTime' class='input_time' style='width:80px'  onfocus=\"WdatePicker({doubleCalendar:true,dateFmt:'yyyy-MM-dd'})\" required='true' type='text' value='" + getDate(convertJsonDateToJSDate(c.UploadingTime)) + "'>",
                        "<input readonly class='CaseOfficer' id='CaseOfficer" + j + "' type='text' style='width:60px' value='" + c.CaseOfficer + "'/>" + "<input id='CaseOfficerId" + j + "' type='hidden' value='" + c.CaseOfficer + "'/>",
                        "<input id='CaseOfficeFeeAmount' type='text' style='width:50px' value='" + (c.CaseFeeAmount == null ? '' : c.CaseFeeAmount) + "'/>",
                         "<span id='CaseFeeTypeName' >" + $.caseFeeType.getCaseFeeTypeName(c.CaseTypeId, c.CaseFeeTypeId) + "</span>",
                        "<input readonly class='CaseFeeResponseUser' id='CaseFeeResponseUser" + j + "'type='text' style='width:60px'  value='" + c.CaseFeeResponseUser + "''/>" + "<input id='CaseFeeResponseUserId" + j + "' type='hidden' value='" + c.CaseFeeResponseUser + "'/>"
                    );
                    j++;
                } else {
                    $('#tblCaseList>tbody>tr:last').after("<tr><td colspan='11'><span id='message' >" + c.CustomFileName + "," + c.Message + "</span></td></tr>");
                }
            });

        } else {
            $('#tblCaseList>tbody>tr:last').after("<tr><td colspan='11'><span id='message' >未找到文件，请确认上传文件正确.</span></td></tr>");
        }
    },

    BatchUpload: function () {
        if ($("#flZip").val() == '') {
            $.showModalMessageBox("请选择上传的文件.");
            return false;
        }
        $("#uploadingForm").attr("action",  AP_ROOT + AP_PAGE_ID + "/IPR/CaseFile/CaseFileCustomImportUploading");

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
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFile/CaseCustomFileImport", data, function (response) {
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
        if ($(e).prop("checked") == true) {
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
        caseFileImport.BatchUpload();
    });

    $("#btnImport").click(function () {
        caseFileImport.BatchImport();
    });

    $("#flZip").change(function () {
        $("#txtFilePath").val($("#flZip").val());
    });

    $("#chkCaseAll").off().on("click", function () {
        caseFileImport.Selected(this);
    });

    $(".CaseOfficer,.CaseFeeResponseUser").off().on("click", function () {
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

    $("#divUsers").find("li").off().on("click", function () {
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        var currentSelectedControlId = $("#hidUserId").val();
        var currentSelectedControlName = $("#hidUserName").val();
        $("#" + currentSelectedControlId).val(userId);
        $("#" + currentSelectedControlName).val(userName);
        $("#divUserList").hide();
    });

    $(".CaseFeeTypeName").off().on("click", function () {
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

    $("#divCaseFeeTypeList").find("li").off().on("click", function () {
        var caseFeeTypeId = $(this).find("a").attr("id");
        var caseFeeTypeName = $(this).find("a").text();
        var currentSelectedControlId = $("#hidCaseFeeTypeId").val();
        var currentSelectedControlName = $("#hidCaseFeeTypeName").val();
        $("#" + currentSelectedControlId).val(caseFeeTypeId);
        $("#" + currentSelectedControlName).val(caseFeeTypeName);
        $("#divCaseFeeTypeList").hide();
    });



});