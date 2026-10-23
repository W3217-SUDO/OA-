using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas
{
    public class ConsoleAreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "Console";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "Index",
                "Console/{controller}/{action}/{id}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.Web.Areas.Console.Controllers" }
            );
        }
    }
}
