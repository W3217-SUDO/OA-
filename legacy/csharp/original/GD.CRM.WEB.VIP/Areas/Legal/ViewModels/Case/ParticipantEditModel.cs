using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel.Legal.Case;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.BizModel.Legal.Investigation.Clue;

namespace Dchien.Legal.Web.Areas.Legal.ViewModels.Case
{
    public class ParticipantEditModel
    {
        /// <summary>
        /// 
        /// </summary>
	    public List<string> CaseNos { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<string> CaseLawyers { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<string> CourtLawyers { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<string> CaseAssistants { get; set; }

        public List<string> BusinessOwners { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int? CaseTypeId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int? CasePhaseId { get; set; }


        /// <summary>
        /// 诉讼标的
        /// </summary>
        public decimal? LitigationAmount { get; set; }

    }

}





