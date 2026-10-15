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
    public class CaseFileListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
	    public List<BizCaseFile> CaseFiles { get; set; }

        public Dchien.Legal.Entity.IPR.Case.CaseFileSearchCondition SearchCondition { get; set; }

        public CaseFileListModel()
        {
            this.SearchCondition = new Dchien.Legal.Entity.IPR.Case.CaseFileSearchCondition();
        }

	}
}

