using System;
using System.Collections.Generic;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.FCM.ViewModels.Contract
{
    public class ContractObjectListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizContractObject> ContractObjects { get; set; }

        /// <summary>
        /// 回款记录
        /// </summary>
        public List<Dchien.Legal.BizModel.FAM.AR.ReceivedPayment.BizPayment> ReceivedObjects { get; set; }

        public List<Dchien.Legal.BizModel.FAM.AR.Payment.BizPayment> JReceivedObjects { get; set; }


        /// <summary>
        /// 开票记录
        /// </summary>
        public List<Dchien.Legal.BizModel.FAM.Invoice.BizInvoice> InvoicedObjects { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<Dchien.Legal.BizModel.FAM.AP.Payment.BizPayment> PaidObjects { get; set; }


        /// <summary>
        /// 
        /// </summary>
        public long ContractId { get; set; }


	}
}

