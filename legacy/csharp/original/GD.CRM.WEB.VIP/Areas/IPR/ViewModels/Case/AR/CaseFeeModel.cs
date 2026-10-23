using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;


namespace Dchien.Legal.Web.Areas.IPR.ViewModels.Case.AR
{
    public class CaseFeeModel
    { 
        /// <summary>
        /// 
        /// </summary>
        public Dchien.Legal.BizModel.FCM.Contract.BizContractObject ContractObject { get; set; }

    }

    public class CaseFeeObjectModel
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
        public bool FirstYear { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseFeeType> CaseFeeTypeList { get; set; }

        public BizModel.FAM.AR.CaseFee.BizCaseFee DefaultCaseFee { get; set; }

        public List<BizModel.FAM.AR.CaseFee.BizCaseFee> CaseFeeList { get; set; }

    }

    /// <summary>
    /// 
    /// </summary>
    public class CaseFeeListInvoiceConfirmModel
    {
        /// <summary>
        /// 
        /// </summary>
        public string CaseFeeIdList { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<long> CaseFeeIds { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public DateTime? InvoiceDate { get; set; }


        public decimal? InvoiceAmount { get; set; }

        public string InvoiceNo { get; set; }
    }

}





