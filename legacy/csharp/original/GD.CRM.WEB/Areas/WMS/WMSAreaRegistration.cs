using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas.WMS
{
    public class WMSAreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "WMS";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "WMS_default",
                "{id}/WMS/{controller}/{action}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.Web.Areas.WMS.Controllers" }
            );
        }
    }
}
