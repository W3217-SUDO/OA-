/*案件类型*/
var caseFileType = {
    List: function () {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CaseFileTypeList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseFileTypeList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.CaseFileTypes, function (i, c) {
                        $("tbody", "#tblCaseFileTypeList").addRow(c.FileTypeId,
                                                                  c.FileTypeName,
                                                                  c.CaseTypeName,
                                                                  c.IsOfficeFileType ? "是" : "否",
                                                                  c.CanBatchUpload ? "是":"否",
                                                                  c.IsTransformed ? "是" : "否",
                                                                  c.TransformedFileName,
                                          "<a href='javascript:void(0)' onclick='javascript:caseFileType.Open(" + c.FileTypeId + ")'>修改</a>");

                    });

                    $("tfoot", "#tblCaseFileTypeList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.casefiletype").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: caseFileType.List,
                        callBackArgs: null
                    });
                } else {
                    
                    $("tfoot", "#tblCaseFileTypeList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    /*创建案件文档类型*/
    Open: function (caseFileTypeId) {
        var url =  AP_ROOT + AP_PAGE_ID +  "/System/SystemCenter/CaseFileType";
        var data = {
            caseFileTypeId: caseFileTypeId
        };
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            $('#caseFileTypeModal').modal({ backdrop: 'static', keyboard: false });
            $('#caseFileTypeModal').on('hidden.bs.modal', function () {
                $("#caseFileTypeModal").remove();
            });
        });

        //$('.caseFileType').load(url, data, function (result) {
        //    $.closeLoading();
        //    $('#caseFileTypeModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },
    
    //保存案件文档类型
    CreateUpdate: function () {

        if ($("#CaseFileTypeId").val() == '') {
            $.showModalMessageBox("请输入8位数字类型Id号.");
            return false;
        }

        if ($("#CaseFileType_FileTypeName").val() == '') {
            $.showModalMessageBox("请输入文档类型名.");
            return false;
        }


        if ($("#CaseFileType_CaseTypeId").val() == '') {
            $.showModalMessageBox("请选择案件类型.");
            return false;
        }

        if ($("#CaseFileType_IsTransformed").attr('checked') == 'checked' && $("#CaseFileType_TransformedFileName").val() == '') {
            $.showModalMessageBox("请输入转文模板文件名.");
            return false;
        }

        $("#CaseFileType_FileTypeId").val($("#CaseFileTypeId").val());

        $("#CaseFileType").ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CaseFileTypeCreateUpdate", function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                $('#caseFileTypeModal').modal('hide');
                caseFileType.List();
            }
            else {
                 $.showModalMessageBox(response.Message);
            }
        });
    },

    //保存案件文档类型与案件类型关联关系
    CaseTypeCreateUpdate: function () {

        var caseTypeIds = $.checkbox.vals("chkCaseTypeId");

        var data = {
            caseFileTypeId: parseInt($("#CaseFileTypeId").val()),
            caseTypeIds: caseTypeIds
        }

        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CaseFileTypeCaseTypeCreate", data, function (response) {

            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                $('#CaseTypeModal').modal('hide');
                caseType.List();
            }
            else {
                ;
                $.showModalMessageBox(response.Message);
            }
        });
    },


    CaseFeeTypeCreateUpdate: function () {

        var caseFeeTypeIds = $.checkbox.vals("chkCaseFeeTypeId");
        var data = {
            caseFileTypeId: parseInt($("#CaseFileTypeId").val()),
            caseFeeTypeIds: caseFeeTypeIds
        }

        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CaseFileTypeCaseFeeTypeCreate", data, function (response) {

            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                $('#CaseFeeTypeModal').modal('hide');
                caseType.List();
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    /*案件类型*/
    CaseTypeList: function (caseFileTypeId) {
        var data = {
            caseFileTypeId: caseFileTypeId
        };
        var url =  AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CaseFileTypeCaseTypeList";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            $('#CaseTypeModal').modal({ backdrop: 'static', keyboard: false });
            $('#CaseTypeModal').on('hidden.bs.modal', function () {
                $("#CaseTypeModal").remove();
            });
        });

        //$('.caseType').load(url, data, function (result) {
        //    $.closeLoading();
        //    $('#CaseTypeModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },

    CaseFileTypeListClose: function () {
        $('#CaseFeeTypeModal').modal('hide');
    },

    CaseFeeTypeList: function (caseFileTypeId) {
        var url =  AP_ROOT + AP_PAGE_ID +  "/System/SystemCenter/CaseFileTypeCaseFeeTypeList";
        var data = {
            caseFileTypeId: caseFileTypeId
        };
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            $('#CaseFeeTypeModal').modal({ backdrop: 'static', keyboard: false });
            $('#CaseFeeTypeModal').on('hidden.bs.modal', function () {
                $("#CaseFeeTypeModal").remove();
            });
        });

        //$('.caseFeeType').load(url, data, function (result) {
        //    $.closeLoading();
        //    $('#CaseFeeTypeModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },
}

$(document).ready(function () {

    //caseFileType.List();

    $(document).off('click', '.CaseFileTypeCreate').on('click', '.CaseFileTypeCreate', function () {
        caseFileType.Open();
    });

    $(document).off('click', '#btnCaseFileType').on('click', '#btnCaseFileType', function () {
        caseFileType.CreateUpdate();
    });

    $(document).off('click', '#btnCaseFileTypeCreate').on('click', '#btnCaseFileTypeCreate', function () {
        caseFileType.Open();
    });

    $(document).off('click', '#btnCaseFileTypeClose').on('click', '#btnCaseFileTypeClose', function () {
        $('#caseFileTypeModal').modal('hide');
    });

    $(document).off('click', '#btnCaseFileTypeCancel').on('click', '#btnCaseFileTypeCancel', function () {
        $('#caseFileTypeModal').modal('hide');
    });

    $(document).off('click', '#btnCaseTypeClose').on('click', '#btnCaseTypeClose', function () {
        $('#CaseTypeModal').modal('hide');
    });

    $(document).off('click', '#btnCaseTypeCancel').on('click', '#btnCaseTypeCancel', function () {
        $('#CaseTypeModal').modal('hide');
    });

    $(document).off('click', '#btnCaseTypeCreate').on('click', '#btnCaseTypeCreate', function () {
        caseFileType.CaseTypeCreateUpdate();
    });

    $(document).off('click', '#btnCaseFeeTypeClose').on('click', '#btnCaseFeeTypeClose', function () {
        $('#CaseFeeTypeModal').modal('hide');
    });

    $(document).off('click', '#btnCaseFeeTypeCreate').on('click', '#btnCaseFeeTypeCreate', function () {
        caseFileType.CaseFeeTypeCreateUpdate();
    });

    $(document).off('click', '#btnCaseFeeTypeCancel').on('click', '#btnCaseFeeTypeCancel', function () {
        $('#CaseFeeTypeModal').modal('hide');
    });

    $(document).off('click', '#btnCaseFileTypeSearch').on('click', '#btnCaseFileTypeSearch', function () {
        caseFileType.List();
    });
});


