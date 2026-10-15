using System;
using System.Collections.Generic;
using Dchien.Legal.Web.Models;
using Dchien.Legal.BizModel.HR.Staff;

namespace Dchien.Legal.Web.Areas.HR.ViewModels.Staff
{
    public class StaffFileListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizStaffFile> StaffFiles { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long? StaffId { get; set; }


	}
}

