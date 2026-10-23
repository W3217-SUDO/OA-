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

using Dchien.Legal.BizModel.FAM.AP.Payment;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.Account;
using Dchien.Legal.Entity.FAM.AP.Payment;
using Dchien.Legal.Entity.FAM.AP.Payment.Packing;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.FAM.AP;
using Dchien.Legal.Service.FAM.AP.Payment;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Web.Areas.FAM.ViewModels.AP.Payment;
using Dchien.Legal.Web.Areas.FAM.ViewModels.AP.Payment.Packing;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using ListModel = Dchien.Legal.Web.Areas.FAM.ViewModels.AP.Payment.ListModel;
using Dchien.Legal.Entity.BAS.Type;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class APController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.APController");


        [CheckUserLogin]
        public ActionResult PaymentCreate(long contractId, string batchNos)
        {
            var model = new PaymentModel();

            model.Payment = PaymentService.Instance.CreatePayment(contractId,new List<long>());

            if (model.Payment != null)
            {
                var contract = ContractService.Instance.GetContractById(contractId);

                model.Contract = contract;
                model.Customer = contract.ContractBasicInfo.CustomerId.HasValue ? CustomerService.Instance.GetCustomerById(contract.ContractBasicInfo.CustomerId.Value) : null;
                model.Payment.PaymentBasic.PayerName = model.Customer == null ? string.Empty : model.Customer.CustomerBasic.CustomerName;

                if (!string.IsNullOrEmpty(batchNos))
                {
                    var batchNoList = batchNos.Split(',').ToList();
                    model.Payment.PaymentObjects = model.Payment.PaymentObjects.FindAll(x => batchNoList.Contains(x.BatchNo));
                }
            }

            return View("Payment/Create", model);
        }

        ///// <summary>
        ///// 
        ///// </summary>
        ///// <param name="contractId"></param>
        ///// <returns></returns>
        //[CheckUserLogin]
        //public ActionResult PaymentCreate(long contractId)
        //{
        //    var model = new PaymentModel();

        //    model.Payment = PaymentService.Instance.CreatePayment(contractId);

        //    if (model.Payment != null)
        //    {
        //        var contract = ContractService.Instance.GetContractById(contractId);

        //        model.Contract = contract;
        //        model.Customer = contract.ContractBasicInfo.CustomerId.HasValue ? CustomerService.Instance.GetCustomerById(contract.ContractBasicInfo.CustomerId.Value) : null;
        //        model.Payment.PaymentBasic.PayerName = model.Customer == null ? string.Empty : model.Customer.CustomerBasic.CustomerName;
        //    }

        //    return View("Payment/Create", model);
        //}

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentEdit(long paymentId)
        {
            var model = new PaymentModel();

            model.Payment = PaymentService.Instance.GetPayment(paymentId);

            if (model.Payment != null)
            {
                var contract = ContractService.Instance.GetContractById(model.Payment.PaymentBasic.ContractId);

                model.Contract = contract;
                model.Customer = contract.ContractBasicInfo.CustomerId.HasValue ? CustomerService.Instance.GetCustomerById(contract.ContractBasicInfo.CustomerId.Value) : null;
            }

            return View("Payment/Edit", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentCancel(long paymentId)
        {
            var model = new PaymentModel();

            model.Payment = PaymentService.Instance.GetPayment(paymentId);

            if (model.Payment != null)
            {
                var contract = ContractService.Instance.GetContractById(model.Payment.PaymentBasic.ContractId);

                model.Contract = contract;
                model.Customer = contract.ContractBasicInfo.CustomerId.HasValue ? CustomerService.Instance.GetCustomerById(contract.ContractBasicInfo.CustomerId.Value) : null;
            }

            return View("Payment/Cancel", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentView(long paymentId)
        {
            var model = new PaymentModel();

            model.Payment = PaymentService.Instance.GetPayment(paymentId);

            if (model.Payment != null)
            {
                var contract = ContractService.Instance.GetContractById(model.Payment.PaymentBasic.ContractId);

                model.Contract = contract;
                model.Customer = contract.ContractBasicInfo.CustomerId.HasValue ? CustomerService.Instance.GetCustomerById(contract.ContractBasicInfo.CustomerId.Value) : null;

                if (!string.IsNullOrEmpty(model.Payment.PaymentBasic.PackageNo))
                {
                    var packing = PaymentPackingService.Instance.GetPaymentPackingBasic(model.Payment.PaymentBasic.PackageNo);
                    model.Packing = packing;
                }
            }

            return View("Payment/View", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentAudit(long paymentId)
        {
            var model = new PaymentAuditModel();

            model.Payment = PaymentService.Instance.GetPayment(paymentId);

            var flowAudits = PaymentAuditService.Instance.GetPaymentAuditList(paymentId);

            model.Audit = flowAudits.FirstOrDefault(f => f.AuditRoundId == model.Payment.PaymentBasic.AuditRoundId
                                                    && f.AuditFlowNodeId == model.Payment.PaymentBasic.AuditFlowNodeId
                                                    && f.AuditFlowId == model.Payment.PaymentBasic.AuditFlowId);

            if (model.Payment != null)
            {
                var contract = ContractService.Instance.GetContractById(model.Payment.PaymentBasic.ContractId);

                model.Contract = contract;
                model.Customer = contract.ContractBasicInfo.CustomerId.HasValue ? CustomerService.Instance.GetCustomerById(contract.ContractBasicInfo.CustomerId.Value) : null;
            }

            return View("PaymentAudit/Audit", model);
        }


        #region 审批

        [HttpPost]
        public ActionResult MultiPaymentAudit(string paymentIds)
        {
            var model = new PaymentAuditModel();
            model.Payments = PaymentService.Instance.GetPaymentList(paymentIds.Split(',').Select(long.Parse).ToList());
            model.PaymentIds = paymentIds;
            return PartialView("PaymentAudit/MultiAudit", model);
        }

        #endregion

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentList(string id, string packageNo,int? paymentStatus)
        {
            var menus = MenuService.Instance.GetMenusByCurrentUser();

            if ((id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003001
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003002
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003003 
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003004
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003005
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003006

                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003001
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003002
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003003
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003004
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003005
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003006
                )
                && menus.Any(x => x.MenuCode == id.ToString()))
            {
                var listModel = new ListModel();
                listModel.SearchCondition = new PaymentSearchCondition();

                if (id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003001
                    || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003001)
                {
                    listModel.SearchCondition.Applicant = LoginHelper.GetUserName();
                }

                if (id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003006
                    || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003006)
                {
                    listModel.SearchCondition.PaymentStatus = (int)PaymentStatus.Packing;
                }

                if (id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003003
                    || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003003)
                {
                    listModel.SearchCondition.PaymentStatus = (int)PaymentStatus.Approved;
                }

                if (paymentStatus.HasValue)
                {
                    listModel.SearchCondition.PaymentStatus = paymentStatus;
                }
 

                listModel.SearchCondition.PackageNo = packageNo;
                listModel.SearchCondition.PageId = id;
                listModel.SearchCondition.PageNo = 1;
                listModel.SearchCondition.PageSize = 15;
                return View("Payment/List", listModel);
            }

         
            return new RedirectResult("~/NoPermission.html?" + id.ToString());
        }

        [CheckUserLogin]
        public ActionResult PendingPaymentList(string id, string packageNo)
        {
 
            var listModel = new ListModel();
            listModel.SearchCondition = new PaymentSearchCondition();

            listModel.SearchCondition.PaymentStatus = (int)PaymentStatus.Approved;
            listModel.SearchCondition.PackageNo = packageNo;
            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 15;
            return View("Payment/PendingList", listModel);
 
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
 
        public ActionResult PaymentAuditList(string id)
        {
            var listModel = new ListModel();
            listModel.SearchCondition = new PaymentSearchCondition();
            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 15;
            listModel.SearchCondition.PaymentStatus = (int)PaymentStatus.P;
            return View("PaymentAudit/List", listModel);
          }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentPackingList(string id)
        {
            var menus = MenuService.Instance.GetMenusByCurrentUser();

            if ((id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003004
               || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003006)
              && menus.Any(x => x.MenuCode == id.ToString()))
            {
                var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.AP.Payment.Packing.ListModel();
                listModel.SearchCondition = new PaymentPackingSearchCondition();
                listModel.SearchCondition.PageId = id;
                listModel.SearchCondition.PageNo = 1;
                listModel.SearchCondition.PageSize = 15;
                return View("PaymentPacking/PackingList", listModel);
            }
            return new RedirectResult("~/NoPermission.html?" + id.ToString());
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
 
        public ActionResult PendingPaymentPackingList(string id)
        {
            var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.AP.Payment.Packing.ListModel();
            listModel.SearchCondition = new PaymentPackingSearchCondition();
            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 15;
            return View("PaymentPacking/PendingList", listModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentPackingPrint(long packingId)
        {
            var printModel = new PrintModel();

            printModel.Packing = PaymentPackingService.Instance.GetPaymentPacking(packingId);
            printModel.Company = CompanyService.Instance.GetCompany();

            if (printModel.Packing.PaymentPackingBasic.PaymentType.PaymentTypeId == (int)Dchien.Legal.Entity.FAM.AP.Payment.PaymentTypeId.PatentOffice)
            {
                return View("PaymentPacking/PrintPatent", printModel);
            }
            return View("PaymentPacking/Print", printModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentPackingPrintOnNo(int groupId,string  packingNo)
        {
            var printModel = new PrintModel();
            printModel.GroupId = (GroupId)groupId;
            printModel.PackingNo = packingNo;
            printModel.Packing = PaymentPackingService.Instance.GetPaymentPacking(packingNo);
            printModel.Company = CompanyService.Instance.GetCompany();
            return View("PaymentPacking/PrintOnPackingNo", printModel);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentPackingPrintOnNoList(int groupId, string packingNos)
        {
            var printModel = new PrintListModel();
            printModel.GroupId = (GroupId)groupId;
            printModel.PackingNo = packingNos;
            printModel.PackingList = new List<BizModel.FAM.AP.Payment.Packing.BizPaymentPacking>();
            packingNos.Split(',').Distinct().ToList().ForEach(x =>
            {
                var packing = PaymentPackingService.Instance.GetPaymentPacking(x);
                printModel.PackingList.Add(packing);
            });            

            printModel.Company = CompanyService.Instance.GetCompany();
            return View("PaymentPacking/PrintOnPackingNoList", printModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        public ActionResult PaymentPackingPrintToWord(long packingId)
        {

            //var fileName = PaymentPackingService.Instance.PackingPrintOnExcel(id);
            var fileName = PaymentPackingService.Instance.PackingPrint(packingId);

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

        /// <summary>
        /// 
        /// </summary>
        /// <param name="packingNo"></param>
        /// <returns></returns>
        public ActionResult PaymentPackingPrintToWordOnNo(int groupId, string  packingNo)
        {

            //var fileName = PaymentPackingService.Instance.PackingPrintOnExcel(id);
            var fileName = PaymentPackingService.Instance.PackingPrint((GroupId)groupId,packingNo);

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

        /// <summary>
        /// 
        /// </summary>
        /// <param name="packingNo"></param>
        /// <returns></returns>
        public ActionResult PaymentPackingPrintToWordOnNoList(int groupId,string packingNos)
        {

            //var fileName = PaymentPackingService.Instance.PackingPrintOnExcel(id);
            var fileName = PaymentPackingService.Instance.PackingPrint((GroupId)groupId,packingNos.Split(',').Distinct().ToList());

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


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentPackingVerify(string packingNo)
        {
            var packingListModel = new PackingListModel();
            var packingList = new List<BizModel.FAM.AP.Payment.Packing.BizPaymentPacking>();
            packingNo.Split(',').Distinct().ToList().ForEach(x =>
            {
                var packing = PaymentPackingService.Instance.GetPaymentPacking(x);
                packingList.Add(packing);
            });
            packingListModel.PackingNo = packingNo;
            packingListModel.PaidDate = DateTime.Now; 
            packingListModel.TotalAmount = packingList.Sum(x => x.PaymentPackingBasic.PackingAmount.Value);
            return PartialView("PaymentPacking/PackingVerify", packingListModel);
        }

        #region 批量新建

        [CheckUserLogin]
        public ActionResult MultiCreate(string caseNos)
        {
            return PartialView("Payment/MultiCreate");
        }


        [CheckUserLogin]
        public ActionResult MultiCreatePayment(string caseNos)
        {
            return PartialView("Payment/MultiCreatePayment");
        }

        [CheckUserLogin]
        public ActionResult MultiCreatePaymentList()
        {
            return PartialView("Payment/MultiCreatePaymentList");
        }

        #endregion 
    }
}
