using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.Web.Models;
using Dchien.Legal.Entity.FAM.AR.Payment;
using Dchien.Legal.Entity.IPR.Case;

namespace Dchien.Legal.Web.Areas.RPT.ViewModels.Report
{
    public class CountFileListModel
    {
        public CountFileListModel()
        {
            this.SearchCondition = new CaseFileCountSearchCondition();
        }

        public CaseFileCountSearchCondition SearchCondition { get; set; }
 
	}
}





