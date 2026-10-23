using System.Collections.Generic;
using Dchien.Legal.BizModel.CMS.Contract;
using Dchien.Legal.Entity.CMS.Contract;

namespace Dchien.Legal.Web.Areas.CMS.ViewModels.Contract
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
