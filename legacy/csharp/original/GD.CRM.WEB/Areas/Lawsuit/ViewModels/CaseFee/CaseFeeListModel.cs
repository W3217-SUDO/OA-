using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Lawsuit.Case;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.Lawsuit.ViewModels.CaseFee
{
    public class CaseFeeListModel : BaseListModel
	{
 
        /// <summary>
        /// 
        /// </summary>
        public CaseFeeListModel()
        {
            this.SearchCondition = new Dchien.Legal.Entity.FAM.AR.CaseFee.CaseFeeSearchCondition();
        }

        /// <summary>
        /// 
        /// </summary>
        public Dchien.Legal.Entity.FAM.AR.CaseFee.CaseFeeSearchCondition SearchCondition { get; set; }



	}
}

