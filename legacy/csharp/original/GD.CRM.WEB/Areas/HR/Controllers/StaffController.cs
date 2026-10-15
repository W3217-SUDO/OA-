using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using System.Text;
using log4net.Repository.Hierarchy;

using Dchien.Legal.BizModel.HR;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.HR;
using Dchien.Legal.Service;
using Dchien.Legal.Service.HR.Staff;
using Dchien.Legal.Service.HR.Staff.File;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Web.Areas.HR.ViewModels.Staff;
using Dchien.Legal.Entity.HR.Staff;
using Dchien.Legal.BizModel.HR.Staff;
using Dchien.Legal.Service.HR.Staff.Event;

namespace Dchien.Legal.Web.Areas.HR.Controllers
{
    [CheckUserLogin]
    public class StaffController : Controller
    {
        internal Log Logger = new Log("HR.Controllers.StaffController");

        [CheckUserLogin]
        public ActionResult List()
        {
            var model = new StaffListModel();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;

            return View("List", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        public JsonResult StaffList(StaffListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizStaffSearchResultInfo();
                result.StaffList = StaffService.Instance.GetStaffList(model.SearchCondition);
                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;

                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }

            return Json(response);
        }

        [CheckUserLogin]
        [PermissionAttribute(Dchien.Legal.Entity.System.PageId.PageId_8001001)]
        public ActionResult CreateUpdate(int? staffId)
        {
            var model = new CreateUpdateModel();

            if (staffId.HasValue && staffId.Value > 0)
            {
                model.Staff = StaffService.Instance.GetStaffById(staffId.Value);
            }
            else
            {
                model.Staff = new BizStaff();
                model.Staff.StaffBasic = new BizStaffBasic();
                model.Staff.StaffBasic.StaffGuid = Guid.NewGuid().ToString();
                model.Staff.StaffBasic.IsActived = true;
                model.Staff.StaffBasic.JobStatus = true;
            }

            return View(model);
        }


        [HttpPost]
        [CheckUserLogin]
        public JsonResult StaffCreateUpdate(CreateUpdateModel model)
        {
            var response = new PostResponse();

            try
            {
                bool result = StaffService.Instance.CreateUpdate(model.Staff);

                if (result)
                {
                    response.Message = "保存成功！";
                    response.Data = model.Staff;
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "保存失败！";
                    response.IsSuccess = false;
                }
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }

            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "StaffController.StaffCreateUpdate", "StaffController.StaffCreateUpdate", ex);
                response.Message = "保存失败";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult ResetPassword(int staffId)
        {
            var response = new PostResponse();

            var result = StaffService.Instance.ResetDefaultPassword(staffId);

            response.IsSuccess = true;
            response.Data = true;

            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult Delete(List<string> staffNames)
        {
            var response = new PostResponse();
            var staffInCases = new List<string>();
            var result = StaffService.Instance.Delete(staffNames, staffInCases);
            if (staffInCases.Any())
            {
                response.IsSuccess = false;
                response.Data = staffInCases;
                response.Message = "案件中存在员工，不允许删除.";
                return Json(response);
            }
            response.IsSuccess = true;
            response.Data = true;
            return Json(response);
        }


        [CheckUserLogin]
        [HttpPost]
        public ActionResult OffWorkDayList(string id, bool? isView, int? staffId, int? pageNo, int? pageSize)
        {
            var model = new OffWorkDayListModel();

            model.IsView = isView;
            model.SearchCondition = new OffWorkDaySearchCondition();
            model.SearchCondition.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            model.SearchCondition.PageSize = pageSize.HasValue ? pageSize.Value : 200;

            if (staffId.HasValue && staffId > 0)
            {
                model.OffWorkDayList = OffWorkDayService.Instance.GetOffWorkDayList(staffId.Value);
                model.SearchCondition.TotalCount = model.OffWorkDayList.Count;
                model.OffWorkDayList = model.OffWorkDayList.Any()
                    ? model.OffWorkDayList.Skip(model.SearchCondition.PageSize * (model.SearchCondition.PageNo - 1))
                        .Take(model.SearchCondition.PageSize)
                        .OrderByDescending(x => x.SeqId)
                        .ToList()
                    : new List<BizOffWorkDay>();
            }

            return PartialView("PartialView/OffWorkDayList", model);
        }

        [CheckUserLogin]
        public ActionResult StaffFileList()
        {
            var model = new StaffFileListModel();

            return PartialView("PartialView/StaffFileList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="staffGuid"></param>
        /// <returns></returns>
        public JsonResult StaffFiles(string staffGuid)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            var staffFiles = new List<BizStaffFile>();

            if (!string.IsNullOrEmpty(staffGuid))
            {
                staffFiles = StaffFileService.Instance.GetStaffFileList(staffGuid);
            }

            response.IsSuccess = true;
            response.Data = staffFiles;

            return Json(response);
        }

        [CheckUserLogin]
        [HttpPost]
        public ActionResult StaffEventList()
        {
            var model = new StaffEventListModel();

            return PartialView("PartialView/StaffEventList", model);
        }

        [CheckUserLogin]
        public ActionResult StaffEvent()
        {
            var model = new StaffEventModel();

            return PartialView("PartialView/StaffEvent", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="staffGuid"></param>
        /// <param name="content"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public JsonResult StaffEventCreate(string staffGuid, string content)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            var staffEvent = new BizStaffEvent();

            staffEvent.StaffGuid = staffGuid;
            staffEvent.Content = content;
            staffEvent.OperateTime = DateTime.Now;

            SatffEventService.Instance.Create(staffEvent);

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="staffGuid"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult StaffEvents(string staffGuid)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            var staffEvents = new List<BizStaffEvent>();

            if (!string.IsNullOrEmpty(staffGuid))
            {
                staffEvents = SatffEventService.Instance.GetStaffEventList(staffGuid);
            }

            response.IsSuccess = true;
            response.Data = staffEvents;

            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult StaffEventDelete(long eventId)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            SatffEventService.Instance.Delete(eventId);

            return Json(response);
        }

        [CheckUserLogin]
        public ActionResult OffWorkDay(int staffId)
        {
            var model = new OffWorkDayModel();
            model.StaffId = staffId;

            return PartialView("PartialView/OffWorkDay", model);
        }

        [CheckUserLogin]
        public JsonResult OffWorkDayCreateUpdate(OffWorkDayModel model)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            model.OffWorkDay.StaffId = model.StaffId;

            OffWorkDayService.Instance.Create(model.OffWorkDay);

            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult StaffFileDelete(long fileId)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            StaffFileService.Instance.Delete(fileId);

            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult OffWorkDayDelete(long seqId)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            OffWorkDayService.Instance.Delete(seqId);

            return Json(response);
        }


        [CheckUserLogin]
        public ActionResult StaffFileUpload(StaffFileUpload model)
        {
            return PartialView("PartialView/StaffFileUpload", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult StaffFileUploading(StaffFileUpload model)
        {
            var response = this.CheckStaffFileUploading();

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

            var staffFile = new BizStaffFile();
            staffFile.StaffGuid = model.StaffGuid;
            staffFile.FileGuid = Guid.NewGuid().ToString();
            staffFile.FileName = file.FileName;

            var result = StaffService.Instance.CreateNewStaffFile(staffFile, bytes);

            if (result)
            {
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
        /// <returns></returns>
        private PostResponse CheckStaffFileUploading()
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

        /// <summary>
        /// 合同文件下载
        /// </summary>
        /// <param name="staffFileId"></param>
        /// <returns></returns>
        public ActionResult StaffFileDownload(long staffFileId)
        {
            try
            {
                var staffFile = StaffFileService.Instance.GetStaffFile(staffFileId);

                if (staffFile != null)
                {
                    StringWriter strWriter = null;
                    HtmlTextWriter htmlWriter = null;

                    // 设置编码和附件格式  
                    Response.Charset = "gb2312";
                    Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                    //Response.ContentType = "application/vnd.ms-word";

                    Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                                 HttpUtility.UrlEncode(staffFile.FileName, Encoding.UTF8)
                                                                     .ToString());

                    // 返回客户端  
                    var bytes =
                        FileHelper.ReadFile(Path.Combine(FileHelper.StaffFiles, staffFile.StaffNo, staffFile.FileName));

                    if (bytes == null)
                    {
                        bytes = new byte[0];
                    }

                    return File(bytes, "attachment;filename=" + staffFile.FileName);
                }

            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "StaffFileController.StaffFileDownload", "StaffFileController.StaffFileDownload", ex);
                throw ex;
            }


            return null;
        }

        /// <summary>
        /// 合同文件下载
        /// </summary>
        /// <param name="staffFileGuid"></param>
        /// <returns></returns>
        public ActionResult StaffFileDownloadByGuid(string staffFileGuid)
        {
            try
            {
                var staffFile = StaffFileService.Instance.GetStaffFile(staffFileGuid);

                if (staffFile != null)
                {
                    StringWriter strWriter = null;
                    HtmlTextWriter htmlWriter = null;

                    // 设置编码和附件格式  
                    Response.Charset = "gb2312";
                    Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                    //Response.ContentType = "application/vnd.ms-word";

                    Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                                 HttpUtility.UrlEncode(staffFile.FileName, Encoding.UTF8)
                                                                     .ToString());

                    // 返回客户端  
                    var bytes =
                        FileHelper.ReadFile(Path.Combine(FileHelper.StaffFiles, staffFile.StaffGuid, staffFile.FileName));

                    if (bytes == null)
                    {
                        bytes = new byte[0];
                    }

                    return File(bytes, "attachment;filename=" + staffFile.FileName);
                }

            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "StaffFileController.StaffFileDownload", "StaffFileController.StaffFileDownload", ex);
            }

            return null;
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="isView"></param>
        /// <param name="staffName"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
        public ActionResult PerformanceList(string id, bool? isView, string staffName, int? pageNo, int? pageSize)
        {
            var model = new PerformanceListModel();
            model.IsView = isView;
            model.SearchCondition = new PerformanceSearchCondition();
            model.SearchCondition.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            model.SearchCondition.PageSize = pageSize.HasValue ? pageSize.Value : 200;
            if (!string.IsNullOrEmpty(staffName))
            {
                model.PerformanceList = StaffPerformanceService.Instance.GetStaffPerformanceList(staffName);
                model.SearchCondition.TotalCount = model.PerformanceList.Count;
                model.PerformanceList = model.PerformanceList.Any()
                    ? model.PerformanceList.Skip(model.SearchCondition.PageSize * (model.SearchCondition.PageNo - 1))
                        .Take(model.SearchCondition.PageSize)
                        .OrderByDescending(x => x.SettingId)
                        .ToList()
                    : new List<BizStaffPerformance>();
            }
            return PartialView("PartialView/PerformanceList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="settingId"></param>
        /// <returns></returns>

        [CheckUserLogin]
        [HttpPost]
        public ActionResult Performance(int? settingId,string staffName)
        {
            var model = new PerformanceModel();
            if (settingId.HasValue)
            {
                model.Performance = StaffPerformanceService.Instance.GetStaffPerformance(settingId.Value);
            }
            else
            {
                model.Performance = new BizStaffPerformance();
                model.Performance.StaffName = staffName;
                model.Performance.AnnualFrom = DateTime.Now;
                model.Performance.AnnualEnd = DateTime.Now.AddYears(1);
                model.Performance.Salary = 0;
                model.Performance.KtRate = (decimal)0.10;
                model.Performance.KtFixed = 0;
                model.Performance.WsRate = (decimal)0.05;
                model.Performance.WsFixed = 0;
                model.Performance.AyRate = (decimal)0.05;
                model.Performance.AyFixed = 0;
                model.Performance.TcRate = (decimal)0.05;
                model.Performance.TcFixed = 0;
                model.Performance.PgRate = (decimal)0.02;
                model.Performance.PgFixed = 0;
            }
            return PartialView("PartialView/Performance", model);
        }

        [CheckUserLogin]
        [HttpPost]
        public ActionResult PerformanceView(string staffName, string caseNo)
        {
            var model = new PerformanceModel();
            model.Performance = StaffPerformanceService.Instance.GetStaffPerformance(staffName, caseNo);
            return PartialView("PartialView/PerformanceView", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
        public JsonResult PerformanceCreateUpdate(PerformanceModel model)
        {
            var response = new PostResponse();
            response.IsSuccess = true;
            StaffPerformanceService.Instance.CreateUpdate(model.Performance);
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
        public JsonResult PerformanceDelete(int settingId)
        {
            var response = new PostResponse();
            response.IsSuccess = true;
            StaffPerformanceService.Instance.Delete(settingId);
            return Json(response);
        }
    }
}
