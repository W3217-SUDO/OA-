using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.CRM.Customer;
using Dchien.Legal.Web.Areas.CRM.ViewModels.Customer;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using log4net.Repository.Hierarchy;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.CRM.Controllers
{
    [CheckUserLogin]
    public class CustomerContactsController : Controller
    {
        internal Log Logger = new Log("CRM.Controllers.CustomerContactsController ");

        [CheckUserLogin]
        [HttpPost]
        public ActionResult ContactsList(bool? isView,long? customerId, int? pageNo, int? pageSize)
        {
            var model = new ContactsListModel();

            model.IsView = isView;
            model.SearchCondition = new ContactsSearchCondition();
            model.SearchCondition.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            model.SearchCondition.PageSize = pageSize.HasValue ? pageSize.Value : 15;

            if (customerId.HasValue && customerId > 0)
            {
                model.CustomerContactsList = ContactsService.Instance.GetCustomerContacts(customerId.Value);
                model.SearchCondition.TotalCount = model.CustomerContactsList.Count;
                model.CustomerContactsList = model.CustomerContactsList.Any()
                    ? model.CustomerContactsList.Skip(model.SearchCondition.PageSize * (model.SearchCondition.PageNo - 1))
                        .Take(model.SearchCondition.PageSize)
                        .OrderByDescending(x => x.ContactsId)
                        .ToList()
                    : new List<BizCustomerContacts>();
            }

            return PartialView("ContactsList", model);
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
                    model.SearchCondition.PageSize = 15;

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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CustomerController.GetContactsList", "CustomerController.GetContactsList", ex);

                response.IsSuccess = false;
                response.Message = "查询联系人失败.";
            }
            return Json(response);
        }

        [CheckUserLogin]
        [HttpPost]
        public ActionResult CreateUpdate(ContactsModel model)
        {
            if (model.ContactsId > 0)
            {
                model.Contacts = ContactsService.Instance.GetCustomerContactsById(model.ContactsId);
            }
            else
            {
                model.Contacts = new BizCustomerContacts();
                model.Contacts.CustomerId = model.CustomerId;
                model.Contacts.CustomerNo = model.CustomerNo; 
                model.Contacts.ContactsGuid = Guid.NewGuid().ToString();
                model.Contacts.PhotoFileFullPath = FileHelper.HttpCustomerContactsPhotoTemplateFile;
                model.Contacts.IsActived = true;
                model.Contacts.IsContacted = true;
                model.Contacts.IsPeopleBASE = true;
                model.Contacts.IsReceivedEmail = true;
            }

            return PartialView(model);
        }


        [CheckUserLogin]
        [HttpPost]
        public ActionResult View(ContactsModel model)
        {
            if (model.ContactsId > 0)
            {
                model.Contacts = ContactsService.Instance.GetCustomerContactsById(model.ContactsId);
            }
            else
            {
                model.Contacts = new BizCustomerContacts();
                model.Contacts.CustomerId = model.CustomerId;
                model.Contacts.CustomerNo = model.CustomerNo;
                model.Contacts.ContactsGuid = Guid.NewGuid().ToString();
                model.Contacts.PhotoFileFullPath = FileHelper.HttpCustomerContactsPhotoTemplateFile;
                model.Contacts.IsActived = true;
                model.Contacts.IsContacted = true;
                model.Contacts.IsPeopleBASE = true;
                model.Contacts.IsReceivedEmail = true;
            }

            return PartialView(model);
        }

        [CheckUserLogin]
        [HttpPost]
        public JsonResult ContactsCreateUpdate(ContactsModel model)
        {
            var response = new PostResponse();

            if (model.Contacts != null)
            {
                bool result = ContactsService.Instance.CreateUpdate(model.Contacts);

                if (result)
                {
                    response.Message = "保存成功！";
                    response.IsSuccess = true;
                    response.Data = model.Contacts;
                    return Json(response);
                }

            }

            response.Message = "保存失败！";
            response.IsSuccess = false;

            return Json(response);
        }

        [CheckUserLogin]
        [HttpPost]
        public JsonResult SetDefatultContacts(long customerId, long contactsId)
        {
            var response = new PostResponse();

            bool result = ContactsService.Instance.SetDefatultContacts(customerId, contactsId);

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

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ContactsPhoto(ContactsPhotoModel model)
        {
            return PartialView(model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>

        [CheckUserLogin]
        [HttpPost]
        public JsonResult ContactsPhotoUpload(ContactsPhotoModel model)
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

            var contacts = new BizCustomerContacts();
            contacts.CustomerNo = model.CustomerNo;
            contacts.ContactsGuid = model.ContactsGuid;

            contacts.PhotoFileName = contacts.ContactsGuid + Path.GetExtension(file.FileName);

            bool result = ContactsService.Instance.UploadContactsPhoto(contacts, bytes);

            if (result)
            {
                contacts.PhotoFileFullPath = Url.Content(FileHelper.HttpCustomerContactsPhotoFiles + "/" + contacts.CustomerNo + "/" + contacts.PhotoFileName);
                response.Data = contacts; 
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
 
    }
}
