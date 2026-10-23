using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using System.Text;
using log4net.Repository.Hierarchy;

using Dchien.Legal.BizModel.HR;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.HR;
using Dchien.Legal.Service;
using Dchien.Legal.Service.HR.Staff;
using Dchien.Legal.Service.HR.Staff.File;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Web.Areas.HR.ViewModels.Staff;
using Dchien.Legal.Entity.HR.Staff;
using Dchien.Legal.BizModel.HR.Staff;
using Dchien.Legal.Service.HR.Staff.Event;

namespace Dchien.Legal.Web.Areas.HR.Controllers
{
    [CheckUserLogin]
    public class StaffPerformanceController : Controller
    {
        internal Log Logger = new Log("Dchien.Legal.Web.Areas.HR.Controllers.StaffPerformanceController");

    }
}
