using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Lawsuit.Case;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case
{
    public class CaseLogListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseLog> CaseLogs { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long CaseId { get; set; }


	}
}

