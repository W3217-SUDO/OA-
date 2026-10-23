using System.Collections.Generic;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.Entity.FAM.AP.Payment;
using Dchien.Legal.Entity.FCM.Contract;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AR
{
    /// <summary>
    /// 应付款申请列表
    /// </summary>
    public class ListModel 
	{
        /// <summary>
        /// 合同
        /// </summary>
        public List<BizContract> ContractList { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public ContractSearchCondition SearchCondition { get; set; }

	}
}
