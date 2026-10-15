using Dchien.Legal.Common;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;

using Dchien.Legal.Service.Legal.Case;
using Dchien.Legal.Service.FAM.InternalFee;
using Dchien.Legal.Web.Models;
using Dchien.Legal.BizModel.FAM.InternalFee;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Areas.Legal.ViewModels.Case.InternalFee;

namespace Dchien.Legal.Web.Areas.Legal.Controllers
{
    [CheckUserLogin]
    public class InternalFeeController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.InternalFeeController");

        [HttpPost]
        public ActionResult List(long caseId, int? pageNo, int? pageSize)
        {
            var model = new InternalListModel();
            model.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            model.PageSize = pageSize.HasValue ? pageSize.Value : 15;
            if (caseId > 0)
            {
                model.Case = CaseService.Instance.GetCaseBasic(caseId);

                model.InternalFeeList =
                    InternalFeeService.Instance.GetInternalFeeList(caseId);
            
                model.TotalCount = model.InternalFeeList.Count;
                model.InternalFeeList = model.InternalFeeList.Any()
                    ? model.InternalFeeList.Skip(model.PageSize * (model.PageNo - 1))
                        .Take(model.PageSize)
                        .ToList()
                    : new List<BizInternalFee>();
            }
            return PartialView("PartialView/List", model);
        }

        /// <summary>
        /// 新建内部费用
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        public ActionResult Create()
        {
            var model = new InteralFeeModel();
            model.InternalFee = new BizInternalFee();
            model.InternalFee.PaymentDate = DateTime.Now;
            return PartialView("PartialView/Create", model);
        }

        /// <summary>
        /// 新建内部费用
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        public ActionResult MultiCreate()
        {
            var model = new InteralFeeListModel();
            model.InternalFees = new List<BizInternalFee>();
            return PartialView("MultiCreate", model);
        }


        /// <summary>
        /// 新建内部费用
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        public ActionResult Edit(long internalFeeId)
        {
            var model = new InteralFeeModel();
            model.InternalFee = InternalFeeService.Instance.GetInternalFee(internalFeeId);
            return PartialView("PartialView/Edit", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="internalFeeObjects"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult InternalFeeObjectsCreate(List<BizInternalFee> internalFeeObjects)
        {
            var response = new PostResponse();

            try
            {
                bool result = InternalFeeService.Instance.CreateUpdate(internalFeeObjects);

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

        [HttpPost]
        [CheckUserLogin]
        public JsonResult Delete(List<long> internalFeeIds)
        {
            var response = new PostResponse();

            try
            {
                bool result = InternalFeeService.Instance.Delete(internalFeeIds);

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

    }
}
