using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.IPR.ViewModels.Case
{
    public class CaseFeeListModel : BaseListModel
	{


        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseFeeItem> CaseFees { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long CaseId { get; set; }


	}

    /// <summary>
    /// 
    /// </summary>
    public class CaseFeeSearchListModel : BaseListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public CaseFeeSearchListModel()
        {
            this.SearchCondition = new Dchien.Legal.Entity.IPR.Case.CaseFeeSearchCondition();
        }

        /// <summary>
        /// 
        /// </summary>
        public Dchien.Legal.Entity.IPR.Case.CaseFeeSearchCondition SearchCondition { get; set; }


    }
}

