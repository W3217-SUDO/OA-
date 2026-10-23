using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Security.Permissions;
using System.Web;
using System.Web.Mvc;
using System.Xml.Serialization;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.IPR.Case;


namespace Dchien.Legal.Web.Areas.IPR.ViewModels.Case
{
    /// <summary>
    /// 
    /// </summary>
    public class CaseTreeModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizCase> CaseList { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long CustomerId { get; set; }

        public string SearchKeyword { get; set; }


        /// <summary>
        /// 
        /// </summary>
        public BizCustomer Customer { get; set; }

    }

}
