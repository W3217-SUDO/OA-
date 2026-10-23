
var contacts = {

    List: function () {
         $("#contactsListForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/LawFirm/GetContactsList", function (response) {
            if (response.IsSuccess) {
                 $("tbody", "#tblContactsList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                   
                    $.each(response.Data.ContactsList, function (i, e) {
                         $("tbody", "#tblContactsList").addRow(e.ContactsId,  e.Contacts,e.ContactAddress, e.ContactZip,
                            e.ContactTelphone, e.ContactFax, e.ContactEmail, e.CreateUser, e.CreateTimeToString,
                             "<a href='javascript:void(0)' onclick='javascript:contacts.Open(" + e.ContactsId + ")'>修改</a>&nbsp; &nbsp;&nbsp;" +
                             "<a href='javascript:void(0)' onclick='javascript:contacts.SetDefault(" + e.LawFirmId + "," + e.ContactsId + ")'>设置成默认</a>&nbsp; &nbsp;&nbsp;" +
                             "<a href='javascript:void(0)' onclick='javascript:contacts.SetActived(" + e.ContactsId + ")'>无效</a>"
                             );
                    });

                    $("tfoot", "#tblContactsList").show();
             
                    $("#contactslistpaging").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: contacts.List,
                        callBackArgs: null
                    });
                }
                else {
                    $("tfoot", "#tblContactsList").hide();
                }
            }
        });
    },

    /*设置默认联系人*/
    SetDefault: function (lawFirmId,contactsId) {
        var data = {
            lawFirmId: lawFirmId,
            contactsId: contactsId
        };

        
        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/LawFirm/SetDefatultContacts", data, function (response) {
            if (response.IsSuccess) {
                contacts.List();
                $.showModalMessageBox("设置成功.");
            }
        });
    },

    /*设置联系人有效无效*/
    SetActived: function (contactsId) {
        var data = {
            contactsId: contactsId
        };
        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/LawFirm/SetActivedContacts", data, function (response) {
            if (response.IsSuccess) {
                contacts.List();
                $.showModalMessageBox("设置成功.");
            }
        });
    },

    /*创建律所联系人*/
    Open: function (contactsId) {
        var data = {
            lawFirmId: $('#LawFirmId').val(),
            contactsId : contactsId
        };
        var url =  AP_ROOT + AP_PAGE_ID + "/CRM/LawFirm/Contacts";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);
            $('#contactsModal').modal({ backdrop: 'static', keyboard: false });
            $('#contactsModal').on('hidden.bs.modal', function () {
                $("#contactsModal").remove();
            });
        });

        //$('.contacts').load(url, data, function (result) {
        //    $.closeLoading();
        //    $('#contactsModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },

    /*关闭*/
    Close: function () {
        $('#contactsModal').modal('hide');
    },

    ListClose: function () {
        $('#contactsListModal').modal('hide');
    },

    /**/
    CreateUpdate: function () {
        //if (!postValid()) {
        //    return false;
        //}

        if ($("#Contacts_ContactEmail").val() != '') {
            var isEmail = /^\w+((-\w+)|(\.\w+))*\@[A-Za-z0-9]+((\.|-)[A-Za-z0-9]+)*\.[A-Za-z0-9]+$/;

            if (!isEmail.test($("#Contacts_ContactEmail").val())) {
                $.showModalMessageBox("请填写正确联系EMAI.");
                return false;
            }
        }

        $("#contactsForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/LawFirm/ContactsCreateUpdate", function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                contacts.List();
                contacts.Close();
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        });

        return true;
    },

    ///*关闭窗体*/
    //Close: function () {
    //    $('#contactsModal').modal('hide');
    //}
}

$(document).ready(function () {

    contacts.List();

    $("#btnContactsListCreate").off().on("click", function () {
        contacts.Open();
    });

    $("#btnContactsListCancel").off().on("click", function () {
        contacts.ListClose();
    });

    $("#btnContactsListClose").off().on("click", function () {
        contacts.ListClose();
    });

    $("#btnContactsCancle").off().on("click", function () {
        contacts.Close();
    });

    $("#btnContactsClose").off().on("click", function () {
        contacts.Close();
    });

    $("#btnContactsSubmit").off().on("click", function () {
        contacts.CreateUpdate();
    });
});


function postValid() {

    //if (!CheckModifyTime()) return false;

    //判断必填项的项是否填写
    var flag = true;
    $("#tblLawFirm :text").each(function () {
        var value = $(this).val().trim();

        var desc;
        if ($(this).parent().prev().find("label")
            && $(this).parent().prev().find("label").html() != null) {
            desc = $(this).parent().prev().find("label").html().replace(":", "").replace("：", "");
        } else if ($(this).parent().parent().prev().find("label")
            && $(this).parent().parent().prev().find("label").html() != null) {
            desc = $(this).parent().parent().prev().find("label").html().replace(":", "").replace("：", "");
        }

        if ($(this).attr("required") == "required") {

            if (value == "") {
                flag = false;

                $.showModalMessageBox(desc + "不能为空");
                return false;
            }

            if ($(this).attr("func") && $(this).attr("func") != "") {
                var func = $(this).attr("func");

                var value = $(this).val();
                var that = $(this);
                var data = { func: func, value: value }

                $.ajaxSetup({
                    async: false
                });

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IntlFare/ValidAssociate", data, function (response) {
                    if (!response.IsSuccess) {

                        $.showModalMessageBox(desc + "不存在");

                        flag = false;
                        return false;
                    }
                });

                $.ajaxSetup({
                    async: true
                });
            }
        }
    });

    if (!flag) {
        return false;
    }
    return true;
}



