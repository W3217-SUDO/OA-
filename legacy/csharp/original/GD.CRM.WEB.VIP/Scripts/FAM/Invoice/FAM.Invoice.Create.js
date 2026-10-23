$(document).ready(function () {

    var province = $("#Customer_CustomerBasic_Province").val();
    var city = $("#Customer_CustomerBasic_City").val();

    //$('#district').citys();
    $('#district').citys({ code: city });

    invoice.Invoice.Objects.List();
});