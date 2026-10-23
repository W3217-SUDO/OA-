using System.Collections.Generic;
using System.Web.UI.WebControls.Expressions;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.BizModel.CRM.Customer;

namespace Dchien.Legal.Web.Areas.FCM.ViewModels.ContractPayment
{
    public class ApplicationCreateModel 
	{
        public Dchien.Legal.BizModel.FAS.AP.Application.BizApplication Application { get; set; }

        /// <summary>
        /// 合同
        /// </summary>
        public BizContract Contract { get; set; }

        /// <summary>
        /// 合同费用
        /// </summary>
        public List<BizContractObject> ContractObjects { get; set; }

        /// <summary>
        /// 客户
        /// </summary>
        public BizCustomer Customer { get; set; }

	}
}
