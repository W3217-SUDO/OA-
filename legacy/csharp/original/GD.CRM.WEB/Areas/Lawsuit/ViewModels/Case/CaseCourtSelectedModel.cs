using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Lawsuit.Court;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.Lawsuit.Court;


namespace Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case
{
    public class CaseCourtSelectedModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizCourt> Customers { get; set; }

        public CourtSearchCondition SearchCondition { get; set; }

        public long CaseId { get; set; }

    }
}





