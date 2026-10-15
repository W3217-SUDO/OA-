using System;
using System.Collections.Generic;
using System.Web.Mvc;

using Dchien.Legal.Web.Models;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Service.BAS.Court;
using Dchien.Legal.Web.Areas.BAS.ViewModels.CourtOfficer;
using System.Linq;
using Dchien.Legal.Service.BAS.Warehouse;
 
using Dchien.Legal.Service;

namespace Dchien.Legal.Web.Areas.BAS.Controllers
{
    public class WarehouseController : Controller
    {
        [HttpPost]
        public JsonResult GetWarehouses()
        {
            var response = new PostResponse();
 
            try
            {
                var warehouses = WarehouseService.Instance.GetWarehouseList();
                response.Data = new { Warehouses = warehouses };
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                //Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "WarehouseController.GetStorageLocationGoodsCountList", "WarehouseService.Instance.GetWarehouseList()", ex);
                response.Message = "未知错误.";
                response.IsSuccess = false;
            }

            return Json(response);
        }

    }
}
