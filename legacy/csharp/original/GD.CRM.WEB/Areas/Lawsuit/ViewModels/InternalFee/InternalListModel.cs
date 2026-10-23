using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Lawsuit.Case;
using Dchien.Legal.Entity.Lawsuit.Case;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case.InternalFee
{
    public class InternalListModel : BaseListModel
    {
        public List<Dchien.Legal.BizModel.FAM.Settlement.BizInternalFee> InternalFeeList { get; set; }

        /// </summary>
        public long CaseId { get; set; }

    }

}

