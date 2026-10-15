using System;
using System.Web.Mvc;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.Service;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service.IPR.CPC;

namespace Dchien.Legal.Web.Areas.IPR.Controllers
{
    [CheckUserLogin]
    public class CPCController : BaseController
    {
        internal Log Logger = new Log("IPR.Controllers.CpcController");
 
        #region 生成CPC文件包

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult GeneratePatentApplication(long caseId)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            try
            {
                var c = CaseService.Instance.GetCase(caseId);
                var cpc = CPCServiceFactory.Create(c);

                var sb = cpc.PreCheck();

                if (!string.IsNullOrEmpty(sb.ToString()))
                {
                    response.IsSuccess = false;
                    response.Message = sb.ToString();
                    return Json(response);
                }

                var result = cpc.Generate();

                if (!result)
                {
                    response.IsSuccess = false;
                    response.Message = "生成申请书出错.";
                    return Json(response);
                }

                response.IsSuccess = true;
                response.Message = "生成申请书成功.";
                response.Data = cpc.ZipFile;
                return Json(response);
            }
            catch (NotImplementedException ex)
            {
                response.Data = string.Empty;
                response.IsSuccess = false;
                response.Message = ex.Message;
                return Json(response);
            }
            catch (ApplicationException ex)
            {
                response.Data = string.Empty;
                response.IsSuccess = false;
                response.Message = ex.Message;
                return Json(response);
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CpcController.GeneratePatentApplication", "CpcController.GeneratePatentApplication", ex);
                throw;
            }
        }


        #endregion

    }
}
