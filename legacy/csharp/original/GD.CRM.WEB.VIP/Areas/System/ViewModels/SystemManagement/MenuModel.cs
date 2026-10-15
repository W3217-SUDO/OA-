using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using System.Web.UI.WebControls.Expressions;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.System;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.System;

namespace Dchien.Legal.Web.Areas.System.ViewModels.SystemManagement
{
    public class MenuModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public BizMenu Menu { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int MenuId { get; set; }

	}

    /// <summary>
    /// 
    /// </summary>
    public class MenuListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizMenu> Menus { get; set; }

        public MenuSearchCondition SearchCondition { get; set; }

        public MenuListModel()
        {
            this.SearchCondition = new MenuSearchCondition();
        }
    }
}





