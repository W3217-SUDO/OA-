using System;
using System.Collections.Generic;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.FIO.PatentOffice;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.FIO.ViewModels
{
    public class PatentOfficeFileImportModel
    {
        public BizPatentOfficeFile PatentOfficeFile { get; set; }

    }

    public class PatentOfficeFileCheckListModel : BaseListModel
    {

        /// <summary>
        /// 
        /// </summary>
        public CasePatentOfficeFileSearchCondition SearchCondition { get; set; }

    }
}
