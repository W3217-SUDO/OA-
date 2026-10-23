/*案件批量处理*/

function AssociateCustomer(div, ctlid, ctlname) {
    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;

    this.Customer = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") { return false; }
        var curobj = new Object();
        curobj.keyword = name;
        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CustomerList", curobj, function (response) {
            $(div).find(".i_common_list").empty();
            if (response.IsSuccess) {
                if (response.Data) {
                    var html = "";
                    $.each(response.Data.Customers, function (i, c) {
                        html += '<a href="javascript:void(0)" customerid=' + c.CustomerBasic.CustomerId + ' >' + c.CustomerBasic.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").click(function () {
                        $(ctlid).val($(this).attr("customerId"));
                        $(ctlname).val($(this).text());
                        $(div).hide();
                    });
                }
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        }, false);

        $(div).css({
            "position": "absolute",
            "left": $(ctlname).position().left + 15,
            "top": $(ctlname).position().top + 110
        }).toggle();
    }

    $(ctlname).bind('keyup', { obj: this }, function (event) {
        if (event.keyCode == 38) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).prev().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).prev().addClass("hover");
                        $(hover).prev().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 40) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).next().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).next().addClass("hover");
                        $(hover).next().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 13) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    $(hover).click();
                }
            }
        } else {
            clearTimeout(event.data.obj.Event);
            event.data.obj.Event = setTimeout(function () { event.data.obj.Customer(event.data.obj); }, 500);
        }
    });

    $(ctlname).bind('blur', { obj: this }, function (event) {
        if ($(this).val() == "" || ($(this).val() == $(this).attr("mod-notice-tip"))) {
            event.data.obj.GlobalName = "";
            $(ctlid).val("");
        }
        if ($(ctlid).val() == "") {
            if ($(this).attr("mod-notice-tip")) {
                $(this).val($(this).attr("mod-notice-tip"));
            } else {
                $(this).val("");
            }
        }
        //        if (event.data.obj.GlobalName != "") {
        //            $(this).val(event.data.obj.GlobalName);
        //            $(ctlid).val(event.data.obj.GlobalID);
        //        }
    });

    return this;
}

