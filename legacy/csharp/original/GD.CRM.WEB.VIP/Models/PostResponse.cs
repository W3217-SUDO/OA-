using System.Web.Mvc;
using System;
using System.Web;
using System.Web.Script.Serialization;
using System.Web.Configuration;
using System.Configuration;

namespace Dchien.Legal.VipWeb.Models
{
    public class PostResponse
    {
        public PostResponse()
        {
            this.IsSuccess = true;
        }

        public PostResponse(object data)
        {
            this.IsSuccess = true;
            this.Data = data;
        }

        public bool IsSuccess { get; set; }
        public object Data { get; set; }
        public string Message { get; set; }
    }
    public class ConfigurableJsonResult : System.Web.Mvc.JsonResult
     {
           public override void ExecuteResult(ControllerContext context)
          {
              if (context == null)
               {
                  throw new ArgumentNullException("context");
             }
              if (JsonRequestBehavior == JsonRequestBehavior.DenyGet &&
                 String.Equals(context.HttpContext.Request.HttpMethod, "GET", StringComparison.OrdinalIgnoreCase))
             {
                 throw new InvalidOperationException("This request has been blocked because sensitive information could be disclosed to third party web sites when this is used in a GET request. To allow GET requests, set JsonRequestBehavior to AllowGet.");
             }

            HttpResponseBase response = context.HttpContext.Response;
              if (!String.IsNullOrEmpty(ContentType))
             {
                 response.ContentType = ContentType;
             }
             else
             {
                 response.ContentType = "application/json";
            }
             if (ContentEncoding != null)
            {
                response.ContentEncoding = ContentEncoding;
            }
            if (Data != null)
             {
                 JavaScriptSerializer serializer = new JavaScriptSerializer();
 
                 ScriptingJsonSerializationSection section = ConfigurationManager.GetSection("system.web.extensions/scripting/webServices/jsonSerialization") as ScriptingJsonSerializationSection;           
               if (section != null)
                {
                     serializer.MaxJsonLength = section.MaxJsonLength;
                    serializer.RecursionLimit = section.RecursionLimit;
                }

                 response.Write(serializer.Serialize(Data));
             }
         }
     }
}