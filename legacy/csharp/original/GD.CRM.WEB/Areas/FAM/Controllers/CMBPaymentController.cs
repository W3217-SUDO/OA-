using System;
using System.Web.Mvc;
using System.IO;
using System.Collections.Generic;

using Dchien.Legal.BizModel.FAM.AR.CMB;
using Dchien.Legal.Common;
using Dchien.Legal.Service.FAM.AR.CMB;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Entity.System;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class CMBPaymentController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.CMBPaymentController");
         
        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult PaymentList(Dchien.Legal.Web.Areas.FAM.ViewModels.AR.CMB.CMBListModel model)
        {
            var response = new PostResponse();
            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;
                var result = new BizPaymentSearchResultInfo();
                result.PaymentList = PaymentService.Instance.GetPaymentList(model.SearchCondition);
                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CMBPaymentController.PaymentList", "CMBPaymentController.PaymentList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }
 

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult PaymentDelete(List<long> paymentIds)
        {
            var response = new PostResponse();
            try
            {
                PaymentService.Instance.Delete(paymentIds);
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ARController.PaymentDelete", "ARController.PaymentDelete", ex);
                response.IsSuccess = false;
                response.Message = "删除出错.";
            }
            return Json(response);
        }


        [HttpPost]
        [CheckUserLogin]
        public JsonResult PaymentIn(List<long> paymentIds)
        {
            var response = new PostResponse();
            try
            {
                PaymentService.Instance.PaymentIn(paymentIds);
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ARController.PaymentIn", "ARController.PaymentIn", ex);
                response.IsSuccess = false;
                response.Message = "删除出错.";
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CMBFileUploading()
        {
            var response = new PostResponse();
            var file = Request.Files[0];
            if (file == null)
            {
                response.Message = "请选择文件进行上传.";
                response.IsSuccess = false;
                return Json(response);
            }
            if (file.FileName.IndexOf(".xlsx") <= 0 && file.FileName.IndexOf(".xls") <= 0)
            {
                response.Message = "请上传Excel格式文件.";
                response.IsSuccess = false;
                return Json(response);
            }
            int fileLen = file.ContentLength;
            Stream stream;
            byte[] bytes = new byte[fileLen];
            stream = file.InputStream;
            stream.Read(bytes, 0, fileLen);
            try
            {
                var guid = Guid.NewGuid();
                var payments = Dchien.Legal.Service.FAM.AR.CMB.PaymentService.Instance.Process(bytes, guid, file.FileName);
                var groupId = this.Request.Path.Contains(PageId.PageId_5001001014) ? Entity.BAS.Type.GroupId.Lawfirm : Entity.BAS.Type.GroupId.Trad;
                Dchien.Legal.Service.FAM.AR.CMB.PaymentService.Instance.Create(payments, groupId);
                response.Data = guid;
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CMBFileUploading", "CMBFileUploading", ex);
                response.Message = "上传失败！";
                response.IsSuccess = false;
            }
            return new JsonResult()
            {
                Data = response,
                MaxJsonLength = int.MaxValue,
                ContentType = "application/json"
            };
        }
    }
}
