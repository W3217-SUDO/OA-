/*用户*/
var user = {
    List: function() {
        $("#postForm").ajaxPost(AP_ROOT + "System/SystemManagement/UserList", function(response) {
            if (response.IsSuccess) {
                $("tbody", "#tblUserList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.UserList, function(i, c) {
                        $("tbody", "#tblUserList").addRow(c.UserId, c.StaffBasic.StaffChName, c.EmployeeName, c.Email, c.MobilePhone, c.OfficePhone, c.DepartmentName,
                            "<a href='javascript:void(0)' onclick='javascript:user.Open(" + c.UserId + ")'>修改</a>&nbsp; &nbsp;&nbsp;<a href='javascript:void(0)' onclick='javascript:user.ResetPassword(" + c.UserId + "REDACTED_ARCHIVE_ONLY");
                    });

                    $("tfoot", "#tblUserList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.Userlist").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: user.List,
                        callBackArgs: null
                    });
                } else {
                    $("tfoot", "#tblUserList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

 
/*创建用户*/
    Open: function(userId) {

        var url = AP_ROOT + "System/SystemManagement/User";
        var data = {
            userId: userId
        };
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            $('#userModal').modal({ backdrop: 'static', keyboard: false });
            $('#userModal').on('hidden.bs.modal', function () {
                $("#userModal").remove();
            });
        });

        //$('.user').load(url, data, function(result) {
        //    $.closeLoading();
        //    $('#userModal').modal({ backdrop: 'static', keyboard: false });
        //});
    },

    Close: function() {
        $('#userModal').modal('hide');
    },

    CreateUpdate: function () {

        if ($("#User_UserName").val() == '') {
            $.showModalMessageBox("请输入员工登录名.");
            return false;
        }

        if ($("#User_EmployeeName").val() == '') {
            $.showModalMessageBox("请输入真实姓名.");
            return false;
        }

        if ($("#User_UserId").val() == '') {
            //新增用户时需要检查密码
            if ($("#User_Password").val() == '') {
                $.showModalMessageBox("请输入密码.");
                return false;
            }

            if ($("#User_PasswordConfirm").val() == '') {
                $.showModalMessageBox("请输入确认密码.");
                return false;
            }

            if ($("#User_Password").val() != $("#User_PasswordConfirm").val()) {
                $.showModalMessageBox("两次密码输入不一致.");
                return false;
            }
        }

        if ($("#User_Email").val() == '') {
            $.showModalMessageBox("请输入Email.");
            return false;
        }

        var isEmail = /^\w+((-\w+)|(\.\w+))*\@[A-Za-z0-9]+((\.|-)[A-Za-z0-9]+)*\.[A-Za-z0-9]+$/;

        if (!isEmail.test($("#User_Email").val())) {
            $.showModalMessageBox("请填写正确Email.");
            return false;
        }

        if ($("#User_MobilePhone").val() == '') {
            $.showModalMessageBox("请输入机号码.");
            return false;
        }

        if ($("#User_OfficePhone").val() == '') {
            $.showModalMessageBox("请输入固定电话.");
            return false;
        }

        if ($("#User_DepartmentName").val() == '') {
            $.showModalMessageBox("请选择所属部门.");
            return false;
        }

        if ($("#Role_Name").val() == '') {
            $.showModalMessageBox("请选择角色.");
            return false;
        }

        var data = {};

        data["User.UserId"] = $("#User_UserId").val();
        data["User.StaffBasic.StaffChName"] = $("#User_UserName").val();
        data["User.Password"] = $("#User_Password").val();
        data["User.EmployeeName"] = $("#User_EmployeeName").val();
        data["User.Email"] = $("#User_Email").val();
        data["User.MobilePhone"] = $("#User_MobilePhone").val();
        data["User.OfficePhone"] = $("#User_OfficePhone").val();
        data["User.Company"] = $("#User_Company").val();
        data["User.DepartmentId"] = $("#User_DepartmentId").val();

        data["User.IsAdmin"] = $("#User_IsAdmin").attr("checked") == "checked";
        data["User.IsDepartmentManager"] =  $("#User_IsDepartmentManager").attr("checked") == "checked";
        data["User.AccessLevel"] = $("#User_AccessLevel").val();
        data["User.OrgId"] = $("#User_OrgId").val();
        data["User.LeadRate"] = $("#User_LeadRate").val();
        data["User.CopyRate"] = $("#User_CopyRate").val();

        if ($("#Role_Id").val() != '') {
            var roleIds = $("#Role_Id").val().split(',');
            var i = 0;
            for (i = 0; i < roleIds.length; i++) {
                data["RoleIds[" + i + "]"] = roleIds[i];
            }
        }

        $.ajaxPost(AP_ROOT + "System/SystemManagement/UserCreateUpdate", data, function(response) {
             if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                user.Close();
                user.List();
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },


    ResetPassword: function (userId) {

        var data = {
            userId: userId
        };
 
        $.ajaxPost(AP_ROOT + "System/SystemManagement/ResetPassword", data, function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("设定成功.");
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },
}

$(document).ready(function() {

    $(document).click(function() {
        $("#divRoleList").die().hide();
        $("#divDepartmentList").die().hide();
        $("#divUserList").die().hide();
    });

    //user.List();

    $(".UserCreate").click(function() {
        user.Open();
    });

    $("#btnUserCreate").click(function() {
        user.Open();
    });

    $("#btnUserClose").die().live("click", function() {
        user.Close();
    });

    $("#btnUserCancel").die().live("click", function() {
        user.Close();
    });

    $("#btnUserAddItem").die().live("click", function() {
        user.UserItem.Add();
    });

    $(".btn_clear").die().live("click", function() {
        user.UserItem.Clear(this);
    });

    $(".btn_remove").die().live("click", function() {
        user.UserItem.Remove(this);
    });

    $("#btnUser").die().live("click", function() {
        user.CreateUpdate();
    });

    $("#btnUserPermissions").die().live("click", function() {
        user.CreateUpdateUserPermissions();
    });

    $("#btnUserPermissionsCancel").die().live("click", function() {
        user.PermissionsClose();
    });

    $("#btnUserPermissionsClose").die().live("click", function() {
        user.PermissionsClose();
    });

    $("#Role_Name").die().live("click", function() {

        $("#divRoleList").css({
            "position": "absolute",
            "left": $("#Role_Name").offsetParent().position().left + 15,
            "top": $("#Role_Name").offsetParent().position().top + 32
        }).toggle();
        return false;

    });

    $("#divRoleList").find("li").die().live("click", function() {
        var roleId = $(this).find("a").attr("id");
        var roleName = $(this).find("a").text();

        $("#Role_Id").val(roleId);
        $("#Role_Name").val(roleName);

        $("#divRoleList").hide();
    });

    $("#User_DepartmentName").die().live("click", function() {
        $("#divDepartmentList").css({
            "position": "absolute",
            "left": $("#User_DepartmentName").offsetParent().position().left + 15,
            "top": $("#User_DepartmentName").offsetParent().position().top + 32,
            "z-index": 1200
        }).toggle();

        return false;

    });

    $("#divDepartmentList").find("li").die().live("click", function() {
        var roleId = $(this).find("a").attr("id");
        var roleName = $(this).find("a").text();

        $("#User_DepartmentId").val(roleId);
        $("#User_DepartmentName").val(roleName);

        $("#divDepartmentList").hide();
    });


    $("#btnUserSearch").click(function () {
        user.List();
    });

    $("#User_OrgName").die().live("click", function () {
        $("#hidUserId").val("User_OrgId");
        $("#hidUserName").val("User_OrgName");
        $("#divUserList").css({
            "position": "absolute",
            "left": $("#User_OrgName").offsetParent().position().left + 15,
            "top": $("#User_OrgName").offsetParent().position().top + 32,
            "z-index": 1200
        }).toggle();
        return false;
    });

    $("#divUserList").find("li").die().live("click", function (e) {
        var currentSelectedControl = $("#hidUserName").val();
        var currentSelectedIdControl = $("#hidUserId").val();
        if ($(this).attr("id") == 'btnClear') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }
        var userId = $(this).find("a").attr("userid");
        var userName = $(this).find("a").text();
        $("#" + currentSelectedControl).val(userName);
        $("#" + currentSelectedIdControl).val(userId);
        $("#divUserList").hide();
        return false;
    });

});


