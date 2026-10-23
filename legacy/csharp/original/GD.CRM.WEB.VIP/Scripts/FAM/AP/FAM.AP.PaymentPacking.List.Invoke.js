$(document).ready(function () {
    payment.List.PendingPackingList();
});

$("#btnPackingListSearch").off().on("click", function () {
    payment.List.PendingPackingList();
});

