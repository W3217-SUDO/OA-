using System;
using System.Collections.Generic;
using Dchien.Legal.Web.Models;

using Dchien.Legal.BizModel.AWS.OfficialDocument;

namespace Dchien.Legal.Web.Areas.AWS.ViewModels.OfficialDocumentFile
{
    public class FileListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizOfficialDocumentFile> Files { get; set; }

	}
}

