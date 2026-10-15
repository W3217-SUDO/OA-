using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Web.Mvc;

using Dchien.Legal.BizModel.Lawsuit.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.Lawsuit.Case;
using Dchien.Legal.Service.Lawsuit.Case;
using Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;

namespace Dchien.Legal.Web.Areas.Lawsuit.Controllers
{
    [CheckUserLogin]
    public class CaseFeeController : BaseController
    {
        internal Log Logger = new Log("Lawsuit.Controllers.CaseFeeController");


        /// <summary>
        ///  案件费用列表
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseFeeList(long caseId, int? pageNo, int? pageSize)
        {
            var caseModel = new CaseFeeListModel();
            caseModel.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            caseModel.PageSize = pageSize.HasValue ? pageSize.Value : 10;
            if (caseId > 0)
            {
                caseModel.CaseFees = CaseFeeService.Instance.GetCaseFeeItems(caseId);
                caseModel.TotalCount = caseModel.CaseFees.Count;
                caseModel.CaseFees = caseModel.CaseFees.Any()
                    ? caseModel.CaseFees.Skip(caseModel.PageSize * (caseModel.PageNo - 1))
                        .Take(caseModel.PageSize)
                        .ToList()
                    : new List<BizCaseFeeItem>();
            }
            return PartialView("CaseFeeList", caseModel);
        }

        #region 案件费用通知

        /// <summary>
        /// 打开案件费用通知
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseFeeInform(CaseFeeModel model)
        {
            var caseModel = new CaseFeeModel();

            if (model == null)
            {
                throw new ArgumentNullException("model");
            }
            caseModel.CaseTypeId = model.CaseTypeId;

            var caseFeeTypes = CaseTypeService.Instance.GetAllCaseFeeTypes();

            caseModel.CaseFeeTypeList = caseFeeTypes;
            caseModel.CaseFee = new BizCaseFee();

            if (model.CaseFileTypeId.HasValue)
            {
                caseModel.CaseFee.CaseFeeItems =
                    CaseFeeService.Instance.GetCaseFeeItemsByCaseFileTypeId((CaseFileType)model.CaseFileTypeId);
            }
            else
            {
                var caseFeeItem = new BizCaseFeeItem();

                caseFeeItem.IsDefalut = true;
                caseFeeItem.IsFeeMitigation = false;
                caseFeeItem.Amount = 0;
                caseFeeItem.InformDate = DateTime.Now;
                caseModel.CaseFee.CaseFeeItems = new List<BizCaseFeeItem>();
                caseModel.CaseFee.CaseFeeItems.Add(caseFeeItem);
            }

            caseModel.DefaultCaseFee = caseModel.CaseFee.CaseFeeItems.FirstOrDefault(x => x.IsDefalut);

            return PartialView("CaseFeeInform", caseModel);
        }

