using System;
using System.Web.Mvc;
using System.Linq;

using Dchien.Legal.BizModel.System;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FCM.Contract;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Service;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Web.Areas.FCM.ViewModels.AR;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using System.Collections.Generic;

namespace Dchien.Legal.Web.Areas.FCM.Controllers
{
    [CheckUserLogin]
    public class ARController : Controller
    {
        internal Log Logger = new Log("FCM.Controllers.ARController");
 
        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult List(int id)
        {
            var menus = MenuService.Instance.GetMenusByCurrentUser();

            if ((id.ToString() == PageId.PageId_4001009
               || id.ToString() == PageId.PageId_4001010
               || id.ToString() == PageId.PageId_4001011)

              && menus.Any(x => x.MenuCode == id.ToString()))
            {
                var model = new ListModel();

                model.SearchCondition = new ContractSearchCondition();
                model.SearchCondition.PageNo = 1;
                model.SearchCondition.PageSize = 15;
                model.SearchCondition.PageId = id.ToString();

                return View(model);
            }
            else
            {
                return new RedirectResult("~/NoPermission.html?" + id.ToString());
            }
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
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

                if (model.SearchCondition.PageId == PageId.PageId_4001009)
                {
                    model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_4001010)
                {
                    model.SearchCondition.DepartmentId = LoginHelper.GetDepartmentId();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_4001011)
                {
                    model.SearchCondition.CompanyId = LoginHelper.GetCompanyId();
                }

                model.SearchCondition.TotalAmountFrom = 0;

                var result = new BizContractSearchResultInfo();

                result.ContractList = ContractService.Instance.GetContractARList(model.SearchCondition);

                result.TotalPaidCaseOfficeFeeAmount = model.SearchCondition.TotalPaidCaseOfficeFeeAmount;
                result.TotalCashedCaseOfficeFeeAmount = model.SearchCondition.TotalCashedCaseOfficeFeeAmount;
                result.TotalUnCashedCaseOfficeFeeAmount = model.SearchCondition.TotalUnCashedCaseOfficeFeeAmount;
                result.TotalDeficitCaseOfficeFeeAmount = model.SearchCondition.TotalDeficitCaseOfficeFeeAmount;
                result.TotalCaseNonOfficeFeeAmount = model.SearchCondition.TotalCaseNonOfficeFeeAmount;
                result.TotalCashedCaseNonOfficeFeeAmount = model.SearchCondition.TotalCashedCaseNonOfficeFeeAmount;
                result.TotalUnCashedCaseNonOfficeFeeAmount = model.SearchCondition.TotalUnCashedCaseNonOfficeFeeAmount;
                result.TotalCaseCommissionFeeAmount = model.SearchCondition.TotalCaseCommissionFeeAmount;
                result.TotalCashedCaseCommissionFeeAmount = model.SearchCondition.TotalCashedCaseCommissionFeeAmount;
                result.TotalPaidCaseCommissionFeeAmount = model.SearchCondition.TotalPaidCaseCommissionFeeAmount;
                result.TotalUnPaidCaseCommissionFeeAmount = model.SearchCondition.TotalUnPaidCaseCommissionFeeAmount;
                result.TotalInvoicedAmount = model.SearchCondition.TotalInvoicedAmount;
                result.TotalInvoiceOverAmount = model.SearchCondition.TotalInvoiceOverAmount;
                result.TotalUnInvoicedAmount = model.SearchCondition.TotalUnInvoicedAmount;

                result.TotalItemCount = model.SearchCondition.TotalCount;

                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"ARController.List","ARController.List", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ItemList(string id, 
            string contractNo, 
            decimal? paidCaseOfficeFeeAmount, 
            decimal? cashedCaseOfficeFeeAmount,
            decimal? unCashedCaseOfficeFeeAmount,
            decimal? deficitCaseOfficeFeeAmount, 
            decimal? caseNonOfficeFeeAmount,
            decimal? cashedCaseNonOfficeFeeAmount,
            decimal? unCashedCaseNonOfficeFeeAmount)
        {
            var model = new ItemListModel();

            model.SearchCondition = new ContractSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 10;

            if (!string.IsNullOrEmpty(contractNo))
            {
                model.SearchCondition.ContractNo = contractNo;
            }
            if (paidCaseOfficeFeeAmount.HasValue)
            {
                model.SearchCondition.CaseFeeTypeId = "1,11010010,11010020,11010030,11010040,11010050,11010060,11010070,11010090,11010140,11010150,11010160,11010190,11010200";
                model.SearchCondition.CaseFeeTypeName = "官费,差旅费,一审诉讼费,二审诉讼费,再审诉讼费,公证费,调解金额,判决金额,保全费,公告费,担保费,鉴定费,执行费,公证服务费";
            }
            if (cashedCaseOfficeFeeAmount.HasValue)
            {
                model.SearchCondition.CaseFeeTypeId = "1,11010010,11010020,11010030,11010040,11010050,11010060,11010070,11010090,11010140,11010150,11010160,11010190,11010200";
                model.SearchCondition.CaseFeeTypeName = "官费,差旅费,一审诉讼费,二审诉讼费,再审诉讼费,公证费,调解金额,判决金额,保全费,公告费,担保费,鉴定费,执行费,公证服务费";
            }
            if (unCashedCaseOfficeFeeAmount.HasValue)
            {
                model.SearchCondition.CaseFeeTypeId = "1,11010010,11010020,11010030,11010040,11010050,11010060,11010070,11010090,11010140,11010150,11010160,11010190,11010200";
                model.SearchCondition.CaseFeeTypeName = "官费,差旅费,一审诉讼费,二审诉讼费,再审诉讼费,公证费,调解金额,判决金额,保全费,公告费,担保费,鉴定费,执行费,公证服务费";
            }
            if (deficitCaseOfficeFeeAmount.HasValue)
            {
                model.SearchCondition.CaseFeeTypeId = "1,11010010,11010020,11010030,11010040,11010050,11010060,11010070,11010090,11010140,11010150,11010160,11010190,11010200";
                model.SearchCondition.CaseFeeTypeName = "官费,差旅费,一审诉讼费,二审诉讼费,再审诉讼费,公证费,调解金额,判决金额,保全费,公告费,担保费,鉴定费,执行费,公证服务费";
                model.SearchCondition.CasePhaseId = "106018";
                model.SearchCondition.CasePhaseName = "亏损归档";
            }
            if (caseNonOfficeFeeAmount.HasValue)
            {
                model.SearchCondition.CaseFeeTypeId = "2,11020010,11020020,11020030,11020040,11020065";
                model.SearchCondition.CaseFeeTypeName = "代理费,律师代理费,律师咨询费,律师培训费,律师见证费,核定成本";
            }
            if (cashedCaseNonOfficeFeeAmount.HasValue)
            {
                model.SearchCondition.CaseFeeTypeId = "2,11020010,11020020,11020030,11020040,11020065";
                model.SearchCondition.CaseFeeTypeName = "代理费,律师代理费,律师咨询费,律师培训费,律师见证费,核定成本";
            }
            if (unCashedCaseNonOfficeFeeAmount.HasValue)
            {
                model.SearchCondition.CaseFeeTypeId = "2,11020010,11020020,11020030,11020040,11020065";
                model.SearchCondition.CaseFeeTypeName = "代理费,律师代理费,律师咨询费,律师培训费,律师见证费,核定成本";
            }

            model.SearchCondition.PageId = id;

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult ItemList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 10;

                model.SearchCondition.TotalAmountFrom = 0;

                var result = new BizContractSearchResultInfo();

                result.ContractList = ContractService.Instance.GetContractARItemList(model.SearchCondition);
                result.TotalPaidCaseOfficeFeeAmount = model.SearchCondition.TotalPaidCaseOfficeFeeAmount;
                result.TotalCashedCaseOfficeFeeAmount = model.SearchCondition.TotalCashedCaseOfficeFeeAmount;
                result.TotalUnCashedCaseOfficeFeeAmount = model.SearchCondition.TotalUnCashedCaseOfficeFeeAmount;
                result.TotalDeficitCaseOfficeFeeAmount = model.SearchCondition.TotalDeficitCaseOfficeFeeAmount;
                result.TotalCaseNonOfficeFeeAmount = model.SearchCondition.TotalCaseNonOfficeFeeAmount;
                result.TotalCashedCaseNonOfficeFeeAmount = model.SearchCondition.TotalCashedCaseNonOfficeFeeAmount;
                result.TotalUnCashedCaseNonOfficeFeeAmount = model.SearchCondition.TotalUnCashedCaseNonOfficeFeeAmount;
                result.TotalCaseCommissionFeeAmount = model.SearchCondition.TotalCaseCommissionFeeAmount;
                result.TotalCashedCaseCommissionFeeAmount = model.SearchCondition.TotalCashedCaseCommissionFeeAmount;
                result.TotalPaidCaseCommissionFeeAmount = model.SearchCondition.TotalPaidCaseCommissionFeeAmount;
                result.TotalUnPaidCaseCommissionFeeAmount = model.SearchCondition.TotalUnPaidCaseCommissionFeeAmount;
                result.TotalInvoicedAmount = model.SearchCondition.TotalInvoicedAmount;
                result.TotalInvoiceOverAmount = model.SearchCondition.TotalInvoiceOverAmount;
                result.TotalUnInvoicedAmount = model.SearchCondition.TotalUnInvoicedAmount;

                result.TotalItemCount = model.SearchCondition.TotalCount;

                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ARController.ItemList", "ARController.ItemList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }
  
    }
}
