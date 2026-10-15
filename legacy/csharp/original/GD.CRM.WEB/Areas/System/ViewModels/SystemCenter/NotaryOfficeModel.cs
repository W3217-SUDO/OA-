using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.Entity;
using Dchien.Legal.BizModel.BAS.NotaryOffice;
using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.Entity.BAS.NotaryOffice;

namespace Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter
{
    public class NotaryOfficeModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public BizNotaryOffice NotaryOffice { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int NotaryOfficeId { get; set; }

	}

    public class NotaryOfficeListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizNotaryOffice> NotaryOfficeList { get; set; }

        public NotaryOfficeListModel()
        {
            this.SearchCondition = new NotaryOfficeSearchCondition();
        }
        public NotaryOfficeSearchCondition SearchCondition { get; set; }

    }
}





