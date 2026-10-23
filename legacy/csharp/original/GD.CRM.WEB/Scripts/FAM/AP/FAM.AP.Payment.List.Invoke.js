$(document).ready(function () {
    payment.List.PaymentList();  
});

$(document).off('click', '#btnPaymentListSearch').on('click', '#btnPaymentListSearch', function () {
    payment.List.PaymentList();
});

$(document).off('click', '#btnPaymentPackingPrint').on('click', '#btnPaymentPackingPrint', function () {
    var packageNos = [];
    $("input[name='chkPaymentId']:checked").each(
        function (i) { packageNos[i] = $(this).val(); }
    );
    if (packageNos.length < 1) {
        $.showModalMessageBox("请选择需要导出的请款单.");
        return false;
    }
    if ($("#SearchCondition_PageId").val() == "5001003004") {
        payment.Payment.Packing.PrintOnNos( packageNos,$.lsGroupId.Lawfirm);
    }
    else {
        payment.Payment.Packing.PrintOnNos( packageNos,$.lsGroupId.Trad);
    }
});

$(document).off('click', '#chkPaymentPrintAll').on('click', '#chkPaymentPrintAll', function () {
    payment.Payment.Selected(this);
});

$(document).off('click', '#btnPaymentPackingVerify').on('click', '#btnPaymentPackingVerify', function () {
    var packageNos = [];
    $("input[name='chkPaymentId']:checked").each(
        function (i) { packageNos[i] = $(this).val(); }
    );
    if (packageNos.length < 1) {
        $.showModalMessageBox("请选择需要导出的请款单.");
        return false;
    }
    payment.Payment.Packing.Verification.Open(packageNos.join());
});



 