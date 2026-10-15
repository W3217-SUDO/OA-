using System;
using System.Collections.Generic;
using System.Data;
using System.Data.Entity.Infrastructure;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Text;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using System.Web.UI.WebControls;
using Dchien.Legal.BizModel.Lawsuit.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Service.Lawsuit.Case;
using Dchien.Legal.Service.FAM.AR.CaseFee;
using Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.Lawsuit.Controllers
{
    [CheckUserLogin]
    public class CaseFeeFileController : BaseController
    {
        public ActionResult CaseFeeList()
        {
            var model = new Dchien.Legal.Web.Areas.Lawsuit.ViewModels.CaseFee.CaseFeeListModel();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 100;
            return View("CaseFeeList", model);
        }
    }
}
