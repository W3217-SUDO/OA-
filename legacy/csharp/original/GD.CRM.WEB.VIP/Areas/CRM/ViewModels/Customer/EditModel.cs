using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.CRM.Customer;

namespace Dchien.Legal.Web.Areas.CRM.ViewModels.Customer
{
    public class CreateUpdateModel
    {
        public BizCustomer Customer { get; set; }

        /// <summary>
        /// 客户来源类型:1：非诉讼，2：诉讼
        /// </summary>
        public int CustomerSourceType { get; set; }
    }
}
