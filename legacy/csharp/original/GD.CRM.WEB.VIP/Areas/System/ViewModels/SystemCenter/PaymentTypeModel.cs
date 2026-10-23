using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using System.Web.UI.WebControls.Expressions;

using Dchien.Legal.BizModel.FAM.AP.Payment;
using Dchien.Legal.Entity.FAM.AP.Payment;

namespace Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter.PaymentType
{
    public class PaymentTypeModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public BizPaymentType PaymentType { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int PaymentTypeId { get; set; }

	}

    /// <summary>
    /// 
    /// </summary>
    public class PaymentTypeListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizPaymentType> PaymentTypes { get; set; }

        public PaymentTypeSearchCondition SearchCondition { get; set; }

        public PaymentTypeListModel()
        {
            this.SearchCondition = new PaymentTypeSearchCondition();
        }
    }
}





