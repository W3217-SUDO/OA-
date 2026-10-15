/*案由*/
var cause = {
    List: function () {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CauseList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCauseList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.Causes, function (i, c) {
                        $("tbody", "#tblCauseList").addRow(
                            c.CauseId,
                            c.CauseName,
                            c.ParentCauseId,
                            c.CreateUser,
                            c.CreateTime == null ? '' : getDateTime(convertJsonDateToJSDate(c.CreateTime)),
                            c.ChangeUser,
                            c.ChangeTime == null ? '' : getDateTime(convertJsonDateToJSDate(c.ChangeTime)),
                           "<a href='javascript:void(0)' onclick='javascript:cause.Open(" + c.CauseId + ")'>修改</a>");
                    });

                    $("tfoot", "#tblCauseList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.causes").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: cause.List,
                        callBackArgs: null
                    });
                } else {
                    $("tfoot", "#tblCauseList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    /* 保存案由*/
    CreateUpdate: function () {
        if ($("#Cause_CauseName").val() == '') {
            $.showModalMessageBox("请输入案由名称.");
            return false;
        }
        $("#Cause").ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CauseCreateUpdate", function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                $('#CauseModal').modal('hide');
                cause.List();
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    /*创建案由*/
    Open: function (causeId) {
        var data = {
            causeId: causeId,
        }
         
        var url =  AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/Cause";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            $('#CauseModal').modal({ backdrop: 'static', keyboard: false });
            $('#CauseModal').on('hidden.bs.modal', function () {
                $("#CauseModal").remove();
            });
        });
    },

    Close: function () {
        $('#CauseModal').modal('hide');
     },
}

$(document).ready(function () {
    cause.List();
    $(document).off('click', '.causeCreate').on('click', '.causeCreate', function () {
        cause.Open();
    });

    $(document).off('click', '#btnCauseCreate').on('click', '#btnCauseCreate', function () {
        cause.Open();
    });

    $(document).off('click', '#btnCauseSearch').on('click', '#btnCauseSearch', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(15);
        cause.List();
    });

    $(document).off('click', '#btnCause').on('click', '#btnCause', function () {
        cause.CreateUpdate();
    });

    $(document).off('click', '#btnCauseClose').on('click', '#btnCauseClose', function () {
        cause.Close();
    });

    $(document).off('click', '#btnCauseCancel').on('click', '#btnCauseCancel', function () {
        cause.Close();
    });
});


