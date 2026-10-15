$(document).ready(function () {
    payment.List.PendingList();
  
});

$(document).off('click', '#btnPaymentListSearch').on('click', '#btnPaymentListSearch', function () {
//$("#btnPaymentListSearch").off().on("click", function () {
    payment.List.PendingList();
});

$(document).off('click', '#btnPaymentAudit').on('click', '#btnPaymentAudit', function () {

    var chkPaymentIds = $.checkbox.vals("chkPaymentId");
    if (chkPaymentIds.length == 0) {
        $.showModalMessageBox("请选择审批项.");
        return false;
    }
    payment.Payment.Audit.MultiAudit(chkPaymentIds);
});


$(document).off('click', '#chkPaymentAll').on('click', '#chkPaymentAll', function () {
    payment.Payment.Selected(this);
});
