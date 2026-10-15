using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.Web.Models;
using Dchien.Legal.Entity.FAM.AR.Payment;


namespace Dchien.Legal.Web.Areas.RPT.ViewModels.Report
{
    public class CountJPaymentListModel
    {
        public CountJPaymentListModel()
        {
            this.SearchCondition = new PaymentSearchCondition();
        }

        public PaymentSearchCondition SearchCondition { get; set; }
 
	}
}





