/*用户*/
var user = {
    Login: function () {

        if ($("#fm-login-id").val() == "") {
            $("#fm-login-id").focus();
            $("#J-error").html("<i class='fa fa-info-circle'></i><span>请输入用户名</span>");
            return false;
        }

        if ($("#fm-login-password").val() == "") {
            $("#fm-login-password").focus();
            $("#J-error").html("<i class='fa fa-info-circle'></i><span>请输入密码</span>");
            return false;
        }

        if ($("#fm-login-authCode").val() == "") {
            $("#fm-login-authCode").focus();
            $("#J-error").html("<i class='fa fa-info-circle'></i><span>请验证码</span>");
            return false;
        }

        var userName = $("#fm-login-id").val();
        var REDACTED_ARCHIVE_ONLY"#fm-login-password").val();
        var _captchaText = $("#fm-login-authCode").val();
        var _captchaGuid = $("#_captchaGuid").val();

        $("#J-error").html("");

        $(".mini-button-text").text("登录中...");

        var data = {
            userName: userName, passWord: password, _captchaText: _captchaText, _captchaGuid: _captchaGuid, rank: Math.random()
        };

        $.ajaxPost(AP_ROOT + "Home/UserLogin", data, function (response) {
            if (response.IsSuccess) {
                window.location = AP_ROOT + "Console/Index";
            } else {
                $("#loginBtn").removeAttr("disabled");
                $(".mini-button-text").text("登录");
                $("#J-error").html("<i class='fa fa-info-circle'></i><span>" + response.Message + "</span>");

                _reloadCaptchaImage();
            }
        }, false);
    },
}

$(document).ready(function () {

    $("#loginBtn").off().on("click", function () {
        user.Login();
    });

    $(window).keydown(function (e) {
        if (e.which == 13) {
            jQuery("#loginBtn").click();
        }
    });

});


