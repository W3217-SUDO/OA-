/*用户*/
var user = {
    Login: function () {

        if ($("#fm-login-id").val() == "") {
            $("#fm-login-id").focus();
            $(".login-msg-ctn").html("<div class='msg'><i class='glyphicon glyphicon-exclamation-sign' style='float: left;padding: 2.5px 5px 0 0;font-size: 1.5em;'></i><ul><li><span class='msg-item'>请输入用户名</span></li></ul></div>");
            return false;
        }

        if ($("#fm-login-password").val() == "") {
            $("#fm-login-password").focus();
            $(".login-msg-ctn").html("<div class='msg'><i class='glyphicon glyphicon-exclamation-sign' style='float: left;padding: 2.5px 5px 0 0;font-size: 1.5em;'></i><ul><li><span class='msg-item'>请输入密码</span></li></ul></div>");
            return false;
        }

        if (window.ENABLE_LOGIN_CAPTCHA && $("#fm-login-authCode").val() == "") {
            $("#fm-login-authCode").focus();
            $(".login-msg-ctn").html("<div class='msg'><i class='glyphicon glyphicon-exclamation-sign' style='float: left;padding: 2.5px 5px 0 0;font-size: 1.5em;'></i><ul><li><span class='msg-item'>请验证码</span></li></ul></div>");
            return false;
        }

        var userName = $("#fm-login-id").val();
        var REDACTED_ARCHIVE_ONLY"#fm-login-password").val();
        var _captchaText = window.ENABLE_LOGIN_CAPTCHA ? $("#fm-login-authCode").val() : "";
        var _captchaGuid = window.ENABLE_LOGIN_CAPTCHA ? $("#_captchaGuid").val() : "";

        $(".login-msg-ctn").html("");

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
                $(".login-msg-ctn").html("<div class='msg'><i class='glyphicon glyphicon-exclamation-sign' style='float: left;padding: 2.5px 5px 0 0;font-size: 1.5em;'></i><ul><li><span class='msg-item'>" + response.Message + "</span></li></ul></div>");

                if (window.ENABLE_LOGIN_CAPTCHA) {
                    _reloadCaptchaImage();
                }
            }
        },false);
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


