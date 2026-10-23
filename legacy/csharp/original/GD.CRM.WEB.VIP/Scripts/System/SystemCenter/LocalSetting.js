$(document).ready(function () {

    $(document).off('click', '#btnCreateUpdate').on('click', '#btnCreateUpdate', function () {
        //if (!postValid()) {
        //    return false;
        //}
        var data = {};
        var i = 0;
       
        $("input[name='item.Item1']").each(function () {
            data["LocalSettingList[" + i + "].SettingId"] = $(this).val();
            i++;
        });
        i = 0;
        $("input[name='item.Item3']").each(function () {
            data["LocalSettingList[" + i + "].SettinGV_IPRalue"] = $(this).val();
            i++;
        });

        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/LocalSettingCreateUpdate", data, function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        });
    });
})