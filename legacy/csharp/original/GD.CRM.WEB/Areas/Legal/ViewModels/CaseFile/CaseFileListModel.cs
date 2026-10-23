using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Legal.Case;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.Legal.ViewModels.CaseFile
{
    public class CaseFileListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
	    public List<BizCaseFile> CaseFiles { get; set; }

	}
}

