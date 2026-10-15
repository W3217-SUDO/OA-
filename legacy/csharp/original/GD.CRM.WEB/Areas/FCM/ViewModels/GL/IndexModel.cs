using System.Collections.Generic;
using Dchien.Legal.BizModel.CMS.Contract;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.BizModel.CMS.GL;

namespace Dchien.Legal.Web.Areas.FCM.ViewModels.GL
{
    public class IndexModel 
	{
        /// <summary>
        /// 合同台账
        /// </summary>
        public BizGeneralLedger GeneralLedger { get; set; }

        /// <summary>
        /// 合同
        /// </summary>
        public BizContract Contract { get; set; }

        /// <summary>
        /// 客户
        /// </summary>
        public BizCustomer Customer { get; set; }


        /// <summary>
        /// AR 应收账款
        /// </summary>
        public List<Dchien.Legal.BizModel.FAS.AR.CaseFee.BizCaseFee> ARCaseFeeList { get; set; }
 

        /// <summary>
        /// AP 应付账款
        /// </summary>
        public List<Dchien.Legal.BizModel.FAS.AP.CaseFee.BizCaseFee> APCaseFeeList { get; set; }
      

	}
}
