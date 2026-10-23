using System;

using Dchien.Legal.Web.Models;
using Dchien.Legal.Entity.Legal.Case;

namespace Dchien.Legal.Web.Areas.FIO.ViewModels
{
    /// <summary>
    /// 
    /// </summary>
    public class LegalOfficialFileModel
    {
        public CaseFileSearchCondition SearchCondition { get; set; }

    }

    /// <summary>
    /// 
    /// </summary>
    public class  MetaFileModel
    {
        public MetaFileSearchCondition SearchCondition { get; set; }

    }

}
