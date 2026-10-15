using System;
using System.Collections.Generic;
using Dchien.Legal.BizModel.HR;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Entity.HR.Staff;

namespace Dchien.Legal.Web.Areas.HR.ViewModels.Staff
{
    public class PerformanceListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizStaffPerformance> PerformanceList { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long StaffId { get; set; }


        public bool? IsView { get; set; }


        public PerformanceListModel()
        {
            this.SearchCondition = new PerformanceSearchCondition();
        }

        public PerformanceSearchCondition SearchCondition { get; set; }

	}
}

