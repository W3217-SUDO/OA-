using System.Collections;
using System.Collections.Generic;

 
using Dchien.Legal.BizModel.AWS.OfficialDocument;
 

namespace Dchien.Legal.Web.Areas.AWS.ViewModels.OfficialDocument
{
    public class OfficialDocumentModel
    {
        /// 
        /// </summary>
        public BizOfficialDocument OfficialDocument { get; set; }
    }


    public class OfficialDocumentCreateModel
    {
        /// <summary>
        /// 
        /// </summary>
        public BizOfficialDocumentBasic OfficialDocument { get; set; }

    }
}
