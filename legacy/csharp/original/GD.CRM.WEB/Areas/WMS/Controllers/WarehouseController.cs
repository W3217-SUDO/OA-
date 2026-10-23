using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;

using Dchien.ServiceStack.Text;
using Dchien.ServiceStack.Common.Extensions;

using Dchien.Legal.Web.Models;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Areas.WMS.ViewModels.Warehouse;
using Dchien.Legal.Service;
using Dchien.Legal.BizModel.WMS.Warehouse;
using Dchien.Legal.Service.WMS.Warehouse;

namespace Dchien.Legal.Web.Areas.WMS.Controllers
{
    [CheckUserLogin]
    public class WarehouseController : Controller
    {
        internal Log Logger = new Log("WMS.Controllers.WarehouseController");

        [CheckUserLogin]
        public ActionResult List(int? id)
        {
            var model = new WarehouseListModel();
            return View("GoodsList",model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult GoodsList(WarehouseListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizWarehouseObjectSearchResultInfo();

                result.GoodsList = WarehouseService.Instance.GetWarehouseObjectList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
 
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "WarehouseController.GoodsList", model.SearchCondition.ToJson(), ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }



    }
}
