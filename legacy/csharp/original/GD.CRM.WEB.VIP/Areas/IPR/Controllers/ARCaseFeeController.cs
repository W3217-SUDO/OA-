using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Areas.IPR.ViewModels.Case.AR;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.IPR.Controllers
{
    [CheckUserLogin]
    public class ARCaseFeeController : BaseController
    {
        internal Log Logger = new Log("IPR.Controllers.ARCaseFeeController");


        /////// <summary>
        /////// 打开案件费用通知
        /////// </summary>
        /////// <param name="model"></param>
        /////// <returns></returns>
        ////[HttpPost]
        ////public ActionResult CaseFeeInform(CaseFeeModel model)
        ////{
        ////    var caseModel = new CaseFeeModel();

        ////    if (model == null)
        ////    {
        ////        throw new ArgumentNullException("model");
        ////    }

        ////    var c = CaseService.Instance.GetCase(model.CaseId);

        ////    caseModel.CaseTypeId = model.CaseTypeId;
        ////    caseModel.CaseRequestDate = c.CaseBasicInfo.CaseRequestDate;

        ////    var caseType = CaseTypeService.Instance.GetCaseType(model.CaseTypeId);

        ////    if (null == caseType)
        ////    {
        ////        throw new ApplicationException(string.Format("未找到案件类型，caseId:{0},caseTypeId:{1}", model.CaseId,
        ////            model.CaseTypeId));
        ////    }

        ////    caseModel.CaseFeeTypeList = caseType.CaseFeeTypeList;
        ////    caseModel.CaseFeeList = new List<Dchien.Legal.BizModel.FAM.AR.CaseFee.BizCaseFee>();

        ////    if (model.CaseFileTypeId.HasValue)
        ////    {
        ////        caseModel.CaseFeeList =
        ////            Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.GetCaseFeesByCaseFileTypeId((CaseFileType)model.CaseFileTypeId);
        ////    }
        ////    else
        ////    {
        ////        var caseFee = new BizCaseFee();
        ////        caseFee.Amount = 0;
        ////        caseFee.InformDate = DateTime.Now;
        ////        caseModel.CaseFeeList.Add(caseFee);
        ////    }

        ////    caseModel.DefaultCaseFee = caseModel.CaseFeeList.FirstOrDefault();

        ////    return PartialView("CaseFeeInform", caseModel);
        ////}

        ///// <summary>
        ///// 保存案件费用通知
        ///// </summary>
        ///// <param name="model"></param>
        ///// <returns></returns>
        //[HttpPost]
        //public JsonResult CaseFeeInformCreate(CaseFeeModel model)
        //{
        //    var response = new PostResponse();

        //    try
        //    {
        //        bool result = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.CreateCaseFee(model.CaseFeeList);

        //        if (result)
        //        {
        //            response.Message = "保存成功！";
        //            response.IsSuccess = true;
        //        }
        //        else
        //        {
        //            response.Message = "保存失败！";
        //            response.IsSuccess = false;
        //        }
        //    }
        //    catch (ApplicationException ex)
        //    {
        //        response.Message = ex.Message;
        //        response.IsSuccess = false;
        //    }

        //    return Json(response);
        //}

        ///// <summary>
        ///// 
        ///// </summary>
        ///// <param name="caseFeeId"></param>
        ///// <returns></returns>
        //[HttpPost]
        //public JsonResult CaseFeeConfirmClear(long caseFeeId)
        //{
        //    var response = new PostResponse();

        //    try
        //    {
        //        bool result = false;//CaseFeeService.Instance.CaseFeeConfirmClear(caseFeeId);

        //        if (result)
        //        {
        //            response.Message = "保存成功！";
        //            response.IsSuccess = true;
        //        }
        //        else
        //        {
        //            response.Message = "保存失败！";
        //            response.IsSuccess = false;
        //        }
        //    }
        //    catch (ApplicationException ex)
        //    {
        //        response.Message = ex.Message;
        //        response.IsSuccess = false;
        //    }

        //    return Json(response);
        //}

        ///// <summary>
        ///// 案件费用首年年费
        ///// </summary>
        ///// <param name="caseId"></param>
        ///// <param name="caseFeeId"></param>
        ///// <returns></returns>
        //[HttpPost]
        //public JsonResult LabelFirstYear(long caseId, long caseFeeId)
        //{
        //    var response = new PostResponse();

        //    try
        //    {
        //        bool result = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.CaseFeeLabelFirstYear(caseId,
        //            caseFeeId);

        //        if (result)
        //        {
        //            response.Message = "设定成功！";
        //            response.IsSuccess = true;
        //        }
        //        else
        //        {
        //            response.Message = "设定失败！";
        //            response.IsSuccess = false;
        //        }
        //    }
        //    catch (ApplicationException ex)
        //    {
        //        response.Message = ex.Message;
        //        response.IsSuccess = false;
        //    }

        //    return Json(response);
        //}

        ///// <summary>
        ///// 
        ///// </summary>
        ///// <param name="model"></param>
        ///// <returns></returns>
        //[HttpPost]
        //public ActionResult CaseFeeInformAnnualYear(CaseFeeModel model)
        //{
        //    var c = CaseService.Instance.GetCase(model.CaseId);

        //    model.CaseRequestDate = c.CaseBasicInfo.CaseRequestDate;

        //    return PartialView("CaseFeeInformAnnualYear", model);
        //}

        ///// <summary>
        ///// 
        ///// </summary>
        ///// <param name="model"></param>
        ///// <returns></returns>
        //[HttpPost]
        //public ActionResult LabelAnnualYear(CaseFeeModel model)
        //{
        //    var response = new PostResponse();

        //    var caseFee = new BizCaseFee();
        //    caseFee.CaseFeeId = model.CaseFeeId;
        //    caseFee.AnnualYear = model.Yearly;
        //    caseFee.AnnualEnd = model.AnnualFrom;
        //    caseFee.AnnualEnd = model.AnnualEnd;

        //    bool result = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.CaseFeeLableAnnualYear(caseFee);

        //    if (result)
        //    {
        //        response.Message = "设定成功！";
        //        response.IsSuccess = true;
        //    }
        //    else
        //    {
        //        response.Message = "设定失败！";
        //        response.IsSuccess = false;
        //    }

        //    return Json(response);
        //}


        ///// <summary>
        ///// 
        ///// </summary>
        ///// <param name="caseFeeId"></param>
        ///// <returns></returns>
        //[HttpPost]
        //public JsonResult CaseFeeUnlock(long caseFeeId)
        //{
        //    var response = new PostResponse();

        //    bool result = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.CaseFeeUnlock(caseFeeId);

        //    if (result)
        //    {
        //        response.Message = "解锁成功！";
        //        response.IsSuccess = true;
        //    }
        //    else
        //    {
        //        response.Message = "解锁失败！";
        //        response.IsSuccess = false;
        //    }

        //    return Json(response);
        //}



        ///// <summary>
        ///// 
        ///// </summary>
        ///// <param name="caseFeeId"></param>
        ///// <returns></returns>
        //[HttpPost]
        //public JsonResult CaseFeeDelete(long caseFeeId)
        //{
        //    var response = new PostResponse();

        //    try
        //    {
        //        bool result = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.CaseFeeDelete(caseFeeId);

        //        if (result)
        //        {
        //            response.Message = "删除成功！";
        //            response.IsSuccess = true;
        //        }
        //        else
        //        {
        //            response.Message = "删除失败！";
        //            response.IsSuccess = false;
        //        }

        //    }
        //    catch (ApplicationException ex)
        //    {
        //        response.Message = ex.Message;
        //        response.IsSuccess = false;
        //    }
        //    catch (Exception ex)
        //    {
        //        Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseController.CaseFeeDelete", "CaseController.CaseFeeDelete", ex);
        //        throw;
        //    }

        //    return Json(response);
        //}

        ///// <summary>
        ///// 
        ///// </summary>
        ///// <returns></returns>
        //private PostResponse CheckCaseFileUploading()
        //{
        //    var response = new PostResponse();

        //    if (Request.Files == null || Request.Files.Count == 0)
        //    {
        //        response.Message = "请选择文件进行上传.";
        //        response.IsSuccess = false;
        //        return response;
        //    }

        //    var file = Request.Files[0];

        //    if (file == null)
        //    {
        //        response.Message = "请选择文件进行上传.";
        //        response.IsSuccess = false;
        //        return response;
        //    }

        //    if (file.ContentLength == 0)
        //    {
        //        response.Message = "文件没有任何内容.";
        //        response.IsSuccess = false;
        //        return response;
        //    }

        //    if (!CheckFileType(file.FileName))
        //    {
        //        response.Message = "上传文件类型不正确,上传失败！";
        //        response.IsSuccess = false;
        //        return response;
        //    }

        //    return null;

        //}

        ///// <summary>
        ///// 
        ///// </summary>
        ///// <param name="fileName"></param>
        ///// <returns></returns>
        //private bool CheckFileType(string fileName)
        //{
        //    //FileName为空时不验证 图片格式 修改图片适用
        //    if (string.IsNullOrEmpty(fileName))
        //        return true;

        //    var start = fileName.LastIndexOf(".");
        //    string type = fileName.Substring(start, fileName.Length - start);
        //    //if (type.ToLower() == ".jpg" || type.ToLower() == ".png" || type.ToLower() == ".gif")
        //    //    return true;

        //    //return false;

        //    return true;
        //}

        ///// <summary>
        ///// 
        ///// </summary>
        ///// <param name="caseFeeId"></param>
        ///// <returns></returns>
        //[HttpPost]
        //public JsonResult CaseFeeInvoiceConfirmClear(long caseFeeId)
        //{
        //    var response = new PostResponse();

        //    try
        //    {
        //        bool result = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.CaseFeeInvoiceConfirmClear(caseFeeId);

        //        if (result)
        //        {
        //            response.Message = "保存成功！";
        //            response.IsSuccess = true;
        //        }
        //        else
        //        {
        //            response.Message = "保存失败！";
        //            response.IsSuccess = false;
        //        }
        //    }
        //    catch (ApplicationException ex)
        //    {
        //        response.Message = ex.Message;
        //        response.IsSuccess = false;
        //    }

        //    return Json(response);
        //}

        //#region 案件费用客户自缴

        //[HttpPost]
        //public JsonResult CaseFeePaymentByCustomer(long caseFeeId)
        //{
        //    var response = new PostResponse();

        //    try
        //    {
        //        bool result = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.CaseFeePaymentByCustomer(caseFeeId);

        //        if (result)
        //        {
        //            response.Message = "设定成功！";
        //            response.IsSuccess = true;
        //        }
        //        else
        //        {
        //            response.Message = "设定失败！";
        //            response.IsSuccess = false;
        //        }
        //    }
        //    catch (ApplicationException ex)
        //    {
        //        response.Message = ex.Message;
        //        response.IsSuccess = false;
        //    }

        //    return Json(response);
        //}

        //#endregion


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
            caseModel.PageSize = pageSize.HasValue ? pageSize.Value : 15;
            if (caseId > 0)
            {
                caseModel.CaseId = caseId;
                caseModel.CaseFeeList =
                    Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.GetCaseFeeListByCaseId(caseId);
                caseModel.TotalCount = caseModel.CaseFeeList.Count;
                caseModel.CaseFeeList = caseModel.CaseFeeList.Any()
                    ? caseModel.CaseFeeList.Skip(caseModel.PageSize * (caseModel.PageNo - 1))
                        .Take(caseModel.PageSize)
                        .ToList()
                    : new List<Dchien.Legal.BizModel.FAM.AR.CaseFee.BizCaseFee>();
            }
            return PartialView("CaseFeeList", caseModel);
        }

        /// <summary>
        /// 打开案件费用通知
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult Create(Dchien.Legal.Web.Areas.IPR.ViewModels.Case.AR.CaseFeeModel model)
        {
            var caseModel = new Dchien.Legal.Web.Areas.IPR.ViewModels.Case.AR.CaseFeeModel();

            if (model == null)
            {
                throw new ArgumentNullException("model");
            }
            return PartialView("Create", caseModel);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="seqno"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult Edit(string seqno)
        {
            var caseModel = new Dchien.Legal.Web.Areas.IPR.ViewModels.Case.AR.CaseFeeModel();

            caseModel.ContractObject = Dchien.Legal.Service.FCM.Contract.ContractService.Instance.GetContractObjectByBatchNo(seqno);

            if (caseModel.ContractObject == null)
            {
                throw new KeyNotFoundException(seqno);
            }
            return PartialView("Edit", caseModel);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFeeId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult RemoveFeeHedgingFile(List<long> caseFeeIds)
        {
            var response = new PostResponse();

            bool result = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.RemoveFeeHedgingFile(caseFeeIds);

            if (result)
            {
                response.Message = "解除待转票成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "解除待转票失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }
    }
}
