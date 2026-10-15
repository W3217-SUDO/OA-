using System;
using System.Collections.Generic;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.CMS.ViewModels.ContractFile
{
    public class ContractFileListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizContractFile> ContractFiles { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long ContractId { get; set; }


	}
}

