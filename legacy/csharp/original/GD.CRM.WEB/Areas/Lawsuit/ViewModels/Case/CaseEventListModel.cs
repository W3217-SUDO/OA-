using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Lawsuit.Case;

namespace Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case
{
    public class CaseEventListModel
	{

        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseEvent> CaseEvents { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long CaseId { get; set; }


	}
}

