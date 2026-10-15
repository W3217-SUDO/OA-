using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Xml.Serialization;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Account.Communication;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.Account.Communication;
using Dchien.Legal.Entity.CRM.Customer;

namespace Dchien.Legal.Web.Areas.Account.ViewModels.Communication
{
    public class CommunicationListModel
    {
        public List<BizCommunication> Communications { get; set; }

        public CommunicationListModel()
        {
            this.SearchCondition = new CommunicationSearchCondition();
        }

        public CommunicationSearchCondition SearchCondition { get; set; }
    }


    public class CommunicationModel
    {
        public BizCommunication Communication { get; set; }

        public List<BizCommunication> CommunicationLogs { get; set; }

    }
}
