using System;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.BizModel.FAM;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FAM.AR.CaseFee;
using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.Service.FAM.AR.CaseFee;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Web.Areas.IPR.ViewModels.Case.AR;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;

namespace Dchien.Legal.Web.Areas.IPR.Controllers
{
    [CheckUserLogin]
    public class CaseFeeController : BaseController
    {
        internal Log Logger = new Log("IPR.Controllers.CaseFeeController");

        [CheckUserLogin]
        public ActionResult CaseFeeList(string id,int caseTypeId,int invoiceTypeId )
        {
            var model = new CaseFeeSearchListModel();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            model.SearchCondition.CaseClassType = (CaseClassType) caseTypeId;
            model.SearchCondition.InvoiceType = (Dchien.Legal.Entity.FAM.Invoice.InvoiceType)invoiceTypeId;

            return View(model);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult CaseFees(CaseFeeSearchListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizCaseFeeSearchResultInfo();

                result.CaseFeeList = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.GetCaseFeeList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;

                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFeeController.CaseFees", "CaseFeeController.CaseFees", ex);
            }
            return Json(response);
        }
       
        [HttpPost]
        public ActionResult CaseFeeFileBatchImport()
        {
            //model.UploadingTime = DateTime.Now;

            //return PartialView("CaseFileBatchImport", model);
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
        public ActionResult CaseFeeListInvoiceConfirm(CaseFeeListInvoiceConfirmModel model)
        {
            if (model == null)
            {
                throw new ArgumentNullException("model");
            }

            if (model.CaseFeeIds == null || !model.CaseFeeIds.Any())
            {
                throw new ArgumentNullException("model");
            }

            model.InvoiceDate = DateTime.Now;

            return PartialView("CaseFeeListInvoiceConfirm", model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <param name="caseFeeItemIdList"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFeeListInvoiceConfirmCreate(CaseFeeListInvoiceConfirmModel model, string caseFeeItemIdList)
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

            if (!string.IsNullOrEmpty(caseFeeItemIdList))
            {
                caseFeeItemIdList.Split(',').ToList().ForEach(x =>
                {
                    var caseFee = CaseFeeService.Instance.GetCaseFeeByCaseFeeId(long.Parse(x));

                    caseFee.InvoiceFile = new Dchien.Legal.BizModel.FAM.Invoice.BizInvoiceFile();
                    caseFee.InvoiceFile.InvoiceNo = model.InvoiceNo;
                    caseFee.InvoiceFile.InvoiceDate = model.InvoiceDate;
                    caseFee.InvoiceFile.InvoiceAmount = caseFee.Amount;
                    caseFee.InvoiceFile.InvoiceFileName = file.FileName;
                    caseFee.InvoiceFile.InvoiceFileSize = fileSize;

                    var c = CaseService.Instance.GetCaseBasic(caseFee.CaseId);
                    result = CaseService.Instance.Process(c, caseFee, bytes);

                });
            }

            if (result)
            {
                response.Message = "批量确认成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "批量确认失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

    }
}
