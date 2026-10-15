using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;

using Dchien.Legal.Web.Models;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Areas.RPT.ViewModels.Report;
using Dchien.Legal.Entity.FAM.AR.Payment;
using Dchien.Legal.Service.FAM.AR.Payment;
using Dchien.Legal.Service;
using Dchien.Legal.BizModel.FAM.AR.Payment;
using Dchien.Legal.Service.Legal.Case;
using Dchien.Legal.Entity.BAS.Type;

namespace Dchien.Legal.Web.Areas.RPT.Controllers
{
    [CheckUserLogin]
    public class ReportController : Controller
    {
        internal Log Logger = new Log("RPT.Controllers.ReportController");

 
        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CountRoiGroupByCustomer(string id)
        {
            var model = new CountRoiListModel();

            model.SearchCondition = new Entity.Legal.Case.CaseSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>

        [CheckUserLogin]
        public ActionResult CountRoiGroupByStaff(string id)
        {
            var model = new CountRoiListModel();

            model.SearchCondition = new Entity.Legal.Case.CaseSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CountRefundCaseGroupByAssistant(string id)
        {
            var model = new CountRefundListModel();

            model.SearchCondition = new Entity.Legal.Case.CaseSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;

            return View(model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CountRoiGroupByCustomer(CountRoiListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                #region 默认客户

                if (string.IsNullOrEmpty(model.SearchCondition.CustomerNos))
                {
                    var customerNos = new List<string>();
                    customerNos.Add("SHKH1911615");
                    customerNos.Add("SHKH1700015");
                    customerNos.Add("SHKH1910002");
                    customerNos.Add("SHKH1911386");
                    customerNos.Add("SHKH1910750");
                    customerNos.Add("SHKH2110183");
                    customerNos.Add("SHKH1710351");
                    customerNos.Add("SHKH1810382");
                    customerNos.Add("SHKH2110115");
                    customerNos.Add("SHKH1810686");
                    customerNos.Add("SHKH1910499");
                    customerNos.Add("SHKH2010825");
                    customerNos.Add("SHKH2111554");
                    customerNos.Add("SHKH1600134");
                    customerNos.Add("SHKH1810135");
                    customerNos.Add("SHKH1911538");
                    customerNos.Add("SHKH2110589");
                    customerNos.Add("SHKH1810745");
                    customerNos.Add("SHKH1600001");
                    customerNos.Add("SHKH1700064");
                    customerNos.Add("SHKH1910814");
                    customerNos.Add("SHKH1910498");
                    customerNos.Add("SHKH1810376");
                    customerNos.Add("SHKH1710151");
                    customerNos.Add("SHKH2010891");

                    model.SearchCondition.CustomerNos = string.Join(",", customerNos);
                }

                #endregion

                var cycle = CaseSearchService.Instance.CountRoiCycleGroupByCustomer(model.SearchCondition);
                var rate = CaseSearchService.Instance.CountRoiRateGroupByCustomer(model.SearchCondition);
                var deficit = CaseSearchService.Instance.CountRoiDeficitGroupByCustomer(model.SearchCondition);

                var roi = new { Cycle = cycle, Rate = rate, Deficit = deficit };

                response.Data = new { Roi = roi };

                response.IsSuccess = true;
  
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ReportController.CountRoi", "ReportController.CountRoi", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CountRoiGroupByStaff(CountRoiListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                if (string.IsNullOrEmpty(model.SearchCondition.CountRoiGroupStaffs))
                {
                    if (model.SearchCondition.CountRoiGroupId == 10)
                    {
                        var staffs = new List<string>();
                        staffs.Add("tgn");
                        staffs.Add("chenmt");
                        staffs.Add("shenjf");
                        staffs.Add("taoyg");
                        staffs.Add("lijiang");
                        staffs.Add("wangxy");
                        staffs.Add("xuejd");
                        staffs.Add("wtt");
                        staffs.Add("xiajian");

                        model.SearchCondition.CountRoiGroupStaffs = string.Join(",", staffs);
                    }
                    else if (model.SearchCondition.CountRoiGroupId == 20)
                    {
                        var staffs = new List<string>();
                        staffs.Add("wangxy");
                        staffs.Add("xuejd");
                        staffs.Add("wtt");
                        staffs.Add("xiajian");
                        staffs.Add("zhushuyi");
                        staffs.Add("liuhuiyan");
                        staffs.Add("lijiani");
                        staffs.Add("heyunlong");
                        staffs.Add("hezhenmei");
                        staffs.Add("sunruyi");

                        model.SearchCondition.CountRoiGroupStaffs = string.Join(",", staffs);
                    }
                }

                var cycle = CaseSearchService.Instance.CountRoiCycleGroupByStaff(model.SearchCondition);
                var rate = CaseSearchService.Instance.CountRoiRateGroupByStaff(model.SearchCondition);
                var deficit = CaseSearchService.Instance.CountRoiDeficitGroupByStaff(model.SearchCondition);

                var roi = new { Cycle = cycle, Rate = rate, Deficit = deficit };

                response.Data = new { Roi = roi } ;

                response.IsSuccess = true;

            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ReportController.CountRoiGroupByStaff", "ReportController.CountRoiGroupByStaff", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CountRefundCaseGroupByAssistant(CountRefundListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15; 

                var refund = CaseSearchService.Instance.CountRefundCaseGroupByAssistant(model.SearchCondition);
                var r10 = refund.FirstOrDefault(x => x.Key == (int)RefundStatus.R10);
                var r20 = refund.FirstOrDefault(x => x.Key == (int)RefundStatus.R20);
                var r30 = refund.FirstOrDefault(x => x.Key == (int)RefundStatus.R30);
                var r35 = refund.FirstOrDefault(x => x.Key == (int)RefundStatus.R35);
                var r40 = refund.FirstOrDefault(x => x.Key == (int)RefundStatus.R40);
                var r50 = refund.FirstOrDefault(x => x.Key == (int)RefundStatus.R50);
                var r = new { R10 = r10, R20 = r20, R30 = r30,  R35 = r35, R40 = r40, R50 = r50 };
                response.Data = new { Refund = r };
                response.IsSuccess = true;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ReportController.CountRefundGroupByAssistant", "ReportController.CountRefundGroupByAssistant", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CountExecuteCaseGroupByAssistant(string id)
        {
            var model = new CountExecuteListModel();
            model.SearchCondition = new Entity.Legal.Case.CaseSearchCondition();
            model.SearchCondition.PageId = id;
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CountExecuteCaseGroupByAssistant(CountExecuteListModel model)
        {
            var response = new PostResponse();
            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;
                var execute = CaseSearchService.Instance.CountExecuteCaseGroupByAssistant(model.SearchCondition);
                var r10 = execute.FirstOrDefault(x => x.Key ==  101020);
                var r20 = execute.FirstOrDefault(x => x.Key ==  102017);
                var r30 = execute.FirstOrDefault(x => x.Key == 104019);
                var r40 = execute.FirstOrDefault(x => x.Key ==  104011);
                var r50 = execute.FirstOrDefault(x => x.Key ==  104012);
                var r60 = execute.FirstOrDefault(x => x.Key == 104013);
                var r70 = execute.FirstOrDefault(x => x.Key == 104014);
                var r80 = execute.FirstOrDefault(x => x.Key == 104015);
                var r90 = execute.FirstOrDefault(x => x.Key == 104016);
                var r100 = execute.FirstOrDefault(x => x.Key == 104021);
                var r = new { R10 = r10, R20 = r20, R30 = r30, R40 = r40, R50 = r50, R60 = r60, R70 = r70, R80 = r80, R90 = r90, R100 = r100 };
                response.Data = new { Execute = r };
                response.IsSuccess = true;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ReportController.CountExecuteCaseGroupByAssistant", "ReportController.CountExecuteCaseGroupByAssistant", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult LargeScreen(string id)
        {
            return View();
        }

    }
}
