using System.Collections.Generic;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.Entity.FCM.Contract;

namespace Dchien.Legal.Web.Areas.FCM.ViewModels.Contract
{
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
