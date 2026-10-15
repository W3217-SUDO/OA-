using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.CRM.LawFirm;

namespace Dchien.Legal.Web.Areas.CRM.ViewModels.LawFirm
{
    public class ContactsListModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizLawFirmContacts> LawFirmContactsList { get; set; }


        public ContactsListModel()
        {
            this.SearchCondition = new Dchien.Legal.Entity.CRM.LawFirm.ContactsSearchCondition();
        }
        public Dchien.Legal.Entity.CRM.LawFirm.ContactsSearchCondition SearchCondition { get; set; }


        /// <summary>
        /// 
        /// </summary>
        public int LawFirmId { get; set; }
	}
}





