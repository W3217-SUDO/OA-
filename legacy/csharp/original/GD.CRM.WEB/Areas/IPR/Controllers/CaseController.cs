using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Web.Mvc;

using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.BizModel.CRM.LawFirm;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.Service.FAM.AR.CaseFee;
using Dchien.Legal.Service.IPR.CaseFileProcess.Patent;
using Dchien.Legal.Service.IPR.CaseFileProcess.Trademark;
using Dchien.Legal.Service.IPR.CaseFileProcess;
using Dchien.Legal.Web.Areas.IPR.ViewModels.Case;
using Dchien.Legal.Service;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.CRM.LawFirm;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.IPR.Controllers
{
    [CheckUserLogin]
    [PermissionAttribute(Dchien.Legal.Entity.System.PageId.PageId_1001001)]
    public class CaseController : BaseController
    {
        internal Log Logger = new Log("IPR.Controllers.CaseController");

        #region 案件基本信息

        /// <summary>
        /// type=1 表示我的案件
        /// type=2 表示提醒案件
        /// type=3 未申请案件
        /// </summary>
        /// <param name="typeId"></param>
        /// <param name="caseId"></param>
        /// <param name="k"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CreateUpdate(int? typeId = 1, long? caseId = 0, string k = "")
        {
            var model = new CaseModel();

            if (caseId.HasValue && caseId.Value > 0)
            {
                model.Case = CaseService.Instance.GetCase(caseId.Value);
            }
            else
            {
                model.Case = new BizCase();
                model.Case.CaseBasicInfo = new BizCaseBasic();

                model.Case.CaseBasicInfo.CaseOriginPeople = LoginHelper.GetUserName(); //案源人，默认为当前用户
                model.Case.CaseBasicInfo.CaseOriginPeopleName = LoginHelper.GetUserChName();
                model.Case.CaseBasicInfo.CaseOriginDate = DateTime.Now; //默认为当天
                model.Case.CaseBasicInfo.Deadline = DateTime.Now.AddDays(1);
                model.Case.CaseBasicInfo.CaseSubmitDate = DateTime.Now; //默认为当天
                model.Case.CaseBasicInfo.CaseSubmitter = LoginHelper.GetUserName(); //默认为当前用户
                model.Case.CaseBasicInfo.CaseSubmitterName = LoginHelper.GetUserChName();
                model.Case.CaseBasicInfo.CaseOfficer = LoginHelper.GetUserName(); //默认为当前用户
                model.Case.CaseBasicInfo.CaseOfficerName = LoginHelper.GetUserChName();

                model.Case.CaseBasicInfo.CaseRegisterDate = DateTime.Now;

                model.Case.CaseFiles = new List<BizCaseFile>();
                model.Case.CaseCustomers = new List<BizCustomer>();
                model.Case.CaseEvents = new List<BizCaseEvent>();
                model.Case.CaseBasicInfo.CaseTypeId = (int) CaseType.Invention;
                model.Case.CaseBasicInfo.CasePhaseId = (int) CasePhaseType.Phase0;
            }

            model.CaseSearchTypeId = typeId;

            if (!string.IsNullOrEmpty(k))
            {
                 model.Keyword = k;
            }
            return View(model);
        }

        [CheckUserLogin]
        public ActionResult Create(long customerId)
        {
            var model = new CaseModel();

            model.Case = new BizCase();
            model.Case.CaseBasicInfo = new BizCaseBasic();

            model.Case.CaseBasicInfo.CaseOriginPeople = LoginHelper.GetUserName(); //案源人，默认为当前用户
            model.Case.CaseBasicInfo.CaseOriginPeopleName = LoginHelper.GetUserChName();
            model.Case.CaseBasicInfo.CaseOriginDate = DateTime.Now; //默认为当天
            model.Case.CaseBasicInfo.Deadline = DateTime.Now.AddDays(1);
            model.Case.CaseBasicInfo.CaseSubmitDate = DateTime.Now; //默认为当天
            model.Case.CaseBasicInfo.CaseSubmitter = LoginHelper.GetUserName(); //默认为当前用户
            model.Case.CaseBasicInfo.CaseSubmitterName = LoginHelper.GetUserChName();
            model.Case.CaseBasicInfo.CaseOfficer = LoginHelper.GetUserName(); //默认为当前用户
            model.Case.CaseBasicInfo.CaseOfficerName = LoginHelper.GetUserChName();

            model.Case.CaseBasicInfo.CaseRegisterDate = DateTime.Now;

            model.Case.CaseFiles = new List<BizCaseFile>();
            model.Case.CaseCustomers = new List<BizCustomer>();

            var customer = CustomerService.Instance.GetCustomerBasicById(customerId);
            model.Case.CaseCustomers.Add(customer);

            model.Case.CaseEvents = new List<BizCaseEvent>();
            model.Case.CaseBasicInfo.CaseTypeId = (int)CaseType.Invention;
            model.Case.CaseBasicInfo.CasePhaseId = (int)CasePhaseType.Phase0;
            model.Case.CaseBasicInfo.FirstApplicantId = customerId;

            return PartialView(model);
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

            if (isSubmit)
            {
                model.Case.CaseBasicInfo.CaseSubmitter = LoginHelper.GetUserName(); //提交人默认自己
                model.Case.CaseBasicInfo.CaseSubmitDate = DateTime.Now; //提交时间默认当前时间
            }

            try
            {
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

            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <param name="isSubmit"></param>
        /// <returns></returns>
        public JsonResult CaseQuickCreateUpdate(CaseModel model, long? orgCaseId, bool isSubmit)
        {
            var response = new PostResponse();

            //model.Case.CaseBasicInfo.CaseOriginPeople = LoginHelper.GetUserName(); //提交人默认自己
            //model.Case.CaseBasicInfo.CaseOriginDate = DateTime.Now;
            model.Case.CaseBasicInfo.CaseSubmitter = LoginHelper.GetUserName(); //提交人默认自己
            model.Case.CaseBasicInfo.CaseRegisterDate = DateTime.Now;
            model.Case.CaseBasicInfo.CaseOfficer = LoginHelper.GetUserName();
            model.Case.CaseBasicInfo.Deadline = DateTime.Now.AddYears(1);
            model.Case.CaseBasicInfo.CaseSubmitDate = DateTime.Now; //提交时间默认当前时间
            model.Case.CaseBasicInfo.VersionNo = BizCase.DefaultVesionNo; //

            try
            {
                bool result = CaseService.Instance.CreateUpdateCase(model.Case);

                if (orgCaseId.HasValue)
                {
                    //复制的案件

                    var lst = CaseCustomerService.Instance.GetCaseCustomerContactsList(orgCaseId.Value);

                    var documentContactsIds = lst.FindAll(x => x.Item1 == (int)Dchien.Legal.Entity.IPR.Case.CaseCustomerContactsType.Document).Select(x => x.Item2).ToList();
                    var technologyContactsIds = lst.FindAll(x => x.Item1 == (int)Dchien.Legal.Entity.IPR.Case.CaseCustomerContactsType.Technology).Select(x => x.Item2).ToList();

                    CaseService.Instance.CreateCaseCustomerContacts(model.Case.CaseBasicInfo.CaseId, model.Case.CaseBasicInfo.CustomerId.Value, documentContactsIds, technologyContactsIds);
                }

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

            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }

            return Json(response);
        }


        ///// <summary>
        ///// 
        ///// </summary>
        ///// <param name="caseReminderTypeId"></param>
        ///// <returns></returns>
        //[CheckUserLogin]
        //[HttpPost]
        //public JsonResult GetCasesByReminderType(int? caseReminderTypeId)
        //{
        //    var response = new PostResponse();

        //    var lst = caseReminderTypeId.HasValue
        //        ? CaseService.Instance.GetCasesByReminderTypeId(caseReminderTypeId.Value, false)
        //        : new List<BizCase>();

        //    response.IsSuccess = true;
        //    response.Data = lst;

        //    return Json(response);
        //}

        ///// <summary>
        ///// 
        ///// </summary>
        ///// <param name="caseCategoryTypeId"></param>
        ///// <returns></returns>
        //[CheckUserLogin]
        //[HttpPost]
        //public JsonResult GetCasesByCategoryType(int? caseCategoryTypeId)
        //{
        //    var response = new PostResponse();

        //    var lst = caseCategoryTypeId.HasValue
        //        ? CaseService.Instance.GetCasesByCategoryTypeId(caseCategoryTypeId.Value, false)
        //        : new List<BizCase>();

        //    response.IsSuccess = true;
        //    response.Data = lst.Any() ? lst.OrderBy(x => x.CaseBasicInfo.Deadline).ToList() : lst;

        //    return Json(response);
        //}

        //[CheckUserLogin]
        //[HttpPost]
        //public JsonResult GetCasesByCustom(string keyword)
        //{
        //    var response = new PostResponse();

        //    var search = new BizCaseSearch();
        //    search.CaseSearchParams = new CaseSearchCondition();
        //    search.CaseSearchParams.Keyword = keyword;
        //    search.CaseSearchParams.PageNo = 1;
        //    search.CaseSearchParams.PageSize = 500;

        //    var lst = !string.IsNullOrEmpty(keyword)
        //        ? CaseService.Instance.GetCaseList(search, false)
        //        : new List<BizCase>();

        //    response.IsSuccess = true;
        //    response.Data = lst.Any() ? lst.OrderBy(x => x.CaseBasicInfo.Deadline).ToList() : lst;

        //    return Json(response);
        //}

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="caseListSelectedTypeId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult CaseInfo(long caseId, int? caseListSelectedTypeId)
        {
            var caseModel = new CaseModel();

            caseModel.CurrentSelectedListTypeId = caseListSelectedTypeId;

            if (caseId > 0)
            {
                caseModel.Case = CaseService.Instance.GetCase(caseId);
            }
            else
            {
                caseModel.Case = new BizCase();

                caseModel.Case.CaseBasicInfo = new BizCaseBasic();

                caseModel.Case.CaseBasicInfo.CaseOriginPeople = LoginHelper.GetUserName(); //案源人，默认为当前用户
                caseModel.Case.CaseBasicInfo.CaseOriginPeopleName = LoginHelper.GetUserChName();
                caseModel.Case.CaseBasicInfo.CaseOriginDate = DateTime.Now; //默认为当天
                caseModel.Case.CaseBasicInfo.CaseSubmitDate = DateTime.Now; //默认为当天
                caseModel.Case.CaseBasicInfo.CaseSubmitter = LoginHelper.GetUserName(); //默认为当前用户
                caseModel.Case.CaseBasicInfo.CaseSubmitterName = LoginHelper.GetUserChName();
                caseModel.Case.CaseBasicInfo.CaseOfficer = LoginHelper.GetUserName(); //默认为当前用户
                caseModel.Case.CaseBasicInfo.CaseOfficerName = LoginHelper.GetUserChName();
                caseModel.Case.CaseBasicInfo.Deadline = DateTime.Now.AddDays(30); //默认为当天

                caseModel.Case.CaseBasicInfo.CaseRegisterDate = DateTime.Now;

                caseModel.Case.CaseFiles = new List<BizCaseFile>();
                caseModel.Case.CaseCustomers = new List<BizCustomer>();
                caseModel.Case.CaseBasicInfo.CaseTypeId = (int) CaseType.Invention;
                caseModel.Case.CaseBasicInfo.CasePhaseId = (int) CasePhaseType.Phase0;
                caseModel.Case.CaseEvents = new List<BizCaseEvent>();
            }

            return this.CaseInfo(caseModel);
        }

        [CheckUserLogin]
        public ActionResult CaseInfo(CaseModel caseModel)
        {
            return PartialView("CaseInfo", caseModel);
        }

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
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult GetCaseBasic(long caseId)
        {
            var response = new PostResponse();
            var caseInfo = CaseService.Instance.GetCaseBasic(caseId);
            response.Data = caseInfo;
            response.IsSuccess = true;
            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public ActionResult GetCaseBasicByCaseNo(string caseNo)
        {
            var response = new PostResponse();
            var caseInfo = CaseService.Instance.GetCaseBasicByCaseNo(caseNo);
            if (caseInfo.CaseBasicInfo != null)
            {
                response.Data = caseInfo;
                response.IsSuccess = true;
            }
            else
            {
                response.IsSuccess = false;
            }
            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public ActionResult GetCaseBasicByCaseRequestNo(string caseRequestNo)
        {
            var response = new PostResponse();
            var caseInfo = CaseService.Instance.GetCaseBasic(caseRequestNo);
            if (caseInfo.CaseBasicInfo != null)
            {
                response.Data = caseInfo;
                response.IsSuccess = true;
            }
            else
            {
                response.IsSuccess = false;
            }
            return Json(response);
        }


        [HttpPost]
        [CheckUserLogin]
        public ActionResult GetCaseBasicByCaseNoByOwner(string caseNo)
        {
            var response = new PostResponse();
            var caseInfo = CaseService.Instance.GetCaseBasicByCaseNo(caseNo);

            if (caseInfo == null || caseInfo.CaseBasicInfo == null)
            {
                response.Message = "输入的案号不存在.";
                response.IsSuccess = false;

            }
            else if (caseInfo.CaseBasicInfo.BusinessOwner != LoginHelper.GetUserName())
            {
                response.Message = "该案件不属于您名下,不允许添加到该合同下.";
                response.IsSuccess = false;
            }
            else
            {
                response.Data = caseInfo;
                response.IsSuccess = true;

            }
            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public ActionResult GetCaseBasicByCaseRequestNoByOwner(string caseRequestNo)
        {
            var response = new PostResponse();
            var caseInfo = CaseService.Instance.GetCaseBasic(caseRequestNo);

            if (caseInfo== null || caseInfo.CaseBasicInfo == null)
            {
                response.Message = "输入的案号不存在.";
                response.IsSuccess = false;

            }
            else if (caseInfo.CaseBasicInfo.BusinessOwner != LoginHelper.GetUserName())
            {
                response.Message = "该案件不属于您名下,不允许添加到该合同下.";
                response.IsSuccess = false;
            }
            else
            {
                response.Data = caseInfo;
                response.IsSuccess = true;
            }

            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="reminderTypeId"></param>
        /// <param name="categoryTypeId"></param>
        /// <param name="customerId"></param>
        /// <param name="k"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CaseList(int? reminderTypeId, int? categoryTypeId, int? customerId, string k)
        {
            var searchParams = new CaseSearchCondition();
            searchParams.ReminderTypeId = reminderTypeId;
            searchParams.CategoryTypeId = categoryTypeId;
            searchParams.CustomerId = customerId;
            searchParams.Keyword = k;

            return this.CaseList(null, searchParams);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="search"></param>
        /// <param name="searchParams"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult CaseList(BizCaseSearchCondition search, CaseSearchCondition searchParams)
        {
            if (search != null)
            {
                if (!string.IsNullOrEmpty(Request["caseTypeIds"]))
                {
                    var caseTypeIds = Request["caseTypeIds"].ToString();
                    search.CaseBasicSearchCondition.CaseTypeId = caseTypeIds.Split(',').Select(int.Parse).ToList();
                }

                if (!string.IsNullOrEmpty(Request["caseTypeNames"]))
                {
                    var caseTypeNames = Request["caseTypeNames"].ToString();
                    search.CaseBasicSearchCondition.CaseTypeName = caseTypeNames.Split(',').ToList();
                }

                if (!string.IsNullOrEmpty(Request["casePhaseIds"]))
                {
                    var casePhaseIds = Request["casePhaseIds"].ToString();
                    search.CaseBasicSearchCondition.CasePhaseId = casePhaseIds.Split(',').Select(int.Parse).ToList();
                }

                if (!string.IsNullOrEmpty(Request["casePhaseNames"]))
                {
                    var casePhaseNames = Request["casePhaseNames"].ToString();
                    search.CaseBasicSearchCondition.CasePhaseName = casePhaseNames.Split(',').ToList();
                }

                if (!string.IsNullOrEmpty(Request["caseFeeTypeIds"]))
                {
                    var caseFeeTypeIds = Request["caseFeeTypeIds"].ToString();
                    search.CaseFeeSearchCondition.FeeTypeId = caseFeeTypeIds.Split(',').Select(int.Parse).ToList();
                }

                if (!string.IsNullOrEmpty(Request["caseFeeTypeNames"]))
                {
                    var caseFeeTypeNames = Request["caseFeeTypeNames"].ToString();
                    search.CaseFeeSearchCondition.FeeTypeName = caseFeeTypeNames.Split(',').ToList();
                }

                if (!string.IsNullOrEmpty(Request["caseFileTypeIds"]))
                {
                    var caseFileTypeIds = Request["caseFileTypeIds"].ToString();
                    search.CaseFileSearchCondition.FileTypeId = caseFileTypeIds.Split(',').Select(int.Parse).ToList();
                }

                if (!string.IsNullOrEmpty(Request["caseFileTypeNames"]))
                {
                    var caseFileTypeNames = Request["caseFileTypeNames"].ToString();
                    search.CaseFileSearchCondition.FileTypeName = caseFileTypeNames.Split(',').ToList();
                }

                if (!string.IsNullOrEmpty(Request["caseFeeInvoiceStatusIds"]))
                {
                    var caseFeeInvoiceStatusIds = Request["caseFeeInvoiceStatusIds"].ToString();
                    //search.CaseFeeSearchCondition.InvoiceStatus = caseFeeInvoiceStatusIds.Split(',').Select(int.Parse).ToList();
                    search.CaseFeeSearchCondition.BillStatusId =
                        caseFeeInvoiceStatusIds.Split(',').Select(int.Parse).ToList();
                }

                if (!string.IsNullOrEmpty(Request["caseFeeInvoiceStatusNames"]))
                {
                    var caseFeeInvoiceStatusNames = Request["caseFeeInvoiceStatusNames"].ToString();
                    search.CaseFeeSearchCondition.BillStatusName = caseFeeInvoiceStatusNames.Split(',').ToList();
                }
            }

            var caseListModel = new CaseListModel();
            caseListModel.Search = search;
            caseListModel.SearchCondition = searchParams ?? new CaseSearchCondition();
            caseListModel.SearchCondition.PageNo = 1;
            caseListModel.SearchCondition.PageSize = 15;
            return View(caseListModel);
        }

        ///// <summary>
        ///// 
        ///// </summary>
        ///// <param name="search"></param>
        ///// <returns></returns>
        //[HttpPost]
        //[CheckUserLogin]
        //public JsonResult Cases(CaseSearchConditionModel search)
        //{
        //    var response = new PostResponse();

        //    try
        //    {
        //        if (search.SearchCondition.PageNo == 0)
        //            search.SearchCondition.PageNo = 1;
        //        if (search.SearchCondition.PageSize == 0)
        //            search.SearchCondition.PageSize = 15;

        //        var result = new BizCaseSearchResultInfo();

        //        var caseSearch = new BizCaseSearch()
        //        {
        //            CaseSearchCondition = search.Search,
        //            CaseSearchParams = search.SearchCondition
        //        };


        //        result.CaseList = CaseService.Instance.GetCaseList(caseSearch, true);

        //        result.TotalItemCount = caseSearch.CaseSearchParams.TotalCount;
        //        result.PageNo = caseSearch.CaseSearchParams.PageNo;
        //        result.PageSize = caseSearch.CaseSearchParams.PageSize;

        //        response.IsSuccess = true;
        //        response.Data = result;
        //    }
        //    catch (Exception ex)
        //    {
        //        response.IsSuccess = false;
        //        Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"CaseController.Cases","CaseController.Cases", ex);
        //    }
        //    return Json(response);
        //}


        #endregion

        #region 案件批量修改 

        /// <summary>
        /// 案件批量修改
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseBatchEdit(CaseBatchEditModel model)
        {
            model.CaseOfficer = LoginHelper.GetUserName();
            model.CaseOfficerName = LoginHelper.GetUserChName();
            //model.Deadline = DateTime.Now;

            if (model == null)
            {
                throw new ArgumentNullException("model");
            }

            return PartialView("PartialView/CaseBatchEdit", model);
        }


        /// <summary>
        ///  保存案件批量修改
        /// </summary>
        /// <param name="model"></param>
        /// <param name="caseIdList"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseBatchEditCreate(CaseBatchEditModel model, string caseIdList)
        {
            var response = new PostResponse();
            bool result = false;
            try
            {
                caseIdList.Split(',').ToList().ForEach(x =>
                {
                    var c = CaseService.Instance.GetCaseBasic(long.Parse(x));

                    if (!string.IsNullOrEmpty(model.CaseNo))
                    {
                        c.CaseBasicInfo.CaseNo = model.CaseNo;

                        CaseService.Instance.ChangCaseNo(c.CaseBasicInfo, c.CaseBasicInfo.CaseNo, model.CaseNo);
                    }

                    if (!string.IsNullOrEmpty(model.CaseOfficer))
                    {
                        c.CaseBasicInfo.CaseOfficer = model.CaseOfficer;
                    }

                    if (model.Deadline.HasValue)
                    {
                        c.CaseBasicInfo.Deadline = model.Deadline;
                    }

                    if (model.CasePhaseId.HasValue && model.CasePhaseId.Value != -1)
                    {
                        c.CaseBasicInfo.CasePhaseId = model.CasePhaseId.Value;
                    }

                    result = CaseService.Instance.CreateUpdateCase(c);
                });
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
                return Json(response);
            }

            if (result)
            {
                response.Message = "批量修改成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "批量修改失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

        #region 案件年度修改

        /// <summary>
        ///  
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseAnnualYearEdit(CaseAnnualYearEditModel model)
        {
            if (model == null)
            {
                throw new ArgumentNullException("model");
            }

            return PartialView("PartialView/CaseAnnualYearEdit", model);
        }


        /// <summary>
        ///   
        /// </summary>
        /// <param name="model"></param>
        /// <param name="caseIdList"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseAnnualYearEditCreate(List<long> caseIds, int? firstAnnualYear, decimal? costSlowRate)
        {
            var response = new PostResponse();
            bool result = false;
            try
            {
                caseIds.ForEach(x =>
                {
                    var c = CaseService.Instance.GetCaseBasic(x);

                    if (firstAnnualYear.HasValue && firstAnnualYear > 0)
                    {
                        c.CaseBasicInfo.FirstAnnualYear = firstAnnualYear;
                    }

                    if (costSlowRate.HasValue)
                    {
                        c.CaseBasicInfo.CostSlowRate = costSlowRate;
                    }

                    result = CaseService.Instance.CreateUpdateCase(c);
                });
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
                return Json(response);
            }

            if (result)
            {
                response.Message = "批量修改成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "批量修改失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

        #region 提成比例设定


        /// <summary>
        /// 案件批量修改
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseRate(CaseRateModel model)
        {
            if (model == null)
            {
                throw new ArgumentNullException("model");
            }

            var c = CaseService.Instance.GetCaseBasic(model.CaseId);

            if (c != null)
            {
                model.CopyRate = c.CaseBasicInfo.CopyRate;
                model.LeadRate = c.CaseBasicInfo.LeadRate;
            }

            return PartialView("PartialView/CaseRate", model);
        }

        [HttpPost]
        public JsonResult CaseRateCreateUpdate(CaseRateModel model)
        {
            var response = new PostResponse();
            bool result = false;
            try
            {
                var c = CaseService.Instance.GetCaseBasic(model.CaseId);

                c.CaseBasicInfo.CopyRate = model.CopyRate;
                c.CaseBasicInfo.LeadRate = model.LeadRate;

                result = CaseService.Instance.CaseRateCreateUpdate(c);
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
                return Json(response);
            }

            if (result)
            {
                response.Message = "提成比例设定成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "提成比例设定失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

        #region 案件基本信息 截止日期，处理人设定

        [HttpPost]
        [CheckUserLogin]
        public ActionResult CaseDeadLine(long caseId)
        {
            var caseModel = new CaseModel();

            if (caseId > 0)
            {
                caseModel.Case = CaseService.Instance.GetCase(caseId);
            }
            else
            {
                caseModel.Case = new BizCase();

                caseModel.Case.CaseBasicInfo = new BizCaseBasic();

                caseModel.Case.CaseBasicInfo.CaseOriginPeople = LoginHelper.GetUserName(); //案源人，默认为当前用户
                caseModel.Case.CaseBasicInfo.CaseOriginPeopleName = LoginHelper.GetUserChName();
                caseModel.Case.CaseBasicInfo.CaseOriginDate = DateTime.Now; //默认为当天
                caseModel.Case.CaseBasicInfo.CaseSubmitDate = DateTime.Now; //默认为当天
                caseModel.Case.CaseBasicInfo.CaseSubmitter = LoginHelper.GetUserName(); //默认为当前用户
                caseModel.Case.CaseBasicInfo.CaseSubmitterName = LoginHelper.GetUserChName();
                caseModel.Case.CaseBasicInfo.CaseOfficer = LoginHelper.GetUserName(); //默认为当前用户
                caseModel.Case.CaseBasicInfo.CaseOfficerName = LoginHelper.GetUserChName();
                caseModel.Case.CaseBasicInfo.Deadline = DateTime.Now.AddDays(30); //默认为当天

                caseModel.Case.CaseFiles = new List<BizCaseFile>();
                caseModel.Case.CaseCustomers = new List<BizCustomer>();
                caseModel.Case.CaseBasicInfo.CaseTypeId = (int) CaseType.Invention;
                caseModel.Case.CaseBasicInfo.CasePhaseId = (int) CasePhaseType.Phase0;
                caseModel.Case.CaseEvents = new List<BizCaseEvent>();
            }

            return PartialView("PartialView/CaseDeadLine", caseModel);
        }

        #endregion

        #region 案件律所

        public ActionResult CaseLawFirmSelected(long caseId)
        {
            var model = new CaseLawFirmSelectedModel();
            model.CaseId = caseId;

            return PartialView("PartialView/CaseLawFirmSelected", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <returns></returns>
        [HttpPost]

        public ActionResult CaseLawFirmList(long caseId)
        {
            var caseModel = new CaseLawFirmListModel();
            if (caseId > 0)
            {
                caseModel.CaseLawFirms = CaseService.Instance.GetCaseLawFirms(caseId);
            }

            return PartialView("PartialView/CaseLawFirmList", caseModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseLawFirmListSelected(CaseLawFirmSelectedModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 10;

                var result = new BizLawFirmSearchResultInfo();

                result.LawFirms = LawFirmService.Instance.GetLawFirmsAll(model.SearchCondition);

                result.SelectedLawFirms =
                    CaseService.Instance.GetCaseLawFirms(model.CaseId).Select(x => x.LawFirmId).ToList();

                result.TotalItemCount = result.LawFirms.Count;
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
        /// <param name="lawfirmIds"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CreateCaseLawFirm(long caseId, int[] lawfirmIds)
        {
            var response = new PostResponse();
            CaseService.Instance.CreateCaseLawFirm(caseId, lawfirmIds.ToList());

            response.Data = "";
            response.IsSuccess = true;
            return Json(response);

        }

        #endregion

        #region 案件资费

        [HttpPost]
        public ActionResult CaseAssistedFee(CaseAssistedFeeModel model)
        {
            return PartialView("PartialView/CaseAssistedFee", model);
        }

        /// <summary>
        /// /案件费用列表
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseAssistedFeeList(long caseId, int? pageNo, int? pageSize)
        {
            var caseModel = new CaseAssistedFeeListModel();
            caseModel.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            caseModel.PageSize = pageSize.HasValue ? pageSize.Value : 15;
            if (caseId > 0)
            {
                caseModel.CaseAssistedFees = CaseAssistedFeeService.Instance.GetCaseAssistedFees(caseId);
                caseModel.TotalCount = caseModel.CaseAssistedFees.Count;
                caseModel.CaseAssistedFees = caseModel.CaseAssistedFees.Any()
                    ? caseModel.CaseAssistedFees.Skip(caseModel.PageSize*(caseModel.PageNo - 1))
                        .Take(caseModel.PageSize)
                        .ToList()
                    : new List<BizCaseAssistedFee>();
            }
            return PartialView("PartialView/CaseAssistedFeeList", caseModel);
        }

        [HttpPost]
        public JsonResult CaseAssistedFeeCreate(CaseAssistedFeeModel model)
        {
            var response = new PostResponse();

            var caseFee = new BizCaseAssistedFee();
            caseFee.CaseId = model.CaseId;
            caseFee.CaseNo = model.CaseNo;
            caseFee.AssistedFeeTypeId = model.CaseAssistedFeeTypeId;

            bool result = CaseAssistedFeeService.Instance.CreateCaseAssistedFee(caseFee);

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

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseAssistedFeeId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseAssistedFeeDelete(int caseAssistedFeeId)
        {
            var response = new PostResponse();

            bool result = CaseAssistedFeeService.Instance.DeleteCaseAssistedFee(caseAssistedFeeId);

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


        [HttpPost]
        public ActionResult CaseAssistedFeeConfirm(int caseAssistedFeeId)
        {
            var model = new CaseAssistedFeeModel();
            model.CaseAssistedFeeId = caseAssistedFeeId;
            var caseFee = CaseAssistedFeeService.Instance.GetCaseAssistedFee(caseAssistedFeeId);

            model.CaseAssistedFeeTypeId = caseFee.AssistedFeeTypeId;
            model.ResponseDate = DateTime.Now;
            model.CaseId = caseFee.CaseId;
            model.CaseNo = caseFee.CaseNo;

            return PartialView("PartialView/CaseAssistedFeeConfirm", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseAssistedFeeTransact(CaseAssistedFeeModel model)
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

            var caseFee = new BizCaseAssistedFee();
            caseFee.AssistedFeeId = model.CaseAssistedFeeId;
            caseFee.CaseId = model.CaseId;
            caseFee.CaseNo = model.CaseNo;
            caseFee.ResponseDate = model.ResponseDate;
            caseFee.FileName = file.FileName;
            caseFee.FileFullPath = file.FileName;
            caseFee.FileSize = fileSize;

            bool result = CaseAssistedFeeService.Instance.TransactCaseAssistedFee(caseFee, bytes);

            if (result)
            {
                response.Message = "办理成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "办理失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }


        #endregion

        #region 案件文档 列表，文件上传

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseFileList(long caseId, int? pageNo, int? pageSize)
        {
            var caseModel = new CaseFileListModel();
            caseModel.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            caseModel.PageSize = pageSize.HasValue ? pageSize.Value : 15;

            if (caseId > 0)
            {
                caseModel.CaseFiles = CaseFileService.Instance.GetCaseFiles(caseId);
                caseModel.TotalCount = caseModel.CaseFiles.Count;
                caseModel.CaseFiles = caseModel.CaseFiles.Any()
                    ? caseModel.CaseFiles.Skip(caseModel.PageSize*(caseModel.PageNo - 1))
                        .Take(caseModel.PageSize)
                        .OrderByDescending(x => x.UploadingTime.Date).ThenByDescending(x=>x.FileId)
                        //.OrderByDescending(x => x.FileId)
                        .ToList()
                    : new List<BizCaseFile>();
            }

            return PartialView("PartialView/CaseFileList", caseModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
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

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFileUploading(CaseFileUploadModel model)
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

            var caseFile = this.ConvertToCaseFile(model, DateTime.Now.ToString("yyyyMMddHHmmss") + "_" + file.FileName, fileSize);
            var canRepeatUpload = CaseFileService.Instance.CheckCaseFileCanRepeatUpload(caseFile);

            if (!canRepeatUpload)
            {
                response.Message = string.Format("案件({0})已存在该类型文档，且不允许重复上传。", caseFile.CaseNo);
                response.IsSuccess = false;
                return Json(response);
            }

            var result = this.ProcessCaseFileUploading(caseFile, bytes);

            if (result)
            {
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
        /// <param name="model"></param>
        /// <param name="fileName"></param>
        /// <param name="fileSize"></param>
        /// <returns></returns>
        private BizCaseFile ConvertToCaseFile(CaseFileUploadModel model, string fileName, long fileSize)
        {
            var caseFile = new BizCaseFile();
            caseFile.CaseId = model.CaseId;
            caseFile.CaseNo = model.CaseNo;
            caseFile.FileTypeId = model.CaseFileTypeId;
            caseFile.FileTypeName = model.CaseFileTypeName;
            caseFile.FileName = fileName;
            caseFile.FileSize = fileSize;
            caseFile.IsActive = true;
            caseFile.UploadingTime = model.UploadingTime.HasValue ? model.UploadingTime.Value : DateTime.Now;
            caseFile.UploadingTime = model.UploadingTime.HasValue ? model.UploadingTime.Value : DateTime.Now;
            caseFile.HedgingFileTypeId = model.HedgingFileTypeId;
            caseFile.HedgingFileId = model.HedgingFileId;
            caseFile.HedgingFeeId = model.HedgingFeeId;

            caseFile.CaseRequestNo = model.CaseRequestNo;

            return caseFile;
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFile"></param>
        /// <param name="bytes"></param>
        /// <returns></returns>
        private bool ProcessCaseFileUploading(BizCaseFile caseFile, byte[] bytes)
        {
            var c = CaseService.Instance.GetCaseBasic(caseFile.CaseId);
            bool result = CaseService.Instance.Process(c, caseFile, bytes);

            //if (c.CaseBasicInfo.CaseTypeId == (int)CaseType.Invention)
            //{
            //    var service = new InventionCaseService();
            //    result = service.Process(c, caseFile, bytes);
            //}
            //else if (c.CaseBasicInfo.CaseTypeId == (int)CaseType.UtilityModel)
            //{
            //    var service = new UtilityModelService();
            //    result = service.Process(c, caseFile, bytes);
            //}
            //else if (c.CaseBasicInfo.CaseTypeId == (int)CaseType.Design)
            //{
            //    var service = new DesignCaseService();
            //    result = service.Process(c, caseFile, bytes);
            //}
            //else if (c.CaseBasicInfo.CaseTypeId == (int)CaseType.Trade)
            //{
            //    var service = new TradeCaseService();
            //    result = service.Process(c, caseFile, bytes);
            //}
            //else if (c.CaseBasicInfo.CaseTypeId == (int)CaseType.Copyright)
            //{
            //    var service = new CopyrightCaseService();
            //    result = service.Process(c, caseFile, bytes);
            //}
            //else
            //{
            //    result = CaseService.Instance.Process(c, caseFile, bytes);
            //}
            return result;
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

            var start = fileName.LastIndexOf(".");
            string type = fileName.Substring(start, fileName.Length - start);
            //if (type.ToLower() == ".jpg" || type.ToLower() == ".png" || type.ToLower() == ".gif")
            //    return true;

            //return false;

            return true;
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseFileUpload(CaseFileUploadModel model)
        {
            if (model == null)
            {
                throw new ArgumentNullException("model");
            }
            var caseType = CaseTypeService.Instance.GetCaseType(model.CaseTypeId);
            model.CustomerId = CaseService.Instance.GetCaseCustomers(model.CaseId).FirstOrDefault() != null
                ? CaseService.Instance.GetCaseCustomers(model.CaseId).FirstOrDefault().CustomerBasic.CustomerId
                : 0;

            if (null == caseType)
            {
                throw new ApplicationException(string.Format("未找到案件类型，caseId:{0},caseTypeId:{1}", model.CaseId,
                    model.CaseTypeId));
            }

            model.CaseFileTypeList = caseType.CaseFileTypeList;
            model.UploadingTime = DateTime.Now.Date; // 默认值

            if (model.HedgingFileTypeId.HasValue && model.HedgingFileTypeId.Value > 0)
            {
                model.CaseFileTypeList =
                    model.CaseFileTypeList.Where(x => x.FileTypeId == model.HedgingFileTypeId.Value).ToList();
            }

            return PartialView("PartialView/CaseFileUpload", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFileId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFileUnlock(long caseFileId)
        {
            var response = new PostResponse();

            bool result = CaseFileService.Instance.CaseFileUnlock(caseFileId);

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
        /// <param name="caseFileId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult TagTransformed(List<long> caseFileIds)
        {
            var response = new PostResponse();

            bool result = CaseFileService.Instance.TagTransformed(caseFileIds);

            if (result)
            {
                response.Message = "转文成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "转文失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFileId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFileDelete(long caseFileId)
        {
            var response = new PostResponse();

            try
            {
                bool result = CaseFileService.Instance.CaseFileDelete(caseFileId);

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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"CaseController.CaseFileDelete","CaseController.CaseFileDelete", ex);
                throw;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="caseFileTypeId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult GetHedgingFileAndFeeList(long caseId, int caseFileTypeId)
        {
            var response = new PostResponse();

            var caseFileType =
                CaseTypeService.Instance.GetAllCaseFileTypes().FirstOrDefault(x => x.FileTypeId == caseFileTypeId);

            if (caseFileType == null)
            {
                response.Message = "文件类型未找到.";
                response.IsSuccess = false;
                return Json(response);
            }

            var hedgingFileTypeIds = caseFileType.HedgingFileTypeId;
            var hedgingFeeTypeIds = caseFileType.HedgingFeeTypeId;

            var caseHedgingFiles = new List<BizCaseFile>();
            var caseHedgingFees = new List<Dchien.Legal.BizModel.FAM.AR.CaseFee.BizCaseFee>();

            if (!string.IsNullOrEmpty(hedgingFileTypeIds))
            {
                //获取待转文文档列表
                var hedgingFileTypeIdList = hedgingFileTypeIds.Split(',').ToList();
                var caseFiles = CaseFileService.Instance.GetCaseFiles(caseId);
                caseHedgingFiles =
                    caseFiles.FindAll(
                        x => x.IsActive && !x.HasHedgingFile && hedgingFileTypeIdList.Contains(x.FileTypeId.ToString()));
            }

            if (!string.IsNullOrEmpty(hedgingFeeTypeIds))
            {
                //获取待转票通知列表
                var hedgingFeeTypeIdList = hedgingFeeTypeIds.Split(',').ToList();
                var caseFees = CaseFeeService.Instance.GetCaseFeeListByCaseId(caseId);
                caseHedgingFees =
                    caseFees.FindAll(
                        x =>
                            x.IsActived && !x.HasHedgingFile &&
                            hedgingFeeTypeIdList.Contains(x.CaseFeeTypeId.ToString()));
            }

            response.Data =
                new Tuple<List<BizCaseFile>, List<Dchien.Legal.BizModel.FAM.AR.CaseFee.BizCaseFee>>(caseHedgingFiles,
                    caseHedgingFees);

            response.IsSuccess = true;

            //对冲文件
            return Json(response);
        }


        #endregion

        #region 案件日志

        /// <summary>
        /// 打开案件日志
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseLog(CaseLogModel model)
        {
            var caseModel = new CaseLogModel();

            if (model.LogId.HasValue && model.LogId > 0)
            {
                caseModel.CaseLog = CaseLogService.Instance.GetCaseLog(model.LogId.Value);
            }
            else
            {
                caseModel.CaseLog = new BizCaseLog();
                caseModel.CaseLog.LogType = (int)CaseLogType.Business;
            }

            return PartialView("PartialView/CaseLog", caseModel);
        }

        [HttpPost]
        public ActionResult CaseOperatingLogList(long caseId, int? pageNo, int? pageSize)
        {
            var caseModel = new CaseLogListModel();
            caseModel.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            caseModel.PageSize = pageSize.HasValue ? pageSize.Value : 15;

            if (caseId > 0)
            {
                caseModel.CaseLogs = CaseLogService.Instance.GetCaseLogs(caseId);
                caseModel.TotalCount = caseModel.CaseLogs.FindAll(x => x.LogType == (int)CaseLogType.Operation).Count;
                caseModel.CaseLogs = caseModel.CaseLogs.FindAll(x => x.LogType == (int)CaseLogType.Operation).Any()
                    ? caseModel.CaseLogs.FindAll(x=>x.LogType == (int)CaseLogType.Operation).Skip(caseModel.PageSize * (caseModel.PageNo - 1))
                        .Take(caseModel.PageSize)
                        .OrderByDescending(x => x.OperatorDate)
                        .ToList()
                    : new List<BizCaseLog>();
            }

            return PartialView("PartialView/CaseOperatingLogList", caseModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseLogCreate(CaseLogModel model)
        {
            var response = new PostResponse();

            var caseLog = new BizCaseLog();
            caseLog.CaseId = model.CaseId;
            caseLog.CaseNo = model.CaseNo;
            caseLog.Content = model.CaseLog.Content;
            caseLog.LogType = (int) CaseLogType.Business;

            bool result = CaseLogService.Instance.CreateCaseLog(caseLog);

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

        [HttpPost]
        public ActionResult CaseLogList(long caseId)
        {
            var caseModel = new CaseLogListModel();
            if (caseId > 0)
            {
                caseModel.CaseLogs = CaseLogService.Instance.GetCaseLogs(caseId);
            }
            return PartialView("PartialView/CaseLogList", caseModel);
        }

        #endregion

        #region 案件事件提醒

        /// <summary>
        /// 打开案件日志
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseEvent(CaseEventModel model)
        {
            if (model.EventId.HasValue && model.EventId > 0)
            {
                //model.CaseEvent = CaseEventService.Instance.GetCaseEvent(model.EventId.Value);
                return PartialView("PartialView/CaseEvent", model);
            }
            else
            {
                var c = CaseService.Instance.GetCaseBasic(model.CaseId);
                model.CaseEvent = new BizCaseEvent();
                model.CaseEvent.Deadline = c.CaseBasicInfo.Deadline;
                model.CaseEvent.EventTime = c.CaseBasicInfo.ReminderDate;
                return PartialView("PartialView/CaseEvent", model);
            }

        }

        [HttpPost]
        public JsonResult CaseEventCreate(CaseEventModel model)
        {
            var response = new PostResponse();
            var c = CaseService.Instance.GetCaseBasic(model.CaseId);

            var caseEvent = new BizCaseEvent();
            caseEvent.CaseId = model.CaseId;
            caseEvent.CaseNo = c.CaseBasicInfo.CaseNo;
            caseEvent.CompanyId = model.CompanyId;
            caseEvent.FileId = 0;
            caseEvent.EventTypeId = 0;
            caseEvent.Deadline = model.CaseEvent.Deadline;
            caseEvent.EventTime = model.CaseEvent.EventTime;
            caseEvent.EventContent = model.CaseEvent.EventContent;

            bool result = CaseEventService.Instance.CreateCaseEvent(caseEvent);

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

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseEventList(long caseId)
        {
            var caseModel = new CaseEventListModel();
            if (caseId > 0)
            {
                caseModel.CaseEvents = CaseEventService.Instance.GetCaseEvents(caseId);
            }
            return PartialView("PartialView/CaseEventList", caseModel);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseEventId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseEventDelete(long caseEventId)
        {
            var response = new PostResponse();

            try
            {
                bool result = CaseEventService.Instance.CaseEventDelete(caseEventId);

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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"CaseController.CaseEventDelete","CaseController.CaseEventDelete", ex);
                throw;
            }

            return Json(response);
        }

        #endregion

        #region 案件文档批量导出

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult CaseListToWord()
        {
            var model = new CaseListModel();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 100;
            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerId"></param>
        /// <param name="caseFileTypeId"></param>
        /// <param name="caseIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult ExportCaseListToWord(long customerId, int caseFileTypeId, long[] caseIds)
        {
            var response = new PostResponse();

            try
            {
                var caseFileType =
                    CaseTypeService.Instance.GetAllCaseFileTypes().FirstOrDefault(x => x.FileTypeId == caseFileTypeId);

                if (caseFileType != null && caseFileType.IsTransformed)
                {
                    //var fileProcess = CaseFileProcessFactory.Create((CaseFileType) caseFileTypeId);

                    CaseFileBaseProcess fileProcess = null;
                    if (caseFileType.CaseTypeId == (int)CaseClassType.Patent)
                    {
                        fileProcess = PatentCaseFileProcessFactory.Create((CaseFileType)caseFileTypeId);
                    }
                    else
                    {
                        fileProcess = TrademarkCaseFileProcessFactory.Create((CaseFileType)caseFileTypeId);
                    }

                    var c = CaseService.Instance.GetCaseBasic(caseIds[0]);

                    if (c.CaseBasicInfo.CustomerId.HasValue)
                    {
                        customerId = c.CaseBasicInfo.CustomerId.Value;
                    }

                    var fileName = fileProcess.ExportToWord(customerId,caseFileTypeId);

                    response.Data = customerId + "|" + fileName;
                    response.IsSuccess = true;
                    return Json(response);
                }
                else
                {
                    response.Data = string.Empty;
                    response.IsSuccess = false;
                    response.Message = string.Format("未找到案件文件类型{0}，或该文件类型不是转文文档.", caseFileTypeId);
                    return Json(response);
                }
            }
            catch (ApplicationException ex)
            {
                response.Data = string.Empty;
                response.IsSuccess = false;
                response.Message = ex.Message;
                return Json(response);
            }
            catch (NotImplementedException ex)
            {
                response.Data = string.Empty;
                response.IsSuccess = false;
                response.Message = "未实现.";
                return Json(response);
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseController.ExportCaseListToWord", "CaseController.ExportCaseListToWord", ex);
                throw;
            }
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFileId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult ExportCaseFileToWord(long caseFileId)
        {
            var caseFile = CaseFileService.Instance.GetCaseFile(caseFileId);
            if (caseFile != null)
            {
                var customers = CaseService.Instance.GetCaseCustomers(caseFile.CaseId);
                if (customers.Any())
                {
                    return this.ExportCaseListToWord(customers.FirstOrDefault().CustomerBasic.CustomerId.Value, caseFile.FileTypeId,
                        new[] {caseFile.CaseId});
                }
                else
                {
                    var response = new PostResponse();
                    response.IsSuccess = false;
                    response.Message = "未找到案件客户";
                    return Json(response);
                }
            }
            else
            {
                var response = new PostResponse();
                response.IsSuccess = false;
                response.Message = "未找到案件文件";
                return Json(response);
            }
        }

        [HttpPost]
        public JsonResult CaseListToWord(CaseListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 100;

                var result = new BizCaseSearchResultInfo();

                result.CaseList = CaseService.Instance.GetCaseListToWord(model.SearchCondition);

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
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseListExportToWord(CaseListToWordModel model)
        {
            return PartialView("PartialView/CaseListExportToWord", model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseIdList"></param>
        /// <param name="caseFileIdList"></param>
        /// <param name="caseFileTypeId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseListFileUploading(string caseIdList, string caseFileIdList, string caseFeeIdList, int caseFileTypeId)
        {
            var response = this.CheckCaseFileUploading();

            if (response != null)
            {
                return Json(response);
            }

            var file = Request.Files[0];
            int fileSize = file.ContentLength;
            var bytes = new byte[fileSize];
            using (var stream = file.InputStream)
            {
                stream.Read(bytes, 0, fileSize);
            }

            response = new PostResponse();
            var messages = new StringBuilder();
            var existsCaseFileNos = new List<string>();

            var caseFileType =
                CaseTypeService.Instance.GetAllCaseFileTypes().FirstOrDefault(x => x.FileTypeId == caseFileTypeId);

            if (caseFileType == null)
            {
                response.IsSuccess = false;
                response.Message = "未找到文件类型.";
            }

            var hedgingFeeTypeIds = new List<int>();
            var hedgingFileTypeIds = new List<int>();

            hedgingFeeTypeIds = string.IsNullOrEmpty(caseFileType.HedgingFeeTypeId)
                ? new List<int>()
                : caseFileType.HedgingFeeTypeId.Split(',').Select(Int32.Parse).ToList();
            hedgingFileTypeIds = string.IsNullOrEmpty(caseFileType.HedgingFileTypeId)
                ? new List<int>()
                : caseFileType.HedgingFileTypeId.Split(',').Select(Int32.Parse).ToList();


            caseIdList.Split(',').Select(long.Parse).ToList().ForEach(caseId =>
            {
                var c = CaseService.Instance.GetCaseBasic(caseId);
                if (c != null)
                {

                    var caseFile = new BizCaseFile()
                    {
                        CaseId = c.CaseBasicInfo.CaseId,
                        CaseNo = c.CaseBasicInfo.CaseNo,
                        FileTypeId = caseFileTypeId,
                        FileName = file.FileName,
                        FileSize = fileSize,
                        IsActive = true,

                        UploadingTime = DateTime.Now
                    };

                    var canRepeatUpload = CaseFileService.Instance.CheckCaseFileCanRepeatUpload(caseFile);

                    if (!canRepeatUpload)
                    {
                        existsCaseFileNos.Add(c.CaseBasicInfo.CaseNo);
                    }
                    else
                    {
                        List<BizCaseFile> hedgingFiles = null;
                        List<Dchien.Legal.BizModel.FAM.AR.CaseFee.BizCaseFee> hedgingFees = null;
                        if (hedgingFileTypeIds.Any())
                        {
                            var caseFiles = CaseFileService.Instance.GetCaseFiles(caseId);
                            hedgingFiles = caseFiles.Any()
                                ? caseFiles.FindAll(
                                    x =>
                                        hedgingFileTypeIds.Contains(x.FileTypeId) && x.IsActive &&
                                        x.HasHedgingFile == false)
                                : null;
                        }

                        if (hedgingFeeTypeIds.Any())
                        {
                            var caseFees = CaseFeeService.Instance.GetCaseFeeListByCaseId(caseId);
                            hedgingFees = caseFees.Any()
                                ? caseFees.FindAll(
                                    x => hedgingFeeTypeIds.Contains(x.CaseFeeTypeId) && x.IsActived &&
                                         x.HasHedgingFile == false)
                                : null;
                        }

                        caseFile.HedgingFileId = hedgingFiles == null
                            ? null
                            : hedgingFiles.Select(x => (long?) x.FileId).ToList();
                        caseFile.HedgingFeeId = hedgingFees == null
                            ? null
                            : hedgingFees.Select(x => (long?) x.CaseFeeId).ToList();

                        this.ProcessCaseFileUploading(caseFile, bytes);
                    }
                }
            });

            if (existsCaseFileNos.Any())
            {
                response.Message = string.Format("案件({0})已存在该类型文档，且不允许重复上传。", string.Join(",", existsCaseFileNos));
                response.IsSuccess = false;
            }
            else
            {
                //标记已转 
                if (!string.IsNullOrEmpty(caseFileIdList))
                {
                    CaseFileService.Instance.TagTransformed(caseFileIdList.Split(',').Select(long.Parse).ToList());
                }

                if (!string.IsNullOrEmpty(caseFeeIdList))
                {
                    CaseFeeService.Instance.RemoveFeeHedgingFile(caseFeeIdList.Split(',').Select(long.Parse).ToList());
                }

                response.Message = "上传成功！";
                response.IsSuccess = true;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseIdList"></param>
        /// <param name="caseFileIdList"></param>
        /// <param name="caseFileTypeId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFeeInformFileUploading(string caseIdList, string caseFeeIdList, int caseFileTypeId)
        {
            var response = this.CheckCaseFileUploading();

            if (response != null)
            {
                return Json(response);
            }

            var file = Request.Files[0];
            int fileSize = file.ContentLength;
            var bytes = new byte[fileSize];
            using (var stream = file.InputStream)
            {
                stream.Read(bytes, 0, fileSize);
            }

            response = new PostResponse();
            var messages = new StringBuilder();
            var existsCaseFileNos = new List<string>();

            var caseFileType =
                CaseTypeService.Instance.GetAllCaseFileTypes().FirstOrDefault(x => x.FileTypeId == caseFileTypeId);

            if (caseFileType == null)
            {
                response.IsSuccess = false;
                response.Message = "未找到文件类型.";
            }

            caseIdList.Split(',').Select(long.Parse).ToList().ForEach(caseId =>
            {
                var c = CaseService.Instance.GetCaseBasic(caseId);
                if (c != null)
                {

                    var caseFile = new BizCaseFile()
                    {
                        CaseId = c.CaseBasicInfo.CaseId,
                        CaseNo = c.CaseBasicInfo.CaseNo,
                        FileTypeId = caseFileTypeId,
                        FileName = file.FileName,
                        FileSize = fileSize,
                        IsActive = true,

                        UploadingTime = DateTime.Now
                    };

                    this.ProcessCaseFileUploading(caseFile, bytes);
                }

            });


            response.Message = "上传成功！";
            response.IsSuccess = true;


            return Json(response);
        }

        #endregion

        #region 批量新建案件

        [CheckUserLogin]
        [PermissionAttribute(Dchien.Legal.Entity.System.PageId.PageId_1001003)]
        public ActionResult MultiCreate(string id)
        {
            var createModel = new MultiCreateModel();
            createModel.Cases = new List<BizCase>();
            return View(createModel);
        }


        [HttpPost]
        [CheckUserLogin]
        public JsonResult MultiCaseCreateUpdate(MultiCreateModel model)
        {
            var response = new PostResponse();

            var result = false;

            var list = new List<string>();

            if (model.Cases != null && model.Cases.Any())
            {
                try
                {
                    model.Cases.ForEach(x =>
                    {
                        x.CaseBasicInfo.CaseOriginPeople = LoginHelper.GetUserName();
                        x.CaseBasicInfo.CaseOfficer = LoginHelper.GetUserName();
                        result = CaseService.Instance.CreateUpdateCase(x);
                        list.Add(x.CaseBasicInfo.CaseNo);
                    });
                }
                catch (Exception ex)
                {
                    throw ex;
                }

            }
 
            if (result)
            {
                response.Data = list;
                response.Message = "批量创建案件成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "批量创建案件失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult MultiCaseList()
        {
            var listModel = new MultiCreateModel();
            listModel.Cases = new List<BizCase>();

            var c = new BizCase();

            c.CaseBasicInfo = new BizCaseBasic();
            c.CaseBasicInfo.CaseOfficer = LoginHelper.GetUserName();
            c.CaseBasicInfo.CasePhaseId = (int)CasePhaseType.Phase1;
            c.CaseBasicInfo.CaseOfficerName = LoginHelper.GetUserChName();
            c.CaseBasicInfo.CaseRegisterDate = DateTime.Now;
            c.CaseBasicInfo.CaseOriginPeople = LoginHelper.GetUserName();
            c.CaseBasicInfo.CaseOriginPeopleName = LoginHelper.GetUserChName();
            c.CaseBasicInfo.Deadline = DateTime.Now.AddMonths(1);

            listModel.Cases.Add(c);


            return PartialView("PartialView/MultiCaseList", listModel);
        }
 
    #endregion

        #region 客户案件树

        [CheckUserLogin]
        [HttpPost]
        public ActionResult CaseTreeView(long customerId)
        {
            var caseModel = new CaseTreeModel();
            caseModel.CustomerId = customerId;
            caseModel.Customer = CustomerService.Instance.GetCustomerById(customerId);
            return PartialView("CaseTreeView", caseModel);
        }

        [HttpPost]
        public JsonResult CaseListByCustomerId(long customerId,string keyword)
        {
            var response = new PostResponse();
            var cases = CaseService.Instance.GetCaseBasicByCustomerId(customerId, keyword);
            var caseTypes = CaseTypeService.Instance.GetAllCaseTypes();
 
            var nodes = new List<Node>();

            //第一级菜单 案件类型
            caseTypes.ForEach(x =>
            {
                if (cases.FindAll(c => c.CaseBasicInfo.CaseTypeId == x.CaseTypeId && c.CaseBasicInfo.CasePhaseId != (int)CasePhaseType.Phase99).Any())
                {
                    var node = new Node()
                    {
                        nodeType = "M",
                        nodeOriginalId = x.CaseTypeId,
                        nodeCode = x.CaseTypeShortCode,
                        nodeId = x.CaseTypeId,
                        text = x.CaseTypeName,
                        state = new State(),
                        nodes = cases.FindAll(c => c.CaseBasicInfo.CaseTypeId == x.CaseTypeId).Any() ? new List<Node>() : null
                    };

                    //第二级 案件号
                    cases.FindAll(c => c.CaseBasicInfo.CaseTypeId == x.CaseTypeId).ForEach(c =>
                    {
                        var node2 = new Node()
                        {
                            nodeType = "A",
                            nodeOriginalId = c.CaseBasicInfo.CaseId,
                            nodeId = c.CaseBasicInfo.CaseId,
                            nodeCode = c.CaseBasicInfo.CaseNo,
                            text = c.CaseBasicInfo.CaseNo + "_" + (string.IsNullOrEmpty(c.CaseBasicInfo.CaseName) ? "暂无名称" : c.CaseBasicInfo.CaseName),
                            state = new State(),
                            nodes = null
                        };

                        node.nodes.Add(node2);
                    });

                    nodes.Add(node);
                }

            });

            response.Data = nodes;

            return Json(response);
        }

        #endregion

        #region 快速新建案件

        [CheckUserLogin]
        [HttpPost]
        public ActionResult QuickCreate(long customerId)
        {
            var caseModel = new QuickCreateModel();
            caseModel.CustomerId = customerId;
            return PartialView("QuickCreate", caseModel);
        }
        [CheckUserLogin]
        [HttpPost]
        public ActionResult QuickCopy(long customerId)
        {
            var caseModel = new QuickCopyModel();
            caseModel.CustomerId = customerId;
            return PartialView("QuickCopy", caseModel);
        }


        #endregion

        #region 重复提交案件

        [HttpPost]
        [CheckUserLogin]
        public ActionResult GetRebootingCaseByCaseNo(string caseNo)
        {
            var response = new PostResponse();

            var versions = new Dictionary<int, string>();

            versions.Add(1, "A");
            versions.Add(2, "B");
            versions.Add(3, "C");
            versions.Add(4, "D");
            versions.Add(5, "E");
            versions.Add(6, "F");
            versions.Add(7, "G");
            versions.Add(8, "H");
            versions.Add(9, "I");
            versions.Add(10, "J");

            var lastChar = caseNo.Substring(caseNo.Length - 1, 1);

            if (versions.Values.ToList().FirstOrDefault(x => x == lastChar) != null)
            {
                caseNo = caseNo.Substring(0, caseNo.Length - 1);
            }

            var caseInfo = CaseService.Instance.GetCaseBasicByCaseNo(caseNo);

            caseInfo.CaseBasicInfo.RebootingCaseNo = CaseService.Instance.GetCaseNextVersionNo(caseInfo.CaseBasicInfo.CaseNo, caseInfo.CaseBasicInfo.VersionNo);

             response.Data = caseInfo;
            response.IsSuccess = true;
            return Json(response);
        }

        [PermissionAttribute(Dchien.Legal.Entity.System.PageId.PageId_1001004)]
        public ActionResult CaseRebooting(string id)
        {
            var model = new RebootingCaseModle();

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseRebootingCreate(string caseNo)
        {
            var response = new PostResponse();

            var c = CaseService.Instance.CaseRebooting(caseNo);

            if (c != null)
            {
                response.Data = c;
                response.Message = "案件重提成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "案件重提失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

        #region 年费监控

        [HttpPost]
        public JsonResult CaseAddInAFM(List<long> caseIds)
        {
            var response = new PostResponse();

            try
            {

                bool result = CaseService.Instance.AddInAfm(caseIds);

                if (result)
                {
                    response.Message = "所选案件已加入年费监控.";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "操作失败！";
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseController.CaseAddInAFM", "CaseController.CaseAddInAFM", ex);
            }

            return Json(response);
        }

        [HttpPost]
        public JsonResult CaseRemoveAFM(List<long> caseIds)
        {
            var response = new PostResponse();

            try
            {

                bool result = CaseService.Instance.RemoveAfm(caseIds);

                if (result)
                {
                    response.Message = "所选案件已放弃年费监控.";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "操作失败！";
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseController.CaseAddRemoveAFM", "CaseController.CaseAddRemoveAFM", ex);
            }

            return Json(response);
        }

        #endregion

    }
}
