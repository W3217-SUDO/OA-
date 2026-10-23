using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;

using Dchien.Legal.Entity.Legal.Case;

namespace Dchien.Legal.Web.Areas.Legal.ViewModels.CaseList
{
    public class CaseListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public CaseSearchCondition SearchCondition { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public CaseListModel()
        {
            this.SearchCondition = new CaseSearchCondition();
        }

    }
}