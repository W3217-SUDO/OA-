using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Web.Mvc;


using Dchien.Legal.BizModel.Lawsuit.Cause;
using Dchien.Legal.Common;
using Dchien.Legal.Service.Lawsuit.Cause;
using Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.Lawsuit.Controllers
{
    [CheckUserLogin]
    public class CaseCauseController : BaseController
    {
        internal Log Logger = new Log("Lawsuit.Controllers.CaseCauseController");

        #region 案由

        /// <summary>
        /// 打开案件日志
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseCause(CaseCauseModel model)
        {
            return PartialView("CaseCause", model);
        }

       [CheckUserLogin]
       [HttpPost]
        public JsonResult GetCaseCauses(long? caseId)
        {
            var response = new PostResponse();
            var causes = CauseService.Instance.GetCauses();
            var caseCauses = new List<int>();

                var nodes = new List<Node>();

                //第一级菜单 大菜单
                causes.FindAll(x => x.ParentCauseId == -1).ForEach(x =>
                {
                    var node = new Node()
                    {
                        nodeType = "M",
                        nodeOriginalId = x.CauseId,
                        nodeCode = x.CauseId.ToString(),
                        nodeId = x.CauseId,
                        text = x.CauseName,
                        state = caseCauses.Any(p => p == x.CauseId ) ? new State() { Checked = true } : new State(),
                        nodes = new List<Node>()
                    };

                    //第二级 分类菜单
                    causes.FindAll(t => t.ParentCauseId == x.CauseId).ForEach(m =>
                    {
                        var node2 = new Node()
                        {
                            nodeType = "M",
                            nodeOriginalId = m.CauseId,
                            nodeId = m.CauseId,
                            nodeCode = m.CauseId.ToString(),
                            text = m.CauseName,
                            state = caseCauses.Any(p => p == x.CauseId) ? new State() { Checked = true } : new State(),
                            nodes = (causes.FindAll(n => n.ParentCauseId == m.CauseId).Count > 0) ? new List<Node>() : null
                        };

                        //第三级
                        causes.FindAll(n => n.ParentCauseId == m.CauseId).ForEach(n =>
                        {
                            var node3 = new Node()
                            {
                                nodeType = "M",
                                nodeOriginalId = n.CauseId,
                                nodeId = n.CauseId,
                                nodeCode = n.CauseId.ToString(),
                                text = n.CauseName,
                                state = caseCauses.Any(p => p == n.CauseId) ? new State() { Checked = true } : new State(),
                                nodes = (causes.FindAll(f => f.ParentCauseId == n.CauseId).Count > 0) ? new List<Node>() : null
                            };


                            //第四级
                            causes.FindAll(f => f.ParentCauseId == n.CauseId).ForEach(f =>
                            {
                                var node4 = new Node()
                                {
                                    nodeType = "M",
                                    nodeOriginalId = f.CauseId,
                                    nodeId = f.CauseId,
                                    nodeCode = f.CauseId.ToString(),
                                    text = f.CauseName,
                                    state = caseCauses.Any(p => p == f.CauseId) ? new State() { Checked = true } : new State(),
                                    nodes = null
                                };

                                node3.nodes.Add(node4);
                            });

                            node2.nodes.Add(node3);
                        });

                        node.nodes.Add(node2);
                    });

                    nodes.Add(node);
                });

                response.Data = nodes;
                response.IsSuccess = true;
                return Json(response);
            
        }

        #endregion

    }
}
