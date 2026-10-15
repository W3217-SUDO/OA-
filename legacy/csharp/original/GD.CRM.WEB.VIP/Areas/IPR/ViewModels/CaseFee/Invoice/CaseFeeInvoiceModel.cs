using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Entity.FAM.AR.CaseFee;
using Dchien.Legal.Entity.FAM.Invoice;
using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.Entity.System;


namespace Dchien.Legal.Web.Areas.IPR.ViewModels.CaseFee.Invoice
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

        public CaseClassType CaseClassType { get; set; }

        public InvoiceType InvoiceType { get; set; }



    }
}
