using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using System.Web.UI.WebControls.Expressions;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Entity;

namespace Dchien.Legal.Web.Areas.Lawsuit.ViewModels.IprBase
{
    /// <summary>
    /// 
    /// </summary>
    public class CaseFeeTypeListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseFeeType> CaseFeeTypes { get; set; }
 
    }
}
