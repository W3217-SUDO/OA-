using System;
using System.Collections.Generic;
using Dchien.Legal.BizModel.FAS.AR.CaseFee;
using Dchien.Legal.Entity.FAS.AR.CaseFee;

namespace Dchien.Legal.Web.Areas.FAS.ViewModels.Cashed
{
    public class CashUnsettledListModel 
	{
        /// <summary>
        ///未确认发票
        /// </summary>
        public List<BizCaseFee> CashUnsettledList { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public CaseFeeSearchCondition CashUnsettledSearchCondition { get; set; }

	}
}
