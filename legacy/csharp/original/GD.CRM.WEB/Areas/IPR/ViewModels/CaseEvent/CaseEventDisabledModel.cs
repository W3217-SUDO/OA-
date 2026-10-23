using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;

namespace Dchien.Legal.Web.Areas.IPR.ViewModels.CaseEvent
{
    public class CaseEventDisabledModel
    {

        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseEventDisabled> DisabledEvents{get;set;}

        /// <summary>
        /// 
        /// </summary>

        public string Remark { get; set; }

    }

    /// <summary>
    /// 
    /// </summary>
    public class CaseEventDisabledAllModel
    {

        /// <summary>
        /// 
        /// </summary>

        public string Remark { get; set; }

    }

    public class CaseEventDisabledEventTypeModel
    {
 
        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseEventType> CaseEventTypes { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string Remark { get; set; }
    }

}





