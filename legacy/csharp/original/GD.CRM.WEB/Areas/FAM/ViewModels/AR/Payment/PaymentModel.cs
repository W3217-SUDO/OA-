using Dchien.Legal.BizModel.FAM.AR.Payment;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.BizModel.CRM.Customer;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AR.Payment
{
    public class PaymentModel 
	{
        /// <summary>
        /// 付款信息
        /// </summary>
        public BizPayment Payment { get; set; }

        /// <summary>
        /// 合同
        /// </summary>
        public BizContract Contract { get; set; }

        /// <summary>
        /// 客户
        /// </summary>
        public BizCustomer Customer { get; set; }

	}
 
}
