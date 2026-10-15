/*缓存*/
var cache = {
    List: function() {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemManagement/CacheList", function(response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCacheList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.CacheList, function(i, c) {
                        $("tbody", "#tblCacheList").addRow(c.CacheId, c.CacheName, c.CacheKey,
                            "<a href='javascript:void(0)' onclick='javascript:cache.Clear(" + c.CacheId + ")'>清除</a>");
                    });

                    $("tfoot", "#tblCacheList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.cache").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: cache.List,
                        callBackArgs: null
                    });
                } else {
                    $("tfoot", "#tblCacheList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    Clear: function (cacheId) {

        if (cacheId == undefined) return false;
        var data = { cacheId: cacheId };
        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemManagement/ClearCache", data, function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("清除成功.");
                return true;
            }
        });
    },

    ClearAll: function () {
    var data = {  };
    $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemManagement/ClearAllCache", data, function (response) {
        if (response.IsSuccess) {
            $.showModalMessageBox("清除成功.");
            return true;
        }
    });
}
}

$(document).ready(function () {
    cache.List();
});


