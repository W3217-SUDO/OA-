using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using System.Web.UI.WebControls.Expressions;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.IPR.Case;

namespace Dchien.Legal.Web.Areas.CRM.ViewModels.CaseFee
{
    public class CaseFeeInformModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseFeeItem> CaseFees { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long? CustomerId { get; set;}

        /// <summary>
        ///
        /// </summary>
        public string CustomerNo { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string CustomerName { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string ContractNo { get; set; }

        /// <summary>
        /// 
        /// </summary>

        public long? ContractId { get; set; }

	}

    /// <summary>
    /// 
    /// </summary>
    public class CaseFeeInformListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseFeeItem> CaseFees { get; set; }

 
    }
}





