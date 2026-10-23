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
using Dchien.Legal.Web.Areas.Lawsuit.ViewModels;
using Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.CRM.LawFirm;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.Lawsuit.Controllers
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

        [HttpPost]
        public ActionResult GetIndustry(string accountEmail)
        {
            var response = new PostResponse();

            var industrys = new List<Industry>();

            industrys.Add(new Industry() {Id = 1, PId = 0, Name = "11111111111111111"});
            industrys.Add(new Industry() {Id = 2, PId = 0, Name = "22222222222222222"});
            industrys.Add(new Industry() {Id = 3, PId = 0, Name = "33333333333333333"});
            industrys.Add(new Industry() {Id = 4, PId = 0, Name = "44444444444444444"});
            industrys.Add(new Industry() {Id = 5, PId = 0, Name = "55555555555555555"});

            response.Data = industrys;
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


    public class Industry
    {
        /// <summary>
        /// 
        /// </summary>
        public int Id { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int PId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string Name { get; set; }

    }
}