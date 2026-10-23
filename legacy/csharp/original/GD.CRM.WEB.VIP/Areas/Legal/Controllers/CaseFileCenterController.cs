using System;
using System.IO;
using System.Text;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using System.Linq;

using Dchien.Legal.Common;
using Dchien.Legal.Service.Legal.Case;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Entity.Legal.Case;

namespace Dchien.Legal.Web.Areas.Legal.Controllers
{
    [CheckUserLogin]
    public class CaseFileCenterController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.CaseFileCenterController");

        /// <summary>
        /// 案件文件下载
        /// </summary>
        /// <param name="caseFileId"></param>
        /// <returns></returns>
        public ActionResult CaseFileDownload(long caseFileId)
        {
            try
            {
                var caseFile = CaseFileService.Instance.GetCaseFile(caseFileId);

                if (caseFile != null)
                {
                    StringWriter strWriter = null;
                    HtmlTextWriter htmlWriter = null;

                    // 设置编码和附件格式  
                    Response.Charset = "gb2312";
                    Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                    //Response.ContentType = "application/vnd.ms-word";

                    Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                                 HttpUtility.UrlEncode(caseFile.FileName, Encoding.UTF8)
                                                                     .ToString());

                    // 返回客户端  
                    var bytes =
                        FileHelper.ReadFile(Path.Combine(FileHelper.CaseFiles, caseFile.CaseNo, caseFile.FileName));

                    if (bytes == null)
                    {
                        bytes = new byte[0];
                    }

                    return File(bytes, "attachment;filename=" + caseFile.FileName);
                }

            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFileCenterController.CaseFileDownload", "CaseFileCenterController.CaseFileDownload", ex);
                throw ex;
            }


            return null;
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFileId"></param>
        /// <param name="caseFileTypeId"></param>
        /// <returns></returns>
        public ActionResult CaseFileDownloadByFileTypeId(long caseFileId,int caseFileTypeId)
        {
            if (caseFileTypeId == (int)CaseFileTypeId.CRM)
            {
                return new RedirectResult("~/CustomerFile/CustomerFileDownload?customerFileId=" + caseFileId);
            }
            else if (caseFileTypeId == (int)CaseFileTypeId.FCM)
            {
                return new RedirectResult("~/ContractFile/ContractFileDownload?contractFileId=" + caseFileId);
            }

            else if (caseFileTypeId == (int)CaseFileTypeId.Investigation || caseFileTypeId == (int)CaseFileTypeId.Investigation_Task)
            {
                return new RedirectResult("~/InvestigationFile/InvestigationFileDownload?fileId=" + caseFileId);
            }
            else if (caseFileTypeId == (int)CaseFileTypeId.Investigation_Clue)
            {
                return new RedirectResult("~/InvestigationClueFile/InvestigationClueFileDownload?investigationFileId=" + caseFileId);
            }

            else if (caseFileTypeId == (int)CaseFileTypeId.Investigation_Clue_Evidence)
            {
                return new RedirectResult("~/InvestigationClueEvidenceFile/InvestigationClueEvidenceFileDownload?fileId=" + caseFileId);
            }

            return new RedirectResult("~/CaseFileCenter/CaseFileDownload?caseFileId=" + caseFileId);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFeeId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CaseFeeFileDownload(long caseFeeId)
        {
            var caseFee = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.GetCaseFeeByCaseFeeId(caseFeeId);

            if (caseFee != null )
            {
                // 设置编码和附件格式  
                Response.Charset = "gb2312";
                Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                //Response.ContentType = "application/vnd.ms-word";

                Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                             HttpUtility.UrlEncode(caseFee.InvoiceFile.InvoiceFileName, Encoding.UTF8).ToString());

                // 返回客户端  
                var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CaseFeeFiles, caseFee.CaseNo, caseFee.InvoiceFile.InvoiceFileName));

