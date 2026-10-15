using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Web;
using System.Web.Mvc;


using Dchien.Legal.BizModel.System;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Web.Areas.System.ViewModels.User;
using Dchien.Legal.Service;
using log4net.Repository.Hierarchy;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.System.Controllers
{
    [CheckUserLogin]
    public class UserController : Controller
    {
        internal Log Logger = new Log("System.Controllers.UserController");
 
        #region 用户基本信息

        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerId"></param>
        /// <param name="customerSourceTypeId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CreateUpdate(long? userId)
        {
            var model = new CreateUpdateModel();

            if (userId.HasValue && userId.Value > 0)
            {
                model.User = null;
            }
            else
            {
                model.User = new BizUser();
                model.User.UserBasic = new BizUserBasic(); 
            }

            return View(model);
        }


        #endregion

    }
}
