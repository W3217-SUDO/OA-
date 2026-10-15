$(document).ready(function () {
    payment.List.PendingList();
});


$(document).off('click', '#btnPaymentListSearch').on('click', '#btnPaymentListSearch', function () {
//$("#btnPaymentListSearch").off().on("click", function () {
    payment.List.PendingList();
});