$(document).ready(function () {
    invoice.List.InvoiceList();
});

$(document).off('click', '#btnInvoiceListSearch').on('click', '#btnInvoiceListSearch', function () {
    invoice.List.InvoiceList();
});