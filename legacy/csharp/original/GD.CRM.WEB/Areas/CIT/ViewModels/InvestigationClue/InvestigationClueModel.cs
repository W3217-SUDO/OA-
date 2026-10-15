using System.Collections;
using System.Collections.Generic;

using Dchien.Legal.BizModel.Legal.Investigation.Clue;
using Dchien.Legal.BizModel.Legal.Investigation;
using Dchien.Legal.BizModel.Legal.Investigation.Task;

namespace Dchien.Legal.Web.Areas.CIT.ViewModels.InvestigationClue
{
    public class InvestigationClueModel 
	{
        /// 
        /// </summary>
        public BizInvestigationClue InvestigationClue { get; set; }


        /// <summary>
        /// 
        /// </summary>
        public BizInvestigationTask InvestigationTask { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizInvestigation Investigation { get; set; }


        /// <summary>
        /// 冲突线索
        /// </summary>
        public List<string> ConflictInvestigationClueNos { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<string> ConflictCaseNos { get; set; }
    }


    public class InvestigationClueCreateModel
    {
        /// <summary>
        /// 
        /// </summary>
        public BizInvestigationClueBasic InvestigationClue { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizInvestigationClueProduct InvestigationClueProduct { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizInvestigationClueIndictee> InvestigationClueIndicteeList { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizInvestigationClueProducer> InvestigationClueProducerList { get; set; }

    }
}
