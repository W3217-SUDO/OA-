using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.BizModel.FAM;
using Dchien.Legal.BizModel.FAM.Invoice;
using Dchien.Legal.BizModel.Lawsuit.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FAM.AR.CaseFee;
using Dchien.Legal.Entity.FAM.AR.CaseFee;
using Dchien.Legal.Entity.Lawsuit.Case;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Service;
using Dchien.Legal.Service.FAM.AR.CaseFee;
using Dchien.Legal.Service.FAM.Invoice;
using Dchien.Legal.Service.Lawsuit.Case;
using Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case;
using Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case.AR;
using Dchien.Legal.Web.Areas.Lawsuit.ViewModels.CaseFee.Invoice;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.Lawsuit.Controllers
{
    [CheckUserLogin]
    public class InvoiceFileController : BaseController
    {
        internal Log Logger = new Log("Lawsuit.Controllers.InvoiceFileController  ");

        public ActionResult CaseFeeList()
        {
            var model = new Dchien.Legal.Web.Areas.Lawsuit.ViewModels.CaseFee.CaseFeeListModel();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 100;
            return View("CaseFeeList", model);
        }


        #region 票据文件

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

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        private PostResponse CheckCaseFeeFileUploading()
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
        /// 打开案件票据确认
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseFeeInvoiceConfirm(CaseFeeInvoiceModel model)
        {
            if (model == null)
            {
                throw new ArgumentNullException("model");
            }

            if (model.CaseFeeIds == null || !model.CaseFeeIds.Any())
            {
                throw new ArgumentNullException("model");
            }

            model.Invoice = new BizInvoiceFile();

            model.Invoice.InvoiceDate = DateTime.Now;


            return PartialView("CaseFeeInvoiceConfirm", model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <param name="caseFeeItemIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFeeInvoiceConfirmCreate(CaseFeeInvoiceModel model, string caseFeeListIds)
        {
            var response = this.CheckCaseFeeFileUploading();

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

            bool result = false;

            if (!string.IsNullOrEmpty(caseFeeListIds))
            {
                var caseFees = CaseFeeService.Instance.GetCaseFeeListByCaseFeeIds(caseFeeListIds.Split(',').Select(long.Parse).ToList());

                var invoiceFiles = new List<BizInvoiceFile>();

                caseFees.ForEach(x =>
                {
                    var invoiceFile = new BizInvoiceFile();
                    invoiceFile.CaseFeeId = x.CaseFeeGuid;
                    invoiceFile.CaseNo = x.CaseNo;
                    invoiceFile.InvoiceNo = model.Invoice.InvoiceNo;
                    invoiceFile.InvoiceDate = model.Invoice.InvoiceDate;
                    invoiceFile.InvoiceAmount = x.Amount;
                    invoiceFile.InvoiceFileName = file.FileName;
                    invoiceFile.InvoiceFileSize = fileSize;

                    invoiceFiles.Add(invoiceFile);

                });

                result = InvoiceFileService.Instance.Create(invoiceFiles, bytes);
            }

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

        #endregion

        #region 收据自定文件导入

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult ReceiptCustomizedFile()
        {
            return View();
        }

        ///// <summary>
        ///// 
        ///// </summary>
        ///// <returns></returns>
        //public JsonResult ReceiptCustomizedFileUpload()
        //{
        //    var response = this.CheckCaseFeeFileUploading();

        //    if (response != null)
        //    {
        //        return Json(response);
        //    }

        //    response = new PostResponse();

        //    var file = Request.Files[0];
        //    int fileSize = file.ContentLength;
        //    var bytes = new byte[fileSize];
        //    using (var stream = file.InputStream)
        //    {
        //        stream.Read(bytes, 0, fileSize);
        //    }

        //    var lstCase = CaseFileService.Instance.ProcessCustomCaseFeeFile(file.FileName, bytes);

        //    response.Data = lstCase;
        //    response.Message = "上传成功！";
        //    response.IsSuccess = true;

        //    return Json(response);

        //}

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        //[HttpPost]
        //public JsonResult ReceiptCustomizedFileImport(CaseFeeReceiptCustomizedFileUploadModel model)
        //{
        //    var response = new PostResponse();
        //    bool result = CaseFileService.Instance.CaseFeeReceiptCustomizedFileProcess(model.CustomFileCaseFees);

        //    if (result)
        //    {
        //        response.Message = "导入成功！";
        //        response.IsSuccess = true;
        //    }
        //    else
        //    {
        //        response.Message = "导入失败！";
        //        response.IsSuccess = false;
        //    }

        //    return Json(response);
        //}

        #endregion

        //#region 发票自定文件导入

        ///// <summary>
        ///// 
        ///// </summary>
        ///// <returns></returns>
        //public ActionResult InvoiceCustomizedFile()
        //{
        //    return View();
        //}

        ///// <summary>
        ///// 
        ///// </summary>
        ///// <returns></returns>
        //public JsonResult InvoiceCustomizedFileUpload()
        //{
        //    var response = this.CheckCaseFeeFileUploading();

        //    if (response != null)
        //    {
        //        return Json(response);
        //    }

        //    response = new PostResponse();

        //    var file = Request.Files[0];
        //    int fileSize = file.ContentLength;
        //    var bytes = new byte[fileSize];
        //    using (var stream = file.InputStream)
        //    {
        //        stream.Read(bytes, 0, fileSize);
        //    }

        //    var lst = CaseFileService.Instance.ProcessCaseFeeInvoiceCustomizedFile(file.FileName, bytes);

        //    if (lst != null && lst.Any())
        //    {
        //        var invoices = new List<BizInvoice>();

        //        lst.ForEach(f =>
        //        {
        //            var invoice = InvoiceService.Instance.GetInvoiceByInvoiceNo(Path.GetFileNameWithoutExtension(f));
        //            invoice.InvoiceBasic.FileName = f;
        //            invoices.Add(invoice);
        //        });

        //        response.Data = new CaseFeeInvoiceCustomizedFileUploadModel { Invoices = invoices, PrimaryFileName = file.FileName};
        //        response.Message = "上传成功！";
        //        response.IsSuccess = true;
        //    }
        //    else
        //    {
        //        response.Message = "上传失败！";
        //        response.IsSuccess = false;
        //    }

        //    return Json(response);

        //}

        ///// <summary>
        ///// 
        ///// </summary>
        ///// <param name="model"></param>
        ///// <returns></returns>
        //[HttpPost]
        //public JsonResult InvoiceCustomizedFileImport(CaseFeeInvoiceCustomizedFileUploadModel model)
        //{
        //    var response = new PostResponse();

        //    bool result = true;

        //    model.Invoices.ForEach(x =>
        //    {
        //        var fileName = x.InvoiceBasic.FileName;
        //        var invoice = InvoiceService.Instance.GetInvoiceBasic(x.InvoiceBasic.InvoiceId.Value);

        //        x.InvoiceBasic = invoice.InvoiceBasic;
        //        x.InvoiceBasic.FileName = fileName;

        //        byte[] bytes = null;

        //        if (Path.GetExtension(model.PrimaryFileName) != null && Path.GetExtension(model.PrimaryFileName).ToLower() == ".zip")
        //        {
        //            bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CustomCaseFiles, Path.GetFileNameWithoutExtension(model.PrimaryFileName), x.InvoiceBasic.FileName));
        //        }
        //        else
        //        {
        //            bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CustomCaseFiles, x.InvoiceBasic.FileName));
        //        }

        //        result = InvoiceService.Instance.Process(x, bytes);
        //    });

        //    if (result)
        //    {
        //        response.Message = "导入成功！";
        //        response.IsSuccess = true;
        //    }
        //    else
        //    {
        //        response.Message = "导入失败！";
        //        response.IsSuccess = false;
        //    }

        //    return Json(response);
        //}

        //#endregion
    }
}
