using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;

using Dchien.ServiceStack.Common.Extensions;
using Dchien.Legal.BizModel.Legal.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Service;
using Dchien.Legal.Web.Areas.Legal.ViewModels.Case;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service.Legal.Case;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.Legal.Investigation.Clue;
using Dchien.Legal.Service.Legal.Investigation;
using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.BizModel.Legal.Investigation.Clue;


namespace Dchien.Legal.Web.Areas.Legal.Controllers
{
    [CheckUserLogin]
    public class CaseController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.CaseController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="taskId"></param>
        /// <returns></returns>
        public ActionResult CaseView(string id, string caseNo)
        {
            if (!string.IsNullOrEmpty(caseNo))
            {
                var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();
                model.Case = CaseService.Instance.GetCase(caseNo);

                if (model.Case == null)
                {
                    throw new Exception("未找到案件." + caseNo);
                }

                //return View("View2", model); // 顾问

               // return View("CivilDispute/View", model); //民事 行政 仲裁

                return View("View",model); // 刑事
            }
            return View("CreateUpdate");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseTypeId"></param>
        /// <returns></returns>
        public ActionResult Create(string id, long? contractId, int? caseTypeId)
        {
            var model = new CaseModel();
            model.Case = new BizCase();
            model.Case.Basic = new BizCaseBasic();

            if (contractId.HasValue)
            {
                var contract = ContractService.Instance.GetContractBasicById(contractId.Value);

                if (contract == null)
                {
                    throw new Exception("未找到合同.");
                }

                var customer = CustomerService.Instance.GetCustomerBasicByNo(contract.ContractBasicInfo.CustomerNo);

                if (customer == null)
                {
                    throw new Exception("未找到客户.");
                }

                model.Customer = customer;
                model.Contract = contract;
                model.Case.Basic.CustomerNo = customer.CustomerBasic.CustomerNo;
                model.Case.Basic.CustomerName = customer.CustomerBasic.CustomerName;
                model.Case.Basic.ContractNo = contract.ContractBasicInfo.ContractNo;

                model.ClueList = InvestigationClueService.Instance.GetNotUsedInvestigationClueListByIndicterNo(customer.CustomerBasic.CustomerNo);
            }

            if (caseTypeId.HasValue)
            {
                model.Case.Basic.CaseTypeId = (int)caseTypeId;
            }
            else
            {
                model.Case.Basic.CaseTypeId = (int)CaseType.CaseType_110;
            }

            model.Case.Basic.ConsultantBeginDate = DateTime.Now;
            model.Case.Basic.ConsultantEndDate = DateTime.Now.AddYears(1);

            return View("Create", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult CivilDispute()
        {
            var model = new CaseModel();
            model.Case = new BizCase();
            model.Case.Basic = new BizCaseBasic();
            model.Case.Basic.CaseTypeId = (int)CaseType.CaseType_110;
            return View("CivilDispute/CivilDispute", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <param name="caseTypeId"></param>
        /// <returns></returns>
        //public ActionResult Create(long? contractId,int caseTypeId)
        //{
        //    var model = new CaseModel();
        //    model.Case = new BizCase();
        //    model.Case.Basic = new BizCaseBasic();

        //    if (contractId.HasValue)
        //    {
        //        var contract = ContractService.Instance.GetContractBasicById(contractId.Value);

        //        if (contract == null)
        //        {
        //            throw new Exception("未找到合同.");
        //        }

        //        var customer = CustomerService.Instance.GetCustomerBasicByNo(contract.ContractBasicInfo.CustomerNo);

        //        if (customer == null)
        //        {
        //            throw new Exception("未找到客户.");
        //        }

        //        model.Customer = customer;
        //        model.Contract = contract;
        //        model.Case.Basic.CustomerNo = customer.CustomerBasic.CustomerNo;
        //        model.Case.Basic.CustomerName = customer.CustomerBasic.CustomerName;
        //        model.Case.Basic.ContractNo = contract.ContractBasicInfo.ContractNo;

        //        model.ClueList = InvestigationClueService.Instance.GetInvestigationClueListByIndicterNo(customer.CustomerBasic.CustomerNo);
        //    }
           
        //    model.Case.Basic.CaseTypeId = caseTypeId;
        //    return View("CivilDispute/CivilDispute", model);
        //}

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CaseCreateUpdate(CaseModel model)
        {
            var response = new PostResponse();

            try
            {
                
                bool result = CaseService.Instance.CreateUpdate(model.Case);

                if (result)
                {
                    response.Data =  new { CaseNo = model.Case.Basic.CaseNo };

                    response.Message = "保存成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "保存失败！";
                    response.IsSuccess = false;
                }
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNo"></param>
        /// <returns></returns>

        [HttpPost]
        public ActionResult CaseBasicEdit(string id, string caseNo)
        {
            if (!string.IsNullOrEmpty(caseNo))
            {
                var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();
                model.Case = CaseService.Instance.GetCaseBasic(caseNo);

                if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_110)
                {
                    return PartialView("PartialView/CivilDisputeCase/CivilDisputeCase_Basic_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_120)
                {
                    return PartialView("PartialView/CriminalCase/CriminalCase_Basic_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_130)
                {
                    return PartialView("PartialView/AdministrativeCase/AdministrativeCase_Basic_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_140)
                {
                    return PartialView("PartialView/ConsultantCase/ConsultantCase_Basic_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_150)
                {
                    return PartialView("PartialView/ArbitrationCase/ArbitrationCase_Basic_Edit", model);
                }
            }

            throw new Exception("caseNo");

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CourtLawyerEdit(string id, string caseNo)
        {
            if (!string.IsNullOrEmpty(caseNo))
            {
                var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();
                model.Case = CaseService.Instance.GetCaseBasic(caseNo);

                if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_110)
                {
                    return PartialView("PartialView/CivilDisputeCase/CivilDisputeCase_CourtLawyer_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_120)
                {
                    return PartialView("PartialView/CriminalCase/CriminalCase_CourtLawyer_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_130)
                {
                    return PartialView("PartialView/AdministrativeCase/AdministrativeCase_CourtLawyer_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_140)
                {
                    return PartialView("PartialView/ConsultantCase/ConsultantCase_CourtLawyer_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_150)
                {
                    return PartialView("PartialView/ArbitrationCase/ArbitrationCase_CourtLawyer_Edit", model);
                }
            }

            throw new Exception("caseNo");

        }

        
        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CivilDisputeEdit(string id, string caseNo)
        {
            if (!string.IsNullOrEmpty(caseNo))
            {
                var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();
                model.Case = CaseService.Instance.GetCaseBasic(caseNo);
                return PartialView("CivilDispute/PartialView/Edit", model);
            }

            throw new Exception("caseNo");
           
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult LitigantEdit(string id, string caseNo)
        {
            if (!string.IsNullOrEmpty(caseNo))
            {
                var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();
                model.Case = CaseService.Instance.GetCaseBasic(caseNo);

                if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_110)
                {
                    return PartialView("PartialView/CivilDisputeCase/CivilDisputeCase_Litigant_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_120)
                {
                    return PartialView("PartialView/CriminalCase/CriminalCase_Litigant_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_130)
                {
                    return PartialView("PartialView/AdministrativeCase/AdministrativeCase_Litigant_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_140)
                {
                    return PartialView("PartialView/ConsultantCase/CriminalCase_Litigant_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_150)
                {
                    return PartialView("PartialView/ArbitrationCase/ArbitrationCase_Litigant_Edit", model);
                }
            }

            throw new Exception("caseNo");

        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult PublicSecurityUnitEdit(string id, string caseNo)
        {
            if (!string.IsNullOrEmpty(caseNo))
            {
                var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();
                model.Case = CaseService.Instance.GetCaseBasic(caseNo);
                return PartialView("PartialView/CriminalCase/CriminalCase_PublicSecurityUnit_Edit", model);
            }

            throw new ArgumentNullException("caseNo");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult FirstProcuratorateUnitEdit(string id, string caseNo)
        {
            if (!string.IsNullOrEmpty(caseNo))
            {
                var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();
                model.Case = CaseService.Instance.GetCaseBasic(caseNo);
                model.FirstInstace = true;
                model.SecondInstace = false;
                model.LastInstace = false;

                return PartialView("PartialView/CriminalCase/CriminalCase_ProcuratorateUnit_Edit", model);
            }

            throw new ArgumentNullException("caseNo");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult SecondProcuratorateUnitEdit(string id, string caseNo)
        {
            if (!string.IsNullOrEmpty(caseNo))
            {
                var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();
                model.Case = CaseService.Instance.GetCaseBasic(caseNo);
                model.FirstInstace = false;
                model.SecondInstace = true;
                model.LastInstace = false;

                return PartialView("PartialView/CriminalCase/CriminalCase_ProcuratorateUnit_Edit", model);
            }

            throw new ArgumentNullException("caseNo");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult LastProcuratorateUnitEdit(string id, string caseNo)
        {
            if (!string.IsNullOrEmpty(caseNo))
            {
                var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();
                model.Case = CaseService.Instance.GetCaseBasic(caseNo);
                model.FirstInstace = false;
                model.SecondInstace = false;
                model.LastInstace = true;

                return PartialView("PartialView/CriminalCase/CriminalCase_ProcuratorateUnit_Edit", model);
            }

            throw new ArgumentNullException("caseNo");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        public ActionResult Litigant(string id, string caseNo)
        {
            var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();

            if (!string.IsNullOrEmpty(caseNo))
            {
                model.Case = CaseService.Instance.GetCaseBasic(caseNo);

                if (model.Case.Basic.CustomerTypeId == (int)CaseCustomerType.Appellant)
                {
                    model.Case.Basic.AppellantNos = model.Case.Basic.CustomerNo;
                    model.Case.Basic.AppellantNames = model.Case.Basic.CustomerName;

                    model.Case.Basic.AppellantAgents = new List<BizCaseLitigantAgent>();

                    foreach (var lawyer in model.Case.Basic.CaseLawyerName.Split(','))
                    {
                        model.Case.Basic.AppellantAgents.Add(new BizCaseLitigantAgent() { Name = lawyer,Position = "律师", AgentAuthCode= "一般" });
                    }
                }
                else if (model.Case.Basic.CustomerTypeId == (int)CaseCustomerType.Appellee)
                {
                    model.Case.Basic.AppelleeNos = model.Case.Basic.CustomerNo;
                    model.Case.Basic.AppelleeNames = model.Case.Basic.CustomerName;

                    model.Case.Basic.AppelleeAgents = new List<BizCaseLitigantAgent>();

                    foreach (var lawyer in model.Case.Basic.CaseLawyerName.Split(','))
                    {
                        model.Case.Basic.AppelleeAgents.Add(new BizCaseLitigantAgent() { Name = lawyer, Position = "律师", AgentAuthCode = "一般" });
                    }
                }
                else if (model.Case.Basic.CustomerTypeId == (int)CaseCustomerType.TheThird)
                {
                    model.Case.Basic.TheThirdNos = model.Case.Basic.CustomerNo;
                    model.Case.Basic.TheThirdNames = model.Case.Basic.CustomerName;

                    model.Case.Basic.TheThirdAgents = new List<BizCaseLitigantAgent>();

                    foreach (var lawyer in model.Case.Basic.CaseLawyerName.Split(','))
                    {
                        model.Case.Basic.TheThirdAgents.Add(new BizCaseLitigantAgent() { Name = lawyer, Position = "律师", AgentAuthCode = "一般" });
                    }
                }

                model.FirstInstace = true;
                return View("PartialView/Litigant", model);
            }

            throw new Exception("案号为空.");
        }

        /// <summary>
        /// /
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        public ActionResult Court(string id, string caseNo)
        {
            var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();
            model.Case = CaseService.Instance.GetCase(caseNo);
            model.FirstInstace = true;

            return View("PartialView/Court", model);
        }

        [HttpPost]
        public ActionResult FirstCourtEdit(string id, string caseNo)
        {
            if (!string.IsNullOrEmpty(caseNo))
            {
                var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();
                model.Case = CaseService.Instance.GetCase(caseNo);
                model.FirstInstace = true;
                model.SecondInstace = false;
                model.LastInstace = false;
                model.ExecutionInstace = false;

                if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_110)
                {
                    return PartialView("PartialView/CivilDisputeCase/CivilDisputeCase_Court_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_120)
                {
                    return PartialView("PartialView/CriminalCase/CriminalCase_Court_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_130)
                {
                    return PartialView("PartialView/AdministrativeCase/AdministrativeCase_Court_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_140)
                {
                    return PartialView("PartialView/ConsultantCase/CriminalCase_Court_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_150)
                {
                    return PartialView("PartialView/ArbitrationCase/ArbitrationCase_Court_Edit", model);
                }
              
            }

            throw new Exception("caseNo");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult SecondCourtEdit(string id, string caseNo)
        {
            if (!string.IsNullOrEmpty(caseNo))
            {
                var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();
                model.Case = CaseService.Instance.GetCase(caseNo);
                model.FirstInstace = false;
                model.SecondInstace = true;
                model.LastInstace = false;
                model.ExecutionInstace = false;

                if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_110)
                {
                    return PartialView("PartialView/CivilDisputeCase/CivilDisputeCase_Court_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_120)
                {
                    return PartialView("PartialView/CriminalCase/CriminalCase_Court_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_130)
                {
                    return PartialView("PartialView/AdministrativeCase/AdministrativeCase_Court_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_140)
                {
                    return PartialView("PartialView/ConsultantCase/CriminalCase_Court_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_150)
                {
                    return PartialView("PartialView/ArbitrationCase/ArbitrationCase_Court_Edit", model);
                }

                //return PartialView("CivilDispute/PartialView/CourtEdit", model);
            }

            throw new Exception("caseNo");
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult ExecutionCourtEdit(string id, string caseNo)
        {
            if (!string.IsNullOrEmpty(caseNo))
            {
                var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();
                model.Case = CaseService.Instance.GetCase(caseNo);
                model.FirstInstace = false;
                model.SecondInstace = false;
                model.ExecutionInstace = true; 
                model.LastInstace = false;

                if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_110)
                {
                    return PartialView("PartialView/CivilDisputeCase/CivilDisputeCase_Court_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_120)
                {
                    return PartialView("PartialView/CriminalCase/CriminalCase_Court_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_130)
                {
                    return PartialView("PartialView/AdministrativeCase/AdministrativeCase_Court_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_140)
                {
                    return PartialView("PartialView/ConsultantCase/CriminalCase_Court_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_150)
                {
                    return PartialView("PartialView/ArbitrationCase/ArbitrationCase_Court_Edit", model);
                }

                //return PartialView("CivilDispute/PartialView/CourtEdit", model);
            }

            throw new Exception("caseNo");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult LastCourtEdit(string id, string caseNo)
        {
            if (!string.IsNullOrEmpty(caseNo))
            {
                var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();
                model.Case = CaseService.Instance.GetCase(caseNo);
                model.FirstInstace = false;
                model.SecondInstace = false;
                model.LastInstace = true;
                model.ExecutionInstace = false;

                if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_110)
                {
                    return PartialView("PartialView/CivilDisputeCase/CivilDisputeCase_Court_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_120)
                {
                    return PartialView("PartialView/CriminalCase/CriminalCase_Court_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_130)
                {
                    return PartialView("PartialView/AdministrativeCase/AdministrativeCase_Court_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_140)
                {
                    return PartialView("PartialView/ConsultantCase/CriminalCase_Court_Edit", model);
                }
                else if (model.Case.Basic.CaseTypeId == (int)CaseType.CaseType_150)
                {
                    return PartialView("PartialView/ArbitrationCase/ArbitrationCase_Court_Edit", model);
                }

                //return PartialView("CivilDispute/PartialView/CourtEdit", model);
            }

            throw new Exception("caseNo");
        }

        [HttpPost]
        public ActionResult SettlementAmountEdit(string id, string caseNo)
        {
            if (!string.IsNullOrEmpty(caseNo))
            {
                var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();
                model.Case = CaseService.Instance.GetCase(caseNo);
                return PartialView("CivilDispute/PartialView/SettlementAmountEdit", model);
            }

            throw new Exception("caseNo");
        }

        /// <summary>
        /// 仓库位置修改
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult NotarialNoEdit(string id, string caseNo)
        {
            if (!string.IsNullOrEmpty(caseNo))
            {
                var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();
                model.Case = CaseService.Instance.GetCase(caseNo);
                return PartialView("PartialView/CivilDisputeCase/CivilDisputeCase_NotarialNo_Edit", model);
            }

            throw new Exception("caseNo");
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult NotarialNoCreateUpdate(CaseModel model)
        {
            var response = new PostResponse();

            try
            {
                bool result = CaseService.Instance.UpdateNotarialNo(model.Case);

                if (result)
                {
                    response.Data = new { CaseNo = model.Case.Basic.CaseNo };

                    response.Message = "保存成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "保存失败！";
                    response.IsSuccess = false;
                }
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
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
        public JsonResult CourtLawyerCreateUpdate(CaseModel model)
        {
            var response = new PostResponse();

            try
            {
                bool result = CaseService.Instance.UpdateCourtLawyer(model.Case);

                if (result)
                {
                    response.Data = new { CaseNo = model.Case.Basic.CaseNo };

                    response.Message = "保存成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "保存失败！";
                    response.IsSuccess = false;
                }
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }

            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult CourtCreateUpdate(CaseModel model)
        {
            var response = new PostResponse();

            try
            {
                bool result = CaseService.Instance.UpdateCourt(model.Case);

                if (result)
                {
                    response.Data = new { CaseNo = model.Case.Basic.CaseNo };

                    response.Message = "保存成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "保存失败！";
                    response.IsSuccess = false;
                }
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
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
        public JsonResult ProcuratorateUnitCreateUpdate(CaseModel model)
        {
            var response = new PostResponse();

            try
            {
                bool result = CaseService.Instance.UpdateProcuratorateUnit(model.Case);

                if (result)
                {
                    response.Data = new { CaseNo = model.Case.Basic.CaseNo };

                    response.Message = "保存成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "保存失败！";
                    response.IsSuccess = false;
                }
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
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
        public JsonResult PublicSecurityUnitCreateUpdate(CaseModel model)
        {
            var response = new PostResponse();

            try
            {
                bool result = CaseService.Instance.UpdatePublicSecurityUnit(model.Case);

                if (result)
                {
                    response.Data = new { CaseNo = model.Case.Basic.CaseNo };

                    response.Message = "保存成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "保存失败！";
                    response.IsSuccess = false;
                }
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }

            return Json(response);
        }


        [HttpPost]
        [CheckUserLogin]
        public JsonResult LitigantCreateUpdate(CaseModel model)
        {
            var response = new PostResponse();

            try
            {
                bool result = CaseService.Instance.UpdateLitigant(model.Case);

                if (result)
                {
                    response.Data = new { CaseNo = model.Case.Basic.CaseNo };

                    response.Message = "保存成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "保存失败！";
                    response.IsSuccess = false;
                }
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }

            return Json(response);
        }


        [HttpPost]
        [CheckUserLogin]
        public JsonResult SettlementAmountCreateUpdate(CaseModel model)
        {
            var response = new PostResponse();

            try
            {
                bool result = CaseService.Instance.UpdateSettlementAmount(model.Case);

                if (result)
                {
                    response.Data = new { CaseNo = model.Case.Basic.CaseNo };

                    response.Message = "保存成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "保存失败！";
                    response.IsSuccess = false;
                }
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }

            return Json(response);
        }


        [CheckUserLogin]
        [HttpPost]
        public ActionResult QuickCreate()
        {
             return PartialView("QuickCreate");
        }


        [HttpPost]
        public JsonResult CaseDelete(List<string> caseNos)
        {
            var response = new PostResponse();

            try
            {
                bool result = CaseService.Instance.DeleteCase(caseNos);

                if (result)
                {
                    response.Message = "删除成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "删除失败！";
                    response.IsSuccess = false;
                }

            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseController.CaseDelete", "CaseController.CaseDelete", ex);
                throw;
            }

            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult ParticipantEdit(string caseNos)
        {
            var model = new ParticipantEditModel();
            model.CaseNos = caseNos.Split(',').ToList();

            var c = CaseService.Instance.GetCaseBasic(model.CaseNos[0]);

            model.CaseTypeId = c.Basic.CaseTypeId;

            return PartialView("CivilDispute/PartialView/ParticipantEdit", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult ParticipantUpdate(ParticipantEditModel model)
        {
            var response = new PostResponse();

            try
            {
                bool result = CaseService.Instance.UpdateMultipleCase(model.CaseNos, model.CourtLawyers,model.CaseLawyers,model.CaseAssistants, model.BusinessOwners,model.CasePhaseId,model.LitigationAmount);

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
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }

            return Json(response);
        }


        [HttpPost]
        [CheckUserLogin]
        public ActionResult ClueToCase(string id, string investigationClueNos)
        {
            var model = new CaseModel();
          
           var investigationClueNo = investigationClueNos.Split(',')[0];

            if (string.IsNullOrEmpty(investigationClueNos))
            {
                throw new ArgumentNullException("investigationClueNos");
            }
            var clueNos = new List<string>();
            var hasDoneClueNos = new List<string>();

            investigationClueNos.Split(',').ToList().ForEach(clueNo =>
            {
                var c = CaseService.Instance.GetCaseBasicByClueNo(clueNo);

                if (c == null)
                {
                    clueNos.Add(clueNo);
                }
                else
                {
                    hasDoneClueNos.Add(clueNo);
                }
            });

            model.InvestigationClueNos = clueNos.Join(",");

            if (hasDoneClueNos.Any())
            {
                model.ErrorMessage = hasDoneClueNos.Join(",") + "已生成过案件.";
            }

            model.Case = new BizCase();
            model.Case.Basic = new BizCaseBasic();

            var clue = InvestigationClueService.Instance.GetInvestigationClueBasic(investigationClueNo);
            var investigation = InvestigationService.Instance.GetInvestigation(clue.Basic.InvestigationNo);
            var investigationTask = InvestigationTaskService.Instance.GetInvestigationTask(clue.Basic.InvestigationTaskNo);

            var customer = CustomerService.Instance.GetCustomerBasicByNo(investigation.Basic.Indicter);

            if (customer == null)
            {
                throw new Exception("未找到客户.");
            }

            model.Customer = customer;
            model.Case.Basic.CustomerNo = customer.CustomerBasic.CustomerNo;
            model.Case.Basic.CustomerName = customer.CustomerBasic.CustomerName;
            model.Case.Basic.Investigator = investigationTask.Basic.Investigator;
            model.Case.Basic.InvestigatorName = investigationTask.Basic.InvestigatorName;

            model.ContractList = ContractService.Instance.GetBasicContractListByCustomerNo(customer.CustomerBasic.CustomerNo);
            model.ClueList = InvestigationClueService.Instance.GetNotUsedInvestigationClueListByIndicterNo(customer.CustomerBasic.CustomerNo);

            model.Case.Basic.CaseTypeId = (int)investigation.Basic.CaseTypeId;
            return PartialView("CivilDispute/PartialView/ClueToCase", model);

        }

        [HttpPost]
        [CheckUserLogin]
        public ActionResult ClueToCaseList()
        {
            return PartialView("CivilDispute/PartialView/ClueToCaseList");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult ClueToCaseCreateUpdate(CaseModel model, List<string> investigationClueNos)
        {
            var response = new PostResponse();
            var caseList = new List<BizCase>();
            if (investigationClueNos != null && investigationClueNos.Any())
            {
                investigationClueNos.ForEach(clueNo =>
                {
                    try
                    {
                        var clue = InvestigationClueService.Instance.GetInvestigationClueBasic(clueNo);
                        var investigation = InvestigationService.Instance.GetInvestigation(clue.Basic.InvestigationNo);
                        var investigationTask = InvestigationTaskService.Instance.GetInvestigationTask(clue.Basic.InvestigationTaskNo);

                        BizCase c = null;

                        if (!string.IsNullOrEmpty(clue.Basic.AuditNeedMergeCaseNo))
                        {
                            c = CaseService.Instance.GetCase(clue.Basic.AuditNeedMergeCaseNo);

                            if (c != null)
                            {
                                c.Basic.InvestigationClueNos = string.IsNullOrEmpty(c.Basic.InvestigationClueNos) ? clueNo : c.Basic.InvestigationClueNos + "," + clueNo;
                                c.Basic.Investigator = string.IsNullOrEmpty(c.Basic.Investigator) ?
                                                                                  (!string.IsNullOrEmpty(clue.Basic.Investigators) ? clue.Basic.BusinessOwner + "," + clue.Basic.Investigators : clue.Basic.BusinessOwner)
                                                    : c.Basic.Investigator + "," + (!string.IsNullOrEmpty(clue.Basic.Investigators) ? clue.Basic.BusinessOwner + "," + clue.Basic.Investigators : clue.Basic.BusinessOwner);

                                c.Basic.InvestigatorName = string.IsNullOrEmpty(c.Basic.InvestigatorName) ?
                                                                                  (!string.IsNullOrEmpty(clue.Basic.InvestigatorNames) ? clue.Basic.BusinessOwnerName + "," + clue.Basic.InvestigatorNames : clue.Basic.BusinessOwnerName)
                                               : c.Basic.InvestigatorName + "," + (!string.IsNullOrEmpty(clue.Basic.InvestigatorNames) ? clue.Basic.BusinessOwnerName + "," + clue.Basic.InvestigatorNames : clue.Basic.BusinessOwnerName);
                            }

                        }

                        if (c == null)
                        {
                            c = new BizCase();
                            c.Basic = model.Case.Basic.TranslateTo<BizCaseBasic>();
                            c.Basic.CasePhaseId = (int)CasePhaseType.Phase_101001;
                            c.Basic.CaseNo = string.Empty;

                            c.Basic.CaseRegisterDate = DateTime.Now;
                            c.Basic.CaseTypeId = (int)CaseType.CaseType_110;
                            c.Basic.CaseRightTypeId = investigation.Basic.CaseTypeId;
                            c.Basic.CaseName = investigation.Basic.IndicterName + "_" + c.Basic.CauseName + "_" + clue.Basic.StoreName;
                            c.Basic.InvestigationClueNos = clueNo;

                            c.Basic.Investigator = string.IsNullOrEmpty(clue.Basic.Investigators) ? clue.Basic.BusinessOwner : clue.Basic.BusinessOwner + "," + clue.Basic.Investigators;
                            c.Basic.InvestigatorName = string.IsNullOrEmpty(clue.Basic.InvestigatorNames) ? clue.Basic.BusinessOwnerName : clue.Basic.BusinessOwnerName + "," + clue.Basic.InvestigatorNames;
                 
                        }

                        CaseService.Instance.CreateUpdate(c);
                        clue.Basic.CaseNo = c.Basic.CaseNo;
                        InvestigationClueService.Instance.BackFillCaseNo(clue);

                        caseList.Add(c);
                    }
                    catch (ApplicationException ex)
                    {
                        response.Message += ex.Message + "<br>";
                        response.IsSuccess = false;
                    }
                    catch (Exception ex)
                    {
                        response.Message += ex.Message + "<br>";
                        response.IsSuccess = false;
                    }
                });
            }

            response.Data = new { CaseList = caseList };
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="investigationClueNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult ClueGenerateCase(string id, string investigationClueNo)
        {
            var model = new CaseModel();
            model.Case = CaseService.Instance.GetCaseBasicByClueNo(investigationClueNo);

            if (model.Case == null)
            {
                model.Case = new BizCase();
                model.Case.Basic = new BizCaseBasic();
            }

            var clue = InvestigationClueService.Instance.GetInvestigationClueBasic(investigationClueNo);
            var investigation = InvestigationService.Instance.GetInvestigation(clue.Basic.InvestigationNo);
            var investigationTask = InvestigationTaskService.Instance.GetInvestigationTask(clue.Basic.InvestigationTaskNo);

            var customer = CustomerService.Instance.GetCustomerBasicByNo(investigation.Basic.Indicter);

            if (customer == null)
            {
                throw new Exception("未找到客户.");
            }

            model.InvestigationClueNo = clue.Basic.ClueNo;

            model.Customer = customer;
            model.Case.Basic.CustomerNo = customer.CustomerBasic.CustomerNo;
            model.Case.Basic.CustomerName = customer.CustomerBasic.CustomerName;
            model.Case.Basic.Investigator = investigationTask.Basic.Investigator;
            model.Case.Basic.InvestigatorName = investigationTask.Basic.InvestigatorName;

            model.ContractList = ContractService.Instance.GetBasicContractListByCustomerNo(customer.CustomerBasic.CustomerNo);
            model.ClueList = InvestigationClueService.Instance.GetNotUsedInvestigationClueListByIndicterNo(customer.CustomerBasic.CustomerNo);

            model.Case.Basic.CaseTypeId = (int)investigation.Basic.CaseTypeId; 
            return View("CivilDispute/PartialView/ClueGenerateCase", model);

            
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult ClueGenerateCaseLitigant(string id, string caseNo)
        {
            var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();

            if (!string.IsNullOrEmpty(caseNo))
            {
                model.Case = CaseService.Instance.GetCaseBasic(caseNo);

                if (model.Case.Basic.CustomerTypeId == (int)CaseCustomerType.Appellant)
                {
                    model.Case.Basic.AppellantNos = model.Case.Basic.CustomerNo;
                    model.Case.Basic.AppellantNames = model.Case.Basic.CustomerName;

                    model.Case.Basic.AppellantAgents = new List<BizCaseLitigantAgent>();

                    foreach (var lawyer in model.Case.Basic.CaseLawyerName.Split(','))
                    {
                        model.Case.Basic.AppellantAgents.Add(new BizCaseLitigantAgent() { Name = lawyer, Position = "律师", AgentAuthCode = "一般" });
                    }
                }
                else if (model.Case.Basic.CustomerTypeId == (int)CaseCustomerType.Appellee)
                {
                    model.Case.Basic.AppelleeNos = model.Case.Basic.CustomerNo;
                    model.Case.Basic.AppelleeNames = model.Case.Basic.CustomerName;

                    model.Case.Basic.AppelleeAgents = new List<BizCaseLitigantAgent>();

                    foreach (var lawyer in model.Case.Basic.CaseLawyerName.Split(','))
                    {
                        model.Case.Basic.AppelleeAgents.Add(new BizCaseLitigantAgent() { Name = lawyer, Position = "律师", AgentAuthCode = "一般" });
                    }
                }
                else if (model.Case.Basic.CustomerTypeId == (int)CaseCustomerType.TheThird)
                {
                    model.Case.Basic.TheThirdNos = model.Case.Basic.CustomerNo;
                    model.Case.Basic.TheThirdNames = model.Case.Basic.CustomerName;

                    model.Case.Basic.TheThirdAgents = new List<BizCaseLitigantAgent>();

                    foreach (var lawyer in model.Case.Basic.CaseLawyerName.Split(','))
                    {
                        model.Case.Basic.TheThirdAgents.Add(new BizCaseLitigantAgent() { Name = lawyer, Position = "律师", AgentAuthCode = "一般" });
                    }
                }

                model.FirstInstace = true;
                return View("CivilDispute/PartialView/Litigant", model);
            }

            model.Case = new BizCase();
            model.Case.Basic = new BizCaseBasic();
           model.FirstInstace = true;
            return View("CivilDispute/PartialView/Litigant", model);
            //throw new Exception("案号为空.");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult ClueGenerateCaseCourt(string id, string caseNo)
        {
            var model = new Dchien.Legal.Web.Areas.Legal.ViewModels.Case.CaseModel();
            model.Case = new BizModel.Legal.Case.BizCase();
            model.Case.Basic = new BizModel.Legal.Case.BizCaseBasic();
            model.Case.Basic.CaseNo = caseNo;
            model.Case.Basic.CaseTypeId = (int)CaseType.CaseType_110;
            model.FirstInstace = true;

            return View("CivilDispute/PartialView/Court", model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
        public ActionResult Merge()
        {
            return PartialView("PartialView/Merge");
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult Merged(string orgCaseNo,string destCaseNo)
        {
            var response = new PostResponse();

            try
            {

                var destCase = CaseService.Instance.GetCaseBasic(destCaseNo);

                if (destCase == null)
                {
                    response.Message = "未找到待合并的案件，请确认输入的案号正确！";
                    response.IsSuccess = false;
                    return Json(response);
                }

                var orgCase = CaseService.Instance.GetCaseBasic(orgCaseNo);

                if (destCase.Basic.CustomerNo == destCase.Basic.CustomerNo)
                {
                    response.Message = "待合并案号的客户与本案件的客户不一致，不允许操作.";
                    response.IsSuccess = false;
                }

                bool result = CaseService.Instance.Merge(orgCase, destCase);

                if (result)
                {
                    response.Message = "合并成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "合并失败！";
                    response.IsSuccess = false;
                }
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }

            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CasePhaseTypeChange(List<string> caseNos, int casePhaseId)
        {
            var response = new PostResponse();

            try
            {
                var casePhaseList = CaseService.Instance.UpdateMultipleCase(caseNos,new List<string>(),new List<string>(),new List<string>(),new List<string>(),casePhaseId,null);
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseController.CasePhaseTypeChange", "CaseController.CasePhaseTypeChange", ex);
                throw;
            }

            return Json(response);
        }

    }
}
