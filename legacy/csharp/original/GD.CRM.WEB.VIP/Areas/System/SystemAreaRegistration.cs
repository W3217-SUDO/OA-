using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas.IPR
{
    public class SystemAreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "System";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "System_default",
                "{id}/System/{controller}/{action}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.Web.Areas.System.Controllers" }
            );
        }
    }
}
