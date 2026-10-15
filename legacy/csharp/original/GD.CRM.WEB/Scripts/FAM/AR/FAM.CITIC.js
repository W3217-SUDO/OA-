var CITIC = {
        File: {

            Open: function () {

                var url = AP_ROOT + AP_PAGE_ID + "/FAM/AR/CITICImport";
                $.openLoading();

                $("<div></div>").load(url, null, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#CITICImport').modal({ backdrop: 'static', keyboard: false });
                    $('#CITICImport').on('hidden.bs.modal', function () {
                        $("#CITICImport").remove();
                    });

                });
            },

            Close: function () {
                $('#CITICImport').modal('hide');
            },

            Upload: function () {
                if ($("#flCITICFile").val() == '') {
                    $.showModalMessageBox("请选择上传的文件.");
                    return false;
                }
                $("#uploadingForm").attr("action", AP_ROOT + AP_PAGE_ID + "/FAM/CITICPayment/CITICFileUploading");

                $.openLoading();

                $('#uploadingForm').ajaxSubmit({ 
                    success: function (response) {
                        $.closeLoading();
                        if (response.IsSuccess) {
                            $("#SearchCondition_FileGuid").val(response.Data);
                            CITIC.List();
                            CITIC.File.Close();
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
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/CITICPayment/PaymentList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.PaymentList, function (i, f) {
                            var message = '';
                            $("tbody", "#tblPaymentList").addRow(
                                "<input type='checkbox' id='chkPaymentId' name='chkPaymentId' class='ng-pristine ng-valid'     value=" + f.PaymentBasic.PaymentId + ">",
                                f.PaymentBasic.CITIC_BankNo,
                                f.PaymentBasic.HousekeeperName,
                                f.PaymentBasic.Payer_BankNo,
                                f.PaymentBasic.Payer_Name,
                                f.PaymentBasic.CashedAmount,
                                f.PaymentBasic.PaymentModeName,
                                f.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(f.PaymentBasic.CashedDate)),
                                f.PaymentBasic.ChannelName,
                                f.PaymentBasic.SeqNo,
                                f.PaymentBasic.Remark,
                             
                                f.PaymentBasic.StatusName
                                );
                        });

                        $("tfoot", "#tblPaymentList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.paymentList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: CITIC.List,
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
            $.showModalConfirmDialog("已导入的到账,不再导入系统,确定导入？", "CITIC.InCallBack", paymentIds);
            return true;
        },

        InCallBack: function (paymentIds) {
            var data = { paymentIds: paymentIds };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/CITICPayment/PaymentIn", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("导入成功.");
                    CITIC.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        Delete: function (paymentIds) {
            $.showModalConfirmDialog("确定删除？", "CITIC.DeleteCallBack", paymentIds);
            return true;
        },
        DeleteCallBack: function (paymentIds) {
            var data = { paymentIds: paymentIds };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/CITICPayment/PaymentDelete", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("删除成功.");
                    CITIC.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
}

$(document).ready(function () {

    $(document).click(function () {
    });

    CITIC.List();

    $(document).off('click', '#btnSearch').on('click', '#btnSearch', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);
        CITIC.List();
    });

    $(document).off('click', '#btnFileUpload').on('click', '#btnFileUpload', function () {
        CITIC.File.Open();
    });

    $(document).off('click', '#btnCITICImport').on('click', '#btnCITICImport', function () {
        CITIC.File.Upload();
    });

    $(document).off('click', '#btnCITICImportClose,#btnCITICImportCancel').on('click', '#btnCITICImportClose,#btnCITICImportCancel', function () {
        CITIC.File.Close();
    });

    $(document).off('click', '#flCITICFile').on('change', '#flCITICFile', function () {
        $("#txtCITICFilePath").val($("#flCITICFile").val());
    });

    $(document).off('click', '#btnExport').on('click', '#btnExport', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(60000);

        CITIC.ListExportToExcel();
    });

    $(document).off('click', '#chkPaymentAll').on('click', '#chkPaymentAll', function () {
        CITIC.Selected(this);
    });

    $(document).off('click', '#btnPaymentDelete').on('click', '#btnPaymentDelete', function () {
        /*列表选中修改*/
        var pamentIds = $.checkbox.vals("chkPaymentId");
        if (pamentIds.length == 0) {
            $.showModalMessageBox("请选择到账项.");
            return false;
        }

        CITIC.Delete(pamentIds);
    });


    $(document).off('click', '#btnPaymentIn').on('click', '#btnPaymentIn', function () {
        /*列表选中修改*/
        var pamentIds = $.checkbox.vals("chkPaymentId");
        if (pamentIds.length == 0) {
            $.showModalMessageBox("请选择到账项.");
            return false;
        }

        CITIC.In(pamentIds);
    });
    
});