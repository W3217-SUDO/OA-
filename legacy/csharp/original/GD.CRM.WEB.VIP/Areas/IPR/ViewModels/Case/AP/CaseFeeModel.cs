using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.IPR.ViewModels.Case.AP
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
        public bool FirstYear { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseFeeType> CaseFeeTypeList { get; set; }
 
        public BizModel.FAM.AP.CaseFee.BizCaseFee DefaultCaseFee { get; set; }
        
        public List<BizModel.FAM.AP.CaseFee.BizCaseFee> CaseFeeList { get; set; }

    }

    /// <summary>
    /// 应付账款
    /// </summary>
    public class CaseFeeListModel : BaseListModel
    {

        /// <summary>
        /// 应收账款
        /// </summary>

        public List<Dchien.Legal.BizModel.FAM.AP.CaseFee.BizCaseFee> CaseFeeList { get; set; }


        /// <summary>
        /// 
        /// </summary>
        public long CaseId { get; set; }


    }

    /// <summary>
    /// 垫付款申请
    /// </summary>
    public class PaymentApplyModel
    {

        /// <summary>
        /// 
        /// </summary>
        public List<long> CaseFeeIds { get; set; }

        public string Remark { get; set; }
    }

}
