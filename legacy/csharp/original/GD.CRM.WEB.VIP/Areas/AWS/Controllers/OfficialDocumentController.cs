using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using System.Text;
using System.IO;

using Dchien.Legal.Common;
using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.BizModel.AWS.OfficialDocument;
using Dchien.Legal.Web.Areas.AWS.ViewModels.OfficialDocument;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Service.AWS.OfficialDocument;
using Dchien.Legal.Web.Areas.AWS.ViewModels.OfficialDocumentAudit;
using Dchien.Legal.Service.AWS.OfficialDocument.Audit;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Entity.AWS.OfficialDocument;

namespace Dchien.Legal.Web.Areas.AWS.Controllers
{
    [CheckUserLogin]
    public class OfficialDocumentController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.OfficialDocumentController");
 
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult List(string id)
        {
            var model = new OfficialDocumentListModel();
            model.PageSize = 15;
            model.PageNo = 1;
            model.SearchCondition.PageId = id;

            if (id == PageId.PageId_8101001001  )
            {
                model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.P;
            }
            else if (id == PageId.PageId_8101001002  )
            {
                model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.E;
            }
            else if (id == PageId.PageId_8101001003)
            {
                model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.N;
            }
            else if (id == PageId.PageId_8101001004)
            {
                model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.R;
            }
            else if(id == PageId.PageId_8101002001)
            {
                model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.P;
            }
            else if (id == PageId.PageId_8101002002)
            {
                model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.E;
            }
            else if (id == PageId.PageId_8101002003)
            {
                model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.R;
            }
            else if (id == PageId.PageId_8101003001)
            {
                model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.E;
            }
            else if (id == PageId.PageId_8101003002)
            {
                model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.N;
            }


            return View("List", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="request"></param>
        /// <param name="needToAudit"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        [HttpPost]
        public JsonResult CreateUpdate(OfficialDocumentCreateModel request, bool needToAudit)
        {
            var response = new PostResponse();

            var officialDocument = new BizOfficialDocument();
            officialDocument.Basic = request.OfficialDocument;

            bool result = OfficialDocumentService.Instance.CreateUpdate(officialDocument);

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

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult List(OfficialDocumentListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                if (model.SearchCondition.PageId == PageId.PageId_8101001001)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.P;
                    model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_8101001002)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.E;
                    model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_8101001003)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.N;
                    model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_8101001004)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.R;
                    model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_8101002001)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.P;
                    model.SearchCondition.Auditor = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_8101002002)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.E;
                    //model.SearchCondition.Auditor = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_8101002003)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.R;
                    //model.SearchCondition.Auditor = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_8101003001)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.E;
                }
                else if (model.SearchCondition.PageId == PageId.PageId_8101003002)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.N;
                }

                var result = new BizOfficialDocumentSearchResultInfo();

                result.OfficialDocuments = OfficialDocumentService.Instance.GetOfficialDocumentList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;

                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = "查询出错";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Create(string id)
        {
            var model = new OfficialDocumentModel();
            model.OfficialDocument = new BizOfficialDocument();
            model.OfficialDocument.Basic = new BizOfficialDocumentBasic();
            model.OfficialDocument.Basic.OfficialDocumentGuid = Guid.NewGuid().ToString();
            model.OfficialDocument.Basic.OfficialDocumentBeginDate = DateTime.Now;

            return PartialView("PartialView/Create", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="officialDocumentNo"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Preview(string id, string officialDocumentNo)
        {
            var model = new OfficialDocumentModel();
            model.OfficialDocument = OfficialDocumentService.Instance.GetOfficialDocument(officialDocumentNo);
            return PartialView("PartialView/Preview", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="officialDocumentNo"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        [HttpPost]
        public ActionResult Edit(string id, string officialDocumentNo)
        {
            var model = new OfficialDocumentModel();
            model.OfficialDocument = OfficialDocumentService.Instance.GetOfficialDocument(officialDocumentNo);
            return PartialView("PartialView/Edit", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="officialDocumentNo"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult AuditList(string id, string officialDocumentNo)
        {
            var model = new AuditListModel();
            model.OfficialDocumentAuditList = OfficialDocumentAuditService.Instance.GetOfficialDocumentAuditList(officialDocumentNo);
            return PartialView("PartialView/Audit", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="officialDocumentNo"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult GetOfficialDocument(string officialDocumentNo)
        {
            var response = new PostResponse();

            try
            {
                var officialDocument = OfficialDocumentService.Instance.GetOfficialDocument(officialDocumentNo);
                response.Data = officialDocument;
                response.IsSuccess = true;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "OfficialDocumentController.GetOfficialDocument", "OfficialDocumentController.GetOfficialDocument", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="request"></param>
        /// <param name="needToAudit"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        [HttpPost]
        public JsonResult Print(List<string> officialDocumentNos)
        {
            var response = new PostResponse();

            OfficialDocumentService.Instance.Print(officialDocumentNos);

            response.Message = "用印成功！";
            response.IsSuccess = true;

            return Json(response);
        }

    }
}
