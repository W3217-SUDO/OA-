using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Web;
using System.Web.Mvc;


using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Entity.CRM.Customer;
using Dchien.Legal.Web.Areas.CRM.ViewModels.Customer;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.Legal.Case;
using log4net.Repository.Hierarchy;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.CRM.Controllers
{
    [CheckUserLogin]
    public class CustomerController : Controller
    {
        internal Log Logger = new Log("CRM.Controllers.CustomerController");

        #region 客户列表


        [CheckUserLogin]
        public ActionResult CustomerList(long id)
        {
            var menus = MenuService.Instance.GetMenusByCurrentUser();

            if ((id.ToString() == PageId.PageId_6001001
                || id.ToString() == PageId.PageId_6001002
                || id.ToString() == PageId.PageId_6001003
                || id.ToString() == PageId.PageId_6001004
                || id.ToString() == PageId.PageId_6001005
                || id.ToString() == PageId.PageId_6001006
                || id.ToString() == PageId.PageId_6001007
                || id.ToString() == PageId.PageId_6001008
                || id.ToString() == PageId.PageId_6001009
                || id.ToString() == PageId.PageId_6001010
               ) && menus.Any(x => x.MenuCode == id.ToString()))
            {
                var model = new ListModel();

                model.SearchCondition = new CustomerSearchCondition();
                model.SearchCondition.PageNo = 1;
                model.SearchCondition.PageSize = 15;

                model.SearchCondition.PageId = id.ToString();

                if (id.ToString() == PageId.PageId_6001001
                || id.ToString() == PageId.PageId_6001002)
                {
                    model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
                    model.SearchCondition.BusinessOwnerName = LoginHelper.GetUserChName();
                }

                return View(model);
            }

            return new RedirectResult("~/NoPermission.html?" + id.ToString());
        }

        [CheckUserLogin]
        public ActionResult CustomerPublicList(long id)
        {
            if ((id.ToString() == PageId.PageId_6001011))
            {
                var model = new ListModel();

                model.SearchCondition = new CustomerSearchCondition();
                model.SearchCondition.PageNo = 1;
                model.SearchCondition.PageSize = 15;
                model.SearchCondition.PageId = id.ToString();

                return View(model);
            }

            return new RedirectResult("~/NoPermission.html?" + id.ToString());
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
        public JsonResult List(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizCustomerSearchResultInfo();

                model.SearchCondition.IsActived = true;
                model.SearchCondition.IsShared = false;
                model.SearchCondition.IsOpened = false;

                var id = model.SearchCondition.PageId;

                if ((id.ToString() == PageId.PageId_6001001))
                {
                    model.SearchCondition.IsShared = null;
                    //我的客户
                     model.SearchCondition.UserIds = new List<int>();
                     model.SearchCondition.UserIds.Add(LoginHelper.GetUserId());
                }
                else if ((id.ToString() == PageId.PageId_6001002))
                {
                    //个人回收站
                     model.SearchCondition.UserIds = new List<int>();
                     model.SearchCondition.UserIds.Add(LoginHelper.GetUserId());
                     model.SearchCondition.IsActived = false;
                }
                else if ((id.ToString() == PageId.PageId_6001003))
                {
                    //部门客户
                     model.SearchCondition.DepartmentId = LoginHelper.GetDepartmentId();
                }
                else if ((id.ToString() == PageId.PageId_6001004))
                {
                    //部门回收站
                     model.SearchCondition.DepartmentId = LoginHelper.GetDepartmentId();
                     model.SearchCondition.IsActived = false;
                }
                else if ((id.ToString() == PageId.PageId_6001005))
                {
                    //公司客户
                    model.SearchCondition.CompanyId = LoginHelper.GetCompanyId();
                    model.SearchCondition.IsActived = null;
                    model.SearchCondition.IsShared = null;
                    model.SearchCondition.IsOpened = null;
                }

                else if ((id.ToString() == PageId.PageId_6001010))
                {
                    //公司回收站
                    model.SearchCondition.CompanyId = LoginHelper.GetCompanyId();
                    model.SearchCondition.IsActived = false;
                }
                else if ((id.ToString() == PageId.PageId_6001006))
                {
                    //公海客户
                    model.SearchCondition.IsActived = false;
                    model.SearchCondition.IsOpened = true;
                }
                else if ((id.ToString() == PageId.PageId_6001007))
                {
                    //我的共享客户

                    model.SearchCondition.UserIds = new List<int>();
                    model.SearchCondition.UserIds.Add(LoginHelper.GetUserId());
                    model.SearchCondition.IsShared = true;
                }
                else if ((id.ToString() == PageId.PageId_6001008))
                {
                    model.SearchCondition.IsActived = null;
                    model.SearchCondition.IsShared = null;
                    model.SearchCondition.IsOpened = null;

                    model.SearchCondition.UserIds = new List<int>();
                    model.SearchCondition.UserIds.Add(LoginHelper.GetUserId());

                    //最近联系
                    model.SearchCondition.LastContactTimeBegin = DateTime.Now.AddMonths(-1);
                    model.SearchCondition.LastContactTimeEnd = DateTime.Now;
                }
                else if ((id.ToString() == PageId.PageId_6001009))
                {
                    model.SearchCondition.IsActived = null;
                    model.SearchCondition.IsShared = null;
                    model.SearchCondition.IsOpened = null;

                    model.SearchCondition.UserIds = new List<int>();
                    model.SearchCondition.UserIds.Add(LoginHelper.GetUserId());

                    //最近更新
                    model.SearchCondition.LastUpdateTimeBegin = DateTime.Now.AddMonths(-1);
                    model.SearchCondition.LastUpdateTimeEnd = DateTime.Now;
                }

                result.Customers = CustomerService.Instance.GetCustomers(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;

                result.TotalPaidCaseOfficeFeeAmount = model.SearchCondition.TotalPaidCaseOfficeFeeAmount;
                result.TotalCashedCaseOfficeFeeAmount = model.SearchCondition.TotalCashedCaseOfficeFeeAmount;
                result.TotalUnCashedCaseOfficeFeeAmount = model.SearchCondition.TotalUnCashedCaseOfficeFeeAmount;
                result.TotalDeficitCaseOfficeFeeAmount = model.SearchCondition.TotalDeficitCaseOfficeFeeAmount;
                result.TotalCaseNonOfficeFeeAmount = model.SearchCondition.TotalCaseNonOfficeFeeAmount;
                result.TotalCashedCaseNonOfficeFeeAmount = model.SearchCondition.TotalCashedCaseNonOfficeFeeAmount;
                result.TotalUnCashedCaseNonOfficeFeeAmount = model.SearchCondition.TotalUnCashedCaseNonOfficeFeeAmount;
                result.TotalCaseCommissionFeeAmount = model.SearchCondition.TotalCaseCommissionFeeAmount;
                result.TotalCashedCaseCommissionFeeAmount = model.SearchCondition.TotalCashedCaseCommissionFeeAmount;
                result.TotalPaidCaseCommissionFeeAmount = model.SearchCondition.TotalPaidCaseCommissionFeeAmount;
                result.TotalUnPaidCaseCommissionFeeAmount = model.SearchCondition.TotalUnPaidCaseCommissionFeeAmount;
                result.TotalInvoicedAmount = model.SearchCondition.TotalInvoicedAmount;
                result.TotalInvoiceOverAmount = model.SearchCondition.TotalInvoiceOverAmount;
                result.TotalUnInvoicedAmount = model.SearchCondition.TotalUnInvoicedAmount;

                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"CustomerController.List","CustomerController.List", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="keyWord"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CustomerList(string keyWord)
        {
            var response = new PostResponse();

            try
            {
                var result = new BizCustomerSearchResultInfo();

                result.Customers = CustomerService.Instance.SearchCustomer(keyWord);

                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CustomerController.CustomerList", "CustomerController.CustomerList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="keyWord"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult AllCustomerList(string keyWord)
        {
            var response = new PostResponse();

            try
            {
                var result = new BizCustomerSearchResultInfo();
                result.Customers = CustomerService.Instance.SearchAllCustomer(keyWord);
                response.Data = result;
                return new JsonResult()
                {
                    Data = response,
                    MaxJsonLength = int.MaxValue,
                    ContentType = "application/json"
                };
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CustomerController.CustomerList", "CustomerController.CustomerList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }
        #endregion

        #region 客户

        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerId"></param>
        /// <param name="customerSourceTypeId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CreateUpdate(long? customerId)
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
                model.Customer.CustomerBasic.CustomerGuid = Guid.NewGuid().ToString();
                model.Customer.CustomerExtend = new BizCustomerExtend();
                model.Customer.CustomerControlling = new BizCustomerControlling();
                model.Customer.CustomerControlling.InputDate = DateTime.Now;
                model.Customer.CustomerExtend.BusinessOwner = LoginHelper.GetUserName();
                model.Customer.CustomerExtend.BusinessOwnerName = LoginHelper.GetUserChName();
                model.Customer.CustomerControlling.Holder = LoginHelper.GetUserName();
                model.Customer.CustomerControlling.HolderName = LoginHelper.GetUserChName();
            }

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerId"></param>
        /// <param name="customerSourceTypeId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult View(long? customerId)
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
                model.Customer.CustomerBasic.CustomerGuid = Guid.NewGuid().ToString();
                model.Customer.CustomerExtend = new BizCustomerExtend();
                model.Customer.CustomerControlling = new BizCustomerControlling();
                model.Customer.CustomerControlling.InputDate = DateTime.Now;
                model.Customer.CustomerExtend.BusinessOwner = LoginHelper.GetUserName();
                model.Customer.CustomerExtend.BusinessOwnerName = LoginHelper.GetUserChName();
                model.Customer.CustomerControlling.Holder = LoginHelper.GetUserName();
                model.Customer.CustomerControlling.HolderName = LoginHelper.GetUserChName();
            }

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CustomerCreateUpdate(CreateUpdateModel model)
        {
            var response = new PostResponse();

            try
            {
                //model.Customer.CustomerBasic.CustomerTypeId = CustomerTypeId.Customer;
                bool result = CustomerService.Instance.CreateUpdate(model.Customer, model.Customer.CustomerExtend.BusinessOwner);

                if (result)
                {
                    response.Message = "保存成功！";
                    response.Data = model.Customer;
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

            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CustomerController.CustomerCreateUpdate", "CustomerController.CustomerCreateUpdate", ex);
                response.Message = "保存失败";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult CaseCustomerCreateUpdate(CreateUpdateModel model)
        {
            var response = new PostResponse();

            try
            {
                if (!model.Customer.CustomerBasic.CustomerId.HasValue)
                {
                    model.Customer.CustomerBasic.CustomerTypeId = CustomerTypeId.Applicant;
                    model.Customer.CustomerBasic.CustomerGuid = Guid.NewGuid().ToString();
                }

                var customer = model.Customer.CustomerBasic.CustomerId.HasValue ? CustomerService.Instance.GetCustomerById(model.Customer.CustomerBasic.CustomerId.Value) : model.Customer;

                customer.CustomerBasic.Zip = model.Customer.CustomerBasic.Zip;
                customer.CustomerBasic.ContactPhone = model.Customer.CustomerBasic.ContactPhone;
                customer.CustomerRegistration.OrganizationCode = model.Customer.CustomerRegistration.OrganizationCode;
                customer.CustomerRegistration.LicenseNo = model.Customer.CustomerRegistration.LicenseNo;
                customer.CustomerRegistration.AccountBankName = model.Customer.CustomerRegistration.AccountBankName;
                customer.CustomerRegistration.BankAccount = model.Customer.CustomerRegistration.BankAccount;
                customer.CustomerBasic.Province = model.Customer.CustomerBasic.Province;
                customer.CustomerBasic.City = model.Customer.CustomerBasic.City;
                customer.CustomerExtend.CustomerTypeName = model.Customer.CustomerExtend.CustomerTypeName;
                customer.CustomerRegistration.RegistrationAddress = model.Customer.CustomerRegistration.RegistrationAddress;
                customer.CustomerControlling.IsFeeReducing = model.Customer.CustomerControlling.IsFeeReducing;
                customer.CustomerExtend.IsAssisted = model.Customer.CustomerExtend.IsAssisted;

                bool result = CustomerService.Instance.CreateUpdate(customer);

                if (result)
                {
                    response.Message = "保存成功！";
                    response.Data = customer;
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

            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CustomerController.CustomerCreateUpdate", "CustomerController.CustomerCreateUpdate", ex);
                response.Message = "保存失败";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CustomerDelete(long customerId)
        {
            var response = new PostResponse();
            try
            {
                bool result = CustomerService.Instance.DeleteCustomer(customerId);
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CustomerController.CustomerDelete", "CustomerController.CustomerDelete", ex);
                response.Message = "删除失败";
                response.IsSuccess = false;
            }
            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult CustomerRestore(long customerId)
        {
            var response = new PostResponse();

            try
            {
                bool result = CustomerService.Instance.RestoreCustomer(customerId);

                if (result)
                {
                    response.Message = "恢复成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "恢复失败！";
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CustomerController.CustomerRestore", "CustomerController.CustomerRestore", ex);
                response.Message = "恢复失败";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult CustomerOpen(long customerId)
        {
            var response = new PostResponse();

            try
            {
                bool result = CustomerService.Instance.OpenCustomer(customerId);

                if (result)
                {
                    response.Message = "设定成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "设定失败！";
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CustomerController.CustomerOpen", "CustomerController.CustomerOpen", ex);
                response.Message = "设定失败";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult CustomerClose(long customerId)
        {
            var response = new PostResponse();

            try
            {
                bool result = CustomerService.Instance.CloseCustomer(customerId);

                if (result)
                {
                    response.Message = "拾回成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "拾回失败！";
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CustomerController.CustomerClose", "CustomerController.CustomerClose", ex);
                response.Message = "拾回失败";
                response.IsSuccess = false;
            }

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
        [HttpPost]
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

        [CheckUserLogin]
        public ActionResult ViewCustomer(string customerNo)
        {
            var model = new CreateUpdateModel();

            if (!string.IsNullOrEmpty(customerNo))
            {
                model.Customer = CustomerService.Instance.GetCustomerByNo(customerNo);
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

        #region 客户检索


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CustomerSearching()
        {
            var model = new CustomerSearchingModel();
            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerName"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CustomerQuery(string customerName)
        {
            var response = new PostResponse();

            try
            {
                var customer = CustomerService.Instance.GetCustomerBasicByName(customerName);

                if (customer == null)
                {
                    response.IsSuccess = true;
                }
                else
                {
                    var c = CaseService.Instance.GetCaseBasicByCustomerNo(customer.CustomerBasic.CustomerNo);
                    response.Data = new { Customer = customer , Case = c };
                    response.IsSuccess = true;
                }
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CustomerController.CustomerSearching", "CustomerController.CustomerSearching", ex);
                response.Message = "保存失败";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

    }
}
