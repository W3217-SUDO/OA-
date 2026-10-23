using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;

namespace Dchien.Legal.Web.Areas.IPR.ViewModels.CaseLog
{
    public class CaseLogModel 
	{
        
        /// <summary>
        /// 
        /// </summary>
        public List<long> CaseIds { get; set; }

 

        /// <summary>
        /// 
        /// </summary>
        public DateTime? LogTime { get; set; }

        /// <summary>
        /// 
        /// </summary>

        public string LogContent { get; set; }
        
    }



}





