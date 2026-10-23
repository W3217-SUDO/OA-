using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Xml.Serialization;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.CMS.Contract;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.BizModel.System;

namespace Dchien.Legal.Web.Areas.CMS.ViewModels.Patent
{
    public class ContractModel
    {
        /// <summary>
        /// 客户 甲方
        /// </summary>
        public BizCustomer ACustomer { get; set; }

        /// <summary>
        /// 本公司 乙方
        /// </summary>
        public BizCompany BCustomer { get; set; }

        /// <summary>
        /// 合同
        /// </summary>
        public BizContract Contract { get; set; }


        /// <summary>
        /// 
        /// </summary>
        public BizContractScope ContractScope { get; set; }

        /// <summary>
        /// 合同条款的补充
        /// </summary>
        public string Remark { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public DateTime ContractDate { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string BusinessOwner { get; set; }

        public bool IsSubmit { get; set; }

    }
}
