using System;
using System.Collections.Generic;
using System.Web.Mvc;
using Dchien.Legal.BizModel.FAM.Invoice;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FAM.Invoice;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.FAM.Invoice;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Web.Areas.FAM.ViewModels.Invoice;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.ServiceStack.Common.Extensions;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class InvoiceProcessController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.InvoiceProcessController");

        #region 待处理开票

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        [PermissionAttribute(Dchien.Legal.Entity.System.PageId.PageId_5001006002)]
        public ActionResult PendingList(string id)
        {
            var listModel = new ListModel();
            listModel.SearchCondition = new InvoiceSearchCondition();
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 15;
            listModel.SearchCondition.PageId = id;
            return View(listModel);
        }

        #endregion

        #region 已处理开票

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        [PermissionAttribute(Dchien.Legal.Entity.System.PageId.PageId_5001006003)]
        public ActionResult InvoicedList(string id)
        {
            var listModel = new ListModel();
            listModel.SearchCondition = new InvoiceSearchCondition();
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 15;
            listModel.SearchCondition.PageId = id;
            return View(listModel);
        }

        #endregion


        /// <summary>
        /// 
        /// </summary>
        /// <param name="invoiceId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult Process(long invoiceId)
        {
            var model = new InvoiceModel();

            var invoice = InvoiceService.Instance.GetInvoice(invoiceId);

            if (invoice != null)
            {
                model.Invoice = invoice;
                model.Invoice.InvoiceBasic.InvoiceHolder = model.Invoice.InvoiceBasic.InvoiceApplicant;
                model.Invoice.InvoiceBasic.InvoiceHolderName = model.Invoice.InvoiceBasic.InvoiceApplicantName;
                model.Invoice.InvoiceBasic.InvoiceStatus = InvoiceStatus.Invoiced;
                model.Invoice.InvoiceBasic.InvoiceStatusName = InvoiceStatus.Invoiced.ToDescription();
                model.Customer = CustomerService.Instance.GetCustomerById(model.Invoice.InvoiceBasic.CustomerId);
            }

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="invoice"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult Invoiced(BizInvoice invoice)
        {
            var response = new PostResponse();

            try
            {
                var orginvoice = InvoiceService.Instance.GetInvoice(invoice.InvoiceBasic.InvoiceId.Value);

                if (orginvoice == null)
                {
                    response.Message = "提交失败！";
                    response.IsSuccess = true;
                    return Json(response);
                }

                orginvoice.InvoiceBasic.InvoicedOpinion = invoice.InvoiceBasic.InvoicedOpinion;
                orginvoice.InvoiceBasic.InvoiceHolder = invoice.InvoiceBasic.InvoiceHolder;
                orginvoice.InvoiceBasic.Remark = invoice.InvoiceBasic.Remark;
                orginvoice.InvoiceBasic.InvoiceStatus = InvoiceStatus.Invoiced;
                orginvoice.InvoiceBasic.InvoiceNo = invoice.InvoiceBasic.InvoiceNo;
                orginvoice.InvoiceBasic.InvoiceDate = DateTime.Now;

                bool result = InvoiceService.Instance.Invoiced(invoice);

                if (result)
                {
                    response.Message = "提交成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "提交失败！";
                    response.IsSuccess = false;
                }

                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvoiceController.Invoiced", "InvoiceController.Invoiced", ex);
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="invoice"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult Rejected(BizInvoice invoice)
        {
            var response = new PostResponse();

            try
            {
                var orginvoice = InvoiceService.Instance.GetInvoice(invoice.InvoiceBasic.InvoiceId.Value);

                if (orginvoice == null)
                {
                    response.Message = "驳回失败！";
                    response.IsSuccess = true;
                    return Json(response);
                }

                orginvoice.InvoiceBasic.InvoicedOpinion = invoice.InvoiceBasic.InvoicedOpinion;
                orginvoice.InvoiceBasic.InvoiceStatus = InvoiceStatus.ApplicaionCanceled;

                bool result = InvoiceService.Instance.ApplicationCanceled(orginvoice);

                if (result)
                {
                    response.Message = "驳回成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "驳回失败！";
                    response.IsSuccess = false;
                }

                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvoiceController.ApplicationCanceled", "InvoiceController.ApplicationCanceled", ex);
            }
            return Json(response);
        }
    }
}
