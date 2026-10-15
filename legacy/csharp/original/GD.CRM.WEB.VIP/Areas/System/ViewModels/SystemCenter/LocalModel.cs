using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.System;
using Dchien.Legal.Entity;

namespace Dchien.Legal.Web.Areas.System.ViewModels.SystemCenter
{
    public class LocalModel 
	{
        /// <summary>
        /// Id, Name, Value
        /// </summary>
        public List<Tuple<int,string,string>> LocalSettings { get; set; }

        public List<BizLocalSetting> LocalSettingList { get; set; }

	}

 
}





