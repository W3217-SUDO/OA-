using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using Dchien.Legal.BizModel.System;
using Dchien.Legal.Common;
using Dchien.Legal.Common.Utility;

using Dchien.Legal.Service;
using Dchien.Legal.VipWeb.Captcha;
using Dchien.Legal.VipWeb.Models;

namespace Dchien.Legal.VipWeb.Controllers
{
    public class HomeController : Controller
    {
        internal Log Logger = new Log("Legal.Controllers.HomeController");

        [AllowAnonymous]
        [NoAuthorize]
        public ActionResult Index()
        {
            if (System.Web.HttpContext.Current.Session["legal_vip_userId"] != null || System.Web.HttpContext.Current.Session["legal_vip_userInfo"] != null)
            {
                return new RedirectResult("~/Console/Index");
            }
           
            System.Web.HttpContext.Current.Session["legal_vip_userId"] = null;
            System.Web.HttpContext.Current.Session["legal_vip_userInfo"] = null;
            return View();
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [AllowAnonymous]
        [NoAuthorize]
        public ActionResult Login()
        {
            System.Web.HttpContext.Current.Session["legal_vip_userId"] = null;
            System.Web.HttpContext.Current.Session["legal_vip_userInfo"] = null;
            return View();
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [AllowAnonymous]
        [NoAuthorize]
        public ActionResult Logout()
        {
            System.Web.HttpContext.Current.Session["legal_vip_userId"] = null;
            System.Web.HttpContext.Current.Session["legal_vip_userInfo"] = null;
            var account = Request.Cookies["legal_vip_uid"];
            if (account == null)
                account = new HttpCookie("legal_vip_uid");
            account.Value = string.Empty;
            Response.AppendCookie(account);
            return RedirectToAction("Index", "Home");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [AllowAnonymous]
        [AcceptVerbs(HttpVerbs.Post), ValidateCaptcha()]
        [NoAuthorize]
        public ActionResult UserLogin()
        {
            var response = new PostResponse();
            if (!ModelState.IsValid)
            {
                response.IsSuccess = false;
                response.Message = "验证码错误，请重新输入";
                return Json(response);
            }

            if (string.IsNullOrEmpty(Request["userName"]) || string.IsNullOrEmpty(Request["passWord"]))
            {
                response.IsSuccess = false;
                response.Message = "用户名不存在，或密码不正确";
                return Json(response);
            }

            var userName = string.Empty;
            var REDACTED_ARCHIVE_ONLY;

            if (!string.IsNullOrEmpty(Request["userName"]))
                userName = CommonHelperFunc.SecurityFilterHtml(Request["userName"]);

            if (!string.IsNullOrEmpty(Request["passWord"]))
                REDACTED_ARCHIVE_ONLY"passWord"]);

            string md5Pad = CommonHelperFunc.MD5HashBinary(passWord);
            //
            var userInfo = Dchien.Legal.Service.CRM.Customer.ContactsService.Instance.GetVipAccountByPassword(userName, md5Pad);
            if (userInfo == null)
            {
                response.IsSuccess = false;
                response.Message = "用户名不存在，或密码不正确";
                return Json(response);
            }

            #region

            long userId = userInfo.UserId;
            System.Web.HttpContext.Current.Session["legal_vip_userId"] = null;
            System.Web.HttpContext.Current.Session["legal_vip_userId"] = userId;

            System.Web.HttpContext.Current.Session["legal_vip_userInfo"] = null;
            System.Web.HttpContext.Current.Session["legal_vip_userInfo"] = userInfo;

            var account = Request.Cookies["legal_vip_uid"];
            if (account == null)
            {
                account = new HttpCookie("legal_vip_uid");
            }
            account.Expires = DateTime.Now.AddDays(1);
            account.Value = CommonHelperFunc.EncryptDES(userInfo.UserName); 
            Response.AppendCookie(account);

            #endregion

            response.IsSuccess = true;
            return Json(response);

        }
    }
}