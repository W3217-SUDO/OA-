using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using SunHold.Legal.BizModel;
using SunHold.Legal.BizModel.IPR.Customer;
using SunHold.Legal.Entity.IPR.Customer;

namespace SunHold.Legal.Web.Areas.IPR.ViewModels.Customer
{
    public class ContactsListModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizCustomerContacts> CustomerContactsList { get; set; }


        public ContactsListModel()
        {
            this.SearchCondition = new ContactsSearchCondition();
        }
        public ContactsSearchCondition SearchCondition { get; set; }


        /// <summary>
        /// 
        /// </summary>
        public int CustomerId { get; set; }
	}
}





