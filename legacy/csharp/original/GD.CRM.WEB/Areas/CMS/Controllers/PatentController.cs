using System;
using System.Web.Mvc;
using Dchien.Legal.BizModel.CMS.Contract;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.CMS.Contract;
using Dchien.Legal.Entity.System.AuditFlow;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CMS.Contract;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Web.Areas.CMS.ViewModels.Patent;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.CMS.Controllers
{
    [CheckUserLogin]
    public class PatentController : Controller
    {
        internal Log Logger = new Log("CMS.Controllers.PatentController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        public ActionResult Draft(long? id)
        {
            var model = new ContractModel();

            model.ContractDate = DateTime.Now;
            model.BusinessOwner = LoginHelper.GetUserChName();

            model.BCustomer = CompanyService.Instance.GetCompany();
            model.BCustomer.Contracts = LoginHelper.GetUserChName();

            if (id.HasValue)
            {
                model.ACustomer = CustomerService.Instance.GetCustomerById(id.Value);
            }
            else
            {
                model.ACustomer = new BizCustomer();
                model.ACustomer.DefaultContacts = new BizCustomerContacts();
            }

            return View(model);
        }

        [HttpPost]
        public JsonResult Create(ContractModel model,bool isSubmit)
        {
            var response = new PostResponse();

            model.Contract.ContractBasicInfo = new BizContractBasic();

            model.Contract.ContractBasicInfo.ContractNo = ContractService.Instance.GenerateContractNo();

            model.Contract.ContractBasicInfo.CustomerId = model.ACustomer.CustomerId;
            model.Contract.ContractBasicInfo.CustomerNo = model.ACustomer.CustomerNo;
            model.Contract.ContractBasicInfo.ContractName = model.ACustomer.CustomerName + "_国内专利代理长期合同";
            model.Contract.ContractBasicInfo.BusinessOwner =LoginHelper.GetUserName();
            model.Contract.ContractBasicInfo.ContractType = (int)ContractType.PI;
            model.Contract.ContractBasicInfo.ContractMoney = 0;
            model.Contract.ContractBasicInfo.TaxRate = 0;
            model.Contract.ContractBasicInfo.ContractStatus = isSubmit ? ContractStatus.P : ContractStatus.D;
            model.Contract.ContractBasicInfo.AuditFlowId = AuditFlowNodeEntity.DEFAULT_FLOWID;
            model.Contract.ContractBasicInfo.ContractBeginDate = DateTime.Now;
            model.Contract.ContractBasicInfo.ContractEndDate = DateTime.Now.AddYears(20);
            model.Contract.ContractBasicInfo.AuditDate = DateTime.Now;
            model.Contract.ContractBasicInfo.Remark = model.Remark;
            model.Contract.ContractBasicInfo.IsChanged = false;
            model.Contract.ContractBasicInfo.IsActived = true;
            model.Contract.ContractBasicInfo.Submiter = LoginHelper.GetUserName();

            ContractService.Instance.Create(model.Contract, model.ACustomer, model.BCustomer, model.ContractScope);

            return  Json(response);
        }
    }
}