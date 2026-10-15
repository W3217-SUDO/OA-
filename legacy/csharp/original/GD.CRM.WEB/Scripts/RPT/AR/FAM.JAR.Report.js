var payment = {
    ResetSize: function() {
        if ($("#divContextList").length > 0) {
            $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 22);
        }
    },

    List: {
        CountForPaymentList: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/RPT/Report/PaymentList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                            $.each(response.Data.PaymentList, function (i, c) {
                                $("tbody", "#tblPaymentList").addRow(
                                    c.PaymentBasic.BusinessOwnerName,
                                    c.PaymentBasic.CaseOfficeFeeCashedAmount,
                                    c.PaymentBasic.CaseNonOfficeFeeCashedAmount,
                                    c.PaymentBasic.CaseCommissionFeeCashedAmount,
                                    c.PaymentBasic.CashedAmount
                                 );
                            });

                            $("tbody", "#tblPaymentList").addRow(
                            "",
                            response.Data.TotalCaseOfficeFeeCashedAmount,
                            response.Data.TotalCaseNonOfficeFeeCashedAmount,
                            response.Data.TotalCaseCommissionFeeCashedAmount,
                            response.Data.TotalCashedAmount);

                        //$("tfoot", "#tblPaymentList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        //$(".pull-right.page-box.paymentList").cPaging({
                        //    totalCount: response.Data.TotalItemCount,
                        //    pageNo: response.Data.PageNo,
                        //    pageSize: response.Data.PageSize,
                        //    callBack: payment.List.PaymentList,
                        //    callBackArgs: null
                        //});
                    } else {
                        $("tfoot", "#tblPaymentList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
      },
      PaymentListExportToExcel: function () {
          $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/JARFileCenter/PaymentListExportToExcel", function (response) {
              if (response.IsSuccess) {
                  window.open(AP_ROOT + AP_PAGE_ID + "/FAM/JARFileCenter/PaymentListExportToExcelDownload?fileName=" + response.Data);
                  $.showModalMessageBox("导出成功.");
              } else {
                  $.showModalMessageBox(response.Message);
              }
          });
      },
    }
}
 

$(document).ready(function () {
    $(window).resize(function () {
        payment.ResetSize();
    });

    payment.ResetSize();

    $(document).click(function () {
        $("#divAssociateUserList").off().hide();
    });

    var businessOwner = new AssociateUser(
        $("#divAssociateUserList"),
        $("#SearchCondition_BusinessOwner"),
        $("#SearchCondition_BusinessOwnerName"),
        null
    );

    $(document).off('click', '#btnPaymentSearch').on('click', '#btnPaymentSearch', function () {
        payment.List.CountForPaymentList();
    });

    $(document).off('click', '#btnPaymentListExportToExcel').on('click', '#btnPaymentListExportToExcel', function () {
        payment.List.PaymentListExportToExcel();
    });

});