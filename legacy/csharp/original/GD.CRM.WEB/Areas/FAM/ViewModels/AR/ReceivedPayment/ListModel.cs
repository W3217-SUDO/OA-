using System.Collections;
using System.Collections.Generic;

using Dchien.Legal.Entity.FAM.AR.ReceivedPayment;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment
{
    /// <summary>
    /// 
    /// </summary>
    public class ListModel 
	{
        public PaymentSearchCondition SearchCondition { get; set; }

	}

    /// <summary>
    /// 
    /// </summary>
    public class PaymentListModel
    {
        public List<BizModel.FAM.AR.ReceivedPayment.BizPayment> PaymentList { get; set; }

    }
}
