using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Xml.Serialization;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.System;

namespace Dchien.Legal.Web.Areas.Contract.ViewModels.Patent
{
    public class ContractModel
    {
        /// <summary>
        /// 用户基本信息
        /// </summary>
        public BizUser User { get; set; }
        public int UserId { get; set; }
 
    }
 

}
