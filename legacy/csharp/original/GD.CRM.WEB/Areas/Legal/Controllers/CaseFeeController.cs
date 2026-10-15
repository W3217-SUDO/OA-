using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;

using Dchien.Legal.Common;
using Dchien.Legal.Web.Areas.Legal.ViewModels.CaseFee;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Service.FAM.AR.CaseFee;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.BizModel.HR;
using System.Configuration;
using Dchien.Legal.Service.HR.Staff;
using Dchien.Legal.BizModel.FAM.AR.CaseFee;

namespace Dchien.Legal.Web.Areas.Legal.Controllers
{
    [CheckUserLogin]
    public class CaseFeeController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.CaseFeeController");

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
                caseModel.CaseFeeList =  CaseFeeService.Instance.GetCaseFeeListByCaseId(caseId);
                caseModel.TotalCount = caseModel.CaseFeeList.Where(x => x.GroupId == (int)GroupId.Lawfirm).Count();
                caseModel.CaseFeeList = caseModel.CaseFeeList.Any(x => x.GroupId == (int)GroupId.Lawfirm)
                    ? caseModel.CaseFeeList.Where(x => x.GroupId == (int)GroupId.Lawfirm).Skip(caseModel.PageSize * (caseModel.PageNo - 1))
                        .Take(caseModel.PageSize)
                        .ToList()
                    : new List<Dchien.Legal.BizModel.FAM.AR.CaseFee.BizCaseFee>();
            }
            return PartialView("PartialView/CaseFeeList", caseModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>

        [HttpPost]
        public ActionResult TradFeeList(long caseId, int? pageNo, int? pageSize)
        {
            var caseModel = new CaseFeeListModel();
            caseModel.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            caseModel.PageSize = pageSize.HasValue ? pageSize.Value : 15;
            if (caseId > 0)
            {
                caseModel.CaseId = caseId;
                caseModel.CaseFeeList = CaseFeeService.Instance.GetCaseFeeListByCaseId(caseId);
                caseModel.TotalCount = caseModel.CaseFeeList.Where(x => x.GroupId == (int)GroupId.Trad).Count();
                caseModel.CaseFeeList = caseModel.CaseFeeList.Any(x=>x.GroupId == (int)GroupId.Trad)
                    ? caseModel.CaseFeeList.Where(x => x.GroupId == (int)GroupId.Trad).Skip(caseModel.PageSize * (caseModel.PageNo - 1))
                        .Take(caseModel.PageSize)
                        .ToList()
                    : new List<Dchien.Legal.BizModel.FAM.AR.CaseFee.BizCaseFee>();
            }
            return PartialView("PartialView/TradFeeList", caseModel);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult Create(string customerNo,string contractNo)
        {
            var model = new CaseFeeModel();
            model.CustomerNo = customerNo;
            model.CaseFee = new BizModel.FAM.AR.CaseFee.BizCaseFee();
            model.CaseFee.ContractNo = contractNo;

            return PartialView("PartialView/Create", model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFeeId"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult Edit(long caseFeeId)
        {
            var caseFee = CaseFeeService.Instance.GetCaseFeeByCaseFeeId(caseFeeId);
            var caseModel = new CaseFeeModel();

            caseModel.CaseFee = caseFee;
            caseModel.CustomerNo = caseFee.CustomerNo;

            return PartialView("PartialView/Edit", caseModel);
        }

        [HttpPost]
        public ActionResult RefundAmount(long caseFeeId)
        {
            var caseFee = CaseFeeService.Instance.GetCaseFeeByCaseFeeId(caseFeeId);
            var caseModel = new CaseFeeModel();

            caseModel.CaseFee = caseFee;
            caseModel.CustomerNo = caseFee.CustomerNo;

            return PartialView("PartialView/RefundAmount", caseModel);
        }

        [HttpPost]
        public JsonResult RefundAmountCreateUpdate(long caseFeeId,decimal refundAmount)
        {
            var response = new PostResponse();

            try
            {
                bool result = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.CaseFeeRefundAmountCreateUpdate(caseFeeId, refundAmount);

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


        #region 批量新建

        [CheckUserLogin]
        public ActionResult MultiCreate(int feeTypeId, string caseNos)
        {
            ViewBag.FeeTypeId = feeTypeId;
            return PartialView("PartialView/MultiCreate");
        }

        [CheckUserLogin]
        public ActionResult TradFeeCreate(int feeTypeId, string caseNos)
        {
            ViewBag.FeeTypeId = feeTypeId;
            return PartialView("PartialView/TradFeeCreate");
        }


        [HttpPost]
        [CheckUserLogin]
        public JsonResult GetCaseFeeListByCaseFeeIds(List<long> caseFeeIds)
        {
            var response = new PostResponse();

            try
            {
                var caseFeeList = CaseFeeService.Instance.GetCaseFeeListByCaseFeeIds(caseFeeIds);

                response.IsSuccess = true;
                response.Data = new { CaseFeeList = caseFeeList };

            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = "获取出错.";
            }
            return Json(response);
        }


        [HttpPost]
        [CheckUserLogin]
        public JsonResult GetCaseFeesByCaseFeeIds(List<long> caseFeeIds)
        {
            var response = new PostResponse();

            try
            {
                var caseFeeList = CaseFeeService.Instance.GetCaseFeeListByCaseFeeIds(caseFeeIds);
                var staffPerformanceList = new List<Tuple<string, List<BizStaffPerformance>,decimal, decimal,decimal,decimal>>();
                if (caseFeeList != null && caseFeeList.Any())
                {
                    var caseFees = CaseFeeService.Instance.GetCaseFeeListByCaseIds(caseFeeList.Select(x => x.CaseId).ToList());
                    decimal? invoiceOverAmount = 0;
                    decimal? costOverAmount = 0;
                    decimal? baseAmount = caseFeeList.Sum(x=>x.Amount.Value);
                    caseFeeList.ForEach(c =>
                    {
                        //baseAmount = c.Amount.Value;
                        var refundAmount = caseFees.FindAll(x => x.CaseNo == c.CaseNo).Sum(x => x.RefundAmount.Value - x.RefundedAmount.Value);

                        if (c.GroupId == (int)GroupId.Lawfirm)
                        {
                            invoiceOverAmount = caseFees.FindAll(x => x.CaseNo == c.CaseNo && c.GroupId == x.GroupId).Sum(x => x.InvoicedAmount) -
                                                  caseFees.FindAll(x => x.CaseNo == c.CaseNo && c.GroupId == x.GroupId && (x.CaseFeeTypeId == (int)CaseFeeType.FeeType_11020010 || x.CaseTypeId == (int)CaseFeeType.FeeType_11020050)).Sum(x => x.CashedAmount);
                            costOverAmount = invoiceOverAmount.Value <= 0 ? 0 : (invoiceOverAmount.Value * (decimal)Convert.ToDecimal(ConfigurationManager.AppSettings["InvoiceOverAmountRate"])) / 100;
                        }
                        var staffNames = new List<string>();
                        if (!string.IsNullOrEmpty(c.Parent.Basic.CourtLawyer))
                        {
                            staffNames.AddRange(c.Parent.Basic.CourtLawyer.Split(',').ToList());
                        }
                        if (!string.IsNullOrEmpty(c.Parent.Basic.CaseLawyer))
                        {
                            staffNames.AddRange(c.Parent.Basic.CaseLawyer.Split(',').ToList());
                        }
                        if (!string.IsNullOrEmpty(c.Parent.Basic.CaseAssistant))
                        {
                            staffNames.AddRange(c.Parent.Basic.CaseAssistant.Split(',').ToList());
                        }
                        if (!string.IsNullOrEmpty(c.Parent.Basic.BusinessOwner))
                        {
                            staffNames.AddRange(c.Parent.Basic.BusinessOwner.Split(',').ToList());
                        }
                        if (!string.IsNullOrEmpty(c.Parent.Basic.Coordinator))
                        {
                            staffNames.AddRange(c.Parent.Basic.Coordinator.Split(',').ToList());
                        }
                        if (!string.IsNullOrEmpty(c.Parent.Basic.Investigator))
                        {
                            staffNames.AddRange(c.Parent.Basic.Investigator.Split(',').ToList());
                        }
                        if (string.IsNullOrEmpty(c.Parent.Basic.ArchivedFileNo) && ConfigurationManager.AppSettings["AppId"] == "10000001002")
                        {
                            c.Parent.Basic.ArchivedFileNo = DateTime.Now.ToString("yyyyMMddHHmmssfffff");
                        }
                        var performanceList = StaffPerformanceService.Instance.GetStaffPerformanceList(staffNames, c.Parent.Basic.CaseRegisterDate.Value);

                        if (!staffPerformanceList.Any(x => x.Item1 == c.Parent.Basic.CaseNo))
                        {
                            staffPerformanceList.Add(new Tuple<string, List<BizStaffPerformance>, decimal, decimal, decimal,decimal>(
                            c.Parent.Basic.CaseNo,
                            performanceList,
                            refundAmount,
                            invoiceOverAmount.HasValue ? invoiceOverAmount.Value : 0,
                            costOverAmount.HasValue ? costOverAmount.Value : 0,
                            baseAmount.Value - costOverAmount.Value));
                        }
                    });
                }
                response.IsSuccess = true;
                response.Data = new { CaseFeeList = new List<BizCaseFee> { caseFeeList[0] }, PerformanceList = staffPerformanceList };
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = "获取出错.";
            }
            return Json(response);
        }


        #endregion


        [HttpPost]
        public JsonResult CaseFeeDelete(long caseFeeId)
        {
            var response = new PostResponse();

            try
            {
                bool result = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.CaseFeeDelete(caseFeeId);

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

            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFeeId"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult RefundStatus(List<long> caseFeeIds)
        {
            return PartialView("PartialView/RefundStatus");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFeeId"></param>
        /// <param name="refundAmount"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult RefundStatusChange(List<long> caseFeeIds, int refundStatus)
        {
            var response = new PostResponse();
            try
            {
                bool result = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.RefundStatusChange(caseFeeIds, refundStatus);
                if (result)
                {
                    response.Message = "修改成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "修改失败！";
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
    }
}
