using System.Collections.Generic;
using System.Web.UI.WebControls.Expressions;
using Dchien.Legal.BizModel.FAM.AP.Payment;
using Dchien.Legal.BizModel.FAM.AP.Payment.Audit;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.BizModel.FAM.AP.Payment.Packing;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AP.Payment
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

        /// <summary>
        /// 
        /// </summary>
        public BizPaymentPacking Packing { get; set; }

	}

    public class PaymentAuditModel : PaymentModel
    {
        /// <summary>
        /// 
        /// </summary>
        public BizPaymentAudit Audit { get; set; }
    }
}
