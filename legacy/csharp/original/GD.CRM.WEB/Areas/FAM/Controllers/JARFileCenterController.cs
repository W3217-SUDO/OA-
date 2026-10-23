using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using System.Text;
using System.IO;
using Dchien.Legal.BizModel.FAM.AR.Payment;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FAM.AR.Payment;
using Dchien.Legal.Entity.FCM.Contract;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.FAM.AR.Payment;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Web.Areas.FAM.ViewModels.AR.Payment;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using ListModel = Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ListModel;
using Dchien.Legal.Service;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class JARFileCenterController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.JARFileCenterController");

        /// <summary>
        /// 开票信息导出
        /// </summary>
        /// <param name="search"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult PaymentListExportToExcel(Dchien.Legal.Web.Areas.FAM.ViewModels.AR.Payment.ListModel model)
        {
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 60000;

            if (model.SearchCondition.PageNo == 0)
                model.SearchCondition.PageNo = 1;
            if (model.SearchCondition.PageSize == 0)
                model.SearchCondition.PageSize = 15;

            var result = new BizPaymentSearchResultInfo();

            result.PaymentList = PaymentService.Instance.GetPaymentList(model.SearchCondition);

            var sb = new StringBuilder();


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

            #region header

            sb.Append(@" 
                        <tr>
                            <th style='text-align: center'>银行单据号</th>
                            <th style='text-align: center'>合同编号</th>
                            <th style='text-align: center'>客户名称</th>
                            <th style='text-align: center'>回款单位</th>
                            <th style='text-align: center'>客戶管理人</th>
                            <th style='text-align: center'>回款日期</th>
                            <th style='text-align: center'>回款金额</th>
                            <th style='text-align: center'>官费</th>
                            <th style='text-align: center'>代理费</th>
                            <th style='text-align: center'>其他费用</th>
                            <th style='text-align: center'>回款方式</th>
                        </tr>");

            #endregion

            #region body

            result.PaymentList.ForEach(c =>
            {
                c = PaymentService.Instance.GetPayment(c.PaymentBasic.PaymentId.Value);

                //var contract = ContractService.Instance.GetContractBasicById(c.PaymentBasic.ContractId);
                var customer = CustomerService.Instance.GetCustomerBasicById(c.PaymentBasic.CustomerId);

                var totalCashedAmount = c.PaymentObjects.Sum(x => x.CaseOfficeFeeCashedAmount + x.CaseNonOfficeFeeCashedAmount);
                var totalCaseOfficeFeeCashedAmount = c.PaymentObjects.Sum(x => x.CaseOfficeFeeCashedAmount);
                var totalCaseNonOfficeFeeCashedAmount = c.PaymentObjects.Sum(x => x.CaseNonOfficeFeeCashedAmount);

                var tr = "<tr>"
                     + "<td style='color:#06C'>" + c.PaymentBasic.InvoiceNo + "</td>"
                     + "<td>" + c.PaymentBasic.ContractNo + "</td>"
                     + "<td>" + customer.CustomerBasic.CustomerName + "</td>"
                     + "<td>" + c.PaymentBasic.PayerName + "</td>"
                     + "<td>" + c.PaymentBasic.BusinessOwnerName + "</td>"
                     +"<td style='text-align: center'>" + (c.PaymentBasic.CashedDate.HasValue ? c.PaymentBasic.CashedDate.Value.ToString("yyyy-MM-dd") : string.Empty) + "</td>"
                     + "<td>" + "￥" + c.PaymentBasic.CashedAmount.ToString("###,##0.00") + "</td>"
                     + "<td>" + "￥" + c.PaymentBasic.CaseOfficeFeeCashedAmount.ToString("###,##0.00") + "</td>"
                     + "<td>" + "￥" + c.PaymentBasic.CaseNonOfficeFeeCashedAmount.ToString("###,##0.00") + "</td>"
                     + "<td >" + "￥" + c.PaymentBasic.CaseCommissionFeeCashedAmount.ToString("###,##0.00") + "</td>"
                     + "<td>" + c.PaymentBasic.PaymentModeName + "</td>"
                     + "</tr>";

                sb.Append(tr);

            });

            #endregion

            template = template.Replace("{table}", sb.ToString());
            template = template.Replace("{worksheet}", "回款信息");

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
        public ActionResult PaymentListExportToExcelDownload(string fileName)
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
