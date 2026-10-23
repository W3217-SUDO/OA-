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

namespace Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter.CaseFileType
{
    public class CaseFileTypeModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public BizCaseFileType CaseFileType { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int? CaseFileTypeId { get; set; }

        public bool IsNew { get; set; }

    }

    /// <summary>
    /// 
    /// </summary>
    public class CaseFileTypeListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseFileType> CaseTypes { get; set; }

        public CaseFileTypeSearchCondition SearchCondition { get; set; }

        public CaseFileTypeListModel()
        {
            this.SearchCondition = new CaseFileTypeSearchCondition();
        }
    }

    public class CaseTypeListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseType> CaseTypesAll { get; set; }

        public List<int> CaseTypes { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int CaseFileTypeId { get; set; }

    }
}





