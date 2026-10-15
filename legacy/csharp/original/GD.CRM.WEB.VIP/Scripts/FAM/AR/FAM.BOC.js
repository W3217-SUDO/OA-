var boc = {
        File: {

            Open: function () {

                var url = AP_ROOT + AP_PAGE_ID + "/FAM/AR/BOCImport";
                $.openLoading();

                $("<div></div>").load(url, null, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#bocImport').modal({ backdrop: 'static', keyboard: false });
                    $('#bocImport').on('hidden.bs.modal', function () {
                        $("#bocImport").remove();
                    });

                });
            },

            Close: function () {
                $('#bocImport').modal('hide');
            },

            Upload: function () {
                if ($("#flBOCFile").val() == '') {
                    $.showModalMessageBox("请选择上传的文件.");
                    return false;
                }
                $("#uploadingForm").attr("action", AP_ROOT + AP_PAGE_ID + "/FAM/BOCPayment/BOCFileUploading");

                $.openLoading();

                $('#uploadingForm').ajaxSubmit({
                    success: function (response) {
                        $.closeLoading();
                        if (response.IsSuccess) {
                            $("#SearchCondition_FileGuid").val(response.Data);
                            boc.List();
                            boc.File.Close();
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
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/BOCPayment/PaymentList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.PaymentList, function (i, f) {
                            var message = '';
                            $("tbody", "#tblPaymentList").addRow(
                                "<input type='checkbox' id='chkPaymentId' name='chkPaymentId' class='ng-pristine ng-valid'     value=" + f.PaymentBasic.PaymentId + ">",
                                f.PaymentBasic.TransactionType + '_' + f.PaymentBasic.BusinessType,
                                 f.PaymentBasic.TransactionDate == null ? '' : getDateTime(convertJsonDateToJSDate(f.PaymentBasic.TransactionDate)),
                                f.PaymentBasic.Payer_Account_No,
                                f.PaymentBasic.Payer_Name,
                                f.PaymentBasic.TradeAmount,
                                f.PaymentBasic.TransactionNo,
                            
                                f.PaymentBasic.Reference,
                                f.PaymentBasic.Purpose,
                                f.PaymentBasic.Remark,
                                f.PaymentBasic.Remarks,
                                f.PaymentBasic.StatusName
                                );
                        });

                        $("tfoot", "#tblPaymentList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.paymentList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: boc.List,
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
            $.showModalConfirmDialog("已导入的到账,不再导入系统,确定导入？", "boc.InCallBack", paymentIds);
            return true;
        },

        InCallBack: function (paymentIds) {
            var data = { paymentIds: paymentIds };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/BOCPayment/PaymentIn", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("导入成功.");
                    boc.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        Delete: function (paymentIds) {
            $.showModalConfirmDialog("确定删除？", "boc.DeleteCallBack", paymentIds);
            return true;
        },
        DeleteCallBack: function (paymentIds) {
            var data = { paymentIds: paymentIds };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/BOCPayment/PaymentDelete", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("删除成功.");
                    boc.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
}

$(document).ready(function () {

    $(document).click(function () {
    });

    boc.List();

    $(document).off('click', '#btnSearch').on('click', '#btnSearch', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);
        boc.List();
    });

    $(document).off('click', '#btnFileUpload').on('click', '#btnFileUpload', function () {
        boc.File.Open();
    });

    $(document).off('click', '#btnBOCImport').on('click', '#btnBOCImport', function () {
        boc.File.Upload();
    });

    $(document).off('click', '#btnBOCImportClose,#btnBOCImportCancel').on('click', '#btnBOCImportClose,#btnBOCImportCancel', function () {
        boc.File.Close();
    });

    $(document).off('click', '#flBOCFile').on('change', '#flBOCFile', function () {
        $("#txtBOCFilePath").val($("#flBOCFile").val());
    });

    $(document).off('click', '#btnExport').on('click', '#btnExport', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(60000);

        boc.ListExportToExcel();
    });

    $(document).off('click', '#chkPaymentAll').on('click', '#chkPaymentAll', function () {
        boc.Selected(this);
    });

    $(document).off('click', '#btnPaymentDelete').on('click', '#btnPaymentDelete', function () {
        /*列表选中修改*/
        var pamentIds = $.checkbox.vals("chkPaymentId");
        if (pamentIds.length == 0) {
            $.showModalMessageBox("请选择中行到账项.");
            return false;
        }

        boc.Delete(pamentIds);
    });


    $(document).off('click', '#btnPaymentIn').on('click', '#btnPaymentIn', function () {
        /*列表选中修改*/
        var pamentIds = $.checkbox.vals("chkPaymentId");
        if (pamentIds.length == 0) {
            $.showModalMessageBox("请选择中行到账项.");
            return false;
        }

        boc.In(pamentIds);
    });
    
});