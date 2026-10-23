using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Legal.Case;
using Dchien.Legal.Entity.Legal.Case;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AR.CaseFee
{
    /// <summary>
    ///  
    /// </summary>
    public class PendingSettlementCaseFeeListModel : BaseListModel
    {

        /// <summary>
        ///  
        /// </summary>

        public List<Dchien.Legal.BizModel.FAM.AR.CaseFee.BizCaseFee> CaseFeeList { get; set; }


        /// <summary>
        /// 
        /// </summary>
        public long CaseId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public CaseSearchCondition SearchCondition { get; set; }


    }

}

