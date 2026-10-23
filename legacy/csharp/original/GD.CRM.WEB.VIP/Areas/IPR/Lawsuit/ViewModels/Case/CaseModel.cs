using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel.Lawsuit.Case;
using Dchien.Legal.Entity.Lawsuit.Case;

namespace Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case
{
    public class CaseModel : ListModel
	{
        /// <summary>
        /// 
        /// </summary>
	    public BizCase Case { get; set; }

        /// <summary>
        /// 
        /// </summary>

        public long CaseId
        {
            get;
            set;
        }


        /// <summary>
        /// 
        /// </summary>
        public List<int> CustomerIds { get; set; }

	}


    public class CaseListModel
    {
 

        /// <summary>
        /// 
        /// </summary>
        public List<BizCase> CaseList { get; set; }

        public CaseSearchCondition SearchCondition { get; set; }

    }

    /// <summary>
    /// 
    /// </summary>
    public class CaseListToWordModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<long> CaseIds { get; set; }

        /// <summary>
        /// 文档类型Id
        /// </summary>
        public int? CaseFileTypeId { get; set; }

    } 
}





