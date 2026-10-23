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
    public class CaseModel 
	{
        /// <summary>
        /// 
        /// </summary>
	    public BizCase Case { get; set; }

        public bool FirstInstace { get; set; }
        public bool SecondInstace { get; set; }

        public bool ExecutionInstace { get; set; }

        public bool LastInstace { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizContract Contract { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizContract> ContractList { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizCustomer Customer { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizInvestigationClue> ClueList { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string InvestigationClueNo { get; set; }


        /// <summary>
        /// 
        /// </summary>
        public string InvestigationClueNos { get; set; }


        public string ErrorMessage { get; set; }
    }

}





