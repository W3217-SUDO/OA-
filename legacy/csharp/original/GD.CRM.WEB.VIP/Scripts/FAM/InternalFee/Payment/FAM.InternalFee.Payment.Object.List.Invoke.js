$(document).ready(function () {
    payment.List.PaymentObjectList();
});

$(document).off('click', '#btnPaymentObjectListSearch').on('click', '#btnPaymentObjectListSearch', function () {
    payment.List.PaymentObjectList();
});


$(document).off('click', '#btnPaymentPay').on('click', '#btnPaymentPay', function () {
    var chkPaymentObjectIds = $.checkbox.vals("chkPaymentObjectId");
    if (chkPaymentObjectIds.length == 0) {
        $.showModalMessageBox("请选择提成.");
        return false;
    }

    var paymentObjects = new Array();

    $("input[name='chkPaymentObjectId']:checked").each(
        function () {
            if ($.inArray($(this).attr("paymentobject"), paymentObjects) > -1) {
            } else {
                paymentObjects.push($(this).attr("paymentobject"));
            }
        }
    );
    if (paymentObjects.length > 1) {
        $.showModalMessageBox("请选择同一收款人进行打包付款.");
        return false;
    }

    payment.Payment.Objects.Packing.CreateUpdate(chkPaymentObjectIds);

});

$(document).off('click', '#chkPaymentAll').on('click', '#chkPaymentAll', function () {
    payment.Payment.Objects.Selected(this);
});