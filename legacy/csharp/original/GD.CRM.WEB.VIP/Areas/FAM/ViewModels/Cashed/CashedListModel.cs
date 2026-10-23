using System;
using System.Collections.Generic;
using Dchien.Legal.BizModel.FAS.AR.CaseFee;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.FAS.AR.CaseFee;

namespace Dchien.Legal.Web.Areas.FAS.ViewModels.Cashed
{
    public class CashedListModel 
	{
        /// <summary>
        /// 到账管理
        /// </summary>
        public List<BizCaseFeeCashed> CashedList { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public CaseFeeCashedSearchCondition CashedSearchCondition { get; set; }

	}
}