var cases = {
    List: function() {

        var search = {};
        search.Search = GV_IPRSearch.Condition;
        search.SearchCondition = {};
        search.SearchCondition.PageNo = $("#SearchCondition_PageNo").val();
        search.SearchCondition.PageSize = $("#SearchCondition_PageSize").val();
        search.SearchCondition.ReminderTypeId = $("#SearchCondition_ReminderTypeId").val();
        search.SearchCondition.CategoryTypeId = $("#SearchCondition_CategoryTypeId").val();
        search.SearchCondition.Keyword = $("#SearchCondition_Keyword").val();
        search.SearchCondition.CustomerId = $("#SearchCondition_CustomerId").val();
        search.SearchCondition.CustomerKeyword = $("#txtCustomerNo").val();

        if ($("#txtCaseNo").val() != '') {
            search.SearchCondition.Keyword = $("#txtCaseNo").val();
        }
        search.SearchCondition.CasePhaseId = $("#SearchCondition_CasePhaseId").val();
        search.SearchCondition.CaseTypeId = $("#SearchCondition_CaseTypeId").val();
        search.SearchCondition.CaseRequestDateStart = $("#SearchCondition_CaseRequestDateStart").val();
        search.SearchCondition.CaseRequestDateEnd = $("#SearchCondition_CaseRequestDateEnd").val();
        search.SearchCondition.SearchByMonthAndDay = $("#SearchCondition_SearchByMonthAndDay").prop("checked") == true;

        $.ajaxPostJson( AP_ROOT + AP_PAGE_ID + "/IPR/Case/Cases", JSON.stringify({ search: search }), function(response) {

            if (response.IsSuccess) {
                $("tbody", "#tblCaseList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.CaseList, function(i, c) {
                        var customerNames = new Array();
                        if (c.CaseCustomers != null) {
                            $.each(c.CaseCustomers, function (j, cc) {
                                customerNames.push(cc.CustomerName);
                            });
                        }

                        $("tbody", "#tblCaseList").addRow(
                            "<input type='checkbox' name='chkCaseId' class='ng-pristine ng-valid' value='" + c.CaseBasicInfo.CaseId + "'>",
                            c.CaseBasicInfo.CaseNo,
                            c.CaseCustomers != null ? customerNames.join() : '',
                            $.caseType.getCaseTypeName(c.CaseBasicInfo.CaseTypeId),
                            $.casePhase.getcasePhaseName(c.CaseBasicInfo.CaseTypeId, c.CaseBasicInfo.CasePhaseId),
                            c.CaseBasicInfo.CaseRequestNo,
                            c.CaseBasicInfo.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseRequestDate)),
                            c.CaseBasicInfo.CaseRegisterDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseRegisterDate)),
                            c.CaseBasicInfo.CaseOriginPeopleName,
                            c.CaseBasicInfo.CaseOriginDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseOriginDate)),
                            c.CaseBasicInfo.ProcuratorName,
                            c.CaseBasicInfo.CopywriterName,
                            //c.CaseBasicInfo.CaseSubmitterName,
                            //c.CaseBasicInfo.CaseSubmitDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseSubmitDate)),
                            c.CaseBasicInfo.CaseOfficerName,
                            c.CaseBasicInfo.Deadline == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.Deadline)),
                            "<a href='javascript:void(0)' onclick='javascript:cases.Open(" + c.CaseBasicInfo.CaseId + ")'>查看</a>");
                    });

                    $("tfoot", "#tblCaseList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.Caselist").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: cases.List,
                        callBackArgs: null
                    });

                    cases.BindMenu();

                } else {
                    $("tfoot", "#tblCaseList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    BindMenu: function() {
        $('div.gridSection').contextMenu('batchEditMenu', {
            menuStyle: {
                width: '152px'
            },

            itemStyle: {
                width: '150px'
            },

            //itemHoverStyle: {
            //    color: '#fff',
            //    backgroundColor: '#0f0',
            //    border: 'none'
            //},

            bindings: {
                'batchEdit': function(t, e) {
                    cases.BatchEdit();
                },

                'caseFileBatchImport': function (t, e) {
                    cases.CaseFileBatchImport();
                },
            },
            onContextMenu: function(e) {
                return true;
            },
            onShowMenu: function(e, menu) {
                return menu;
            }
        });
    },

    ExportToExcel: function() {

        var search = {};
        search.Search = GV_IPRSearch.Condition;
        search.SearchCondition = {};
        search.SearchCondition.PageNo = $("#SearchCondition_PageNo").val();
        search.SearchCondition.PageSize = $("#SearchCondition_PageSize").val();
        search.SearchCondition.ReminderTypeId = $("#SearchCondition_ReminderTypeId").val();
        search.SearchCondition.CategoryTypeId = $("#SearchCondition_CategoryTypeId").val();
        search.SearchCondition.Keyword = $("#SearchCondition_Keyword").val();
        search.SearchCondition.CustomerId = $("#SearchCondition_CustomerId").val();
        search.SearchCondition.CustomerKeyword = $("#txtCustomerNo").val();
        if ($("#txtCaseNo").val() != '') {
            search.SearchCondition.Keyword = $("#txtCaseNo").val();
        }
        search.SearchCondition.CasePhaseId = $("#SearchCondition_CasePhaseId").val();
        search.SearchCondition.CaseTypeId = $("#SearchCondition_CaseTypeId").val();

        search.SearchCondition.CaseRequestDateStart = $("#SearchCondition_CaseRequestDateStart").val();
        search.SearchCondition.CaseRequestDateEnd = $("#SearchCondition_CaseRequestDateEnd").val();
        search.SearchCondition.SearchByMonthAndDay = $("#SearchCondition_SearchByMonthAndDay").prop("checked") == true;

        $.ajaxPostJson( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseListExportToExcel", JSON.stringify({ search: search }), function(response) {
            if (response.IsSuccess) {
                window.open( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseListExportToExcelDownload?fileName=" + response.Data);
                $.showModalMessageBox("导出成功.");
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    /*创建案件*/
    Open: function(caseId) {
        if (caseId == undefined) {
            var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CreateUpdate?typeId=1";
            window.location = url;
        } else {
            var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CreateUpdate?CaseId=" + caseId;
            window.location = url;
        }
    },

    Reset: function() {

        if (typeof (GV_IPRSearch) != 'undefined') {
            GV_IPRSearch.Condition = null;
        }

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);
        $("#SearchCondition_ReminderTypeId").val('');
        $("#SearchCondition_CategoryTypeId").val('');
        $("#SearchCondition_Keyword").val('');
        $("#SearchCondition_CustomerId").val('');
        $("#SearchCondition_CaseOriginDateStart").val('');
        $("#SearchCondition_CaseOriginDateEnd").val('');
        $("#txtCustomerNo").val('');
        $("#txtCaseNo").val('');
        $("#SearchCondition_CasePhaseName").val('');
        $("#SearchCondition_CasePhaseId").val('');
        $("#SearchCondition_CaseTypeName").val('');
        $("#SearchCondition_CaseTypeId").val('');

    },

    Selected: function(e) {

        if ($(e).prop("checked") == true) {
            $.checkbox.all("chkCaseId");
        } else {
            $.checkbox.not("chkCaseId");
        }
    },

    /*批量案件基本信息*/
    BatchEdit: function() {
        var caseIds = $.checkbox.vals("chkCaseId");
        if (caseIds.length == 0) {
            $.showModalMessageBox("请选择需要修改的案件.");
            return false;
        }

        var data =
        {
            caseIds: caseIds
        };

        var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseBatchEdit";
        $.openLoading();

        $("<div></div>").load(url, data, function(result) {
            $.closeLoading();
            $(document.body).append(result);
            $('#caseBatchEditModal').modal({ backdrop: 'static', keyboard: false });
            $('#caseBatchEditModal').on('hidden.bs.modal', function() {
                $("#caseBatchEditModal").remove();
            });
        });
    },

    /*批量修改*/
    BatchEditCreate: function() {

        if ($("#caseIdList").val().split(',').length > 1 && $("#CaseNo").val() != '') {
            $.showModalMessageBox("不允许同时修改多个案件为同一案件编号.");
            return false;
        }

        $.openLoading();
        $('#caseBatchEdit').ajaxSubmit({
            success: function(response) {
                $.closeLoading();
                if (response.IsSuccess) {
                    $.showModalMessageBox("批量修改成功.");
                    $('#caseBatchEdit').modal('hide');
                } else {
                    $.showModalMessageBox(response.Message);
                }
            }
        });
    },

    /*关闭*/
    BatchEditClose: function() {
        $('#caseBatchEditModal').modal('hide');
    },

    /*批量导入open*/
    CaseFileBatchImport: function() {
        var caseIds = $.checkbox.vals("chkCaseId");
        if (caseIds.length == 0) {
            $.showModalMessageBox("请选择需要导入文件的案件.");
            return false;
        }

        var data =
        {
            caseIds: caseIds
        };

        var url =  AP_ROOT + AP_PAGE_ID + "/IPR/CaseFile/CaseFileBatchImport";
        $.openLoading();

        $("<div></div>").load(url, data, function(result) {
            $.closeLoading();
            $(document.body).append(result);
            $('#caseFileBatchImportModal').modal({ backdrop: 'static', keyboard: false });
            $('#caseFileBatchImportModal').on('hidden.bs.modal', function() {
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
    CaseFileBatchImportClose: function() {
        $('#caseFileBatchImportModal').modal('hide');
    },

    /*批量导入*/
    CaseFileBatchImportCreate: function () {
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

}
$(document).ready(function () {

    $(document).click(function (e) {
        $("#divCasePhaseCheckBoxList").off().hide();
        $("#divCaseTypeCheckBoxList").off().hide();

        $("#divUserList").off().hide();
    });

    cases.List();

    $("#chkCaseAll").off().on("click", function () {
        cases.Selected(this);
    });

    $("#btnCaseSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);
        $("#SearchCondition_ReminderTypeId").val('');
        $("#SearchCondition_CategoryTypeId").val('');
        $("#SearchCondition_Keyword").val('');
        $("#SearchCondition_CustomerId").val('');

        cases.List();
    });

    $("#btnCaseExportToExcel").click(function () {
        cases.ExportToExcel();
    });

    $("#btnCaseSearchReset").click(function () {
        cases.Reset();
    });

    $("#SearchCondition_CasePhaseName").off().on("click", function () {
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

    $("#SearchCondition_CaseTypeName").off().on("click", function () {
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

    $("#btnCaseBatchEditCancel,#btnCaseBatchEditClose").off().on("click", function () {
        cases.BatchEditClose();
    });

    $("#btnCaseBatchEdit").off().on("click", function () {
        cases.BatchEditCreate();
    });

    $("#btnCaseFileBatchImportCancel,#btnCaseFileBatchImportClose").off().on("click", function () {
        cases.CaseFileBatchImportClose();
    });

    $("#btnCaseFileBatchImport").off().on("click", function () {
        cases.CaseFileBatchImportCreate();
    });

    $("#divCaseTypeCheckBoxList").find("li").off().on("click", function (e) {

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

    $("#divCasePhaseCheckBoxList").find("li").off().on("click", function (e) {

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
 
    $("#CaseOfficerName").off().on("click", function () {
        $("#hidUserId").val("CaseOfficer");
        $("#hidUserName").val("CaseOfficerName");
        $("#divUserList").off().css({
            "position": "absolute",
            "left": $("#CaseOfficerName").offsetParent().position().left + 15,
            "top": $("#CaseOfficerName").offsetParent().position().top + 32,
            "z-index": 1200
        }).show();
        return false;
    });

    $("#divUserList").find("li").off().on("click", function () {
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        var currentSelectedControl = $("#hidUserName").val();
        var currentSelectedIdControl = $("#hidUserId").val();
        $("#" + currentSelectedControl).val(userName);
        $("#" + currentSelectedIdControl).val(userId);
        $("#divUsers").hide();
    });

    $("#lnkCaseFileTypeId").off().on("click", function () {
        var tirgger = $("#CaseFileTypeName");
 
        $(".divCaseFileTypeList").html($.caseFileType.getAllCaseFileTypeListHtml());
       
        $("#divCaseFileTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left + 15,
            "top": $(tirgger).offsetParent().position().top + 32,
            "z-index": 1200
        }).toggle();

        $("#hidCaseFileTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFileTypeId").val($("#CaseFileTypeId").attr("id"));//Id

        return false;
    });

    $("#divCaseFileTypeList").find("li").off().on("click", function () {
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

    $("#flCaseFile").off().on("change", function () {
        $("#txtCaseFilePath").val($("#flCaseFile").val());
    });

});


