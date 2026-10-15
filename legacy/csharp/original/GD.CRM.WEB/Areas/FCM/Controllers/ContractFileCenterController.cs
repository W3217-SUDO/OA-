using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.Common;
using Dchien.Legal.Service;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Service.FCM.Contract.File;
using Dchien.Legal.Web.Areas.FCM.ViewModels.ContractFile;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Service.Legal.Case;
using Dchien.Legal.Service.BAS.Type;
using Dchien.Legal.Entity.FAM.Invoice;
using Dchien.Legal.Entity.BAS.Type;

namespace Dchien.Legal.Web.Areas.FCM.Controllers
{
    [CheckUserLogin]
    public class ContractFileCenterController : Controller
    {
        internal Log Logger = new Log("FCM.Controllers.ContractFileCenterController");

        #region 合同导出

        /// <summary>
        ///  合同导出
        /// </summary>
        /// <param name="search"></param>
        /// <returns></returns>
        public ActionResult ContractExportToExcel(long contractId)
        {
            var contract = ContractService.Instance.GetContractById(contractId);

            var sb = new StringBuilder();

            #region 合同基本信息

            sb.Append(@"<meta http-equiv='content-type' content='application/ms-excel; charset=gb2312'/>
                        <table cellspacing='0' rules='all' border='1' style='border-collapse:collapse;'>
                                <tr>
                                    <th colspan='14' style='text-align: center'>
                                        <span style='font-weight: bold; font-size: 10pt; '>合同信息-查看</span>
                                    </th>
                                </tr>
                                <tr>
                                    <td>客户名称</td>
                                    <td colspan='3'>" + contract.ContractBasicInfo.CustomerName + @"</td>
                                    <td>客户编码</td>
                                    <td>" + contract.ContractBasicInfo.CustomerNo + @"</td>
                                    <td> 签订日期</td>
                                    <td>" + (contract.ContractBasicInfo.AuditDate.HasValue ? contract.ContractBasicInfo.AuditDate.Value.ToString("yyyy-MM-dd") : string.Empty) + @"</td>
                                    <td></td>
                                    <td></td>
                                    <td></td>
                                    <td></td>
                                    <td></td>
                                    <td></td>
                                </tr>
                                <tr>
                                    <td>合同名称</td>                                    
                                    <td colspan='3'>" + contract.ContractBasicInfo.ContractName + @"</td>
                                    <td>合同编号</td>
                                    <td>" + contract.ContractBasicInfo.ContractNo + @"</td>
                                    <td>客戶管理人</td>
                                    <td>" + contract.ContractBasicInfo.BusinessOwnerName + @"</td>
                                    <td></td>
                                    <td></td>
                                    <td></td>
                                    <td></td>
                                    <td></td>
                                    <td></td>
                                </tr>
                                <tr>
                                    <td rowspan='2'>合同总金额 </td>
                                    <td rowspan='2'>" + contract.ContractBasicInfo.TotalAmount + @"</td>
                                    <td>官费合计</td>
                                    <td>" + contract.ContractBasicInfo.CaseOfficeFeeAmount + @"</td>
                                    <td>回款次数</td>                       
                                    <td>" + contract.ContractBasicInfo.CashedTimes + @"</td>
                                    <td>付款次数</td>
                                    <td>" + contract.ContractBasicInfo.PaidTimes + @"</td>
                                    <td>开票次数</td>
                                    <td>" + contract.ContractBasicInfo.InvoicedTimes + @"</td>
                                    <td></td>
                                    <td></td>
                                    <td></td>
                                    <td></td>
                                </tr>
                                <tr>
                                    <td>代理费合计 </td>
                                    <td>" + contract.ContractBasicInfo.CaseNonOfficeFeeAmount + @"</td>
                                    <td>回款累计  </td>
                                    <td>" + contract.ContractBasicInfo.CashedAmount + @"</td>
                                    <td>已付款金额 </td>
                                    <td>" + contract.ContractBasicInfo.PaidCaseFeeAmount + @"</td>
                                    <td>已开票金额</td>
                                    <td>" + contract.ContractBasicInfo.InvoicedAmount + @"</td>       
                                    <td></td>
                                    <td></td>
                                    <td></td>
                                    <td></td>
                                </tr>
                                <tr>
                                    <td>应付款总计</td>
                                    <td>" + contract.ContractBasicInfo.APAmount + @"</td>                                 
                                    <td>其他费用总计 </td>
                                    <td>" + contract.ContractBasicInfo.CaseCommissionAmount + @"</td>                                 
                                    <td> 应收账款</td>
                                    <td>" + contract.ContractBasicInfo.ARAmount + @"</td>                                 
                                    <td>待付款金额 </td>
                                    <td>" + contract.ContractBasicInfo.UnPaidCaesFeeAmount + @"</td>                                 
                                    <td>可开票金额 </td>
                                    <td>" + contract.ContractBasicInfo.InvoiceAmount + @"</td>    
                                    <td></td>
                                    <td></td>
                                    <td></td>
                                    <td></td>
                                </tr>
                             </table>");

            #endregion

            var contractObjects = ContractService.Instance.GetContractObjects(contractId);
            var invoiceObjects = Dchien.Legal.Service.FAM.Invoice.InvoiceService.Instance.GetInvoiceList(contractId);

            List<Dchien.Legal.BizModel.FAM.AR.Payment.BizPayment> jreceivedObjects = null;
            List<Dchien.Legal.BizModel.FAM.AR.ReceivedPayment.BizPayment> receivedObjects = null;

            if (Dchien.Legal.Service.CompanyService.Instance.GetCompany().CompanyCode == "31253")
            {
                 jreceivedObjects = Dchien.Legal.Service.FAM.AR.Payment.PaymentService.Instance.GetPaymentList(contractId);
            }
            else
            {
                 receivedObjects = Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentService.Instance.GetPaymentList(contractId);
            }

            
            var paidObjects = Dchien.Legal.Service.FAM.AP.Payment.PaymentService.Instance.GetPaymentList(contractId);

            #region 合同标的 标题
            sb.Append(@"<table cellspacing='0' rules='all' border='1' style='border-collapse:collapse;'>
                <colgroup>
                    <col style='width: 4%'>
                    <col style='width: 6%'>
                    <col style='width: 20%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 6%'>
                    <col style='width: 6%'>
                    <col style='width: 6%'>
                    <col style='width: 6%'>
                    <col style='width: 6%'>
                    <col style='width: 6%'>
                    <col style='width: 6%'>
                    <col style='width: 6%'>
                </colgroup>
                <thead>
                    <tr>
                        <td colspan='14' style='text-align: left; font-weight: bold; font-size: 10pt; '>合同标的</td>
                    </tr>
                    <tr>
                        <th>序号</th>
                        <th>案件类型</th>
                        <th>案件名称</th>
                        <th>申请人</th>
                        <th>案号</th>
                        <th>申请号</th>
                        <th>申请日期</th>
                        <th>案件阶段</th>
                        <th>合计</th>
                        <th>官费类型</th>
                        <th>官费金额</th>
                        <th>代理费类型</th>
                        <th>代理费金额</th>
                        <th>其他费用</th>
                    </tr>
                </thead>
                <tbody>");
            #endregion

            #region 合同标的 子项

            var caseFeeTypes = CaseTypeService.Instance.GetAllCaseFeeTypes();
            var casePhases = CaseTypeService.Instance.GetAllCasePhases();

            contractObjects.ForEach(item =>
            {
                var caseInfo = CaseService.Instance.GetCase(item.CaseNo);

                sb.Append(@"<tr>
                                <td><span>" + (contractObjects.IndexOf(item) + 1) + @"</span> </td>
                                <td style='text-align: center'><span>" + CaseTypeService.Instance.GetCaseType(caseInfo.Basic.CaseTypeId.Value).CaseTypeName + @"</span></td>
                                <td style='text-align: center'><span>" + caseInfo.Basic.CaseName + @"</span> </td>
                                <td style='text-align: center'><span>" + caseInfo.Basic.CustomerName + @"</span> </td>
                                <td style='text-align: center;'><span>" + caseInfo.Basic.CaseNo + @"</span> </td>
                                <td style='text-align: center;'><span>" + caseInfo.Basic.FirstIntanceCaseNo + @"&#160;</span></td>
                                <td style='text-align: center;'><span>" + (caseInfo.Basic.CaseRegisterDate.HasValue ? caseInfo.Basic.CaseRegisterDate.Value.ToString("yyyy-MM-dd") : string.Empty) + @"</span></td>
                                <td style='text-align: center;'><span>" + casePhases.FirstOrDefault(x => x.CasePhaseId == caseInfo.Basic.CasePhaseId).CasePhaseName + @"</span> </td>
                                <td style='text-align: center;'><span>" + item.TotalAmount + @"</span> </td>
                                <td style='text-align: center'><span>" + (item.CaseOfficeFeeTypeId.HasValue ? caseFeeTypes.FirstOrDefault(x => x.FeeTypeId == item.CaseOfficeFeeTypeId).FeeTypeName : string.Empty) + @"</span></td>
                                <td style='text-align: center'><span>" + item.CaseOfficeFeeAmount + @"</span></td>
                                <td style='text-align: center'><span>" + (item.CaseNonOfficeFeeTypeId.HasValue ? caseFeeTypes.FirstOrDefault(x => x.FeeTypeId == item.CaseNonOfficeFeeTypeId).FeeTypeName : string.Empty) + @"</span> </td>
                                <td style='text-align: center'><span>" + item.CaseNonOfficeFeeAmount + @"</span></td>
                                <td style='text-align: center'><span>" + item.CaseCommissionFeeAmount + @"</span></td>
                            </tr>");
            });

            sb.Append(@"</tbody></table>");

            #endregion

            #region 回款记录 标题

            sb.Append(@"<table cellspacing='0' rules='all' border='1' style='border-collapse:collapse;'>
                <colgroup>
                    <col style='width: 4%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                </colgroup>
                <thead>
                    <tr> <td colspan='10' style='text-align: left; font-weight: bold; font-size: 10pt; '>回款记录</td></tr>
                    <tr>
                        <th>序号</th>
                        <th>回款单号</th>
                        <th>回款日期</th>
                        <th>银行单据号</th>
                        <th>回款金额</th>
                        <th>官费</th>
                        <th>代理费</th>
                        <th>其他费用费</th>
                        <th>回款方式</th>
                        <th>客戶管理人</th>
                        <td></td>
                        <td></td>
                        <td></td>
                         <td></td>
                    </tr>
                </thead>
                <tbody>");

            #endregion

            #region   回款记录 子项

            if (Dchien.Legal.Service.CompanyService.Instance.GetCompany().CompanyCode == "31253")
            {
                jreceivedObjects = Dchien.Legal.Service.FAM.AR.Payment.PaymentService.Instance.GetPaymentList(contractId);

                jreceivedObjects.ForEach(item =>
                {
                    sb.Append(@"<tr>
                                <td><span>" + (jreceivedObjects.IndexOf(item) + 1) + @"</span> </td>
                                <td style='text-align: center;'><span>" + item.PaymentBasic.SequenceNo + @"</span></td>
                                <td style='text-align: center;'><span>" + (item.PaymentBasic.CashedDate.HasValue ? item.PaymentBasic.CashedDate.Value.ToString("yyyy-MM-dd") : string.Empty) + @"</span> </td>
                                <td style='text-align: center;'><span>" + item.PaymentBasic.InvoiceNo + @"</span> </td>
                                <td style='text-align: center;'><span>" + item.PaymentBasic.CashedAmount + @"</span></td>
                                <td style='text-align: center;'><span>" + item.PaymentBasic.CaseOfficeFeeCashedAmount + @"</span></td>
                                <td style='text-align: center;'><span>" + item.PaymentBasic.CaseNonOfficeFeeCashedAmount + @"</span> </td>
                                <td style='text-align: center'><span>" + item.PaymentBasic.CaseCommissionFeeCashedAmount + @"</span></td>
                                <td style='text-align: center'><span>" + item.PaymentBasic.PaymentModeName + @"</span></td>
                                <td style='text-align: center'><span>" + item.PaymentBasic.BusinessOwnerName + @"</span></td>
                            </tr>");
                });
            }
            else
            {
                receivedObjects = Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentService.Instance.GetPaymentList(contractId);

                receivedObjects.ForEach(item =>
                {
                    sb.Append(@"<tr>
                                <td><span>" + (receivedObjects.IndexOf(item) + 1) + @"</span> </td>
                                <td style='text-align: center;'><span>" + item.PaymentBasic.SequenceNo + @"</span></td>
                                <td style='text-align: center;'><span>" + (item.PaymentBasic.CashedDate.HasValue ? item.PaymentBasic.CashedDate.Value.ToString("yyyy-MM-dd") : string.Empty) + @"</span> </td>
                                <td style='text-align: center;'><span>" + item.PaymentBasic.InvoiceNo + @"</span> </td>
                                <td style='text-align: center;'><span>" + item.PaymentBasic.CashedAmount + @"</span></td>
                                <td style='text-align: center;'><span>" + item.PaymentBasic.CaseOfficeFeeAppliedAmount + @"</span></td>
                                <td style='text-align: center;'><span>" + item.PaymentBasic.CaseNonOfficeFeeAppliedAmount + @"</span> </td>
                                <td style='text-align: center'><span>" + item.PaymentBasic.CaseCommissionFeeAppliedAmount + @"</span></td>
                                <td style='text-align: center'><span>" + item.PaymentBasic.PaymentModeName + @"</span></td>
                                <td style='text-align: center'><span>" + item.PaymentBasic.AppliedOperatorName + @"</span></td>
                            </tr>");
                });

            }


            sb.Append("</tbody></table>");

            #endregion

            #region 开票记录 标题

            sb.Append(@"<table cellspacing='0' rules='all' border='1' style='border-collapse:collapse;'>
                <colgroup>
                    <col style='width: 4%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>

                </colgroup>
                <thead>
                    <tr>
                        <td colspan='10' style='text-align: left; font-weight: bold; font-size: 10pt; '>开票记录</td>
                    </tr>
                    <tr>
                        <th>序号</th>
                        <th>请票单号</th>
                        <th>发票号码</th>
                        <th>开票日期</th>
                        <th>开票金额</th>
                        <th>官费</th>
                        <th>代理费</th>
                        <th>其他费用费</th>
                        <th>状态</th>
                        <th>备注</th>
                        <td></td>
                        <td></td>
                        <td></td>
                        <td></td>
                    </tr>
                </thead>
                <tbody>");
            #endregion

            #region  开票记录 子项

            invoiceObjects.ForEach(item =>
            {
                var line = "";

                if (item.InvoiceBasic.InvoiceStatus == InvoiceStatus.InvoiceCanceled
                    || item.InvoiceBasic.InvoiceStatus == InvoiceStatus.ApplicaionCanceled)
                {
                    line = "style=text-decoration:line-through;";
                }

                sb.Append(@"<tr>
                                <td><span>" + (invoiceObjects.IndexOf(item) + 1) + @"</span> </td>
                                <td style='text-align: center;'><span" + line + ">" + item.InvoiceBasic.InvoiceApplicationNo + @"</span></td>
                                <td style='text-align: center;'><span" + line + ">" + item.InvoiceBasic.InvoiceNo + @"</span> </td>
                                <td style='text-align: center;'><span" + line + ">" + (item.InvoiceBasic.InvoiceDate.HasValue ? item.InvoiceBasic.InvoiceDate.Value.ToString("yyyy-MM-dd") : string.Empty) + @"</span> </td>
                                <td style='text-align: center;'><span" + line + ">" + item.InvoiceBasic.InvoiceAmount + @"</span></td>
                                <td style='text-align: center;'><span" + line + ">" + item.InvoiceBasic.CaseOfficeFeeAmount + @"</span></td>
                                <td style='text-align: center;'><span" + line + ">" + item.InvoiceBasic.CaseNonOfficeFeeAmount + @"</span> </td>
                                <td style='text-align: center;'><span" + line + ">" + item.InvoiceBasic.CaseCommissionFeeAmount + @"</span></td>
                                <td style='text-align: center;'><span" + line + ">" + item.InvoiceBasic.InvoiceStatusName + @"</span></td>
                                <td style='text-align: center;'><span" + line + ">" + item.InvoiceBasic.Remark + @"</span></td>
                                    <td></td>
                                    <td></td>
                                    <td></td>
                                    <td></td>
                            </tr>");
            });

            sb.Append("</tbody></table>");

            #endregion

            #region  付款记录

            sb.Append(@"<table cellspacing='0' rules='all' border='1' style='border-collapse:collapse;'>
                <colgroup>
                    <col style='width: 4%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>
                    <col style='width: 10%'>   
                </colgroup>
                <thead>
                    <tr>
                        <td colspan='10' style='text-align: left; font-weight: bold; font-size: 10pt; '>付款记录</td>
                    </tr>
                    <tr>
                        <th>序号</th>
                        <th>申请单号</th>
                        <th>申请人</th>
                        <th>待付金额</th>
                        <th>付款日期</th>
                        <th>付款单据</th>
                        <th>付款金额</th>
                        <th>付款类型</th>
                        <th>官费</th>
                        <th>其他费用费</th>
                                    <td></td>
                                    <td></td>
                                    <td></td>
                                    <td></td>
                    </tr>
                </thead>
                <tbody>");

            paidObjects.ForEach(item =>
            {

                var line = "";

                if (item.PaymentBasic.PaymentStatus == Dchien.Legal.Entity.FAM.AP.Payment.PaymentStatus.ApplicaionCanceled)
                {
                    line = "style=text-decoration:line-through;";
                }

                sb.Append(@"<tr>
                                <td><span>" + (paidObjects.IndexOf(item) + 1) + @"</span> </td>
                                <td style='text-align: center;'><span" + line + ">" + item.PaymentBasic.ApplicationNo + @"</span></td>
                                <td style='text-align: center;'><span" + line + ">" + item.PaymentBasic.ApplicantName + @"</span> </td>
                                <td style='text-align: center;'><span" + line + ">" + (item.PaymentBasic.PaymentStatus == Dchien.Legal.Entity.FAM.AP.Payment.PaymentStatus.Packing
                || item.PaymentBasic.PaymentStatus == Dchien.Legal.Entity.FAM.AP.Payment.PaymentStatus.Paid ? 0 : item.PaymentBasic.PaidAmount) + @"</span> </td>
                                <td style='text-align: center;'><span" + line + ">" + (item.PaymentBasic.PaymentDate.HasValue ? item.PaymentBasic.PaymentDate.Value.ToString("yyyy-MM-dd") : string.Empty) + @"</span></td>
                                <td style='text-align: center;'><span" + line + ">" + item.PaymentBasic.PackageNo + @"</span></td>
                                <td style='text-align: center;'><span" + line + ">" + (item.PaymentBasic.PaymentStatus == Dchien.Legal.Entity.FAM.AP.Payment.PaymentStatus.Packing
                || item.PaymentBasic.PaymentStatus == Dchien.Legal.Entity.FAM.AP.Payment.PaymentStatus.Paid ? item.PaymentBasic.PaidAmount : 0) + @"</span> </td>
                                <td style='text-align: center;'><span" + line + ">" + item.PaymentType.PaymentTypeName + @"</span></td>
                                <td style='text-align: center;'><span" + line + ">" + (item.PaymentType.CaseFeeTypeId == (int)CaseFeeTypeId.Office ? item.PaymentBasic.PaidAmount : 0) + @"</span></td>
                                <td style='text-align: center;'><span" + line + ">" + (item.PaymentType.CaseFeeTypeId == (int)CaseFeeTypeId.Commission ? item.PaymentBasic.PaidAmount : 0) + @"</span></td>
                                    <td></td>
                                    <td></td>
                                    <td></td>
                                    <td></td>
</tr>");
            });

            sb.Append("</tbody></table>");

            #endregion

            //sb.Append("</table>");

            var fileName = Guid.NewGuid();

            // 返回客户端  
            var bytes = Encoding.GetEncoding("GB2312").GetBytes(sb.ToString());

            Response.Charset = "gb2312";
            Response.ContentEncoding = Encoding.GetEncoding("GB2312");
            Response.ContentType = "application/vnd.ms-excel";

            Response.AppendHeader("Content-Disposition", "attachment;filename=" + fileName + ".xls");

            return File(bytes, "attachment;filename=" + fileName);

            //FileHelper.CreateFile(FileHelper.ExportTempFiles, fileName + ".xls", Encoding.GetEncoding("GB2312").GetBytes(sb.ToString()));

            //var response = new PostResponse();
            //response.IsSuccess = true;
            //response.Data = fileName;
            //return Json(response);
        }

        #endregion

        #region 合同列表导出

        /// <summary>
        /// 下载文件
        /// </summary>
        /// <param name="search"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult ContractListExportToExcel(Dchien.Legal.Web.Areas.FCM.ViewModels.Contract.ListModel model)
        {
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 60000;

            if (model.SearchCondition.PageId == PageId.PageId_4001002)
            {
                model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
            }
            else if (model.SearchCondition.PageId == PageId.PageId_4001006)
            {
                model.SearchCondition.DepartmentId = LoginHelper.GetDepartmentId();
            }
            else if (model.SearchCondition.PageId == PageId.PageId_4001007)
            {
                model.SearchCondition.CompanyId = LoginHelper.GetCompanyId();
            }

            var result = new BizContractSearchResultInfo();

            result.ContractList = ContractService.Instance.GetContractList(model.SearchCondition);

            result.TotalItemCount = model.SearchCondition.TotalCount;
            result.PageNo = model.SearchCondition.PageNo;
            result.PageSize = model.SearchCondition.PageSize;

            var sb = new StringBuilder();

            #region header

            sb.Append(@"<meta http-equiv='content-type' content='application/ms-excel; charset=gb2312'/>
                        <table cellspacing='0' rules='all' border='1' style='border-collapse:collapse;'>
                        <tr>
                            <th style='text-align: center'>合同号</th>
                            <th style='text-align: center'>合同名称</th>
                            <th style='text-align: center'>合同状态</th>
                            <th style='text-align: center'>合同总金额</th>
                            <th style='text-align: center'>回款累计</th>
                            <th style='text-align: center'>应收账款</th>
                            <th style='text-align: center'>客戶管理人</th>
                            <th style='text-align: center'>签订日期</th>
                            <th style='text-align: center'>客户编号</th>
                            <th style='text-align: center'>客户名称</th>
                        </tr>");

            #endregion

            #region body

            result.ContractList.ForEach(c =>
            {

                var tr = "<tr>"
                     + "<td>" + c.ContractBasicInfo.ContractNo + "</td>"
                     + "<td>" + c.ContractBasicInfo.ContractName + "</td>"
                     + "<td>" + c.ContractBasicInfo.ContractStatusName + "</td>"
                     + "<td>" + c.ContractBasicInfo.TotalAmount + "</td>"
                     + "<td>" + c.ContractBasicInfo.CashedAmount + "</td>"
                     + "<td>" + c.ContractBasicInfo.ARAmount + "</td>"
                     + "<td>" + c.ContractBasicInfo.BusinessOwnerName + "</td>"
                     + "<td style='text-align: center'>" + (c.ContractBasicInfo.AuditDate.HasValue ? c.ContractBasicInfo.AuditDate.Value.ToString("yyyy-MM-dd") : string.Empty) + "</td>"
                     + "<td>" + c.ContractBasicInfo.CustomerNo + "</td>"
                     + "<td>" + c.ContractBasicInfo.CustomerName + "</td>"
                     + "</tr>";

                sb.Append(tr);

            });

            #endregion

            sb.Append("</table>");

            var fileName = Guid.NewGuid();

            FileHelper.CreateFile(FileHelper.ExportTempFiles, fileName + ".xls", Encoding.GetEncoding("GB2312").GetBytes(sb.ToString()));

            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = fileName;
            return Json(response);
        }

        /// <summary>
        /// 下载文件
        /// </summary>
        /// <param name="search"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult ContractRejectedListExportToExcel(Dchien.Legal.Web.Areas.FCM.ViewModels.ContractAudit.ListModel model)
        {
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 60000;

            model.SearchCondition.ContractStatus = Dchien.Legal.Entity.FCM.Contract.ContractStatus.R;

            model.SearchCondition.AuditStatus = AuditStatus.R;
            model.SearchCondition.CurrentAuditor = LoginHelper.GetUserName();

            var result = new BizContractSearchResultInfo();

            result.ContractList = ContractService.Instance.GetRejectedContractList(model.SearchCondition);

            result.TotalItemCount = model.SearchCondition.TotalCount;
            result.PageNo = model.SearchCondition.PageNo;
            result.PageSize = model.SearchCondition.PageSize;

            var sb = new StringBuilder();

            #region header

            sb.Append(@"<meta http-equiv='content-type' content='application/ms-excel; charset=gb2312'/>
                        <table cellspacing='0' rules='all' border='1' style='border-collapse:collapse;'>
                        <tr>
                            <th style='text-align: center'>合同号</th>
                            <th style='text-align: center'>合同名称</th>
                            <th style='text-align: center'>合同状态</th>
                            <th style='text-align: center'>合同总金额</th>
                            <th style='text-align: center'>回款累计</th>
                            <th style='text-align: center'>应收账款</th>
                            <th style='text-align: center'>客戶管理人</th>
                            <th style='text-align: center'>签订日期</th>
                            <th style='text-align: center'>客户编号</th>
                            <th style='text-align: center'>客户名称</th>
                        </tr>");

            #endregion

            #region body

            result.ContractList.ForEach(c =>
            {

                var tr = "<tr>"
                     + "<td>" + c.ContractBasicInfo.ContractNo + "</td>"
                     + "<td>" + c.ContractBasicInfo.ContractName + "</td>"
                     + "<td>" + c.ContractBasicInfo.ContractStatusName + "</td>"
                     + "<td>" + c.ContractBasicInfo.TotalAmount + "</td>"
                     + "<td>" + c.ContractBasicInfo.CashedAmount + "</td>"
                     + "<td>" + c.ContractBasicInfo.ARAmount + "</td>"
                     + "<td>" + c.ContractBasicInfo.BusinessOwnerName + "</td>"
                     + "<td style='text-align: center'>" + (c.ContractBasicInfo.AuditDate.HasValue ? c.ContractBasicInfo.AuditDate.Value.ToString("yyyy-MM-dd") : string.Empty) + "</td>"
                     + "<td>" + c.ContractBasicInfo.CustomerNo + "</td>"
                     + "<td>" + c.ContractBasicInfo.CustomerName + "</td>"
                     + "</tr>";

                sb.Append(tr);

            });

            #endregion

            sb.Append("</table>");

            var fileName = Guid.NewGuid();

            FileHelper.CreateFile(FileHelper.ExportTempFiles, fileName + ".xls", Encoding.GetEncoding("GB2312").GetBytes(sb.ToString()));

            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = fileName;
            return Json(response);
        }

        [HttpPost]
        public ActionResult ContractPendingListExportToExcel(Dchien.Legal.Web.Areas.FCM.ViewModels.ContractAudit.ListModel model)
        {
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 60000;

            model.SearchCondition.AuditStatus = AuditStatus.P;
            model.SearchCondition.CurrentAuditor = LoginHelper.GetUserName();

            var result = new BizContractSearchResultInfo();

            result.ContractList = ContractService.Instance.GetPendingContractList(model.SearchCondition);

            result.TotalItemCount = model.SearchCondition.TotalCount;
            result.PageNo = model.SearchCondition.PageNo;
            result.PageSize = model.SearchCondition.PageSize;

            var sb = new StringBuilder();

            #region header

            sb.Append(@"<meta http-equiv='content-type' content='application/ms-excel; charset=gb2312'/>
                        <table cellspacing='0' rules='all' border='1' style='border-collapse:collapse;'>
                        <tr>
                            <th style='text-align: center'>合同号</th>
                            <th style='text-align: center'>合同名称</th>
                            <th style='text-align: center'>合同状态</th>
                            <th style='text-align: center'>合同总金额</th>
                            <th style='text-align: center'>回款累计</th>
                            <th style='text-align: center'>应收账款</th>
                            <th style='text-align: center'>客戶管理人</th>
                            <th style='text-align: center'>签订日期</th>
                            <th style='text-align: center'>客户编号</th>
                            <th style='text-align: center'>客户名称</th>
                        </tr>");

            #endregion

            #region body

            result.ContractList.ForEach(c =>
            {

                var tr = "<tr>"
                     + "<td>" + c.ContractBasicInfo.ContractNo + "</td>"
                     + "<td>" + c.ContractBasicInfo.ContractName + "</td>"
                     + "<td>" + c.ContractBasicInfo.ContractStatusName + "</td>"
                     + "<td>" + c.ContractBasicInfo.TotalAmount + "</td>"
                     + "<td>" + c.ContractBasicInfo.CashedAmount + "</td>"
                     + "<td>" + c.ContractBasicInfo.ARAmount + "</td>"
                     + "<td>" + c.ContractBasicInfo.BusinessOwnerName + "</td>"
                     + "<td style='text-align: center'>" + (c.ContractBasicInfo.AuditDate.HasValue ? c.ContractBasicInfo.AuditDate.Value.ToString("yyyy-MM-dd") : string.Empty) + "</td>"
                     + "<td>" + c.ContractBasicInfo.CustomerNo + "</td>"
                     + "<td>" + c.ContractBasicInfo.CustomerName + "</td>"
                     + "</tr>";

                sb.Append(tr);

            });

            #endregion

            sb.Append("</table>");

            var fileName = Guid.NewGuid();

            FileHelper.CreateFile(FileHelper.ExportTempFiles, fileName + ".xls", Encoding.GetEncoding("GB2312").GetBytes(sb.ToString()));

            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = fileName;
            return Json(response);
        }

        [HttpPost]
        public ActionResult ContractApprovedListExportToExcel(Dchien.Legal.Web.Areas.FCM.ViewModels.ContractAudit.ListModel model)
        {
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 60000;

            model.SearchCondition.ContractStatus = Dchien.Legal.Entity.FCM.Contract.ContractStatus.A;

            model.SearchCondition.AuditStatus = AuditStatus.A;
            model.SearchCondition.CurrentAuditor = LoginHelper.GetUserName();

            var result = new BizContractSearchResultInfo();

            result.ContractList = ContractService.Instance.GetApprovedContractList(model.SearchCondition);

            result.TotalItemCount = model.SearchCondition.TotalCount;
            result.PageNo = model.SearchCondition.PageNo;
            result.PageSize = model.SearchCondition.PageSize;

            var sb = new StringBuilder();

            #region header

            sb.Append(@"<meta http-equiv='content-type' content='application/ms-excel; charset=gb2312'/>
                        <table cellspacing='0' rules='all' border='1' style='border-collapse:collapse;'>
                        <tr>
                            <th style='text-align: center'>合同号</th>
                            <th style='text-align: center'>合同名称</th>
                            <th style='text-align: center'>合同状态</th>
                            <th style='text-align: center'>合同总金额</th>
                            <th style='text-align: center'>回款累计</th>
                            <th style='text-align: center'>应收账款</th>
                            <th style='text-align: center'>客戶管理人</th>
                            <th style='text-align: center'>签订日期</th>
                            <th style='text-align: center'>客户编号</th>
                            <th style='text-align: center'>客户名称</th>
                        </tr>");

            #endregion

            #region body

            result.ContractList.ForEach(c =>
            {

                var tr = "<tr>"
                     + "<td>" + c.ContractBasicInfo.ContractNo + "</td>"
                     + "<td>" + c.ContractBasicInfo.ContractName + "</td>"
                     + "<td>" + c.ContractBasicInfo.ContractStatusName + "</td>"
                     + "<td>" + c.ContractBasicInfo.TotalAmount + "</td>"
                     + "<td>" + c.ContractBasicInfo.CashedAmount + "</td>"
                     + "<td>" + c.ContractBasicInfo.ARAmount + "</td>"
                     + "<td>" + c.ContractBasicInfo.BusinessOwnerName + "</td>"
                     + "<td style='text-align: center'>" + (c.ContractBasicInfo.AuditDate.HasValue ? c.ContractBasicInfo.AuditDate.Value.ToString("yyyy-MM-dd") : string.Empty) + "</td>"
                     + "<td>" + c.ContractBasicInfo.CustomerNo + "</td>"
                     + "<td>" + c.ContractBasicInfo.CustomerName + "</td>"
                     + "</tr>";

                sb.Append(tr);

            });

            #endregion

            sb.Append("</table>");

            var fileName = Guid.NewGuid();

            FileHelper.CreateFile(FileHelper.ExportTempFiles, fileName + ".xls", Encoding.GetEncoding("GB2312").GetBytes(sb.ToString()));

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
        [HttpGet]
        public ActionResult ContractListExportToExcelDownload(string fileName)
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

        #region 应收账款明细导出

        /// <summary>
        /// 下载文件
        /// </summary>
        /// <param name="search"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult ContractARItemListExportToExcel(Dchien.Legal.Web.Areas.FCM.ViewModels.AR.ListModel model)
        {
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 60000;
            model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();

            var result = new BizContractSearchResultInfo();

            result.ContractList = ContractService.Instance.GetContractARItemList(model.SearchCondition);


            result.TotalAmount = model.SearchCondition.TotalAmount;
            result.TotalCashedAmount = model.SearchCondition.TotalCashedAmount;
            result.TotalARAmount = model.SearchCondition.TotalARAmount;
            result.TotalCaseOfficeFeeARAmount = model.SearchCondition.TotalCaseOfficeFeeARAmount;
            result.TotalCaseNonOfficeFeeARAmount = model.SearchCondition.TotalCaseNonOfficeFeeARAmount;

            result.TotalItemCount = model.SearchCondition.TotalCount;
            result.PageNo = model.SearchCondition.PageNo;
            result.PageSize = model.SearchCondition.PageSize;

            var sb = new StringBuilder();

            #region header
            sb.Append(@"<meta http-equiv='content-type' content='application/ms-excel; charset=gb2312'/>
                        <table cellspacing='0' rules='all' border='1' style='border-collapse:collapse;'>
                         <tr>
                            <th style='text-align: center'></th>
                            <th style='text-align: center'></th>
                            <th style='text-align: center'></th>
                            <th style='text-align: center'></th>
                            <th style='text-align: center'></th>
                            <th style='text-align: center'>应收账款合计：</td>
                            <th style='text-align: center'>" + result.TotalARAmount + @"</th>
                            <th style='text-align: center'></th>
                            <th style='text-align: center'></th>
                            <th style='text-align: center'></th>
                            <th style='text-align: center'></th>
                            <th style='text-align: center'></th>
                            <th style='text-align: center'></th>
                     </tr>
                        <tr>
                            <th style='text-align: center'>合同号</th>
                            <th style='text-align: center'>合同名称</th>
                            <th style='text-align: center'>建立日期</th>
                            <th style='text-align: center'>合同总金额</th>
                            <th style='text-align: center'>已回收金额</th>
                            <th style='text-align: center'>应收账款</th>
                            <th style='text-align: center'>案号</th>
                            <th style='text-align: center'>案件类型</th>
                            <th style='text-align: center'>案件名称</th>
                            <th style='text-align: center'>费用类型</th>
                            <th style='text-align: center'>费用金额</th>
                            <th style='text-align: center'>已收</th>
                            <th style='text-align: center'>应收</th>
                        </tr>");

            #endregion

            var contractNo = string.Empty;

            var caseFeeTypes =  CaseTypeService.Instance.GetAllCaseFeeTypes();

            #region body

            result.ContractList.ForEach(c =>
            {
                c.ContractObjectList.ForEach(contractObject =>
                {
                    var tr = string.Empty;

                    var caseTypeName =  CaseTypeService.Instance.GetCaseType(contractObject.CaseTypeId).CaseTypeName;
                    var caseFeeTypeName = caseFeeTypes.FirstOrDefault(f =>  contractObject.CaseFeeTypeId != -100 && f.FeeTypeId == contractObject.CaseFeeTypeId) == null ? string.Empty : caseFeeTypes.FirstOrDefault(f => f.FeeTypeId == contractObject.CaseFeeTypeId).FeeTypeName;

                    if (contractNo != c.ContractBasicInfo.ContractNo)
                    {
                        tr = "<tr>"
                            + "<td rowspan=" + c.ContractObjectList.Count + ">" + c.ContractBasicInfo.ContractNo + "</td>"
                            + "<td rowspan=" + c.ContractObjectList.Count + ">" + c.ContractBasicInfo.ContractName + "</td>"
                            + "<td rowspan=" + c.ContractObjectList.Count + ">" + (c.ContractBasicInfo.AuditDate.HasValue ? c.ContractBasicInfo.AuditDate.Value.ToString("yyyy-MM-dd") : string.Empty) + "</td>"
                            + "<td rowspan=" + c.ContractObjectList.Count + ">" + c.ContractBasicInfo.TotalAmount + "</td>"
                            + "<td rowspan=" + c.ContractObjectList.Count + ">" + c.ContractBasicInfo.CashedAmount + "</td>"
                            + "<td rowspan=" + c.ContractObjectList.Count + ">" + c.ContractBasicInfo.ARAmount + "</td>"
                            + "<td>" + contractObject.CaseNo + "</td>"
                            + "<td style='text-align: center'>" + caseTypeName + "</td>"
                            + "<td>" + contractObject.CaseName + "</td>"
                            + "<td style='text-align: center'>" + caseFeeTypeName + "</td>"
                            + "<td>" + (contractObject.CaseFeeAmount == null ? 0 : contractObject.CaseFeeAmount) + "</td>"
                            + "<td>" + contractObject.TotalCashedAmount + "</td>"
                            + "<td>" + (contractObject.TotalAmount - contractObject.TotalCashedAmount) + "</td>"
                            + "</tr>";
                        contractNo = c.ContractBasicInfo.ContractNo;
                    }
                    else
                    {
                        tr = "<tr>"
                            + "<td>" + contractObject.CaseNo + "</td>"
                            + "<td style='text-align: center'>" + caseTypeName + "</td>"
                            + "<td>" + contractObject.CaseName + "</td>"
                            + "<td style='text-align: center'>" + caseFeeTypeName + "</td>"
                            + "<td>" + (contractObject.CaseFeeAmount == null ? 0 : contractObject.CaseFeeAmount) + "</td>"
                            + "<td>" + contractObject.TotalCashedAmount + "</td>"
                            + "<td>" + (contractObject.TotalAmount - contractObject.TotalCashedAmount) + "</td>"
                            + "</tr>";
                    }

                    sb.Append(tr);
                });
            });

            #endregion

            sb.Append("</table>");

            var fileName = Guid.NewGuid();

            FileHelper.CreateFile(FileHelper.ExportTempFiles, fileName + ".xls", Encoding.GetEncoding("GB2312").GetBytes(sb.ToString()));

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
        [HttpGet]
        public ActionResult ContractARItemListExportToExcelDownload(string fileName)
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

        #region 应收账款导出

        /// <summary>
        /// 下载文件
        /// </summary>
        /// <param name="search"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult ContractARListExportToExcel(Dchien.Legal.Web.Areas.FCM.ViewModels.AR.ListModel model)
        {
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 60000;

            if (model.SearchCondition.PageId == PageId.PageId_4001009)
            {
                model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
            }
            else if (model.SearchCondition.PageId == PageId.PageId_4001010)
            {
                model.SearchCondition.DepartmentId = LoginHelper.GetDepartmentId();
            }
            else if (model.SearchCondition.PageId == PageId.PageId_4001011)
            {
                model.SearchCondition.CompanyId = LoginHelper.GetCompanyId();
            }

            var result = new BizContractSearchResultInfo();

            result.ContractList = ContractService.Instance.GetContractARList(model.SearchCondition);
            result.ContractList = result.ContractList.FindAll(x => x.ContractBasicInfo.TotalAmount > x.ContractBasicInfo.CashedAmount);


            result.TotalAmount = model.SearchCondition.TotalAmount;
            result.TotalCashedAmount = model.SearchCondition.TotalCashedAmount;
            result.TotalARAmount = model.SearchCondition.TotalARAmount;
            result.TotalCaseOfficeFeeARAmount = model.SearchCondition.TotalCaseOfficeFeeARAmount;
            result.TotalCaseNonOfficeFeeARAmount = model.SearchCondition.TotalCaseNonOfficeFeeARAmount;

            result.TotalItemCount = model.SearchCondition.TotalCount;
            result.PageNo = model.SearchCondition.PageNo;
            result.PageSize = model.SearchCondition.PageSize;

            var sb = new StringBuilder();

            #region header
            sb.Append(@"<meta http-equiv='content-type' content='application/ms-excel; charset=gb2312'/>
                        <table cellspacing='0' rules='all' border='1' style='border-collapse:collapse;'>
                         <tr>
                            <th style='text-align: center'></th>
                            <th style='text-align: center'></th>
                            <th style='text-align: center'></th>
                            <th style='text-align: center'></th>
                            <th style='text-align: center'>应收账款合计：</td>
                            <th style='text-align: center'>" + result.TotalARAmount + @"</th>
                            <th style='text-align: center'></th>
                            <th style='text-align: center'></th>
                            <th style='text-align: center'></th>
                            <th style='text-align: center'></th>
                        </tr>
                        <tr>
                            <th style='text-align: center'>合同号</th>
                            <th style='text-align: center'>合同名称</th>
                            <th style='text-align: center'>合同状态</th>
                            <th style='text-align: center'>合同总金额</th>
                            <th style='text-align: center'>回款累计</th>
                            <th style='text-align: center'>应收账款</th>
                            <th style='text-align: center'>客戶管理人</th>
                            <th style='text-align: center'>签订日期</th>
                            <th style='text-align: center'>客户编号</th>
                            <th style='text-align: center'>客户名称</th>
                        </tr>");

            #endregion

            #region body

            result.ContractList.ForEach(c =>
            {

                var tr = "<tr>"
                     + "<td>" + c.ContractBasicInfo.ContractNo + "</td>"
                     + "<td>" + c.ContractBasicInfo.ContractName + "</td>"
                     + "<td>" + c.ContractBasicInfo.ContractStatusName + "</td>"
                     + "<td>" + c.ContractBasicInfo.TotalAmount + "</td>"
                     + "<td>" + c.ContractBasicInfo.CashedAmount + "</td>"
                     + "<td>" + c.ContractBasicInfo.ARAmount + "</td>"
                     + "<td>" + c.ContractBasicInfo.BusinessOwnerName + "</td>"
                     + "<td style='text-align: center'>" + (c.ContractBasicInfo.AuditDate.HasValue ? c.ContractBasicInfo.AuditDate.Value.ToString("yyyy-MM-dd") : string.Empty) + "</td>"
                     + "<td>" + c.ContractBasicInfo.CustomerNo + "</td>"
                     + "<td>" + c.ContractBasicInfo.CustomerName + "</td>"
                     + "</tr>";

                sb.Append(tr);

            });

            #endregion

            sb.Append("</table>");

            var fileName = Guid.NewGuid();

            FileHelper.CreateFile(FileHelper.ExportTempFiles, fileName + ".xls", Encoding.GetEncoding("GB2312").GetBytes(sb.ToString()));

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
        [HttpGet]
        public ActionResult ContractARListExportToExcelDownload(string fileName)
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
