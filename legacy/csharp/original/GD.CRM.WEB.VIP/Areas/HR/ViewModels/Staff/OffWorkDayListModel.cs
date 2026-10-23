using System;
using System.Collections.Generic;
using Dchien.Legal.BizModel.HR;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Entity.HR.Staff;

namespace Dchien.Legal.Web.Areas.HR.ViewModels.Staff
{
    public class OffWorkDayListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizOffWorkDay> OffWorkDayList { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long StaffId { get; set; }


        public bool? IsView { get; set; }


        public OffWorkDayListModel()
        {
            this.SearchCondition = new OffWorkDaySearchCondition();
        }

        public OffWorkDaySearchCondition SearchCondition { get; set; }

	}
}

