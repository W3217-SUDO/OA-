using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.BizModel.FAM.Invoice;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FAM.AR.CaseFee;
using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.Service.FAM.AR.CaseFee;
using Dchien.Legal.Service.FAM.Invoice;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Web.Areas.IPR.ViewModels.Case;
using Dchien.Legal.Web.Areas.IPR.ViewModels.CaseFee.Invoice;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.BizModel.FIO.PatentOffice;

using Dchien.Legal.Service.FIO.PatentOffice;


namespace Dchien.Legal.Web.Areas.IPR.Controllers
{
    [CheckUserLogin]
    public class InvoiceFileController : BaseController
    {
        internal Log Logger = new Log("IPR.Controllers.InvoiceFileController  ");

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

            if (model.CaseClassType == CaseClassType.Patent && model.InvoiceType == Dchien.Legal.Entity.FAM.Invoice.InvoiceType.Invoice)
            {
                //专利发票，对应的是代理费
                model.PaymentMode = (int)CaseFeePaymentMode.Null;
                model.Payer = string.Empty;

            }
            else if (model.CaseClassType == CaseClassType.TradeCopyright && model.InvoiceType == Dchien.Legal.Entity.FAM.Invoice.InvoiceType.Invoice)
            {
                
            }
            else if (model.CaseClassType == CaseClassType.Patent && model.InvoiceType == Dchien.Legal.Entity.FAM.Invoice.InvoiceType.Voucher)
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

            //if (model.CaseClassType == CaseClassType.Patent && model.InvoiceType == Dchien.Legal.Entity.FAM.Invoice.InvoiceType.Invoice)
            //{
                //model.Payer = null;
                //model.PaymentMode = null;
            //}

