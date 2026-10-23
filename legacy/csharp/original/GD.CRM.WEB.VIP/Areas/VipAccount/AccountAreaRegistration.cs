using System.Web.Mvc;

namespace Dchien.Legal.VipWeb.Areas.Account
{
    public class AccountAreaRegistration : AreaRegistration
    {
        public override string AreaName
        {
            get
            {
                return "Account";
            }
        }

        public override void RegisterArea(AreaRegistrationContext context)
        {
            context.MapRoute(
                "Account_default",
                "{id}/Account/{controller}/{action}",
                new { action = "Index", id = UrlParameter.Optional },
                new string[] { "Dchien.Legal.VipWeb.Areas.Account.Controllers" }
            );
        }
    }
}
