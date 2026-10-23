using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Account.Message;
using Dchien.Legal.Common;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.Account.Message;
using Dchien.Legal.Web.Areas.Contract.ViewModels.Patent;
using Dchien.Legal.Web.Areas.IPR.ViewModels;
using Dchien.Legal.Service;
using Dchien.Legal.Service.System;
using Dchien.Legal.Web.Areas.Account.ViewModels.Message;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.Contract.Controllers
{
    [CheckUserLogin]
    public class PatentController : Controller
    {
        internal Log Logger = new Log("Contract.Controllers.PatentController");

        public ActionResult CreateUpdate(int? id)
        {
            var model = new ContractModel();

            return View(model);
        }
 
    }
}