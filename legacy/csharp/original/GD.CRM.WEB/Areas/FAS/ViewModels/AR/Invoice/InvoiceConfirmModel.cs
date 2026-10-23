using System;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AR.Invoice
{
    /// <summary>
    ///发票
    /// </summary>
    public class InvoiceConfirmModel
    {


        /// <summary>
        /// 票据Id
        /// </summary>
        public long InvoiceId { get; set; }

        /// <summary>
        /// 票据编号
        /// </summary>
        public string InvoiceNo { get; set; }

        /// <summary>
        /// 票据金额
        /// </summary>
        public decimal? InvoiceAmount { get; set; }

        /// <summary>
        /// 票据日期
        /// </summary>
        public DateTime? InvoiceDate { get; set; }
    }



}
