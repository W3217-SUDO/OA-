/*案件类型*/
var paymentType = {

    List: function() {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/PaymentTypeList", function(response) {
            if (response.IsSuccess) {
                $("tbody", "#tblPaymentTypeList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.PaymentTypeList, function(i, p) {
                        $("tbody", "#tblPaymentTypeList").addRow(p.PaymentTypeId,
                                                                 p.PaymentTypeName,
                                                                 p.CaseFeeTypeIdName,
                                                                 p.OrganizationName,
                                                                 p.Account,
                                                                 p.Remark,
                            "<a href='javascript:void(0)' onclick='javascript:paymentType.Open(" + p.PaymentTypeId + ")'>修改</a>");
                    });

                    $("tfoot", "#tblPaymentTypeList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.PaymentType").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: paymentType.List,
                        callBackArgs: null
                    });
                } else {
                    $("tfoot", "#tblPaymentTypeList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    /*创建案件类型*/
    Open: function (paymentTypeId) {
         
        var url =  AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/PaymentType";
        var data = {
            paymentTypeId: paymentTypeId
        };
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            $('#paymentTypeModal').modal({ backdrop: 'static', keyboard: false });
            $('#paymentTypeModal').on('hidden.bs.modal', function () {
                $("#paymentTypeModal").remove();
            });
        });
    },

    Close: function() {
        $('#paymentTypeModal').modal('hide');
    },

    CreateUpdate: function () {

        if ($("#PaymentType_PaymentTypeName").val() == '') {
            $.showModalMessageBox("请输入类型名称.");
            return false;
        }

        var data = {};

        data["PaymentType.PaymentTypeId"] = $("#PaymentType_PaymentTypeId").val();
        data["PaymentType.CaseFeeTypeId"] = $("#PaymentType_CaseFeeTypeId").val();
        data["PaymentType.PaymentTypeName"] = $("#PaymentType_PaymentTypeName").val();
        data["PaymentType.OrganizationName"] = $("#PaymentType_OrganizationName").val();
        data["PaymentType.Account"] = $("#PaymentType_Account").val();
        data["PaymentType.Remark"] = $("#PaymentType_Remark").val();
        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/PaymentTypeCreateUpdate", data, function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                paymentType.Close();
                paymentType.List();
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    PaymentTypeItem: {
        Add: function() {
            var tr = null;
            $("#tblPaymentTypeItemList").find("tr").each(function () {
                if ($(this).css("display") == "none") {
                    tr = $(this).clone().show();
                }
            });
            $("#tblPaymentTypeItemList").append(tr);
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

    //paymentType.List();

    $(document).off('click', '.PaymentTypeCreate').on('click', '.PaymentTypeCreate', function () {
        paymentType.Open();
    });

    $(document).off('click', '#btnPaymentTypeCreate').on('click', '#btnPaymentTypeCreate', function () {
        paymentType.Open();
    });

    $(document).off('click', '#btnPaymentTypeClose').on('click', '#btnPaymentTypeClose', function () {
        paymentType.Close();
    });

    $(document).off('click', '#btnPaymentTypeCancel').on('click', '#btnPaymentTypeCancel', function () {
        paymentType.Close();
    });

    $(document).off('click', '#btnPaymentTypeAddItem').on('click', '#btnPaymentTypeAddItem', function () {
        paymentType.PaymentTypeItem.Add();
    });

    $(document).off('click', '.btn_clear').on('click', '.btn_clear', function () {
        paymentType.PaymentTypeItem.Clear(this);
    });

    $(document).off('click', '.btn_remove').on('click', '.btn_remove', function () {
        paymentType.PaymentTypeItem.Remove(this);
    });

    $(document).off('click', '#btnPaymentType').on('click', '#btnPaymentType', function () {
        paymentType.CreateUpdate();
    });

    $(document).off('click', '#btnPaymentTypeSearch').on('click', '#btnPaymentTypeSearch', function () {
        paymentType.List();
    });
});


