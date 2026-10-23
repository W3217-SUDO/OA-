$(document).ready(function () {

    $(document).off('click', '#btnCreateUpdate').on('click', '#btnCreateUpdate', function () {
        var isValid = false;

        $("#companyform :text").each(function () {
            if ($(this).val() == '') {
                $.showModalMessageBox("请输入红星*必填项.");
                isValid = true;
                return false;
            }
        });

        if (isValid) return false;

        var isEmail = /^\w+((-\w+)|(\.\w+))*\@[A-Za-z0-9]+((\.|-)[A-Za-z0-9]+)*\.[A-Za-z0-9]+$/;

        if (!isEmail.test($("#Company_ContractEmail").val())) {
            $.showModalMessageBox("请填写正确联系邮箱！");
            return false;
        }

        $("#companyform").ajaxPost( AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/CompanyCreateUpdate", function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                $("#CompanyId").val(parseInt(response.Data));
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        });
    });
})