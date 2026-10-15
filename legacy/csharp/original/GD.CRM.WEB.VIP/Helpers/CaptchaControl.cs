using Microsoft.VisualBasic;
using Microsoft.VisualBasic.CompilerServices;
using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.Runtime.CompilerServices;
using System.Text;
using System.Web;
using System.Web.Caching;
using System.Web.UI;
using System.Web.UI.WebControls;
namespace WebControlCaptcha
{
	[DefaultProperty("Text")]
	public class CaptchaControl : WebControl, INamingContainer, IPostBackDataHandler, IValidator
	{
		public enum Layout
		{
			Horizontal,
			Vertical
		}
		public enum CacheType
		{
			HttpRuntime,
			Session
		}
		private static List<WeakReference> __ENCList = new List<WeakReference>();
		private int _timeoutSecondsMax;
		private int _timeoutSecondsMin;
		private bool _userValidated;
		private string _text;
		private string _font;
		private CaptchaImage _captcha;
		private CaptchaControl.Layout _layoutStyle;
		private string _prevguid;
		private string _errorMessage;
		private CaptchaControl.CacheType _cacheStrategy;
		[Bindable(true), Browsable(false), Category("Appearance"), DefaultValue("The text you typed does not match the text in the image."), Description("Message to display in a Validation Summary when the CAPTCHA fails to validate.")]
		public string ErrorMessage
		{
			get
			{
				bool flag = !this._userValidated;
				string ErrorMessage;
				if (flag)
				{
					ErrorMessage = this._errorMessage;
				}
				else
				{
					ErrorMessage = "";
				}
				return ErrorMessage;
			}
			set
			{
				this._errorMessage = value;
			}
		}
		[Browsable(false), Category("Behavior"), DefaultValue(true), Description("Is Valid"), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
		public bool IsValid
		{
			get
			{
				return this._userValidated;
			}
			set
			{
			}
		}
		public override bool Enabled
		{
			get
			{
				return base.Enabled;
			}
			set
			{
				base.Enabled = value;
				bool flag = !value;
				if (flag)
				{
					this._userValidated = true;
				}
			}
		}
		[Category("Appearance"), DefaultValue("Enter the code shown above:"), Description("Instructional text displayed next to CAPTCHA image.")]
		public string Text
		{
			get
			{
				return this._text;
			}
			set
			{
				this._text = value;
			}
		}
		[Category("Captcha"), DefaultValue(typeof(CaptchaControl.Layout), "Horizontal"), Description("Determines if image and input area are displayed horizontally, or vertically.")]
		public CaptchaControl.Layout LayoutStyle
		{
			get
			{
				return this._layoutStyle;
			}
			set
			{
				this._layoutStyle = value;
			}
		}
		[Category("Captcha"), DefaultValue(typeof(CaptchaControl.CacheType), "HttpRuntime"), Description("Determines if CAPTCHA codes are stored in HttpRuntime (fast, but local to current server) or Session (more portable across web farms).")]
		public CaptchaControl.CacheType CacheStrategy
		{
			get
			{
				return this._cacheStrategy;
			}
			set
			{
				this._cacheStrategy = value;
			}
		}
		[Category("Captcha"), Description("Returns True if the user was CAPTCHA validated after a postback.")]
		public bool UserValidated
		{
			get
			{
				return this._userValidated;
			}
		}
		[Category("Captcha"), DefaultValue(""), Description("Font used to render CAPTCHA text. If font name is blank, a random font will be chosen.")]
		public string CaptchaFont
		{
			get
			{
				return this._font;
			}
			set
			{
				this._font = value;
				this._captcha.Font = this._font;
			}
		}
		[Category("Captcha"), DefaultValue(""), Description("Characters used to render CAPTCHA text. A character will be picked randomly from the string.")]
		public string CaptchaChars
		{
			get
			{
				return this._captcha.TextChars;
			}
			set
			{
				this._captcha.TextChars = value;
			}
		}
		[Category("Captcha"), DefaultValue(5), Description("Number of CaptchaChars used in the CAPTCHA text")]
		public int CaptchaLength
		{
			get
			{
				return this._captcha.TextLength;
			}
			set
			{
				this._captcha.TextLength = value;
			}
		}
		[Category("Captcha"), DefaultValue(2), Description("Minimum number of seconds CAPTCHA must be displayed before it is valid. If you're too fast, you must be a robot. Set to zero to disable.")]
		public int CaptchaMinTimeout
		{
			get
			{
				return this._timeoutSecondsMin;
			}
			set
			{
				bool flag = value > 15;
				if (flag)
				{
					throw new ArgumentOutOfRangeException("CaptchaTimeout", "Timeout must be less than 15 seconds. Humans aren't that slow!");
				}
				this._timeoutSecondsMin = value;
			}
		}
		[Category("Captcha"), DefaultValue(90), Description("Maximum number of seconds CAPTCHA will be cached and valid. If you're too slow, you may be a CAPTCHA hack attempt. Set to zero to disable.")]
		public int CaptchaMaxTimeout
		{
			get
			{
				return this._timeoutSecondsMax;
			}
			set
			{
				bool flag = value < 15 & value != 0;
				if (flag)
				{
					throw new ArgumentOutOfRangeException("CaptchaTimeout", "Timeout must be greater than 15 seconds. Humans can't type that fast!");
				}
				this._timeoutSecondsMax = value;
			}
		}
		[Category("Captcha"), DefaultValue(50), Description("Height of generated CAPTCHA image.")]
		public int CaptchaHeight
		{
			get
			{
				return this._captcha.Height;
			}
			set
			{
				this._captcha.Height = value;
			}
		}
		[Category("Captcha"), DefaultValue(180), Description("Width of generated CAPTCHA image.")]
		public int CaptchaWidth
		{
			get
			{
				return this._captcha.Width;
			}
			set
			{
				this._captcha.Width = value;
			}
		}
		[Category("Captcha"), DefaultValue(typeof(CaptchaImage.FontWarpFactor), "Low"), Description("Amount of random font warping used on the CAPTCHA text")]
		public CaptchaImage.FontWarpFactor CaptchaFontWarping
		{
			get
			{
				return this._captcha.FontWarp;
			}
			set
			{
				this._captcha.FontWarp = value;
			}
		}
		[Category("Captcha"), DefaultValue(typeof(CaptchaImage.BackgroundNoiseLevel), "Low"), Description("Amount of background noise to generate in the CAPTCHA image")]
		public CaptchaImage.BackgroundNoiseLevel CaptchaBackgroundNoise
		{
			get
			{
				return this._captcha.BackgroundNoise;
			}
			set
			{
				this._captcha.BackgroundNoise = value;
			}
		}
		[Category("Captcha"), DefaultValue(typeof(CaptchaImage.LineNoiseLevel), "None"), Description("Add line noise to the CAPTCHA image")]
		public CaptchaImage.LineNoiseLevel CaptchaLineNoise
		{
			get
			{
				return this._captcha.LineNoise;
			}
			set
			{
				this._captcha.LineNoise = value;
			}
		}
		private bool IsDesignMode
		{
			get
			{
				return HttpContext.Current == null;
			}
		}
		public CaptchaControl()
		{
			CaptchaControl.__ENCAddToList(this);
			this._timeoutSecondsMax = 90;
			this._timeoutSecondsMin = 3;
			this._userValidated = true;
			this._text = "Enter the code shown:";
			this._font = "";
			this._captcha = new CaptchaImage();
			this._layoutStyle = CaptchaControl.Layout.Horizontal;
			this._errorMessage = "";
			this._cacheStrategy = CaptchaControl.CacheType.HttpRuntime;
		}
		[DebuggerNonUserCode]
		private static void __ENCAddToList(object value)
		{
			List<WeakReference> _ENCList = CaptchaControl.__ENCList;
			checked
			{
				lock (_ENCList)
				{
					bool flag = CaptchaControl.__ENCList.Count == CaptchaControl.__ENCList.Capacity;
					if (flag)
					{
						int num = 0;
						int arg_3F_0 = 0;
						int num2 = CaptchaControl.__ENCList.Count - 1;
						int num3 = arg_3F_0;
						while (true)
						{
							int arg_90_0 = num3;
							int num4 = num2;
							if (arg_90_0 > num4)
							{
								break;
							}
							WeakReference weakReference = CaptchaControl.__ENCList[num3];
							flag = weakReference.IsAlive;
							if (flag)
							{
								bool flag2 = num3 != num;
								if (flag2)
								{
									CaptchaControl.__ENCList[num] = CaptchaControl.__ENCList[num3];
								}
								num++;
							}
							num3++;
						}
						CaptchaControl.__ENCList.RemoveRange(num, CaptchaControl.__ENCList.Count - num);
						CaptchaControl.__ENCList.Capacity = CaptchaControl.__ENCList.Count;
					}
					CaptchaControl.__ENCList.Add(new WeakReference(RuntimeHelpers.GetObjectValue(value)));
				}
			}
		}
		public void Validate()
		{
		}
		private CaptchaImage GetCachedCaptcha(string guid)
		{
			bool flag = this._cacheStrategy == CaptchaControl.CacheType.HttpRuntime;
			CaptchaImage GetCachedCaptcha;
			if (flag)
			{
				GetCachedCaptcha = (CaptchaImage)HttpRuntime.Cache.Get(guid);
			}
			else
			{
				GetCachedCaptcha = (CaptchaImage)HttpContext.Current.Session[guid];
			}
			return GetCachedCaptcha;
		}
		private void RemoveCachedCaptcha(string guid)
		{
			bool flag = this._cacheStrategy == CaptchaControl.CacheType.HttpRuntime;
			if (flag)
			{
				HttpRuntime.Cache.Remove(guid);
			}
			else
			{
				HttpContext.Current.Session.Remove(guid);
			}
		}
		private void ValidateCaptcha(string userEntry)
		{
			bool flag = !this.Visible | !this.Enabled;
			if (flag)
			{
				this._userValidated = true;
			}
			else
			{
				CaptchaImage ci = this.GetCachedCaptcha(this._prevguid);
				flag = (ci == null);
				if (flag)
				{
					this.ErrorMessage = "The code you typed has expired after " + Conversions.ToString(this.CaptchaMaxTimeout) + " seconds.";
					this._userValidated = false;
				}
				else
				{
					flag = (this.CaptchaMinTimeout > 0);
					bool flag2;
					if (flag)
					{
						flag2 = (DateTime.Compare(ci.RenderedAt.AddSeconds((double)this.CaptchaMinTimeout), DateAndTime.Now) > 0);
						if (flag2)
						{
							this._userValidated = false;
							this.ErrorMessage = "Code was typed too quickly. Wait at least " + Conversions.ToString(this.CaptchaMinTimeout) + " seconds.";
							this.RemoveCachedCaptcha(this._prevguid);
							return;
						}
					}
					flag2 = (string.Compare(userEntry, ci.Text, true) != 0);
					if (flag2)
					{
						this.ErrorMessage = "The code you typed does not match the code in the image.";
						this._userValidated = false;
						this.RemoveCachedCaptcha(this._prevguid);
					}
					else
					{
						this._userValidated = true;
						this.RemoveCachedCaptcha(this._prevguid);
					}
				}
			}
		}
		private string HtmlColor(Color color)
		{
			bool flag = color.IsEmpty;
			string HtmlColor;
			if (flag)
			{
				HtmlColor = "";
			}
			else
			{
				flag = color.IsNamedColor;
				if (flag)
				{
					HtmlColor = color.ToKnownColor().ToString();
				}
				else
				{
					flag = color.IsSystemColor;
					if (flag)
					{
						HtmlColor = color.ToString();
					}
					else
					{
						HtmlColor = "#" + color.ToArgb().ToString("x").Substring(2);
					}
				}
			}
			return HtmlColor;
		}
		private string CssStyle()
		{
			StringBuilder sb = new StringBuilder();
			StringBuilder stringBuilder = sb;
			stringBuilder.Append(" style='");
			bool flag = this.BorderWidth.ToString().Length > 0;
			if (flag)
			{
				stringBuilder.Append("border-width:");
				stringBuilder.Append(this.BorderWidth.ToString());
				stringBuilder.Append(";");
			}
			flag = (this.BorderStyle != BorderStyle.NotSet);
			if (flag)
			{
				stringBuilder.Append("border-style:");
				stringBuilder.Append(this.BorderStyle.ToString());
				stringBuilder.Append(";");
			}
			string strColor = this.HtmlColor(this.BorderColor);
			flag = (strColor.Length > 0);
			if (flag)
			{
				stringBuilder.Append("border-color:");
				stringBuilder.Append(strColor);
				stringBuilder.Append(";");
			}
			strColor = this.HtmlColor(this.BackColor);
			flag = (strColor.Length > 0);
			if (flag)
			{
				stringBuilder.Append("background-color:" + strColor + ";");
			}
			strColor = this.HtmlColor(this.ForeColor);
			flag = (strColor.Length > 0);
			if (flag)
			{
				stringBuilder.Append("color:" + strColor + ";");
			}
			flag = this.Font.Bold;
			if (flag)
			{
				stringBuilder.Append("font-weight:bold;");
			}
			flag = this.Font.Italic;
			if (flag)
			{
				stringBuilder.Append("font-style:italic;");
			}
			flag = this.Font.Underline;
			if (flag)
			{
				stringBuilder.Append("text-decoration:underline;");
			}
			flag = this.Font.Strikeout;
			if (flag)
			{
				stringBuilder.Append("text-decoration:line-through;");
			}
			flag = this.Font.Overline;
			if (flag)
			{
				stringBuilder.Append("text-decoration:overline;");
			}
			flag = (this.Font.Size.ToString().Length > 0);
			if (flag)
			{
				stringBuilder.Append("font-size:" + this.Font.Size.ToString() + ";");
			}
			flag = (this.Font.Names.Length > 0);
			checked
			{
				if (flag)
				{
					stringBuilder.Append("font-family:");
					string[] names = this.Font.Names;
					for (int i = 0; i < names.Length; i++)
					{
						string strFontFamily = names[i];
						stringBuilder.Append(strFontFamily);
						stringBuilder.Append(",");
					}
					stringBuilder.Length--;
					stringBuilder.Append(";");
				}
				flag = (Operators.CompareString(this.Height.ToString(), "", false) != 0);
				if (flag)
				{
					stringBuilder.Append("height:" + this.Height.ToString() + ";");
				}
				flag = (Operators.CompareString(this.Width.ToString(), "", false) != 0);
				if (flag)
				{
					stringBuilder.Append("width:" + this.Width.ToString() + ";");
				}
				stringBuilder.Append("'");
				flag = (Operators.CompareString(sb.ToString(), " style=''", false) == 0);
				string CssStyle;
				if (flag)
				{
					CssStyle = "";
				}
				else
				{
					CssStyle = sb.ToString();
				}
				return CssStyle;
			}
		}
		protected override void Render(HtmlTextWriter Output)
		{
			Output.Write("<div");
			bool flag = Operators.CompareString(this.CssClass, "", false) != 0;
			if (flag)
			{
				Output.Write(" class='" + this.CssClass + "'");
			}
			Output.Write(this.CssStyle());
			Output.Write(">");
			flag = (this.LayoutStyle == CaptchaControl.Layout.Vertical);
			if (flag)
			{
				Output.Write("<div style='text-align:center;margin:5px;'>");
			}
			else
			{
				Output.Write("<span style='margin:5px;float:left;'>");
			}
			Output.Write("<img src=\"CaptchaImage.aspx");
			flag = !this.IsDesignMode;
			if (flag)
			{
				Output.Write("?guid=" + Convert.ToString(this._captcha.UniqueId));
			}
			flag = (this.CacheStrategy == CaptchaControl.CacheType.Session);
			if (flag)
			{
				Output.Write("&s=1");
			}
			Output.Write("\" border='0'");
			flag = (this.ToolTip.Length > 0);
			if (flag)
			{
				Output.Write(" alt='" + this.ToolTip + "'");
			}
			Output.Write(" width=" + Conversions.ToString(this._captcha.Width));
			Output.Write(" height=" + Conversions.ToString(this._captcha.Height));
			Output.Write(">");
			flag = (this.LayoutStyle == CaptchaControl.Layout.Vertical);
			if (flag)
			{
				Output.Write("</div>");
			}
			else
			{
				Output.Write("</span>");
			}
			flag = (this.LayoutStyle == CaptchaControl.Layout.Vertical);
			if (flag)
			{
				Output.Write("<div style='text-align:center;margin:5px;'>");
			}
			else
			{
				Output.Write("<span style='margin:5px;float:left;'>");
			}
			flag = (this._text.Length > 0);
			if (flag)
			{
				Output.Write(this._text);
				Output.Write("<br>");
			}
			Output.Write("<input name=" + this.UniqueID + " type=text size=");
			Output.Write(this._captcha.TextLength.ToString());
			Output.Write(" maxlength=");
			Output.Write(this._captcha.TextLength.ToString());
			flag = (this.AccessKey.Length > 0);
			if (flag)
			{
				Output.Write(" accesskey=" + this.AccessKey);
			}
			flag = !this.Enabled;
			if (flag)
			{
				Output.Write(" disabled=\"disabled\"");
			}
			flag = (this.TabIndex > 0);
			if (flag)
			{
				Output.Write(" tabindex=" + this.TabIndex.ToString());
			}
			Output.Write(" value=''>");
			flag = (this.LayoutStyle == CaptchaControl.Layout.Vertical);
			if (flag)
			{
				Output.Write("</div>");
			}
			else
			{
				Output.Write("</span>");
				Output.Write("<br clear='all'>");
			}
			Output.Write("</div>");
		}
		private void GenerateNewCaptcha()
		{
			bool flag = !this.IsDesignMode;
			if (flag)
			{
				bool flag2 = this._cacheStrategy == CaptchaControl.CacheType.HttpRuntime;
				if (flag2)
				{
					HttpRuntime.Cache.Add(this._captcha.UniqueId, this._captcha, null, DateTime.Now.AddSeconds(Convert.ToDouble(RuntimeHelpers.GetObjectValue(Interaction.IIf(this.CaptchaMaxTimeout == 0, 90, this.CaptchaMaxTimeout)))), TimeSpan.Zero, CacheItemPriority.NotRemovable, null);
				}
				else
				{
					HttpContext.Current.Session.Add(this._captcha.UniqueId, this._captcha);
				}
			}
		}
		public bool LoadPostData(string PostDataKey, NameValueCollection Values)
		{
			this.ValidateCaptcha(Convert.ToString(Values[this.UniqueID]));
			return false;
		}
		public void RaisePostDataChangedEvent()
		{
		}
		protected override object SaveControlState()
		{
			return this._captcha.UniqueId;
		}
		protected override void LoadControlState(object state)
		{
			bool flag = state != null;
			if (flag)
			{
				this._prevguid = Conversions.ToString(state);
			}
		}
		protected override void OnInit(EventArgs e)
		{
			base.OnInit(e);
			this.Page.RegisterRequiresControlState(this);
			this.Page.Validators.Add(this);
		}
		protected override void OnUnload(EventArgs e)
		{
			bool flag = this.Page != null;
			if (flag)
			{
				this.Page.Validators.Remove(this);
			}
			base.OnUnload(e);
		}
		protected override void OnPreRender(EventArgs e)
		{
			bool visible = this.Visible;
			if (visible)
			{
				this.GenerateNewCaptcha();
			}
			base.OnPreRender(e);
		}
	}
}
