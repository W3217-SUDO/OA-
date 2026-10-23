$(document).ready(function () {
    invoice.List.PendingList();
});

$(document).off('click', '#btnInvoiceListSearch').on('click', '#btnInvoiceListSearch', function () {
    invoice.List.PendingList();
});