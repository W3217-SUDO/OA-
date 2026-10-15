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
    public class UserModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public BizUser User { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int UserId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizRole> Roles { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<int> RoleIds { get; set; }

	}

    /// <summary>
    /// 
    /// </summary>
    public class UserListModel
    {

        public UserSearchCondition SearchCondition { get; set; }

        public UserListModel()
        {
            this.SearchCondition = new UserSearchCondition();
        }
    }
}





