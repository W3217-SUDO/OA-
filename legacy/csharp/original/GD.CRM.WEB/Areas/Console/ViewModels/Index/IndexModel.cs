using System;
using System.Collections.Generic;

using Dchien.Legal.BizModel.TP.Task;
using Dchien.Legal.BizModel.Legal.Case;
 
namespace Dchien.Legal.Web.Areas.Console.ViewModels.Index
{
    public class IndexModel
    {
        /// <summary>
        /// 10 个待办任务
        /// </summary>
        public List<BizTask> Top10Tasks { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizCase> Top10Cases { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizCase> New10Cases { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseFile> Top10CaseOfficeFiles { get; set; }


        /// <summary>
        /// 
        /// </summary>

        public int CaseOfficeFee1_Counts { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int CaseOfficeFee2_Counts { get; set; }


        public int CaseOfficeFee3_Counts { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int CaseOfficeFee4_Counts { get; set; }



        public int CaseOfficeFee5_Counts { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int CaseOfficeFee6_Counts { get; set; }

        public int CaseOfficeFee7_Counts { get; set; }

 
        public decimal TotalUnCashedAdvancedCaseOfficeFeeAmount { get; set; }


        public decimal TotalUnCashedCaseOfficeFeeAmount { get; set; }

        public decimal TotalUnCashedCaseNonOfficeFeeAmount { get; set; }


    }
}
