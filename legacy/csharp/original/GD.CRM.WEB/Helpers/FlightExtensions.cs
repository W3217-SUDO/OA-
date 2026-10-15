using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.ComponentModel;
using Package.Tour.FlightInput.Entity;
using Package.Tour.FlightInput.BizModel;

namespace Package.Tour.FlightInput.Mvc.Helpers
{
	public static class FlightExtensions
	{
		/// <summary>
		/// 获取标签的显示信息
		/// </summary>
		/// <param name="fare"></param>
		/// <param name="propertyName"></param>
		/// <returns></returns>
		public static string DisplayName(this FlightFare fare,string propertyName)
		{
			var type = fare.GetType();
			var propInfo = type.GetProperty(propertyName.Split('.')[0]);
			if (propInfo == null)
			{
				return null;
			}
			var childValue = propInfo.GetValue(fare, null);
			var propChild = childValue.GetType().GetProperty(propertyName.Split('.')[1]);
			var attributes = propChild.GetCustomAttributes(typeof(DisplayNameAttribute), true);
			if (attributes != null
				&& attributes.Length > 0)
			{
				return (attributes[0] as DisplayNameAttribute).DisplayName;
			}
			return string.Empty;
		}

		/// <summary>
		/// 布尔值显示内容
		/// </summary>
		/// <param name="value"></param>
		/// <returns></returns>
		public static string ShowText(this bool value)
		{
			return value ? "是" : "否";
		}

		/// <summary>
		/// 日期值显示内容
		/// </summary>
		/// <param name="value"></param>
		/// <returns></returns>
		public static string ShowText(this DateTime value)
		{
			return value.ToShortDateString();
		}

		/// <summary>
		/// 显示目的地
		/// </summary>
		/// <param name="city"></param>
		/// <returns></returns>
		public static HtmlString ToDepartureCityView(this List<BizCityInfo> city)
		{
			if (city == null
				|| city.Count == 0)
			{
				return new HtmlString(string.Empty);
			}
			if (city.Count == 1)
			{
				return new HtmlString(city[0].CityName);
			}
			else
			{
				string cityName = string.Empty;
				city.ForEach(a => cityName += a.CityName + "，");
				cityName = cityName.TrimEnd('，');
				return new HtmlString("<a href='javascript:void(0)' class='cala-remark'>〔多〕" +
                     "<div>"
					 + cityName
                     + "</div>"
                     + "</a>");
			}

		}
	}
}