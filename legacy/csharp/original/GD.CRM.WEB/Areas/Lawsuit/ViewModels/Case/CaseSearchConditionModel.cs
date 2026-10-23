using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.IPR.Case;

namespace Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case
{
    public class CaseSearchConditionModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public CaseSearchCondition SearchCondition { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int? CaseSearchConditionId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizCaseSearchCondition Search { get; set; }


        /// <summary>
        /// 
        /// </summary>
        public List<BizCasePhase> CasePhases { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseFeeType> CaseFeeTypes { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseType> CaseTypes { get; set; }

        public List<BizCaseFileType> CaseFileTypes { get; set; }

 

	}
}

