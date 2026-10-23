using System;
using System.Collections.Generic;
using Dchien.Legal.BizModel.HR;

using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.HR.ViewModels.Staff
{
    public class PerformanceModel
    {
        /// <summary>
        /// 
        /// </summary>
        public BizStaffPerformance Performance { get; set; }

        /// </summary>
        public string StaffName { get; set; }


        public int? SettingId { get; set; }
    }
}

