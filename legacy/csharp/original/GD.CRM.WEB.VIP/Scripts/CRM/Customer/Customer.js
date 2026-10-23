function AssociateCustomerOwner(div, ctlid, ctlname, func) {

    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;
    this.CallBackFunc = func;

    this.CaseUserName = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") {
            return false;
        }
        var curobj = new Object();
        curobj.keyword = name;

        var html = '';
        var data = { userName: name };
        $.ajaxPostMessage( AP_ROOT + AP_PAGE_ID + "/Account/UserCenter/Users", data, function (response) {
            if (response.IsSuccess) {
                $.each(response.Data, function (i, c) {
                    html += '<a href="javascript:void(0)" userId=' + c.Item1 + '>' + c.Item2 + '</a>';
                });

                $(div).find(".i_common_list").html(html);
                $(div).find(".i_common_list a").click(function () {
                    $(ctlid).val($(this).attr("userId"));
                    $(ctlname).val($(this).text());
                    $(div).hide();
                });

                $(div).css({
                    "position": "absolute",
                    "left": $(ctlname).offsetParent().position().left + 650,
                    "top": $(ctlname).offsetParent().position().top + 168,
                    "z-index": 99999
                }).show();
            }
        }, false);


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
            event.data.obj.Event = setTimeout(function () { event.data.obj.CaseUserName(event.data.obj); }, 500);
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
    });

    return this;
}

/*案件客户*/
var customer = {
    List: function() {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/Customer/List", function(response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCustomerList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.Customers, function (i, c) {

                        $("tbody", "#tblCustomerList").addRow(
                                        "<a href=" +  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseList?customerId=" + c.CustomerId + " target='_blank'><span>" + c.CustomerNo + "</span></a>",
                                        "<span style='width: 200px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.CustomerName + "</span>",
                                          "<span style='width: 200px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.CompanyCode + "</span>",
                                        "<a href='javascript:void(0)' onclick='javascript:contract.Open(" + c.CustomerId + ")'>新建合同</a> &nbsp; "
                                        + "<a href='javascript:void(0)' onclick='javascript:customer.OpenCommunication(" + c.CustomerId + ")'>新增沟通记录</a> &nbsp;"
                                        + "<a href='javascript:void(0)' onclick='javascript:customer.Open(" + c.CustomerId + "," + c.CustomerSourceTypeId + ")'>修改</a> &nbsp;"
                                        + "<a href='javascript:void(0)' onclick='javascript:customer.ContactsList(" + c.CustomerId + ")'>联系人管理</a>");
                                       
                        
                    });

                    $("tfoot", "#tblCustomerList").show();
                    $(".simple-grid-none-data-wrap").hide();
                     
                    $(".pull-right.page-box.customer").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: customer.List,
                        callBackArgs: null
                    });
                } else {
                     
                    $("tfoot", "#tblCustomerList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    /*创建沟通记录*/
    OpenCommunication: function (customerId) {
        var data = { customerId: customerId };
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

    /*创建客户*/
    Open: function (customerId, customerSourceTypeId) {
         
        var data =
        {
            customerId: customerId,
            customerSourceTypeId: customerSourceTypeId
        };
        var url =  AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CreateUpdate";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            var customerOwner = new AssociateCustomerOwner(
                $("#divUserList"),
                $("#Customer_CustomerOwner"),
                $("#Customer_CustomerOwnerName"),
                null
                );

            $('#customerModal').modal({ backdrop: 'static', keyboard: false });
             $('#customerModal').on('hidden.bs.modal', function () {
                $("#customerModal").remove();
            });
        });

        //$('.customerCreateUpdate').load(url, data, function (result) {
        //    $.closeLoading();
        //    $('#customerModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },

    /*客户联系人*/
    ContactsList: function (customerId) {
        var data = {
            customerId: customerId
        };
        var url =  AP_ROOT + AP_PAGE_ID + "/CRM/Customer/ContactsList";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);
            $('#contactsListModal').modal({ backdrop: 'static', keyboard: false });
            $('#contactsListModal').on('hidden.bs.modal', function () {
                $("#contactsListModal").remove();
            });
        });

        //$('.contactsList').load(url, data, function (result) {
        //    $.closeLoading();
        //    $('#contactsListModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },

    /*保存客户信息*/
    CreateUpdate: function () {
        if (!postValid()) {
            return false;
        }

        if ($("#flLicenseFile").val() == '') {
            $.showModalMessageBox("请选择上传文件.");
            return false;
        }
        
        $("#customerForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CustomerCreateUpdate", function (response) {
            if (response.IsSuccess) {
                $('#Customer_CustomerBasic_CustomerId').val(response.Data.CustomerId);
                $('#Customer_DefaultContacts_ContactsId').val(response.Data.DefaultContacts.ContactsId);
                $.showModalMessageBox("保存成功.");
                customer.List();
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        });

        return true;
    },

    /*关闭窗体*/
    Close: function () {
        $('#customerModal').modal('hide');
    } ,
    
    License:
    {
        /*上传营业执照*/
        Open: function () {
            var data =
            {
                customerId: $('#Customer_CustomerBasic_CustomerId').val(),
                customerNo: $('#Customer_CustomerBasic_CustomerNo').val()
            };
             
            if ($('#Customer_CustomerBasic_CustomerId').val() == '' || $('#Customer_CustomerBasic_CustomerId').val() == "0") {
                $.showModalMessageBox("请先保存客户基本资料，再上传.");
                return false;
            }

            var url =  AP_ROOT + AP_PAGE_ID + "/CRM/Customer/License";

            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#licenseModal').modal({ backdrop: 'static', keyboard: false });
                $('#licenseModal').on('hidden.bs.modal', function () {
                    $("#licenseModal").remove();
                });
            });

            //$('.licenseUploading').load(url, data, function (result) {
            //    $('#licenseModal').modal({ backdrop: 'static', keyboard: false });
            //});
        },

        /*上传*/
        Upload: function () {
            $('#uploadingForm').ajaxSubmit({
                success: function (response) {
                    $("#imgLicense").attr("src", response.Data);
                    $("#aimgLicense").attr("href", response.Data);
                    $.showModalMessageBox("保存成功.");
                    $('#licenseModal').modal('hide');
                }
            });
        },

        /*关闭律所窗体*/
        Close: function () {
            $('#licenseModal').modal('hide');
        }
    },
}

