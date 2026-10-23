using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas.TP
{
    public class TPAreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "TP";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "TP_default",
                "{id}/TP/{controller}/{action}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.Web.Areas.TP.Controllers" }
            );
        }
    }
}
