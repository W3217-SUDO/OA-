using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Lawsuit.Case;
using Dchien.Legal.Entity.Lawsuit.Case;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case.AR
{
    /// <summary>
    /// 应收账款
    /// </summary>
    public class CaseFeeListModel : BaseListModel
    {

        /// <summary>
        /// 应收账款
        /// </summary>

        public List<Dchien.Legal.BizModel.FAM.AR.CaseFee.BizCaseFee> CaseFeeList { get; set; }


        /// <summary>
        /// 
        /// </summary>
        public long CaseId { get; set; }


    }

}

