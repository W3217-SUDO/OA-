using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.Entity;
using Dchien.Legal.BizModel.BAS.Type;
using Dchien.Legal.Entity.BAS.Type;

namespace Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter
{
    public class CauseModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public BizCause Cause { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int CauseId { get; set; }

	}

    public class CauseListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizCause> CauseList { get; set; }

        public CauseListModel()
        {
            this.SearchCondition = new CauseSearchCondition();
        }
        public CauseSearchCondition SearchCondition { get; set; }

    }
}





