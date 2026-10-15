using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas.RPT
{
    public class RPTAreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "RPT";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "RPT_default",
                "{id}/RPT/{controller}/{action}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.Web.Areas.RPT.Controllers" }
            );
        }
    }
}
