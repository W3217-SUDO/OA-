using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Web.Mvc;
using System.Web.Routing;

using Dchien.Legal.Service;

namespace Dchien.Legal.Web.Controllers
{

    /// <summary>
    /// 重写判定用户登录是否登录以及登录身份的合法性验证
    /// </summary>
    public class CheckUserLogin : ActionFilterAttribute
    {
        public override void OnActionExecuting(ActionExecutingContext filterContext)
        {
            if (filterContext.HttpContext.Session != null)
            {
                var userId = filterContext.HttpContext.Session["ipr_userId"];

                if (userId == null || userId.ToString() == "" || userId.ToString() == "0")
                {
                    var userInfo = LoginHelper.GetUserAccount();

                    if (userInfo != null && userInfo.UserId.ToString() !=  "0")
                    {
                        userId = userInfo.UserId;

                        System.Web.HttpContext.Current.Session["ipr_userId"] = null;
                        System.Web.HttpContext.Current.Session["ipr_userId"] = userId;

                        System.Web.HttpContext.Current.Session["ipr_userInfo"] = null;
                        System.Web.HttpContext.Current.Session["ipr_userInfo"] = userInfo;

                        return;
                    }
                   
                    if (!filterContext.HttpContext.Request.IsAjaxRequest())
                    {
                        filterContext.Result =
                            new RedirectToRouteResult(
                                new RouteValueDictionary(new {Controller = "Home", Action = "Index", area = ""}));
                        //这里是跳转到Account下的LogOff,自己定义
                    }
                    else
                    {
 
                        filterContext.Result = new JsonResult
                        {
                            Data = new
                            {
                                IsSuccess = false,
                                Message = string.Empty,
                                IsRedirect = true
                            }
                        };
                    }
                }
            }
        }
    }

    ///// <summary>
    ///// 
    ///// </summary>
    //public class CheckOfflinePermission : ActionFilterAttribute
    //{
    //    public override void OnActionExecuting(ActionExecutingContext filterContext)
    //    {
    //        if (filterContext.HttpContext.Session != null)
    //        {
    //            if (filterContext.HttpContext.Session["ipr_userId"] == null)
    //            {
    //                filterContext.Result = new RedirectToRouteResult(new RouteValueDictionary(new { Controller = "Home", Action = "Index" }));//这里是跳转到Account下的LogOff,自己定义
    //            }
    //            else
    //            {
    //                long userId = (long)filterContext.HttpContext.Session["ipr_userId"];

    //                var userModel = new UserModel();  //useBusiness.GetUserInfoByUserId(userId);
                   
    //                //if (userViewModel == null || userViewModel.UserID == 0)
    //                //    filterContext.Result = new RedirectToRouteResult(new RouteValueDictionary(new { Controller = "User", Action = "Login" }));

    //                //当是offlien页面时，如当前用户不是小二用户，则是非法进入的
    //                if (userModel.UserType ==1)
    //                    filterContext.Result = new RedirectToRouteResult(new RouteValueDictionary(new { Controller = "Home", Action = "Index" }));
    //            }

    //        }

    //    }
    //}
}