                if (bytes != null)
                {
                    return File(bytes, "attachment;filename=" + caseFee.InvoiceFile.InvoiceFileName);
                }
            }

            return null;
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="invoiceFileId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult InvoiceFileDownload(long invoiceFileId)
        {
            var invoiceFile = Dchien.Legal.Service.FAM.Invoice.InvoiceFileService.Instance.GetInvoiceFile(invoiceFileId);
            var caseFee = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.GetCaseFeeBasicByCaseFeeId(invoiceFile.CaseFeeId);

            if (invoiceFile != null)
            {
                // 设置编码和附件格式  
                Response.Charset = "gb2312";
                Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                //Response.ContentType = "application/vnd.ms-word";

                Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                             HttpUtility.UrlEncode(invoiceFile.InvoiceFileName, Encoding.UTF8).ToString());

                // 返回客户端  
                var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CaseFeeFiles, caseFee.CaseNo, invoiceFile.InvoiceFileName));

                if (bytes != null)
                {
                    return File(bytes, "attachment;filename=" + invoiceFile.InvoiceFileName);
                }
            }

            return null;
        }



        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFeeId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult APCaseFeeFileDownload(long caseFeeId)
        {
            var caseFee = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.GetCaseFeeByCaseFeeId(caseFeeId);

            if (caseFee != null)
            {
                // 设置编码和附件格式  
                Response.Charset = "gb2312";
                Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                //Response.ContentType = "application/vnd.ms-word";

                Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                             HttpUtility.UrlEncode(caseFee.InvoiceFile.InvoiceFileName, Encoding.UTF8).ToString());

                // 返回客户端  
                var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CaseFeeFiles, caseFee.CaseNo, caseFee.InvoiceFile.InvoiceFileName));

                if (bytes != null)
                {
                    return File(bytes, "attachment;filename=" + caseFee.InvoiceFile.InvoiceFileName);
                }
            }

            return null;
        }

 

        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerId"></param>
        /// <param name="fileName"></param>
        /// <returns></returns>
        public ActionResult CaseExportFileDownload(int customerId, string fileName)
        {

            // 设置编码和附件格式  
            Response.Charset = "gb2312";
            Response.ContentEncoding = Encoding.GetEncoding("gb2312");
            Response.ContentType = "application/vnd.ms-word";

            Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                         HttpUtility.UrlEncode(fileName, Encoding.UTF8).ToString());

            var customer = CustomerService.Instance.GetCustomerById(customerId);

            if (customer != null)
            {
                // 返回客户端  
                var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.ExportCaseFiles,  customer.CustomerBasic.CustomerNo, fileName));
                return File(bytes, "attachment;filename=" + fileName);
            }

            var response = new PostResponse();
            response.IsSuccess = false;
            response.Message = "文件不存在";
            return Json(response);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerNo"></param>
        /// <param name="fileName"></param>
        /// <returns></returns>
        public ActionResult CaseCommonFileDownload(string customerNo, string fileName)
        {

            // 设置编码和附件格式  
            Response.Charset = "gb2312";
            Response.ContentEncoding = Encoding.GetEncoding("gb2312");
            Response.ContentType = "application/vnd.ms-word";

            Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                         HttpUtility.UrlEncode(fileName, Encoding.UTF8).ToString());

            // 返回客户端  
            var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.ExportCaseFiles, customerNo, fileName));
            return File(bytes, "attachment;filename=" + fileName);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerNo"></param>
        /// <param name="fileName"></param>
        /// <returns></returns>
        public ActionResult ExportTempFileDownload(string fileName)
        {

            // 设置编码和附件格式  
            Response.Charset = "gb2312";
            Response.ContentEncoding = Encoding.GetEncoding("gb2312");
            Response.ContentType = "application/vnd.ms-word";

            Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                         HttpUtility.UrlEncode(fileName, Encoding.UTF8).ToString());

            // 返回客户端  
            var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.ExportTempFiles, fileName));
            return File(bytes, "attachment;filename=" + fileName);

        }

        [HttpGet]
        public ActionResult CaseListExportToExcelDownload(string fileName)
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
