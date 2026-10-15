using System.Collections.Generic;
using System.Web.UI.WebControls.Expressions;

using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.BizModel.Legal.Case;
using Dchien.Legal.BizModel.FAM.InternalFee.Payment;
using Dchien.Legal.BizModel.FAM.InternalFee.Payment.Audit;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.InternalFee.Payment
{
    public class PaymentModel 
	{
        /// <summary>
        /// 付款信息
        /// </summary>
        public BizPayment Payment { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizCase Case { get; set; }

        /// <summary>
        /// 合同
        /// </summary>
        public BizContract Contract { get; set; }

        /// <summary>
        /// 客户
        /// </summary>
        public BizCustomer Customer { get; set; }

    }

    /// <summary>
    /// 
    /// </summary>
    public class PaymentMultiCreateModel
    {

    }

    public class PaymentAuditModel : PaymentModel
    {
        /// <summary>
        /// 
        /// </summary>
        public BizPaymentAudit Audit { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizPayment> Payments { get; set; }

        public string PaymentIds { get; set; }
    }
}
