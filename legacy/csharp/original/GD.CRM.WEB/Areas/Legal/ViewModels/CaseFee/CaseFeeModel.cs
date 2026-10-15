using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Legal.Case;

namespace Dchien.Legal.Web.Areas.Legal.ViewModels.CaseFee
{
    public class CaseFeeModel
    {
        /// <summary>
        /// 
        /// </summary>
        public BizModel.FAM.AR.CaseFee.BizCaseFee CaseFee { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string CustomerNo { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string CaseNo { get; set; }



    }

    /// <summary>
    /// 
    /// </summary>
    public class RefundStatusModel
    {
        /// <summary>
        /// 
        /// </summary>
        public int? RefundStatus { get; set; }

    }
}