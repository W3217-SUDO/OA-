using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.BizModel.FAS;
using Dchien.Legal.BizModel.FAS.AR.Invoice;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FAS.AR.CaseFee;
using Dchien.Legal.Entity.FAS.CaseFee;
using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Service;
using Dchien.Legal.Service.FAS.AR.CaseFee;
using Dchien.Legal.Service.FAS.AR.Invoice;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Web.Areas.IPR.ViewModels.Case;
using Dchien.Legal.Web.Areas.IPR.ViewModels.Case.AR;
using Dchien.Legal.Web.Areas.IPR.ViewModels.CaseFee.Invoice;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.IPR.Controllers
{
    [CheckUserLogin]
    public class CaseFeeInvoiceController : BaseController
    {
        internal Log Logger = new Log("IPR.Controllers.CaseFeeInvoiceController ");

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

            model.Invoice = new BizCaseFeeInvoice();

            model.Invoice.InvoiceDate = DateTime.Now;

            if (model.CaseClassType == CaseClassType.Patent && model.InvoiceType == InvoiceType.Invoice)
            {
                //专利发票，对应的是代理费
                model.PaymentMode = (int)CaseFeePaymentMode.Null;
                model.Payer = string.Empty;

            }
            else if (model.CaseClassType == CaseClassType.TradeCopyright && model.InvoiceType == InvoiceType.Invoice)
            {
                
            }
            else if (model.CaseClassType == CaseClassType.Patent && model.InvoiceType == InvoiceType.Voucher)
            {

            }


            return PartialView("CaseFeeInvoiceConfirm", model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <param name="caseFeeItemIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFeeInvoiceConfirmCreate(CaseFeeInvoiceModel model, string caseFeeItemIds)
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

            if (model.CaseClassType == CaseClassType.Patent && model.InvoiceType == InvoiceType.Invoice)
            {
                model.Payer = null;
                model.PaymentMode = null;
            }

            if (!string.IsNullOrEmpty(caseFeeItemIds))
            {
                caseFeeItemIds.Split(',').ToList().ForEach(x =>
                {
                    var caseFee = CaseFeeService.Instance.GetCaseFeeByCaseFeeId(long.Parse(x));

                    caseFee.PaymentMode = model.PaymentMode;
                    caseFee.Payer = model.Payer;

                    caseFee.Invoice = new BizCaseFeeInvoice();
                    caseFee.Invoice.InvoiceNo = model.Invoice.InvoiceNo;
                    caseFee.Invoice.InvoiceDate = model.Invoice.InvoiceDate;
                    caseFee.Invoice.InvoiceAmount = caseFee.Amount;
                    caseFee.Invoice.InvoiceFileName = file.FileName;
                    caseFee.Invoice.InvoiceFileSize = fileSize;

                    var c = CaseService.Instance.GetCaseBasic(caseFee.CaseId);
                    result = CaseService.Instance.Process(c, caseFee, bytes);

                });
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

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public JsonResult ReceiptCustomizedFileUpload()
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

            var lstCase = CaseFileService.Instance.ProcessCustomCaseFeeFile(file.FileName, bytes);

            response.Data = lstCase;
            response.Message = "上传成功！";
            response.IsSuccess = true;

            return Json(response);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult ReceiptCustomizedFileImport(CaseFeeReceiptCustomizedFileUploadModel model)
        {
            var response = new PostResponse();
            bool result = CaseFileService.Instance.CaseFeeReceiptCustomizedFileProcess(model.CustomFileCaseFees);

            if (result)
            {
                response.Message = "导入成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "导入失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

        #region 发票自定文件导入

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult InvoiceCustomizedFile()
        {
            return View();
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public JsonResult InvoiceCustomizedFileUpload()
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

            var lst = CaseFileService.Instance.ProcessCaseFeeInvoiceCustomizedFile(file.FileName, bytes);

            if (lst != null && lst.Any())
            {
                var invoices = new List<BizInvoice>();

                lst.ForEach(f =>
                {
                    var list = InvoiceService.Instance.GetInvoiceByInvoiceNo(Path.GetFileNameWithoutExtension(f));

                    list.ForEach(x =>
                    {
                        x.InvoiceFile = new BizInvoiceFile();
                        x.InvoiceFile.FileName = Path.GetFileName(f);
                        x.InvoiceFile.UploadTime = DateTime.Now;
                        x.InvoiceFile.InvoiceNo = Path.GetFileNameWithoutExtension(f);
                    });

                    invoices.AddRange(list);

                });

                response.Data = new CaseFeeInvoiceCustomizedFileUploadModel { Invoices = invoices, PrimaryFileName = file.FileName};
                response.Message = "上传成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "上传失败！";
                response.IsSuccess = false;
            }

            return Json(response);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult InvoiceCustomizedFileImport(CaseFeeInvoiceCustomizedFileUploadModel model)
        {
            var response = new PostResponse();

            var invoices = new List<BizInvoice>();

            var caseFeeIds = new List<long>();

            model.Invoices.ForEach(x =>
            {
                if (x.CaseFeeList != null && x.CaseFeeList.Any())
                {
                    caseFeeIds.AddRange(x.CaseFeeList.Select(f => f.CaseFeeId));
                }
            });

            bool result = true;

            model.Invoices.ForEach(x =>
            {
                if (!invoices.Any(i => i.InvoiceBasic.InvoiceId == x.InvoiceBasic.InvoiceId))
                {
                    byte[] bytes = null;

                    if (Path.GetExtension(model.PrimaryFileName) != null && Path.GetExtension(model.PrimaryFileName).ToLower() == ".zip")
                    {
                        bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CustomCaseFiles, Path.GetFileNameWithoutExtension(model.PrimaryFileName),x.InvoiceFile.FileName));
                    }
                    else
                    {
                        bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CustomCaseFiles, x.InvoiceFile.FileName));
                    }

                    var bizInvoice = InvoiceService.Instance.GetInvoice(x.InvoiceBasic.InvoiceId);
                    bizInvoice.InvoiceFile = new BizInvoiceFile();
                    bizInvoice.InvoiceFile.InvoiceId = bizInvoice.InvoiceBasic.InvoiceId;
                    bizInvoice.InvoiceFile.InvoiceNo = bizInvoice.InvoiceBasic.InvoiceNo;
                    bizInvoice.InvoiceFile.CustomerId = bizInvoice.InvoiceBasic.CustomerId;
                    bizInvoice.InvoiceFile.CustomerNo = bizInvoice.InvoiceBasic.CustomerNo;
                    bizInvoice.InvoiceFile.FileName = x.InvoiceFile.FileName;
                    bizInvoice.InvoiceFile.FileSize = bytes.Length;
                    bizInvoice.InvoiceFile.IsActived = true;
                    bizInvoice.InvoiceFile.UploadTime = DateTime.Now;
                    bizInvoice.InvoiceFile.UploadUser = LoginHelper.GetUserName();

                    var caseFeeList = new List<Dchien.Legal.BizModel.FAS.AR.CaseFee.BizCaseFee>();
                    
                    bizInvoice.CaseFeeList.ForEach(caseFee =>
                    {
                        if (caseFeeIds.Any(f=>f == caseFee.CaseFeeId))
                        {
                            caseFee.Invoice = new BizCaseFeeInvoice();
                            caseFee.Invoice.InvoiceNo = bizInvoice.InvoiceFile.InvoiceNo;
                            caseFee.Invoice.InvoiceDate = DateTime.Now;
                            caseFee.Invoice.InvoiceAmount = caseFee.Amount;
                            caseFee.Invoice.InvoiceFileName = bizInvoice.InvoiceFile.FileName;
                            caseFee.Invoice.InvoiceFileSize = bizInvoice.InvoiceFile.FileSize;
                            caseFeeList.Add(caseFee);
                        }
                    });

                    bizInvoice.CaseFeeList = caseFeeList;

                    invoices.Add(bizInvoice);

                    result = InvoiceService.Instance.Process(bizInvoice, bytes);
                }
            });

            if (result)
            {
                response.Message = "导入成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "导入失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion
    }
}
