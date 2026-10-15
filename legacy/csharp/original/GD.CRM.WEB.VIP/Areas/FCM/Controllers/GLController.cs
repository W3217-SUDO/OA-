using System;
using System.Collections.Generic;
using System.Linq;
using System.Linq.Expressions;
using System.Web.Mvc;
using Dchien.Legal.BizModel.CMS.Contract;
using Dchien.Legal.BizModel.FAS.AP.CaseFee;
using Dchien.Legal.BizModel.CMS.GL;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.CMS.Contract;
using Dchien.Legal.Entity.FAS.AR;
using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.Service.CMS.Contract;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Web.Areas.CMS.ViewModels.Contract;
using Dchien.Legal.Web.Areas.CMS.ViewModels.GL;
using Dchien.Legal.Web.Controllers;
using BizCaseFee = Dchien.Legal.BizModel.FAS.AR.CaseFee.BizCaseFee;

namespace Dchien.Legal.Web.Areas.FCM.Controllers
{
    [CheckUserLogin]
    public class GLController : Controller
    {
        internal Log Logger = new Log("FCM.Controllers.GLController");

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult Index(long contractId)
        {
            var indexModel = new IndexModel();

            indexModel.Contract = ContractService.Instance.GetContractById(contractId);
            indexModel.Customer = CustomerService.Instance.GetCustomerById(indexModel.Contract.ContractBasicInfo.CustomerId.Value);
            indexModel.ARCaseFeeList =
                Dchien.Legal.Service.FAS.AR.CaseFee.CaseFeeService.Instance.GetCaseFeeList(contractId);

            indexModel.APCaseFeeList =
                Dchien.Legal.Service.FAS.AP.CaseFee.CaseFeeService.Instance.GetCaseFeeList(contractId);

            indexModel.GeneralLedger = new BizGeneralLedger();

            var caseOfficeFeeTypes = CaseTypeService.Instance.GetAllCaseFeeTypes().FindAll(x => x.TypeId == CaseFeeTypeId.Office);
            var caseNonOfficeFeeTypes = CaseTypeService.Instance.GetAllCaseFeeTypes().FindAll(x => x.TypeId == CaseFeeTypeId.NonOffice);
            var caseCommissionFeeTypes = CaseTypeService.Instance.GetAllCaseFeeTypes().FindAll(x => x.TypeId == CaseFeeTypeId.Commission);

            //合同总金额
            indexModel.GeneralLedger.TotalAmount = indexModel.ARCaseFeeList.FindAll(x=> x.Amount.HasValue).Sum(x => x.Amount);
            //官费合计
            indexModel.GeneralLedger.ARCaseOfficeFeeAmount = indexModel.ARCaseFeeList.FindAll(x => caseOfficeFeeTypes.Any(f => f.FeeTypeId == x.CaseFeeTypeId) && x.Amount.HasValue).Sum(x => x.Amount);
            //代理费合计
            indexModel.GeneralLedger.ARCaseNonOfficeFeeAmount = indexModel.ARCaseFeeList.FindAll(x => caseNonOfficeFeeTypes.Any(f => f.FeeTypeId == x.CaseFeeTypeId) && x.Amount.HasValue).Sum(x => x.Amount);
            //回款累计
            indexModel.GeneralLedger.CashedAmount = indexModel.ARCaseFeeList.FindAll(x => x.CashedAmount.HasValue).Sum(x => x.Amount);

            var caseFeeAppliedList = Dchien.Legal.Service.FAS.AR.CaseFee.CaseFeeAppliedService.Instance.GetCaseFeeAppliedList(indexModel.Contract.ContractBasicInfo.ContractNo);

            //回款次数
            indexModel.GeneralLedger.CashedTimes = caseFeeAppliedList == null ? 0 : caseFeeAppliedList.Count;

            //已付官费	
            indexModel.GeneralLedger.PaidCaseOfficeFeeAmount = indexModel.APCaseFeeList.FindAll(x => caseOfficeFeeTypes.Any(f => f.FeeTypeId == x.CaseFeeTypeId) && x.PaidAmount.HasValue).Sum(x => x.PaidAmount);
            //应付官费
            indexModel.GeneralLedger.APCaseOfficeFeeAmount = indexModel.APCaseFeeList.FindAll(x => caseOfficeFeeTypes.Any(f => f.FeeTypeId == x.CaseFeeTypeId) && x.Amount.HasValue).Sum(x => x.Amount) - indexModel.GeneralLedger.PaidCaseOfficeFeeAmount;

            //应付提成
            indexModel.GeneralLedger.APCommissionAmount = indexModel.APCaseFeeList.FindAll(x => caseCommissionFeeTypes.Any(f => f.FeeTypeId == x.CaseFeeTypeId) && x.Amount.HasValue).Sum(x => x.Amount);
            //已付提成	
            indexModel.GeneralLedger.PaidAPCommissionAmount = indexModel.APCaseFeeList.FindAll(x => caseCommissionFeeTypes.Any(f => f.FeeTypeId == x.CaseFeeTypeId) && x.CashedAmount.HasValue).Sum(x => x.Amount);

            //应收账款
            indexModel.GeneralLedger.ARCaseFeeAmount = indexModel.GeneralLedger.TotalAmount - indexModel.ARCaseFeeList.FindAll(x => x.CashedAmount.HasValue).Sum(x => x.CashedAmount);

            //应开票额
            indexModel.GeneralLedger.InvoiceAmount = 0;

            //已开票额
            indexModel.GeneralLedger.InvoicedAmount = 0;

            return View(indexModel);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
        public ActionResult ARCaseFeeList(long contractId,int? pageNo, int? pageSize)
        {
            var model = new ARCaseFeeListModel();
            model.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            model.PageSize = pageSize.HasValue ? pageSize.Value : 15;

            model.CaseFeeList = Dchien.Legal.Service.FAS.AR.CaseFee.CaseFeeService.Instance.GetCaseFeeList(contractId);

            model.TotalCount = model.CaseFeeList.Count;
            model.CaseFeeList = model.CaseFeeList.Any()
                ? model.CaseFeeList.Skip(model.PageSize * (model.PageNo - 1))
                    .Take(model.PageSize)
                    .ToList()
                : new List<Dchien.Legal.BizModel.FAS.AR.CaseFee.BizCaseFee>();

            return PartialView("PartialView/ARCaseFeeList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
       [HttpPost]
        public ActionResult APCaseFeeList(long contractId,int? pageNo, int? pageSize)
        {
            var model = new APCaseFeeListModel();
            model.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            model.PageSize = pageSize.HasValue ? pageSize.Value : 15;
            model.CaseFeeList = Dchien.Legal.Service.FAS.AP.CaseFee.CaseFeeService.Instance.GetCaseFeeList(contractId);

            model.TotalCount = model.CaseFeeList.Count;
            model.CaseFeeList = model.CaseFeeList.Any()
                ? model.CaseFeeList.Skip(model.PageSize * (model.PageNo - 1))
                    .Take(model.PageSize)
                    .ToList()
                : new List<Dchien.Legal.BizModel.FAS.AP.CaseFee.BizCaseFee>();

            return PartialView("PartialView/APCaseFeeList", model);
        }

        [CheckUserLogin]
        public ActionResult List(int? Id)
        {
            var model = new ListModel();
            model.SearchCondition = new ContractSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 20;
            model.SearchCondition.ContractStatus = ContractStatus.A;
            return View(model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult InvoiceList()
        {
            var model = new InvoiceListModel();

            model.InvoiceList = new List<BizInvoice>();

            return PartialView("PartialView/InvoiceList", model);
        }

 
      
        
    }
}
