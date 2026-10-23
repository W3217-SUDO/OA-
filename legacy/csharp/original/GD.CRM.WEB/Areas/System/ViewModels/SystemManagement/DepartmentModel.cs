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
    public class DepartmentModel 
	{
        public BizDepartment Department { get; set; }
	}

    /// <summary>
    /// 
    /// </summary>
    public class DepartmentListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizDepartment> Departments { get; set; }

        public DepartmentSearchCondition SearchCondition { get; set; }

        public DepartmentListModel()
        {
            this.SearchCondition = new DepartmentSearchCondition();
        }
    }
}