            if (!string.IsNullOrEmpty(caseFeeItemIds))
            {
                caseFeeItemIds.Split(',').ToList().ForEach(x =>
                {
                    var caseFee = CaseFeeService.Instance.GetCaseFeeByCaseFeeId(long.Parse(x));

                    //caseFee.PaymentMode = model.PaymentMode;
                    //caseFee.Payer = model.Payer;

                    caseFee.InvoiceFile = new BizInvoiceFile();
                    caseFee.InvoiceFile.InvoiceNo = model.Invoice.InvoiceNo;
                    caseFee.InvoiceFile.InvoiceDate = model.Invoice.InvoiceDate;
                    caseFee.InvoiceFile.InvoiceAmount = caseFee.Amount;
                    caseFee.InvoiceFile.InvoiceFileName = file.FileName;
                    caseFee.InvoiceFile.InvoiceFileSize = fileSize;
                    caseFee.InvoiceFile.InvoiceTypeId = (int)model.InvoiceType;
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
        public ActionResult ReceiptCustomizedFile(string id)
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
        public ActionResult InvoiceCustomizedFile(string id)
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
            decimal? totalAmount = 0;

            if (lst != null && lst.Any())
            {
                var list = new List<BizInvoice>();

                lst.ForEach(f =>
                {
                    var invoices = InvoiceService.Instance.GetInvoiceByInvoiceNo(Path.GetFileNameWithoutExtension(f));

                    if (invoices != null && invoices.Any())
                    {
                        invoices.ForEach(x =>
                        {
                            if (x.CaseFees != null && x.CaseFees.Any())
                            {
                                x.InvoiceBasic.FileName = f;
                                list.Add(x);
                                totalAmount += x.CaseFees.Sum(cf => cf.Amount);
                            }
                        });
                    }
                });

               

                response.Data = new CaseFeeInvoiceCustomizedFileUploadModel { Invoices = list, PrimaryFileName = file.FileName,  TotalAmount = totalAmount };
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

            bool result = true;

            model.Invoices.ForEach(x =>
            {
                var fileName = x.InvoiceBasic.FileName;
                var invoice = InvoiceService.Instance.GetInvoiceBasic(x.InvoiceBasic.InvoiceId.Value);

                x.InvoiceBasic = invoice.InvoiceBasic;
                x.InvoiceBasic.FileName = fileName;

                byte[] bytes = null;

                if (Path.GetExtension(model.PrimaryFileName) != null && Path.GetExtension(model.PrimaryFileName).ToLower() == ".zip")
                {
                    bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CustomCaseFiles, Path.GetFileNameWithoutExtension(model.PrimaryFileName), x.InvoiceBasic.FileName));
                }
                else
                {
                    bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CustomCaseFiles, x.InvoiceBasic.FileName));
                }

                result = InvoiceService.Instance.Process(x, bytes);
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

        #region 发票自定文件导入(合同)

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult ContractInvoiceCustomizedFile()
        {
            return View();
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public JsonResult ContractInvoiceCustomizedFileUpload()
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
                var list = new List<BizInvoice>();

                lst.ForEach(f =>
                {
                    var invoices = InvoiceService.Instance.GetInvoiceByInvoiceNo(Path.GetFileNameWithoutExtension(f));

                    if (invoices != null && invoices.Any())
                    {
                        invoices.ForEach(x =>
                        {
                            x.InvoiceBasic.FileName = f;
                            list.Add(x);
                        });
                    }
                });

                response.Data = new CaseFeeInvoiceCustomizedFileUploadModel { Invoices = list, PrimaryFileName = file.FileName };
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
        public JsonResult ContractInvoiceCustomizedFileImport(CaseFeeInvoiceCustomizedFileUploadModel model)
        {
            var response = new PostResponse();

            bool result = true;

            model.Invoices.ForEach(x =>
            {
                var fileName = x.InvoiceBasic.FileName;
                var invoice = InvoiceService.Instance.GetInvoiceBasic(x.InvoiceBasic.InvoiceId.Value);
 
                x.InvoiceBasic = invoice.InvoiceBasic;
                x.InvoiceBasic.FileName = fileName;
                x.CaseFees = InvoiceService.Instance.GetInvoiceCaseFeeList(x.InvoiceBasic.InvoiceId.Value);

                byte[] bytes = null;

                if (Path.GetExtension(model.PrimaryFileName) != null && Path.GetExtension(model.PrimaryFileName).ToLower() == ".zip")
                {
                    bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CustomCaseFiles, Path.GetFileNameWithoutExtension(model.PrimaryFileName), x.InvoiceBasic.FileName));
                }
                else
                {
                    bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CustomCaseFiles, x.InvoiceBasic.FileName));
                }

                result = InvoiceService.Instance.ProcessOnContract(x, bytes);
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

        #region 专利收据文件AI处理


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult ReceiptOcrFile()
        {
            var model = new CasePatentOfficeFeeFileListModel();

            model.SearchCondition = new CasePatentOfficeFeeFileSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        public JsonResult ReceiptOcrFileUpload()
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

            var metaFileGuid = Guid.NewGuid();
            var metaFileName = file.FileName;
            var fileName = metaFileGuid + Path.GetExtension(file.FileName);

            var lst = CaseFileService.Instance.ProcessCaseFeeReceiptOcrFile(fileName, bytes);

            if (lst.Count > 20)
            {
                response.Message = "不能超过20张票据文件.";
                response.IsSuccess = false;
                return Json(response);
            }

            if (lst != null && lst.Any())
            {
                var files = PatentOfficeFeeFileService.Instance.Parse(metaFileGuid.ToString(), metaFileName, lst);
                PatentOfficeFeeFileService.Instance.Create(files);

                response.IsSuccess = true;
                response.Message = "上传成功.";
                response.Data = metaFileGuid;
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
        public JsonResult GetCaseOfficeFeeMetaFileList(CasePatentOfficeFeeFileListModel model)
        {
           var  response = new PostResponse();
 
            var files = PatentOfficeFeeFileService.Instance.GetCasePatentOfficeFileList(model.SearchCondition);

            var result = new BizPatentOfficeFeeMetaFileResultInfo();

            result.TotalItemCount = model.SearchCondition.TotalCount;
            result.PageNo = model.SearchCondition.PageNo;
            result.PageSize = model.SearchCondition.PageSize;
            result.CaseFiles = files;
 
            response.Data = result;
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
        public JsonResult ReceiptOcrFileImport(string metaFileGuid, List<string> selectedIds)
        {
            var response = new PostResponse();

            bool result = true;

            if (selectedIds == null || !selectedIds.Any())
            {
                response.Message = "请选择需要导入专利票据的费用.";
                response.IsSuccess = false;
                return Json(response);
            }

            var model = new CasePatentOfficeFeeFileListModel();
            model.SearchCondition = new CasePatentOfficeFeeFileSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            model.SearchCondition.MetaFileGuid = metaFileGuid;

            var files = PatentOfficeFeeFileService.Instance.GetCasePatentOfficeFileList(model.SearchCondition);

            files.ForEach(x =>
            {
                x.Results.ForEach(r =>
                {
                    result = CaseFileService.Instance.CaseFeeReceiptOcrFileProcess(x,r,r.CaseFeeResults);
                });
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
