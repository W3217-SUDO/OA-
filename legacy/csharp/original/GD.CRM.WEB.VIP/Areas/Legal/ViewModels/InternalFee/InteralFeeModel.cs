using System.Collections.Generic;

namespace Dchien.Legal.Web.Areas.Legal.ViewModels.Case.InternalFee
{
    public class InteralFeeModel
    {
        public BizModel.FAM.InternalFee.BizInternalFee InternalFee { get; set; }
    }

    /// <summary>
    /// 
    /// </summary>
    public class InteralFeeListModel
    {
        public List<BizModel.FAM.InternalFee.BizInternalFee> InternalFees { get; set; }
    }
}
