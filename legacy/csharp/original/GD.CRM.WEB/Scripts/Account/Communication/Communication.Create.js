
function AssociateCustomer(div, ctlhid, ctlno, ctlname, ctlcontacts, ctlcontactTelphone) {
    
    this.GlobalHID = $(ctlhid).val(); //隐藏Id号
    this.GlobalNo = $(ctlno).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;

    this.Customer = function() {
        var name = ctlno.val();
        if ($.trim(name) == "") {
            return false;
        }

        var regd = /^.*[\\\'\"<>]+.*$/;
        if (regd.test(name)) {
            $.showModalMessageBox("禁止输入 <  >  \"   \'  \\ 半角字符，请检查");
            ctlno.val('');
            return false;
        }

        var curobj = new Object();
        curobj.keyword = name;
        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CustomerList", curobj, function(response) {
            $(div).find(".i_common_list").empty();
            if (response.IsSuccess) {
                if (response.Data) {
                    var html = "";
                    $.each(response.Data.Customers, function(i, c) {

                        var contacts = c.DefaultContacts == null ? '' : c.DefaultContacts.Contacts;
                        var contactTelphone = c.DefaultContacts == null ? '' : c.DefaultContacts.OfficePhone;

                        html += '<a href="javascript:void(0)" customerid=' + c.CustomerBasic.CustomerId + ' customerno=' + c.CustomerBasic.CustomerNo + ' contacts=' + contacts + ' contactTelphone=' + contactTelphone + ' >' + c.CustomerBasic.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").click(function() {

                        $(ctlhid).val($(this).attr("customerId"));
                        $(ctlno).val($(this).attr("customerNo"));
                        $(ctlcontacts).val($(this).attr("contacts"));
                        $(ctlcontactTelphone).val($(this).attr("contactTelphone"));

                        $(ctlname).val(this.text);
                        $(div).hide();

                        if (communication) {
                            communication.RefreshLogs($(ctlhid).val());
                        }
                    });
                }
            } else {
                $.showModalMessageBox(response.Message);
            }
        }, false);

        $(div).css({
            "position": "absolute",
            //"left": $(ctlno).offsetParent().position().left + 127,
            //"top": $(ctlno).offsetParent().position().top + 57
            "left": $(ctlno).offsetParent().position().left + 15,
            "top": $(ctlno).offsetParent().position().top + 32
        }).toggle();
    }

    $(ctlno).bind('keyup', { obj: this }, function (event) {
        
        if (event.keyCode == 38) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).prev().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).prev().addClass("hover");
                        $(hover).prev().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 40) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).next().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).next().addClass("hover");
                        $(hover).next().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 13) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    $(hover).click();
                }
            }
        } else {
            clearTimeout(event.data.obj.Event);
            event.data.obj.Event = setTimeout(function () { event.data.obj.Customer(event.data.obj); }, 500);
        }
    });

    $(ctlno).bind('blur', { obj: this }, function (event) {
        
        if ($(this).val() == "" || ($(this).val() == $(this).attr("mod-notice-tip"))) {
            event.data.obj.GlobalName = "";
            $(ctlno).val("");
        }
        if ($(ctlno).val() == "") {
            if ($(this).attr("mod-notice-tip")) {
                $(this).val($(this).attr("mod-notice-tip"));
            } else {
                $(this).val("");
            }
        }
        //        if (event.data.obj.GlobalName != "") {
        //            $(this).val(event.data.obj.GlobalName);
        //            $(ctlid).val(event.data.obj.GlobalID);
        //        }
    });

    return this;
}
 

/*沟通记录*/
var communication = {

    /*保存记录*/
    Create: function () {

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

        $("#communicationForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/Account/Communication/CreateUpdate", function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");

                if (typeof (communications) == 'undefined') {
                    communication.RefreshLogs($("#Communication_CustomerId").val());
                } else {
                    communications.List();
                    communication.Close();
                }

            } else {
                $.showModalMessageBox(response.Message);
            }
        });

        return true;
    },

    /*关闭窗体*/
    Close: function () {
        $('#communicationModal').modal('hide');
    },

    /*刷新沟通历史记录*/
    RefreshLogs: function (customerId) {
        if (customerId == undefined) return false;
        var data = { customerId: customerId };

        $.openLoading();

        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Account/Communication/CommunicationLogList", data, function (response) {
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

    var customter = new AssociateCustomer(
     $("#div_customer"),
     $("#Communication_CustomerId"),
     $("#Communication_CustomerNo"),
     $("#Communication_CustomerName"),
     $("#Communication_Contacts"),
     $("#Communication_ContactPhone")
    );

    $(document).click(function () {
    });

    $(document).off('click', '#btnCommunicationClose,#btnCommunicationCancel').on('click', '#btnCommunicationClose,#btnCommunicationCancel', function () {
        communication.Close();
    });

    $(document).off('click', '#btnCommunicationCreateUpdate').on('click', '#btnCommunicationCreateUpdate', function () {
        communication.Create();
    });

    $(document).off('click', '#btnCommunicationCreateNew').on('click', '#btnCommunicationCreateNew', function () {
        $(":input", "#communicationForm").each(function () {
            $(this).removeAttr("disabled");
        });

        $("#Communication_Content").empty();
        $("#btnCommunicationCreateNew").hide();
        $("#btnCommunicationCreateUpdate").show();
    });

});
