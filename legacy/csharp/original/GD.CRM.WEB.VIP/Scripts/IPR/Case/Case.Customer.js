
var customer = {
    Customer: {
        CreateUpdate: function () {

            if ($("#Customer_CustomerBasic_CustomerName").val() == '') {
                $.showModalMessageBox("请输入客户名称.");
                return false;
            }

            if ($("#province").val() != "- 请选择 -") {
                $("#Customer_CustomerBasic_Province").val($("#province").val());
            }

            if ($("#city").val() != "- 请选择 -") {
                $("#Customer_CustomerBasic_City").val($("#city").val());
            }

            var regd = /^.*[-—\\\'\"<>|]+.*$/;
            if (regd.test($("#Customer_CustomerRegistration_RegistrationAddress").val())) {
                $.showModalMessageBox("注册地址禁止输入 <  >  \"   \'  \\ 半角字符，请检查");
                return false;
            }

            if (regd.test($("#Customer_CustomerRegistration_LicenseNo").val())) {
                $.showModalMessageBox("统一社会信用代码禁止输入 <  >  \"   \'  \\ 半角字符，请检查");
                return false;
            }

            if (regd.test($("#Customer_CustomerBasic_Zip").val())) {
                $.showModalMessageBox("邮编禁止输入 <  >  \"   \'  \\ 半角字符，请检查");
                return false;
            }

            $("#customerForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CaseCustomerCreateUpdate", function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("保存成功.");
                    caseInfo.CaseCustomer.AddIn(response.Data.CustomerBasic.CustomerId, response.Data.CustomerBasic.CustomerNo, response.Data.CustomerBasic.CustomerName)
                    caseInfo.CaseCustomer.Close();
                    
                }
                else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },
    },
};

$(document).ready(function () {

    //$(":input", "#customerForm").each(function () {
    //    $(this).attr("disabled", "disabled");
    //});

    var province = $("#Customer_CustomerBasic_Province").val();
    var city = $("#Customer_CustomerBasic_City").val();
    $('#district').citys({ code: city });

});


$("#btnCustomerEdit").off().on("click", function () {
    $(":input", "#customerForm").each(function () {
        $(this).removeAttr("disabled", "disabled");
    });

    $("#Customer_CustomerBasic_CustomerNo").attr("disabled", "disabled");
    $("#Customer_CustomerBasic_CustomerName").attr("disabled", "disabled");
    $("#btnCustomerCreateUpdate").css("display", "inline-block")
    $("#btnCustomerEdit").css("display", "none")

});

$("#btnCustomerCreateUpdate").off().on("click", function () {
    customer.Customer.CreateUpdate();
});

$("#btnCustomerCreate").off().on("click", function () {
    customer.Customer.CreateUpdate();
});

 