using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas.CRM
{
    public class CRMAreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "CRM";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "CRM_default",
                "{id}/CRM/{controller}/{action}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.Web.Areas.CRM.Controllers" }
            );
        }
    }
}
