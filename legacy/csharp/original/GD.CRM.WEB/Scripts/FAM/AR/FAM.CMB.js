var CMB = {
        File: {

            Open: function () {

                var url = AP_ROOT + AP_PAGE_ID + "/FAM/AR/CMBImport";
                $.openLoading();

                $("<div></div>").load(url, null, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#CMBImport').modal({ backdrop: 'static', keyboard: false });
                    $('#CMBImport').on('hidden.bs.modal', function () {
                        $("#CMBImport").remove();
                    });

                });
            },

            Close: function () {
                $('#CMBImport').modal('hide');
            },

            Upload: function () {
                if ($("#flCMBFile").val() == '') {
                    $.showModalMessageBox("请选择上传的文件.");
                    return false;
                }
                $("#uploadingForm").attr("action", AP_ROOT + AP_PAGE_ID + "/FAM/CMBPayment/CMBFileUploading");

                $.openLoading();

                $('#uploadingForm').ajaxSubmit({
                    success: function (response) {
                        $.closeLoading();
                        if (response.IsSuccess) {
                            $("#SearchCondition_FileGuid").val(response.Data);
                            CMB.List();
                            CMB.File.Close();
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
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/CMBPayment/PaymentList", function (response) {
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
                            callBack: CMB.List,
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
            $.showModalConfirmDialog("已导入的到账,不再导入系统,确定导入？", "CMB.InCallBack", paymentIds);
            return true;
        },
        InCallBack: function (paymentIds) {
            var data = { paymentIds: paymentIds };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/CMBPayment/PaymentIn", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("导入成功.");
                    CMB.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        Delete: function (paymentIds) {
            $.showModalConfirmDialog("确定删除？", "CMB.DeleteCallBack", paymentIds);
            return true;
        },
        DeleteCallBack: function (paymentIds) {
            var data = { paymentIds: paymentIds };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/CMBPayment/PaymentDelete", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("删除成功.");
                    CMB.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
}

$(document).ready(function () {

    $(document).click(function () {
    });

    CMB.List();

    $(document).off('click', '#btnSearch').on('click', '#btnSearch', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);
        CMB.List();
    });

    $(document).off('click', '#btnFileUpload').on('click', '#btnFileUpload', function () {
        CMB.File.Open();
    });

    $(document).off('click', '#btnCMBImport').on('click', '#btnCMBImport', function () {
        CMB.File.Upload();
    });

    $(document).off('click', '#btnCMBImportClose,#btnCMBImportCancel').on('click', '#btnCMBImportClose,#btnCMBImportCancel', function () {
        CMB.File.Close();
    });

    $(document).off('click', '#flCMBFile').on('change', '#flCMBFile', function () {
        $("#txtCMBFilePath").val($("#flCMBFile").val());
    });

    $(document).off('click', '#btnExport').on('click', '#btnExport', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(60000);

        CMB.ListExportToExcel();
    });

    $(document).off('click', '#chkPaymentAll').on('click', '#chkPaymentAll', function () {
        CMB.Selected(this);
    });

    $(document).off('click', '#btnPaymentDelete').on('click', '#btnPaymentDelete', function () {
        /*列表选中修改*/
        var pamentIds = $.checkbox.vals("chkPaymentId");
        if (pamentIds.length == 0) {
            $.showModalMessageBox("请选择中行到账项.");
            return false;
        }

        CMB.Delete(pamentIds);
    });


    $(document).off('click', '#btnPaymentIn').on('click', '#btnPaymentIn', function () {
        /*列表选中修改*/
        var pamentIds = $.checkbox.vals("chkPaymentId");
        if (pamentIds.length == 0) {
            $.showModalMessageBox("请选择中行到账项.");
            return false;
        }

        CMB.In(pamentIds);
    });
    
});