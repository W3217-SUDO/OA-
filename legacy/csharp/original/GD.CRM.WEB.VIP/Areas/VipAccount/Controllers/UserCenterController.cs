using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Helpers;
using System.Web.Mvc;
using Dchien.Legal.BizModel;
using Dchien.Legal.Common;
using Dchien.Legal.VipWeb.Areas.VipAccount.ViewModels.UserCenter;
using Dchien.Legal.Service;
using Dchien.Legal.VipWeb.Controllers;
using Dchien.Legal.VipWeb.Models;
using Dchien.Legal.Service.HR.Staff;

namespace Dchien.Legal.VipWeb.Areas.VipAccount.Controllers
{
    [CheckVipUserLogin]
    public class UserCenterController : Controller
    {
        public ActionResult Account(string id)
        {
            var model = new AccountModel();
            model.UserId = VipLoginHelper.GetUserId();
            model.Account = Dchien.Legal.Service.CRM.Customer.ContactsService.Instance.GetVipAccountByName(VipLoginHelper.GetUserName());
            return View(model);
        }

        public ActionResult Password(string id)
        {
            var model = new PasswordModel();
            model.UserId = VipLoginHelper.GetUserId();
            
            return View(model);
        }

        public ActionResult Setting(string id)
        {
            var model = new SettingModel();
            model.UserId = VipLoginHelper.GetUserId();
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
            var account = Dchien.Legal.Service.CRM.Customer.ContactsService.Instance.GetCustomerContactsById(VipLoginHelper.GetUserId());

            account.Contacts = model.Account.UserChName;
            account.Email = model.Account.Email;
            account.OfficePhone = model.Account.OfficePhone;
             
            Dchien.Legal.Service.CRM.Customer.ContactsService.Instance.UpdateVipAccount(account);

            var response = new PostResponse();

            response.Message = "基本信息修改成功.";
            response.IsSuccess = true;
            return Json(response);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
         [HttpPost]
        public JsonResult PassordReset(string password, string newPassword)
        {
            var oldPassword = Dchien.Legal.Service.CRM.Customer.ContactsService.Instance.GetCustomerContactsById(VipLoginHelper.GetUserId()).OrgPassword;

            var response = new PostResponse();

            if (password != oldPassword)
            {
                response.Message = "原密码不正确.";
                response.IsSuccess = false;
                return Json(response);
            }

            Dchien.Legal.Service.CRM.Customer.ContactsService.Instance.ResetPassword(newPassword, VipLoginHelper.GetUserId());

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
                if (!string.IsNullOrEmpty(x.StaffBasic.StaffChName) && x.StaffBasic.StaffChName.Contains(userName) && x.StaffBasic.IsActived)
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
                if (!string.IsNullOrEmpty(x.StaffBasic.StaffChName) && x.StaffBasic.StaffChName.Contains(userName) && x.StaffBasic.IsActived)
                {
                    list.Add(new Tuple<string, string>(x.StaffBasic.StaffName, x.StaffBasic.StaffChName));
                }
            });

            response.Data = list;
            return Json(response);
        }
    }
}
