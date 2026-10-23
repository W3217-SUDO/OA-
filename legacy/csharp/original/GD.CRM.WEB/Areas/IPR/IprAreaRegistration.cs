using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas.IPR
{
    public class IPRAreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "IPR";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "IPR_default",
                "{id}/IPR/{controller}/{action}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.Web.Areas.IPR.Controllers" }
            );
        }
    }
}
