using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Web;
using System.Web.Http;
using System.Web.Mvc;
using System.Web.Optimization;
using System.Web.Routing;
using FluentValidation;
using FluentValidation.Attributes;
using FluentValidation.Mvc;
using Dchien.Legal.Infrastructure;

using System.Configuration;

namespace Dchien.Legal.Web
{
    // Note: For instructions on enabling IIS6 or IIS7 classic mode, 
    // visit http://go.microsoft.com/?LinkId=9394801

    public class MvcApplication : System.Web.HttpApplication
    {

        protected void Application_Start()
        {
            AreaRegistration.RegisterAllAreas();

            WebApiConfig.Register(GlobalConfiguration.Configuration);
            FilterConfig.RegisterGlobalFilters(GlobalFilters.Filters);
            
            RouteConfig.RegisterRoutes(RouteTable.Routes);
            BundleConfig.RegisterBundles(BundleTable.Bundles);
            AuthConfig.RegisterAuth();

            // Register Validators;
            //AutoRegisterHelper.RegisterFluentObjectValidators(Dchien.Legal.Infrastructure.Container.Current, typeof(ControlFlightTicketInfoValidator).Assembly);
            FluentValidation.ValidatorOptions.ResourceProviderType = typeof(MyResources);

            FluentValidationModelValidatorProvider.Configure(e => e.ValidatorFactory = new ContainerValidatorFactory());
            
            // Mapping Register
            //MappingRegister.Regist();
        }

    }

    public class ContainerValidatorFactory : IValidatorFactory
    {


        public IValidator GetValidator(Type type)
        {
            Type validatorType = typeof (IValidator<>);
            Type genericType = validatorType.MakeGenericType(type);
            IValidator validator = Dchien.Legal.Infrastructure.Container.Current.TryResolve(genericType) as IValidator;
            return validator;
        }

        public IValidator<T> GetValidator<T>()
        {
            return Dchien.Legal.Infrastructure.Container.Current.TryResolve<IValidator<T>>();
            
        }
    }



}