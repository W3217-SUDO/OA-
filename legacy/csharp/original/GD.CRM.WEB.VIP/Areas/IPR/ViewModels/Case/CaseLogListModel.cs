using System.Collections.Generic;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.IPR.ViewModels.Case
{
    public class CaseLogListModel : BaseListModel
    {


        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseLog> CaseLogs { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long CaseId { get; set; }


	}
}

