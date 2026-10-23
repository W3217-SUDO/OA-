using System;
using System.Collections.Generic;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.CRM.ViewModels.CustomerFile
{
    public class CustomerFileListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizContractFile> CustomerFiles { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long? CustomerId { get; set; }


	}
}

