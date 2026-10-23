using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.BAS.Type;

namespace Dchien.Legal.Web.Areas.Legal.ViewModels.CaseFile
{
    public class MultiCaseFileUploadModel
    {
        /// <summary>
        /// 
        /// </summary>
        public string CaseNos { get; set; }


        public string Relativepath { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long? FileTypeId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string FileTypeName { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public DateTime? UploadingTime { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long? CaseFileTypeId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long? CaseFileTypeName { get; set; }


        public int? TypeId { get; set; }

    }

    public class CaseFileUploadModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseFileType> CaseFileTypeList { get; set; }

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
        /// 默认客户Id
        /// </summary>
        public long? CustomerId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long? CaseFileTypeId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string CaseFileTypeName { get; set; }

        /// <summary>
        /// 对冲文件类型
        /// </summary>
        public int? HedgingFileTypeId { get; set; }

        public List<long?> HedgingFileId { get; set; }

        public List<long?> HedgingFeeId { get; set; }

        public DateTime? UploadingTime { get; set; }

        /// <summary>
        /// 申请号
        /// </summary>
        public string CaseRequestNo { get; set; }

        /// <summary>
        /// 是否导出转文文档
        /// </summary>
        public bool IsTransformedFile { get; set; }


        public string Name { get; set; }

        public string Relativepath { get; set; }

    }

 


    /// <summary>
    /// 
    /// </summary>
    [Serializable]
    public class CaseFeeInvoiceCustomizedFileUploadModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<Dchien.Legal.BizModel.FAM.Invoice.BizInvoice> Invoices { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string PrimaryFileName { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public decimal? TotalAmount { get; set; }

    }


}





