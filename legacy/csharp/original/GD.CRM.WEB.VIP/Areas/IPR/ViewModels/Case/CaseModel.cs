using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Security.Permissions;
using System.Web;
using System.Web.Mvc;
using System.Xml.Serialization;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.IPR.Case;


namespace Dchien.Legal.Web.Areas.IPR.ViewModels.Case
{
    public class CaseModel : ListModel
	{
        /// <summary>
        /// 
        /// </summary>
	    public BizCase Case { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long CaseId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<int> CustomerIds { get; set; }


        public int? CurrentSelectedListTypeId { get; set; }

	}

    /// <summary>
    /// 重提案件
    /// </summary>
    public class RebootingCaseModle
    {
        /// <summary>
        /// 原案件信息
        /// </summary>
        public BizCase OriginalCase { get; set; }


        /// <summary>
        /// 新生成案件
        /// </summary>
        public BizCase TargetCase { get; set; }

    }


    /// <summary>
    /// 批量新建案件
    /// </summary>
    public class MultiCreateModel 
    {
        /// <summary>
        /// 
        /// </summary>
        public List<BizCase> Cases { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int? CustomerId { get; set; }

        [Display(Name = "客户编号")]
        [XmlAttribute]
        public string CustomerNo { get; set; }

        [Display(Name = "客户名称")]
        [XmlAttribute]
        public string CustomerName { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long? ContractId { get; set; }

        [Display(Name = "合同编号")]
        [XmlAttribute]
        public string ContractNo { get; set; }

    }

    /// <summary>
    /// 
    /// </summary>
    public class CaseListModel
    {
        public BizCaseSearchCondition Search { get; set; }

        public CaseSearchCondition SearchCondition { get; set; }

        public CaseListModel()
        {
            this.SearchCondition = new CaseSearchCondition();
        }

        /// <summary>
        /// 
        /// </summary>
        public List<BizCase> CaseList { get; set; }

    }

    /// <summary>
    /// 
    /// </summary>
    public class CaseListToWordModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<long> CaseIds { get; set; }

        /// <summary>
        /// 文档类型Id
        /// </summary>
        public int? CaseFileTypeId { get; set; }

        public long CustomerId { get; set; }


    }

    /// <summary>
    /// 
    /// </summary>
    public class CaseBatchEditModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<long> CaseIds { get; set; }

        /// <summary>
        /// 文档类型Id
        /// </summary>
        public int? CasePhaseId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string CaseNo { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string CaseOfficer { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string CaseOfficerName { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public DateTime? Deadline { get; set; }

    }

    public class CaseAnnualYearEditModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<long> CaseIds { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int? FirstAnnualYear { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public decimal? CostSlowRate { get; set; }

    }

    /// <summary>
    /// 提成比例设定
    /// </summary>
    public class CaseRateModel
    {
        public long CaseId { get; set; }

        //public string CaseOriginPeople { get; set; }   

        public decimal? LeadRate { get; set; }

        public decimal? CopyRate { get; set; }

    }

    /// <summary>
    /// 批量上传文件
    /// </summary>
    public class CaseFileBatchImportModel
    {
        /// <summary>
        /// 
        /// </summary>
        public int? CaseFileTypeId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string CaseFileTypeName { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<long> CaseIds { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public DateTime? UploadingTime { get; set; }

    }

    public class QuickCreateModel
    {
        /// <summary>
        /// 
        /// </summary>
        public long CustomerId { get; set; }

        public BizCase CaseInfo { get; set; }

    }

    public class QuickCopyModel
    {
        /// <summary>
        /// 
        /// </summary>
        public long CustomerId { get; set; }

        public string Message { get; set; }

        public BizCase OrgCaseInfo { get; set; }

    }
}





