using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.Entity;
using Dchien.Legal.BizModel.BAS.Type;
using Dchien.Legal.Entity.BAS.Type;

namespace Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter.CaseType
{
    public class CaseTypeModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public BizCaseType CaseType { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int CaseTypeId { get; set; }

	}

    public class CaseTypeListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseType> CaseTypeList { get; set; }

        public CaseTypeListModel()
        {
            this.SearchCondition = new CaseTypeSearchCondition();
        }
        public CaseTypeSearchCondition SearchCondition { get; set; }

    }

    /// <summary>
    /// 
    /// </summary>
    public class CasePhaseListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizCasePhase> CasePhasesAll { get; set; }
        
        public List<int> CasePhases { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int CaseTypeId { get; set; }
 
    }

    /// <summary>
    /// 
    /// </summary>
    public class CaseFileTypeListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseFileType> CaseFileTypesAll { get; set; }

        public List<int> CaseFileTypess { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int CaseTypeId { get; set; }

    }

    /// <summary>
    /// 
    /// </summary>
    public class CaseFileTypeCaseFeeTypeListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseFeeType> CaseFeeTypesAll { get; set; }

        public List<int> CaseFeeTypes { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int CaseFileTypeId { get; set; }

    }
}





