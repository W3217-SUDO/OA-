/*缓存*/
var appSetting = {
    List: function() {
        $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/System/SystemManagement/ConfigAppSettings", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblAppSettingList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.SettingList, function (i, c) {
                        $("tbody", "#tblAppSettingList").addRow(
                            (++i),
                            c.GroupName,
                            c.ConfigName,
                            c.ConfigKey,
                            c.ConfigValue,
                           c.IsValid ? "是" : "否")
                    });

                    $("tfoot", "#tblAppSettingList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.appSetting").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: appSetting.List,
                        callBackArgs: null
                    });
                } else {
                    $("tfoot", "#tblAppSettingList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    Clear: function (appSettingId) {

        if (appSettingId == undefined) return false;
        var data = { appSettingId: appSettingId };
        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemManagement/ClearCache", data, function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("清除成功.");
                return true;
            }
        });
    }
}

$(document).ready(function () {
    appSetting.List();
});


