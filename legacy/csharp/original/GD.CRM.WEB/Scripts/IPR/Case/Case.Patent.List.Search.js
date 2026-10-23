/*案件批量处理*/

var caseInfo = 
{
    Multiple: {

        Edit: {
            /*批量案件基本信息*/
            Open: function () {
                var caseIds = $.checkbox.vals("chkCaseId");
                if (caseIds.length == 0) {
                    $.showModalMessageBox("请选择需要修改的案件.");
                    return false;
                }

                var data =
                {
                    caseIds: caseIds
                };

                var url = AP_ROOT + "IPR/Case/CaseBatchEdit";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#caseBatchEditModal').modal({ backdrop: 'static', keyboard: false });
                    $('#caseBatchEditModal').on('hidden.bs.modal', function () {
                        $("#caseBatchEditModal").remove();
                    });
                });
            },

            /*批量修改*/
            Create: function () {

                if ($("#caseIdList").val().split(',').length > 1 && $("#CaseNo").val() != '') {
                    $.showModalMessageBox("不允许同时修改多个案件为同一案件编号.");
                    return false;
                }

                $.openLoading();
                $('#caseBatchEdit').ajaxSubmit({
                    success: function (response) {
                        $.closeLoading();
                        if (response.IsSuccess) {
                            $.showModalMessageBox("批量修改成功.");
                            $('#caseBatchEdit').modal('hide');
                            caseQuery.List();
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    }
                });
            },

            /*关闭*/
            Close: function () {
                $('#caseBatchEditModal').modal('hide');
            },
        },


        Import: {

            /*批量导入open*/
            Open: function () {
                var caseIds = $.checkbox.vals("chkCaseId");
                if (caseIds.length == 0) {
                    $.showModalMessageBox("请选择需要导入文件的案件.");
                    return false;
                }

                var data =
                {
                    caseIds: caseIds
                };

                var url = AP_ROOT + "IPR/CaseFile/CaseFileBatchImport";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#caseFileBatchImportModal').modal({ backdrop: 'static', keyboard: false });
                    $('#caseFileBatchImportModal').on('hidden.bs.modal', function () {
                        $("#caseFileBatchImportModal").remove();
                    });

                    var caseFileType = new AssociateCaseFileType(
                        $("#div_CaseFileTypeList"),
                        $("#CaseFileTypeId"),
                        $("#CaseFileTypeName"),
                        null,
                        false,
                        null
                    );
                });
            },

            /*批量导入关闭*/
            Close: function () {
                $('#caseFileBatchImportModal').modal('hide');
            },

            /*批量导入*/
            Create: function () {
                $.openLoading();
                $('#caseFileBatchImportProcess').ajaxSubmit({
                    success: function (response) {
                        $.closeLoading();
                        if (response.IsSuccess) {
                            $.showModalMessageBox("批量导入成功.");
                            $('#caseFileBatchImportModal').modal('hide');
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    }
                });
            },
        },

        Transfer: {

            Open: function () {

                var caseIds = $.checkbox.vals("chkCaseId");
                if (caseIds.length == 0) {
                    $.showModalMessageBox("请选择转文的案件.");
                    return;
                }

                var customerIds = new Array();

                $("input[name='chkCaseId']:checked").each(
                    function () {
                        if ($.inArray($(this).attr("customerid"), customerIds) > -1) {
                        } else {
                            customerIds.push($(this).attr("customerid"));
                        }
                    }
                );
                if (customerIds.length > 1) {
                    $.showModalMessageBox("客户不一致,不允许转文.");
                    return false;
                }

                 var data = {
                     customerId: customerIds[0],
                    caseIds: caseIds,
                }

                var url = AP_ROOT + "IPR/Case/CaseListExportToWord";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#caseToWordModal').modal({ backdrop: 'static', keyboard: false });
                    $('#caseToWordModal').on('hidden.bs.modal', function () {
                        $("#caseToWordModal").remove();
                    });

                    var caseFileType = new AssociateCaseFileType(
                     $("#div_CaseFileTypeList"),
                     $("#CaseFileTypeId"),
                     $("#CaseFileTypeName"),
                     null,
                     $("#IsTransformedFile").val() == 'true',
                     null
                    );
                });

                //$('.casetoword').load(url, data, function (result) {
                //    $.closeLoading();
                //    $('#caseToWordModal').modal('toggle');
                //});
            },

            /*关闭客户*/
            Close: function () {
                $('#caseToWordModal').modal('hide');
            },

            Export: function () {
                var caseIds = $.checkbox.vals("chkCaseId");
                if (caseIds.length == 0) {
                    $.showModalMessageBox("请选择导出的案件.");
                    return false;
                }
                if ($("#hidCaseFileTypeId").val() == '') {
                    $.showModalMessageBox("请选择专文文档.");
                    return false;
                }

                var data = {
                    customerId: $("#CustomerId").val(),
                    caseFileTypeId: $("#CaseFileTypeId").val(),
                    caseIds: caseIds,
                }

                $.ajaxPost(AP_ROOT + "IPR/Case/ExportCaseListToWord", data, function (response) {
                    if (response.IsSuccess) {
                        var customerId = response.Data.split('|')[0];
                        var fileName = response.Data.split('|')[1];
                        window.open(AP_ROOT + "IPR/CaseFileCenter/CaseExportFileDownload?customerId=" + customerId + "&fileName=" + fileName);
                        $.showModalMessageBox("导出成功.");
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });

                return true;
            },

            Upload: function () {

                if ($("#CaseFileType").val() == '') {
                    $.showModalMessageBox("请选择文件类型.");
                    return false;
                }

                if ($("#flFile").val() == "") {
                    $.showModalMessageBox("请选择文档文件.");
                    return false;
                }

                $.openLoading();
                $('#uploadingForm').ajaxSubmit({
                    success: function (response) {
                        $.closeLoading();
                        if (response.IsSuccess) {
                            $.showModalMessageBox("上传成功.");
                            $('#caseToWordModal').modal('hide');
                            return false;
                        } else {
                            $.showModalMessageBox(response.Message);
                            return false;
                        }
                    }
                });
            },


            ProcessFileTypeSelectedCallBack: function (caseFileTypeId, caseFileTypeNameText, hedgingFileTypeId) {
                $(".spanreferencedate").text(caseFileTypeNameText + "日期");

                if (caseFileTypeId == '8'
                    || caseFileTypeId == '38'
                    || caseFileTypeId == '126'
                    || caseFileTypeId == '127'
                    || caseFileTypeId == '157') {
                    //$(".spanreferencedate").text("申请日期");
                    if (caseFileTypeId == '8') {
                        $(".caserequestno").css("display", 'block');
                    }
                } else if (caseFileTypeId == '253'
                    || caseFileTypeId == '239'
                    || caseFileTypeId == '249'
                    || caseFileTypeId == '42'
                   ) {
                    //$(".spanreferencedate").text("授权日期");
                } else {
                    // $(".spanreferencedate").text("参考日期");
                }

                $(".caseHedgingFile").css("display", 'none');
                $("#HedgingFileId").empty();

                if (hedgingFileTypeId != '') {

                    var data = {
                        caseId: parseInt($("#CaseId").val()),
                        caseFileTypeId: caseFileTypeId
                    };

                    $.ajaxSetup({
                        async: false
                    });

                    $.ajaxPost(AP_ROOT + "IPR/Case/GetHedgingFileList", data, function (response) {
                        if (response.IsSuccess) {
                            if (response.Data.length > 0) {
                                $(".caseHedgingFile").css("display", 'block');
                                $.each(response.Data, function (i, c) {
                                    if (i == 0) {
                                        $("#HedgingFileId").append("<option selected value='" + c.FileId + "'>" + c.FileTypeId + c.FileTypeName + "</option>");
                                    } else {
                                        $("#HedgingFileId").append("<option value='" + c.FileId + "'>" + c.FileTypeId + c.FileTypeName + "</option>");
                                    }
                                });
                            } else {
                                $("#HedgingFileId").append("<option selected value=''>" + "无" + "</option>");
                            }
                        } else {
                            $("#HedgingFileId").append("<option selected value=''>" + "无" + "</option>");
                        }
                    });
                    $.ajaxSetup({
                        async: true
                    });

                } else {
                    $("#HedgingFileId").append("<option selected value='" + -1 + "'>" + "无" + "</option>");
                }
            },
        }
    }
};

