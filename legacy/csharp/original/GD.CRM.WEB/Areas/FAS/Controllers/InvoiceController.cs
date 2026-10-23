using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.BizModel.FAM;
using Dchien.Legal.BizModel.FAM.AR.Invoice;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FAM.Invoice;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.FAM.AR.Invoice;
using Dchien.Legal.Service.FAM.AR.Invoice.Audit;
using Dchien.Legal.Web.Areas.FAM.ViewModels.AR.Invoice;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class InvoiceController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.InvoiceController");

        #region 发票申请

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult List()
        {
            var listModel = new ListModel();
            listModel.CaseFeeSearchCondition = new CaseFeeSearchCondition();
            listModel.CaseFeeSearchCondition.PageNo = 1;
            listModel.CaseFeeSearchCondition.PageSize = 40;
            listModel.CaseFeeSearchCondition.IsInvoiced = false;
            return View(listModel);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult CaseFees(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.CaseFeeSearchCondition.PageNo == 0)
                    model.CaseFeeSearchCondition.PageNo = 1;
                if (model.CaseFeeSearchCondition.PageSize == 0)
                    model.CaseFeeSearchCondition.PageSize = 40;

                var result = new BizCaseFeeSearchResultInfo();

                result.CaseFeeList = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.GetCaseFeeList(model.CaseFeeSearchCondition);

                result.TotalItemCount = model.CaseFeeSearchCondition.TotalCount;
                result.PageNo = model.CaseFeeSearchCondition.PageNo;
                result.PageSize = model.CaseFeeSearchCondition.PageSize;

                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error("InvoiceController.CaseFees", ex);
            }
            return Json(response);
        }

        [CheckUserLogin]
        public ActionResult Create(long customerId, List<long> caseFeeIds)
        {
            var model = new FAM.ViewModels.AR.Invoice.CreateModel();
            model.CaseFeeIds = caseFeeIds;
 
            var customer =  CustomerService.Instance.GetCustomerById(customerId);

            if(customer == null)
            {
                throw new ApplicationException(string.Format("未找到客户{0}", customerId));
            }

            model.Invoice = new BizInvoice();
            model.Invoice.InvoiceBasic = new BizInvoiceBasic();

            //客户信息
            model.Invoice.InvoiceBasic.CustomerId = customer.CustomerId;
            model.Invoice.InvoiceBasic.CustomerNo = customer.CustomerNo;
            model.Invoice.InvoiceBasic.CustomerName = customer.CustomerName;
            model.Invoice.InvoiceBasic.CustomerBusinessAddress = customer.BusinessAddress;
            model.Invoice.InvoiceBasic.CustomerCompanyCode = customer.CompanyCode;
            model.Invoice.InvoiceBasic.CustomerPhone = customer.Telphone;
            model.Invoice.InvoiceBasic.CustomerBankAccount = customer.BankAccount;
            model.Invoice.InvoiceBasic.CustomerBankName = customer.BankName;

            model.Invoice.InvoiceBasic.InvoiceName = customer.CustomerName;

            model.Invoice.InvoiceBasic.InvoiceDate = DateTime.Now;

            var company = CompanyService.Instance.GetCompany();

            model.Invoice.InvoiceBasic.CompanyName = company.CompanyName;
            model.Invoice.InvoiceBasic.CompanyCode = company.CompanyCode;
            model.Invoice.InvoiceBasic.CompanyBankName = company.BankName;
            model.Invoice.InvoiceBasic.CompanyBankAccount = company.BankAccount;

            model.Invoice.CaseFeeList = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.GetCaseFeeListByCaseFeeIds(caseFeeIds);
            
             return PartialView(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="invoice"></param>
        /// <param name="caseFeeIdList"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult InvoiceCreate(BizInvoice invoice)
        {
            var response = new PostResponse();

            try
            {
                if (invoice.CaseFeeList == null || !invoice.CaseFeeList.Any())
                {
                    response.Message = "无应收款信息.";
                    response.IsSuccess = false;
                    return Json(response);
                }
                var caseFeeIds = invoice.CaseFeeList.Select(f=>f.CaseFeeId).ToList();

                var caseFeeList = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.GetCaseFeeListByCaseFeeIds(caseFeeIds);

                invoice.CaseFeeList.ForEach(f =>
                {
                    var caseFee = caseFeeList.FirstOrDefault(x => x.CaseFeeId == f.CaseFeeId);

                    if (caseFee != null)
                    {
                        caseFee.InvoiceAmount = f.InvoiceAmount;
                    }
                });

                invoice.CaseFeeList = caseFeeList;

                bool result = InvoiceService.Instance.CreateInvoice(invoice);

                if (result)
                {
                    response.Message = "申请成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "申请失败！";
                    response.IsSuccess = false;
                }

                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error("InvoiceController.InvoiceCreate", ex);
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
        public JsonResult Invoiced(BizInvoice invoice)
        {
            var response = new PostResponse();

            try
            {
                bool result = InvoiceService.Instance.Invoiced(invoice);

                if (result)
                {
                    response.Message = "保存成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "保存失败！";
                    response.IsSuccess = false;
                }

                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error("InvoiceController.InvoiceEdit", ex);
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult InvoiceList()
        {
            var listModel = new ListModel();
            listModel.SearchCondition = new InvoiceSearchCondition();
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 20;
            listModel.SearchCondition.InvoiceStatus = InvoiceStatus.R;
            return View(listModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult InvoiceList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 20;

                var result = new BizInvoiceSearchResultInfo();

                model.SearchCondition.InvoiceApplicant = LoginHelper.GetUserName();

                result.InvoiceList = InvoiceService.Instance.GetInvoiceList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error("InvoiceController.InvoiceList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }
        
        #endregion

        #region 开票
 
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult InvoiceConfirm(long invoiceId)
        {
            var model = new InvoiceConfirmModel();
            var invoice = InvoiceService.Instance.GetInvoice(invoiceId);

            model.InvoiceId = invoiceId;
            model.InvoiceNo = invoice.InvoiceBasic.InvoiceNo;
            model.InvoiceDate = invoice.InvoiceBasic.InvoiceDate;
            model.InvoiceAmount = invoice.InvoiceBasic.InvoiceAmount;

            return PartialView(model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult InvoiceConfirmCreate(InvoiceConfirmModel model)
        {
            var response = this.CheckInvoiceFileUploading();

            if (response != null)
            {
                return Json(response);
            }

            response = new PostResponse();

            var file = Request.Files[0];
            int fileSize = file.ContentLength;
            var bytes = new byte[fileSize];
            using (var stream = file.InputStream)
            {
                stream.Read(bytes, 0, fileSize);
            }

            var bizInvoice = InvoiceService.Instance.GetInvoice(model.InvoiceId);
            bizInvoice.InvoiceBasic.InvoiceNo = model.InvoiceNo;

            bizInvoice.InvoiceFile = new BizInvoiceFile();
            bizInvoice.InvoiceFile.InvoiceId = bizInvoice.InvoiceBasic.InvoiceId;
            bizInvoice.InvoiceFile.InvoiceNo = model.InvoiceNo;
            bizInvoice.InvoiceFile.CustomerId = bizInvoice.InvoiceBasic.CustomerId;
            bizInvoice.InvoiceFile.CustomerNo = bizInvoice.InvoiceBasic.CustomerNo;
            bizInvoice.InvoiceFile.FileName = file.FileName;
            bizInvoice.InvoiceFile.FileSize = fileSize;
            bizInvoice.InvoiceFile.IsActived = true;
            bizInvoice.InvoiceFile.UploadTime = DateTime.Now;
            bizInvoice.InvoiceFile.UploadUser = LoginHelper.GetUserName();

            bizInvoice.CaseFeeList.ForEach(caseFee =>
            {
                caseFee.Invoice = new BizInvoiceFile();
                caseFee.Invoice.InvoiceNo = model.InvoiceNo;
                caseFee.Invoice.InvoiceDate = model.InvoiceDate;
                caseFee.Invoice.InvoiceAmount = caseFee.Amount;
                caseFee.Invoice.InvoiceFileName = file.FileName;
                caseFee.Invoice.InvoiceFileSize = fileSize;
            });

            bool result = InvoiceService.Instance.Process(bizInvoice, bytes);

            if (result)
            {
                response.Message = "票据确认成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "票据确认失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="invoiceId"></param>
        /// <param name="auditId"></param>
        /// <param name="viewMode"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult View(long invoiceId,long?auditId,ViewMode? viewMode)
        {
            var model = new FAM.ViewModels.AR.Invoice.ViewModel();

            if (viewMode.HasValue)
            {
                model.ViewMode = (ViewMode)viewMode;
            }
            
            model.Invoice = InvoiceService.Instance.GetInvoice(invoiceId);

            model.AuditId = auditId;

            return PartialView(model);
        }

        [HttpPost]
        [CheckUserLogin]
        public ActionResult InvoiceAudit(long invoiceId, long? auditId, ViewMode? viewMode)
        {
            var model = new FAM.ViewModels.AR.Invoice.ViewModel();

            if (viewMode.HasValue)
            {
                model.ViewMode = (ViewMode)viewMode;
            }

            model.Invoice = InvoiceService.Instance.GetInvoice(invoiceId);

            model.AuditId = auditId;

            return PartialView(model);
        }

        #endregion

        #region 检查上传文件

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        private PostResponse CheckInvoiceFileUploading()
        {
            var response = new PostResponse();

            if (Request.Files == null || Request.Files.Count == 0)
            {
                response.Message = "请选择文件进行上传.";
                response.IsSuccess = false;
                return response;
            }

            var file = Request.Files[0];

            if (file == null)
            {
                response.Message = "请选择文件进行上传.";
                response.IsSuccess = false;
                return response;
            }

            if (file.ContentLength == 0)
            {
                response.Message = "文件没有任何内容.";
                response.IsSuccess = false;
                return response;
            }

            if (!CheckFileType(file.FileName))
            {
                response.Message = "上传文件类型不正确,上传失败！";
                response.IsSuccess = false;
                return response;
            }

            return null;

        }
        /// <summary>
        /// 
        /// </summary>
        /// <param name="fileName"></param>
        /// <returns></returns>
        private bool CheckFileType(string fileName)
        {
            //FileName为空时不验证 图片格式 修改图片适用
            if (string.IsNullOrEmpty(fileName))
                return true;

            var start = fileName.LastIndexOf(".");
            string type = fileName.Substring(start, fileName.Length - start);
            //if (type.ToLower() == ".jpg" || type.ToLower() == ".png" || type.ToLower() == ".gif")
            //    return true;

            //return false;

            return true;
        }

        #endregion
    }
}
