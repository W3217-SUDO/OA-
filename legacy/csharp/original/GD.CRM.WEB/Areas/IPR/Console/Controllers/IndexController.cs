using System;
using System.Collections.Generic;
using System.Web.Mvc;
using System.Linq;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Web.Areas.Console.ViewModels.Index;
using Dchien.Legal.Service.Legal.Case;
using Dchien.Legal.Entity.TP.Task;
using Dchien.Legal.Service.TP.Task;
using Dchien.Legal.Entity.Legal.Case;
using Dchien.Legal.Service;

namespace Dchien.Legal.Web.Areas.Console.Controllers
{
    [CheckUserLogin]
    public class IndexController : Controller
    {
        internal Log Logger = new Log("Console.Controllers.IndexController");
 
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult Index()
        {
            var model = new Dchien.Legal.Web.Areas.Console.ViewModels.Index.IndexModel();
            return View(model);
        }

    }
}