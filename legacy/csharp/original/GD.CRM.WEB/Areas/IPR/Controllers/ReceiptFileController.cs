using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Web.Mvc;

using Dchien.Legal.Service;
using Dchien.Legal.Common;
using Dchien.Legal.BizModel;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Entity.IPR.Receipt;
using Dchien.Legal.Web.Areas.IPR.ViewModels.ReceiptFile;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Service.IPR.Receipt;
using Dchien.Legal.BizModel.IPR.Receipt;

namespace Dchien.Legal.Web.Areas.IPR.Controllers
{
    [CheckUserLogin]
    public class ReceiptFileController : BaseController
    {
        internal Log Logger = new Log("IPR.Controllers.ReceiptFileController");

        #region 专利收据规则文件

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult List()
        {
            var model = new ListModel();

            model.SearchCondition = new ReceiptRuleFileSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 20;

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult ReceiptRuleFileList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                var list = ReceiptRuleFileService.Instance.GetReceiptRuleFileList(model.SearchCondition);

                if (list != null && list.Any())
                {
                    var result = new BizReceiptRuleFileSearchResultInfo();

                    result.TotalItemCount = model.SearchCondition.TotalCount;
                    result.PageNo = model.SearchCondition.PageNo;
                    result.PageSize = model.SearchCondition.PageSize;
                    result.ReceiptRuleFiles = list;
                    response.Data = result;

                    response.IsSuccess = true;
                }
                else
                {
                    response.IsSuccess = false;
                }
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ReceiptFileController.ReceiptRuleFileList", "ReceiptFileController.ReceiptRuleFileList", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult FileUpload()
        {
            var model = new FileUploadModel();
            model.ReceiptDate = DateTime.Now;

            return PartialView(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        public JsonResult ReceiptRuleFileUpload(FileUploadModel model)
        {
            var response = new PostResponse();

            var file = Request.Files[0];

            if (file == null)
            {
                response.Message = "请选择文件进行上传.";
                response.IsSuccess = false;
                return Json(response);
            }

            int fileLen = file.ContentLength;

            Stream stream;
            byte[] bytes = new byte[fileLen];
            stream = file.InputStream;
            stream.Read(bytes, 0, fileLen);

            try
            {
                var guid = Guid.NewGuid();
                var files = ReceiptRuleFileService.Instance.Process(bytes, model.ReceiptDate, file.FileName);
                var result =  ReceiptRuleFileService.Instance.Create(files);

                //var message = "清单共有{0}文件,过滤重复项后正常文件数{1}，已导入{2}文件,未导入{3}文件,遗漏{4}文件.";

                //response.Message = string.Format(message,
                //                            fileList.Count(),
                //                            fileFiterList.Count(),
                //                            fileFiterList.FindAll(x => x.PatentOfficeFileStatus == CasePatentOfficeFileStatus.Imported).Count(),
                //                            fileFiterList.FindAll(x => x.PatentOfficeFileStatus == CasePatentOfficeFileStatus.UnImported).Count(),
                //                            fileFiterList.FindAll(x => x.PatentOfficeFileStatus == CasePatentOfficeFileStatus.NotExists).Count());

                response.Data = guid;
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ReceiptRuleFileUpload", "ReceiptRuleFileUpload", ex);
                response.Message = "上传失败！";
                response.IsSuccess = false;
            }

            return new JsonResult()
            {
                Data = response,
                MaxJsonLength = int.MaxValue,
                ContentType = "application/json"
            };
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult ReceiptRuleFileImport(string metaFileGuid, List<string> selectedIds)
        {
            var response = new PostResponse();

            bool result = true;

            if (selectedIds == null || !selectedIds.Any())
            {
                response.Message = "请选择需要导入专利票据的费用.";
                response.IsSuccess = false;
                return Json(response);
            }

            var model = new ListModel();
            model.SearchCondition = new ReceiptRuleFileSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 20;
            model.SearchCondition.FileName = metaFileGuid;

            //var files = PatentOfficeFeeFileService.Instance.GetCasePatentOfficeFileList(model.SearchCondition);

            //files.ForEach(x =>
            //{
            //    x.Results.ForEach(r =>
            //    {
            //        //result = CaseFileService.Instance.CaseFeeReceiptRuleFileProcess(x, r, r.CaseFeeResults);
            //    });
            //});

            //if (result)
            //{
            //    response.Message = "导入成功！";
            //    response.IsSuccess = true;
            //}
            //else
            //{
            //    response.Message = "导入失败！";
            //    response.IsSuccess = false;
            //}

            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        private PostResponse CheckFileUploading()
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

        public JsonResult ReceiptRuleFileDelete(List<long> selectedIds)
        {
            var response = new PostResponse();

            if (selectedIds == null || !selectedIds.Any())
            {
                response.Message = "请选择文件.";
                response.IsSuccess = false;
                return Json(response);
            }

            bool result = ReceiptRuleFileService.Instance.DeleteRuleFiles(selectedIds);

            if (result)
            {
                response.Message = "删除成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "删除失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

       

    }
}
