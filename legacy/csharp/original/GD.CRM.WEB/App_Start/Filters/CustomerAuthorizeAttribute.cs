using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Web;
using System.Web.Mvc;

namespace Dchien.Legal.Web
{
    public class CustomerAuthorizeAttribute : AuthorizeAttribute
    {
        public override void OnAuthorization(AuthorizationContext filterContext)
        {
            object[] actionNoAuthorize = filterContext.ActionDescriptor.GetCustomAttributes(typeof (NoAuthorizeAttribute),
                false);
            if (actionNoAuthorize.Length > 0)
            {
                return;
            }

            object[] controllerNoAuthorize =
                filterContext.ActionDescriptor.ControllerDescriptor.GetCustomAttributes(typeof (NoAuthorizeAttribute),
                    false);

            if (controllerNoAuthorize.Length > 0)
            {
                return;
            }

            base.OnAuthorization(filterContext);
        }

        protected override bool AuthorizeCore(HttpContextBase httpContext)
        {
            if (string.IsNullOrWhiteSpace(Dchien.Legal.Service.LoginHelper.GetUserName()))
            {
                return false;
            }
            else
            {
                return true;
            }
        }

        protected override void HandleUnauthorizedRequest(AuthorizationContext filterContext)
        {
            filterContext.Result = new RedirectResult("~/Home/Login");
        }
    }
}