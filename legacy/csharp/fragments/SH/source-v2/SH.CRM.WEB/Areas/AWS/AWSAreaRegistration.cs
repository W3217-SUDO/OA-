using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas.AWS
{
    public class AWSAreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "AWS";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "AWS_default",
                "{id}/AWS/{controller}/{action}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.Web.Areas.AWS.Controllers" }
            );
        }
    }
}
