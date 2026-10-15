using System;
using System.Collections.Generic;
using System.Configuration;
using System.IO;
using System.Web;
using System.Web.Mvc;
using System.Text;
using System.Linq;
using Dchien.Legal.BizModel.FIO;
using Dchien.Legal.BizModel.FIO.PatentOffice;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.Service.FIO;
using Dchien.Legal.Service.FIO.PatentOffice;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Web.Areas.FIO.ViewModels;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Entity.System;

namespace Dchien.Legal.Web.Areas.FIO.Controllers
{
    [CheckUserLogin]
    public class PatentOfficeFileController : BaseController
    {
        internal Log Logger = new Log("IPR.Controllers.PatentOfficeFileController");

        #region 打包下载


        /// <summary>
        /// 
        /// </summary>
        /// <param name="officeFileId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult PatentOfficeFilePacking(long[] officeFileIds)
        {
            var response = new PostResponse();

            try
            {
                var fileList = PatentOfficeFileService.Instance.GetCasePatentOfficeFileListById(officeFileIds.ToList());

                var files = new List<string>();

                fileList.ForEach(x =>
                {
                    files.Add(Path.Combine(FileHelper.PatentOfficeFiles, x.MetaFile.FileGuid.ToString(), x.FileOfficialName));

                    var originalPath = Path.Combine(FileHelper.PatentOfficeFiles, x.MetaFile.FileGuid.ToString(), x.TONGZHISID, x.FileOfficialName);

                    if (string.IsNullOrEmpty(x.CaseRequestNo))
                    {
                        var caseInfo = CaseService.Instance.GetCaseBasicByCaseNo(x.CaseNo);

                        if (caseInfo.CaseBasicInfo != null)
                        {
                            x.CaseRequestNo = caseInfo == null ? "A" + caseInfo.CaseBasicInfo.CaseNo : "S" + caseInfo.CaseBasicInfo.CaseRequestNo;
                        }
                        else
                        {
                            x.CaseRequestNo = x.TONGZHISID;
                        }
                    }
                    else
                    {
                        x.CaseRequestNo = "S" + x.CaseRequestNo;
                    }

                    var destinationPath = Path.Combine(FileHelper.ExportTempFiles, x.CaseRequestNo + "W" + x.FileTypeId.ToString() + "R" + x.FAWENR.Value.ToString("yyyyMMdd") + "N" + x.FileOfficialName);

                    FileHelper.CopyFile(destinationPath, originalPath);

                    files.Add(destinationPath);
                });

                if (files.Any())
                {
                    var fileName = Guid.NewGuid() + ".zip";
                    FileHelper.CreateZipFile(files.ToArray(), Path.Combine(FileHelper.ExportTempFiles, fileName), string.Empty);
                    response.Data = fileName;
                }
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.CasePatentOfficeFileInList", "PatentOfficeFileController.CasePatentOfficeFileInList", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }


        [HttpPost]
        public JsonResult HistoryPatentOfficeFilePacking(long[] officeFileIds)
        {
            var response = new PostResponse();

            try
            {
                var fileList = PatentOfficeFileService.Instance.GetHistoryCasePatentOfficeFileListById(officeFileIds.ToList());

                var files = new List<string>();

                fileList.ForEach(x =>
                {
                    files.Add(Path.Combine(FileHelper.HistoryPatentOfficeFiles, x.CaseRequestNo.Replace(".", ""), x.FileOfficialName));

                    var originalPath = Path.Combine(FileHelper.HistoryPatentOfficeFiles, x.CaseRequestNo.Replace(".", ""), x.FileOfficialName);

                    if (string.IsNullOrEmpty(x.CaseRequestNo))
                    {
                        var caseInfo = CaseService.Instance.GetCaseBasicByCaseNo(x.CaseNo);

                        if (caseInfo.CaseBasicInfo != null)
                        {
                            x.CaseRequestNo = caseInfo == null ? "A" + caseInfo.CaseBasicInfo.CaseNo : "S" + caseInfo.CaseBasicInfo.CaseRequestNo;
                        }
                        else
                        {
                            x.CaseRequestNo = x.TONGZHISID;
                        }
                    }
                    else
                    {
                        x.CaseRequestNo = "S" + x.CaseRequestNo;
                    }

                    var destinationPath = Path.Combine(FileHelper.ExportTempFiles, x.CaseRequestNo + "W" + x.FileTypeId.ToString() + "R" + x.FAWENR.Value.ToString("yyyyMMdd") + "N" + x.FileOfficialName);

                    FileHelper.CopyFile(destinationPath, originalPath);

                    files.Add(destinationPath);
                });

                if (files.Any())
                {
                    var fileName = Guid.NewGuid() + ".zip";
                    FileHelper.CreateZipFile(files.ToArray(), Path.Combine(FileHelper.ExportTempFiles, fileName), string.Empty);
                    response.Data = fileName;
                }
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.CasePatentOfficeFileInList", "PatentOfficeFileController.CasePatentOfficeFileInList", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFileId"></param>
        /// <returns></returns>
        public ActionResult PatentOfficeFileDownload(string fileName)
        {
            try
            {
                // 设置编码和附件格式  
                Response.Charset = "gb2312";
                Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                //Response.ContentType = "application/vnd.ms-word";

                Response.AppendHeader("Content-Disposition", "attachment;filename=" + HttpUtility.UrlEncode(fileName, Encoding.UTF8).ToString());

                // 返回客户端  
                var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.ExportTempFiles, fileName));

                if (bytes == null)
                {
                    bytes = new byte[0];
                }

                return File(bytes, "attachment;filename=" + fileName);
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.PatentOfficeFileDownload", "PatentOfficeFileController.PatentOfficeFileDownload", ex);
                throw ex;
            }

            return null;
        }

        #endregion

        #region 页面导出

        /// <summary>
        /// 专利文件导出
        /// </summary>
        /// <param name="search"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult PatentOfficeFileListExportToExcel(CasePatentOfficeFileListModel model)
        {
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 5000;

            if (model.SearchCondition.PageId == PageId.PageId_1101002)
            {
                model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
            }
            if (model.SearchCondition.PageId == PageId.PageId_1101006)
            {
                model.SearchCondition.DepartmentId = LoginHelper.GetDepartmentId();
            }

            if (model.SearchCondition.PageId == PageId.PageId_1101001003)
            {
                model.SearchCondition.Status = CasePatentOfficeFileStatus.UnImported;
                //model.SearchCondition.DepartmentId = LoginHelper.GetDepartmentId();
            }

            var caseList = PatentOfficeFileService.Instance.GetPatentOfficeFileList(model.SearchCondition);

            var result = new BizPatentOfficeFileResultInfo();

            result.TotalItemCount = model.SearchCondition.TotalCount;
            result.PageNo = model.SearchCondition.PageNo;
            result.PageSize = model.SearchCondition.PageSize;
            result.Cases = caseList;

            var sb = new StringBuilder();

            #region template

            var template = @"<html xmlns:o='urn:schemas-microsoft-com:office:office'
                              xmlns:x='urn:schemas-microsoft-com:office:excel' 
                              xmlns='http://www.w3.org/TR/REC-html40'>
                            <head><!--[if gte mso 9]>
                                 <xml>
                                     <x:ExcelWorkbook><x:ExcelWorksheets><x:ExcelWorksheet>
                                       <x:Name>{worksheet}</x:Name><x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions></x:ExcelWorksheet></x:ExcelWorksheets>
                                     </x:ExcelWorkbook>
                                 </xml><![endif]-->  
                                <style type='text/css'>  
                                    table.dataintable {
                                          margin-top:15px;
                                          border-collapse:collapse;
                                          border:1px solid #aaa;
                                           
                                        }
                                        table.dataintable th {
                                          vertical-align:baseline;
                                          padding:0px;
                                          background-color:#999;
	                                      border:1px solid #aaa;
                                          text-align:left;
                                          color:#fff;
                                          font-size: 10pt;
                                          font-family: SimSun;
                                          font-color: #000;

                                        }
                                        table.dataintable td {
                                          vertical-align:text-top;
                                          padding:0px;
                                          border:1px solid #aaa;
                                          overflow: hidden;
                                            font-size: 10pt;
                                            font-family: SimSun;
                                        }
                                        table.dataintable tr:nth-child(odd) {
                                          background-color:#F5F5F5;
                                        }
                                        table.dataintable tr:nth-child(even) {
                                          background-color:#fff;
                                        }
                                    </style >
                            </head>
                          <body >
                          <table class='dataintable'>{table}</table></body></html>";
            #endregion 

            #region header

            sb.Append(@" 
                        <tr>
                            <th style='text-align: center'>流程处理</th>
                            <th style='text-align: center'>业务处理</th>
                            <th style='text-align: center'>入库时间	</th>
                            <th style='text-align: center'>案号</th>
                            <th style='text-align: center'>案件类型</th>
                            <th style='text-align: center'>客户名称</th>
                            <th style='text-align: center'>申请人</th>
                            <th style='text-align: center'>申请号</th>
                            <th style='text-align: center'>专利名称</th>
                            <th style='text-align: center'>客戶管理人</th>
                            <th style='text-align: center'>收发文日</th>
                            <th style='text-align: center'>发文号</th>
                            <th style='text-align: center'>通知书名</th>
                        </tr>");

            #endregion

            #region body

            result.Cases.ForEach(c =>
            {
                var caseType = CaseTypeService.Instance.GetCaseType(c.CaseBasicInfo.CaseTypeId);

                c.CaseFileList.ForEach(f =>
                {

                    var tr = "<tr>"
                        + "<td>" + f.ServiceProcessStatusName + "</td>"
                        + "<td>" + f.BusinessProcessStatusName + "</td>"
                        + "<td>" + (f.InDate.HasValue ? f.InDate.Value.ToString("yyyy-MM-dd") : string.Empty) + "</td>"
                        + "<td>" + (String.IsNullOrEmpty(c.CaseBasicInfo.CaseNo) ? string.Empty : c.CaseBasicInfo.CaseNo) + "</td>"
                        + "<td>" + (caseType == null ? string.Empty : caseType.CaseTypeName) + "</td>"
                        + "<td>" + (String.IsNullOrEmpty(c.CaseBasicInfo.CustomerName) ? string.Empty : c.CaseBasicInfo.CustomerName) + "</td>"
                        + "<td>" + (String.IsNullOrEmpty(c.CaseBasicInfo.ApplicantName) ? string.Empty : c.CaseBasicInfo.ApplicantName) + "</td>"
                        + "<td>" + "'" + (String.IsNullOrEmpty(c.CaseBasicInfo.CaseRequestNo) ? string.Empty : c.CaseBasicInfo.CaseRequestNo) + "</td>"
                        + "<td>" + (String.IsNullOrEmpty(f.FAMINGMC) ? c.CaseBasicInfo.CaseName : f.FAMINGMC) + "</td>"
                        + "<td>" + (String.IsNullOrEmpty(c.CaseBasicInfo.CaseOriginPeopleName) ? string.Empty : c.CaseBasicInfo.CaseOriginPeopleName) + "</td>"
                        + "<td>" + (f.FAWENR.HasValue ? f.FAWENR.Value.ToString("yyyy-MM-dd") : string.Empty) + "</td>"
                        + "<td><span>" + f.FAWENXLH + "</span></td>"
                        + "<td>" + f.TONGZHISMC + "</td>"
                        + "</tr>";

                    sb.Append(tr);

                });
            });

            #endregion

            template = template.Replace("{table}", sb.ToString());
            template = template.Replace("{worksheet}", "专利收文");

            var fileName = Guid.NewGuid();

            FileHelper.CreateFile(FileHelper.ExportTempFiles, fileName + ".xls", Encoding.GetEncoding("GB2312").GetBytes(template));

            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = fileName;
            return Json(response);
        }

        public ActionResult HistoryPatentOfficeFileListExportToExcel(CasePatentOfficeFileListModel model)
        {
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 1500;

            var caseList = PatentOfficeFileService.Instance.GetHistoryPatentOfficeFileList(model.SearchCondition);

            var result = new BizPatentOfficeFileResultInfo();

            result.TotalItemCount = model.SearchCondition.TotalCount;
            result.PageNo = model.SearchCondition.PageNo;
            result.PageSize = model.SearchCondition.PageSize;
            result.Cases = caseList;

            var sb = new StringBuilder();

            #region template

            var template = @"<html xmlns:o='urn:schemas-microsoft-com:office:office'
                              xmlns:x='urn:schemas-microsoft-com:office:excel' 
                              xmlns='http://www.w3.org/TR/REC-html40'>
                            <head><!--[if gte mso 9]>
                                 <xml>
                                     <x:ExcelWorkbook><x:ExcelWorksheets><x:ExcelWorksheet>
                                       <x:Name>{worksheet}</x:Name><x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions></x:ExcelWorksheet></x:ExcelWorksheets>
                                     </x:ExcelWorkbook>
                                 </xml><![endif]-->  
                                <style type='text/css'>  
                                    table.dataintable {
                                          margin-top:15px;
                                          border-collapse:collapse;
                                          border:1px solid #aaa;
                                           
                                        }
                                        table.dataintable th {
                                          vertical-align:baseline;
                                          padding:0px;
                                          background-color:#999;
	                                      border:1px solid #aaa;
                                          text-align:left;
                                          color:#fff;
                                          font-size: 10pt;
                                          font-family: SimSun;
                                          font-color: #000;

                                        }
                                        table.dataintable td {
                                          vertical-align:text-top;
                                          padding:0px;
                                          border:1px solid #aaa;
                                          overflow: hidden;
                                            font-size: 10pt;
                                            font-family: SimSun;
                                        }
                                        table.dataintable tr:nth-child(odd) {
                                          background-color:#F5F5F5;
                                        }
                                        table.dataintable tr:nth-child(even) {
                                          background-color:#fff;
                                        }
                                    </style >
                            </head>
                          <body >
                          <table class='dataintable'>{table}</table></body></html>";
            #endregion 

            #region header

            sb.Append(@" 
                        <tr>
                            <th style='text-align: center'>流程处理</th>
                            <th style='text-align: center'>业务处理</th>
                            <th style='text-align: center'>入库时间	</th>
                            <th style='text-align: center'>案号</th>
                            <th style='text-align: center'>案件类型</th>
                            <th style='text-align: center'>客户名称</th>
                            <th style='text-align: center'>申请人</th>
                            <th style='text-align: center'>申请号</th>
                            <th style='text-align: center'>专利名称</th>
                            <th style='text-align: center'>客戶管理人</th>
                            <th style='text-align: center'>收发文日</th>
                            <th style='text-align: center'>发文号</th>
                            <th style='text-align: center'>通知书名</th>
                        </tr>");

            #endregion

            #region body

            result.Cases.ForEach(c =>
            {
                var caseType = CaseTypeService.Instance.GetCaseType(c.CaseBasicInfo.CaseTypeId);

                c.CaseFileList.ForEach(f =>
                {
                    var tr = "<tr>"
                        + "<td>" + f.ServiceProcessStatusName + "</td>"
                        + "<td>" + f.BusinessProcessStatusName + "</td>"
                        + "<td>" + (f.InDate.HasValue ? f.InDate.Value.ToString("yyyy-MM-dd") : string.Empty) + "</td>"
                        + "<td>" + (String.IsNullOrEmpty(c.CaseBasicInfo.CaseNo) ? string.Empty : c.CaseBasicInfo.CaseNo) + "</td>"
                        + "<td>" + (caseType == null ? string.Empty : caseType.CaseTypeName) + "</td>"
                        + "<td>" + (String.IsNullOrEmpty(c.CaseBasicInfo.CustomerName) ? string.Empty : c.CaseBasicInfo.CustomerName) + "</td>"
                        + "<td>" + (String.IsNullOrEmpty(c.CaseBasicInfo.ApplicantName) ? string.Empty : c.CaseBasicInfo.ApplicantName) + "</td>"
                        + "<td>" + "'" + (String.IsNullOrEmpty(c.CaseBasicInfo.CaseRequestNo) ? string.Empty : c.CaseBasicInfo.CaseRequestNo) + "</td>"
                        + "<td>" + (String.IsNullOrEmpty(f.FAMINGMC) ? c.CaseBasicInfo.CaseName : f.FAMINGMC) + "</td>"
                        + "<td>" + (String.IsNullOrEmpty(c.CaseBasicInfo.CaseOriginPeopleName) ? string.Empty : c.CaseBasicInfo.CaseOriginPeopleName) + "</td>"
                        + "<td>" + (f.FAWENR.HasValue ? f.FAWENR.Value.ToString("yyyy-MM-dd") : string.Empty) + "</td>"
                        + "<td><span>" + f.FAWENXLH + "</span></td>"
                        + "<td>" + f.TONGZHISMC + "</td>"
                        + "</tr>";

                    sb.Append(tr);

                });
            });

            #endregion

            template = template.Replace("{table}", sb.ToString());
            template = template.Replace("{worksheet}", "专利收文");

            var fileName = Guid.NewGuid();

            FileHelper.CreateFile(FileHelper.ExportTempFiles, fileName + ".xls", Encoding.GetEncoding("GB2312").GetBytes(template));

            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = fileName;
            return Json(response);
        }


        [HttpPost]
        public ActionResult PatentOfficeFileCheckListExportToExcel(CasePatentOfficeFileListModel model)
        {
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = int.MaxValue;

            var list = PatentOfficeFileService.Instance.GetCasePatentOfficeFileCheckList(model.SearchCondition);

            var result = new BizPatentOfficeFileCheckListResultInfo();

            result.TotalItemCount = model.SearchCondition.TotalCount;
            result.PageNo = model.SearchCondition.PageNo;
            result.PageSize = model.SearchCondition.PageSize;
            result.CheckFiles = list;

            var sb = new StringBuilder();

            #region template

            var template = @"<html xmlns:o='urn:schemas-microsoft-com:office:office'
                              xmlns:x='urn:schemas-microsoft-com:office:excel' 
                              xmlns='http://www.w3.org/TR/REC-html40'>
                            <head><!--[if gte mso 9]>
                                 <xml>
                                     <x:ExcelWorkbook><x:ExcelWorksheets><x:ExcelWorksheet>
                                       <x:Name>{worksheet}</x:Name><x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions></x:ExcelWorksheet></x:ExcelWorksheets>
                                     </x:ExcelWorkbook>
                                 </xml><![endif]-->  
                                <style type='text/css'>  
                                    table.dataintable {
                                          margin-top:15px;
                                          border-collapse:collapse;
                                          border:1px solid #aaa;
                                           
                                        }
                                        table.dataintable th {
                                          vertical-align:baseline;
                                          padding:0px;
                                          background-color:#999;
	                                      border:1px solid #aaa;
                                          text-align:left;
                                          color:#fff;
                                          font-size: 10pt;
                                          font-family: SimSun;
                                          font-color: #000;

                                        }
                                        table.dataintable td {
                                          vertical-align:text-top;
                                          padding:0px;
                                          border:1px solid #aaa;
                                          overflow: hidden;
                                            font-size: 10pt;
                                            font-family: SimSun;
                                        }
                                        table.dataintable tr:nth-child(odd) {
                                          background-color:#F5F5F5;
                                        }
                                        table.dataintable tr:nth-child(even) {
                                          background-color:#fff;
                                        }
                                    </style >
                            </head>
                          <body >
                          <table class='dataintable'>{table}</table></body></html>";
            #endregion 

            #region header

            sb.Append(@" 
                        <tr>
                            <th style='text-align: center'>申请号/不受理编号</th>
                            <th style='text-align: center'>通知书名称</th>
                            <th style='text-align: center'>发明创造名称</th>
                            <th style='text-align: center'>发文序列号</th>
                            <th style='text-align: center'>电子发文日</th>
                            <th style='text-align: center'>下载状态</th>
                            <th style='text-align: center'>系统状态</th>
                            <th style='text-align: center'>案号</th>
                            <th style='text-align: center'>入库时间</th>
                            <th style='text-align: center'>错误消息</th>
                        </tr>");

            #endregion

            #region body

            result.CheckFiles.ForEach(f =>
            {
                var tr = "<tr>"
                    + "<td>" + f.CaseRequestNo + "</td>"
                    + "<td>" + f.TONGZHISMC + "</td>"
                    + "<td>" + f.FAMINGMC + "</td>"
                    + "<td>" + f.FAWENXLH + "</td>"
                    + "<td>" + (f.FAWENR.HasValue ? f.FAWENR.Value.ToString("yyyy-MM-dd") : string.Empty) + "</td>"
                    + "<td>" + f.DownloadStatus + "</td>"
                    + "<td>" + f.PatentOfficeFileStatusName + "</td>"
                    + "<td>" + f.CaseNo + "</td>"
                    + "<td>" + (f.InDate.HasValue ? f.InDate.Value.ToString("yyyy-MM-dd") : string.Empty) + "</td>"
                    + "<td>" + string.Join(",", f.Errors.Select(x => x.Message)) + "</td>"
                    + "</tr>";
                sb.Append(tr);
            });

            #endregion

            template = template.Replace("{table}", sb.ToString());
            template = template.Replace("{worksheet}", "专利文件清单");

            var fileName = Guid.NewGuid();

            FileHelper.CreateFile(FileHelper.ExportTempFiles, fileName + ".xls", Encoding.GetEncoding("GB2312").GetBytes(template));

            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = fileName;
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="fileName"></param>
        /// <returns></returns>
        public ActionResult PatentOfficeFileListExportToExcelDownload(string fileName)
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

        #endregion

    }
}
