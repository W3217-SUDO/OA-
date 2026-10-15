using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;

namespace Dchien.Legal.Web.Areas.CRM.ViewModels.Customer
{
    public class ContactsPhotoModel 
	{
        /// <summary>
        /// 联系人Id
        /// </summary>
        public int ContactsId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string CustomerNo { get; set; }

        /// <summary>
        ///  联系人No
        /// </summary>
        public string ContactsGuid { get; set; }

	}
}
