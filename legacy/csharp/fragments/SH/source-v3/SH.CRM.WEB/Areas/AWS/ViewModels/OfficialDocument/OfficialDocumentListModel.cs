using Dchien.Legal.Web.Models;
using Dchien.Legal.Entity.AWS.OfficialDocument;

namespace Dchien.Legal.Web.Areas.AWS.ViewModels.OfficialDocument
{
    public class OfficialDocumentListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
	    public OfficialDocumentSearchCondition SearchCondition { get; set; }


        /// <summary>
        /// 
        /// </summary>
        public OfficialDocumentListModel()
        {
            this.SearchCondition = new OfficialDocumentSearchCondition();
            this.SearchCondition.PageNo = 1;
            this.SearchCondition.PageSize = 15;
        }
    }
}
