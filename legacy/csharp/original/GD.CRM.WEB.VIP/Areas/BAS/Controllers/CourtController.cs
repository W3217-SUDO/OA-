using System;
using System.Collections;
using System.Collections.Generic;
using System.Web.Mvc;

using Dchien.Legal.BizModel.BAS.Court;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Service.BAS.Court;

namespace Dchien.Legal.Web.Areas.BAS.Controllers
{
    public class CourtController : Controller
    {
        #region 法院


        /// <summary>
        /// 
        /// </summary>
        /// <param name="keyword"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult Courts(string keyword)
        {
            var response = new PostResponse();

            try
            {
                var courts = CourtService.Instance.GetCourts();

                var list = new List<Tuple<string, string>>();
                courts.ForEach(x =>
                {
                    if (!string.IsNullOrEmpty(x.CourtName) && x.CourtName.Contains(keyword))
                    {
                        list.Add(new Tuple<string, string>(x.CourtCode.ToString(), x.CourtName));
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

        #endregion
     
    }
}
