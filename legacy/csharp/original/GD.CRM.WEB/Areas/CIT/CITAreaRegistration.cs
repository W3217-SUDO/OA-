using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas.CIT
{
    public class CITAreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "CIT";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "CIT_default",
                "{id}/CIT/{controller}/{action}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.Web.Areas.CIT.Controllers" }
            );
        }
    }
}
