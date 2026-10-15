using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.FIO.PatentOffice;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.IPR.ViewModels.Case
{
    public class CasePatentOfficeFileListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizCasePatentOfficeFile> CaseFiles { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public CasePatentOfficeFileSearchCondition SearchCondition { get; set; }

	}
}

