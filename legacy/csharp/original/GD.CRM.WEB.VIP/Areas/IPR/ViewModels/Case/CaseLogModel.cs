using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;


namespace Dchien.Legal.Web.Areas.IPR.ViewModels.Case
{
    public class CaseLogModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public int? LogId { get; set; }
        
        /// <summary>
        /// 
        /// </summary>
        public long CaseId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string CaseNo { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizCaseLog CaseLog { get; set; }
	}
}





