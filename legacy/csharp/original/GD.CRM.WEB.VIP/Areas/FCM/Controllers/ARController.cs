using System;
using System.Web.Mvc;
using System.Linq;

using Dchien.Legal.BizModel.System;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FCM.Contract;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Service;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Web.Areas.FCM.ViewModels.AR;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.FCM.Controllers
{
    [CheckUserLogin]
    public class ARController : Controller
    {
        internal Log Logger = new Log("FCM.Controllers.ARController");
 
        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult List(int id)
        {
            var menus = MenuService.Instance.GetMenusByCurrentUser();

            if ((id.ToString() == PageId.PageId_4001009
               || id.ToString() == PageId.PageId_4001010
               || id.ToString() == PageId.PageId_4001011)

              && menus.Any(x => x.MenuCode == id.ToString()))
            {
                var model = new ListModel();

                model.SearchCondition = new ContractSearchCondition();
                model.SearchCondition.PageNo = 1;
                model.SearchCondition.PageSize = 15;
                model.SearchCondition.PageId = id.ToString();

                return View(model);
            }
            else
            {
                return new RedirectResult("~/NoPermission.html?" + id.ToString());
            }
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult List(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                if (model.SearchCondition.PageId == PageId.PageId_4001009)
                {
                    model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_4001010)
                {
                    model.SearchCondition.DepartmentId = LoginHelper.GetDepartmentId();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_4001011)
                {
                    model.SearchCondition.CompanyId = LoginHelper.GetCompanyId();
                }

                var result = new BizContractSearchResultInfo();

                result.ContractList = ContractService.Instance.GetContractARList(model.SearchCondition);

                //result.ContractList = result.ContractList.FindAll(x => x.ContractBasicInfo.ARAmount > 0);

                result.TotalAmount = model.SearchCondition.TotalAmount;
                result.TotalCashedAmount = model.SearchCondition.TotalCashedAmount;
                result.TotalARAmount = model.SearchCondition.TotalARAmount;
                result.TotalCaseOfficeFeeARAmount = model.SearchCondition.TotalCaseOfficeFeeARAmount;
                result.TotalCaseNonOfficeFeeARAmount = model.SearchCondition.TotalCaseNonOfficeFeeARAmount;

                result.TotalItemCount = model.SearchCondition.TotalCount > model.SearchCondition.PageSize ? model.SearchCondition.TotalCount : result.ContractList.Count;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"ARController.List","ARController.List", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [PermissionAttribute(Dchien.Legal.Entity.System.PageId.PageId_4001012)]
        public ActionResult ItemList()
        {
            var model = new ItemListModel();

            model.SearchCondition = new ContractSearchCondition();
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
        public JsonResult ItemList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 5;

               // model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();

                var result = new BizContractSearchResultInfo();

                result.ContractList = ContractService.Instance.GetContractARItemList(model.SearchCondition);

                result.TotalAmount = model.SearchCondition.TotalAmount;
                result.TotalCashedAmount = model.SearchCondition.TotalCashedAmount;
                result.TotalARAmount = model.SearchCondition.TotalARAmount;
                result.TotalCaseOfficeFeeARAmount = model.SearchCondition.TotalCaseOfficeFeeARAmount;
                result.TotalCaseNonOfficeFeeARAmount = model.SearchCondition.TotalCaseNonOfficeFeeARAmount;

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ARController.List", "ARController.List", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }
  
    }
}
