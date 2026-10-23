using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;

namespace Dchien.Legal.VipWeb.Models
{
    public class Employee
    {
        public string Eid { get; set; }
        public string Name { get; set; }
        public int Accesslevel { get; set; }
        public int Internalaccess { get; set; }

        public Employee()
        {
            Eid = "System";
            Name = "System";
            Accesslevel = 0;
            Internalaccess = 0;
        }
    }
}