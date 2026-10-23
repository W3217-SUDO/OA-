using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using System.Web.UI.WebControls;
using System;
using System.Text;
using System.Web;
using System.Web.UI;
using System.IO;

using Dchien.Legal.Service;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Common;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.FCM.Contract;

using Dchien.Legal.Entity.System;
using Dchien.Legal.BizModel.FAM.AR.CaseFee;
using Dchien.Legal.Service.FAM.AR.CaseFee;
using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.Entity.FAM.AR.ReceivedPayment;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class CaseFeeController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.CaseFeeController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFeeList(Dchien.Legal.Entity.FAM.AR.CaseFee.CaseFeeSearchCondition searchCondition)
        {
            var response = new PostResponse();
            try
            {
                if (searchCondition.PageNo == 0)
                    searchCondition.PageNo = 1;
                if (searchCondition.PageSize == 0)
                    searchCondition.PageSize = 15;

                if (searchCondition.PageId == Entity.System.PageId.PageId_5001010001 
                    || searchCondition.PageId == Entity.System.PageId.PageId_5001010002
                    || searchCondition.PageId == Entity.System.PageId.PageId_5001010003
                    || searchCondition.PageId == Entity.System.PageId.PageId_5001010)
                {
                    searchCondition.GroupId  = (int)GroupId.Lawfirm;
                }
                else if (searchCondition.PageId == Entity.System.PageId.PageId_50001010001
                    || searchCondition.PageId == Entity.System.PageId.PageId_50001010002
                    || searchCondition.PageId == Entity.System.PageId.PageId_50001010003 
                    || searchCondition.PageId == Entity.System.PageId.PageId_50001010)
                {
                    searchCondition.GroupId = (int)GroupId.Trad;
                }

                if (searchCondition.PageId == Entity.System.PageId.PageId_5001004009)
                {
                    searchCondition.CaseFeeTypeId = "11020010,11020050";
                    searchCondition.HasUnSettlementFee = true;
                }

                if (searchCondition.PageId == Entity.System.PageId.PageId_5001010001 || searchCondition.PageId == Entity.System.PageId.PageId_50001010001)
                {
                    searchCondition.HasRefundFee = true;
                    searchCondition.CompanyId = LoginHelper.GetCompanyId();
                }
                else if (searchCondition.PageId == Entity.System.PageId.PageId_5001010003 || searchCondition.PageId == Entity.System.PageId.PageId_50001010003)
                {
                    searchCondition.HasRefundFee = true;
                    searchCondition.UserId = LoginHelper.GetUserName();
                }
                else if (searchCondition.PageId == Entity.System.PageId.PageId_5001010002 || searchCondition.PageId == Entity.System.PageId.PageId_50001010002)
                {
                    searchCondition.HasUnPaidOfficeFee = true;
                    searchCondition.UserId = LoginHelper.GetUserName();
                }
                else if (LoginHelper.GetAccesslevel() == (int)Dchien.Legal.Entity.Account.AccessLevel.All)
                {
                    searchCondition.CompanyId = LoginHelper.GetCompanyId();
                }
                else
                {
                    searchCondition.UserId = LoginHelper.GetUserName();
                }

                var result = new BizCaseFeeSearchResultInfo();
                result.CaseFeeList = CaseFeeService.Instance.GetCaseFeeList(searchCondition);
                result.TotalItemCount = searchCondition.TotalCount;
                result.PageNo = searchCondition.PageNo;
                result.PageSize = searchCondition.PageSize;
                result.TotalAmount = searchCondition.TotalAmount;
                result.TotalCashedAmount = searchCondition.TotalCashedAmount;
                result.TotalRefundAmount = searchCondition.TotalRefundAmount;
                result.TotalRefundedAmount = searchCondition.TotalRefundedAmount;
                result.TotalPaidAmount = searchCondition.TotalPaidAmount;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFeeController.CaseFeeList", "CaseFeeController.CaseFeeList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

  

        /// <summary>
        /// 
        /// </summary>
        /// <param name="searchCondition"></param>
        /// <returns></returns>
        public JsonResult CaseFeeListSelectedSettlemented(List<long> caseFeeIds)
        {
            var response = new PostResponse();
            try
            {
                response.IsSuccess = CaseFeeService.Instance.SettlementStatusChange(caseFeeIds, (int)SettlementStatus.Paid); 
                response.Message = "";
                return Json(response);
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFeeController.CaseFeeListSelectedSettlemented", "CaseFeeController.CaseFeeListSelectedSettlemented", ex);
                response.IsSuccess = false;
                response.Message = "标识提成发放出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        public ActionResult CaseFeeList(string id)
        {
            var listModel = new Dchien.Legal.Web.Areas.Legal.ViewModels.CaseFee.CaseFeeListModel();

            listModel.SearchCondition = new Entity.FAM.AR.CaseFee.CaseFeeSearchCondition();
            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 15;

            if (id == Entity.System.PageId.PageId_5001010001)
            {
                listModel.SearchCondition.HasRefundFee = true;
            }
            else if (id == Entity.System.PageId.PageId_5001010002)
            {
                listModel.SearchCondition.HasUnPaidOfficeFee = true;
            }

           return View("CaseFeeList", listModel);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        public ActionResult PendingSettlementCaseFeeList(string id)
        {
            var listModel = new Dchien.Legal.Web.Areas.Legal.ViewModels.CaseFee.CaseFeeListModel();
            listModel.SearchCondition = new Entity.FAM.AR.CaseFee.CaseFeeSearchCondition();
            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 15; 
            return View("PendingSettlementCaseFeeList", listModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        public ActionResult RefundCaseFeeList(string id)
        {
            var listModel = new Dchien.Legal.Web.Areas.Legal.ViewModels.CaseFee.CaseFeeListModel();
            listModel.SearchCondition = new Entity.FAM.AR.CaseFee.CaseFeeSearchCondition();
            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 15;
            listModel.SearchCondition.HasRefundFee = true;
            listModel.SearchCondition.Sorting = "T.RefundStatusStartTime";
            return View("RefundCaseFeeList", listModel);
        }

        public ActionResult RefundNotRequiredCaseFeeList(string id)
        {
            var listModel = new Dchien.Legal.Web.Areas.Legal.ViewModels.CaseFee.CaseFeeListModel();
            listModel.SearchCondition = new Entity.FAM.AR.CaseFee.CaseFeeSearchCondition();
            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 15;
            listModel.SearchCondition.HasRefundFee = false;
            listModel.SearchCondition.RefundStatus = (int)RefundStatus.R100;
            listModel.SearchCondition.Sorting = "T.RefundStatusStartTime desc";
            return View("RefundNotRequiredCaseFeeList", listModel);
        }

        [HttpPost]
        public ActionResult CaseFeeListAllExportToExcel(Dchien.Legal.Entity.FAM.AR.CaseFee.CaseFeeSearchCondition searchCondition)
        {
            searchCondition.PageSize = 100000;
            var CaseFees = CaseFeeService.Instance.GetCaseFeeList(searchCondition);
            var fileName = CaseFeeService.Instance.CaseFeeListSelectedExportToExcel(CaseFees);
            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = Path.GetFileNameWithoutExtension(fileName);
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="CaseFeeIds"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseFeeListSelectedExportToExcel(List<long> CaseFeeIds)
        {
            var CaseFees = CaseFeeService.Instance.GetCaseFeeListByCaseFeeIds(CaseFeeIds);
            var fileName = CaseFeeService.Instance.CaseFeeListSelectedExportToExcel(CaseFees);

            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = Path.GetFileNameWithoutExtension(fileName);
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="fileName"></param>
        /// <returns></returns>
        public ActionResult CaseFeeListExportToExcelDownload(string fileName)
        {
            // 设置编码和附件格式  
            Response.Charset = "gb2312";
            Response.ContentEncoding = Encoding.GetEncoding("GB2312");
            Response.ContentType = "application/vnd.ms-excel";

            Response.AppendHeader("Content-Disposition", "attachment;filename=" + fileName + ".xls");

            // 返回客户端  
            var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.ExportTempFiles, fileName + ".xls"));

            return File(bytes, "attachment;filename=" + fileName);
        }
    }
}
