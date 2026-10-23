using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace Dchien.Legal.Web.Models
{
    public class UserModel
    {
        public long UserId { get; set; }
     
        public string UserCode { get; set; }
     
        public string UserName { get; set; }

        public int UserStatus { get; set; }
      
        public string Password { get; set; }

       
        public int UserType { get; set; }

     
        public string IsDelete { get; set; }

     
        public string IpAddress { get; set; }

        /// <summary>
        /// 返回状态
        /// </summary>
        public int ReturnCode { get; set; }
    }

}
