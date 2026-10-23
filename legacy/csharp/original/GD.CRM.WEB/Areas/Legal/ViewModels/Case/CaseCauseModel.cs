using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.Entity;
using Dchien.Legal.BizModel.Lawsuit.Cause;

namespace Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case
{
    public class CaseCauseModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public long? CaseId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizCause CaseCause { get; set; }
	}
}





