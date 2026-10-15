using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas.AFM
{
    public class IPRAreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "AFM";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "AFM_default",
                "{id}/AFM/{controller}/{action}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.Web.Areas.AFM.Controllers" }
            );
        }
    }
}
