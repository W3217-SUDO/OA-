using System;
using System.Collections.Generic;
using System.Web.Mvc;

using Dchien.Legal.Web.Models;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Service.BAS.Court;
using Dchien.Legal.Web.Areas.BAS.ViewModels.CourtOfficer;
using System.Linq;

namespace Dchien.Legal.Web.Areas.BAS.Controllers
{
    public class CourtOfficerController : Controller
    {

        [HttpPost]
        [CheckUserLogin]
        public ActionResult Create(string courtNo)
        {
            var model = new CourtOfficerModel();
            model.CourtOfficer = new BizModel.BAS.Court.BizCourtOfficer();
            model.CourtOfficer.CourtNo = courtNo;
            return PartialView("PartialView/Create", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="courtNo"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult Edit(string courtOfficerNo)
        {
            var model = new CourtOfficerModel();
            model.CourtOfficer = CourtOfficerService.Instance.GetCourtOfficer(courtOfficerNo);
            return PartialView("PartialView/Edit", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CreateUpdate(CourtOfficerModel model)
        {
            var response = new PostResponse();

            try
            {
                bool result = CourtOfficerService.Instance.CreateUpdate(model.CourtOfficer);

                if (result)
                {
                    response.Data = model.CourtOfficer;

                    response.Message = "保存成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "保存失败！";
                    response.IsSuccess = false;
                }
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="keyword"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CourtOfficers(string courtNo,string keyword)
        {
            var response = new PostResponse();

            try
            {
                var courts = CourtOfficerService.Instance.GetCourtOfficers();

                var list = new List<Tuple<string, string>>();
                courts.ForEach(x =>
                {
                    if (!string.IsNullOrEmpty(x.OfficerName) && x.OfficerName.Contains(keyword) && x.CourtNo == courtNo)
                    {
                        list.Add(new Tuple<string, string>(x.OfficerNo.ToString(), x.OfficerName));
                    }
                });

                response.Data = list;
                response.IsSuccess = true;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult GetCourtOfficers(string courtNo)
        {
            var response = new PostResponse();

            try
            {
                var courts = CourtOfficerService.Instance.GetCourtOfficers(courtNo);

                var list = new List<Tuple<string, string>>();

                if (courts != null && courts.Any())
                {
                    courts.ForEach(x =>
                    {
                        list.Add(new Tuple<string, string>(x.OfficerNo.ToString(), x.OfficerName));
                    });
                }

                response.Data = list;
                response.IsSuccess = true;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }



    }
}
