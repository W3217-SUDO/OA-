using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel.FIO.PatentOffice;
using Dchien.Legal.BizModel.FIO.PatentOfficeInvoice;
using Dchien.Legal.Entity.FIO.PatentOfficeInvoice;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.FIO.ViewModels
{
    public class PatentOfficeInvoiceFileListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizPatentOfficeInvoiceFile> InvoiceFiles { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public PatentOfficeInvoiceFileSearchCondition SearchCondition { get; set; }

	}
}

