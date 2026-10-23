using System.Collections.Generic;
using Dchien.Legal.BizModel.FAM.InternalFee.Payment.Packing;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.InternalFee.Payment.Packing
{
    public class PrintModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public long PackingId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public Dchien.Legal.BizModel.System.BizCompany Company { get; set; }
        /// <summary>
        /// 
        /// </summary>
        public BizPaymentPacking Packing { get; set; }
	}
}
