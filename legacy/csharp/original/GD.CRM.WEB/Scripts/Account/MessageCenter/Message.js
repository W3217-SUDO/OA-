/*案件客户*/
var message = {
    List: function () {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/Account/MessageCenter/List", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblMessageList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.Messages, function (i, m) {
                        $("tbody", "#tblMessageList").addRow(
                            "<input type='checkbox' id='chkMessageId' name='chkMessageId'      value=" + m.MessageId + ">",
                            i+1,
                            m.SenderName,
                            m.ReceiverName,
                            m.Title,
                            m.Content,
                            getDate(convertJsonDateToJSDate(m.SendTime)),
                            m.TypeName,
                           "<a href='javascript:void(0)' onclick='javascript:message.Open(" + m.MessageId + ")'>查看</a>");
                    });

                    $("tfoot", "#tblMessageList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.message").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: message.List,
                        callBackArgs: null
                    });
                } else {

                    $("tfoot", "#tblMessageList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    /*创建消息*/
    Open: function (messageId) {
        var data = { messageId: messageId };
        var url = AP_ROOT + (AP_PAGE_ID == '' ? "2001002" : AP_PAGE_ID) + "/Account/MessageCenter/Message";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            $('#messageModal').modal({ backdrop: 'static', keyboard: false });
            $('#messageModal').on('hidden.bs.modal', function () {
                $("#messageModal").remove();
            });
            if (messageId) {
                
                message.MarkRead(messageId);
            }
        });

        //$('.messageCreateUpdate').load(url, data, function (result) {
        //    $.closeLoading();
        //    if (messageId) {
        //        message.MarkRead(messageId);
        //    }
        //    $('#messageModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },

    MarkRead: function(messageId) {
        var data = { messageId: messageId };
        
        $.ajaxPost(AP_ROOT + (AP_PAGE_ID == '' ? "2001002" : AP_PAGE_ID) + "/Account/MessageCenter/MarkRead", data, function (response) {
            
            if (response.IsSuccess) {
                messager.polling(false);
                return true;
            } else {
                
                return false;
            }
        });
    },

    MarkReadAll: function () {

        var messageIds = $.checkbox.vals("chkMessageId");
        if (messageIds.length == 0) {
            $.showTips("请选择消息.", 0, 3);
            return false;
        }
        var data = { messageIds: messageIds };

        $.ajaxPost(AP_ROOT + (AP_PAGE_ID == '' ? "2001002" : AP_PAGE_ID) + "/Account/MessageCenter/MarkReadAll", data, function (response) {

            if (response.IsSuccess) {
                message.List();
                return true;
            } else {

                return false;
            }
        });
    },

    /*发送消息*/
    Send: function () {

        if ($("#Message_Receiver").val() == '') {
            $.showModalMessageBox("请选择接收人.");
            return false;
        }

        if ($("#Message_Title").val() == '') {
            $.showModalMessageBox("请输入标题.");
            return false;
        }

        if ($("#Message_Content").val() == '') {
            $.showModalMessageBox("请输入内容.");
            return false;
        }

        $("#messageForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/Account/MessageCenter/Send", function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("发送成功.");
                message.List();
                message.Close();
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        });

        return true;
    },

    /*关闭窗体*/
    Close: function () {
        $('#messageModal').modal('hide');
    },

    Selected: function (e) {
    if ($(e).prop('checked') == true) {
        $.checkbox.all("chkMessageId");
        $.checkbox.all("chkMessageAll");

    } else {
        $.checkbox.not("chkMessageId");
        $.checkbox.not("chkMessageAll");
    }
},
}

$(document).ready(function () {

    $(document).click(function () {
        $("#divUsers").off().hide();
    });

    $(document).off('click', '#btnMessageClose,#btnMessageCancel').on('click', '#btnMessageClose,#btnMessageCancel', function () {
        message.Close();
    });

    $(document).off('click', '.messageCreate').on('click', '.messageCreate', function () {
        message.Open();
    });

    $(document).off('click', '#btnMessageSend').on('click', '#btnMessageSend', function () {
        message.Send();
    });

    $(document).off('click', '#btnMessageListSearch').on('click', '#btnMessageListSearch', function () {
        message.List();
    });

    $(document).off('click', '#Message_ReceiverName').on('click', '#Message_ReceiverName', function () {
        $("#hidUserId").val("Message_Receiver");
        $("#hidUserName").val("Message_ReceiverName");

        $("#divUsers").css({
            "position": "absolute",
            "left": $("#Message_ReceiverName").offsetParent().position().left + 15,
            "top": $("#Message_ReceiverName").offsetParent().position().top + 32
        }).show();
        return false;

        //$("#divUsers").css({
        //    "position": "absolute",
        //    "left": $("#Message_ReceiverName").position().left + 167,
        //    "top": $("#Message_ReceiverName").position().top + 127
        //}).show();
        //return false;

    });

    $("#divUsers").find("li").off().on("click", function () {
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        var currentSelectedControl = $("#hidUserName").val();
        var currentSelectedIdControl = $("#hidUserId").val();
        $("#" + currentSelectedControl).val(userName);
        $("#" + currentSelectedIdControl).val(userId);
        $("#divUsers").hide();
    });
});

