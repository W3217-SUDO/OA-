using System;
using System.Collections.Generic;
using Dchien.Legal.BizModel.FAS.AR.CaseFee;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.FCM.ViewModels.GL
{
    /// <summary>
    /// 
    /// </summary>
    public class ARCaseFeeListModel : BaseListModel
	{
        /// <summary>
        /// 应收款列表
        /// </summary>
        public List<BizCaseFee> CaseFeeList { get; set; }

        public string ContractId { get; set; }

        


	}
}
