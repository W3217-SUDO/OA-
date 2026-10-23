using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.IPR.ViewModels.Case
{
    public class CaseFeeFileListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
        public List<Dchien.Legal.BizModel.FAM.AR.CaseFee.BizCaseFee> CaseFees { get; set; }
 
        public Dchien.Legal.Entity.IPR.Case.CaseFeeFileSearchCondition SearchCondition { get; set; }

        public CaseFeeFileListModel()
        {
            this.SearchCondition = new Dchien.Legal.Entity.IPR.Case.CaseFeeFileSearchCondition();
        }

	}
}

