using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas.Legal.ViewModels.CaseFee.Invoice
{
    public class CaseFeeInvoiceModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<long> CaseFeeIds { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizModel.FAM.Invoice.BizInvoiceFile Invoice { get; set; }
        

        /// <summary>
        /// 
        /// </summary>
        public int? PaymentMode { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string Payer { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string PayerName { get; set; }
 

    }
}
