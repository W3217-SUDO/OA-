using System;
using System.Collections.Generic;
using Dchien.Legal.BizModel.FAS.AP.CaseFee;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.CMS.ViewModels.GL
{
    /// <summary>
    /// 
    /// </summary>
    public class APCaseFeeListModel : BaseListModel
	{
        /// <summary>
        /// 应付款列表
        /// </summary>
        public List<BizCaseFee> CaseFeeList { get; set; }

        public string ContractId { get; set; }


	}
}
