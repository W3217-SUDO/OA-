using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.BizModel.Lawsuit;
using Dchien.Legal.BizModel.Lawsuit.Cause;
using Dchien.Legal.BizModel.Lawsuit.Court;
using Dchien.Legal.BizModel.FAM.AP.Payment;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Service.Lawsuit.Cause;
using Dchien.Legal.Service.Lawsuit.Court;
using Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter;
using Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter.CaseFeeType;
using Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter.CaseFileType;
using Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter.CasePhase;
using Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter.CaseType;
using Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter.PaymentType;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service.FAM.AP.Payment;
using Dchien.Legal.Service.BAS;

namespace Dchien.Legal.Web.Areas.System.Controllers
{
    public class SystemCenterController : Controller
    {
        #region 案件客户类型

         [CheckUserLogin]
        public ActionResult Index()
        {
            var customerTypeModel = new CustomerTypeModel();

            customerTypeModel.CaseCustomerTypeList = CustomerTypeService.Instance.GetCustomerType();

            return View(customerTypeModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CustomerTypeCreateUpdate(CustomerTypeModel model)
        {
            var response = new PostResponse();

            bool result = CustomerTypeService.Instance.CustomerTypeCreateUpdate(model.CaseCustomerTypeList);

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

        #region 系统本地配置

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
         [CheckUserLogin]
        public ActionResult LocalSettings()
        {
            var model = new LocalModel();

            model.LocalSettings = LocalSettingService.Instance.GetLocalSettings();

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult LocalSettingCreateUpdate(LocalModel model)
        {
            var response = new PostResponse();

            bool result = LocalSettingService.Instance.SettingsCreateUpdate(model.LocalSettingList);

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

        #region 案件文档类型

         [CheckUserLogin]
        public ActionResult CaseFileType(int? caseFileTypeId)
        {
            var model = new CaseFileTypeModel();
             model.CaseFileType = new BizCaseFileType();
            model.IsNew = true;
            if (caseFileTypeId.HasValue && caseFileTypeId.Value > -1)
            {
                model.CaseFileType =
                    CaseTypeService.Instance.GetAllCaseFileTypes()
                        .FirstOrDefault(x => x.FileTypeId == caseFileTypeId.Value);
                model.CaseFileTypeId = caseFileTypeId.Value;
                model.IsNew = false;
            }

            return PartialView(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>

         [CheckUserLogin]
        public ActionResult CaseFileTypeList()
        {
            var model = new Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter.CaseFileType.CaseFileTypeListModel();

            return View(model);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult CaseFileTypeList(Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter.CaseFileType.CaseFileTypeListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizCaseFileTypeSearchResultInfo();

                result.CaseFileTypes = CaseTypeService.Instance.GetAllCaseFileTypes();

                if (!string.IsNullOrEmpty(model.SearchCondition.CaseFileTypeName))
                {
                    result.CaseFileTypes =
                        result.CaseFileTypes.FindAll(x => x.FileTypeName.Contains(model.SearchCondition.CaseFileTypeName));

                }

                int start = (model.SearchCondition.PageNo - 1)*model.SearchCondition.PageSize;

                result.TotalItemCount = result.CaseFileTypes.Count;

                result.CaseFileTypes = result.CaseFileTypes.Skip(start).Take(model.SearchCondition.PageSize).ToList();

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
        public ActionResult CaseFileTypeCaseTypeList(int caseFileTypeId)
        {
            var model = new Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter.CaseFileType.CaseTypeListModel();

            model.CaseTypesAll = CaseTypeService.Instance.GetAllCaseTypes();
            model.CaseTypes = CaseTypeService.Instance.GetCaseTypes(caseFileTypeId);

            return PartialView(model);
        }

        /// <summary>
        ///  案件文档类型，关联费用类型，生成转字文档时需要
        /// </summary>
        /// <param name="caseFileTypeId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult CaseFileTypeCaseFeeTypeList(int caseFileTypeId)
        {
            var model = new CaseFileTypeCaseFeeTypeListModel();

            model.CaseFeeTypesAll = CaseTypeService.Instance.GetAllCaseFeeTypes();
            model.CaseFeeTypes = CaseTypeService.Instance.GetCaseFeeTypes(caseFileTypeId);
            model.CaseFileTypeId = caseFileTypeId;

            return PartialView(model);
        }

        /// <summary>
        ///  案件文档类型，关联费用类型 保存
        /// </summary>
        /// <param name="caseFileTypeId"></param>
        /// <param name="caseFeeTypeIds"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult CaseFileTypeCaseFeeTypeCreate(int caseFileTypeId, int[] caseFeeTypeIds)
        {
            var response = new PostResponse();
            CaseFileTypeService.Instance.CaseFileTypeCaseFeeTypeBound(caseFileTypeId, caseFeeTypeIds.ToList());

            response.Data = "";
            response.IsSuccess = true;
            return Json(response);
        }

        /// <summary>
        ///  案件文档类型，关联案件类型 保存
        /// </summary>
        /// <param name="caseFileTypeId"></param>
        /// <param name="caseTypeIds"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult CaseFileTypeCaseTypeCreate(int caseFileTypeId, int[] caseTypeIds)
        {
            var response = new PostResponse();
            CaseFileTypeService.Instance.CaseFileTypeCaseTypeBound(caseFileTypeId, caseTypeIds.ToList());

            response.Data = "";
            response.IsSuccess = true;
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CaseFileTypeCreateUpdate(CaseFileTypeModel model)
        {
            var response = new PostResponse();

            try
            {
                var result = CaseFileTypeService.Instance.CreateCaseFileType(model.CaseFileType, model.IsNew);
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

        #region 案件费用类型

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFeeTypeId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult CaseFeeType(int? caseFeeTypeId)
        {
            var model = new CaseFeeTypeModel();
            model.IsNew = true;
            if (caseFeeTypeId.HasValue && caseFeeTypeId.Value > -1)
            {
                model.CaseFeeType = CaseTypeService.Instance.GetAllCaseFeeTypes().FirstOrDefault(x => x.FeeTypeId == caseFeeTypeId.Value);
                model.CaseFeeTypeId = caseFeeTypeId.Value;
                model.IsNew = false;
            }
            else
            {
                model.CaseFeeType = new BizCaseFeeType();
            }

            return PartialView(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
         [CheckUserLogin]
        public ActionResult CaseFeeTypeList()
        {
            var model = new CaseFeeTypeListModel();

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CaseFeeTypeList(CaseFeeTypeListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizCaseFeeTypeSearchResultInfo();

                result.CaseFeeTypes = CaseTypeService.Instance.GetAllCaseFeeTypes().FindAll(x=>x.CaseTypeId>0);

                if (!string.IsNullOrEmpty(model.SearchCondition.CaseFeeTypeName))
                {
                    result.CaseFeeTypes =
                        result.CaseFeeTypes.FindAll(x => x.FeeTypeName.Contains(model.SearchCondition.CaseFeeTypeName));
                }

                int start = (model.SearchCondition.PageNo - 1)*model.SearchCondition.PageSize;

                result.TotalItemCount = result.CaseFeeTypes.Count;

                result.CaseFeeTypes = result.CaseFeeTypes.Skip(start).Take(model.SearchCondition.PageSize).ToList();

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
        [CheckUserLogin]
        public JsonResult CaseFeeTypeCreateUpdate(CaseFeeTypeModel model)
        {
            var response = new PostResponse();

            var result = CaseFeeTypeService.Instance.CreateCaseFeeType(model.CaseFeeType,model.IsNew);
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

        #region 案件阶段

        /// <summary>
        /// 
        /// </summary>
        /// <param name="casePhaseId"></param>
        /// <returns></returns>
         [CheckUserLogin]
        public ActionResult CasePhase(int? casePhaseId)
        {
            var model = new CasePhaseModel();

            if (casePhaseId.HasValue && casePhaseId.Value > -1)
            {
                model.CasePhase =
                    CaseTypeService.Instance.GetAllCasePhases()
                        .FirstOrDefault(x => x.CasePhaseId == casePhaseId.Value);
                model.CasePhaseId = casePhaseId.Value;
            }

            return PartialView(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
         [CheckUserLogin]
        public ActionResult CasePhaseList()
        {
            var model = new Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter.CasePhase.CasePhaseListModel();

            return View(model);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult CasePahseList(Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter.CasePhase.CasePhaseListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizCasePhaseSearchResultInfo();

                result.CasePhases = CaseTypeService.Instance.GetAllCasePhases();

                if (!string.IsNullOrEmpty(model.SearchCondition.CasePhaseName))
                {
                    result.CasePhases =
                        result.CasePhases.FindAll(x => x.CasePhaseName.Contains(model.SearchCondition.CasePhaseName));
                }

                int start = (model.SearchCondition.PageNo - 1)*model.SearchCondition.PageSize;

                result.TotalItemCount = result.CasePhases.Count;

                result.CasePhases = result.CasePhases.Skip(start).Take(model.SearchCondition.PageSize).ToList();

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
        [CheckUserLogin]
        public JsonResult CasePhaseCreateUpdate(CasePhaseModel model)
        {
            var response = new PostResponse();

            bool result = CasePhaseService.Instance.CasePhaseCreateUpdate(model.CasePhase);

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

        #region 代理公司
        [CheckUserLogin]
        public ActionResult Company()
        {
            var model = new CompanyModel();
            model.Company = CompanyService.Instance.GetCompany();
            return View(model);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult CompanyCreateUpdate(CompanyModel model)
        {
            var response = new PostResponse();
            
            bool result = CompanyService.Instance.CompanyCreateUpdate(model.Company);

            if (result)
            {
                response.Data = model.Company.CompanyId;
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

        #region 案件类型

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseTypeId"></param>
        /// <returns></returns>
        /// 
        [CheckUserLogin]
        public ActionResult CaseType(int? caseTypeId)
        {
            var model = new CaseTypeModel();

            if (caseTypeId.HasValue && caseTypeId.Value > -1)
            {
                model.CaseType =
                    CaseTypeService.Instance.GetAllCaseTypes()
                        .FirstOrDefault(x => x.CaseTypeId == caseTypeId.Value);
                model.CaseTypeId = caseTypeId.Value;
            }

            return PartialView(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
         [CheckUserLogin]
        public ActionResult CaseTypeList()
        {
            var model = new Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter.CaseType.CaseTypeListModel();

            return View(model);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CaseTypeList(Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter.CaseType.CaseTypeListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizCaseTypeSearchResultInfo();

                result.CaseTypes = CaseTypeService.Instance.GetAllCaseTypes();

                if (!string.IsNullOrEmpty(model.SearchCondition.CaseTypeName))
                {
                    result.CaseTypes =
                        result.CaseTypes.FindAll(x => x.CaseTypeName == model.SearchCondition.CaseTypeName);

                }

                int start = (model.SearchCondition.PageNo - 1) * model.SearchCondition.PageSize;

                result.TotalItemCount = result.CaseTypes.Count;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                result.CaseTypes = result.CaseTypes.Skip(start).Take(model.SearchCondition.PageSize).ToList();

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
        [CheckUserLogin]
        public JsonResult CaseTypeCreateUpdate(CaseTypeModel model)
        {
            var response = new PostResponse();

            bool result = CaseTypeService.Instance.CaseTypeCreateUpdate(model.CaseType);

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
        /// 案件关联阶段 列表显示
        /// </summary>
        /// <param name="caseTypeId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult CaseTypeCasePhaseList(int caseTypeId)
        {
            var model = new Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter.CaseType.CasePhaseListModel();

            model.CasePhasesAll = CaseTypeService.Instance.GetAllCasePhases();
            model.CasePhases = CaseTypeService.Instance.GetCasePahses(caseTypeId);

            return PartialView(model);
        }

        /// <summary>
        /// 案件关联阶段 保存
        /// </summary>
        /// <param name="caseTypeId"></param>
        /// <param name="casePhaseIds"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult CaseTypeCasePhaseCreate(int caseTypeId, int[] casePhaseIds)
        {
            var response = new PostResponse();
            CaseTypeService.Instance.CaseTypeCasePhaseBound(caseTypeId, casePhaseIds.ToList());

            response.Data = "";
            response.IsSuccess = true;
            return Json(response);
        }

        #endregion

        #region 法院
        /// <summary>
        /// 
        /// </summary>
        /// <param name="courtId"></param>
        /// <returns></returns>
        /// 
        [CheckUserLogin]
        public ActionResult Court(int? courtId)
        {
            var model = new CourtModel();

            if (courtId.HasValue && courtId.Value > 0)
            {
                model.Court =
                    CourtService.Instance.GetCourt(courtId.Value);

            }

            return PartialView(model);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult CourtCreateUpdate(CourtModel model)
        {
            var response = new PostResponse();

            bool result = CourtService.Instance.CreateUpdate(model.Court);

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
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CourtList()
        {
            var model = new CourtListModel();

            return View(model);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CourtList(CourtListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizCourtSearchResultInfo();

                result.Courts = CourtService.Instance.GetCourts(model.SearchCondition);

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

        #endregion

        #region 案由
        /// <summary>
        /// 
        /// </summary>
        /// <param name="causeId"></param>
        /// <returns></returns>
        /// 
        [CheckUserLogin]
        public ActionResult Cause(int? causeId)
        {
            var model = new CauseModel();

            if (causeId.HasValue && causeId.Value > 0)
            {
                model.Cause =
                    CauseService.Instance.GetCause(causeId.Value);

            }

            return PartialView(model);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult CauseCreateUpdate(CauseModel model)
        {
            var response = new PostResponse();

            bool result = CauseService.Instance.CreateUpdate(model.Cause);

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
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CauseList()
        {
            var model = new CauseListModel();

            return View(model);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CauseList(CauseListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizCauseSearchResultInfo();

                result.Causes = CauseService.Instance.GetCauses(model.SearchCondition);

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

        #endregion

        #region  付款类型

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentTypeList()
        {
            var model = new PaymentTypeListModel();

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFeeTypeId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult PaymentType(int? paymentTypeId)
        {
            var model = new PaymentTypeModel();

            if (paymentTypeId.HasValue && paymentTypeId.Value > -1)
            {
                model.PaymentType = PaymentTypeService.Instance.GetPaymentTypeById(paymentTypeId.Value);
            }
            else
            {
                model.PaymentType = new BizPaymentType();
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
        public JsonResult PaymentTypeCreateUpdate(PaymentTypeModel model)
        {
            var response = new PostResponse();
            var result = PaymentTypeService.Instance.CreateUpdatePaymentType(model.PaymentType);
            if (result)
            {
                response.Data = new { PaymentType = model.PaymentType };
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
        [CheckUserLogin]
        public JsonResult PaymentTypeList(PaymentTypeListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new Dchien.Legal.BizModel.FAM.AP.Payment.BizPaymentTypeSearchResultInfo();

                result.PaymentTypeList = PaymentTypeService.Instance.GetPaymentTypeList(model.SearchCondition);

                int start = (model.SearchCondition.PageNo - 1) * model.SearchCondition.PageSize;

                result.TotalItemCount = result.PaymentTypeList.Count;

                result.PaymentTypeList = result.PaymentTypeList.Skip(start).Take(model.SearchCondition.PageSize).ToList();

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
        [CheckUserLogin]
        public JsonResult GetPaymentTypeList(string keyword)
        {
            var response = new PostResponse();

            try
            {
                var searchCondition = new Entity.FAM.AP.Payment.PaymentTypeSearchCondition();
                searchCondition.OrganizationName = keyword;
                var paymentTypeList = PaymentTypeService.Instance.GetPaymentTypeList(searchCondition);
 
                response.IsSuccess = true;
                response.Data = new { PaymentTypeList = paymentTypeList};
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message + " || " + ex.StackTrace;
            }
            return Json(response);
        }


        #endregion

        #region 省市

        [HttpPost]
        [CheckUserLogin]
        public JsonResult DistrictList(string keyWord, string parentDistrictCode)
        {
            var response = new PostResponse();

            try
            {
                var list = DistrictService.Instance.GetAllDistricts();
                response.Data = list.FindAll(x => x.DistrictName.Contains(keyWord));
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        #endregion
    }
}
