using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.CRM.Customer;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Web.Areas.IPR.ViewModels.Case;
using Dchien.Legal.Web.Areas.CRM.ViewModels.Customer;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.CRM.LawFirm;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.ServiceStack.Common.Extensions;


namespace Dchien.Legal.Web.Areas.IPR.Controllers
{
    [CheckUserLogin]
    public class CaseCustomerController : BaseController
    {
        internal Log Logger = new Log("IPR.Controllers.CaseCustomerController");

        #region 案件客户

        public ActionResult CaseCustomerSelected(long caseId,string customerNames)
        {
            var model = new CaseCustomerSelectedModel();
            model.CaseId = caseId;
            model.SearchCondition = new CustomerSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 10;
            return PartialView("CaseCustomerSelected", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerIds"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseCustomerList(List<long> customerIds)
        {
            var caseModel = new CaseCustomerListModel();
            if (customerIds.Any())
            {
                caseModel.CaseCustomers = CustomerService.Instance.GetCaseCustomersByIds(customerIds);
            }

            return PartialView("CaseCustomerList", caseModel);
        }

        [HttpPost]
        public JsonResult GetCaseCustomers(long caseId)
        {
            var response = new PostResponse();
            response.Data = CaseService.Instance.GetCaseCustomers(caseId);
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseCustomerListSelected(CaseCustomerSelectedModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 10;

                model.SearchCondition.IsActived = true;

                var result = new BizCustomerSearchResultInfo();

                if (LoginHelper.GetAccesslevel() == (int)Dchien.Legal.Entity.Account.AccessLevel.All)
                {
                    model.SearchCondition.CompanyId = LoginHelper.GetCompanyId();
                }
                else if (LoginHelper.GetAccesslevel() == (int)Dchien.Legal.Entity.Account.AccessLevel.Group)
                {
                    model.SearchCondition.DepartmentId = LoginHelper.GetDepartmentId();
                }
                else if (LoginHelper.GetAccesslevel() == (int)Dchien.Legal.Entity.Account.AccessLevel.Team)
                {
                    model.SearchCondition.DepartmentId = LoginHelper.GetDepartmentId();
                }
                else
                {
                    model.SearchCondition.UserIds = new List<int>();
                    model.SearchCondition.UserIds.Add(LoginHelper.GetUserId());
                }

                result.Customers = CustomerService.Instance.GetCustomers(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message + " || " + ex.StackTrace;
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="customerIds"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CreateCaseCustomer(long caseId, int[] customerIds)
        {
            var response = new PostResponse();
            CaseService.Instance.CreateCaseCustomer(caseId, customerIds.ToList());

            response.Data = "";
            response.IsSuccess = true;
            return Json(response);

        }

        #endregion

        #region 查看客户 

        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult Customer(long? customerId = 0)
        {
            var model = new CreateUpdateModel();

            if (customerId.HasValue && customerId.Value > 0)
            {
                model.Customer = CustomerService.Instance.GetCustomerById(customerId.Value);
            }
            else
            {
                model.Customer = new BizCustomer();
                model.Customer.CustomerBasic = new BizCustomerBasic();
                model.Customer.License = new BizCustomerFile();
                model.Customer.License.FileName = FileHelper.HttpCustomerLincenseTemplateFile;
            }

            return PartialView("Customer", model);
        }

        #endregion


        [CheckUserLogin]
        [HttpPost]
        public ActionResult CaseContactsList(long? caseId, int? pageNo, int? pageSize)
        {
            var model = new CaseCustomerContactsSelectedModel();
            model.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            model.PageSize = pageSize.HasValue ? pageSize.Value : 15;

            if (caseId.HasValue && caseId > 0)
            {
                model.CaseId = caseId.Value;
                model.ContactsList = new List<BizCustomerContacts>();
                var lst = CaseCustomerService.Instance.GetCaseCustomerContactsList(caseId.Value);
               var customerContactsList = Dchien.Legal.Service.CRM.Customer.ContactsService.Instance.GetCustomerContacts(lst.FindAll(x=>x.Item1 == (int)Dchien.Legal.Entity.IPR.Case.CaseCustomerContactsType.Document).Select(x=>x.Item2).ToList());

                if (customerContactsList.Any())
                {
                    customerContactsList.ForEach(x => {
                        x.ContactsType = Dchien.Legal.Entity.IPR.Case.CaseCustomerContactsType.Document;
                        x.ContactsTypeName = x.ContactsType.ToDescription();
                    });
                    model.ContactsList.AddRange(customerContactsList);
                }

                var customerContactsList2 = Dchien.Legal.Service.CRM.Customer.ContactsService.Instance.GetCustomerContacts(lst.FindAll(x => x.Item1 == (int)Dchien.Legal.Entity.IPR.Case.CaseCustomerContactsType.Technology).Select(x => x.Item2).ToList());

                if (customerContactsList2.Any())
                {
                    customerContactsList2.ForEach(x => {
                        x.ContactsType = Dchien.Legal.Entity.IPR.Case.CaseCustomerContactsType.Technology;
                        x.ContactsTypeName = x.ContactsType.ToDescription();
                    });
                    model.ContactsList.AddRange(customerContactsList2);
                }
               
                model.TotalCount = model.ContactsList.Count;
                model.ContactsList = model.ContactsList.Any()
                    ? model.ContactsList.Skip(model.PageSize * (model.PageNo - 1))
                        .Take(model.PageSize)
                        .OrderByDescending(x => x.ContactsId)
                        .ToList()
                    : new List<BizCustomerContacts>();
            }

            return PartialView("CaseContactsList", model);
        }


        [CheckUserLogin]
        [HttpPost]
        public ActionResult CaseCustomerContactsSelected(long customerId)
        {
            var model = new CaseCustomerContactsSelectedModel();
            model.ContactsList = Dchien.Legal.Service.CRM.Customer.ContactsService.Instance.GetCustomerContacts(customerId);
            return PartialView("CaseCustomerContactsSelected", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="customerId"></param>
        /// <param name="documentContactsIds"></param>
        /// <param name="technologyContactsIds"></param>
        /// <returns></returns>
        public ActionResult CreateCaseCustomerContacts(long caseId, long customerId, long[] documentContactsIds, long[] technologyContactsIds)
        {
            var response = new PostResponse();

            var documentContactsIdList = documentContactsIds == null ? new List<long>() : documentContactsIds.ToList();
            var technologyContactsIdList = technologyContactsIds == null ? new List<long>() : technologyContactsIds.ToList();

            CaseService.Instance.CreateCaseCustomerContacts(caseId, customerId, documentContactsIdList, technologyContactsIdList);

            response.Data = "";
            response.IsSuccess = true;
            return Json(response);

        }
    }
}
