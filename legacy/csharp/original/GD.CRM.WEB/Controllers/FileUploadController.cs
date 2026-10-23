using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using Dchien.Legal.BizModel.System;
using Dchien.Legal.Common;
using Dchien.Legal.Common.Utility;
using Dchien.Legal.Service;
using Dchien.Legal.Web.Captcha;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Controllers
{
    public class FileUploadController : Controller
    {
        internal Log Logger = new Log("IPR.Controllers.FileUploadController");

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [AllowAnonymous]
        [AcceptVerbs(HttpVerbs.Post), ValidateCaptcha()]
        [NoAuthorize]
        public ActionResult Upload()
        {
            var response = new PostResponse();

            for (int i = 0; i < Request.Files.Count; i++)
            {
                var file = Request.Files[i];
                int fileSize = file.ContentLength;
                var bytes = new byte[fileSize];
                using (var stream = file.InputStream)
                {
                    stream.Read(bytes, 0, fileSize);
                }

            }

            response.Message = "上传成功！";
            response.IsSuccess = true;

            return Json(response);

        }
    }
}