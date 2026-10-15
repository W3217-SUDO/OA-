using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;


namespace Dchien.Legal.Web.Areas.IPR.ViewModels.Case
{
    public class CaseFeeModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public long CaseId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string CaseNo { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int CaseTypeId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<long> CaseFeeIds { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long CaseFeeId { get; set; }

        /// <summary>
        /// 上传文件Id
        /// </summary>
        public int? CaseFileTypeId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public DateTime? CaseRequestDate { get; set; }

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
        public int? Yearly { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseFeeType> CaseFeeTypeList { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizCaseFee CaseFee { get; set; }

        public BizCaseFeeItem DefaultCaseFee { get; set; }

	}

    /// <summary>
    /// 
    /// </summary>
    public class CaseFeeListBillConfirmModel
    {
        /// <summary>
        /// 
        /// </summary>
        public string CaseFeeItemIdList { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<long> CaseFeeItemIds { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public DateTime? BillDate { get; set; }


        public decimal? BillAmount { get; set; }

        public string BillNo { get; set; }
    }
}





