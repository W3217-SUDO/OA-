
using Dchien.Legal.BizModel.FAM.AP.Payment.Packing;
using System;
using System.Collections.Generic;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AP.Payment.Packing
{
    public class PackingModel 
	{
        /// <summary>
        /// 付款包信息
        /// </summary>
        public BizPaymentPacking Packing { get; set; }
	}

    public class PackingListModel
    {
 
        /// <summary>
        /// 
        /// </summary>
        public string PackingNo { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public decimal TotalAmount { get; set; }


        public string Remark { get; set; }

 
        public DateTime? PaidDate { get; set; }

 
        public string InvoiceNo { get; set; }

 
        public int? PaymentMode { get; set; }

    }

}
