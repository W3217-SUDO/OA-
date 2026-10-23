/*沟通记录*/
var communication = {
    List: function() {
        $("#postForm").ajaxPost(AP_ROOT + "IPR/Communication/List", function(response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCommunicationList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.Communications, function(i, c) {
                        $("tbody", "#tblCommunicationList").addRow(c.CurrentUserName, getDate(convertJsonDateToJSDate(c.CommunicationTime)), c.CustomerNo, c.CustomerName, c.Contacts, c.ContactPhone, c.Content,
                            "<a href='javascript:void(0)' onclick='javascript:communication.Open(" + c.CommunicationId + ")'>查看</a>");
                    });

                    $("tfoot", "#tblCommunicationList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.communication").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: communication.List,
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
        //$('.communicationCreateUpdate').html('');
        var data = { id: communicationId };
        var url = AP_ROOT + "IPR/Communication/Communication";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);
            $('#communicationModal').modal({ backdrop: 'static', keyboard: false });
            $('#communicationModal').on('hidden.bs.modal', function () {
                $("#communicationModal").remove();
            });
        });

        //$('.communicationCreateUpdate').load(url, data, function(result) {
        //    $.closeLoading();
        //    $('#communicationModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },

    /*保存记录*/
    Create: function() {

        if ($("#Communication_CustomerId").val() == '') {
            $.showModalMessageBox("请输入客户编号.");
            return false;
        }

        if ($("#Communication_CustomerNo").val() == '') {
            $.showModalMessageBox("请输入客户编号.");
            return false;
        }

        if ($("#Communication_Contacts").val() == '') {
            $.showModalMessageBox("请输入联系人.");
            return false;
        }

        if ($("#Communication_ContactPhone").val() == '') {
            $.showModalMessageBox("请输入联系电话.");
            return false;
        }

        if ($("#Communication_Content").val() == '') {
            $.showModalMessageBox("请输入沟通内容.");
            return false;
        }

        $("#communicationForm").ajaxPost(AP_ROOT + "IPR/Communication/CreateUpdate", function(response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                communication.List();
                communication.Close();
            } else {
                $.showModalMessageBox(response.Message);
            }
        });

        return true;
    },

    /*关闭窗体*/
    Close: function() {
        $('#communicationModal').modal('hide');
    },

    /*刷新沟通历史记录*/
    RefreshLogs: function (customerId) {
        if (customerId == undefined) return false;
        var data = { customerId: customerId };

        $.openLoading();

        $.ajaxPost(AP_ROOT + "IPR/Communication/CommunicationLogList", data, function (response) {
            if (response.IsSuccess) {
              
                $(".communicationlogs").empty();
                $(".communicationlogs").html(response.Data);
                $.closeLoading();
            }
        }, true);

        return true;
    },
}

$(document).ready(function () {

    communication.List();

    $(document).click(function () {
    });

    $("#btnCommunicationClose,#btnCommunicationCancel").die().live("click", function () {
        communication.Close();
    });

    $("#btnCommunicationCreate,.communicationCreate").die().live("click", function () {
        communication.Open();
    });

    $("#btnCommunicationCreateUpdate").die().live("click", function () {
        communication.Create();
    });
 
});

