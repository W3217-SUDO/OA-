using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case
{
    public class CaseAssistedFeeListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseAssistedFee> CaseAssistedFees { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long CaseId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string CaseNo { get; set; }

	}
}

