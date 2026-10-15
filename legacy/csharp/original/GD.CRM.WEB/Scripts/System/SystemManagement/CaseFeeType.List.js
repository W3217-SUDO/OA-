/*案件类型*/
var caseFeeType = {
    List: function () {
        $("#postForm").ajaxPost(AP_ROOT + "SystemCenter/CaseFeeTypeList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseFeeTypeList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.CaseFeeTypes, function (i, c) {
                        $("tbody", "#tblCaseFeeTypeList").addRow(c.FeeTypeId, c.FeeTypeName,
                                        "<a href='javascript:void(0)' onclick='javascript:caseFeeType.CreateUpdate(" + c.FeeTypeId + ")'>修改</a>");
                    });

                    $("tfoot", "#tblCaseFeeTypeList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.CaseFeeType").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: caseFeeType.List,
                        callBackArgs: null
                    });
                } else {
                    $("tfoot", "#tblCaseFeeTypeList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    /*创建案件类型*/
    CreateUpdate: function (caseFeeTypeId) {
        var url = "/SystemCenter/CaseFeeType";
        var data = {
            caseFeeTypeId: caseFeeTypeId
        };
        $('.caseFeeType').load(url,data, function (result) {
            $('#caseFeeTypeModal').modal({ backdrop: 'static', keyboard: false });
        });
    },
}

$(document).ready(function () {

    caseFeeType.List();

    $(".CaseFeeTypeCreate").click(function () {
        caseFeeType.CreateUpdate();
    });

    $("#btnCaseFeeTypeCreate").click(function () {
        caseFeeType.CreateUpdate();
    });

});


