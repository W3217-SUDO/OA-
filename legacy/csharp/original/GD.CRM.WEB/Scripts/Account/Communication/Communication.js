/*沟通记录*/
var communications = {
    List: function() {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/Account/Communication/List", function(response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCommunicationList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.Communications, function(i, c) {
                        $("tbody", "#tblCommunicationList").addRow(
                            c.CurrentUserName,
                            getDateTime(convertJsonDateToJSDate(c.CommunicationTime)),
                            c.CustomerNo,
                            c.CustomerName,
                            c.Contacts,
                            c.ContactPhone,
                            "<span style='width: 400px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" +c.Content +"</span>",
                            "<a href='javascript:void(0)' onclick='javascript:communications.Open(" + c.CommunicationId + ")'>查看</a>");
                    });

                    $("tfoot", "#tblCommunicationList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.communication").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: communications.List,
                        callBackArgs: null
                    });
                } else {

                    $("tfoot", "#tblCommunicationList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    /*创建沟通记录*/
    Open: function(communicationId) {
        var data = { communicationId: communicationId };
        var url =  AP_ROOT + AP_PAGE_ID + "/Account/Communication/Communication";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);
            $('#communicationModal').modal({ backdrop: 'static', keyboard: false });
            $('#communicationModal').on('hidden.bs.modal', function () {
                $("#communicationModal").remove();
            });
        });
    },
}

$(document).ready(function () {

    communications.List();

    $(document).click(function () {
    });

    $("#btnCommunicationCreate,.communicationCreate").off().on("click", function () {
        communications.Open();
    });

    $("#btnCustomerSearch").off().on("click", function () {
        communications.List();
    });

});

