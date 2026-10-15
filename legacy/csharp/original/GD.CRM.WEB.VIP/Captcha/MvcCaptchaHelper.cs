using System.Text;
using System.Web;
using System.Web.Mvc;
using System.Web.Routing;

namespace Dchien.Legal.Web.Captcha
{
    public static class CaptchaHelper
    {
        private static MvcHtmlString Captcha(this HtmlHelper helper, string actionName, string controllerName, CaptchaOptions options)
        {
            if(options==null)
                options=new CaptchaOptions();
            var image = new CaptchaImage(options);
            HttpContext.Current.Session.Add(
                image.UniqueId,
                image);
            var url = new UrlHelper(helper.ViewContext.RequestContext);
            var sb = new StringBuilder(1500);
            const string copyrightText = "";
            sb.Append(copyrightText);
            sb.Append("<input type=\"hidden\" name=\"_captchaGuid\" id=\"_captchaGuid\"");

            if (options.DelayLoad)
            {
                sb.Append("/><script language=\"javascript\" type=\"text/javascript\">if (typeof (jQuery) == \"undefined\") { alert(\"jQuery脚本库未加载，请检查！\"); }");
                sb.Append("var _captchaPrevGuid = null,_captchaImgLoaded = false;function _loadCaptchaImage(){");
                sb.Append("if(!_captchaImgLoaded){$.ajax({type:'GET',url:'");
                sb.Append(url.Action("CaptchaLoader", "_Captcha",new RouteValueDictionary{{"area",null}}));
                sb.Append("?'+_captchaPrevGuid,global:false,success:function(data){_captchaImgLoaded=true;");
                sb.Append("$(\"#_captchaGuid\").val(data);_captchaPrevGuid=data;$(\"#");
                sb.Append(options.CaptchaImageContainerId).Append("\").html('");
                sb.Append(CreateImgTag(url.Action(actionName, controllerName, new RouteValueDictionary { { "area", null } }) + "?'+data+'", options, null));
                sb.Append("');}});} };function _reloadCaptchaImage(){_captchaImgLoaded=false;_loadCaptchaImage();};$(function(){");
                sb.Append("if($(\"#").Append(options.ValidationInputBoxId).Append("\").length==0){alert(\"未能找到验证码输入文本框，请检查ValidationInputBoxId属性是否设置正确！\");}");
                sb.Append("if($(\"#").Append(options.CaptchaImageContainerId).Append("\").length==0){alert(\"未能找到验证码图片父容器，请检查CaptchaImageContainerId属性是否设置正确！\");}");
                sb.Append("$(\"#").Append(options.ValidationInputBoxId);
                sb.Append("\").bind(\"focus\",_loadCaptchaImage)});</script>");
            }
            else
            {
                sb.AppendFormat(" value=\"{0}\" />",image.UniqueId);
                sb.Append(CreateImgTag(url.Action(actionName, controllerName, new RouteValueDictionary { { "area", null } }) + "?" + image.UniqueId, options, image.UniqueId));
                sb.Append("<script language=\"javascript\" type=\"text/javascript\">function _reloadCaptchaImage(){var ci=document.getElementById(\"");
                sb.Append(image.UniqueId);
                sb.Append("\");var sl=ci.src.length;if(ci.src.indexOf(\"&\")>-1)sl=ci.src.indexOf(\"&\");ci.src=ci.src.substr(0,sl)+\"&\"+(new Date().valueOf());}</script>");
            }
            sb.Append(copyrightText);
            return MvcHtmlString.Create(sb.ToString());
        }

        static string CreateImgTag(string url, CaptchaOptions options, string id)
        {
            var sb = new StringBuilder("<a href=\"javascript:_reloadCaptchaImage()\"><img src=\"");
            sb.Append(url);
            sb.Append("\" alt=\"Captcha\" title=\"刷新图片\" class='auth-img' width=\"");
            sb.Append(options.Width);
            sb.Append("\" height=\"");
            sb.Append(options.Height);
            if (!string.IsNullOrEmpty(id))
                sb.Append("\" id=\"").Append(id);
            //sb.Append("\" border=\"0\"/></a><a href=\"javascript:_reloadCaptchaImage()\">").Append(options.ReloadLinkText).Append("</a>");
            sb.Append("\" border=\"0\"/></a>");
            return sb.ToString();
        }

        public static MvcHtmlString Captcha(this HtmlHelper helper)
        {
            return Captcha(helper, new CaptchaOptions());
        }

        public static MvcHtmlString Captcha(this HtmlHelper helper, CaptchaOptions options)
        {
            return Captcha(helper, "CaptchaImage", "_Captcha", options);
        }
    }
}
