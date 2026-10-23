using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.CRM.Customer;

namespace Dchien.Legal.Web.Areas.CRM.ViewModels.Customer
{
    public class ContactsModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public BizCustomerContacts Contacts { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long CustomerId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string CustomerNo { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int ContactsId { get; set; }

        /// <summary>
	    /// 获取文本框状态
	    /// </summary>
	    public HtmlString GetTextBoxState(string style)
	    {
	        return new HtmlString(@"style=""" + style + @"""");
	    }
	}
}





