using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using SunHold.Legal.BizModel;
using SunHold.Legal.BizModel.IPR.LawFirm;

namespace SunHold.Legal.Web.Areas.IPR.ViewModels.LawFirm
{
    public class ContactsModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public BizLawFirmContacts Contacts { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long LawFirmId { get; set; }

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





