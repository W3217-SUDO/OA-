using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;


namespace Dchien.Legal.Web
{
    public class MyActionFilter : FilterAttribute, IActionFilter
    {

        public void OnActionExecuted(ActionExecutedContext filterContext)
        {
            //filterContext.RequestContext
            //throw new NotImplementedException();
        }

        public void OnActionExecuting(ActionExecutingContext filterContext)
        {
           // throw new NotImplementedException();
        }
    }

    public class MyRenderFilter : ActionFilterAttribute
    {
        public override void OnResultExecuting(ResultExecutingContext filterContext)
        {
           
            base.OnResultExecuting(filterContext);
        }
    }
}