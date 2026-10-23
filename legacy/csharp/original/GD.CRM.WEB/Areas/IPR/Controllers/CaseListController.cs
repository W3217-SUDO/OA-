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
using Dchien.Legal.Entity.System;
using Dchien.Legal.Entity.IPR.Case;

namespace Dchien.Legal.Web.Areas.IPR.Controllers
{
    [CheckUserLogin]
    public class CaseListController : BaseController
    {

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult List(string id)
        {
            var model = new CaseListModel();
            model.SearchCondition = new Entity.IPR.Case.CaseSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            model.SearchCondition.PageId = id;

            model.SearchCondition.AccessLevel = (Entity.Account.AccessLevel)LoginHelper.GetAccesslevel();
            model.SearchCondition.UserId = LoginHelper.GetUserName();

            if (id == PageId.PageId_1001001001)
            {
                model.SearchCondition.CaseOriginPeopleName = LoginHelper.GetUserChName();
                model.SearchCondition.PageName = "我是案源人";
            }
            else if (id == PageId.PageId_1001001002)
            {
                model.SearchCondition.CaseProcuratorName = LoginHelper.GetUserChName();
                model.SearchCondition.PageName = "我是代理人";
            }
            else if (id == PageId.PageId_1001001003)
            {
                model.SearchCondition.CaseCopywriterName = LoginHelper.GetUserChName();
                model.SearchCondition.PageName = "我是撰稿人";
            }
            else if (id == PageId.PageId_1001001004)
            {
                model.SearchCondition.CaseOfficer = LoginHelper.GetUserName();
                model.SearchCondition.CaseOfficerName = LoginHelper.GetUserChName();
                model.SearchCondition.PageName = "我是处理人";
            }
            else if (id == PageId.PageId_1001001005)
            {
                model.SearchCondition.AccessLevel = Entity.Account.AccessLevel.User;
                model.SearchCondition.PageName = "我的案件";
            }
            else if (id == PageId.PageId_1001001006)
            {
                //model.SearchCondition.AccessLevel = Entity.Account.AccessLevel.User;
                model.SearchCondition.BusinessOwnerName = LoginHelper.GetUserChName();
                model.SearchCondition.PageName = "我是客戶管理人";
            }

            else if (id == PageId.PageId_1001001010)
            {
                model.SearchCondition.PageName = "所有案件";
            }
            else if (id == PageId.PageId_1001001011)
            {
                model.SearchCondition.PageName = "年费监控案件";
            }
            else if (id == PageId.PageId_1001001012)
            {
                model.SearchCondition.PageName = "失效案件";
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1001002001)
            {
                model.SearchCondition.PageName = "申请费";
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1001002002)
            {
                model.SearchCondition.PageName = "提实审费";
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1001002003)
            {
                model.SearchCondition.PageName = "办登费";
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1001002004)
            {
                model.SearchCondition.PageName = "年费";
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1001002005)
            {
                model.SearchCondition.PageName = "年费滞纳金";
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1001002006)
            {
                model.SearchCondition.PageName = "优先权费";
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1001002007)
            {
                model.SearchCondition.PageName = "补充优先权";
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1001002008)
            {
                model.SearchCondition.PageName = "专利补正";
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1001002009)
            {
                model.SearchCondition.PageName = "提复审及缴费";
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1001002010)
            {
                model.SearchCondition.PageName = "缴项目变更费";
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1001002011)
            {
                model.SearchCondition.PageName = "专利补充证据";
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1001002017)
            {
                model.SearchCondition.PageName = "著作权补正";
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1001003001)
            {
                model.SearchCondition.PageName = "商标提出复审";
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1001003002)
            {
                model.SearchCondition.PageName = "商标补正";
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1001003003)
            {
                model.SearchCondition.PageName = "商标补证据";
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1001003004)
            {
                model.SearchCondition.PageName = "商标续展";
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1001003005)
            {
                model.SearchCondition.PageName = "商标初审公布";
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1001003006)
            {
                model.SearchCondition.PageName = "商标异议答辩";
            }

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        public ActionResult AnnualYearFeeList(string id)
        {
            var model = new CaseListModel();
            model.SearchCondition = new Entity.IPR.Case.CaseSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            model.SearchCondition.PageId = id;

            if (id == PageId.PageId_1001015001)
            {
                model.SearchCondition.CaseRequestDateFrom = new DateTime(DateTime.Now.Year, 1, 1);
                model.SearchCondition.CaseRequestDateTo = new DateTime(DateTime.Now.Year, 12, 31);
                model.SearchCondition.ByAFM = true;
                model.SearchCondition.SearchByMonthAndDay = true;
                model.SearchCondition.PageName = (DateTime.Now.ToString("yyyy")) + "全年年费";
            }
            else if (id == PageId.PageId_1001015002)
            {
                model.SearchCondition.CaseRequestDateFrom = new DateTime(DateTime.Now.Year, 1, 1);
                model.SearchCondition.CaseRequestDateTo = new DateTime(DateTime.Now.Year, 3, 31);
                model.SearchCondition.ByAFM = true;
                model.SearchCondition.SearchByMonthAndDay = true;
                model.SearchCondition.PageName = (DateTime.Now.ToString("yy")) + "一季度年费";
            }
            else if (id == PageId.PageId_1001015003)
            {
                model.SearchCondition.CaseRequestDateFrom = new DateTime(DateTime.Now.Year, 4, 1);
                model.SearchCondition.CaseRequestDateTo = new DateTime(DateTime.Now.Year, 6, 30);
                model.SearchCondition.ByAFM = true;
                model.SearchCondition.SearchByMonthAndDay = true;
                model.SearchCondition.PageName = (DateTime.Now.ToString("yy")) + "二季度年费";
            }
            else if (id == PageId.PageId_1001015004)
            {
                model.SearchCondition.CaseRequestDateFrom = new DateTime(DateTime.Now.Year, 7, 1);
                model.SearchCondition.CaseRequestDateTo = new DateTime(DateTime.Now.Year, 9, 30);
                model.SearchCondition.ByAFM = true;
                model.SearchCondition.SearchByMonthAndDay = true;
                model.SearchCondition.PageName = (DateTime.Now.ToString("yy")) + "三季度年费";
            }
            else if (id == PageId.PageId_1001015005)
            {
                model.SearchCondition.CaseRequestDateFrom = new DateTime(DateTime.Now.Year, 10, 1);
                model.SearchCondition.CaseRequestDateTo = new DateTime(DateTime.Now.Year, 12, 31);
                model.SearchCondition.ByAFM = true;
                model.SearchCondition.SearchByMonthAndDay = true;
                model.SearchCondition.PageName = (DateTime.Now.ToString("yy")) + "四季度年费";
            }

            else if (id == PageId.PageId_1001015006)
            {
                model.SearchCondition.CaseRequestDateFrom = new DateTime(DateTime.Now.Year + 1, 1, 1);
                model.SearchCondition.CaseRequestDateTo = new DateTime(DateTime.Now.Year + 1, 3, 31);
                model.SearchCondition.ByAFM = true;
                model.SearchCondition.SearchByMonthAndDay = true;
                model.SearchCondition.PageName = (DateTime.Now.AddYears(1).ToString("yy")) + "一季度年费";
            }

            else if (id == PageId.PageId_1001015007)
            {
                model.SearchCondition.CaseRequestDateFrom = new DateTime(DateTime.Now.Year + 1, 4, 1);
                model.SearchCondition.CaseRequestDateTo = new DateTime(DateTime.Now.Year + 1, 6, 30);
                model.SearchCondition.ByAFM = true;
                model.SearchCondition.SearchByMonthAndDay = true;
                model.SearchCondition.PageName = (DateTime.Now.AddYears(1).ToString("yy")) + "二季度年费";
            }
            else if (id == PageId.PageId_1001015008)
            {
                model.SearchCondition.CaseRequestDateFrom = new DateTime(DateTime.Now.Year + 1, 7, 1);
                model.SearchCondition.CaseRequestDateTo = new DateTime(DateTime.Now.Year + 1, 9, 30);
                model.SearchCondition.ByAFM = true;
                model.SearchCondition.SearchByMonthAndDay = true;
                model.SearchCondition.PageName = (DateTime.Now.AddYears(1).ToString("yy")) + "三季度年费";
            }
            else if (id == PageId.PageId_1001015009)
            {
                model.SearchCondition.CaseRequestDateFrom = new DateTime(DateTime.Now.Year + 1, 10, 1);
                model.SearchCondition.CaseRequestDateTo = new DateTime(DateTime.Now.Year + 1, 12, 31);
                model.SearchCondition.ByAFM = true;
                model.SearchCondition.SearchByMonthAndDay = true;
                model.SearchCondition.PageName = (DateTime.Now.AddYears(1).ToString("yy")) + "四季度年费";
            }


            model.SearchCondition.AccessLevel = (Entity.Account.AccessLevel)LoginHelper.GetAccesslevel();
            model.SearchCondition.UserId = LoginHelper.GetUserName();

            return View(model);
        }

        ///// <summary>
        ///// 
        ///// </summary>
        ///// <param name="id"></param>
        ///// <returns></returns>
        //public ActionResult PatentCaseList(string id)
        //{
        //    var model = new CaseListModel();
        //    model.SearchCondition = new Entity.IPR.Case.CaseSearchCondition();
        //    model.SearchCondition.PageNo = 1;
        //    model.SearchCondition.PageSize = 15;
        //    model.SearchCondition.PageId = id;

        //    if (model.SearchCondition.PageId == PageId.PageId_1001002001)
        //    {
        //        model.SearchCondition.PageName = "申请费";
        //    }
        //    else if (model.SearchCondition.PageId == PageId.PageId_1001002002)
        //    {
        //        model.SearchCondition.PageName = "提实审费";
        //    }
        //    else if (model.SearchCondition.PageId == PageId.PageId_1001002003)
        //    {
        //        model.SearchCondition.PageName = "办登费";
        //    }
        //    else if (model.SearchCondition.PageId == PageId.PageId_1001002004)
        //    {
        //        model.SearchCondition.PageName = "年费";
        //    }
        //    else if (model.SearchCondition.PageId == PageId.PageId_1001002005)
        //    {
        //        model.SearchCondition.PageName = "年费滞纳金";
        //    }
        //    else if (model.SearchCondition.PageId == PageId.PageId_1001002006)
        //    {
        //        model.SearchCondition.PageName = "优先权费";
        //    }
        //    else if (model.SearchCondition.PageId == PageId.PageId_1001002007)
        //    {
        //        model.SearchCondition.PageName = "补充优先权";
        //    }
        //    else if (model.SearchCondition.PageId == PageId.PageId_1001002008)
        //    {
        //        model.SearchCondition.PageName = "专利补正";
        //    }
        //    else if (model.SearchCondition.PageId == PageId.PageId_1001002009)
        //    {
        //        model.SearchCondition.PageName = "提复审及缴费";
        //    }
        //    else if (model.SearchCondition.PageId == PageId.PageId_1001002010)
        //    {
        //        model.SearchCondition.PageName = "缴项目变更费";
        //    }
        //    else if (model.SearchCondition.PageId == PageId.PageId_1001002011)
        //    {
        //        model.SearchCondition.PageName = "专利补充证据";
        //    }
        //    else if (model.SearchCondition.PageId == PageId.PageId_1001002017)
        //    {
        //        model.SearchCondition.PageName = "著作权补正";
        //    }
        //    else if (model.SearchCondition.PageId == PageId.PageId_1001003001)
        //    {
        //        model.SearchCondition.PageName = "商标提出复审";
        //    }
        //    else if (model.SearchCondition.PageId == PageId.PageId_1001003002)
        //    {
        //        model.SearchCondition.PageName = "商标补正";
        //    }
        //    else if (model.SearchCondition.PageId == PageId.PageId_1001003003)
        //    {
        //        model.SearchCondition.PageName = "商标补证据";
        //    }
        //    else if (model.SearchCondition.PageId == PageId.PageId_1001003004)
        //    {
        //        model.SearchCondition.PageName = "商标续展";
        //    }
        //    else if (model.SearchCondition.PageId == PageId.PageId_1001003005)
        //    {
        //        model.SearchCondition.PageName = "商标初审公布";
        //    }
        //    else if (model.SearchCondition.PageId == PageId.PageId_1001003006)
        //    {
        //        model.SearchCondition.PageName = "商标异议答辩";
        //    }

        //    model.SearchCondition.AccessLevel = (Entity.Account.AccessLevel)LoginHelper.GetAccesslevel();
        //    model.SearchCondition.UserId = LoginHelper.GetUserName();

        //    return View("List", model);
        //}

        [HttpPost]
        [CheckUserLogin]
        public JsonResult SearchAnnualYearFeeList(CaseListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                model.SearchCondition.ByAFM = true;
                model.SearchCondition.SearchByMonthAndDay = true;

                var result = new Dchien.Legal.BizModel.IPR.Case.BizCaseSearchResultInfo();

                result.CaseList = CaseAnnualYearService.Instance.GetAnnualYearCaseFeeList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;

                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = "查询出错";
            }
            return Json(response);
        }


