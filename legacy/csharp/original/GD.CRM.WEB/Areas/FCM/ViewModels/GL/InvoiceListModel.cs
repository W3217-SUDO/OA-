using System;
using System.Collections.Generic;
using Dchien.Legal.BizModel.CMS.GL;

namespace Dchien.Legal.Web.Areas.FCM.ViewModels.GL
{
    public class InvoiceListModel 
	{
        /// <summary>
        /// 合同
        /// </summary>
        public List<BizInvoice> InvoiceList { get; set; }

        public string ContractId { get; set; }


	}
}
