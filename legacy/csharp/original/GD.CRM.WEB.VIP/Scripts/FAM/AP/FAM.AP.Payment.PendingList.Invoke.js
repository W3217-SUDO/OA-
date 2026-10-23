$(document).ready(function () {
    payment.List.PendingPaymentList();
  
});

$(document).off('click', '#btnPaymentListSearch').on('click', '#btnPaymentListSearch', function () {
//$("#btnPaymentListSearch").off().on("click", function () {
    payment.List.PendingPaymentList();
});