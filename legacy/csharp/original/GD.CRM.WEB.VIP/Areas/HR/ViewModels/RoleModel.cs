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
using Dchien.Legal.Common;
namespace Dchien.Legal.Web.Areas.HR.ViewModels
{
    public class RoleModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public BizRole Role { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int RoleId { get; set; }

        /// <summary>
        /// 权限
        /// </summary>
        public List<int> Permissions { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizMenu> Menus { get; set; }




	}

    /// <summary>
    /// 
    /// </summary>
    public class RoleListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizRole> Roles { get; set; }

        public RoleSearchCondition SearchCondition { get; set; }

        public RoleListModel()
        {
            this.SearchCondition = new RoleSearchCondition();
        }
    }

    public class RolePermissionModel
    {
        public int RoleId { get; set; }
        public List<Node> Nodes { get; set; }

    }
}





