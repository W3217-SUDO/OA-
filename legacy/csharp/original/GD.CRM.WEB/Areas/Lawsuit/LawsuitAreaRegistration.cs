using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas.IPR
{
    public class LawsuitAreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "Lawsuit";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "Lawsuit_default",
                "{id}/Lawsuit/{controller}/{action}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.Web.Areas.Lawsuit.Controllers" }
            );
        }
    }
}
