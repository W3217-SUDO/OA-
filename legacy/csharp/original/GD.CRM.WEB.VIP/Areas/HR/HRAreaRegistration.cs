using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas
{
    public class HRAreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "HR";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "HR_default",
                "{id}/HR/{controller}/{action}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.Web.Areas.HR.Controllers" }
            );
        }
    }
}
