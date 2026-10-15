using System.Collections.Generic;

using Dchien.Legal.Entity.TP.Task;
using Dchien.Legal.BizModel.TP.Task;

namespace Dchien.Legal.Web.Areas.TP.ViewModels.Task
{
    public class TaskNodeModel
    {

        public TaskNodeModel()
        {
             
        }

        public string TaskIds { get; set; }
 

        public BizTaskNode TaskNode { get; set; }
       
	}
}
