using System.Collections.Generic;
using System.Web.UI.WebControls.Expressions;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.Entity.FCM.Contract;

namespace Dchien.Legal.Web.Areas.FCM.ViewModels.Contract
{
    public class DraftModel 
	{
        /// <summary>
        /// 合同
        /// </summary>
        public BizContract Contract { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizContractObject> ContractObjects { get; set; }

        /// <summary>
        /// 客户
        /// </summary>
        public BizCustomer Customer { get; set; }

	}
}
