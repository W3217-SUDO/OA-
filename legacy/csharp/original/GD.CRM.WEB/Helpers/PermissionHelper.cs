using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using Ctrip.Entity.BasOfflineEntity;
using Microsoft.Ajax.Utilities;
using Ctrip.Business.BasOfflineBusiness;
using Ctrip.Business.BasOfflineUI;

namespace IntellectualProperty.Mvc.Helpers
{
    public class PermissionHelper
    {
        public static bool CheckPermission(int moduleCode)
        {
            string eid = LoginHelper.GetEid();
            if (string.IsNullOrEmpty(eid))
            {
                //TODO
                //throw new Exception("未登录");
            }
            return CheckPermission(moduleCode, eid);
        }

        public static bool CheckPermission(int moduleCode, string eid)
        {
            const string zhfMachineName = "DST60615";//张浩峰的电脑，有权限方便做测试
			if (Environment.MachineName == zhfMachineName)
			{
				return true;
			}
			if (!HttpContext.Current.Items.Contains("InitUserInfo"))
			{
				MVCBaseOffLinePage.InitUserInfo();
				HttpContext.Current.Items.Add("InitUserInfo", true);
			}
            HttpContext ht = System.Web.HttpContext.Current; 
			const string oldUrl="http://pkgint";
			if (ht.Request.Url.ToString().ToLower().StartsWith(oldUrl))
			{
				return false;
			}
            string permissionKey = string.Format("permission_{0}_{1}", eid, moduleCode);
            object permission = ht.Items[permissionKey];
            if (permission != null)
            {
                return (bool) permission;
            }
            CheckPermissionEntity query = new CheckPermissionEntity
            {
                RemoteAddr = ht.Request.ServerVariables["Remote_Addr"],
                LocalAdd = ht.Request.ServerVariables["Local_Addr"],
                Url = ht.Request.ServerVariables["URL"],
                Referurl = string.Empty,
                QueryString = ht.Request.ServerVariables["Query_String"],
                RequestMethod = ht.Request.ServerVariables["Request_Method"]
            };

            if ((query.RemoteAddr == "127.0.0.1") || (query.RemoteAddr.Substring(0, 3) == "172"))
            {
                query.Accesslevel = 30;
            }
            else
            {
                query.Accesslevel = 20;
            }
            query.Internalaccess = 1;


            //if ((query.RemoteAddr == "127.0.0.1") || (query.RemoteAddr.Substring(0, 3) == "172"))
            //{
            //    this._userInfoEntity.Accesslevel = 30;
            //    this._userInfoEntity.Internalaccess = 1;
            //}
            //query.Accesslevel = 20;
            //query.Internalaccess = 1;
            query.ModuleCode = moduleCode;
            query.ModuleID = string.Empty;
            query.Eid = eid;
            query.Log = "F";
            if (string.IsNullOrEmpty(query.Eid))
            {
                throw new Exception("用户Eid为空,请登录。");
            }
            Module _Module = new Module(query);
            ModuleEntity _myModuleEntity = _Module.ModuleInfo;
            if (_Module.IsSOAError)
            {
				throw new Exception("权限验证SOA出现UnKnow错误，请重试");
            }
            // TODO
			//if (LoginHelper.GetEid() == "hhu")
			//{
			//    _myModuleEntity.HasPermission = true;
			//}
            permission = _myModuleEntity.HasPermission;
            ht.Items.Add(permissionKey, permission);
            return _myModuleEntity.HasPermission;
        }
    }
}
