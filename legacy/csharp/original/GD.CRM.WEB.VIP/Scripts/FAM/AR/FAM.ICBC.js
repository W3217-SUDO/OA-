var icbc = {
        File: {

            Open: function () {

                var url = AP_ROOT + AP_PAGE_ID + "/FAM/AR/ICBCImport";
                $.openLoading();

                $("<div></div>").load(url, null, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#icbcImport').modal({ backdrop: 'static', keyboard: false });
                    $('#icbcImport').on('hidden.bs.modal', function () {
                        $("#icbcImport").remove();
                    });

                });
            },

            Close: function () {
                $('#icbcImport').modal('hide');
            },

            Upload: function () {
                if ($("#flICBCFile").val() == '') {
                    $.showModalMessageBox("请选择上传的文件.");
                    return false;
                }
                $("#uploadingForm").attr("action", AP_ROOT + AP_PAGE_ID + "/FAM/ICBCPayment/ICBCFileUploading");

                $.openLoading();

                $('#uploadingForm').ajaxSubmit({
                    success: function (response) {
                        $.closeLoading();
                        if (response.IsSuccess) {
                            $("#SearchCondition_FileGuid").val(response.Data);
                            icbc.List();
                            icbc.File.Close();
                            $("#message").text(response.Message);
                            $.showModalMessageBox("上传成功.");
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    }
                });
                return true;
            },

        },
        List: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ICBCPayment/PaymentList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.PaymentList, function (i, f) {
                            var message = '';
                            $("tbody", "#tblPaymentList").addRow(
                                "<input type='checkbox' id='chkPaymentId' name='chkPaymentId' class='ng-pristine ng-valid'     value=" + f.PaymentBasic.PaymentId + ">",
                                f.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(f.PaymentBasic.CashedDate)),
                                f.PaymentBasic.PaymentModeName,
                                f.PaymentBasic.VoucherType,
                                f.PaymentBasic.VoucherNo,
                                f.PaymentBasic.Payer_BankName,
                                f.PaymentBasic.Payer_BankNo,
                                f.PaymentBasic.Remark,
                                f.PaymentBasic.CashedAmount,
                                f.PaymentBasic.StatusName
                                );
                        });

                        $("tfoot", "#tblPaymentList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.paymentList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: icbc.List,
                            callBackArgs: null
                        });

                    } else {
                        $("tfoot", "#tblPaymentList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
                else {
                    $("tbody", "#tblPaymentList").clearRow();
                    $("tfoot", "#tblPaymentList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            });
        },
        Selected: function (e) {
            if ($(e).prop('checked') == true) {
                $.checkbox.all("chkPaymentId");
                $.checkbox.all("chkPaymentAll");

            } else {
                $.checkbox.not("chkPaymentId");
                $.checkbox.not("chkPaymentAll");
            }
        },

        In: function (paymentIds) {
            $.showModalConfirmDialog("已导入的到账,不再导入系统,确定导入？", "icbc.InCallBack", paymentIds);
            return true;
        },

        InCallBack: function (paymentIds) {
            var data = { paymentIds: paymentIds };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ICBCPayment/PaymentIn", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("导入成功.");
                    icbc.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        Delete: function (paymentIds) {
            $.showModalConfirmDialog("确定删除？", "icbc.DeleteCallBack", paymentIds);
            return true;
        },
        DeleteCallBack: function (paymentIds) {
            var data = { paymentIds: paymentIds };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ICBCPayment/PaymentDelete", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("删除成功.");
                    icbc.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
}

$(document).ready(function () {

    $(document).click(function () {
    });

    icbc.List();

    $(document).off('click', '#btnSearch').on('click', '#btnSearch', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);
        icbc.List();
    });

    $(document).off('click', '#btnFileUpload').on('click', '#btnFileUpload', function () {
        icbc.File.Open();
    });

    $(document).off('click', '#btnICBCImport').on('click', '#btnICBCImport', function () {
        icbc.File.Upload();
    });

    $(document).off('click', '#btnICBCImportClose,#btnICBCImportCancel').on('click', '#btnICBCImportClose,#btnICBCImportCancel', function () {
        icbc.File.Close();
    });

    $(document).off('click', '#flICBCFile').on('change', '#flICBCFile', function () {
        $("#txtICBCFilePath").val($("#flICBCFile").val());
    });

    $(document).off('click', '#btnExport').on('click', '#btnExport', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(60000);

        icbc.ListExportToExcel();
    });

    $(document).off('click', '#chkPaymentAll').on('click', '#chkPaymentAll', function () {
        icbc.Selected(this);
    });

    $(document).off('click', '#btnPaymentDelete').on('click', '#btnPaymentDelete', function () {
        /*列表选中修改*/
        var pamentIds = $.checkbox.vals("chkPaymentId");
        if (pamentIds.length == 0) {
            $.showModalMessageBox("请选择工行到账项.");
            return false;
        }

        icbc.Delete(pamentIds);
    });


    $(document).off('click', '#btnPaymentIn').on('click', '#btnPaymentIn', function () {
        /*列表选中修改*/
        var pamentIds = $.checkbox.vals("chkPaymentId");
        if (pamentIds.length == 0) {
            $.showModalMessageBox("请选择工行到账项.");
            return false;
        }

        icbc.In(pamentIds);
    });
    
});