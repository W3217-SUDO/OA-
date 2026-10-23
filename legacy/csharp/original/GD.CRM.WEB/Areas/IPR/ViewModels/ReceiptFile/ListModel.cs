using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.Entity.IPR.Receipt;

namespace Dchien.Legal.Web.Areas.IPR.ViewModels.ReceiptFile
{
    public class ListModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public ListModel()
        {

        }

        /// <summary>
        /// 
        /// </summary>
        public ReceiptRuleFileSearchCondition SearchCondition { get; set; }

    }
}





