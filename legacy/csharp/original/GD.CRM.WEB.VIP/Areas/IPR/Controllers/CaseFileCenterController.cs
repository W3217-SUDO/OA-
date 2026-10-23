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
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.BizModel.CRM.LawFirm;
using Dchien.Legal.Common;
using Dchien.Legal.Entity;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Web.Areas.IPR.ViewModels;
using Dchien.Legal.Web.Areas.IPR.ViewModels.Case;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.CRM.LawFirm;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.IPR.Controllers
{
    [CheckUserLogin]
    public class CaseFileCenterController : BaseController
    {
        internal Log Logger = new Log("IPR.Controllers.CaseFileCenterController");

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
        /// <param name="caseFeeId"></param>
        /// <returns></returns>
         [CheckUserLogin]
        public ActionResult CaseFeeFileDownload(long caseFeeId)
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
        /// <param name="caseAssistedFeeId"></param>
        /// <returns></returns>
        public ActionResult CaseAssistedFeeFileDownload(int caseAssistedFeeId)
        {
            var caseAssistedFee = CaseAssistedFeeService.Instance.GetCaseAssistedFee(caseAssistedFeeId);

            if (caseAssistedFee != null)
            {
                // 设置编码和附件格式  
                Response.Charset = "gb2312";
                Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                //Response.ContentType = "application/vnd.ms-word";

                Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                             HttpUtility.UrlEncode(caseAssistedFee.FileName, Encoding.UTF8).ToString());

                // 返回客户端  
                var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CaseAssistedFeeFiles, caseAssistedFee.CaseNo, caseAssistedFee.FileName));

                if (bytes != null)
                {
                    return File(bytes, "attachment;filename=" + caseAssistedFee.FileName);
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
            var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.ExportTempFiles, fileName + ".xls"));

            return File(bytes, "attachment;filename=" + fileName);
        }

        /// <summary>
        /// 下载文件
        /// </summary>
        /// <param name="search"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseListExportToExcel(CaseSearchConditionModel search)
        {
            search.SearchCondition.PageNo = 1;
            search.SearchCondition.PageSize = int.MaxValue;

            var result = new BizCaseSearchResultInfo();

            result.CaseList = CaseSearchService.Instance.GetCaseList(search.SearchCondition);

            var casePhases = CaseTypeService.Instance.GetAllCasePhases();
            var caseTypes = CaseTypeService.Instance.GetAllCaseTypes();

            var dt = new DataTable();

            dt.Columns.Add("案件编号", typeof(string));
            dt.Columns.Add("客户编号", typeof(string));
            dt.Columns.Add("名称", typeof(string));
            dt.Columns.Add("案件类型", typeof(string));
            dt.Columns.Add("案件阶段", typeof(string));
            dt.Columns.Add("申请号", typeof(string));
            dt.Columns.Add("申请日", typeof(string));
            dt.Columns.Add("受理日", typeof(string));
            dt.Columns.Add("案源人", typeof(string));
            dt.Columns.Add("案源日", typeof(string));
            dt.Columns.Add("代理人", typeof(string));
            dt.Columns.Add("撰稿人", typeof(string));
            dt.Columns.Add("提交人", typeof(string));
            dt.Columns.Add("提交日", typeof(string));
            dt.Columns.Add("截止日", typeof(string));
            dt.Columns.Add("发明人", typeof(string));


            if (result.CaseList != null &&
                result.CaseList.Any())
            {
                result.CaseList.ForEach(x =>
                {
                    var cusomterName = new List<string>();

                    if (x.CaseCustomers != null && x.CaseCustomers.Any())
                    {
                        x.CaseCustomers.ForEach(c => cusomterName.Add(c.CustomerBasic.CustomerName));
                    }
                    var dr = dt.NewRow();
                    dr[0] = x.CaseBasicInfo.CaseNo;
                    dr[1] = string.Join(",", cusomterName);
                    dr[2] = x.CaseBasicInfo.CaseName;

                    dr[3] = caseTypes.FirstOrDefault(t=>t.CaseTypeId == x.CaseBasicInfo.CaseTypeId) == null ?  string.Empty : caseTypes.FirstOrDefault(t=>t.CaseTypeId == x.CaseBasicInfo.CaseTypeId).CaseTypeName;
                    dr[4] = casePhases.FirstOrDefault(t=>t.CasePhaseId == x.CaseBasicInfo.CasePhaseId) == null ?string.Empty : casePhases.FirstOrDefault(t=>t.CasePhaseId == x.CaseBasicInfo.CasePhaseId).CasePhaseName;
                    dr[5] = x.CaseBasicInfo.CaseRequestNo;
                    dr[6] = x.CaseBasicInfo.CaseRequestDate.HasValue
                        ? x.CaseBasicInfo.CaseRequestDate.Value.ToString("yyyy-MM-dd")
                        : string.Empty;
                    dr[7] = x.CaseBasicInfo.CaseRegisterDate.HasValue
                        ? x.CaseBasicInfo.CaseRegisterDate.Value.ToString("yyyy-MM-dd")
                        : string.Empty;
                    dr[8] = x.CaseBasicInfo.CaseOriginPeopleName;
                    dr[9] = x.CaseBasicInfo.CaseOriginDate.HasValue
                        ? x.CaseBasicInfo.CaseOriginDate.Value.ToString("yyyy-MM-dd")
                        : string.Empty;
                    dr[10] = x.CaseBasicInfo.ProcuratorName;
                    dr[11] = x.CaseBasicInfo.CopywriterName;
                    dr[12] = x.CaseBasicInfo.CaseSubmitterName;
                    dr[13] = x.CaseBasicInfo.CaseSubmitDate.HasValue
                        ? x.CaseBasicInfo.CaseSubmitDate.Value.ToString("yyyy-MM-dd")
                        : string.Empty;
                    dr[14] = x.CaseBasicInfo.Deadline.HasValue
                        ? x.CaseBasicInfo.Deadline.Value.ToString("yyyy-MM-dd")
                        : string.Empty;
                    dr[15] = x.CaseBasicInfo.CaseInventor;

                    dt.Rows.Add(dr);
                });
            }

            //根据传过来的参数查询要到处的数据

            DataGrid dgExport = null;
            // IO用于导出并返回excel文件  
            StringWriter strWriter = null;
            HtmlTextWriter htmlWriter = null;
            string filename = Guid.NewGuid().ToString();
            byte[] str = null;

            if (result.CaseList != null && result.CaseList.Any())
            {
                strWriter = new StringWriter();
                htmlWriter = new HtmlTextWriter(strWriter);

                // 为了解决dgData中可能进行了分页的情况，需要重新定义一个无分页的DataGrid  
                dgExport = new DataGrid();
                dgExport.DataSource = dt.DefaultView;
                dgExport.AllowPaging = false;
                dgExport.DataBind();
                dgExport.RenderControl(htmlWriter);


                FileHelper.CreateFile(FileHelper.ExportTempFiles, filename + ".xls",
                    Encoding.GetEncoding("GB2312").GetBytes(strWriter.ToString()));

                // 返回客户端  
                //str = System.Text.Encoding.GetEncoding("GB2312").GetBytes(strWriter.ToString());

                var response = new PostResponse();
                response.IsSuccess = true;
                response.Data = filename;
                return Json(response);
            }
            else
            {
                var response = new PostResponse();
                response.IsSuccess = false;
                response.Message = "导出错误.";
                return Json(response);
            }

            //return File(str, "attachment;filename=" + filename + ".xls");
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFileId"></param>
        /// <returns></returns>
        public ActionResult CPCFileDownload(string fileName)
        {
            // 设置编码和附件格式  
            Response.Charset = "gb2312";
            Response.ContentEncoding = Encoding.GetEncoding("GB2312");
 
            Response.AppendHeader("Content-Disposition", "attachment;filename=" + fileName);

            // 返回客户端  
            var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.PatentOfficeFiles, fileName));

            return File(bytes, "attachment;filename=" + fileName);
        }
    }
}
