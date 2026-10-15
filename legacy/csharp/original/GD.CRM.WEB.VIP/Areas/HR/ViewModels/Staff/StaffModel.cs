using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using System.Web.UI.WebControls.Expressions;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.HR.Staff;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.HR.Staff;

namespace Dchien.Legal.Web.Areas.HR.ViewModels.Staff
{
    /// <summary>
    /// 
    /// </summary>
    public class StaffListModel
    {
        public StaffSearchCondition SearchCondition { get; set; }

        public StaffListModel()
        {
            this.SearchCondition = new StaffSearchCondition();
        }
    }
}





