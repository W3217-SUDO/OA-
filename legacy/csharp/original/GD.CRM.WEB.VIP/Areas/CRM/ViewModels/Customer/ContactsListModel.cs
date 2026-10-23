using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.Entity.CRM.Customer;

namespace Dchien.Legal.Web.Areas.CRM.ViewModels.Customer
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


        public bool? IsView { get;set; }
	}
}





