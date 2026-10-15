using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;


namespace Dchien.Legal.Web.Areas.IPR.ViewModels.Case
{
    public class CaseEventModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public int? EventId { get; set; }
        
        /// <summary>
        /// 
        /// </summary>
        public long CaseId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int CompanyId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizCaseEvent CaseEvent { get; set; }
	}

    /// <summary>
    /// 
    /// </summary>
    public class CaseEventNotInModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<int> EventTypeIds { get; set; }

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
        public int CompanyId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseEventType> CaseEventTypes { get; set; }
    }
}





