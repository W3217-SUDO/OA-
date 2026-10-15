using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection.Emit;
using System.Web;
using System.Web.Mvc;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.System;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Areas.System.ViewModels.SystemManagement;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using log4net.Repository.Hierarchy;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service.HR.Staff;

namespace Dchien.Legal.Web.Areas.System.Controllers
{   

    public class SystemManagementController : Controller
    {
        internal Log Logger = new Log("System.Controllers.SystemManagementController");

        #region 菜单管理

        /// <summary>
        /// 
        /// </summary>
        /// <param name="menuId"></param>
        /// <returns></returns>
         [CheckUserLogin]
        public ActionResult Menu(int? menuId)
        {
            var model = new MenuModel();

            if (menuId.HasValue && menuId.Value > -1)
            {
                model.Menu = MenuService.Instance.GetMenu(menuId.Value);
                model.MenuId = menuId.Value;
            }

            return PartialView(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult MenuCreateUpdate(MenuModel model)
        {
            var response = new PostResponse();

            bool result = MenuService.Instance.MenuCreateUpdate(model.Menu);

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

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
         [CheckUserLogin]
        public ActionResult MenuList()
        {
            var model = new MenuListModel();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult MenuList(MenuListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizMenuSearchResultInfo();

                result.MenuList = MenuService.Instance.GetMenuList(model.SearchCondition);

                result.TotalItemCount = result.MenuList.Count;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;

                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message + " || " + ex.StackTrace;
            }
            return Json(response);
        }

        #endregion

        #region 系统缓存

        [CheckUserLogin]
        public ActionResult CacheList()
        {
            var model = new CacheListModel();
            return View(model);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult CacheList(CacheListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizCacheSearchResultInfo();
                var cacheList = CacheService.Instance.GetCacheList();

                result.CacheList =
                    cacheList.Skip(model.SearchCondition.PageSize*(model.SearchCondition.PageNo - 1))
                        .Take(model.SearchCondition.PageSize)
                        .ToList();

                result.TotalItemCount = cacheList.Count;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;

                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "SystemManagementController.CacheList", "SystemManagementController.CacheList", ex);
            }
            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult ClearCache(int cacheId)
        {
            var response = new PostResponse();
            var cache = CacheService.Instance.GetCacheList().FirstOrDefault(x=>x.CacheId == cacheId);
            if (null != cache)
            {
               response.IsSuccess = LocalCacheManager.Instance.ClearData(cache.CacheKey);
            }
            else
            {
                response.IsSuccess = false;
            }

            response.Message = response.IsSuccess ? "清除成功" : "清除失败";

            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult ClearAllCache()
        {
            var response = new PostResponse();
            response.IsSuccess = LocalCacheManager.Instance.ClearAll();
            response.Message = response.IsSuccess ? "清除成功" : "清除失败";

            return Json(response);
        }

        #endregion

        #region 系统配置

        [CheckUserLogin]
        public ActionResult ConfigAppSettingList()
        {
            var model = new ConfigSettingListModel();
            return View(model);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult ConfigAppSettings(ConfigSettingListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.PageNo == 0)
                    model.PageNo = 1;
                if (model.PageSize == 0)
                    model.PageSize = 15;

                var result = new BizConfigAppSettingSearchResultInfo();
                var settingList = ConfigAppSettingService.Instance.GetAllAppSettingsFromDb();

                result.SettingList =
                    settingList.Skip(model.PageSize * (model.PageNo - 1))
                        .Take(model.PageSize)
                        .ToList();

                result.TotalItemCount = settingList.Count;
                result.PageNo = model.PageNo;
                result.PageSize = model.PageSize;

                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "SystemManagementController.ConfigAppSettingList", "SystemManagementController.ConfigAppSettingList", ex);
            }
            return Json(response);
        }

        #endregion
    }


}
