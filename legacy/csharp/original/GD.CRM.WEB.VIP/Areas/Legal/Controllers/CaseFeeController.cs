using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;

using Dchien.Legal.Common;
using Dchien.Legal.Web.Areas.Legal.ViewModels.CaseFee;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Service.FAM.AR.CaseFee;
using Dchien.Legal.Web.Models;

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
                caseModel.CaseFeeList =
                    CaseFeeService.Instance.GetCaseFeeListByCaseId(caseId);
                caseModel.TotalCount = caseModel.CaseFeeList.Count;
                caseModel.CaseFeeList = caseModel.CaseFeeList.Any()
                    ? caseModel.CaseFeeList.Skip(caseModel.PageSize * (caseModel.PageNo - 1))
                        .Take(caseModel.PageSize)
                        .ToList()
                    : new List<Dchien.Legal.BizModel.FAM.AR.CaseFee.BizCaseFee>();
            }
            return PartialView("PartialView/CaseFeeList", caseModel);
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
        public JsonResult RefoundAmountCreateUpdate(long caseFeeId,decimal refundAmount)
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
    }
}
