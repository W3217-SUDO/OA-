using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Lawsuit;
using Dchien.Legal.BizModel.Lawsuit.Court;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.Lawsuit;
using Dchien.Legal.Entity.Lawsuit.Court;

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





