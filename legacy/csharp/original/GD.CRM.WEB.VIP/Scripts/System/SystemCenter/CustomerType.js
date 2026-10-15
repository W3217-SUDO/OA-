$(document).ready(function () {

    $(document).off('click', '#btnCreateUpdate').on('click', '#btnCreateUpdate', function () {
        //if (!postValid()) {
        //    return false;
        //}
        var data = {};
        var i = 0;
        
        $("input[name='item.CustomerTypeId']").each(function () {
            data["CaseCustomerTypeList[" + i + "].CustomerTypeId"] = $(this).val();
            i++;
        });
        i = 0;
        $("input[name='item.SharedDays']").each(function () {
            data["CaseCustomerTypeList[" + i + "].SharedDays"] = $(this).val();
            i++;
        });

        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CustomerTypeCreateUpdate", data, function (response) {
        //$("#customerTypeform").ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CustomerTypeCreateUpdate", function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        });
    });
})