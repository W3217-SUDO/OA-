using System;
using System.Collections.Generic;
using System.IO;
using System.Web.Mvc;

using Dchien.Legal.BizModel.CRM.LawFirm;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Areas.CRM.ViewModels.LawFirm;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.LawFirm;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.CRM.Controllers
{
    public class LawFirmController : Controller
    {
        #region 律所列表

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult Index(int? id)
        {
            var model = new IndexModel();

            var lst = new List<BizLawFirmType>();  //LawFirmTypeService.Instance.GetLawFirmType();

            model.LawFirmTypeId = id.HasValue ? id.Value : 1;
            model.CaseLawFirmTypeList = lst;

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
                    model.SearchCondition.PageSize = 15;

                model.SearchCondition.LawFirmTypeId = model.LawFirmTypeId;

                var result = new BizLawFirmSearchResultInfo();

                result.LawFirms = LawFirmService.Instance.GetLawFirmsByType(model.SearchCondition);

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

        #endregion

        #region 律所

        /// <summary>
        /// 
        /// </summary>
        /// <param name="lawFirmId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CreateUpdate(long? lawFirmId = 0)
        {
            var model = new EditModel();

            if (lawFirmId.HasValue && lawFirmId.Value > 0)
            {
                model.LawFirm = LawFirmService.Instance.GetLawFirmById(lawFirmId.Value);
            }
            else
            {
                model.LawFirm = new BizLawFirm();
                model.LawFirm.LicenseFullPath = FileHelper.HttpLawFirmLincenseTemplateFile;

                model.LawFirm.ContactsList = new List<BizLawFirmContacts>();
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
        public JsonResult LawFirmCreateUpdate(EditModel model)
        {
            var response = new PostResponse();

            bool result = LawFirmService.Instance.CreateUpdate(model.LawFirm);

            if (result)
            {
                response.Message = "保存成功！";
                response.Data = model.LawFirm;
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "保存失败！";
                response.IsSuccess = false;
            }

            return Json(response);

        }

        #endregion

        #region 联系人

        /// <summary>
        /// 
        /// </summary>
        /// <param name="LawFirmId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult ContactsList(int LawFirmId)
        {
            var model = new ContactsListModel();

            model.LawFirmId = LawFirmId;

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
                    model.SearchCondition.PageSize = 15;

                model.SearchCondition.LawFirmId = model.LawFirmId;

                var result = new BizLawFirmContactsSearchResultInfo();

                result.ContactsList = ContactsService.Instance.GetLawFirmContacts(model.SearchCondition);

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

        [HttpPost]
        [CheckUserLogin]
        public ActionResult Contacts(ContactsModel model)
        {
            if (model.ContactsId > 0)
            {
                model.Contacts = ContactsService.Instance.GetLawFirmContactsById(model.ContactsId);
            }

            return PartialView(model);
        }
        [CheckUserLogin]
        [HttpPost]
        public JsonResult ContactsCreateUpdate(ContactsModel model)
        {
            var response = new PostResponse();

            var contacts = new BizLawFirmContacts();

            if (model.Contacts != null)
            {
                model.Contacts.ContactsId = model.ContactsId;
                model.Contacts.LawFirmId = model.LawFirmId;

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
        public JsonResult SetDefatultContacts(long LawFirmId, long contactsId)
        {
            var response = new PostResponse();

            bool result = ContactsService.Instance.SetDefatultContacts(LawFirmId, contactsId);

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

            var lawFirm = new BizLawFirm();
            lawFirm.LawFirmId = model.LawFirmId;
            lawFirm.LawFirmNo = model.LawFirmNo;
            lawFirm.LicenseFileName = lawFirm.LawFirmNo + Path.GetExtension(file.FileName);

            bool result = LawFirmService.Instance.UploadLawFirmLicense(lawFirm, bytes);

            if (result)
            {
                response.Data = Url.Content(FileHelper.HttpLawFirmLincenseFiles + "/" + lawFirm.LawFirmNo + "/" + lawFirm.LicenseFileName);
                response.Message = "上传成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "上传失败！";
                response.IsSuccess = false;
            }

            return Json(response);
            //}
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