        /// <summary>
        /// 保存案件费用通知
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFeeInformCreate(CaseFeeModel model)
        {
            var response = new PostResponse();

            try
            {
                bool result = CaseFeeService.Instance.CreateCaseFee(model.CaseFee);

                if (result)
                {
                    response.Message = "保存成功！";
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
                response.Message = ex.Message;
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

        #region 案件费用确认

        /// <summary>
        ///  案件费用 财务确认
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseFeeConfirm(CaseFeeModel model)
        {
            if (model == null)
            {
                throw new ArgumentNullException("model");
            }

            if (model.CaseFeeId == 0)
            {
                throw new ArgumentNullException("model");
            }

            var caseFeeTypes = CaseTypeService.Instance.GetAllCaseFeeTypes();

            model.CaseFeeTypeList = caseFeeTypes;
            model.DefaultCaseFee = CaseFeeService.Instance.GetCaseFeeItem(model.CaseFeeId);

            if (!model.DefaultCaseFee.GainedDate.HasValue)
            {
                model.DefaultCaseFee.GainedDate = DateTime.Now.Date;
            }
            model.DefaultCaseFee.ActualAmount = model.DefaultCaseFee.ActualAmount.HasValue
                ? model.DefaultCaseFee.ActualAmount
                : model.DefaultCaseFee.Amount;

            return PartialView("CaseFeeConfirm", model);
        }

        /// <summary>
        /// 案件费用 财务确认
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFeeConfirmCreate(CaseFeeModel model)
        {
            var response = new PostResponse();

            var caseFee = new BizCaseFeeItem();

            caseFee.FeeItemId = model.DefaultCaseFee.FeeItemId;
            caseFee.FeeTypeId = model.DefaultCaseFee.FeeTypeId;
            caseFee.CaseId = model.CaseId;
            caseFee.CaseNo = model.CaseNo;
            caseFee.ActualAmount = model.DefaultCaseFee.ActualAmount;
            caseFee.GainedDate = model.DefaultCaseFee.GainedDate;

            bool result = CaseFeeService.Instance.CaseFeeConfrim(caseFee);

            if (result)
            {
                response.Message = "保存成功！";
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

        #region 案件票据确认

        /// <summary>
        /// 打开案件票据确认
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseFeeBillConfirm(CaseFeeModel model)
        {
            if (model == null)
            {
                throw new ArgumentNullException("model");
            }

            if (model.CaseFeeId == 0)
            {
                throw new ArgumentNullException("model");
            }

            //var caseFeeTypes = CaseTypeService.Instance.GetAllCaseFeeTypes();

            model.DefaultCaseFee = CaseFeeService.Instance.GetCaseFeeItem(model.CaseFeeId);

            if (!model.DefaultCaseFee.BillDate.HasValue)
            {
                model.DefaultCaseFee.BillDate = DateTime.Now.Date;
            }

            model.DefaultCaseFee.BillAmount = model.DefaultCaseFee.BillAmount.HasValue
                ? model.DefaultCaseFee.BillAmount
                : model.DefaultCaseFee.Amount;

            return PartialView("CaseFeeBillConfirm", model);
        }

        /// <summary>
        /// 保存案件票据确认
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFeeBillConfirmCreate(CaseFeeModel model)
        {
            var response = this.CheckCaseFileUploading();

            if (response != null)
            {
                return Json(response);
            }

            response = new PostResponse();

            var file = Request.Files[0];
            int fileSize = file.ContentLength;
            var bytes = new byte[fileSize];
            using (var stream = file.InputStream)
            {
                stream.Read(bytes, 0, fileSize);
            }

            var caseFee = new BizCaseFeeItem();
            caseFee.CaseId = model.CaseId;
            caseFee.CaseNo = model.CaseNo;
            caseFee.FeeId = model.CaseFeeId;
            caseFee.FeeItemId = model.DefaultCaseFee.FeeItemId;
            caseFee.FeeTypeId = model.DefaultCaseFee.FeeTypeId;

            caseFee.BillNo = model.DefaultCaseFee.BillNo;
            caseFee.BillDate = model.DefaultCaseFee.BillDate;
            caseFee.BillAmount = model.DefaultCaseFee.BillAmount;
            caseFee.BillFileName = file.FileName;
            caseFee.BillFileSize = fileSize;

            var c = CaseService.Instance.GetCaseBasic(model.CaseId);

            bool result = CaseService.Instance.Process(c, caseFee, bytes);

            if (result)
            {
                response.Message = "保存成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "保存失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        private PostResponse CheckCaseFileUploading()
        {
            var response = new PostResponse();

            if (Request.Files == null || Request.Files.Count == 0)
            {
                response.Message = "请选择文件进行上传.";
                response.IsSuccess = false;
                return response;
            }

            var file = Request.Files[0];

            if (file == null)
            {
                response.Message = "请选择文件进行上传.";
                response.IsSuccess = false;
                return response;
            }

            if (file.ContentLength == 0)
            {
                response.Message = "文件没有任何内容.";
                response.IsSuccess = false;
                return response;
            }

            if (!CheckFileType(file.FileName))
            {
                response.Message = "上传文件类型不正确,上传失败！";
                response.IsSuccess = false;
                return response;
            }

            return null;

        }
        private bool CheckFileType(string fileName)
        {
            //FileName为空时不验证 图片格式 修改图片适用
            if (string.IsNullOrEmpty(fileName))
                return true;

            var start = fileName.LastIndexOf(".");
            string type = fileName.Substring(start, fileName.Length - start);
            //if (type.ToLower() == ".jpg" || type.ToLower() == ".png" || type.ToLower() == ".gif")
            //    return true;

            //return false;

            return true;
        }

        #endregion

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFeeId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFeeUnlock(long caseFeeId)
        {
            var response = new PostResponse();

            bool result = CaseFeeService.Instance.CaseFeeUnlock(caseFeeId);

            if (result)
            {
                response.Message = "解锁成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "解锁失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFeeId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFeeDelete(long caseFeeId)
        {
            var response = new PostResponse();

            try
            {
                bool result = CaseFeeService.Instance.CaseFeeDelete(caseFeeId);

                if (result)
                {
                    response.Message = "删除成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "删除失败！";
                    response.IsSuccess = false;
                }

            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"CaseFeeController.CaseFeeDelete","CaseFeeController.CaseFeeDelete", ex);
                throw;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFeeItemIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFeeLinked(List<long> caseFeeItemIds)
        {
            var response = new PostResponse();

            try
            {

                bool result = CaseFeeService.Instance.CaseFeeLinked(caseFeeItemIds);

                if (result)
                {
                    response.Message = "关联成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "关联失败！";
                    response.IsSuccess = false;
                }

            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFeeController.CaseFeeLinked", "CaseFeeController.CaseFeeLinked", ex);
            }

            return Json(response);
        }
    }
}
