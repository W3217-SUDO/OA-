/*案件类型*/
var court = {
    List: function () {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CourtList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCourtList").clearRow();
                if (response.Data.TotalItemCount > 0) {

                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.Courts, function (i, c) {
                        $("tbody", "#tblCourtList").addRow(c.CourtId, c.CourtName,
                            c.CourtCode, c.DistrictCode,
                            c.DistrictName, c.CourtType,
                           "<a href='javascript:void(0)' onclick='javascript:court.Open(" + c.CourtId + ")'>修改</a>");

                    });

                    $("tfoot", "#tblCourtList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.court").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: court.List,
                        callBackArgs: null
                    });
                } else {
                    $("tfoot", "#tblCourtList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    /* 保存法院*/
    CreateUpdate: function () {

        if ($("#Court_CourtName").val() == '') {
            $.showModalMessageBox("请输入法院名称.");
            return false;
        }

        if ($("#Court_CourtCode").val() == '') {
            $.showModalMessageBox("请输入法院代字.");
            return false;
        }

        $("#Court").ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CourtCreateUpdate", function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                $('#CourtModal').modal('hide');
                court.List();
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    /*创建法院*/
    Open: function (courtId) {
        var data = {
            courtId: courtId,
        }
         
        var url =  AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/Court";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            $('#CourtModal').modal({ backdrop: 'static', keyboard: false });
            $('#CourtModal').on('hidden.bs.modal', function () {
                $("#CourtModal").remove();
            });
        });

    },

    Close: function () {
        $('#CourtModal').modal('hide');
     },
}

$(document).ready(function () {

    $(document).off('click', '.courtCreate').on('click', '.courtCreate', function () {
        court.Open();
    });

    $(document).off('click', '#btnCourtCreate').on('click', '#btnCourtCreate', function () {
        court.Open();
    });

    $(document).off('click', '#btnCourtSearch').on('click', '#btnCourtSearch', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);
        court.List();
    });

    $(document).off('click', '#btnCourt').on('click', '#btnCourt', function () {
        court.CreateUpdate();
    });

    $(document).off('click', '#btnCourtClose').on('click', '#btnCourtClose', function () {
        court.Close();
    });

    $(document).off('click', '#btnCourtCancel').on('click', '#btnCourtCancel', function () {
        court.Close();
    });
});


