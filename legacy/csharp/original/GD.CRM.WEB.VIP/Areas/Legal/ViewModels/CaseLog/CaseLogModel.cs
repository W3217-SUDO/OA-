using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Legal.Case;


namespace Dchien.Legal.Web.Areas.Legal.ViewModels.Case
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


        public string CaseNos { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizCaseLog CaseLog { get; set; }
	}
}