var caseQuery = {

    List: function () {
        $("#postForm").ajaxPost(AP_ROOT + "IPR/PatentCaseList/CaseSearchList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.CaseList, function (i, c) {
                            var customerNames = new Array();
                            if (c.CaseCustomers != null) {
                                $.each(c.CaseCustomers, function (j, cc) {
                                    customerNames.push(cc.CustomerBasic.CustomerName);
                                });
                            }
                            $("tbody", "#tblCaseList").addRow(
                                "<input type='checkbox' id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' customerid=" + c.CaseBasicInfo.FirstApplicantId + " value='" + c.CaseBasicInfo.CaseId + "'>",
                                "<a href='javascript:void(0)' onclick='javascript:caseQuery.Open(" + c.CaseBasicInfo.CaseId + ")'>" + c.CaseBasicInfo.CaseNo + "</a>",
                                c.CaseCustomers != null ? customerNames.join() : '',
                                $.caseType.getCaseTypeName(c.CaseBasicInfo.CaseTypeId),
                                $.casePhase.getcasePhaseName(c.CaseBasicInfo.CaseTypeId, c.CaseBasicInfo.CasePhaseId),
                                c.CaseBasicInfo.CaseRequestNo,
                                c.CaseBasicInfo.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseRequestDate)),
                                c.CaseBasicInfo.CaseOriginPeopleName,
                                c.CaseBasicInfo.ProcuratorName,
                                c.CaseBasicInfo.CopywriterName,
                                c.CaseBasicInfo.CaseOfficerName,
                                c.CaseBasicInfo.ReminderDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.ReminderDate)),
                                c.CaseBasicInfo.Deadline == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.Deadline))
                                );
                    });

                    $("tfoot", "#tblCaseList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.Caselist").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: caseQuery.List,
                        callBackArgs: null
                    });

                    caseQuery.BindMenu();

                } else {

                    $("tfoot", "#tblCaseList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    BindMenu: function () {
        $('div.gridSection').contextMenu('menu', {
            menuStyle: {
                width: '152px'
            },

            itemStyle: {
                width: '150px'
            },

            bindings: {

                'inprocess': function (t, e) {
                    var caseId = $(e).find("span").html();
                    caseQuery.InProcess(caseId);
                },

                /**/
                'push': function (t, e) {
                    caseInfo.Multiple.Edit.Open();
                },

                /*文件导入*/
                'fileImport': function (t, e) {
                    caseInfo.Multiple.Import.Open();
                },

                /*转文*/
                'transfer': function (t, e) {
                    caseInfo.Multiple.Transfer.Open();
                },
            },
            onContextMenu: function (e) {
                return true;
            },
            onShowMenu: function (e, menu) {
                var caseId = $(e.target).parents("tr").find("#chkCaseId").val();
                $('#inprocess', menu).append("<span style='display:none'>" + caseId + "</span>");
                return menu;
            }
        });
    },

    ExportToExcel: function () {

        $("#postForm").ajaxPost(AP_ROOT + "IPR/CaseList/CaseListExportToExcel", function (response) {
            if (response.IsSuccess) {
                window.open(AP_ROOT + "IPR/CaseFileCenter/CaseListExportToExcelDownload?fileName=" + response.Data);
                $.showModalMessageBox("导出成功.");
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    InProcess: function (caseId) {

        var search = {};

        search.CaseId = caseId;
        search.PageId = $("#SearchCondition_PageId").val();
        search.PageNo = $("#SearchCondition_PageNo").val();
        search.PageSize = $("#SearchCondition_PageSize").val();
        search.PageName = $("#SearchCondition_PageName").val();

        search.CustomerName = $("#SearchCondition_CustomerName").val();
        search.CaseNos = $("#SearchCondition_CaseNos").val();
        search.CaseTypeId = $("#SearchCondition_CaseTypeId").val();
        search.CasePhaseId = $("#SearchCondition_CasePhaseId").val();
        search.CaseOriginPeopleName = $("#SearchCondition_CaseOriginPeopleName").val();
        search.CaseCopywriterName = $("#SearchCondition_CaseCopywriterName").val();
        search.CaseProcuratorName = $("#SearchCondition_CaseProcuratorName").val();
        search.CaseOfficerName = $("#SearchCondition_CaseOfficerName").val();
        search.CaseRequestDateFrom = $("#SearchCondition_CaseRequestDateFrom").val() == '' ? null : $("#SearchCondition_CaseRequestDateFrom").val();
        search.CaseRequestDateTo = $("#SearchCondition_CaseRequestDateTo").val() == '' ? null : $("#SearchCondition_CaseRequestDateTo").val();
        search.SearchByMonthAndDay = $("#SearchCondition_SearchByMonthAndDay").attr("checked") == "checked";

        search.CaseDeadlineFrom = $("#SearchCondition_CaseDeadlineFrom").val() == '' ? null : $("#SearchCondition_CaseDeadlineFrom").val();
        search.CaseDeadlineTo = $("#SearchCondition_CaseDeadlineTo").val() == '' ? null : $("#SearchCondition_CaseDeadlineTo").val();


        var url = AP_ROOT + "IPR/Case/CreateUpdate?typeId=1&caseId=" + caseId + "&k=" + escape(JSON.stringify(search));
        window.open(url);

    },

    /*创建案件*/
    Open: function (caseId) {
        caseQuery.InProcess(caseId);
    },

    Reset: function () {
        $("#postForm :text").each(function () {
            $(this).val('');
        });
        $("#postForm :hidden").each(function () {
            $(this).val('');
        });

        $("#SearchCondition_SearchByMonthAndDay").attr("checked", false);
    },

    Selected: function (e) {

        if ($(e).attr("checked") == "checked") {
            $.checkbox.all("chkCaseId");
        } else {
            $.checkbox.not("chkCaseId");
        }
    },

}

$(document).ready(function () {

    $(document).click(function (e) {
        $("#divCasePhaseCheckBoxList").die().hide();
        $("#divCaseTypeCheckBoxList").die().hide();
        $("#divCaseFileTypeList").die().hide();
        $("#div_CaseFileTypeList").die().hide();
        
        $("#divUserList").die().hide();
        $("#divUsers").die().hide();
    });

    caseQuery.List();


    $("#chkCaseAll").die().live("click", function () {
        caseQuery.Selected(this);
    });

    $("#btnCaseSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);
 
        caseQuery.List();
    });

    $("#btnCaseExportToExcel").click(function () {
        caseQuery.ExportToExcel();
    });

    $("#btnCaseSearchReset").click(function () {
        caseQuery.Reset();
    });

    $("#SearchCondition_CasePhaseName").die().live("click", function () {
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

    $("#SearchCondition_CaseTypeName").die().live("click", function () {
        var tirgger = this;
        var html = $.caseType.getCaseTypeCheckBoxListHtml();
        $(".divcaseconditioncasetypes").html(html);
        $("#hidCaseTypeId").val("SearchCondition_CaseTypeId");
        $("#hidCaseTypeName").val($(tirgger).attr("id"));
        $("#divCaseTypeCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 15,
            "top": $(tirgger).position().top + 110
        }).toggle();

        return false;
    });

    $("#btnCaseBatchEditCancel,#btnCaseBatchEditClose").die().live("click", function () {
        caseInfo.Multiple.Edit.Close();
    });

    $("#btnCaseBatchEdit").die().live("click", function () {
        caseInfo.Multiple.Edit.Create();
    });

    $("#btnCaseFileBatchImportCancel,#btnCaseFileBatchImportClose").die().live("click", function () {
        caseInfo.Multiple.Import.Close();
    });

    $("#btnCaseFileBatchImport").die().live("click", function () {
        caseInfo.Multiple.Import.Create();
    });

    $("#CaseOfficerName").die().live("click", function () {
        $("#hidUserId").val("CaseOfficer");
        $("#hidUserName").val("CaseOfficerName");
        $("#divUsers").die().css({
            "position": "absolute",
            "left": $("#CaseOfficerName").offsetParent().position().left + 15,
            "top": $("#CaseOfficerName").offsetParent().position().top + 25,
            "z-index": 9999
        }).show();
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

    $("#SearchCondition_CaseOriginPeopleName").die().live("click", function () {
        $("#hidUserId").val("SearchCondition_CaseOriginPeopleId");
        $("#hidUserName").val("SearchCondition_CaseOriginPeopleName");
        $("#divUserList").die().css({
            "position": "absolute",
            "left": $("#SearchCondition_CaseOriginPeopleName").position().left + 0,
            "top": $("#SearchCondition_CaseOriginPeopleName").position().top + 25,
            "z-index": 9999
        }).show();
        return false;
    });

    $("#SearchCondition_CaseOfficerName").die().live("click", function () {
        $("#hidUserId").val("SearchCondition_CaseOfficerId");
        $("#hidUserName").val("SearchCondition_CaseOfficerName");
        $("#divUserList").die().css({
            "position": "absolute",
            "left": $("#SearchCondition_CaseOfficerName").position().left + 0,
            "top": $("#SearchCondition_CaseOfficerName").position().top + 25,
            "z-index": 9999
        }).show();
        return false;
    });

    $("#SearchCondition_CaseCopywriterName").die().live("click", function () {
        $("#hidUserId").val("SearchCondition_CaseCopywriterId");
        $("#hidUserName").val("SearchCondition_CaseCopywriterName");
        $("#divUserList").die().css({
            "position": "absolute",
            "left": $("#SearchCondition_CaseCopywriterName").position().left + 0,
            "top": $("#SearchCondition_CaseCopywriterName").position().top + 25,
            "z-index": 9999
        }).show();
        return false;
    });

    $("#SearchCondition_CaseProcuratorName").die().live("click", function () {
        $("#hidUserId").val("SearchCondition_CaseProcuratorId");
        $("#hidUserName").val("SearchCondition_CaseProcuratorName");
        $("#divUserList").die().css({
            "position": "absolute",
            "left": $("#SearchCondition_CaseProcuratorName").position().left + 0,
            "top": $("#SearchCondition_CaseProcuratorName").position().top + 25,
            "z-index": 9999
        }).show();
        return false;
    });

    $("#divUserList").find("li").die().live("click", function () {
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        var currentSelectedControl = $("#hidUserName").val();
        var currentSelectedIdControl = $("#hidUserId").val();
        $("#" + currentSelectedControl).val(userName);
        $("#" + currentSelectedIdControl).val(userId);
        $("#divUsers").hide();
    });

    $("#divUsers").find("li").die().live("click", function () {
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        var currentSelectedControl = $("#hidUserName").val();
        var currentSelectedIdControl = $("#hidUserId").val();
        $("#" + currentSelectedControl).val(userName);
        $("#" + currentSelectedIdControl).val(userId);
        $("#divUsers").hide();
    });

    $("#lnkCaseFileTypeId").die().live("click", function () {
        var tirgger = $("#CaseFileTypeName");

        $(".divCaseFileTypeList").html($.caseFileType.getAllCaseFileTypeListHtml());

        $("#divCaseFileTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left + 15,
            "top": $(tirgger).offsetParent().position().top + 32,
            "z-index": 9999
        }).toggle();

        $("#hidCaseFileTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFileTypeId").val($("#CaseFileTypeId").attr("id"));//Id

        return false;
    });

    $("#lnkCaseFileTransformedTypeId").die().live("click", function () {
        var tirgger = $("#CaseFileTypeName");

        $(".divCaseFileTypeList").html($.caseFileType.getCaseTransformedFileTypeListHtml());

        $("#divCaseFileTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left + 15,
            "top": $(tirgger).offsetParent().position().top + 32,
            "z-index": 9999
        }).toggle();

        $("#hidCaseFileTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFileTypeId").val($("#CaseFileTypeId").attr("id"));//Id

        return false;
    });

    $("#divCaseFileTypeList").find("li").die().live("click", function () {
        var caseFileTypeId = $(this).find("a").attr("id");
        var caseFileTypeName = $(this).find("a").text();
        var caseFileTypeNameText = $(this).find("a").attr("text");
        var currentSelectedControl = $("#hidCaseFileTypeName").val();
        var currentSelectedIdControl = $("#hidCaseFileTypeId").val();
        $("#" + currentSelectedControl).val(caseFileTypeName);
        $("#" + currentSelectedIdControl).val(caseFileTypeId);

        var hedgingFileTypeId = $(this).find("a").attr("hedgingFileTypeId");
        var hedgingFeeTypeId = $(this).find("a").attr("hedgingFeeTypeId");

        $("#divCaseFileTypeList").hide();
    });

    $("#flCaseFile").die().live("change", function () {
        $("#txtCaseFilePath").val($("#flCaseFile").val());
    });

    $("#SearchCondition_CasePhaseName").die().live("click", function () {
        var tirgger = this;
        var html = $.casePhase.getCasePhaseCheckBoxListHtml();
        $(".divcaseconditioncasephases").html(html);
        $("#hidCasePhaseId").val("SearchCondition_CasePhaseId");
        $("#hidCasePhaseName").val("SearchCondition_CasePhaseName");
        $("#divCasePhaseCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 0,
            "top": $(tirgger).position().top + 25,
            "z-index": 9999
        }).toggle();

        return false;
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
    $("#SearchCondition_CaseTypeName").die().live("click", function () {
        var tirgger = this;
        var html = $.caseType.getCaseTypeCheckBoxListHtml();
        $(".divcaseconditioncasetypes").html(html);
        $("#hidCaseTypeId").val("SearchCondition_CaseTypeId");
        $("#hidCaseTypeName").val($(tirgger).attr("id"));
        $("#divCaseTypeCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 0,
            "top": $(tirgger).position().top + 25,
            "z-index": 9999
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
    $("#SearchCondition_CaseFeeTypeName").die().live("click", function () {
        var tirgger = this;
        var html = $.caseFeeType.getCaseFeeTypeCheckBoxListHtml();
        $(".divcaseconditioncasefeetypes").html(html);
        $("#hidCaseFeeTypeId").val("SearchCondition_CaseFeeTypeId");
        $("#hidCaseFeeTypeName").val($(tirgger).attr("id"));
        $("#divCaseFeeTypeCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 0,
            "top": $(tirgger).position().top + 25,
            "z-index": 9999
        }).toggle();

        return false;
    });

    $("#btnCaseListExportToWordCancel,#btnCaseListExportToWordClose").die().live("click", function () {
        caseInfo.Multiple.Transfer.Close();
    });

    $("#btnCaseListExportToWordCreate").die().live("click", function () {
        caseInfo.Multiple.Transfer.Export();
    });

    $("#btnCaseListExportToWordUpload").die().live("click", function () {
        caseInfo.Multiple.Transfer.Upload();
    });
 
});


