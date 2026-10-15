using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Xml.Serialization;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.System;
using Dchien.Legal.BizModel.HR;

namespace Dchien.Legal.Web.Areas.Console.ViewModels.Index
{
    /// <summary>
    /// 首页数据
    /// </summary>
    public class DashboardModel
    {
        /// <summary>
        ///  
        /// </summary>
        public int CaseType_110_Counts { get; set; }

        /// <summary>
        ///  
        /// </summary>
        public int CaseType_120_Counts { get; set; }

        /// <summary>
        ///  
        /// </summary>
        public int CaseType_130_Counts { get; set; }

        /// <summary>
        ///  
        /// </summary>
        public int CaseType_140_Counts { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int CaseType_150_Counts { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int CaseType_160_Counts { get; set; }

        /// <summary>
        ///  
        /// </summary>
        public int CaseOtherCounts { get; set; }

        /// <summary>
        /// 案件趋势
        /// </summary>
        public List<Tuple<DateTime, int>> To10DayCaseCounts { get; set; }


    }
}
