using Microsoft.VisualBasic.CompilerServices;
using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Text;
namespace WebControlCaptcha
{
	public class CaptchaImage
	{
		public enum FontWarpFactor
		{
			None,
			Low,
			Medium,
			High,
			Extreme
		}
		public enum BackgroundNoiseLevel
		{
			None,
			Low,
			Medium,
			High,
			Extreme
		}
		public enum LineNoiseLevel
		{
			None,
			Low,
			Medium,
			High,
			Extreme
		}
		private int _height;
		private int _width;
		private Random _rand;
		private DateTime _generatedAt;
		private string _randomText;
		private int _randomTextLength;
		private string _randomTextChars;
		private string _fontFamilyName;
		private CaptchaImage.FontWarpFactor _fontWarp;
		private CaptchaImage.BackgroundNoiseLevel _backgroundNoise;
		private CaptchaImage.LineNoiseLevel _lineNoise;
		private string _guid;
		private string _fontWhitelist;
		private string[] ff;
		public string UniqueId
		{
			get
			{
				return this._guid;
			}
		}
		public DateTime RenderedAt
		{
			get
			{
				return this._generatedAt;
			}
		}
		public string Font
		{
			get
			{
				return this._fontFamilyName;
			}
			set
			{
				try
				{
					Font font = new Font(value, 12f);
					this._fontFamilyName = value;
					font.Dispose();
				}
				catch (Exception expr_1E)
				{
					ProjectData.SetProjectError(expr_1E);
					this._fontFamilyName = FontFamily.GenericSerif.Name;
					ProjectData.ClearProjectError();
				}
			}
		}
		public CaptchaImage.FontWarpFactor FontWarp
		{
			get
			{
				return this._fontWarp;
			}
			set
			{
				this._fontWarp = value;
			}
		}
		public CaptchaImage.BackgroundNoiseLevel BackgroundNoise
		{
			get
			{
				return this._backgroundNoise;
			}
			set
			{
				this._backgroundNoise = value;
			}
		}
		public CaptchaImage.LineNoiseLevel LineNoise
		{
			get
			{
				return this._lineNoise;
			}
			set
			{
				this._lineNoise = value;
			}
		}
		public string TextChars
		{
			get
			{
				return this._randomTextChars;
			}
			set
			{
				this._randomTextChars = value;
				this._randomText = this.GenerateRandomText();
			}
		}
		public int TextLength
		{
			get
			{
				return this._randomTextLength;
			}
			set
			{
				this._randomTextLength = value;
				this._randomText = this.GenerateRandomText();
			}
		}
		public string Text
		{
			get
			{
				return this._randomText;
			}
		}
		public int Width
		{
			get
			{
				return this._width;
			}
			set
			{
				bool flag = value <= 60;
				if (flag)
				{
					throw new ArgumentOutOfRangeException("width", value, "width must be greater than 60.");
				}
				this._width = value;
			}
		}
		public int Height
		{
			get
			{
				return this._height;
			}
			set
			{
				bool flag = value <= 30;
				if (flag)
				{
					throw new ArgumentOutOfRangeException("height", value, "height must be greater than 30.");
				}
				this._height = value;
			}
		}
		public string FontWhitelist
		{
			get
			{
				return this._fontWhitelist;
			}
			set
			{
				this._fontWhitelist = value;
			}
		}
		public CaptchaImage()
		{
			this._rand = new Random();
			this._fontWarp = CaptchaImage.FontWarpFactor.Low;
			this._backgroundNoise = CaptchaImage.BackgroundNoiseLevel.Low;
			this._lineNoise = CaptchaImage.LineNoiseLevel.None;
			this._width = 180;
			this._height = 50;
			this._randomTextLength = 5;
			this._randomTextChars = "REDACTED_ARCHIVE_ONLY";
			this._fontFamilyName = "";
			this._fontWhitelist = "arial;arial black;comic sans ms;courier new;estrangelo edessa;franklin gothic medium;georgia;lucida console;lucida sans unicode;mangal;microsoft sans serif;palatino linotype;sylfaen;tahoma;times new roman;trebuchet ms;verdana";
			this._randomText = this.GenerateRandomText();
			this._generatedAt = DateTime.Now;
			this._guid = Guid.NewGuid().ToString();
		}
		public Bitmap RenderImage()
		{
			return this.GenerateImagePrivate();
		}
		private string RandomFontFamily()
		{
			bool flag = this.ff == null;
			if (flag)
			{
				this.ff = this._fontWhitelist.Split(new char[]
				{
					';'
				});
			}
            return this.ff[this._rand.Next(0, this.ff.Length)];
		}
		private string GenerateRandomText()
		{
			StringBuilder sb = new StringBuilder(this._randomTextLength);
			int maxLength = this._randomTextChars.Length;
			int arg_24_0 = 0;
			checked
			{
				int num = this._randomTextLength - 1;
				int i = arg_24_0;
				while (true)
				{
					int arg_52_0 = i;
					int num2 = num;
					if (arg_52_0 > num2)
					{
						break;
					}
					sb.Append(this._randomTextChars.Substring(this._rand.Next(maxLength), 1));
					i++;
				}
				return sb.ToString();
			}
		}
		private PointF RandomPoint(int xmin, int xmax, ref int ymin, ref int ymax)
		{
			PointF result = new PointF((float)this._rand.Next(xmin, xmax), (float)this._rand.Next(ymin, ymax));
			return result;
		}
		private PointF RandomPoint(Rectangle rect)
		{
			int arg_24_1 = rect.Left;
			int arg_24_2 = rect.Width;
			int top = rect.Top;
			int bottom = rect.Bottom;
			return this.RandomPoint(arg_24_1, arg_24_2, ref top, ref bottom);
		}
		private GraphicsPath TextPath(string s, Font f, Rectangle r)
		{
			StringFormat sf = new StringFormat();
			sf.Alignment = StringAlignment.Near;
			sf.LineAlignment = StringAlignment.Near;
			GraphicsPath gp = new GraphicsPath();
			gp.AddString(s, f.FontFamily, (int)f.Style, f.Size, r, sf);
			return gp;
		}
		private Font GetFont()
		{
		     
			string fname = this._fontFamilyName;
			bool flag = Operators.CompareString(fname, "", false) == 0;
			if (flag)
			{
				fname = this.RandomFontFamily();
			}
			float fsize = 0;
			switch (this.FontWarp)
			{
			case CaptchaImage.FontWarpFactor.None:
				fsize = (float)Convert.ToInt32((double)this._height * 0.7);
				break;
			case CaptchaImage.FontWarpFactor.Low:
				fsize = (float)Convert.ToInt32((double)this._height * 0.8);
				break;
			case CaptchaImage.FontWarpFactor.Medium:
				fsize = (float)Convert.ToInt32((double)this._height * 0.85);
				break;
			case CaptchaImage.FontWarpFactor.High:
				fsize = (float)Convert.ToInt32((double)this._height * 0.9);
				break;
			case CaptchaImage.FontWarpFactor.Extreme:
				fsize = (float)Convert.ToInt32((double)this._height * 0.95);
				break;
			}
			return new Font(fname, fsize, FontStyle.Bold);
		}
		private Bitmap GenerateImagePrivate()
		{
			Font fnt = null;
			Bitmap bmp = new Bitmap(this._width, this._height, PixelFormat.Format32bppArgb);
			Graphics gr = Graphics.FromImage(bmp);
			gr.SmoothingMode = SmoothingMode.AntiAlias;
			Rectangle rect = new Rectangle(0, 0, this._width, this._height);
			Brush br = new SolidBrush(Color.White);
			gr.FillRectangle(br, rect);
			int charOffset = 0;
			double charWidth = (double)this._width / (double)this._randomTextLength;
			string randomText = this._randomText;
			int i = 0;
			int length = randomText.Length;
			while (i < length)
			{
				char c = randomText[i];
				fnt = this.GetFont();
				Rectangle rectChar = new Rectangle(Convert.ToInt32((double)charOffset * charWidth), 0, Convert.ToInt32(charWidth), this._height);
				GraphicsPath gp = this.TextPath(Conversions.ToString(c), fnt, rectChar);
				this.WarpText(gp, rectChar);
				br = new SolidBrush(Color.Black);
				gr.FillPath(br, gp);
				checked
				{
					charOffset++;
					i++;
				}
			}
			this.AddNoise(gr, rect);
			this.AddLine(gr, rect);
			fnt.Dispose();
			br.Dispose();
			gr.Dispose();
			return bmp;
		}
		private void WarpText(GraphicsPath textPath, Rectangle rect)
		{
			float WarpDivisor = 0;
			float RangeModifier = 0;
			switch (this._fontWarp)
			{
			case CaptchaImage.FontWarpFactor.None:
				return;
			case CaptchaImage.FontWarpFactor.Low:
				WarpDivisor = 6f;
				RangeModifier = 1f;
				break;
			case CaptchaImage.FontWarpFactor.Medium:
				WarpDivisor = 5f;
				RangeModifier = 1.3f;
				break;
			case CaptchaImage.FontWarpFactor.High:
				WarpDivisor = 4.5f;
				RangeModifier = 1.4f;
				break;
			case CaptchaImage.FontWarpFactor.Extreme:
				WarpDivisor = 4f;
				RangeModifier = 1.5f;
				break;
			}
			RectangleF rectF = new RectangleF(Convert.ToSingle(rect.Left), 0f, Convert.ToSingle(rect.Width), (float)rect.Height);
			int hrange = Convert.ToInt32((float)rect.Height / WarpDivisor);
			int wrange = Convert.ToInt32((float)rect.Width / WarpDivisor);
			checked
			{
				int left = rect.Left - Convert.ToInt32(unchecked((float)wrange * RangeModifier));
				int top = rect.Top - Convert.ToInt32(unchecked((float)hrange * RangeModifier));
				int width = rect.Left + rect.Width + Convert.ToInt32(unchecked((float)wrange * RangeModifier));
				int height = rect.Top + rect.Height + Convert.ToInt32(unchecked((float)hrange * RangeModifier));
				bool flag = left < 0;
				if (flag)
				{
					left = 0;
				}
				flag = (top < 0);
				if (flag)
				{
					top = 0;
				}
				flag = (width > this.Width);
				if (flag)
				{
					width = this.Width;
				}
				flag = (height > this.Height);
				if (flag)
				{
					height = this.Height;
				}
				int arg_17B_1 = left;
				int arg_17B_2 = left + wrange;
				int num = top + hrange;
				PointF leftTop = this.RandomPoint(arg_17B_1, arg_17B_2, ref top, ref num);
				int arg_194_1 = width - wrange;
				int arg_194_2 = width;
				num = top + hrange;
				PointF rightTop = this.RandomPoint(arg_194_1, arg_194_2, ref top, ref num);
				int arg_1AA_1 = left;
				int arg_1AA_2 = left + wrange;
				num = height - hrange;
				PointF leftBottom = this.RandomPoint(arg_1AA_1, arg_1AA_2, ref num, ref height);
				int arg_1C1_1 = width - wrange;
				int arg_1C1_2 = width;
				num = height - hrange;
				PointF rightBottom = this.RandomPoint(arg_1C1_1, arg_1C1_2, ref num, ref height);
				PointF[] points = new PointF[]
				{
					leftTop,
					rightTop,
					leftBottom,
					rightBottom
				};
				Matrix i = new Matrix();
				i.Translate(0f, 0f);
				textPath.Warp(points, rectF, i, WarpMode.Perspective, 0f);
			}
		}
		private void AddNoise(Graphics graphics1, Rectangle rect)
		{
			int density = 0;
			int size = 0;
			switch (this._backgroundNoise)
			{
			case CaptchaImage.BackgroundNoiseLevel.None:
				return;
			case CaptchaImage.BackgroundNoiseLevel.Low:
				density = 30;
				size = 40;
				break;
			case CaptchaImage.BackgroundNoiseLevel.Medium:
				density = 18;
				size = 40;
				break;
			case CaptchaImage.BackgroundNoiseLevel.High:
				density = 16;
				size = 39;
				break;
			case CaptchaImage.BackgroundNoiseLevel.Extreme:
				density = 12;
				size = 38;
				break;
			}
			SolidBrush br = new SolidBrush(Color.Black);
			int max = Convert.ToInt32((double)Math.Max(rect.Width, rect.Height) / (double)size);
			int arg_96_0 = 0;
			checked
			{
				int num = Convert.ToInt32((double)(rect.Width * rect.Height) / (double)density);
				int i = arg_96_0;
				while (true)
				{
					int arg_ED_0 = i;
					int num2 = num;
					if (arg_ED_0 > num2)
					{
						break;
					}
					graphics1.FillEllipse(br, this._rand.Next(rect.Width), this._rand.Next(rect.Height), this._rand.Next(max), this._rand.Next(max));
					i++;
				}
				br.Dispose();
			}
		}
		private void AddLine(Graphics graphics1, Rectangle rect)
		{
			int length = 0;
			float width = 0;
			int linecount = 0;
			switch (this._lineNoise)
			{
			case CaptchaImage.LineNoiseLevel.None:
				return;
			case CaptchaImage.LineNoiseLevel.Low:
				length = 4;
				width = Convert.ToSingle((double)this._height / 31.25);
				linecount = 1;
				break;
			case CaptchaImage.LineNoiseLevel.Medium:
				length = 5;
				width = Convert.ToSingle((double)this._height / 27.7777);
				linecount = 1;
				break;
			case CaptchaImage.LineNoiseLevel.High:
				length = 3;
				width = Convert.ToSingle((double)this._height / 25.0);
				linecount = 2;
				break;
			case CaptchaImage.LineNoiseLevel.Extreme:
				length = 3;
				width = Convert.ToSingle((double)this._height / 22.7272);
				linecount = 3;
				break;
			}
			checked
			{
				PointF[] pf = new PointF[length + 1];
				Pen p = new Pen(Color.Black, width);
				int arg_C8_0 = 1;
				int num = linecount;
				int i = arg_C8_0;
				while (true)
				{
					int arg_116_0 = i;
					int num2 = num;
					if (arg_116_0 > num2)
					{
						break;
					}
					int arg_D0_0 = 0;
					int num3 = length;
					int j = arg_D0_0;
					while (true)
					{
						int arg_F7_0 = j;
						num2 = num3;
						if (arg_F7_0 > num2)
						{
							break;
						}
						pf[j] = this.RandomPoint(rect);
						j++;
					}
					graphics1.DrawCurve(p, pf, 1.75f);
					i++;
				}
				p.Dispose();
			}
		}
	}
}
