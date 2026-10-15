$(document).ready(function () {
    invoice.List.InvoicedList();
});

$(document).off('click', '#btnInvoiceListSearch').on('click', '#btnInvoiceListSearch', function () {
    invoice.List.InvoicedList();
});