using System;
using System.Collections.Generic;
using System.Web.Mvc;
using Dchien.Legal.BizModel.FAM.AP.Payment.Packing;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FAM.AP.Payment.Packing;
using Dchien.Legal.Service;
using Dchien.Legal.Service.FAM.AP.Payment;
using Dchien.Legal.Web.Areas.FAM.ViewModels.AP.Payment.Packing;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using System.Linq;
using Dchien.Legal.Entity.BAS.Type;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class PaymentPackingController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.PaymentPackingController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult PendingList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizPaymentPackingSearchResultInfo();

                model.SearchCondition.PackingStatus = PaymentPackingStatus.Pending;
                result.PaymentPackingList = PaymentPackingService.Instance.GetPaymentPackingList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"PaymentPackingController.PendingList","PaymentPackingController.PendingList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        public JsonResult PackingList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizPaymentPackingSearchResultInfo();

                if (model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003006)
                {
                    model.SearchCondition.PackingStatus = PaymentPackingStatus.Packing;
                }

                if (model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003001
                || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003002
                || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003003
                || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003004
                || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003005
                || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003006)
                {
                    model.SearchCondition.GroupId = (int)GroupId.Lawfirm;
                }
                if (model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003001
                    || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003002
                    || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003003
                    || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003004
                    || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003005
                    || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003006
                    )
                {
                    model.SearchCondition.GroupId = (int)GroupId.Trad;
                }

                result.PaymentPackingList = PaymentPackingService.Instance.GetPaymentPackingList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"PaymentPackingController.PackingList","PaymentPackingController.PackingList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="packingId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult Packing(long packingId)
        {
            var response = new PostResponse();

            try
            {
                var result = PaymentPackingService.Instance.Packing(packingId);

                if (result)
                {
                    response.Message = "打包成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "打包失败！";
                    response.IsSuccess = false;
                }
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"PaymentPackingController.Packing","PaymentPackingController.Packing", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult PackingOnNo(string packingNo)
        {
            var response = new PostResponse();

            try
            {
                var result = true;
                packingNo.Split(',').ToList().ForEach(x =>
                {
                    result = PaymentPackingService.Instance.Packing(x);
                });
                if (result)
                {
                    response.Message = "打包成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "打包失败！";
                    response.IsSuccess = false;
                }
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PaymentPackingController.PackingOnNo", "PaymentPackingController.PackingOnNo", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="packing"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult Validate(PackingListModel packingListModel)
        {
            var response = new PostResponse();

            try
            {
                var files = new List<KeyValuePair<string, byte[]>>();
                for (int i = 0; i < Request.Files.Count; i++)
                {
                    var file = Request.Files[i];
                    int fileSize = file.ContentLength;
                    var bytes = new byte[fileSize];
                    using (var stream = file.InputStream)
                    {
                        stream.Read(bytes, 0, fileSize);
                    }

                    files.Add(new KeyValuePair<string, byte[]>(file.FileName, bytes));
                }

                packingListModel.PackingNo.Split(',').ToList().ForEach(x =>
                {
                    var paymentPacking = PaymentPackingService.Instance.GetPaymentPacking(x);
                    paymentPacking.PaymentPackingBasic.PaidDate = packingListModel.PaidDate;
                    paymentPacking.PaymentPackingBasic.PaymentMode = packingListModel.PaymentMode;
                    paymentPacking.PaymentPackingBasic.InvoiceNo = packingListModel.InvoiceNo;
                    paymentPacking.PaymentPackingBasic.Remark = packingListModel.Remark;
                    paymentPacking.PaymentPackingBasic.PackingStatus = PaymentPackingStatus.Paid;

                    PaymentPackingService.Instance.Validate(paymentPacking, files);
                });

                response.Message = "核销成功！";
                response.IsSuccess = true;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PaymentPackingController.Validate", "PaymentPackingController.Validate", ex);
            }
            return Json(response);
        } 

    }
}
