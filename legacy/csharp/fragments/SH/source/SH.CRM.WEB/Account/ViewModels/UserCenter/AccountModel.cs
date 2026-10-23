using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Xml.Serialization;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.System;
using Dchien.Legal.BizModel.HR;

namespace Dchien.Legal.Web.Areas.Account.ViewModels.UserCenter
{
    public class AccountModel
    {
        /// <summary>
        /// 用户基本信息
        /// </summary>
        public BizStaff Staff { get; set; }
        public int UserId { get; set; }
 
    }

    /// <summary>
    /// 
    /// </summary>
    public class PasswordModel
    {
        public int UserId { get; set; }

        [Display(Name = "原密码：")]
        [XmlAttribute]
        public string Password { get; set; }

        [Display(Name = "新密码：")]
        [XmlAttribute]
        public string NewPassword { get; set; }

        [Display(Name = "新密码确认：")]
        [XmlAttribute]
        public string NewPasswordConfirm { get; set; }
    }

    /// <summary>
    /// 
    /// </summary>
    public class SettingModel
    {
        public int UserId { get; set; }

        [Display(Name = "左侧菜单自动收缩：")]
        [XmlAttribute]
        public bool MenuFold { get; set; }
 
    }

}
