using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;

namespace Dchien.Legal.Web.Areas.IPR.ViewModels.CaseFile
{
    /// <summary>
    /// 转官文
    /// </summary>
    public class TransmitCaseFileModel
    {
        /// <summary>
        /// 
        /// </summary>
        public List<long> CaseFileIds { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<long> CaseFeeIds { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<long> CaseIds { get; set; }


        /// <summary>
        /// 文档类型Id
        /// </summary>
        public int? CaseFileTypeId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string CaseFileTypeName { get; set; }

        public long CustomerId { get; set; }

    }
}