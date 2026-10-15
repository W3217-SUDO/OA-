using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas.FAM
{
    public class FAMAreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "FAM";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "FAM_default",
                "FAM/{controller}/{action}/{id}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.Web.Areas.FAM.Controllers" }
            );
        }
    }
}
