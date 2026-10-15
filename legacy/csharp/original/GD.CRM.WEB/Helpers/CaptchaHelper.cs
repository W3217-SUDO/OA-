using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;

using BotDetect;
using BotDetect.Web;
using BotDetect.Web.UI;
using BotDetect.Web.Mvc;

public class CaptchaHelper
{
    public static MvcCaptcha GetRegistrationCaptcha()
    {
        // all Captcha properties are set in this event handler
        WebFormsCaptcha.InitializedWebCaptcha +=
            new EventHandler<InitializedWebCaptchaEventArgs>(
                RegistrationCaptcha_InitializedWebCaptcha);
                
        // create the control instance
        MvcCaptcha registrationCaptcha = new MvcCaptcha("RegistrationCaptcha");
        registrationCaptcha.UserInputID = "CaptchaCode";

        return registrationCaptcha;
    }

    // event handler used for Captcha control property randomization
    static void RegistrationCaptcha_InitializedWebCaptcha(object sender,
        InitializedWebCaptchaEventArgs e)
    {
        if (e.CaptchaId != "RegistrationCaptcha")
        {
            return;
        }

        Captcha registrationCaptcha = sender as Captcha;

        // fixed Captcha settings 
        registrationCaptcha.ImageSize = new System.Drawing.Size(200, 50);
        registrationCaptcha.CodeLength = 4;

        // randomized Captcha settings
        registrationCaptcha.ImageStyle = CaptchaRandomization.GetRandomImageStyle();
        registrationCaptcha.SoundStyle = CaptchaRandomization.GetRandomSoundStyle();
    }

    public static MvcCaptcha GetLoginCaptcha()
    {
        // all Captcha properties are set in this event handler
        WebFormsCaptcha.InitializedWebCaptcha +=
            new EventHandler<InitializedWebCaptchaEventArgs>(
                LoginCaptcha_InitializedWebCaptcha);

        // create the control instance
        MvcCaptcha loginCaptcha = new MvcCaptcha("LoginCaptcha");
        loginCaptcha.UserInputID = "CaptchaCode";

        return loginCaptcha;
    }

    // event handler used for Captcha control property randomization
    static void LoginCaptcha_InitializedWebCaptcha(object sender,
        InitializedWebCaptchaEventArgs e)
    {
        if (e.CaptchaId != "LoginCaptcha")
        {
            return;
        }

        Captcha loginCaptcha = sender as Captcha;

        // fixed Captcha settings 
        loginCaptcha.ImageSize = new System.Drawing.Size(200, 50);
        loginCaptcha.CodeLength = 4;

        // randomized Captcha settings
        loginCaptcha.ImageStyle = CaptchaRandomization.GetRandomImageStyle();
        loginCaptcha.SoundStyle = CaptchaRandomization.GetRandomSoundStyle();
    }
}
