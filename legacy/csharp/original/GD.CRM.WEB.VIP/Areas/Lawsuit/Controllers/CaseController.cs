using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.BizModel.Lawsuit.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.CRM.Customer;
using Dchien.Legal.Entity.Lawsuit.Case;
using Dchien.Legal.Service.Lawsuit.Case;
using Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.CRM.LawFirm;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.Lawsuit.Controllers
{
    [CheckUserLogin]
    public class CaseController : BaseController
    {
        internal Log Logger = new Log("Lawsuit.Controllers.CaseController");

        #region 案件基本信息

       /// <summary>
       /// 
       /// </summary>
       /// <param name="typeId"></param>
       /// <param name="cId"></param>
       /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CreateUpdate(int? typeId = 1, long? cId = 0)
        {
            var model = new CaseModel();
            if (cId.HasValue && cId.Value > 0)
            {
                model.CaseId = cId.Value;
                model.Case = CaseService.Instance.GetCase(cId.Value);
            }

            if (model.Case == null)
            {
                model.CaseId = 0;
                model.Case = new BizCase();

                model.Case.CaseBasicInfo = new BizCaseBasic();
                model.Case.CaseBasicInfo.CaseId = 0;
                model.Case.CaseBasicInfo.CaseOriginPeople = LoginHelper.GetUserName(); //案源人，默认为当前用户
                model.Case.CaseBasicInfo.CaseOriginPeopleName = LoginHelper.GetUserChName();
                model.Case.CaseBasicInfo.Deadline = DateTime.Now.AddDays(30);
                model.Case.CaseBasicInfo.CaseSubmitDate = DateTime.Now; //默认为当天
                model.Case.CaseBasicInfo.CaseSubmitter = LoginHelper.GetUserName(); //默认为当前用户
                model.Case.CaseBasicInfo.CaseSubmitterName = LoginHelper.GetUserChName();
                model.Case.CaseBasicInfo.CaseOfficer = LoginHelper.GetUserName(); //默认为当前用户
                model.Case.CaseBasicInfo.CaseOfficerName = LoginHelper.GetUserChName();

                model.Case.CaseBasicInfo.CaseTypeId = (int) CaseType.Trade;
                model.Case.CaseBasicInfo.CasePhaseId = (int) CasePhaseType.Phase1;
            }

            model.Case.HasCaseInvestigation = true;
            model.Case.CurrentCaseLevel = CaseLevel.Investigation;

            model.CaseSearchTypeId = typeId;

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <param name="isSubmit"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CaseCreateUpdate(CaseModel model, bool isSubmit)
        {
            var response = new PostResponse();

            model.Case.CaseBasicInfo.CaseSubmitter = LoginHelper.GetUserName(); //提交人默认自己
            model.Case.CaseBasicInfo.CaseSubmitDate = DateTime.Now; //提交时间默认当前时间

            bool result = CaseService.Instance.CreateUpdateCase(model.Case);

            if (result)
            {
                response.Data = model.Case;
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

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseInstance(CaseModel model)
        {
            if (model.CaseId > 0)
            {
                var c = CaseService.Instance.GetCaseBasic(model.CaseId);

            }

            return PartialView("PartialView/CaseInstance", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseReminderTypeId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public JsonResult GetCasesByReminderType(int? caseReminderTypeId)
        {
            var response = new PostResponse();

            var lst = caseReminderTypeId.HasValue
                ? CaseService.Instance.GetCasesByReminderTypeId(caseReminderTypeId.Value)
                : new List<BizCase>();

            response.IsSuccess = true;
            response.Data = lst.Any() ? lst.OrderBy(x => x.CaseBasicInfo.Deadline).ToList() : lst;

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseCategoryTypeId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public JsonResult GetCasesByCategoryType(int? caseCategoryTypeId)
        {
            var response = new PostResponse();

            var lst = caseCategoryTypeId.HasValue
                ? CaseService.Instance.GetCasesByCategoryTypeId(caseCategoryTypeId.Value)
                : new List<BizCase>();

            response.IsSuccess = true;
            response.Data = lst.Any() ? lst.OrderBy(x => x.CaseBasicInfo.Deadline).ToList() : lst;

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="caseLevelId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult CaseInfo(long? caseId, int? caseLevelId)
        {
            var model = new CaseModel();

            if (caseId > 0)
            {
                model.CaseId = caseId.Value;
                model.Case = CaseService.Instance.GetCase(caseId.Value);
            }

            if (model.Case == null)
            {
                model.CaseId = 0;
                model.Case = new BizCase();

                model.Case.CaseBasicInfo = new BizCaseBasic();
                model.Case.CaseBasicInfo.CaseId = 0;
                model.Case.CaseBasicInfo.CaseOriginPeople = LoginHelper.GetUserName(); //案源人，默认为当前用户
                model.Case.CaseBasicInfo.CaseOriginPeopleName = LoginHelper.GetUserChName();
                model.Case.CaseBasicInfo.Deadline = DateTime.Now.AddDays(30);
                model.Case.CaseBasicInfo.CaseSubmitDate = DateTime.Now; //默认为当天
                model.Case.CaseBasicInfo.CaseSubmitter = LoginHelper.GetUserName(); //默认为当前用户
                model.Case.CaseBasicInfo.CaseSubmitterName = LoginHelper.GetUserChName();
                model.Case.CaseBasicInfo.CaseOfficer = LoginHelper.GetUserName(); //默认为当前用户
                model.Case.CaseBasicInfo.CaseOfficerName = LoginHelper.GetUserChName();

                model.Case.CaseBasicInfo.CaseTypeId = (int)CaseType.Trade;
                model.Case.CaseBasicInfo.CasePhaseId = (int)CasePhaseType.Phase1;
            }

            model.Case.HasCaseInvestigation = true;
            model.Case.CurrentCaseLevel = CaseLevel.Investigation;

            return this.CaseInfo(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseModel"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CaseInfo(CaseModel caseModel)
        {
            return PartialView("CaseInfo", caseModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseTypeId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult GetCaseType(int caseTypeId)
        {
            var response = new PostResponse();
            var caseType = CaseTypeService.Instance.GetCaseType(caseTypeId);
            response.Data = caseType;
            response.IsSuccess = true;
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="caseLevelId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult GetCaseBasic(long caseId, CaseLevel caseLevelId)
        {
            var caseInfo = CaseService.Instance.GetCaseBasic(caseId, CaseLevel.Investigation, CaseLevel.FirstInstance, CaseLevel.SecondInstance,CaseLevel.LastInstance,CaseLevel.Execution);

            var caseModel = new CaseModel();
            caseModel.Case = caseInfo;
            caseModel.CaseId = caseId;

            if (caseLevelId == CaseLevel.Investigation)
            {
                return PartialView("PartialView/CaseInvestigation", caseModel);
            }
            else if (caseLevelId == CaseLevel.FirstInstance)
            {
                return PartialView("PartialView/CaseFirstInstance", caseModel);
            }
            else if (caseLevelId == CaseLevel.SecondInstance)
            {
                if (caseInfo == null) return PartialView("PartialView/CaseSecondInstance", caseModel);

                if (caseInfo.HasCaseSecondInstance)
                {
                    return PartialView("PartialView/CaseSecondInstance", caseModel);
                }
                else if(caseInfo.HasCaseFirstInstance && caseInfo.CaseFirstInstance != null)
                {
                    caseInfo.CaseSecondInstance = new BizCaseSecondInstance();
                    this.CopyCaseInstance(caseInfo.CaseSecondInstance, caseInfo.CaseFirstInstance);
                    return PartialView("PartialView/CaseSecondInstance", caseModel);
                }
                else
                {
                    return PartialView("PartialView/CaseSecondInstance", caseModel);
                }
            }
            else if (caseLevelId == CaseLevel.LastInstance)
            {
                if (caseInfo == null) return PartialView("PartialView/CaseLastInstance", caseModel);

                if (caseInfo.HasCaseLastInstance)
                {
                    return PartialView("PartialView/CaseLastInstance", caseModel);
                }
                else if(caseInfo.HasCaseSecondInstance && caseInfo.CaseSecondInstance != null)
                {
                    //重二审复制
                    caseInfo.CaseLastInstance = new BizCaseLastInstance();
                    this.CopyCaseInstance(caseInfo.CaseLastInstance, caseInfo.CaseSecondInstance);
                    return PartialView("PartialView/CaseLastInstance", caseModel);
                }

                else if (caseInfo.HasCaseFirstInstance && caseInfo.CaseFirstInstance != null)
                {
                    //重一审复制
                    caseInfo.CaseLastInstance = new BizCaseLastInstance();
                    this.CopyCaseInstance(caseInfo.CaseLastInstance, caseInfo.CaseFirstInstance);
                    return PartialView("PartialView/CaseLastInstance", caseModel);
                }
                else
                {
                    return PartialView("PartialView/CaseLastInstance", caseModel);
                }
            }
            else if (caseLevelId == CaseLevel.Execution)
            {
                if (caseInfo == null) return PartialView("PartialView/CaseExecution", caseModel);

                if (caseInfo.HasCaseExecution)
                {
                    return PartialView("PartialView/CaseExecution", caseModel);
                }
                else if (caseInfo.HasCaseLastInstance && caseInfo.CaseLastInstance != null)
                {
                    //重再审复制
                    caseInfo.CaseExecution = new BizCaseExecution();
                    this.CopyCaseInstance(caseInfo.CaseExecution, caseInfo.CaseLastInstance);
                    return PartialView("PartialView/CaseExecution", caseModel);
                }
                else if (caseInfo.HasCaseSecondInstance && caseInfo.CaseSecondInstance != null)
                {
                    //重二审复制
                    caseInfo.CaseExecution = new BizCaseExecution();
                    this.CopyCaseInstance(caseInfo.CaseExecution, caseInfo.CaseSecondInstance);
                    return PartialView("PartialView/CaseExecution", caseModel);
                }
                else if (caseInfo.HasCaseFirstInstance && caseInfo.CaseFirstInstance != null)
                {
                    //重一审复制
                    caseInfo.CaseExecution = new BizCaseExecution();
                    this.CopyCaseInstance(caseInfo.CaseExecution, caseInfo.CaseFirstInstance);
                    return PartialView("PartialView/CaseExecution", caseModel);
                }
                else
                {
                    return PartialView("PartialView/CaseExecution", caseModel);
                }
            }

            throw new ApplicationException("can not found page.");

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="targetCaseInstance"></param>
        /// <param name="originalCaseInstance"></param>
        private void CopyCaseInstance( BizCaseInstance targetCaseInstance,BizCaseInstance originalCaseInstance)
        {
            targetCaseInstance.CaseLawyer = originalCaseInstance.CaseLawyer;
            targetCaseInstance.CaseLawyerName = originalCaseInstance.CaseLawyerName;
            targetCaseInstance.Assistant = originalCaseInstance.Assistant;
            targetCaseInstance.AssistantName = originalCaseInstance.AssistantName;
            targetCaseInstance.CaseProsecutor = originalCaseInstance.CaseProsecutor;
            targetCaseInstance.CaseProsecutorName = originalCaseInstance.CaseProsecutorName;
            targetCaseInstance.CaseProsecutorLitigationStatus =
                originalCaseInstance.CaseProsecutorLitigationStatus;

            targetCaseInstance.CaseDefendant = originalCaseInstance.CaseDefendant;
            targetCaseInstance.CaseDefendantName = originalCaseInstance.CaseDefendantName;
            targetCaseInstance.CaseDefendantLitigationStatus =
                originalCaseInstance.CaseDefendantLitigationStatus;

            targetCaseInstance.CaseCustomerAs = originalCaseInstance.CaseCustomerAs;
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="reminderTypeId"></param>
        /// <param name="categoryTypeId"></param>
        /// <param name="customerId"></param>
        /// <param name="k"></param>
        /// <returns></returns>
        //[CheckUserLogin]
        //public ActionResult CaseList(int? reminderTypeId, int? categoryTypeId, int? customerId, string k)
        //{
        //    var searchParams = new CaseSearchCondition();
        //    searchParams.ReminderTypeId = reminderTypeId;
        //    searchParams.CategoryTypeId = categoryTypeId;
        //    searchParams.CustomerId = customerId;
        //    searchParams.Keyword = k;

        //    return this.CaseList(null, searchParams);
        //}

        /// <summary>
        /// 
        /// </summary>
        /// <param name="search"></param>
        /// <param name="searchParams"></param>
        /// <returns></returns>
        //[HttpPost]
        //[CheckUserLogin]
        //public ActionResult CaseList(BizCaseSearchCondition search, CaseSearchCondition searchParams)
        //{
        //    if (search != null)
        //    {
        //        if (!string.IsNullOrEmpty(Request["caseTypeIds"]))
        //        {
        //            var caseTypeIds = Request["caseTypeIds"].ToString();
        //            search.CaseBasicSearchCondition.CaseTypeId = caseTypeIds.Split(',').Select(int.Parse).ToList();
        //        }

        //        if (!string.IsNullOrEmpty(Request["caseTypeNames"]))
        //        {
        //            var caseTypeNames = Request["caseTypeNames"].ToString();
        //            search.CaseBasicSearchCondition.CaseTypeName = caseTypeNames.Split(',').ToList();
        //        }

        //        if (!string.IsNullOrEmpty(Request["casePhaseIds"]))
        //        {
        //            var casePhaseIds = Request["casePhaseIds"].ToString();
        //            search.CaseBasicSearchCondition.CasePhaseId = casePhaseIds.Split(',').Select(int.Parse).ToList();
        //        }

        //        if (!string.IsNullOrEmpty(Request["casePhaseNames"]))
        //        {
        //            var casePhaseNames = Request["casePhaseNames"].ToString();
        //            search.CaseBasicSearchCondition.CasePhaseName = casePhaseNames.Split(',').ToList();
        //        }

        //        if (!string.IsNullOrEmpty(Request["caseFeeTypeIds"]))
        //        {
        //            var caseFeeTypeIds = Request["caseFeeTypeIds"].ToString();
        //            search.CaseFeeSearchCondition.FeeTypeId = caseFeeTypeIds.Split(',').Select(int.Parse).ToList();
        //        }

        //        if (!string.IsNullOrEmpty(Request["caseFeeTypeNames"]))
        //        {
        //            var caseFeeTypeNames = Request["caseFeeTypeNames"].ToString();
        //            search.CaseFeeSearchCondition.FeeTypeName = caseFeeTypeNames.Split(',').ToList();
        //        }

        //        if (!string.IsNullOrEmpty(Request["caseFileTypeIds"]))
        //        {
        //            var caseFileTypeIds = Request["caseFileTypeIds"].ToString();
        //            search.CaseFeeFileSearchCondition.FileTypeId = caseFileTypeIds.Split(',').Select(int.Parse).ToList();
        //        }

        //        if (!string.IsNullOrEmpty(Request["caseFileTypeNames"]))
        //        {
        //            var caseFileTypeNames = Request["caseFileTypeNames"].ToString();
        //            search.CaseFeeFileSearchCondition.FileTypeName = caseFileTypeNames.Split(',').ToList();
        //        }

        //        if (!string.IsNullOrEmpty(Request["caseFeeInvoiceStatusIds"]))
        //        {
        //            var caseFeeInvoiceStatusIds = Request["caseFeeInvoiceStatusIds"].ToString();
        //            search.CaseFeeSearchCondition.InvoiceStatus = caseFeeInvoiceStatusIds.Split(',').Select(int.Parse).ToList();
        //        }

        //        if (!string.IsNullOrEmpty(Request["caseFeeInvoiceStatusNames"]))
        //        {
        //            var caseFeeInvoiceStatusNames = Request["caseFeeInvoiceStatusNames"].ToString();
        //            search.CaseFeeSearchCondition.BillStatusName = caseFeeInvoiceStatusNames.Split(',').ToList();
        //        }
        //    }

        //    var caseListModel = new CaseListModel();
        //    caseListModel.Search = search;
        //    caseListModel.SearchCondition = searchParams ?? new CaseSearchCondition();
        //    return View(caseListModel);
        //}

        /// <summary>
        /// 
        /// </summary>
        /// <param name="search"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult Cases(CaseSearchConditionModel search)
        {
            var response = new PostResponse();

            //try
            //{
            //    if (search.SearchCondition.PageNo == 0)
            //        search.SearchCondition.PageNo = 1;
            //    if (search.SearchCondition.PageSize == 0)
            //        search.SearchCondition.PageSize = 20;

            //    var result = new BizCaseSearchResultInfo();

            //    var caseSearch = new BizCaseSearch()
            //    {
            //        CaseSearchCondition = search.Search,
            //        CaseSearchParams = search.SearchCondition
            //    };

                

            //    result.CaseList = CaseService.Instance.GetCaseList(caseSearch);

            //    result.TotalItemCount = caseSearch.CaseSearchParams.TotalCount;
            //    result.PageNo = caseSearch.CaseSearchParams.PageNo;
            //    result.PageSize = caseSearch.CaseSearchParams.PageSize;

            //    response.IsSuccess = true;
            //    response.Data = result;
            //}
            //catch (Exception ex)
            //{
            //    response.IsSuccess = false;
            //    Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),'',"CaseController.Cases", ex);
            //    throw ex;
            //}
            return Json(response);
        }
       
        #endregion

        #region 案件客户

        [HttpPost]
        public ActionResult CaseCustomerSelected(long caseId,int customerTypeId)
        {
            var model = new CaseCustomerSelectedModel();
            model.CaseId = caseId;
            model.CustomerTypeId = customerTypeId;

            return PartialView("PartialView/CaseCustomerSelected", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerIds"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseCustomerList(List<long> customerIds)
        {
            var caseModel = new CaseCustomerListModel();
            if (customerIds.Any())
            {
                caseModel.CaseCustomers = CustomerService.Instance.GetCaseCustomersByIds(customerIds);
            }

            return PartialView("PartialView/CaseCustomerList", caseModel);
        }

        [HttpPost]
        public JsonResult GetCaseCustomers(long caseId)
        {
            var response = new PostResponse();
            response.Data = CaseService.Instance.GetCaseCustomers(caseId);
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseCustomerListSelected(CaseCustomerSelectedModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 10;

                var result = new BizCustomerSearchResultInfo();

                model.SearchCondition.CustomerTypeId = CustomerLevel.All;
                result.Customers = CustomerService.Instance.GetCustomersByUser(model.SearchCondition);

                //result.SelectedCustomers =
                //    CaseService.Instance.GetCaseCustomers(model.CaseId).Select(x => x.CustomerId).ToList();

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

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="customerIds"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CreateCaseCustomer(long caseId, int[] customerIds)
        {
            var response = new PostResponse();
            CaseService.Instance.CreateCaseCustomer(caseId, customerIds.ToList());

            response.Data = "";
            response.IsSuccess = true;
            return Json(response);

        }

        #endregion

        #region 案件列表

        public ActionResult CaseList()
        {
            var caseListModel = new CaseListModel();
            caseListModel.SearchCondition = new CaseSearchCondition();
            caseListModel.SearchCondition.PageNo = 1;
            caseListModel.SearchCondition.PageSize = 20;
            return View(caseListModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseList(CaseListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 20;

                var result = new BizCaseSearchResultInfo();

                result.CaseList = CaseSearchService.Instance.GetCaseList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;

                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseController.Cases", "CaseController.Cases", ex);
            }
            return Json(response);
        }
        #endregion
    }
}
