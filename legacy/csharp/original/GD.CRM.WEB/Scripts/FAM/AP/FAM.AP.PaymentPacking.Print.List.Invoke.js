$(document).ready(function () {
    payment.List.PackingList();
});

$(document).off('click', '#btnPackingListSearch').on('click', '#btnPackingListSearch', function () {
//$("#btnPackingListSearch").off().on("click", function () {
    payment.List.PackingList();
});