using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection.Emit;
using System.Web;
using System.Web.Mvc;

using log4net.Repository.Hierarchy;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.System;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Areas.HR.ViewModels;
using Dchien.Legal.Service;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.HR.Controllers
{
    public class DepartmentController : Controller
    {
        internal Log Logger = new Log("HR.Controllers.DepartmentController");

        #region   部门管理
         [CheckUserLogin]
        public ActionResult Department(int? departmentId)
        {
            var model = new DepartmentModel();

            if (departmentId.HasValue && departmentId.Value > -1)
            {
                model.Department = DepartmentService.Instance.GetDepartment(departmentId.Value);
                model.Department.DepartmentId = departmentId.Value;
            }

            return PartialView(model);
        }

         [CheckUserLogin]
        public ActionResult DepartmentList()
        {
            var model = new DepartmentListModel();

            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;

            return View(model);
        }

         [HttpPost]
         [CheckUserLogin]
         public JsonResult DepartmentList(DepartmentListModel model)
         {
             var response = new PostResponse();

             if (model.SearchCondition.PageNo == 0)
                 model.SearchCondition.PageNo = 1;
             if (model.SearchCondition.PageSize == 0)
                 model.SearchCondition.PageSize = 15;

             var result = new BizDepartmentSearchResultInfo();

             result.DepartmentList = DepartmentService.Instance.GetDepartmentList(model.SearchCondition);

             result.TotalItemCount = result.DepartmentList.Count;
             result.PageNo = model.SearchCondition.PageNo;
             result.PageSize = model.SearchCondition.PageSize;

             response.IsSuccess = true;
             response.Data = result;

             return Json(response);
         }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult DepartmentCreateUpdate(DepartmentModel model)
        {
            var response = new PostResponse();

            bool result = DepartmentService.Instance.DepartmentCreateUpdate(model.Department);

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

            return Json(response);
        }

        #endregion

   
  
    }
 
}
