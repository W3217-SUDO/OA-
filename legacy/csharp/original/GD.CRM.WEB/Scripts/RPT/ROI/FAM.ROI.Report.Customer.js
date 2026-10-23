$(document).ready(function () {
    $("#SearchCondition_CustomerName").chosen({
        width: '100%',
        disable_search: false,
        search_contains: true
    });

    $("#SearchCondition_CourtLawyerName").chosen({
        width: '100%',
        disable_search: false,
        search_contains: true
    });

    $(document).off('click', '#btnSearchReset').on('click', '#btnSearchReset', function () {
        rpt.Reset();
    });

    $(document).off('click', '#btnSearch').on('click', '#btnSearch', function () {
        rpt.CountRoiGroupByCustomer();
    });

    rpt.CountRoiGroupByCustomer();
    rpt.ResetSize();

    $(window).resize(function () {
        rpt.ResetSize();
    });
});