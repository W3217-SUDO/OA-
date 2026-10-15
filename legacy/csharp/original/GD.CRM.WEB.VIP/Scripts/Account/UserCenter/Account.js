var account = {
    ResetPassword: function () {

        if ($("#Password").val() == '') {
            $.showModalMessageBox("请输入原密码.");
            return false;
        }

        if ($("#NewPassword").val() == '') {
            $.showModalMessageBox("请输入新密码.");
            return false;
        }

        if ($("#Password").val() == $("#NewPassword").val()) {
            $.showModalMessageBox("原密码与新密码不能相同.");
            return false;
        }

        if ($("#NewPasswordConfirm").val() != $("#NewPassword").val()) {
            $.showModalMessageBox("二次输入的新密码不一致.");
            return false;
        }

        var data = {
            password: $("#Password").val(),
            NewPassword: $("#NewPassword").val(),
        };

        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Account/UserCenter/PassordReset", data, function (response) {
            if (response.IsSuccess) {
               
                $.showModalMessageBox("密码重置成功.");
            }
        });
    },

    CreateUpdate: function () {

        if ($("#Staff_StaffBasic_StaffChName").val() == '') {
            $.showModalMessageBox("请输入真实姓名.");
            return false;
        }

        if ($("#Staff_StaffBasic_Email").val() == '') {
            $.showModalMessageBox("请输入Email.");
            return false;
        }

        if ($("#Staff_StaffBasic_OfficePhone").val() == '') {
            $.showModalMessageBox("请输入办公电话.");
            return false;
        }

        if ($("#Staff_StaffBasic_MobilePhone").val() == '') {
            $.showModalMessageBox("请输入手机号码.");
            return false;
        }

        var data = {};

        data["Staff.StaffBasic.StaffChName"] = $("#Staff_StaffBasic_StaffChName").val();
        data["Staff.StaffBasic.Email"] = $("#Staff_StaffBasic_Email").val();
        data["Staff.StaffBasic.OfficePhone"] = $("#Staff_StaffBasic_OfficePhone").val();
        data["Staff.StaffBasic.MobilePhone"] = $("#Staff_StaffBasic_MobilePhone").val();
     

        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Account/UserCenter/AccountCreateUpdate", data, function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("修改基本资料成功.");
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    Setting: function () {

        var data = {};

        data["MenuFold"] = $("#MenuFold").val();

        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Account/UserCenter/SettingCreateUpdate", data, function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("修改成功.");
            }
        });
    },
}

$(document).ready(function () {

    $(document).off('click', '#btnPasswordReset').on('click', '#btnPasswordReset', function () {
        account.ResetPassword();
    });

    $(document).off('click', '#btnCreateUpdate').on('click', '#btnCreateUpdate', function () {
        account.CreateUpdate();
    });

    $(document).off('click', '#btnStaffSetting').on('click', '#btnStaffSetting', function () {
        account.Setting();
    });
    
});

