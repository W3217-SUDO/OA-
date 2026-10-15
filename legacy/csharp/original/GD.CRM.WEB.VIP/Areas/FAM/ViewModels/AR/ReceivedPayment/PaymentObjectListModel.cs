using System;
using System.Collections.Generic;
using Dchien.Legal.Web.Models;
using Dchien.Legal.BizModel.FAM.AR.ReceivedPayment;
using Dchien.Legal.Entity.FAM.AR.ReceivedPayment;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment
{
    public class PaymentObjectListModel : BaseListModel
	{

        /// <summary>
        /// 回款分配记录
        /// </summary>
        public List<BizPaymentObject> PaymentObjects { get; set; }

        /// <summary>
        /// 回款记录
        /// </summary>
        public BizPayment Payment { get; set; }

       public   PaymentObjectSearchCondition SearchCondition { get; set; }


    }
}

