using System;
using System.Linq;
using System.IO;
using System.Text;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using Dchien.Legal.Common;
using Dchien.Legal.Service.FAM.AR.CaseFee;
using Dchien.Legal.Service.FAM.Invoice;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.BizModel.FAM.Invoice;
using Dchien.Legal.Service.BAS.Type;
using System.Collections.Generic;
using Dchien.Legal.Entity.FAM.Invoice;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class InvoiceFileCenterController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.InvoiceFileCenterController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult InvoiceListExportToExcel(Dchien.Legal.Web.Areas.FAM.ViewModels.Invoice.ListModel model)
        {
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 60000;

            if (model.SearchCondition.PageId == "5001006001")
            {
                model.SearchCondition.InvoiceApplicant = LoginHelper.GetUserName();
            }
            else if (model.SearchCondition.PageId == "5001006002")
            {
                model.SearchCondition.InvoiceStatus = InvoiceStatus.Pending;
            }

            var invoices = InvoiceService.Instance.GetInvoiceList(model.SearchCondition);
            var fileName = InvoiceService.Instance.InvoiceListSelectedExportToExcel(invoices);

            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = Path.GetFileNameWithoutExtension(fileName);
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="invoiceIds"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult InvoiceListSelectedExportToExcel(List<long> invoiceIds)
        {
            var invoices = InvoiceService.Instance.GetInvoiceList(invoiceIds);
            var fileName = InvoiceService.Instance.InvoiceListSelectedExportToExcel(invoices);

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
        public ActionResult InvoiceListExportToExcelDownload(string fileName)
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
