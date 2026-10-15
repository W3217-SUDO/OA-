using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Areas.Legal.ViewModels.Case;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
 using Dchien.Legal.Entity.Account;
using Dchien.Legal.Entity.BAS.Type;


namespace Dchien.Legal.Web.Areas.Legal.Controllers
{
    [CheckUserLogin]
    public class LitigantController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.LitigantController");


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        public ActionResult LitigantAgent()
        {
            var model = new LitigantAgentModel();
            model.LitigantAgent = new BizModel.Legal.Case.BizLitigantAgent();
            return PartialView("PartialView/LitigantAgent", model);
        }
    }
}
