using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;

namespace Dchien.Legal.VipWeb.Models
{
    public abstract class BaseModel
    {

        public virtual int CaseId { get; set; }

        public int CaseTypeId { get; set; }

    }

    public abstract class BaseListModel
    {
        public BaseListModel()
        {
            this.PageNo = 1;
            this.PageSize = 15;
        }

        public int PageNo
        {
            get; set;

        }

        public int PageSize { get; set; }

        public int TotalCount { get; set; }


        public string PageId { get; set; }

    }
}