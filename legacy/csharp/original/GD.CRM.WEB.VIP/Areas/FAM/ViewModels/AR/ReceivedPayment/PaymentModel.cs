using Dchien.Legal.BizModel.FAM.AR.ReceivedPayment;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.Entity.FAM.AR.ReceivedPayment;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment
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

    public class PaymentApplyModel
    {
        /// <summary>
        /// 回款
        /// </summary>
        public BizPayment Payment { get; set; }

        public PaymentObjectSearchCondition SearchCondition { get; set; }

        public PaymentApplyModel()
        {
            this.SearchCondition = new PaymentObjectSearchCondition();
        }

    }

    public class PaymentAppliedModel
    {
        /// <summary>
        /// 回款
        /// </summary>
        public BizPayment Payment { get; set; }

        public PaymentObjectSearchCondition SearchCondition { get; set; }

        public PaymentAppliedModel()
        {
            this.SearchCondition = new PaymentObjectSearchCondition();
        }

    }
 
}
