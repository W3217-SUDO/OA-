using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;

namespace Dchien.Legal.Web.Areas.IPR.ViewModels.Case
{
    public class IndexModel 
	{
        public List<BizCaseType> CaseTypeList { get; set; }
	}
}





