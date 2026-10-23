using System;
using System.Collections.Generic;
using Dchien.Legal.BizModel.FAM.AR;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AR
{
    public class ARObjectListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizArObject> ARObjects { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long ContractId { get; set; }


	}
}

