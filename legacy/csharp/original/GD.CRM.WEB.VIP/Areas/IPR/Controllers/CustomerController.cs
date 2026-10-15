 using System;
using System.Collections.Generic;
 using System.IO;
 using System.Linq;
using System.Web;
using System.Web.Mvc;

using SunHold.Legal.BizModel;
 using SunHold.Legal.BizModel.IPR.Customer;
 using SunHold.Legal.Common;
 using SunHold.Legal.Web.Areas.IPR.ViewModels;
using SunHold.Legal.Web.Areas.IPR.ViewModels.Customer;
using SunHold.Legal.Service;
using SunHold.Legal.Service.IPR.Customer;
 using log4net.Repository.Hierarchy;
 using SunHold.Legal.Web.Controllers;
 using SunHold.Legal.Web.Models;

namespace SunHold.Legal.Web.Areas.IPR.Controllers
{
     [CheckUserLogin]
    public class CustomerController : Controller
    {
        #region 客户列表


        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult Index(int? id)
        {
            var model = new IndexModel();

            var lst = CustomerTypeService.Instance.GetCustomerType();
            
            model.CustomerTypeId = id.HasValue ? id.Value : 1;
            model.CaseCustomerTypeList = lst;

            return View(model);
        }

        [CheckUserLogin]
        [HttpPost]
        public JsonResult List(IndexModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 20;

                model.SearchCondition.CustomerTypeId = model.CustomerTypeId;

                var result = new BizCustomerSearchResultInfo();

                result.Customers = CustomerService.Instance.GetCustomersByType(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="keyWord"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CustomerList(string keyWord)
        {
            var response = new PostResponse();

            try
            {
                var result = new BizCustomerSearchResultInfo();

                result.Customers = CustomerService.Instance.SearchCustomer(keyWord);
 
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message + " || " + ex.StackTrace;
            }
            return Json(response);
        } 

        #endregion

        #region 客户

       /// <summary>
       /// 
       /// </summary>
       /// <param name="customerId"></param>
       /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CreateUpdate(long? customerId = 0)
        {
            var model = new EditModel();

           if (customerId.HasValue && customerId.Value > 0)
           {
               model.Customer = CustomerService.Instance.GetCustomerById(customerId.Value);
           }
           else
           {
               model.Customer = new BizCustomer();
               model.Customer.CreateUser = LoginHelper.GetUserName();
               model.Customer.LicenseFullPath = FileHelper.HttpCustomerLincenseTemplateFile;
               model.Customer.ContactsList = new List<BizCustomerContacts>();
           }

           return PartialView(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CustomerCreateUpdate(EditModel model)
        {
            var response = new PostResponse();

            try
            {
                bool result = CustomerService.Instance.CreateUpdate(model.Customer);

                if (result)
                {
                    response.Message = "保存成功！";
                    response.Data = model.Customer;
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "保存失败！";
                    response.IsSuccess = false;
                }


            }
            catch (ApplicationException ex)
            {
                response.Message = "保存失败," + ex.Message;
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

        #region 联系人

        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
        public ActionResult ContactsList(int customerId)
        {
            var model = new ContactsListModel();

            model.CustomerId = customerId;

            return PartialView(model);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult GetContactsList(ContactsListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 20;

                model.SearchCondition.CustomerId = model.CustomerId;

                var result = new BizCustomerContactsSearchResultInfo();

                result.ContactsList = ContactsService.Instance.GetCustomerContacts(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message + " || " + ex.StackTrace;
            }
            return Json(response);
        }

        [CheckUserLogin]
        [HttpPost]
        public ActionResult Contacts(ContactsModel model)
        {
            if (model.ContactsId > 0)
            {
                model.Contacts = ContactsService.Instance.GetCustomerContactsById(model.ContactsId);
            }

            return PartialView(model);
        }

        [CheckUserLogin]
        [HttpPost]
        public JsonResult ContactsCreateUpdate(ContactsModel model)
        {
            var response = new PostResponse();

            var contacts = new BizCustomerContacts();

            if (model.Contacts != null)
            {
                model.Contacts.ContactsId = model.ContactsId;
                model.Contacts.CustomerId = model.CustomerId;

                bool result = ContactsService.Instance.CreateUpdate(model.Contacts);

                if (result)
                {
                    response.Message = "上传成功！";
                    response.IsSuccess = true;

                     return Json(response);
                }

            }
 
            response.Message = "上传失败！";
            response.IsSuccess = false;

            return Json(response);
        }

        [CheckUserLogin]
        [HttpPost]
        public JsonResult SetDefatultContacts(long customerId, long contactsId)
        {
            var response = new PostResponse();

            bool result = ContactsService.Instance.SetDefatultContacts(customerId,contactsId);

            if (result)
            {
                response.Message = "设置成功！";
                response.IsSuccess = true;

                return Json(response);
            }

            response.Message = "设置失败！";
            response.IsSuccess = false;

            return Json(response);
        }

        [CheckUserLogin]
        [HttpPost]
        public JsonResult SetActivedContacts(long contactsId)
        {
            var response = new PostResponse();


            bool result = ContactsService.Instance.SetActivedContacts(contactsId);

            if (result)
            {
                response.Message = "设置成功！";
                response.IsSuccess = true;

                return Json(response);
            }

            response.Message = "设置失败！";
            response.IsSuccess = false;

            return Json(response);
        }
        #endregion

        #region 营业执照

        [CheckUserLogin]
        public ActionResult License(LicenseModel model)
        {
            ViewBag.Message = "Modify this template to jump-start your ASP.NET MVC application.";

            return PartialView(model);
        }
     
        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>

        [CheckUserLogin]
        [HttpPost]
        public JsonResult LicenseUpload(LicenseModel model)
        {
            var response = new PostResponse();

            var file = Request.Files[0];
            int fileLen = file.ContentLength;
            //新增的时候没有选择图片

            if (!CheckFileType(file.FileName))
            {
                response.Message = "上传文件类型不正确,上传失败！";
                response.IsSuccess = false;
                return Json(response);
            }

            Stream stream;
            byte[] bytes = new byte[fileLen];
            stream = file.InputStream;
            stream.Read(bytes, 0, fileLen);

            var customer = new BizCustomer();
            customer.CustomerId = model.CustomerId;
            customer.CustomerNo = model.CustomerNo;

            customer.LicenseFileName = customer.CustomerNo + Path.GetExtension(file.FileName);

            bool result = CustomerService.Instance.UploadCustomerLicense(customer, bytes);

            if (result)
            {
                response.Data = Url.Content(FileHelper.HttpCustomerLincenseFiles + "/" + customer.CustomerNo + "/"+ customer.LicenseFileName);
                response.Message = "上传成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "上传失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="fileName"></param>
        /// <returns></returns>
        private bool CheckFileType(string fileName)
        {
            //FileName为空时不验证 图片格式 修改图片适用
            if (string.IsNullOrEmpty(fileName))
                return true;

            int start = fileName.LastIndexOf(".");
            string type = fileName.Substring(start, fileName.Length - start);
            if (type.ToLower() == ".jpg" || type.ToLower() == ".png" || type.ToLower() == ".gif")
                return true;

            return false;
        }

        #endregion
    }
}
