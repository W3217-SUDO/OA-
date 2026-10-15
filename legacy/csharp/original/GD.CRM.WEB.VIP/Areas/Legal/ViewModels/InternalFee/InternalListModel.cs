using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.Legal.ViewModels.Case.InternalFee
{
    public class InternalListModel : BaseListModel
    {
        public List<Dchien.Legal.BizModel.FAM.InternalFee.BizInternalFee> InternalFeeList { get; set; }

        /// </summary>
        public long CaseId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizModel.Legal.Case.BizCase Case { get; set; }

    }

}

