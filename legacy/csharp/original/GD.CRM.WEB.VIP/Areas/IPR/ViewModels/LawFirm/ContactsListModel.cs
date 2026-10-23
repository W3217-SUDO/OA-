using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using SunHold.Legal.BizModel;
using SunHold.Legal.BizModel.IPR.LawFirm;

namespace SunHold.Legal.Web.Areas.IPR.ViewModels.LawFirm
{
    public class ContactsListModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizLawFirmContacts> LawFirmContactsList { get; set; }


        public ContactsListModel()
        {
            this.SearchCondition = new SunHold.Legal.Entity.IPR.LawFirm.ContactsSearchCondition();
        }
        public SunHold.Legal.Entity.IPR.LawFirm.ContactsSearchCondition SearchCondition { get; set; }


        /// <summary>
        /// 
        /// </summary>
        public int LawFirmId { get; set; }
	}
}





