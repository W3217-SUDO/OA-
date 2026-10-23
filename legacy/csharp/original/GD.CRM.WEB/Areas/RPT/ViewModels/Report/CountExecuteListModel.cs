using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.Entity.Legal.Case;

namespace Dchien.Legal.Web.Areas.RPT.ViewModels.Report
{
    public class CountExecuteListModel
    {
        public CountExecuteListModel()
        {
            this.SearchCondition = new CaseSearchCondition();
        }

        public CaseSearchCondition SearchCondition { get; set; }
 
	}
}





