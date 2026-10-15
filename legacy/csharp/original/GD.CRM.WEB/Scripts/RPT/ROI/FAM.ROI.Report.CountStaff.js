$(document).ready(function () {

    $("#SearchCondition_CustomerName").chosen({
        width: '100%',
        disable_search: false,
        search_contains: true
    });

    $("#SearchCondition_CountStaffName").chosen({
        width: '100%',
        disable_search: false,
        search_contains: true
    });

    $(document).off('click', '#btnSearchReset').on('click', '#btnSearchReset', function () {
        rpt.Reset();
    });

    $(document).off('click', '#btnSearch').on('click', '#btnSearch', function () {
        rpt.CountRoiGroupByStaff();
    });

    rpt.CountRoiGroupByStaff();
    rpt.ResetSize();

    $(window).resize(function () {
        rpt.ResetSize();
    });

    $("#SearchCondition_CountRoiGroupId").change(function () {
        var groupId = $("#SearchCondition_CountRoiGroupId").val();
        if (groupId == '10') {
            $("#lblGroupName").html("开庭律师：");
            $("#liGroupName").html("按开庭律师统计");
            

        } else if (groupId == '20') {
            $("#lblGroupName").html("律师助理：");
            $("#liGroupName").html("按律师助理统计");
        }
    });
});


