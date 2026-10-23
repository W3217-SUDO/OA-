 using System;
using System.Collections.Generic;
using System.Web.Mvc;


using Dchien.Legal.Service.Legal.Investigation;
using Dchien.Legal.Common;
using Dchien.Legal.BizModel.Legal.Investigation;
using Dchien.Legal.Web.Areas.CIT.ViewModels.Investigation;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Service.FCM.Contract;

namespace Dchien.Legal.Web.Areas.CIT.Controllers
{
    [CheckUserLogin]
    public class InvestigationController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.InvestigationController");

        public ActionResult List(string id)
        {
            var model = new InvestigationListModel();
            model.SearchCondition.PageId = id;
            if (model.SearchCondition.PageId == PageId.PageId_1401001002)
            {
                //案源人调查列表
                model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
            }
            if (model.SearchCondition.PageId == PageId.PageId_1401001003)
            {
                //案源人调查列表
                model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1401006)
            {
                model.SearchCondition.Auditor = LoginHelper.GetUserName();
               
            }
            return View("List", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        public ActionResult Create(string id, int? contractId)
        {
            var model = new InvestigationModel();
            model.Investigation = new BizInvestigation();
            model.Investigation.Basic = new BizInvestigationBasic();
            model.Investigation.Basic.InvestigationGuid = Guid.NewGuid().ToString();

            if (contractId.HasValue)
            {
                var contract = ContractService.Instance.GetContractById(contractId.Value);
                model.Investigation.Basic.Indicter = contract.ContractBasicInfo.CustomerNo;
                model.Investigation.Basic.IndicterName =  contract.ContractBasicInfo.CustomerName;
                model.Investigation.Basic.ContractNo = contract.ContractBasicInfo.ContractNo;
                model.Investigation.Basic.ContractName = contract.ContractBasicInfo.ContractName;
            }
            else
            {
                throw new ArgumentNullException("contractId");
            }

            return View("Create", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult PreView(string id, string investigationNo)
        {
            var model = new InvestigationModel();
            model.Investigation = InvestigationService.Instance.GetInvestigation(investigationNo);

            return PartialView("PartialView/PreView", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Edit(string id, string investigationNo)
        {
            var model = new InvestigationModel();
            model.Investigation = InvestigationService.Instance.GetInvestigation(investigationNo);
            if (!string.IsNullOrEmpty(model.Investigation.Basic.ContractNo))
            {
                var contract = ContractService.Instance.GetContractByNo(model.Investigation.Basic.ContractNo);
                if (contract != null)
                {
                    model.Investigation.Basic.ContractNo = contract.ContractBasicInfo.ContractNo;
                    model.Investigation.Basic.ContractName = contract.ContractBasicInfo.ContractName;
                }
            }
            return PartialView("PartialView/Edit", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public JsonResult CreateUpdate(InvestigationModel model)
        {
            var response = new PostResponse();

            model.Investigation.Basic.BusinessOwner = LoginHelper.GetUserName();

            InvestigationService.Instance.CreateUpdate(model.Investigation);

            response.Data = model.Investigation.Basic.InvestigationNo;
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
        [CheckUserLogin]
        public JsonResult InvestigationList(InvestigationListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizInvestigationSearchResultInfo();

                if (model.SearchCondition.PageId == PageId.PageId_1401001002)
                {
                    //案源人调查列表
                    model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_1401001003)
                {
                    //案源人调查列表
                    model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_1401006)
                {
                    model.SearchCondition.Auditor = LoginHelper.GetUserName();
                }

                result.Investigations = InvestigationService.Instance.GetInvestigationList(model.SearchCondition);

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
        /// <param name="investigationNos"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        [CheckUserLogin]
        public ActionResult Delete(List<string> investigationNos)
        {
            var response = new PostResponse();
            var result = InvestigationService.Instance.Delete(investigationNos,LoginHelper.GetUserName());
            response.IsSuccess = true;
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="investigationNo"></param>
        /// <returns></returns>
        public ActionResult Assigning(string id, string investigationNo)
        {
            var model = new InvestigationModel();
            model.Investigation = InvestigationService.Instance.GetInvestigation(investigationNo);
            return View("Assigning", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="investigationNo"></param>
        /// <param name="auditor"></param>
        /// <returns></returns>
        public JsonResult ToAudit(string investigationNo, string auditor)
        {
            var response = new PostResponse();

            var investigation = InvestigationService.Instance.GetInvestigation(investigationNo);
            investigation.Basic.Auditor = auditor;
            bool result = InvestigationService.Instance.ToAudit(investigation);

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

    }
}
