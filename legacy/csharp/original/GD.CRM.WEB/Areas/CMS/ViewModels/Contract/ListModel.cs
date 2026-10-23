using System.Collections.Generic;
using Dchien.Legal.BizModel.CMS.Contract;
using Dchien.Legal.Entity.CMS.Contract;

namespace Dchien.Legal.Web.Areas.CMS.ViewModels.Contract
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
