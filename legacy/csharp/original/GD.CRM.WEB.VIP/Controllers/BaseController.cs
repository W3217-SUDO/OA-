using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Web;
using System.Web.Mvc;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Account.User;


namespace Dchien.Legal.VipWeb.Controllers
{
    /// <summary>
    /// 基础Controller类，提供共用的逻辑到此
    /// </summary>
    public class BaseController : Controller
    {
        public System.Web.HttpContext Context { get { return System.Web.HttpContext.Current; } }

        public UserAccount UserInfo
        {
            get
            {
                if (System.Web.HttpContext.Current.Session["ipr_userInfo"] != null)
                {
                    return (UserAccount)System.Web.HttpContext.Current.Session["ipr_userInfo"];
                }
                //取userId 重新获取
                var user = new UserAccount();      //user = useBusiness.GetUserInfoByUserId(GetUserName());
                return user;
            }
        }


        #region 用户信息
        /// <summary>
        /// 获取登录userId
        /// </summary>
        /// <returns></returns>
        public static long GetUserId()
        {
            if (System.Web.HttpContext.Current.Session["ipr_userId"] != null)
            {
                return (long)System.Web.HttpContext.Current.Session["ipr_userId"];
            }
            return 0;
          
        }
        /// <summary>
        /// 返回用户基本信息
        /// </summary>
        /// <returns></returns>
        public static UserAccount GetUserInfo()
        {

            if (System.Web.HttpContext.Current.Session["ipr_userInfo"] != null)
            {
                return (UserAccount)System.Web.HttpContext.Current.Session["ipr_userInfo"];
            }
           //取userId 重新获取
            var userModel = new UserAccount(); //useBusiness.GetUserInfoByUserId(GetUserName());

            return userModel;
        }

        #endregion
    }
}
