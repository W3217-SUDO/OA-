using System.Web.Mvc;

namespace Dchien.Legal.Web.Areas.FSC
{
    public class FSCAreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "FSC";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "FSC_default",
                "{id}/FSC/{controller}/{action}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.Web.Areas.FSC.Controllers" }
            );
        }
    }
}
