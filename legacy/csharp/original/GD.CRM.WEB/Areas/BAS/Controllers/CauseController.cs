using System;
using System.Collections;
using System.Collections.Generic;
using System.Web.Mvc;

using Dchien.Legal.BizModel.BAS.Type;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Service.BAS.Type;

namespace Dchien.Legal.Web.Areas.BAS.Controllers
{
    public class CauseController : Controller
    {
        #region 案由
 

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult Causes(string keyword)
        {
            var response = new PostResponse();

            try
            {
                var causes = CauseService.Instance.GetCauses();

                var list = new List<Tuple<string, string>>();
                causes.ForEach(x =>
                {
                    if (!string.IsNullOrEmpty(x.CauseName) && x.CauseName.Contains(keyword))
                    {
                        list.Add(new Tuple<string, string>(x.CauseId.ToString(), x.CauseName));
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
