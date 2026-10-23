using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Helpers;
using System.Web.Mvc;
using Dchien.Legal.BizModel;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Areas.Account.ViewModels.UserCenter;
using Dchien.Legal.Service;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service.HR.Staff;

namespace Dchien.Legal.Web.Areas.Account.Controllers
{
    [CheckUserLogin]
    public class UserCenterController : Controller
    {
        public ActionResult Account(string id)
        {
            var model = new AccountModel();
            model.UserId = LoginHelper.GetUserId();
            model.Staff = Dchien.Legal.Service.HR.Staff.StaffService.Instance.GetStaffById(model.UserId);
            return View(model);
        }

        public ActionResult Password(string id)
        {
            var model = new PasswordModel();
            model.UserId = LoginHelper.GetUserId();
            model.REDACTED_ARCHIVE_ONLY;
            return View(model);
        }

        public ActionResult Setting(string id)
        {
            var model = new SettingModel();
            model.UserId = LoginHelper.GetUserId();
            model.MenuFold = Dchien.Legal.Service.HR.Staff.StaffSettingService.Instance.MenuFold();
            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult SettingCreateUpdate(SettingModel model)
        {

            StaffSettingService.Instance.MenuFoldCreateUpdate(model.MenuFold);

            var response = new PostResponse();

            response.Message = "个性配置修改成功.";
            response.IsSuccess = true;
            return Json(response);

        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult AccountCreateUpdate(AccountModel model)
        {
            var response = new PostResponse();
            var staff = Dchien.Legal.Service.HR.Staff.StaffService.Instance.GetStaffById(LoginHelper.GetUserId());

            //staff.StaffBasic.StaffChName = model.Staff.StaffBasic.StaffChName;
            staff.StaffBasic.Email = model.Staff.StaffBasic.Email;
            staff.StaffBasic.OfficePhone = model.Staff.StaffBasic.OfficePhone;
            staff.StaffBasic.MobilePhone = model.Staff.StaffBasic.MobilePhone;

            try
            {
                StaffService.Instance.CreateUpdate(staff);

                response.Message = "基本信息修改成功.";
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }

            return Json(response);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
         [HttpPost]
        public JsonResult PassordReset(string password, string newPassword)
        {
            var oldPassword = Dchien.Legal.Service.HR.Staff.StaffService.Instance.GetStaff(LoginHelper.GetUserId()).StaffBasic.Password;

            var response = new PostResponse();

            if (CommonHelperFunc.MD5HashBinary(password) != oldPassword)
            {
                response.Message = "原密码不正确.";
                response.IsSuccess = false;
                return Json(response);
            }

            StaffService.Instance.ResetPassword(newPassword, LoginHelper.GetUserId());

            response.IsSuccess = true;
            return Json(response);

        }

        [HttpPost]
        public JsonResult Users(string userName)
        {
            var staffs = StaffService.Instance.GetStaffList();
            var response = new PostResponse();
            response.IsSuccess = true;
            var list = new List<Tuple<string, string>>();
            staffs.ForEach(x=>
            {
                if (!string.IsNullOrEmpty(x.StaffBasic.StaffChName) && x.StaffBasic.StaffChName.Contains(userName))
                {
                    list.Add(new Tuple<string, string>(x.StaffBasic.StaffName, x.StaffBasic.StaffChName));
                }
            });

            response.Data = list;
            return Json(response);
        }


        [HttpPost]
        public JsonResult AvailableUsers(string userName)
        {
            var staffs = StaffService.Instance.GetStaffList();
            var response = new PostResponse();
            response.IsSuccess = true;
            var list = new List<Tuple<string, string>>();
            staffs.ForEach(x =>
            {
                if (!string.IsNullOrEmpty(x.StaffBasic.StaffChName) && x.StaffBasic.StaffChName.Contains(userName))
                {
                    list.Add(new Tuple<string, string>(x.StaffBasic.StaffName, x.StaffBasic.StaffChName));
                }
            });

            response.Data = list;
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="userName"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult AvailableUsersWithOutMe(string userName)
        {
            var staffs = StaffService.Instance.GetStaffList();
            var response = new PostResponse();
            response.IsSuccess = true;
            var list = new List<Tuple<string, string>>();
            staffs.FindAll(x => x.StaffBasic.StaffChName != LoginHelper.GetUserChName()).ForEach(x =>
            {
                if (!string.IsNullOrEmpty(x.StaffBasic.StaffChName) && x.StaffBasic.StaffChName.Contains(userName))
                {
                    list.Add(new Tuple<string, string>(x.StaffBasic.StaffName, x.StaffBasic.StaffChName));
                }
            });

            response.Data = list;
            return Json(response);
        }
    }
}
