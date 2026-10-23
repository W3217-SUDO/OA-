using System.Collections.Generic;
using Dchien.Legal.BizModel.FAM.AR.Invoice;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AR.Invoice
{
    public class CreateModel 
	{
        /// <summary>
        /// 开票信息
        /// </summary>
        public BizInvoice Invoice { get; set; }

        /// <summary>
        /// 费用Id集合
        /// </summary>
        public List<long> CaseFeeIds { get; set; }

	}
}
