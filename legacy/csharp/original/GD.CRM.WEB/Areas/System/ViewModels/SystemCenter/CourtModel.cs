using System.Collections.Generic;

using Dchien.Legal.BizModel.BAS.Court;
using Dchien.Legal.Entity.BAS.Court;

namespace Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter
{
    public class CourtModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public BizCourt Court { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int CourtId { get; set; }

	}

    public class CourtListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizCourt> CourtList { get; set; }

        public CourtListModel()
        {
            this.SearchCondition = new CourtSearchCondition();
        }
        public CourtSearchCondition SearchCondition { get; set; }

    }
}





