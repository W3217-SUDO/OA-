using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.Web.Models;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.WMS.WareHouse;

namespace Dchien.Legal.Web.Areas.WMS.ViewModels.Warehouse
{
    public class WarehousetModel
    {
        public WarehousetModel()
        {
            
        }

        public List<BizModel.BAS.Warehouse.BizWarehouse> Warehouses { get; set; }

        public int Count { get; set; }

    }
}
