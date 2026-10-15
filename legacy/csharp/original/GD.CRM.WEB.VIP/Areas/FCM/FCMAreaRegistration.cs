using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas.FCM
{
    public class FCMAreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "FCM";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "FCM_default",
                "{id}/FCM/{controller}/{action}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.Web.Areas.FCM.Controllers" }
            );
        }
    }
}
