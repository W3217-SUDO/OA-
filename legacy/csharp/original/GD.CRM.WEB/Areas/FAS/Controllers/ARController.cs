using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography.X509Certificates;
using System.Web.Mvc;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.BizModel.FAM.AR;
using Dchien.Legal.BizModel.FAM.AR.CaseFee;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FCM.Contract;
using Dchien.Legal.Entity.FAM.AR;
using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Service.FAM.AR;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Web.Areas.FAM.ViewModels.AR;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using CaseFeeService = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class ARController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.ARController");

        #region 新增应收账款

        [CheckUserLogin]
        public ActionResult Create(string contractNo)
        {
            var createModel = new CreateModel();
            createModel.Ar = new BizAR();
            createModel.ArObjects = new List<BizArObject>();
            return View(createModel);
        }
        
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ARObjectList(long? customerId,long? contractId)
        {
            var listModel = new ARObjectListModel();

            if (customerId.HasValue && customerId > 0 && contractId.HasValue && contractId > 0)
            {
                var caseList = CaseService.Instance.GetCaseBasicByContactId(customerId.Value,contractId.Value);
                listModel.ARObjects = new List<BizArObject>();

                if (caseList!=null && caseList.Any())
                {
                    caseList.ForEach(c =>
                    {
                        var ar = new BizArObject();
                        ar.CaseId = c.CaseBasicInfo.CaseId;
                        ar.CaseNo = c.CaseBasicInfo.CaseNo;
                        ar.CaseRequestDate = c.CaseBasicInfo.CaseRequestDate;
                        ar.CaseRequestNo = c.CaseBasicInfo.CaseRequestNo;
                        ar.ContractId = c.CaseBasicInfo.ContractId;
                        ar.ContractNo = c.CaseBasicInfo.ContractNo;
                        ar.CustomerId = c.CaseBasicInfo.FirstApplicantId;

                        listModel.ARObjects.Add(ar);
                    });
                }
                else
                {
                    listModel.ARObjects.Add(new BizArObject());
                }
             }
            else
            {
                listModel.ARObjects = new List<BizArObject>();
                listModel.ARObjects.Add(new BizArObject());
            }

            return PartialView("PartialView/ARObjectList", listModel);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult ARObjects(long? customerId, long? contractId)
        {
            var response = new PostResponse();
            response.IsSuccess = true;
            var arObjects = new List<BizArObject>();

            if (customerId.HasValue && customerId > 0 && contractId.HasValue && contractId > 0)
            {
                var caseList = CaseService.Instance.GetCaseBasicByContactId(customerId.Value, contractId.Value);

                if (caseList != null && caseList.Any())
                {
                    caseList.ForEach(c =>
                    {
                        var ar = new BizArObject();
                        ar.CaseId = c.CaseBasicInfo.CaseId;
                        ar.CaseNo = c.CaseBasicInfo.CaseNo;
                        ar.CaseRequestDate = c.CaseBasicInfo.CaseRequestDate;
                        ar.CaseRequestNo = c.CaseBasicInfo.CaseRequestNo;
                        ar.ContractId = c.CaseBasicInfo.ContractId;
                        ar.ContractNo = c.CaseBasicInfo.ContractNo;
                        ar.CustomerId = c.CaseBasicInfo.FirstApplicantId;

                        arObjects.Add(ar);
                    });
                }
                else
                {
                    arObjects.Add(new BizArObject());
                }
            }
            else
            {
                arObjects.Add(new BizArObject());
            }

            response.Data = arObjects;

            return Json(response);
        }


        [HttpPost]
        [CheckUserLogin]
        public JsonResult ARCreateUpdate(CreateModel model)
        {
            var response = new PostResponse();

            try
            {
                bool result = ARService.Instance.Create(model.ArObjects);

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
                response.IsSuccess = true;
            }
            return Json(response);
        }

        #endregion

        /// <summary>
        /// 费用类型
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult ARObjectCaseFee(ARObjecCaseFeeModel model)
        {
            var c = CaseService.Instance.GetCaseBasic(model.CaseId);

            model.CaseRequestDate = c.CaseBasicInfo.CaseRequestDate;

            return PartialView("PartialView/ARObjectCaseFee", model);
        }
        
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult List()
        {
            var listModel = new ListModel();
            listModel.SearchCondition = new ContractSearchCondition();
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 15;
            return View(listModel);
        }

        [CheckUserLogin]
        [HttpPost]
        public JsonResult List(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizCaseFeeSummarySearchResultInfo();

                result.ContractList = ContractService.Instance.GetComplexContractList(model.SearchCondition);
                result.TotalAmount = model.SearchCondition.TotalAmount;
                result.TotalCashedAmount = model.SearchCondition.TotalCashedAmount;
                result.TotalARAmount = model.SearchCondition.TotalARAmount;
                result.TotalAROfficeAmount = model.SearchCondition.TotalAROfficeAmount;
                result.TotalARNoOfficeAmount = model.SearchCondition.TotalARNoOfficeAmount;

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error("ARController.List", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractNo"></param>
        /// <param name="customerNo"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult Details(string contractNo,string customerNo)
        {
            var detailsModel = new DetailsModel();
            detailsModel.SearchCondition = new ContractSearchCondition();
            detailsModel.SearchCondition.ContractNo = contractNo;
            detailsModel.SearchCondition.CustomerNo = customerNo;
            detailsModel.SearchCondition.PageNo = 1;
            detailsModel.SearchCondition.PageSize = 1000;
            return View(detailsModel);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult Details(DetailsModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 1000;

                var result = new BizCaseFeeDetailSearchResultInfo();

                result.ContractList = ContractService.Instance.GetComplexContractList(model.SearchCondition);

                var caseFeeTypes = CaseTypeService.Instance.GetAllCaseFeeTypes();

                if (result.ContractList != null && result.ContractList.Any())
                {
                    result.ContractList.ForEach(x =>
                    {
                        x.CaseList = new List<BizCase>();

                        var caseFeeList = CaseFeeService.Instance.GetCaseFeeList(x.ContractBasicInfo.ContractId);

                        if (caseFeeList != null && caseFeeList.Any())
                        {
                            caseFeeList.ForEach(fee =>
                            {
                                if (
                                    !x.CaseList.Any(c => c.CaseBasicInfo != null && c.CaseBasicInfo.CaseNo == fee.CaseNo))
                                {
                                    var c = new BizCase();
                                    c.CaseBasicInfo = new BizCaseBasic();
                                    c.CaseBasicInfo.CaseId = fee.CaseId;
                                    c.CaseBasicInfo.CaseNo = fee.CaseNo;

                                    c.CaseBasicInfo.TotalAmount =
                                    caseFeeList.FindAll(ar => ar.CaseId == c.CaseBasicInfo.CaseId)
                                        .Sum(ar => ar.Amount.HasValue ? ar.Amount : 0);
                                    c.CaseBasicInfo.CashedAmount =
                                        caseFeeList.FindAll(ar => ar.CaseId == c.CaseBasicInfo.CaseId)
                                            .Sum(ar => ar.CashedAmount.HasValue ? ar.CashedAmount : 0);

                                    var caseOfficeFee =
                                        caseFeeList.FindAll(
                                            ar =>
                                                ar.CaseId == c.CaseBasicInfo.CaseId &&
                                                caseFeeTypes.Any(
                                                    f =>
                                                        f.TypeId == CaseFeeTypeId.Office &&
                                                        f.FeeTypeId == ar.CaseFeeTypeId))
                                            .Sum(ar => ar.Amount.HasValue ? ar.Amount : 0);
                                    var cashedOfficeFee =
                                        caseFeeList.FindAll(
                                            ar =>
                                                ar.CaseId == c.CaseBasicInfo.CaseId &&
                                                caseFeeTypes.Any(
                                                    f =>
                                                        f.TypeId == CaseFeeTypeId.Office &&
                                                        f.FeeTypeId == ar.CaseFeeTypeId))
                                            .Sum(ar => ar.CashedAmount.HasValue ? ar.CashedAmount : 0);
                                    var caseNonOfficeFee =
                                        caseFeeList.FindAll(
                                            ar =>
                                                ar.CaseId == c.CaseBasicInfo.CaseId &&
                                                caseFeeTypes.Any(
                                                    f =>
                                                        f.TypeId == CaseFeeTypeId.NonOffice &&
                                                        f.FeeTypeId == ar.CaseFeeTypeId))
                                            .Sum(ar => ar.Amount.HasValue ? ar.Amount : 0);
                                    var cashedNonOfficeFee =
                                        caseFeeList.FindAll(
                                            ar =>
                                                ar.CaseId == c.CaseBasicInfo.CaseId &&
                                                caseFeeTypes.Any(
                                                    f =>
                                                        f.TypeId == CaseFeeTypeId.NonOffice &&
                                                        f.FeeTypeId == ar.CaseFeeTypeId))
                                            .Sum(ar => ar.CashedAmount.HasValue ? ar.CashedAmount : 0);

                                    c.CaseBasicInfo.ARCaseOfficeFeeAmount = caseOfficeFee - cashedOfficeFee;
                                    c.CaseBasicInfo.ARCaseNonOfficeFeeAmount = caseNonOfficeFee - cashedNonOfficeFee;
                                    c.CaseBasicInfo.ARAmount =
                                        caseFeeList.FindAll(ar => ar.CaseId == c.CaseBasicInfo.CaseId)
                                            .Sum(ar => ar.Amount.HasValue ? ar.Amount : 0) -
                                        c.CaseBasicInfo.CashedAmount;

                                    x.CaseList.Add(c);
                                }
                            });
                        }
                    });
                }

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error("ARController.Details", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);

        }

    }
}
