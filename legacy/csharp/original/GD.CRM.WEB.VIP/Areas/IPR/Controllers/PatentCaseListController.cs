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
    public class PatentCaseListController : BaseController
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

            if (model.SearchCondition.PageId == PageId.PageId_1001002001)
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

            model.SearchCondition.AccessLevel = (Entity.Account.AccessLevel)LoginHelper.GetAccesslevel();
            model.SearchCondition.UserId = LoginHelper.GetUserName();

            return View("CaseList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
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

                model.SearchCondition.AccessLevel = Entity.Account.AccessLevel.User;

                model.SearchCondition.UserId = LoginHelper.GetUserName();

                if (model.SearchCondition.PageId == PageId.PageId_1001001010)
                {
                    model.SearchCondition.AccessLevel = (Entity.Account.AccessLevel)LoginHelper.GetAccesslevel();
                }

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

                    FileHelper.CreateFile(FileHelper.TemplateFiles, filename + ".xls",
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

     }
}