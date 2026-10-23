$(document).ready(function () {
    payment.List.PaymentList();
  
});

$(document).off('click', '#btnPaymentListSearch').on('click', '#btnPaymentListSearch', function () {
//$("#btnPaymentListSearch").off().on("click", function () {
    payment.List.PaymentList();
});