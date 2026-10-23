using System.Web;
using System.Web.Mvc;

namespace Dchien.Legal.Web.Captcha
{
    public class _CaptchaController:Controller
    {
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [NoAuthorizeAttribute]
        public ActionResult CaptchaImage()
        {
            return new CaptchaImageResult();
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [NoAuthorizeAttribute]
        public ActionResult CaptchaLoader()
        {
            string prevGuid = Request.ServerVariables["Query_String"];
            if (!string.IsNullOrEmpty(prevGuid))
                HttpContext.Session.Remove(prevGuid); 
            var options = new CaptchaOptions();
            var config=CaptchaConfigSection.GetConfig();
            if(config!=null)
            {
                options.TextChars = config.TextChars;
                options.TextLength = config.TextLength;
                options.FontWarp = config.FontWarp;
                options.BackgroundNoise = config.BackgroundNoise;
                options.LineNoise = config.LineNoise;
            }
            
            var image = new CaptchaImage(options);
            HttpContext.Session.Add(
                 image.UniqueId,
                 image);
            HttpContext.Response.Cache.SetNoStore();
            HttpContext.Response.Cache.SetCacheability(HttpCacheability.NoCache);
            return Content(image.UniqueId);
        }
    }
}
