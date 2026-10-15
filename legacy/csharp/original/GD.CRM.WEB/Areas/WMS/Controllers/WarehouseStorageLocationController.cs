using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;

using Dchien.Legal.Common;
using Dchien.Legal.Service;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service.Legal.Case;
using Dchien.Legal.Service.WMS.Warehouse;
using Dchien.Legal.Web.Areas.WMS.ViewModels.Warehouse;
using Dchien.ServiceStack.Text;

namespace Dchien.Legal.Web.Areas.WMS.Controllers
{
    [CheckUserLogin]
    public class WarehouseStorageLocationController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.WarehouseStorageLocationController");
        /// <summary>
        /// 
        /// </summary>
        /// <param name="search"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult GetStorageLocationGoodsCountList(WarehouseListModel model)
        {
            var response = new PostResponse();

            if (model.SearchCondition.PageNo == 0)
                model.SearchCondition.PageNo = 1;
            if (model.SearchCondition.PageSize == 0)
                model.SearchCondition.PageSize = 15;

            try
            {
                var goodsCounts = WarehouseService.Instance.GetGoodsCountGroupbyStorageLocation(model.SearchCondition);
                response.Data = new { WarehouseLocationGoods = goodsCounts };
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "WarehouseController.GetStorageLocationGoodsCountList", model.SearchCondition.ToJson(), ex);
                response.Message = "未知错误.";
                response.IsSuccess = false;
            }

            return Json(response);
        }
    }
}
