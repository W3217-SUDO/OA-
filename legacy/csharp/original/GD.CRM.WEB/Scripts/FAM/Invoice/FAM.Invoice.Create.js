$(document).ready(function () {

    var province = $("#Customer_CustomerBasic_Province").val();
    var city = $("#Customer_CustomerBasic_City").val();

    //$('#district').citys();
    $('#district').citys({ code: city });

    invoice.ResetSize();

    invoice.getCaseFeeList();

    $(document).off('click', '#btnSearch').on('click', '#btnSearch', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(15);

        invoice.getCaseFeeList();
    });
});