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
        if (data.BatchFiles.length > 0) {
            var j = 0;
            $.each(data.BatchFiles, function (i, e) {
                $.each(e.BatchFileCases, function (k, c) {
                    if (!c.HasError) {
                        var fwr = c.FAWENR == null ? '' : getDate(convertJsonDateToJSDate(c.FAWENR));
                        $("tbody", "#tblCaseList").addRow(
                            "<input type='checkbox' Id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' value='" + c.CaseId + "'>",
                            "<span id='TONGZHISID' >" + c.TONGZHISID + "</span><span id = 'CaseTypeId' style='display:none'>" + c.CaseTypeId + "</span><span id='FileFullPath' style='display:none'>" + c.FileFullPath + "</span>" + "</span><span id = 'FileOfficialName' style='display:none'>" + c.FileOfficialName + "</span>",
                            "<span id='CaseNo'  >" + c.CaseNo + "</span>",
                            "<span id='SHENQINGH' >" + c.SHENQINGH + "</span>",
                            "<input readonly id = 'TONGZHISMC' type='text' style='width:200px' value='" + c.TONGZHISMC + "'>"  + "<span id = 'CaseFileTypeId' style='display:none'>" + c.CaseFileTypeId + "</span>",
                            "<input id='FAWENR' class='input_time' style='width:140px'  onfocus=\"WdatePicker({doubleCalendar:true,dateFmt:'yyyy-MM-dd'})\" required='true' type='text' value='" + fwr + "'>",
                            "<input id='QIXIAN' onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\" onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" type='text' style='width:50px' value='" + c.QIXIAN + "''/>",
                            "<input readonly class='CaseOfficer' id='CaseOfficer" + j + "' type='text' style='width:100px' value='" + c.CaseOfficer + "'/>" + "<input id='CaseOfficerId" + j + "' type='hidden' value='" + c.CaseOfficer + "'/>",
                            "<input id='CaseFeeAmount' onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\" onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" type='text' style='width:50px' value='" + (c.CaseFeeAmount == null ? '' : c.CaseFeeAmount) + "'/>",
                            "<input readonly class='CaseFeeTypeName' id = 'CaseFeeTypeName" + j + "' type='text' style='width:50px' value=''/>" + "<input id='CaseFeeTypeId" + j + "' type='hidden'/>",
                            "<input readonly class='CaseFeeResponseUser' id='CaseFeeResponseUser" + j + "'type='text' style='width:100px'  value='" + c.CaseFeeResponseUser + "''/>" + "<input id='CaseFeeResponseUserId" + j + "' type='hidden'/>"
                        );
                    } else {
                        $('#tblCaseList>tbody>tr:last').after("<tr><td colspan='11'><span id='message' >" + c.FileOfficialName + "," + c.Message + "</span></td></tr>");
                    }
                    j++;
                });
            });

        } else {
        }
    },

    BatchUpload: function () {
        if ($("#flZip").val() == '') {
            $.showModalMessageBox("请选择上传的文件.");
            return false;
        }
        $("#uploadingForm").attr("action", AP_ROOT + "IPR/Case/CaseBatchFileUploading");

        $.openLoading();

        $('#uploadingForm').ajaxSubmit({
            success: function (response) {

                $.closeLoading();

                if (response.IsSuccess) {
                    caseFileImport.BulidTreeView(response.Data.BatchFileNodes);
                    caseFileImport.List(response.Data);
                    $.showModalMessageBox("上传成功.");
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

                    if ($(e).find("#chkCaseId").val() == '') {
                        result = false;
                        $.showModalMessageBox("第" + (i) + "行，文件错误，请重新选择.");
                        return false;
                    }

                    var k = i - 1;

                    data["BatchFileCases[" + j + "].CaseId"] = $(e).find("#chkCaseId").val();
                    data["BatchFileCases[" + j + "].CaseTypeId"] = $(e).find(".CaseTypeId").text();
                    data["BatchFileCases[" + j + "].CaseFileTypeId"] = $(e).find("#CaseFileTypeId").text();
                    data["BatchFileCases[" + j + "].TONGZHISID"] = $(e).find("#TONGZHISID").text();
                    data["BatchFileCases[" + j + "].SHENQINGH"] = $(e).find("#SHENQINGH").text();
                    data["BatchFileCases[" + j + "].CaseNo"] = $(e).find("#CaseNo").text();
                    data["BatchFileCases[" + j + "].TONGZHISMC"] = $(e).find("#TONGZHISMC").val();
                    data["BatchFileCases[" + j + "].FAWENR"] = $(e).find("#FAWENR").val();
                    data["BatchFileCases[" + j + "].QIXIAN"] = $(e).find("#QIXIAN").val();
                    data["BatchFileCases[" + j + "].CaseOfficer"] = $(e).find("#CaseOfficerId" + k).val();
                    data["BatchFileCases[" + j + "].CaseFeeTypeId"] = $(e).find("#CaseFeeTypeId" + k).val();
                    data["BatchFileCases[" + j + "].CaseFeeAmount"] = $(e).find("#CaseFeeAmount").val();
                    data["BatchFileCases[" + j + "].CaseFeeResponseUser"] = $(e).find("#CaseFeeResponseUserId" + k).val();
                    data["BatchFileCases[" + j + "].FileFullPath"] = $(e).find("#FileFullPath").text();
                    data["BatchFileCases[" + j + "].FileOfficialName"] = $(e).find("#FileOfficialName").text();

                    if (data["BatchFileCases[" + j + "].CaseOfficer"] == '') {
                        result = false;
                        $.showModalMessageBox("第" + (i) + "行，请选择处理人.");
                        return false;
                    }

                    if (data["BatchFileCases[" + j + "].FAWENR"] == '') {
                        result = false;
                        $.showModalMessageBox("第" + (i) + "行，请输入参考日期.");
                        return false;
                    }

                    if (data["BatchFileCases[" + j + "].QIXIAN"] == '') {
                        result = false;
                        $.showModalMessageBox("第" + (i) + "行，请输入期限.");
                        return false;
                    }

                    if (data["BatchFileCases[" + j + "].CaseFeeTypeId"] != ''
                        || data["BatchFileCases[" + j + "].CaseFeeAmount"] != ''
                        || data["BatchFileCases[" + j + "].CaseFeeResponseUser"] != '') {
                        if (data["BatchFileCases[" + j + "].CaseFeeTypeId"] == '') {
                            result = false;
                            $.showModalMessageBox("第" + (i) + "行，请选择费用类型.");
                            return false;
                        }

                        if (data["BatchFileCases[" + j + "].CaseFeeAmount"] == '') {
                            result = false;
                            $.showModalMessageBox("第" + (i) + "行，请输入费用金额.");
                            return false;
                        }

                        if (data["BatchFileCases[" + j + "].CaseFeeResponseUser"] == '') {
                            result = false;
                            $.showModalMessageBox("第" + (i) + "行，请选择结算人.");
                            return false;
                        }
                    }
                    j++;
                }
            }
        });

        if (result == true) {
            $.ajaxPost(AP_ROOT + "IPR/Case/CaseBatchFileImport", data, function (response) {
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
        $("#divUserList").hide();
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

    $("#chkCaseAll").die().live("click", function () {
        caseFileImport.Selected(this);
    });

    $(".CaseOfficer").die().live("click", function () {

       var tirgger = this;
        var parent = this.parentElement;
        $("#divUserList").css({
            "position": "absolute",
            "left": $(tirgger).position().left,
            "top": $(tirgger).position().top + 150
        }).toggle();
        $("#hidUserName").val($(tirgger).attr("id")); //名称
        $("#hidUserId").val($(parent).find(":hidden").attr("id"));//Id
        return false;
    });
    
    $(".CaseFeeResponseUser").die().live("click", function () {
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

    $(".CaseFeeTypeName").die().live("click", function () {

        var tirgger = this;
        var parent = this.parentElement;
        var caseTypeId = $($(this).parent()).parent().find("#CaseTypeId").text();
        $(".divCaseFeeTypeList").html($.caseFeeType.getCaseFeeTypeListHtml(caseTypeId));

        $("#divCaseFeeTypeList").css({
            "position": "absolute",
            "left": $(tirgger).position().left,
            "top": $(tirgger).position().top + 150
        }).toggle();

        $("#hidCaseFeeTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFeeTypeId").val($(parent).find(":hidden").attr("id"));//Id

        return false;
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

    $("#divUsers").find("li").die().live("click", function () {
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        var currentSelectedControlId = $("#hidUserId").val();
        var currentSelectedControlName = $("#hidUserName").val();
        $("#" + currentSelectedControlId).val(userId);
        $("#" + currentSelectedControlName).val(userName);
        $("#divUsers").hide();
    });

});