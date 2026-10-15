using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas.BAS
{
    public class BASAreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "BAS";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "BAS_default",
                "{id}/BAS/{controller}/{action}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.Web.Areas.BAS.Controllers" }
            );
        }
    }
}
