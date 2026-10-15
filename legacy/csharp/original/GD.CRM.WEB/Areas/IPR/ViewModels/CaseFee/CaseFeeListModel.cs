using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.IPR.ViewModels.CaseFee
{
    /// <summary>
    ///  
    /// </summary>
    public class CaseFeeListModel : BaseListModel
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
        public Dchien.Legal.Entity.FAM.AR.CaseFee.CaseFeeSearchCondition SearchCondition { get; set; }


    }

}

