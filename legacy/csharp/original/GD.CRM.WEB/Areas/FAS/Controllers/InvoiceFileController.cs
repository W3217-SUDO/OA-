using System;
using System.IO;
using System.Text;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using Dchien.Legal.Common;
using Dchien.Legal.Service.FAM.AR.CaseFee;
using Dchien.Legal.Service.FAM.AR.Invoice.File;
using Dchien.Legal.Service.FAM.CaseFee;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class InvoiceFileController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.InvoiceFileController");
 
        /// <summary>
        /// 合同文件下载
        /// </summary>
        /// <param name="invoiceFileId"></param>
        /// <returns></returns>
        public ActionResult InvoiceFileDownload(long invoiceFileId)
        {
            try
            {
                var invoiceFile = InvoiceFileService.Instance.GetInvoiceFile(invoiceFileId);

                if (invoiceFile != null)
                {
                    StringWriter strWriter = null;
                    HtmlTextWriter htmlWriter = null;

                    // 设置编码和附件格式  
                    Response.Charset = "gb2312";
                    Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                    //Response.ContentType = "application/vnd.ms-word";

                    Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                                 HttpUtility.UrlEncode(invoiceFile.FileName, Encoding.UTF8)
                                                                     .ToString());

                    // 返回客户端  
                    var bytes =
                        FileHelper.ReadFile(Path.Combine(FileHelper.InvoiceFiles, invoiceFile.CustomerNo, invoiceFile.FileName));

                    if (bytes == null)
                    {
                        bytes = new byte[0];
                    }

                    return File(bytes, "attachment;filename=" + invoiceFile.FileName);
                }

            }
            catch (Exception ex)
            {
                Logger.Error("InvoiceFileController.InvoiceFileDownload", ex);
                throw ex;
            }


            return null;
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFeeGuid"></param>
        /// <returns></returns>
        public ActionResult List(string caseFeeGuid)
        {
            var model = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.Invoice.File.ListModel();

            try
            {
                model.CaseFeeGuid = new Guid(caseFeeGuid);
                model.CaseFee = CaseFeeService.Instance.GetCaseFeeByCaseFeeId(model.CaseFeeGuid);
            }
            catch (Exception ex)
            {
                Logger.Error("InvoiceFileController.List", ex);
             }
            return PartialView(model);
         } 
    }
}
