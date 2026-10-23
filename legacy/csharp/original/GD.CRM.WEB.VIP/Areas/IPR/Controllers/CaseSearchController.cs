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

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.CRM.LawFirm;
using Dchien.Legal.Common;
using Dchien.Legal.Entity;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Web.Areas.IPR.ViewModels;
using Dchien.Legal.Web.Areas.IPR.ViewModels.Case;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.CRM.LawFirm;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.IPR.Controllers
{
    public class CaseSearchController : BaseController
    {
        /// <summary>
        /// 
        /// </summary>
        /// <param name="accountEmail"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult GetCase(string accountEmail)
        {
            var response = new PostResponse();
            var caseInfo = CaseService.Instance.GetCaseBasic(1);
            response.Data = caseInfo;
            response.IsSuccess = true;
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [HttpGet]
        public ActionResult GetCaseList()
        {
            var response = new PostResponse();

            var caseList = CaseService.Instance.GetTop10CaseList();
            response.Data = caseList;
            response.IsSuccess = true;
            return Json(response, JsonRequestBehavior.AllowGet);
        }


    }

}