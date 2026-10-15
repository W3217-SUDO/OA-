/*案件类型*/
var caseFeeType = {

    List: function() {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CaseFeeTypeList", function(response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseFeeTypeList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.CaseFeeTypes, function(i, c) {
                        $("tbody", "#tblCaseFeeTypeList").addRow(c.FeeTypeId,
                                                                 c.FeeTypeName,
                                                                 c.CaseTypeName,
                                                                 c.TypeIdName,
                                                                 //c.IsInvoiced ? "是" : "否",
                            "<a href='javascript:void(0)' onclick='javascript:caseFeeType.Open(" + c.FeeTypeId + ")'>修改</a>");
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
    Open: function (caseFeeTypeId) {
         
        var url =  AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CaseFeeType";
        var data = {
            caseFeeTypeId: caseFeeTypeId
        };
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            $('#caseFeeTypeModal').modal({ backdrop: 'static', keyboard: false });
            $('#caseFeeTypeModal').on('hidden.bs.modal', function () {
                $("#caseFeeTypeModal").remove();
            });
        });

        //$('.caseFeeType').load(url, data, function (result) {
        //    $.closeLoading();
        //    $('#caseFeeTypeModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },

    Close: function() {
        $('#caseFeeTypeModal').modal('hide');
    },

    CreateUpdate: function () {

        if ($("#CaseFeeTypeId").val() == '') {
            $.showModalMessageBox("请输入7位数字类型Id号.");
            return false;
        }

        if ($("#CaseFeeType_FeeTypeName").val() == '') {
            $.showModalMessageBox("请输入费用类型名称.");
            return false;
        }

        if ($("#CaseFeeType_CaseTypeId").val() == '') {
            $.showModalMessageBox("请选择案件类型.");
            return false;
        }

        var data = {};

        data["CaseFeeType.FeeTypeId"] = $("#CaseFeeTypeId").val();
        data["CaseFeeType.FeeTypeName"] = $("#CaseFeeType_FeeTypeName").val();
        data["CaseFeeType.TypeId"] = $("#CaseFeeType_TypeId").val();
        data["CaseFeeType.CaseTypeId"] = $("#CaseFeeType_CaseTypeId").val();

        $("#CaseFeeType_FeeTypeId").val($("#CaseFeeTypeId").val());

        $("#CaseFeeType").ajaxPost(AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CaseFeeTypeCreateUpdate", function (response) {
        //$.ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CaseFeeTypeCreateUpdate", data, function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                caseFeeType.Close();
                caseFeeType.List();
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    CaseFeeTypeItem: {
        Add: function() {
            var tr = null;
            $("#tblCaseFeeTypeItemList").find("tr").each(function () {
                if ($(this).css("display") == "none") {
                    tr = $(this).clone().show();
                }
            });
            $("#tblCaseFeeTypeItemList").append(tr);
            return tr;
        },
        Clear: function(e) {
            $(e).parents("tr").find(":input[type='text']").val('');
            $(e).parents("tr").find(":input[type='checkbox']").attr("checked", false);
        },
        Remove: function (e) {
            $(e).parents("tr").remove();
        }
    }
}

$(document).ready(function () {

    //caseFeeType.List();

    $(document).off('click', '.CaseFeeTypeCreate').on('click', '.CaseFeeTypeCreate', function () {
        caseFeeType.Open();
    });

    $(document).off('click', '#btnCaseFeeTypeCreate').on('click', '#btnCaseFeeTypeCreate', function () {
        caseFeeType.Open();
    });

    $(document).off('click', '#btnCaseFeeTypeClose').on('click', '#btnCaseFeeTypeClose', function () {
         caseFeeType.Close();
    });

    $(document).off('click', '#btnCaseFeeTypeCancel').on('click', '#btnCaseFeeTypeCancel', function () {
        caseFeeType.Close();
    });

    $(document).off('click', '#btnCaseFeeTypeAddItem').on('click', '#btnCaseFeeTypeAddItem', function () {
        caseFeeType.CaseFeeTypeItem.Add();
    });

    $(document).off('click', '.btn_clear').on('click', '.btn_clear', function () {
        caseFeeType.CaseFeeTypeItem.Clear(this);
    });

    $(document).off('click', '.btn_remove').on('click', '.btn_remove', function () {
        caseFeeType.CaseFeeTypeItem.Remove(this);
    });

    $(document).off('click', '#btnCaseFeeType').on('click', '#btnCaseFeeType', function () {
        caseFeeType.CreateUpdate();
    });

    $(document).off('click', '#btnCaseFeeTypeSearch').on('click', '#btnCaseFeeTypeSearch', function () {
        caseFeeType.List();
    });
});


