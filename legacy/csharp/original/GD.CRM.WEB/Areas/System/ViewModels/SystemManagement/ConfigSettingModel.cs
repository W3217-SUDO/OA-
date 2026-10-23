using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using System.Web.UI.WebControls.Expressions;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.System;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.System.ViewModels.SystemManagement
{
    public class ConfigSettingModel
    {
        /// <summary>
        /// 
        /// </summary>
        public BizConfigAppSetting Menu { get; set; }

    }

    /// <summary>
    /// 
    /// </summary>
    public class ConfigSettingListModel : BaseListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizConfigAppSetting> AppSettings { get; set; }
 

        public ConfigSettingListModel()
        {
           

        }
    }
}





