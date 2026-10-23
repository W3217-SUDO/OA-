using System;
using System.Collections.Generic;
using System.Linq;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas.Lawsuit.Controllers
{
    [CheckUserLogin] 
    public class ARCaseFeeController : BaseController
    {
        internal Log Logger = new Log("Lawsuit.Controllers.ARCaseFeeController");

        /// <summary>
        ///  案件费用列表
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseFeeList(long caseId, int? pageNo, int? pageSize)
        {
            var caseModel = new Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case.AR.CaseFeeListModel();
            caseModel.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            caseModel.PageSize = pageSize.HasValue ? pageSize.Value : 15;
            if (caseId > 0)
            {
                caseModel.CaseFeeList =
                    Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.GetLsCaseFeeListByCaseId(caseId);
                caseModel.TotalCount = caseModel.CaseFeeList.Count;
                caseModel.CaseFeeList = caseModel.CaseFeeList.Any()
                    ? caseModel.CaseFeeList.Skip(caseModel.PageSize*(caseModel.PageNo - 1))
                        .Take(caseModel.PageSize)
                        .ToList()
                    : new List<Dchien.Legal.BizModel.FAM.AR.CaseFee.BizCaseFee>();
            }
            return PartialView("CaseFeeList", caseModel);
        }

        /// <summary>
        /// 打开案件费用通知
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult Create(Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case.AR.CaseFeeModel model)
        {
            var caseModel = new Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case.AR.CaseFeeModel();

            if (model == null)
            {
                throw new ArgumentNullException("model");
            }

 
            return PartialView("Create", caseModel);
        }

        [HttpPost]
        public ActionResult Edit(string seqno)
        {
            var caseModel = new Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case.AR.CaseFeeModel();

            caseModel.ContractObject = Dchien.Legal.Service.FCM.Contract.ContractService.Instance.GetContractObjectByBatchNo(seqno);

            if (caseModel.ContractObject == null)
            {
                throw new KeyNotFoundException(seqno);
            }
            return PartialView("Edit", caseModel);
        }

        /// <summary>
        /// 保存案件费用通知
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFeeInformCreate(Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case.AR.CaseFeeModel model)
        {
            var response = new PostResponse();

            try
            {
                bool result = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.CreateCaseFee(model.CaseFeeList);

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
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }

            return Json(response);
        }
      
        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFeeId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFeeUnlock(long caseFeeId)
        {
            var response = new PostResponse();

            bool result = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.CaseFeeUnlock(caseFeeId);

            if (result)
            {
                response.Message = "解锁成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "解锁失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }
     
        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFeeId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFeeDelete(long caseFeeId)
        {
            var response = new PostResponse();

            try
            {
                bool result = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.CaseFeeDelete(caseFeeId);

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

            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseController.CaseFeeDelete", "CaseController.CaseFeeDelete", ex);
                throw;
            }

            return Json(response);
        }

    }
}
