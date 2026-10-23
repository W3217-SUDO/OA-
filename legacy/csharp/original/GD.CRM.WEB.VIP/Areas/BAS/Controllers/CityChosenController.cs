using System;
using System.Collections.Generic;
using System.Web.Mvc;
 
using Dchien.Legal.Web.Controllers;
 
namespace Dchien.Legal.Web.Areas.BAS.Controllers
{
    public class CityChosenController : Controller
    {

        [HttpPost]
        [CheckUserLogin]
        public ActionResult CityChosen()
        {
              return PartialView("PartialView/CityChosen");
        }
     
    }
}
