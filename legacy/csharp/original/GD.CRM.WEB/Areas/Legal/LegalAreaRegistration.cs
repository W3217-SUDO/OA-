using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas.Legal
{
    public class LegalAreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "Legal";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "Legal_default",
                "{id}/Legal/{controller}/{action}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.Web.Areas.Legal.Controllers" }
            );
        }
    }
}
