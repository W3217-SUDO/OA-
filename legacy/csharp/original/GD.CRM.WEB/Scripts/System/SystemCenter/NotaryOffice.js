var notaryOffice = {
    List: function () {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/NotaryOfficeList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblNotaryOfficeList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.NotaryOffices, function (i, c) {
                        $("tbody", "#tblNotaryOfficeList").addRow(
                            c.NotaryOfficeId,
                            c.NotaryOfficeName,
                            c.NotaryOfficeCode,
                            c.TemplateName,
                            c.CreateUser,
                            c.CreateTime == null ? '' : getDateTime(convertJsonDateToJSDate(c.CreateTime)),
                            c.ChangeUser,
                            c.ChangeTime == null ? '' : getDateTime(convertJsonDateToJSDate(c.ChangeTime)),
                           "<a href='javascript:void(0)' onclick='javascript:notaryOffice.Open(" + c.NotaryOfficeId + ")'>修改</a>");
                    });
                    $("tfoot", "#tblNotaryOfficeList").show();
                    $(".simple-grid-none-data-wrap").hide();
                    $(".pull-right.page-box.notaryOffice").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: notaryOffice.List,
                        callBackArgs: null
                    });
                } else {
                    $("tfoot", "#tblNotaryOfficeList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    /* 保存公证处*/
    CreateUpdate: function () {
        if ($("#NotaryOffice_NotaryOfficeName").val() == '') {
            $.showModalMessageBox("请输入公证处名称.");
            return false;
        }
        if ($("#NotaryOffice_NotaryOfficeCode").val() == '') {
            $.showModalMessageBox("请输入公证处代码.");
            return false;
        }
        $("#NotaryOffice").ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/NotaryOfficeCreateUpdate", function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                $('#NotaryOfficeModal').modal('hide');
                notaryOffice.List();
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    /*创建公证处*/
    Open: function (notaryOfficeId) {
        var data = {
            notaryOfficeId: notaryOfficeId,
        }
        var url =  AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/NotaryOffice";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            $('#NotaryOfficeModal').modal({ backdrop: 'static', keyboard: false });
            $('#NotaryOfficeModal').on('hidden.bs.modal', function () {
                $("#NotaryOfficeModal").remove();
            });
        });
    },

    Close: function () {
        $('#NotaryOfficeModal').modal('hide');
     },
}

$(document).ready(function () {

    notaryOffice.List();

    $(document).off('click', '.notaryOfficeCreate').on('click', '.notaryOfficeCreate', function () {
        notaryOffice.Open();
    });

    $(document).off('click', '#btnNotaryOfficeCreate').on('click', '#btnNotaryOfficeCreate', function () {
        notaryOffice.Open();
    });

    $(document).off('click', '#btnNotaryOfficeSearch').on('click', '#btnNotaryOfficeSearch', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(15);
        notaryOffice.List();
    });

    $(document).off('click', '#btnNotaryOffice').on('click', '#btnNotaryOffice', function () {
        notaryOffice.CreateUpdate();
    });

    $(document).off('click', '#btnNotaryOfficeClose').on('click', '#btnNotaryOfficeClose', function () {
        notaryOffice.Close();
    });

    $(document).off('click', '#btnNotaryOfficeCancel').on('click', '#btnNotaryOfficeCancel', function () {
        notaryOffice.Close();
    });
});


