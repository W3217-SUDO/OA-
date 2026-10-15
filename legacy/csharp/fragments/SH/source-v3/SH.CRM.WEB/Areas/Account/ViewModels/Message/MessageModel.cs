using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Xml.Serialization;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Account.Message;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.Account.Message;
using Dchien.Legal.Entity.CRM.Customer;

namespace Dchien.Legal.Web.Areas.Account.ViewModels.Message
{
    public class MessageListModel
    {
        public List<BizMessage> Messages { get; set; }

        public MessageListModel()
        {
            this.SearchCondition = new MessageSearchCondition();
        }

        public MessageSearchCondition SearchCondition { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int? MessageTypeId { get; set; }

        public int? MessageStatusId { get; set; }

    }


    public class MessageModel
    {
        public BizMessage Message { get; set; }

    }
}
