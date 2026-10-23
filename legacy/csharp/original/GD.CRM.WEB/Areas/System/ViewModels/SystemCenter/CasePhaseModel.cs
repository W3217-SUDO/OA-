using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using System.Web.UI.WebControls.Expressions;
using Dchien.Legal.BizModel;
using Dchien.Legal.Entity;
using Dchien.Legal.BizModel.BAS.Type;
using Dchien.Legal.Entity.BAS.Type;

namespace Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter.CasePhase
{
    public class CasePhaseModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public BizCasePhase CasePhase { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int CasePhaseId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public bool IsNew { get; set; }

    }

    /// <summary>
    /// 
    /// </summary>
    public class CasePhaseListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizCasePhase> CasePhases { get; set; }

        public CasePhaseSearchCondition SearchCondition { get; set; }

        public CasePhaseListModel()
        {
            this.SearchCondition = new CasePhaseSearchCondition();
        }
    }
}





