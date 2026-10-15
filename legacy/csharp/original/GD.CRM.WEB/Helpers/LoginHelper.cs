using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using Package.Tour.FlightInput.Mvc.Models;
using Ctrip.Common.Utility;
using System.Configuration;

namespace IntellectualProperty.Mvc.Helpers
{
    public class LoginHelper
    {
     
        public static string GetEid()
        {
            return GetEmployee().Eid;
        }

        public static Employee GetEmployee()
        {
            var employee = GetUserProfile();
            return employee;
        }

        protected static Employee GetUserProfile()
        {
            if (HttpContext.Current == null)
            {
                throw new Exception("HttpContext is null !");
            }

            var employee = new Employee();
            if (HttpContext.Current.Request.Cookies["EncriptEID"] != null && HttpContext.Current.Request.Cookies["EncriptEID"].Value != string.Empty)
            {
                //if (HttpContext.Current.Session["EncriptEID"] != null && (string)HttpContext.Current.Session["EncriptEID"] == HttpContext.Current.Request.Cookies["EncriptEID"].Value)
                //{
                //    if (HttpContext.Current.Session["EID"] != null)
                //    {
                //        employee.Eid = (string)HttpContext.Current.Session["EID"];
                //    }
                //    if (HttpContext.Current.Session["accesslevel"] != null)
                //    {
                //        employee.Accesslevel = Convert.ToInt32(HttpContext.Current.Session["accesslevel"]);
                //    }
                //    if (HttpContext.Current.Session["internalaccess"] != null)
                //    {
                //        employee.Internalaccess = Convert.ToInt32(HttpContext.Current.Session["internalaccess"]);
                //    }
                //}
                //else
                //{
                //HttpContext.Current.Session["EID"] = string.Empty;
                //HttpContext.Current.Session["EncriptEID"] = string.Empty;
                //HttpContext.Current.Session["accesslevel"] = string.Empty;
                //HttpContext.Current.Session["internalaccess"] = string.Empty;
                if (HttpContext.Current.Request.Cookies["EncriptEID"] != null && HttpContext.Current.Request.Cookies["EncriptEID"].Value != string.Empty)
                {
                    string cookieEID = GetUserCookies(HttpContext.Current.Request.Cookies["EncriptEID"].Value);
                    if (cookieEID != null)
                    {
                        //HttpContext.Current.Session["EID"] = cookieEID.Trim();
                        //HttpContext.Current.Session["EncriptEID"] = HttpContext.Current.Request.Cookies["EncriptEID"].Value;
                        employee.Eid = cookieEID.Trim();
                    }
                }
                if (HttpContext.Current.Request.Cookies["EncriptAccesslevel"] != null &&
                    HttpContext.Current.Request.Cookies["EncriptAccesslevel"].Value != string.Empty)
                {
                    string cookieAccesslevel = GetUserCookies(HttpContext.Current.Request.Cookies["EncriptAccesslevel"].Value);
                    if (cookieAccesslevel != null)
                    {
                        //HttpContext.Current.Session["accesslevel"] = cookieAccesslevel;

                        try
                        {
                            int accesslevel;
                            Int32.TryParse(cookieAccesslevel, out accesslevel);
                            employee.Accesslevel = accesslevel;
                        }
                        catch
                        { }
                    }
                }
                if (HttpContext.Current.Request.Cookies["EncriptInternalaccess"] != null &&
                    HttpContext.Current.Request.Cookies["EncriptInternalaccess"].Value != string.Empty)
                {
                    string cookieInternalaccess = GetUserCookies(HttpContext.Current.Request.Cookies["EncriptInternalaccess"].Value);
                    if (cookieInternalaccess != null)
                    {
                        //HttpContext.Current.Session["internalaccess"] = cookieInternalaccess;
                        //employee.Internalaccess = Convert.ToInt32(cookieInternalaccess);

                        try
                        {
                            int internalaccess;
                            Int32.TryParse(cookieInternalaccess, out internalaccess);
                            employee.Internalaccess = internalaccess;
                        }
                        catch
                        { }
                    }
                }
                //}
            }

            return employee;
        }

        protected static string GetUserCookies(string cookieValue)
        {
            string tempString = null;
            string key = Encryption.DecryptDesKey(ConfigurationManager.AppSettings["CookieDesKey"]);
            if (!string.IsNullOrEmpty(cookieValue))
            {
                tempString = Encryption.DecryptDes(cookieValue, key);
            }
            return tempString;
        }
    }
}