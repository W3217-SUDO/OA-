using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;

namespace Dchien.Legal.Web.Areas.IPR.ViewModels.CaseEvent
{
    public class CaseEventModel 
	{
        
        /// <summary>
        /// 
        /// </summary>
        public List<long> CaseIds { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public DateTime? Deadline { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public DateTime? EventTime { get; set; }

        /// <summary>
        /// 
        /// </summary>

        public string EventContent { get; set; }
        
    }
}





