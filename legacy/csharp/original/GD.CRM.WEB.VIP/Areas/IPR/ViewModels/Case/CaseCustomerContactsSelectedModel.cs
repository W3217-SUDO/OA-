using System.Collections.Generic;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.IPR.ViewModels.Case
{
    public class CaseCustomerContactsSelectedModel : BaseListModel
    {
        /// <summary>
        /// 
        /// </summary>
	    public List<BizCustomerContacts> ContactsList { get; set; }
 

        public long CustomerId { get; set; }

        public long CaseId { get; set; }

    }
}





