using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using System.Web.UI.WebControls.Expressions;
using Dchien.Legal.BizModel;
using Dchien.Legal.Entity;

namespace Dchien.Legal.Web.Areas.System.ViewModels.SystemManagement
{
    /// <summary>
    /// 
    /// </summary>
    public class CacheListModel
    {

        public SearchCondition SearchCondition { get; set; }

        public CacheListModel()
        {
            this.SearchCondition = new SearchCondition();
        }
    }
}





