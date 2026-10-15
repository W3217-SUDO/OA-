$(document).ready(function () {
    payment.List.PackingList();
});


$(document).off('click', '#btnPackingListSearch').on('click', '#btnPackingListSearch', function () {
    payment.List.PackingList();
});

