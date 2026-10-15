using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas.FI
{
    public class FITPreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "FIO";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "FIO_default",
                "{id}/FIO/{controller}/{action}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.Web.Areas.FIO.Controllers" }
            );
        }
    }
}
