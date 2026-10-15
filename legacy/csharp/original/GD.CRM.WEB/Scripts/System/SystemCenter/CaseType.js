/*案件类型*/
var caseType = {
    List: function () {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CaseTypeList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseTypeList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.CaseTypes, function (i, c) {
                        $("tbody", "#tblCaseTypeList").addRow(
                            c.CaseTypeId,
                            c.CaseTypeName,
                            c.CaseTypeShortCode,
                            c.CreateUser,
                            c.CreateTime == null ? '' : getDateTime(convertJsonDateToJSDate(c.CreateTime)),
                            c.ChangeUser,
                            c.ChangeTime == null ? '' : getDateTime(convertJsonDateToJSDate(c.ChangeTime)),
                            "<a href='javascript:void(0)' onclick='javascript:caseType.Open(" + c.CaseTypeId + ")'>修改</a>");

                    });

                    $("tfoot", "#tblCaseTypeList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.casetype").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: caseType.List,
                        callBackArgs: null
                    });
                } else {
                    $("tfoot", "#tblCaseTypeList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    /* 保存案件类型*/
    CreateUpdate: function () {

        if ($("#CaseType_CaseTypeName").val() == '') {
            $.showModalMessageBox("请输入类型名称.");
            return false;
        }

        if ($("#CaseType_CaseTypeShortCode").val() == '') {
            $.showModalMessageBox("请输入类型字母名称.");
            return false;
        }

        $("#CaseType").ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CaseTypeCreateUpdate", function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                $('#CaseTypeModal').modal('hide');
                caseType.List();
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    /* 保存案件类型与阶段关联关系*/
    CasePhaseCreateUpdate: function () {
        var phaseIds = new Array();
        $("input[type='checkbox']:checked").each(function () {
            phaseIds.push(this.value);
        });

        var data = {
            caseTypeId: parseInt($("#CaseTypeId").val()),
            casePhaseIds: phaseIds
        }
         $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CaseTypeCasePhaseCreate", data, function (response) {
             if (response.IsSuccess) {
                 $.showModalMessageBox("保存成功.");
                 $('#CasePhaseModal').modal('hide');
                 caseType.List();
             } else {
                 $.showModalMessageBox(response.Message);
             }
         });
    },

    /*创建案件类型*/
    Open: function (caseTypeId) {
        var data = {
            caseTypeId: caseTypeId,
        }
         
        var url =  AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CaseType";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            $('#CaseTypeModal').modal({ backdrop: 'static', keyboard: false });
            $('#CaseTypeModal').on('hidden.bs.modal', function () {
                $("#CaseTypeModal").remove();
            });
        });

        //$('.casetype').load(url, data, function (result) {
        //    $.closeLoading();
        //    $('#CaseTypeModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },

    Close: function () {
        $('#CaseTypeModal').modal('hide');
     },

    CaseFileTypeListClose: function () {
        $('#CaseFeeTypeModal').modal('hide');
    },

    /*案件阶段*/
    CasePhaseList: function (caseTypeId) {
        var data = {
            caseTypeId:caseTypeId
        };
        
        var url =  AP_ROOT + AP_PAGE_ID +  "/System/SystemCenter/CaseTypeCasePhaseList";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            $('#CasePhaseModal').modal({ backdrop: 'static', keyboard: false });
            $('#CasePhaseModal').on('hidden.bs.modal', function () {
                $("#CasePhaseModal").remove();
            });
        });

        //$('.CasePhaseId').load(url, data, function (result) {
        //    $.closeLoading();
        //    $('#CasePhaseModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },

    /*文件类型*/
    CaseFileTypeList: function (caseTypeId) {
        var data = {
            caseTypeId: caseTypeId
        };
        
        var url =  AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CaseTypeCaseFileTypeList";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            $('#CaseFileTypeModal').modal({ backdrop: 'static', keyboard: false });
            $('#CaseFileTypeModal').on('hidden.bs.modal', function () {
                $("#CaseFileTypeModal").remove();
            });
        });

        //$('.CaseFileType').load(url, data, function (result) {
        //    $.closeLoading();
        //    $('#CaseFileTypeModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },
}

$(document).ready(function () {
    caseType.List();

    $(document).off('click', '.caseTypeCreate').on('click', '.caseTypeCreate', function () {
        caseType.Open();
    });

    $(document).off('click', '#btnCaseTypeCreate').on('click', '#btnCaseTypeCreate', function () {
        caseType.Open();
    });

    $(document).off('click', '#btnCaseType').on('click', '#btnCaseType', function () {
        caseType.CreateUpdate();
    });

    $(document).off('click', '#btnCaseTypeClose').on('click', '#btnCaseTypeClose', function () {
        caseType.Close();
    });

    $(document).off('click', '#btnCaseTypeCancel').on('click', '#btnCaseTypeCancel', function () {
        caseType.Close();
    });

    $(document).off('click', '#btnCasePhaseClose').on('click', '#btnCasePhaseClose', function () {
        $('#CasePhaseModal').modal('hide');
    });

    $(document).off('click', '#btnCasePhaseCancel').on('click', '#btnCasePhaseCancel', function () {
        $('#CasePhaseModal').modal('hide');
    });

    $(document).off('click', '#btnCasePhaseCreate').on('click', '#btnCasePhaseCreate', function () {
        caseType.CasePhaseCreateUpdate();
    });

    $(document).off('click', '#btnCaseTypeSearch').on('click', '#btnCaseTypeSearch', function () {
        caseType.List();
    });

});


