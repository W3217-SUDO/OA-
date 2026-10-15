using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel.Legal.Case;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.BizModel.Legal.Investigation.Clue;

namespace Dchien.Legal.Web.Areas.Legal.ViewModels.Case
{
    public class CaseArchiveModel 
	{
        /// <summary>
        /// 
        /// </summary>
	    public List<BizCase> Cases { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int CaseArchiveTypeId { get; set; }
     }

}





