using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection.Emit;
using System.Web;
using System.Web.Mvc;

using log4net.Repository.Hierarchy;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.System;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Areas.HR.ViewModels;
using Dchien.Legal.Service;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.HR.Controllers
{
    public class RoleController : Controller
    {
        internal Log Logger = new Log("HR.Controllers.RoleController");

        #region 角色管理

        /// <summary>
        /// 
        /// </summary>
        /// <param name="roleId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult Role(int? roleId)
        {
            var model = new RoleModel();

            if (roleId.HasValue && roleId.Value > -1)
            {
                model.Role = RoleService.Instance.GetRole(roleId.Value);
                model.RoleId = roleId.Value;
            }

            return PartialView(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
            /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult RoleCreateUpdate(RoleModel model)
        {
            var response = new PostResponse();

            bool result = RoleService.Instance.RoleCreateUpdate(model.Role);

            if (result)
            {
                response.Message = "保存成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "保存失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

         [CheckUserLogin]
        public ActionResult RoleList()
        {
            var model = new RoleListModel();

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult RoleList(RoleListModel model)
        {
            var response = new PostResponse();

    
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizRoleSearchResultInfo();

                result.RoleList = RoleService.Instance.GetRoleList(model.SearchCondition);

                result.TotalItemCount = result.RoleList.Count;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;

                response.IsSuccess = true;
                response.Data = result;
 
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="roleId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult RolePermissions(int? roleId)
        {
            var model = new RoleModel();

            if (roleId.HasValue && roleId.Value > -1)
            {
                model.Role = RoleService.Instance.GetRole(roleId.Value);
                //model.Permissions = RoleService.Instance.GetRolePermissions(roleId.Value);
                //model.Menus = MenuService.Instance.GetAll();
                model.RoleId = roleId.Value;
            }

            return PartialView(model);
        }

        /// <summary>
        /// 返回Json格式数据
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult GetRolePermissions(int? roleId)
        {
            var response = new PostResponse();

            if (roleId.HasValue && roleId.Value > -1)
            {
                var permissions = RoleService.Instance.GetRolePermissionsByRoleId(roleId.Value);
                var menus = MenuService.Instance.GetAll();
                var actions = ActionService.Instance.GetAll();
                var menuActions = MenuService.Instance.GetMenuActionList();

                var nodes = new List<Node>();

                //第一级菜单 大菜单
                menus.FindAll(x => x.ParentMenuId == -1).ForEach(x =>
                {
                    var node = new Node()
                    {
                        nodeType = "M",
                        nodeOriginalId = x.MenuId,
                        nodeCode = x.MenuCode,
                        nodeId = x.MenuId,
                        text = x.MenuName,
                        state = permissions.Any(p=>p.ResourceId == x.MenuId && p.ResourceType == "M") ? new State() { Checked = true } : new State(),
                        nodes = new List<Node>()
                    };

                    //第二级 分类菜单
                    menus.FindAll(t => t.ParentMenuId.ToString() == x.MenuCode).ForEach(m =>
                    {
                        var node2 = new Node()
                        {
                            nodeType = "M",
                            nodeOriginalId = m.MenuId,
                            nodeId = m.MenuId,
                            nodeCode = m.MenuCode,
                            text = m.MenuName,
                            state = permissions.Any(p => p.ResourceId == m.MenuId && p.ResourceType == "M") ? new State() { Checked = true } : new State(),
                            nodes = (menus.FindAll(n =>  n.ParentMenuId.HasValue && n.ParentMenuId.ToString() == m.MenuCode).Count > 0 || menuActions.Any(a => a.Key == m.MenuId)) ? new List<Node>() : null
                        };

                        if(menuActions.Any(k=>k.Key == m.MenuId))
                        {
                            menuActions[m.MenuId].ForEach(actionId =>
                            {
                                if (actions.Any(action => action.ActionId == actionId))
                                {
                                    var nodeAction = new Node()
                                    {
                                        nodeType = "A",
                                        nodeOriginalId = actionId,
                                        nodeId = actionId,
                                        nodeCode = actions.FirstOrDefault(action => action.ActionId == actionId).ActionCode,
                                        text = actions.FirstOrDefault(action => action.ActionId == actionId).ActionNameCN,
                                        state = permissions.Any(p => p.ResourceId == actionId && p.ResourceType == "A") ? new State() { Checked = true } : new State(),
                                        nodes =  null
                                    };

                                    node2.nodes.Add(nodeAction);
                                }
                            });
                        }

                        try
                        {                         //第三级
                            menus.FindAll(n => n.ParentMenuId.HasValue && n.ParentMenuId.ToString() == m.MenuCode).ForEach(n =>
                            {
                                var node3 = new Node()
                                {
                                    nodeType = "M",
                                    nodeOriginalId = n.MenuId,
                                    nodeId = n.MenuId,
                                    nodeCode = n.MenuCode,
                                    text = n.MenuName,
                                    state = permissions.Any(p => p.ResourceId == n.MenuId && p.ResourceType == "M") ? new State() { Checked = true } : new State(),
                                    nodes = null
                                };

                                node2.nodes.Add(node3);
                            });
                        }
                        catch (Exception ex)
                        {
                            throw ex;
                        }


                        node.nodes.Add(node2);
                    });

                    nodes.Add(node);
                });

                response.Data = nodes;
                response.IsSuccess = true;
                return Json(response);
            }
            return null;
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult RolePermissionsCreateUpdate(RolePermissionModel model)
        {
            var response = new PostResponse();
            var permissions = new List<BizRolePermission>();

            if (model.Nodes != null && model.Nodes.Count > 0)
            {
                model.Nodes.ForEach(x =>
                {
 
                    var permission = new BizRolePermission();
                    permission.ResourceId = Convert.ToInt64(x.nodeOriginalId);
                    permission.ResourceCode = x.nodeCode;
                    permission.ResourceName = x.text;
                    permission.ResourceType = x.nodeType;

                    permissions.Add(permission);
                });

                bool result = RoleService.Instance.RolePermissionsCreateUpdate(model.RoleId, permissions);

                if (result)
                {
                    response.Message = "保存成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "保存失败！";
                    response.IsSuccess = false;
                }
            }

            return Json(response);
        }

        #endregion
  
    }


}
