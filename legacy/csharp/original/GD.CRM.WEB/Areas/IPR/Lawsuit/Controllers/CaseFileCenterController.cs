using System;
using System.Collections.Generic;
using System.Data;
using System.Data.Entity.Infrastructure;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Text;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using System.Web.UI.WebControls;
using Dchien.Legal.BizModel.Lawsuit.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Service.Lawsuit.Case;
using Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.Lawsuit.Controllers
{
    [CheckUserLogin]
    public class CaseFileCenterController : BaseController
    {
        /// <summary>
        /// 案件文件下载
        /// </summary>
        /// <param name="caseFileId"></param>
        /// <returns></returns>
        public ActionResult CaseFileDownload(long caseFileId)
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
                                                             HttpUtility.UrlEncode(caseFile.FileName, Encoding.UTF8).ToString());

                // 返回客户端  
                var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CaseFiles, caseFile.CaseNo, caseFile.FileName));

                if (bytes == null)
                {
                    bytes = new byte[0];
                }

                return File(bytes, "attachment;filename=" + caseFile.FileName);
            }

            return null;
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFeeId"></param>
        /// <returns></returns>
        public ActionResult CaseFeeFileDownload(long caseFeeId)
        {
            var caseFeeItem = CaseFeeService.Instance.GetCaseFeeItem(caseFeeId);

            if (caseFeeItem != null)
            {
                // 设置编码和附件格式  
                Response.Charset = "gb2312";
                Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                //Response.ContentType = "application/vnd.ms-word";

                Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                             HttpUtility.UrlEncode(caseFeeItem.BillFileName, Encoding.UTF8).ToString());

                // 返回客户端  
                var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CaseFeeFiles, caseFeeItem.CaseNo, caseFeeItem.BillFileName));

                if (bytes != null)
                {
                    return File(bytes, "attachment;filename=" + caseFeeItem.BillFileName);
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

         [HttpGet]
        public ActionResult CaseListExportToExcelDownload(string fileName)
        {
            // 设置编码和附件格式  
            Response.Charset = "gb2312";
            Response.ContentEncoding = Encoding.GetEncoding("GB2312");
            Response.ContentType = "application/vnd.ms-excel";

            Response.AppendHeader("Content-Disposition", "attachment;filename=" + fileName + ".xls");

            // 返回客户端  
            var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.TemplateFiles, fileName + ".xls"));

            return File(bytes, "attachment;filename=" + fileName);
        }

 
    }
}
