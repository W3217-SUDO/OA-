/*案件客户*/
var customer = {
    List: function() {
        $("#postForm").ajaxPost(AP_ROOT + "IPR/Customer/List", function(response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCustomerList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.Customers, function (i, c) {

                        $("tbody", "#tblCustomerList").addRow(
                                        "<a href=" + AP_ROOT + "IPR/Case/CaseList?customerId=" + c.CustomerId + " target='_blank'><span>" + c.CustomerNo + "</span></a>",
                                        c.CustomerName, c.RegisteredAddress,
                                        c.Telphone, c.CompanyCode,
                                        c.CustomerCode,
                                        "<a href='javascript:void(0)' onclick='javascript:customer.Open(" + c.CustomerId + ")'>修改</a> &nbsp; &nbsp;&nbsp;" +
                                        "<a href='javascript:void(0)' onclick='javascript:customer.ContactsList(" + c.CustomerId + ")'>联系人管理</a>");
                        
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

    /*创建客户*/
    Open: function (customerId) {
         
        var data =
        {
            customerId: customerId,
        };
        var url = AP_ROOT + "IPR/Customer/CreateUpdate";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);
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
        var url = AP_ROOT + "IPR/Customer/ContactsList";
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
        
        $("#customerForm").ajaxPost(AP_ROOT + "IPR/Customer/CustomerCreateUpdate", function (response) {
            if (response.IsSuccess) {
                $('#Customer_CustomerId').val(response.Data.CustomerId);
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
                customerId: $('#Customer_CustomerId').val(),
                customerNo: $('#Customer_CustomerNo').val()
            };
             
            if ($('#Customer_CustomerId').val() == '' || $('#Customer_CustomerId').val() == "0") {
                $.showModalMessageBox("请先保存客户基本资料，再上传.");
                return false;
            }

            var url = AP_ROOT + "IPR/Customer/License";

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

$(document).ready(function () {

    customer.List();

    $(".customerCreate").click(function () {
         
        customer.Open();
    });

    $("#btnCustomerCreate").click(function () {
        customer.Open();
    });

    $("#btnCancle").die().live("click", function () {
         
        customer.Close();
    });

    $("#btnClose").die().live("click", function () {
        customer.Close();
    });

    $("#btnCreateUpdate").die().live("click", function () {
        customer.CreateUpdate();
    });

    $("#flLicenseFile").die().live("change", function () {
        $("#txtLicenseFilePath").val($("#flLicenseFile").val());
    });

    //
    $("#btnLicenseUploading").die().live("click", function () {
        customer.License.Open();
    });

    $("#btnUploadingCanel").die().live("click", function () {
        customer.License.Close();
    });

    $("#btnUploadingClose").die().live("click", function () {
        customer.License.Close();
    });

    $("#btnUploading").die().live("click", function () {
        customer.License.Upload();
    });

    $("#btnCustomerSearch").die().live("click", function () {
        customer.List();
    });

});

function postValid() {

    //if (!CheckModifyTime()) return false;

    //判断必填项的项是否填写

    var flag = true;
    $("#postForm :text").each(function () {
          $(this).val() = ''

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

                $.ajaxPost(AP_ROOT + "IntlFare/ValidAssociate", data, function (response) {
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


