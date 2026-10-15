using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel.System;
using Dchien.Legal.Service;

namespace Dchien.Legal.Web
{
    public class PermissionAttribute : ActionFilterAttribute
    {
        public string ModuleCode { get; set; }
        public PermissionAttribute(string moduleCode)
        {
            ModuleCode = moduleCode;
        }

        private List<BizMenu> menus { get; set; }
        /// <summary>
        /// 
        /// </summary>
        /// <param name="filterContext"></param>
        public override void OnActionExecuting(ActionExecutingContext filterContext)
        {
            if (menus == null || menus.Count == 0)
            {
                menus = MenuService.Instance.GetMenusByCurrentUser();
            }

            if (!menus.Any(x=>x.MenuCode == this.ModuleCode))
            {
                filterContext.Result = new RedirectResult("~/NoPermission.html?"+this.ModuleCode);
                // TODO
                //throw new Exception("没有权限");
            }
            base.OnActionExecuting(filterContext);
        }
    }
}