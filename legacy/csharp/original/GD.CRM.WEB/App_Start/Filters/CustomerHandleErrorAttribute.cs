using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.Common;
using Dchien.Legal.Common.Utility;

namespace Dchien.Legal.Web
{
    public class CustomerHandleErrorAttribute : HandleErrorAttribute
	{
        internal Log Logger = new Log("Dchien.Legal.Web.CustomerHandleError");
        public override void OnException(ExceptionContext filterContext)
        {
            if (!filterContext.ExceptionHandled)
            {
                string controllerName = (string)filterContext.RouteData.Values["controller"];
                string actionName = (string)filterContext.RouteData.Values["action"];
                string msgTemplate = "在执行 controller[{0}] 的 action[{1}] 时产生异常";

                Logger.Error(Dchien.Legal.Service.LoginHelper.GetClientIP(), Dchien.Legal.Service.LoginHelper.GetUserName(), actionName, string.Format(msgTemplate, controllerName, actionName), filterContext.Exception);
            }

            //if (filterContext.HttpContext.Request.IsAjaxRequest())
            //{
            //    var response = new Dchien.Legal.Web.Models.PostResponse();
            //    response.IsSuccess = false;
            //    response.Message = filterContext.Exception.Message;
            //    filterContext.ExceptionHandled = true;
            //    filterContext.Result = new JsonResult()
            //    {
            //        Data = response,
            //        JsonRequestBehavior = JsonRequestBehavior.AllowGet
            //    };
            //}

            base.OnException(filterContext);
        }
    }
}