var contract = {

    /*新建合同*/
    Open: function(customerId) {

        window.open(AP_ROOT + "4001001/FCM/ContractDraft/Draft?customerId=" + customerId);
        //window.location =  AP_ROOT + AP_PAGE_ID + "/FCM/ContractDraft/Draft?customerId=" + customerId;

        //var data = { customerId: customerId };
        //var url =  AP_ROOT + AP_PAGE_ID + "/FCM/Contract/ContractType";
        //$.openLoading();

        //$("<div></div>").load(url, data, function(result) {
        //    $.closeLoading();
        //    $(document.body).append(result);
        //    $('#contractTypeModal').modal({ backdrop: 'static', keyboard: false });
        //    $('#contractTypeModal').on('hidden.bs.modal', function() {
        //        $("#contractTypeModal").remove();
        //    });
        //});
    },

    Close: function () {
        $('#contractTypeModal').modal('hide');
    },

    Selected: function () {
        var customerId = $("#CustomerId").val();

        var contractType = $("#ContractType").val();

        if (contractType == 'PI') {
            window.location = AP_ROOT + "4001001/FCM/Patent/Draft?customerId=" + customerId;
        } else {
            window.location = AP_ROOT + "4001001/FCM/Contract/Draft?customerId=" + customerId;

        }
    }
}

$(document).ready(function () {

    customer.List();

    $(".customerCreate").click(function () {
         
        customer.Open();
    });

    $("#btnCustomerCreate").click(function () {
        customer.Open(0,1);
    });

    $("#btnLsCustomerCreate").click(function () {
        customer.Open(0,2);
    });

    $("#btnCancle").off().on("click", function () {
         
        customer.Close();
    });

    $("#btnClose").off().on("click", function () {
        customer.Close();
    });

    $("#btnCreateUpdate").off().on("click", function () {
        customer.CreateUpdate();
    });

    $("#flLicenseFile").off().on("change", function () {
        $("#txtLicenseFilePath").val($("#flLicenseFile").val());
    });

    $("#btnLicenseUploading").off().on("click", function () {
        customer.License.Open();
    });

    $("#btnUploadingCanel").off().on("click", function () {
        customer.License.Close();
    });

    $("#btnUploadingClose").off().on("click", function () {
        customer.License.Close();
    });

    $("#btnUploading").off().on("click", function () {
        customer.License.Upload();
    });

    $("#btnCustomerSearch").off().on("click", function () {
        customer.List();
    });

    $("#btnContractType").off().on("click", function () {
        customer.List();
    });
    
    $("#btnContractType").off().on("click", function () {
        contract.Selected();
    });

    $("#btnContractTypeCancel,#btnContractTypeClose").off().on("click", function () {
        contract.Close();
    });

});

function postValid() {

    //if (!CheckModifyTime()) return false;

    //判断必填项的项是否填写

    if ($("#Customer_CustomerSourceTypeId").val() == '2') {

        if ($("#Customer_CustomerName").val() == '') {
            $.showModalMessageBox("客户名不能为空");
            return false;
        }

        return true;
    }

    var flag = true;
    $("#tblCustomer :text").each(function () {
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

    if ($("#Customer_Email").val() != '') {
        var isEmail = /^\w+((-\w+)|(\.\w+))*\@[A-Za-z0-9]+((\.|-)[A-Za-z0-9]+)*\.[A-Za-z0-9]+$/;

        if (!isEmail.test($("#Customer_Email").val())) {
            $.showModalMessageBox("请填写正确客户邮箱.");
            return false;
        }
    }

    if ($("#Customer_DefaultContacts_ContactEmail").val() != '') {
        var isEmail = /^\w+((-\w+)|(\.\w+))*\@[A-Za-z0-9]+((\.|-)[A-Za-z0-9]+)*\.[A-Za-z0-9]+$/;

        if (!isEmail.test($("#Customer_DefaultContacts_ContactEmail").val())) {
            $.showModalMessageBox("请填写正确联系邮件.");
            return false;
        }
    }

    return true;
}


