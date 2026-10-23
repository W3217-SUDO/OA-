using System;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AR
{
    public class ARObjecCaseFeeModel
    {
        /// <summary>
        /// 
        /// </summary>
        public long CaseId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int CaseFeeTypeId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public decimal Amount { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public DateTime? CaseRequestDate { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int? AnnualYear { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public DateTime? AnnualFrom { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public DateTime? AnnualEnd { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public bool IsFirstYear { get; set; }
    }
}

