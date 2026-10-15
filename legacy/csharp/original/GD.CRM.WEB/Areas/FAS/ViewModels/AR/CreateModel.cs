 
using System.Collections.Generic;
 
using Dchien.Legal.BizModel.FAM.AR;
 

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AR
{
    public class CreateModel 
	{
        /// <summary>
        /// 应收款
        /// </summary>
        public BizAR Ar { get; set; }

        /// <summary>
        /// 应收款明细
        /// </summary>
        public List<BizArObject> ArObjects { get; set; }

	}
}