        [HttpPost]
        [CheckUserLogin]
        public JsonResult CaseSearchList(CaseListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new Dchien.Legal.BizModel.IPR.Case.BizCaseSearchResultInfo();

                result.CaseList = CaseSearchService.Instance.GetCaseList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;

                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = "查询出错";
            }
            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult CaseListExportToExcel(CaseListModel model)
        {
            var response = new PostResponse();

            try
            {
                model.SearchCondition.PageNo = 1;
                model.SearchCondition.PageSize = Int32.MaxValue;

                var result = new Dchien.Legal.BizModel.IPR.Case.BizCaseSearchResultInfo();

                result.CaseList = CaseSearchService.Instance.GetCaseList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;

                response.IsSuccess = true;
                response.Data = result;

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

                        dr[3] = caseTypes.FirstOrDefault(t => t.CaseTypeId == x.CaseBasicInfo.CaseTypeId) == null ? string.Empty : caseTypes.FirstOrDefault(t => t.CaseTypeId == x.CaseBasicInfo.CaseTypeId).CaseTypeName;
                        dr[4] = casePhases.FirstOrDefault(t => t.CasePhaseId == x.CaseBasicInfo.CasePhaseId) == null ? string.Empty : casePhases.FirstOrDefault(t => t.CasePhaseId == x.CaseBasicInfo.CasePhaseId).CasePhaseName;
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

                    response.IsSuccess = true;
                    response.Data = filename;
                    return Json(response);
                }
                else
                {
                    response.IsSuccess = false;
                    response.Message = "导出错误.";
                    return Json(response);
                }

            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = "导出错误";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>

        [HttpPost]
        [CheckUserLogin]
        public JsonResult AnnualYearExportToExcel(CaseListModel model)
        {
            var response = new PostResponse();

            try
            {
                model.SearchCondition.PageNo = 1;
                model.SearchCondition.PageSize = Int32.MaxValue;
                model.SearchCondition.ByAFM = true;
                model.SearchCondition.SearchByMonthAndDay = true;

                var result = new Dchien.Legal.BizModel.IPR.Case.BizCaseSearchResultInfo();

                result.CaseList = CaseAnnualYearService.Instance.GetAnnualYearCaseFeeList(model.SearchCondition);
                //var lst = CaseAnnualYearService.Instance.GenerateAnnualYearCaseFee(result.CaseList, Convert.ToDateTime("2019-01-01"), Convert.ToDateTime("2019-03-01"));

                var casePhases = CaseTypeService.Instance.GetAllCasePhases();
                var caseTypes = CaseTypeService.Instance.GetAllCaseTypes();

                var sb = new StringBuilder();

                #region header

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

                sb.Append(@"<tr>
                                <th style='text-align: center'>申请人</th>
                                <th style='text-align: center'>专利名称</th>
                                <th style='text-align: center'>案件类型</th>
                                <th style='text-align: center'>案件编号</th>
                                <th style='text-align: center'>申请号</th>
                                <th style='text-align: center'>申请日</th>
                                <th style='text-align: center'>授权日</th>
                                <th style='text-align: center'>年度</th>
                                <th style='text-align: center'>年度开始日期</th>
                                <th style='text-align: center'>年度结束日期</th>
                                <th style='text-align: center'>正常缴费金额</th>
                                <th style='text-align: center'>85%减缓 </th>
                                <th style='text-align: center'>70%减缓 </th>
                                <th style='text-align: center'>本案缴费金额</th>
 
                            </tr>");
                #endregion

                #region body

                result.CaseList.OrderBy(x=>x.CaseBasicInfo.CustomerName).ToList().ForEach(c =>
                {
                    var cusomterName = new List<string>();

                    if (c.CaseCustomers != null && c.CaseCustomers.Any())
                    {
                        c.CaseCustomers.ForEach(x => cusomterName.Add(x.CustomerBasic.CustomerName));
                    }

                    if (c.AnnualYearFee != null)
                    {
                        var caseTypeName = caseTypes.FirstOrDefault(t => t.CaseTypeId == c.CaseBasicInfo.CaseTypeId) == null ? string.Empty : caseTypes.FirstOrDefault(t => t.CaseTypeId == c.CaseBasicInfo.CaseTypeId).CaseTypeName;

                        var tr = "<tr>"
                                 + "<td>" + string.Join(",", cusomterName) + "</td>"
                                 + "<td>" + c.CaseBasicInfo.CaseName + "</td>"
                                 + "<td>" + caseTypeName + "</td>"
                                 + "<td>" + c.CaseBasicInfo.CaseNo + "</td>"
                                 + "<td style=\"mso-number-format:'\\@';\">" + c.CaseBasicInfo.CaseRequestNo + " </td>"
                                 + "<td>" + c.CaseBasicInfo.CaseRequestDate.Value.ToString("yyyy-MM-dd") + "</td>"
                                 + "<td>" + (c.CaseBasicInfo.AuthorizationDate.HasValue ?  c.CaseBasicInfo.AuthorizationDate.Value.ToString("yyyy-MM-dd") : string.Empty) + "</td>"
                                 //+ "<td>" + c.CaseBasicInfo.CaseInventor + "</td>"
                                 + "<td>" + "第" + c.AnnualYearFee.AnnualYear + "年度" + "</td>"
                                 + "<td>" + c.AnnualYearFee.AnnualFrom.ToString("yyyy-MM-dd") + "</td>"
                                 + "<td>" + c.AnnualYearFee.AnnualEnd.ToString("yyyy-MM-dd") + "</td>"
                                 + "<td>" + c.AnnualYearFee.NormalAmout.ToString() + "</td>"
                                 + "<td>" + c.AnnualYearFee.CostSlowRate85Amout.ToString() + "</td>"
                                 + "<td>" + c.AnnualYearFee.CostSlowRate70Amout.ToString() + "</td>"
                                 + "<td>" + c.AnnualYearFee.CaseCostSlowRateAmout.ToString() + "</td>"
                                + "</tr>";

                        sb.Append(tr);
                    }
                });

                #endregion

                sb.Append("</table>");

                template = template.Replace("{table}", sb.ToString());
                template = template.Replace("{worksheet}", "年费清单");

                var fileName = Guid.NewGuid();

                FileHelper.CreateFile(FileHelper.ExportTempFiles, fileName + ".xls", Encoding.GetEncoding("GB2312").GetBytes(template));

                response.IsSuccess = true;
                response.Data = fileName;
                return Json(response);

            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = "导出错误";
            }
            return Json(response);
        }

    }
}