using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;

namespace Dchien.Legal.Web
{
    [AttributeUsage(AttributeTargets.Class | AttributeTargets.Method)]
    public class NoAuthorizeAttribute : Attribute
    {
        public NoAuthorizeAttribute()
        {
        }
    }
}