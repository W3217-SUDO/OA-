function AssociateCustomer(div, ctlid, ctlno, ctlname) {
    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;

    this.Customer = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") { return false; }
        var curobj = new Object();
        curobj.keyword = name;
        $.ajaxPost(AP_ROOT + "CRM/Customer/CustomerList", curobj, function (response) {
            $(div).find(".i_common_list").empty();
            if (response.IsSuccess) {
                if (response.Data) {
                    var html = "";
                    $.each(response.Data.Customers, function(i, c) {

                        var defaultContactsContacts = c.DefaultContacts == null ? "" : c.DefaultContacts.Contacts;
                        var defaultContactsContactTelphone = c.DefaultContacts == null ? "" : c.DefaultContacts.ContactTelphone;
                        var defaultContactsContactEmail = c.DefaultContacts == null ? "" : c.DefaultContacts.ContactEmail;
                        var defaultContactsContactAddress = c.DefaultContacts == null ? "" : c.DefaultContacts.ContactAddress;

                        html += '<a href="javascript:void(0)" customerid=' + c.CustomerId
                            + ' customerno=' + c.CustomerNo
                            + ' defaultContactsContacts=' + defaultContactsContacts
                            + ' defaultContactsContactTelphone=' + defaultContactsContactTelphone
                            + ' defaultContactsContactEmail=' + defaultContactsContactEmail
                            + ' defaultContactsContactAddress=' + defaultContactsContactAddress
                            + ' >' + c.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").click(function () {
                        $(ctlid).val($(this).attr("customerid"));
                        $(ctlno).val($(this).attr("customerno"));
                        $(ctlname).val($(this).text());

                        $("#ACustomer_DefaultContacts_Contacts").val($(this).attr("defaultContactsContacts"));
                        $("#ACustomer_DefaultContacts_ContactTelphone").val($(this).attr("defaultContactsContactTelphone"));
                        $("#ACustomer_DefaultContacts_ContactEmail").val($(this).attr("defaultContactsContactEmail"));
                        $("#ACustomer_DefaultContacts_ContactAddress").val($(this).attr("defaultContactsContactAddress"));

                        $(div).hide();

                    });
                }
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        }, false);

        $(div).css({
            "position": "absolute",
            "left": $(ctlname).position().left,
            "top": $(ctlname).position().top + 22,
            "z-index": 9999
        }).show();
    }

    $(ctlname).bind('keyup', { obj: this }, function (event) {
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

    $(ctlname).bind('blur', { obj: this }, function (event) {
        if ($(this).val() == "" || ($(this).val() == $(this).attr("mod-notice-tip"))) {
            event.data.obj.GlobalName = "";
            $(ctlid).val("");
        }
        if ($(ctlid).val() == "") {
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

var contract = {
    CreateUpdate: function (isSubmit) {
        try {

            if ($("#ACustomer_CustomerId").val() == '') {
                $.showModalMessageBox("请输入甲方公司名称.");
                $("#ACustomer_CustomerName").focus();
                return false;
            }

            if ($("#ACustomer_CustomerId").val() == '0') {
                $.showModalMessageBox("请输入甲方公司名称选择客户.");
                $("#ACustomer_CustomerName").focus();
                return false;
            }

            if ($("#ACustomer_CustomerName").val() == '') {
                $.showModalMessageBox("请输入甲方公司名称.");
                $("#ACustomer_CustomerName").focus();
                return false;
            }

            if ($("#ACustomer_DefaultContacts_Contacts").val() == '') {
                $.showModalMessageBox("请输入甲方联系人.");
                $("#ACustomer_DefaultContacts_Contacts").focus();
                return false;
            }

            if ($("#ACustomer_DefaultContacts_ContactTelphone").val() == '')
            {
                $.showModalMessageBox("请输入甲方联系电话.");
                $("#ACustomer_DefaultContacts_ContactTelphone").focus();
                return false;
            }

            if ($("#ACustomer_DefaultContacts_ContactEmail").val() == '') {
                $.showModalMessageBox("请输入甲方联系邮箱.");
                $("#ACustomer_DefaultContacts_ContactEmail").focus();
                return false;
            }
            if ($("#ACustomer_DefaultContacts_ContactAddress").val() == '') {
                $.showModalMessageBox("请输入甲方联系地址.");
                $("#ACustomer_DefaultContacts_ContactAddress").focus();
                return false;
            }

            if ($("#BCustomer_CompanyName").val() == '') {
                $.showModalMessageBox("请输入乙方公司名称.");
                $("#BCustomer_CompanyName").focus();
                return false;
            }

            if ($("#BCustomer_Contracts").val() == '') {
                $.showModalMessageBox("请输入乙方人.");
                $("#BCustomer_Contracts").focus();
                return false;
            }

            if ($("#BCustomer_ContractPhone").val() == '') {
                $.showModalMessageBox("请输入乙方联系电话.");
                $("#BCustomer_ContractPhone").focus();
                return false;
            }

            if ($("#BCustomer_ContractEmail").val() == '') {
                $.showModalMessageBox("请输入乙方联系邮箱.");
                $("#BCustomer_ContractEmail").focus();
                return false;
            }

            if ($("#BCustomer_ContractAddress").val() == '') {
                $.showModalMessageBox("请输入乙方联系地址.");
                $("#BCustomer_ContractAddress").focus();
                return false;
            }

            var data = {};

            data["BusinessOwner"] = $("#BusinessOwner").val();

            data["ACustomer.CustomerNo"] = $("#ACustomer_CustomerNo").val();
            data["ACustomer.CustomerId"] = $("#ACustomer_CustomerId").val();
            data["ACustomer.CustomerName"] = $("#ACustomer_CustomerName").val();

            data["ACustomer.DefaultContacts.Contacts"] = $("#ACustomer_DefaultContacts_Contacts").val();
            data["ACustomer.DefaultContacts.ContactTelphone"] = $("#ACustomer_DefaultContacts_ContactTelphone").val();
            data["ACustomer.DefaultContacts.ContactEmail"] = $("#ACustomer_DefaultContacts_ContactEmail").val();
            data["ACustomer.DefaultContacts.ContactAddress"] = $("#ACustomer_DefaultContacts_ContactAddress").val();

            data["ContractScope.ContractScope1"] = $("#ContractScope_ContractScope1").attr("checked") == "checked";
            data["ContractScope.ContractScope2"] = $("#ContractScope_ContractScope2").attr("checked") == "checked";
            data["ContractScope.ContractScope3"] = $("#ContractScope_ContractScope3").attr("checked") == "checked";
            data["ContractScope.ContractScope4"] = $("#ContractScope_ContractScope4").attr("checked") == "checked";
            data["ContractScope.ContractScope5"] = $("#ContractScope_ContractScope5").attr("checked") == "checked";
            
            data["BCustomer.CompanyName"] = $("#BCustomer_CompanyName").val();

            
            data["BCustomer.Contracts"] = $("#BCustomer_Contracts").val();
            data["BCustomer.ContractPhone"] = $("#BCustomer_ContractPhone").val();
            data["BCustomer.ContractEmail"] = $("#BCustomer_ContractEmail").val();
            data["BCustomer.ContractAddress"] = $("#BCustomer_ContractAddress").val();
            data["BCustomer.BankName"] = $("#BCustomer_BankName").val();
            data["BCustomer.BankAccount"] = $("#BCustomer_BankAccount").val();

            data["BCustomer.CompanyShortCode"] = $("#BCustomer_CompanyShortCode").val();

            data["Remark"] = $("#Remark").val();

            var j = 0;

            $("#tblContractApplicationFeeList>tbody>tr>td").each(function (i, e) {
                if (typeof ($(e).attr("casetypeid")) != "undefined") {
                    data["Contract.CaseFeeList[" + j + "].CaseTypeId"] = $(e).attr("casetypeid");
                    data["Contract.CaseFeeList[" + j + "].CaseOfficeFeeTypeId"] = $(e).attr("caseofficefeetypeid");
                    data["Contract.CaseFeeList[" + j + "].CaseNonOfficeFeeTypeId"] = $(e).attr("casenonofficefeetypeid");
                    data["Contract.CaseFeeList[" + j + "].CaseNonOfficeFeeAmount"] = $(e).find("input:text").val();
                    data["Contract.CaseFeeList[" + j + "].Remark"] = $(e).parent().find(".remark").val();
                    j++;
                }
            });

            $("#tblContractCaseFeeList>tbody>tr>td").each(function (i, e) {
                if (typeof ($(e).attr("casetypeid")) != "undefined") {
                    var casetypeids = $(e).attr("casetypeid").split(',');
                    for (var k = 0; k < casetypeids.length; k++) {
                        data["Contract.CaseFeeList[" + j + "].CaseTypeId"] = casetypeids[k];
                        data["Contract.CaseFeeList[" + j + "].CaseOfficeFeeTypeId"] = $(e).attr("caseofficefeetypeid");
                        data["Contract.CaseFeeList[" + j + "].CaseNonOfficeFeeTypeId"] = $(e).attr("casenonofficefeetypeid");
                        data["Contract.CaseFeeList[" + j + "].CaseNonOfficeFeeAmount"] = $(e).find("input:text").val();
                        data["Contract.CaseFeeList[" + j + "].Remark"] = $(e).parent().find(".remark").val();
                        j++;
                    }
                }
            });


            data["isSubmit"] = isSubmit;

            $.ajaxPost(AP_ROOT + "FCM/Patent/Create", data, function (response) {
                if (response.IsSuccess) {
                    if (isSubmit) {
                        $.showModalConfirmDialog("提交成功.", 'contract.CreateUpdateCallBack', isSubmit,true);

                    } else {
                        $.showModalConfirmDialog("保存成功.", 'contract.CreateUpdateCallBack', isSubmit, true);
                    }
                 
                } else if (response.IsRedirect) {
                    window.location = AP_ROOT + 'Home/Index';
                } else {
                    $.showModalMessageBox(response.Message);

                }
            });
        } catch (e) {
            alert(e);
        }
    },
    CreateUpdateCallBack: function (isSubmit) {
        if (isSubmit) {
            window.location = AP_ROOT + "FCM/Contract/ContractList/2";
        } else {
            window.location = AP_ROOT + "FCM/Contract/DraftList";
        }
    },
    ResetSize: function() {
        if ($("#divContract").length > 0) {
            $("#divContract").css("height", $(window).height() - $("#divContract").offset().top);
        }
    },
};

$(document).ready(function() {

    var customter = new AssociateCustomer(
        $("#div_customer"),
        $("#ACustomer_CustomerId"),
        $("#ACustomer_CustomerNo"),
        $("#ACustomer_CustomerName")
    );

    $(window).resize(function() {
        contract.ResetSize();
    });

    $(document).click(function() {

    });

    $("#btnDraft").click(function() {
        contract.CreateUpdate(false);
    });

    $("#btnSubmit").click(function() {
       contract.CreateUpdate(true);
    });

});