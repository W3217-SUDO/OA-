using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Lawsuit.Case;


namespace Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case
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
        public long CaseFeeId { get; set; }

        /// <summary>
        /// 上传文件Id
        /// </summary>
        public int? CaseFileTypeId { get; set; }

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
}





