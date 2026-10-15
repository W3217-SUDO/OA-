using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using System.Web.UI.WebControls.Expressions;
using Dchien.Legal.BizModel;

using Dchien.Legal.Entity;
using Dchien.Legal.BizModel.BAS.Type;
using Dchien.Legal.Entity.BAS.Type;

namespace Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter.CaseFeeType
{
    public class CaseFeeTypeModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public BizCaseFeeType CaseFeeType { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int? CaseFeeTypeId { get; set; }


        public bool IsNew { get; set; }

	}

    /// <summary>
    /// 
    /// </summary>
    public class CaseFeeTypeListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseFeeType> CaseFeeTypes { get; set; }

        public CaseFeeTypeSearchCondition SearchCondition { get; set; }

        public CaseFeeTypeListModel()
        {
            this.SearchCondition = new CaseFeeTypeSearchCondition();
        }
    }
}





