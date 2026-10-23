using System.Collections.Generic;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.BizModel.FAM.Invoice;
using Dchien.Legal.BizModel.FCM.Contract;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.Invoice
{
    public class InvoiceModel 
	{

        /// <summary>
        /// 开票信息
        /// </summary>
        public BizInvoice Invoice { get; set; }

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
