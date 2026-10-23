using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using IntellectualProperty.Mvc.Helpers;

namespace IntellectualProperty.Mvc
{
    public static class PermissionExtensions
    {
        public static bool HasPermission(this HtmlHelper helper, int moduleCode)
        {
            return PermissionHelper.CheckPermission(moduleCode);
        }

        public static string CheckPermission(this string html, int moduleCode)
        {
            if (PermissionHelper.CheckPermission(moduleCode))
            {
                return html;
            }
            else
            {
                return string.Empty;
            }
        }

        public static IHtmlString CheckPermission(this IHtmlString html, int moduleCode)
        {
            if (PermissionHelper.CheckPermission(moduleCode))
            {
                return html;
            }
            else
            {
                return MvcHtmlString.Empty;
            }
        }
    }
}