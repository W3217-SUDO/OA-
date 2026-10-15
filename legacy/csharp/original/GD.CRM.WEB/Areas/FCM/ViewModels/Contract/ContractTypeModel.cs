using System.Collections.Generic;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.Entity.FCM.Contract;

namespace Dchien.Legal.Web.Areas.FCM.ViewModels.Contract
{
    public class ContractTypeModel 
	{
        /// <summary>
        /// 客户
        /// </summary>
        public long CustomerId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public ContractType? ContractType { get; set; }

	}
}
