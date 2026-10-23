using System.Collections.Generic;
using Dchien.Legal.BizModel.FAM.AP.Payment.Packing;
using Dchien.Legal.Entity.BAS.Type;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AP.Payment.Packing
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
        public string PackingNo { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public Dchien.Legal.BizModel.System.BizCompany Company { get; set; }
        /// <summary>
        /// 
        /// </summary>
        public BizPaymentPacking Packing { get; set; }

        public GroupId GroupId { get; set; }
    }

    public class PrintListModel
    {

        public string PackingNo { get; set; }
        /// <summary>
        /// 
        /// </summary>
        public Dchien.Legal.BizModel.System.BizCompany Company { get; set; }
        /// <summary>
        /// 
        /// </summary>
        public List<BizPaymentPacking> PackingList { get; set; }

        public GroupId GroupId { get; set; }
    }
}
