using System;
using System.Configuration;
using System.Web.Mvc;

namespace Dchien.Legal.Web.Captcha
{
    /// <summary>
    /// 
    /// </summary>
    [AttributeUsage(AttributeTargets.Method, AllowMultiple = false, Inherited = false)]
    public sealed class ValidateCaptchaAttribute : ActionFilterAttribute
    {
        /// <summary>
        /// Initializes a new instance of the CaptchaValidationAttribute class.
        /// </summary>
        public ValidateCaptchaAttribute()
            : this("_captchaText") { }

        /// <summary>
        /// Initializes a new instance of the CaptchaValidationAttribute class.
        /// </summary>
        /// <param name="field">The field.</param>
        public ValidateCaptchaAttribute(string field)
        {
            Field = field;
        }

        /// <summary>
        /// Gets or sets the field.
        /// </summary>
        /// <value>The field.</value>
        public string Field { get; private set; }

        public string ConfigurationKey { get; set; }


        /// <summary> 
        /// Called when [action executed]. 
        /// </summary> 
        /// <param name="filterContext">The filter filterContext.</param> 
        public override void OnActionExecuting(ActionExecutingContext filterContext)
        {
            if (!String.IsNullOrEmpty(ConfigurationKey))
            {
                bool enabled;
                var configuredValue = ConfigurationManager.AppSettings[ConfigurationKey];
                if (Boolean.TryParse(configuredValue, out enabled) && !enabled)
                    return;
            }

            // get the guid from the post back 
            string guid = filterContext.HttpContext.Request.Form["_CaptchaGuid"];

            // get values 
            var image = CaptchaImage.GetCachedCaptcha(guid);
            string actualValue = filterContext.HttpContext.Request.Form[Field];
            string expectedValue = image == null ? String.Empty : image.Text;

            // removes the captch from Session so it cannot be used again 
            filterContext.HttpContext.Session.Remove(guid);

            bool isValid = !String.IsNullOrEmpty(actualValue)
                           && !String.IsNullOrEmpty(expectedValue)
                           && String.Equals(actualValue, expectedValue, StringComparison.OrdinalIgnoreCase);
            if (!isValid)
                ((Controller) filterContext.Controller).ModelState.AddModelError(Field, "验证码不匹配");
                                                                                 //(string)filterContext.HttpContext.GetGlobalResourceObject("LangPack","ValidationCode_Not_Match"));
        }

    }
}
