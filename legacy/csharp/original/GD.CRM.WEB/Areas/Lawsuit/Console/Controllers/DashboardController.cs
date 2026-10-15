using System;
using System.Collections.Generic;
using System.Web.Mvc;
using System.Linq;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Web.Areas.Console.ViewModels.Index;
using Dchien.Legal.Service.Legal.Case;
using Dchien.Legal.Entity.TP.Task;
using Dchien.Legal.Service.TP.Task;
using Dchien.Legal.Entity.Legal.Case;
using Dchien.Legal.Service;
using Dchien.Legal.Entity.BAS.Type;

namespace Dchien.Legal.Web.Areas.Console.Controllers
{
    [CheckUserLogin]
    public class DashboardController : Controller
    {
        internal Log Logger = new Log("Console.Controllers.DashboardController");

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult Index()
        {
            var model = new Dchien.Legal.Web.Areas.Console.ViewModels.Index.IndexModel();
            var taskSearchCondition = new TaskSearchCondition();
            taskSearchCondition.PageId = Dchien.Legal.Entity.System.PageId.PageId_9001001020;
            taskSearchCondition.NodeStatus = NodeStatus.Processing;
            taskSearchCondition.PageNo = 1;
            taskSearchCondition.PageSize = 13;
            model.Top10Tasks = TaskService.Instance.GetTaskList(taskSearchCondition);

            //var caseFileSearchCondition = new CaseFileSearchCondition();
            //caseFileSearchCondition.AccessLevel = (Entity.Account.AccessLevel)LoginHelper.GetAccesslevel();
            //caseFileSearchCondition.UserId = LoginHelper.GetUserName();
            //caseFileSearchCondition.PageNo = 1;
            //caseFileSearchCondition.PageSize = 10;
            //caseFileSearchCondition.IsOfficeFileType = true;
            //caseFileSearchCondition.Sorting = "T.UploadingTime desc,T.CaseId";
            //if (LoginHelper.GetAccesslevel() != (int)Dchien.Legal.Entity.Account.AccessLevel.All)
            //{
            //    caseFileSearchCondition.BusinessOwner = LoginHelper.GetUserName();
            //}

            //model.Top10CaseOfficeFiles = Dchien.Legal.Service.IPR.Case.CaseFileSearchService.Instance.GetCaseFileList(caseFileSearchCondition);

            var caseSearchCondition = new Dchien.Legal.Entity.Legal.Case.CaseSearchCondition();

            caseSearchCondition.PageNo = 1;
            caseSearchCondition.PageSize = 13;
            caseSearchCondition.LawfulDayFrom = DateTime.Now;
            caseSearchCondition.LawfulDayTo = DateTime.Now.AddDays(100);

            //var menus = MenuService.Instance.GetMenusByCurrentUser();

            //if (menus.Any(x => x.MenuCode == Dchien.Legal.Entity.System.PageId.PageId_100110110))
            //{
            //    caseSearchCondition.PageId = Dchien.Legal.Entity.System.PageId.PageId_100110110;
            //}
            //else
            //{
            //    caseSearchCondition.PageId = Dchien.Legal.Entity.System.PageId.PageId_1001103100;
            //}

            caseSearchCondition.PageId = Dchien.Legal.Entity.System.PageId.PageId_100110110;

            if (LoginHelper.IsAdmin())
            {
                caseSearchCondition.PageId = Dchien.Legal.Entity.System.PageId.PageId_1001103100;
            }

            caseSearchCondition.Sorting = "T.LawfulDay";
            model.Top10Cases = CaseSearchService.Instance.GetCaseList(caseSearchCondition);
            model.Top10Cases = model.Top10Cases.OrderBy(x => x.Basic.LawfulDay).ToList();

            caseSearchCondition = new Dchien.Legal.Entity.Legal.Case.CaseSearchCondition();

            caseSearchCondition.PageNo = 1;
            caseSearchCondition.PageSize = 13;
            caseSearchCondition.Sorting = "T.CaseRegisterDate desc";

            caseSearchCondition.PageId = Dchien.Legal.Entity.System.PageId.PageId_100110110;

            if (LoginHelper.IsAdmin())
            {
                caseSearchCondition.PageId = Dchien.Legal.Entity.System.PageId.PageId_1001103100;
            }

            model.New10Cases = CaseSearchService.Instance.GetCaseList(caseSearchCondition);
            model.New10Cases = model.New10Cases.OrderByDescending(x => x.Basic.CaseRegisterDate).ToList();

            //待缴官费
            var serach1 = new Dchien.Legal.Entity.FAM.AR.CaseFee.CaseFeeSearchCondition();
            serach1.PageId = Entity.System.PageId.PageId_5001010002;
            serach1.PageNo = 1;
            serach1.PageSize = 1;
            serach1.UserId = LoginHelper.GetUserName();
            serach1.HasUnPaidOfficeFee = true;
            var caseList1 = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.GetCaseFeeList(serach1);
            model.CaseOfficeFee1_Counts = serach1.TotalCount;

            //待退费
            var serach2 = new Dchien.Legal.Entity.FAM.AR.CaseFee.CaseFeeSearchCondition();
            if (CommonService.Instance.CheckPermission(long.Parse(Entity.System.PageId.PageId_1001103010)))
            {
                serach2.PageId = Entity.System.PageId.PageId_5001010001;
                serach2.CompanyId = LoginHelper.GetCompanyId();

            }
            else
            {
                serach2.UserId = LoginHelper.GetUserName();
                serach2.PageId = Entity.System.PageId.PageId_5001010003;
            }
             
            serach2.PageNo = 1;
            serach2.PageSize = 1;
          
            serach2.HasRefundFee = true;
            var caseList2 = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.GetCaseFeeList(serach2);
            model.CaseOfficeFee2_Counts = serach2.TotalCount;

            //补充证据
            var serach3 = new CaseSearchCondition();
            serach3.PageId = Entity.System.PageId.PageId_1001104030;
            serach3.PageNo = 1;
            serach3.PageSize = 1;
            var caseList3 = CaseSearchService.Instance.GetCaseList(serach3);
            model.CaseOfficeFee3_Counts = serach3.TotalCount;

            //补充意见
            var serach4 = new CaseSearchCondition();
            serach4.PageId = Entity.System.PageId.PageId_1001104040;
            serach4.PageNo = 1;
            serach4.PageSize = 1;
            var caseList4 = CaseSearchService.Instance.GetCaseList(serach4);
            model.CaseOfficeFee4_Counts = serach4.TotalCount;

            //待上诉
            var serach5 = new CaseSearchCondition();
            serach5.PageId = Entity.System.PageId.PageId_1001104050;
            serach5.PageNo = 1;
            serach5.PageSize = 1;
            var caseList5 = CaseSearchService.Instance.GetCaseList(serach5);
            model.CaseOfficeFee5_Counts = serach5.TotalCount;

            //待执行
            var serach6 = new CaseSearchCondition();
            serach6.PageId = Entity.System.PageId.PageId_1001104060;
            serach6.PageNo = 1;
            serach6.PageSize = 1;
            var caseList6 = CaseSearchService.Instance.GetCaseList(serach6);
            model.CaseOfficeFee6_Counts = serach6.TotalCount;

            //紧急案件
            var serach7 = new CaseSearchCondition();
            serach7.PageId = Entity.System.PageId.PageId_1001104070;
            serach7.PageNo = 1;
            serach7.PageSize = 1;
            var caseList7 = CaseSearchService.Instance.GetCaseList(serach7);
            model.CaseOfficeFee7_Counts = serach7.TotalCount;


            //var prePaidAmount = Dchien.Legal.Service.FCM.Contract.ContractService.Instance.GetContractPrePaidAmount(LoginHelper.GetUserName());

            var serach8 = new Entity.CRM.Customer.CustomerSearchCondition();
            serach8.BusinessOwner = LoginHelper.GetUserName();
            serach8.PageNo = 1;
            serach8.PageSize = 1;

            Dchien.Legal.Service.CRM.Customer.CustomerService.Instance.GetTotalCaseFeeAmount(serach8);
            model.TotalUnCashedCaseOfficeFeeAmount = serach8.TotalUnCashedCaseOfficeFeeAmount;
            model.TotalUnCashedCaseNonOfficeFeeAmount = serach8.TotalUnCashedCaseNonOfficeFeeAmount;

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult Dashboard()
        {
            var response = new PostResponse();

            try
            {
                var model = new DashboardModel();


                var caseCounts = CaseSearchService.Instance.GetCaseCountGroupbyCasePhase(LoginHelper.IsAdmin() ? Entity.System.PageId.PageId_1001103100 : Entity.System.PageId.PageId_100110110, (int)CaseType.CaseType_110);

                model.CaseType_110_Counts = caseCounts.Find(x => x.Item1.CasePhaseId == (int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101010) == null ?
                                            0 : caseCounts.Find(x => x.Item1.CasePhaseId == (int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101010).Item2;
                model.CaseType_120_Counts = caseCounts.Find(x => x.Item1.CasePhaseId == (int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101011) == null ?
                                            0 : caseCounts.Find(x => x.Item1.CasePhaseId == (int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101011).Item2;
                model.CaseType_130_Counts = caseCounts.Find(x => x.Item1.CasePhaseId == (int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_1010140) == null ?
                                            0 : caseCounts.Find(x => x.Item1.CasePhaseId == (int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_1010140).Item2;
                model.CaseType_140_Counts = caseCounts.Find(x => x.Item1.CasePhaseId == (int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_1020120) == null ?
                                            0 : caseCounts.Find(x => x.Item1.CasePhaseId == (int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_1020120).Item2;

                model.CaseType_150_Counts = caseCounts.Find(x => x.Item1.CasePhaseId == (int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_1030110) == null ?
                                            0 : caseCounts.Find(x => x.Item1.CasePhaseId == (int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_1030110).Item2;

                model.CaseType_160_Counts = caseCounts.Find(x => x.Item1.CasePhaseId == (int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_1040110) == null ?
                                0 : caseCounts.Find(x => x.Item1.CasePhaseId == (int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_1040110).Item2;



                #region 最近10天案件量

                model.To10DayCaseCounts = CaseSearchService.Instance.GetCaseCountGroupbyDay();
                model.To10DayCaseCounts = model.To10DayCaseCounts.OrderBy(x => x.Item1).ToList();

                #endregion

                response.IsSuccess = true;
                response.Data = model;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "DashboardController.Dashboard", "DashboardController.Dashboard", ex);
                response.IsSuccess = false;
                response.Message = "查询出错";
            }
            return Json(response);
        }

    }
}