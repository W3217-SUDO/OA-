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
    payment.Payment.MultiAudit(chkPaymentIds);
});

$(document).off('click', '#btnPaymentApplicationMultiApproved').on('click', '#btnPaymentApplicationMultiApproved', function () {
    payment.Payment.Application.MultiAudit(true);
});

$(document).off('click', '#btnPaymentApplicationMultiRejected').on('click', '#btnPaymentApplicationMultiRejected', function () {
    payment.Payment.Application.MultiAudit(false);
});

//$(document).off('click', '#btnPaymentApplicationCancel').on('click', '#btnPaymentApplicationCancel', function () {
//    payment.Payment.Application.Canceled(true);
//});


$(document).off('click', '#chkPaymentAll').on('click', '#chkPaymentAll', function () {
    payment.Payment.Selected(this);
});