using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.BizModel.FAS.AR.CaseFee;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FAS.AR.CaseFee;
using Dchien.Legal.Service.FAS.AR;
using Dchien.Legal.Service.FAS.AR.CaseFee;
using Dchien.Legal.Web.Areas.FAS.ViewModels.Cashed;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using RegisterModel = Dchien.Legal.Web.Areas.FAS.ViewModels.Cashed.RegisterModel;

namespace Dchien.Legal.Web.Areas.FAS.Controllers
{
    [CheckUserLogin]
    public class CashedController : Controller
    {
        internal Log Logger = new Log("FAS.Controllers.CashedController");

        #region 到账列表

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult List()
        {
            var indexModel = new ListModel();

            indexModel.CashedSearchCondition = new CaseFeeCashedSearchCondition();
            indexModel.CashedSearchCondition.PageNo = 1;
            indexModel.CashedSearchCondition.PageSize = 20;

            return View(indexModel);
        }

        [CheckUserLogin]
        [HttpPost]
        public JsonResult List(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.CashedSearchCondition.PageNo == 0)
                    model.CashedSearchCondition.PageNo = 1;
                if (model.CashedSearchCondition.PageSize == 0)
                    model.CashedSearchCondition.PageSize = 20;

                var result = new BizCaseFeeCashedSearchResultInfo();

                result.CashedList = CaseFeeCashedService.Instance.GetCashedList(model.CashedSearchCondition);

