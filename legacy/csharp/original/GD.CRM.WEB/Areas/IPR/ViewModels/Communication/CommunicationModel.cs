using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Xml.Serialization;
using SunHold.Legal.BizModel;
using SunHold.Legal.BizModel.IPR.Communication;
using SunHold.Legal.Entity;
using SunHold.Legal.Entity.IPR.Communication;
using SunHold.Legal.Entity.IPR.Customer;

namespace SunHold.Legal.Web.Areas.IPR.ViewModels.Communication
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
