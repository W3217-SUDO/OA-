using Microsoft.VisualBasic.CompilerServices;
using System;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.Web;
namespace WebControlCaptcha
{
	public class CaptchaImageHandler : IHttpHandler
	{
		public bool IsReusable
		{
			get
			{
				return true;
			}
		}
		[DebuggerNonUserCode]
		public CaptchaImageHandler()
		{
		}
		public void ProcessRequest(HttpContext context)
		{
			HttpApplication app = context.ApplicationInstance;
			string guid = app.Request.QueryString["guid"];
			CaptchaImage ci = null;
			bool flag = Operators.CompareString(guid, "", false) != 0;
			bool flag2;
			if (flag)
			{
				flag2 = string.IsNullOrEmpty(app.Request.QueryString["s"]);
				if (flag2)
				{
					ci = (CaptchaImage)HttpRuntime.Cache.Get(guid);
				}
				else
				{
					ci = (CaptchaImage)HttpContext.Current.Session[guid];
				}
			}
			flag2 = (ci == null);
			if (flag2)
			{
				app.Response.StatusCode = 404;
				context.ApplicationInstance.CompleteRequest();
			}
			else
			{
				Bitmap b = ci.RenderImage();
				b.Save(app.Context.Response.OutputStream, ImageFormat.Jpeg);
				b.Dispose();
				app.Response.ContentType = "image/jpeg";
				app.Response.StatusCode = 200;
				context.ApplicationInstance.CompleteRequest();
			}
		}
	}
}