                result.TotalItemCount = model.CashedSearchCondition.TotalCount;
                result.PageNo = model.CashedSearchCondition.PageNo;
                result.PageSize = model.CashedSearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error("CashedController.List", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        #endregion

        #region 登记到账

        [CheckUserLogin]
        public ActionResult Register()
        {
            var model = new RegisterModel();
            model.CashedList = new List<BizCaseFeeCashed>();
            model.CashedList.Add(new BizCaseFeeCashed() { CashedDate = DateTime.Now });
            return PartialView(model);
        }

        [HttpPost]
        public JsonResult CashedRegister(RegisterModel model)
        {
            var response = new PostResponse();

            try
            {
                bool result = CaseFeeCashedService.Instance.CashedRegister(model.CashedList);

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

        #region 到账分配
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult Index()
        {
            var indexModel = new IndexModel();

            indexModel.Cashed = new BizCaseFeeCashed();
            indexModel.CashedSearchCondition = new CaseFeeCashedSearchCondition();
            indexModel.CashedSearchCondition.PageNo = 1;
            indexModel.CashedSearchCondition.PageSize = 20;

            indexModel.CashUnsettledSearchCondition = new CaseFeeSearchCondition();
            indexModel.CashUnsettledSearchCondition.PageNo = 1;
            indexModel.CashUnsettledSearchCondition.PageSize = 20;

            return View(indexModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CashedList(CaseFeeCashedSearchCondition search)
        {
            var model = new CashedListModel();

            if (search == null)
            {
                model.CashedSearchCondition = new CaseFeeCashedSearchCondition();
                model.CashedSearchCondition.PageNo = 1;
                model.CashedSearchCondition.PageSize = 20;
            }
            else
            {
                model.CashedSearchCondition = search;
                model.CashedSearchCondition.PageNo = model.CashedSearchCondition.PageNo > 0 ? model.CashedSearchCondition.PageNo : 1;
                model.CashedSearchCondition.PageSize = model.CashedSearchCondition.PageSize > 0 ? model.CashedSearchCondition.PageSize : 20; ;
            }

            model.CashedSearchCondition.NonApplied = true;

            if (!string.IsNullOrEmpty(model.CashedSearchCondition.CustomerNo))
            {
                model.CashedList = CaseFeeCashedService.Instance.GetCashedList(search);
            }
            else
            {
                model.CashedList = new List<BizCaseFeeCashed>();
            }

            return PartialView("PartialView/CashedList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CashUnsettledList(CaseFeeSearchCondition search)
        {
            var model = new CashUnsettledListModel();

            if (search == null)
            {
                model.CashUnsettledSearchCondition = new CaseFeeSearchCondition();
                model.CashUnsettledSearchCondition.PageNo = 1;
                model.CashUnsettledSearchCondition.PageSize = 20;
            }
            else
            {
                model.CashUnsettledSearchCondition = search;
                model.CashUnsettledSearchCondition.PageNo = model.CashUnsettledSearchCondition.PageNo > 0 ? model.CashUnsettledSearchCondition.PageNo : 1;
                model.CashUnsettledSearchCondition.PageSize = model.CashUnsettledSearchCondition.PageSize > 0 ? model.CashUnsettledSearchCondition.PageSize : 20; ;
            }

            if (!string.IsNullOrEmpty(model.CashUnsettledSearchCondition.CustomerNo))
            {
                model.CashUnsettledList = CaseFeeCashedService.Instance.GetCashUnsettledList(search);
            }
            else
            {
                model.CashUnsettledList = new List<BizCaseFee>();
            }

            return PartialView("PartialView/CashUnsettledList", model);
        }

        /// <summary>
        /// 分配
        /// </summary>
        /// <param name="cashedId"></param>
        /// <param name="caseFeeIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CashedApply(long cashedId, List<long> caseFeeIds )
        {
            var response = new PostResponse();

            try
            {
                var cashedFee = CaseFeeCashedService.Instance.GetCashedById(cashedId);

                if (cashedFee == null) throw new ApplicationException("未找到对应的到账信息.");

                if ((cashedFee.Amount - (cashedFee.AppliedAmount.HasValue ? cashedFee.AppliedAmount.Value : 0)) <= 0)
                {
                    throw new ApplicationException("所选到账金额已全部分配完.");
                }

                var caseFeeList = CaseFeeCashedService.Instance.GetCashUnsettledList(caseFeeIds);

                if (!caseFeeIds.Any())
                {
                    throw new ApplicationException("所选未分配费用信息已全部到账，无需再分配.");
                }

                if (caseFeeList.Count > 1 && (cashedFee.Amount - cashedFee.AppliedAmount) < caseFeeList.Sum(x => x.Amount - (x.CashedAmount.HasValue ? x.CashedAmount.Value : 0)))
                {
                    throw new ApplicationException(string.Format("到账金额{0}小余所选未分配费用总金额{1}.", cashedFee.Amount - cashedFee.AppliedAmount, caseFeeList.Sum(x => x.Amount - (x.CashedAmount.HasValue ? x.CashedAmount.Value : 0))));
                }

                //确认到账
                bool result = CaseFeeCashedService.Instance.CashedApply(cashedFee, caseFeeList);

                if (result)
                {
                    response.Message = "分配成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "分配失败！";
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

        #region 历史查询
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult History()
        {
            var indexModel = new IndexHistoryModel();

            indexModel.SearchCondition = new CaseFeeCashedSearchCondition();
            indexModel.SearchCondition.PageNo = 1;
            indexModel.SearchCondition.PageSize = 20;


            return View(indexModel);
        }

        [CheckUserLogin]
        [HttpPost]
        public JsonResult HistoryList(IndexHistoryModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 20;

                var result = new BizCaseFeeCashedSearchResultInfo();

                result.CashedList = CaseFeeCashedService.Instance.GetCashedList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error("CashedController.HistoryList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }
 

        /// <summary>
        /// 
        /// </summary>
        /// <param name="cashedId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
        public ActionResult AppliedList(long cashedId)
        {
            var model = new CaseFeeAppliedListModel();

            //model.CashedId = cashedId;
            model.SearchCondition = new CaseFeeAppliedSearchCondition();
            model.SearchCondition.CashedId = cashedId;
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 20;

            return PartialView("PartialView/AppliedList",model);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult GetAppliedList(CaseFeeAppliedListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 20;

                var result = new BizAppliedSearchResultInfo();

                result.AppliedList = CaseFeeAppliedService.Instance.GetCaseFeeAppliedList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error("CashedController.GetAppliedList", ex);

                response.IsSuccess = false;
                response.Message = "查询分配记录失败.";
            }
            return Json(response);
        }


        /// <summary>
        /// 取消到账分配
        /// </summary>
        /// <param name="appliedIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult AppliedCancel(List<long> appliedIds)
        {
            var response = new PostResponse();

            try
            {
                var caseFeeAppliedList = CaseFeeAppliedService.Instance.GetCaseFeeAppliedList(appliedIds);

                if (caseFeeAppliedList == null || !caseFeeAppliedList.Any())
                {
                    throw new ApplicationException("未找到到账分配记录.");
                }

                //foreach (var caseFeeApplied in caseFeeAppliedList)
                //{
                //    var caseFee = Dchien.Legal.Service.FAS.AR.CaseFee.CaseFeeService.Instance.GetCaseFeeByCaseFeeId(caseFeeApplied.CaseFeeId);
                        
                //    if (caseFee != null )
                //    {
                //        if (caseFee.Invoice != null && !string.IsNullOrEmpty(caseFee.Invoice.InvoiceNo))
                //        {
                //            throw new ApplicationException(string.Format("案件号{0},{1}费用存在票据,请先取消票据.", caseFee.CaseNo, caseFee.CaseFeeTypeName));
                //        }
                //        var apCaseFeeList = Dchien.Legal.Service.FAS.AP.CaseFee.CaseFeeService.Instance.GetCaseFeeListByARCaseFeeId(caseFeeApplied.CaseFeeId);

                //        if (apCaseFeeList != null && apCaseFeeList.Any(f => f.Invoice != null && !string.IsNullOrEmpty(f.Invoice.InvoiceNo)))
                //        {
                //            throw new ApplicationException(string.Format("案件号{0},{1}费用的案源或代理费付款凭证已上传,请先取消付款凭证.", caseFee.CaseNo, caseFee.CaseFeeTypeName));
                //        }
                //    }
                //}


                //确认到账
                bool result = CaseFeeAppliedService.Instance.AppliedCancel(caseFeeAppliedList);

                if (result)
                {
                    response.Message = "取消到账分配成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "取消到账分配失败！";
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
    }
}
