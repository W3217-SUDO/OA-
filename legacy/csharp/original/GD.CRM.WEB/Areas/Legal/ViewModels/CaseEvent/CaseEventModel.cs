using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Legal.Case;


namespace Dchien.Legal.Web.Areas.Legal.ViewModels.CaseEvent
{
    public class CaseEventModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public BizCaseEvent CaseEvent { get; set; }

        /// <summary>
        /// 
        /// </summary>

        public long? EventId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string CaseNo { get; set;
        }
	}

}





