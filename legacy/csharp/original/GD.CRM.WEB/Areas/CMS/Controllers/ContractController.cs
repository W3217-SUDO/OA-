using System;
using System.Collections.Generic;
using System.Web.Mvc;

using Dchien.Legal.BizModel.CMS.Contract;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.CMS.Contract;
using Dchien.Legal.Entity.CMS.Contract.Audit;
using Dchien.Legal.Entity.System.AuditFlow;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CMS.Contract;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Web.Areas.Account.ViewModels.UserCenter;
using Dchien.Legal.Web.Areas.CMS.ViewModels.Contract;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.CMS.Controllers
{
    [CheckUserLogin]
    public class ContractController : Controller
    {
        internal Log Logger = new Log("CMS.Controllers.ContractController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ContractList(int? id)
        {
            var model = new ListModel();
            
            model.SearchCondition = new ContractSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 20;
            if (id.HasValue)
            {
                model.SearchCondition.ContractStatus = (ContractStatus)id.Value;
            }
            else
            {
                model.SearchCondition.ContractStatus = ContractStatus.P;
            }
            return View(model);
        }

        [HttpPost]
        public JsonResult ToAudit(long contractId)
        {
            var response = new PostResponse();

            var contract = ContractService.Instance.GetContractById(contractId);

            contract.ContractBasicInfo.ContractStatus = ContractStatus.P;

            bool result = ContractService.Instance.ToAudit(contract);

            if (result)
            {
                response.Message = "提交成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "提交失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #region 合同列表

        [CheckUserLogin]
        public ActionResult DraftList()
        {
            var model = new ListModel();

            model.SearchCondition = new ContractSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 20;
            model.SearchCondition.ContractStatus = ContractStatus.D;
            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult DraftList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 20;

                model.SearchCondition.ContractStatus = ContractStatus.D;
                model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();

                var result = new BizContractSearchResultInfo();

                result.ContractList = ContractService.Instance.GetContractList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error("ContractController.PendingList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        [HttpPost]
        public JsonResult PendingList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 20;

                model.SearchCondition.ContractStatus = ContractStatus.P;
                model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();

                var result = new BizContractSearchResultInfo();

                result.ContractList = ContractService.Instance.GetContractList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error("ContractController.PendingList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        [HttpPost]
        public JsonResult ApprovedList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 20;

                model.SearchCondition.ContractStatus = ContractStatus.A;
                model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();

                var result = new BizContractSearchResultInfo();

                result.ContractList = ContractService.Instance.GetContractList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error("ContractController.ApprovedList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        [HttpPost]
        public JsonResult RejectedList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 20;

                model.SearchCondition.ContractStatus = ContractStatus.R;
                model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();

                var result = new BizContractSearchResultInfo();

                result.ContractList = ContractService.Instance.GetContractList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error("ContractController.RejectedList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        [HttpPost]
        public JsonResult GeneralLedgerList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 20;

                model.SearchCondition.ContractStatus = ContractStatus.A;

                var result = new BizContractSearchResultInfo();

                result.ContractList = ContractService.Instance.GetContractList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error("ContractController.GeneralLedgerList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        #endregion

        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
        public JsonResult GetBasicContractListByCustomerId(long customerId)
        {
            var response = new PostResponse();

            try
            {
                response.Data = ContractService.Instance.GetBasicContractListByCustomerId(customerId);
                response.IsSuccess = true;
            }
            catch (Exception ex)
            {
                Logger.Error("ContractController.ContractList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ContractType(long customerId)
        {
            var model = new ContractTypeModel();
            model.CustomerId = customerId;
            return PartialView(model);
        }

        [CheckUserLogin]
        public ActionResult Draft(long? id)
        {
            var model = new DraftModel ();

            if (id.HasValue)
            {
                model.Contract = new BizContract();
                model.Contract.ContractBasicInfo = new BizContractBasic();

                var customer = CustomerService.Instance.GetCustomerById(id.Value);
                if (customer != null)
                {
                    model.Contract.ContractBasicInfo.CustomerId = customer.CustomerId;
                    model.Contract.ContractBasicInfo.CustomerName = customer.CustomerName;
                    model.Contract.ContractBasicInfo.CustomerNo = customer.CustomerNo;
                }
            }
            return View(model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        private PostResponse CheckCaseFileUploading()
        {
            var response = new PostResponse();

            if (Request.Files == null || Request.Files.Count == 0)
            {
                response.Message = "请选择文件进行上传.";
                response.IsSuccess = false;
                return response;
            }

            var file = Request.Files[0];

            if (file == null)
            {
                response.Message = "请选择文件进行上传.";
                response.IsSuccess = false;
                return response;
            }

            if (file.ContentLength == 0)
            {
                response.Message = "文件没有任何内容.";
                response.IsSuccess = false;
                return response;
            }
 
            return null;

        }

        [HttpPost]
        public JsonResult DraftCreate(DraftModel model)
        {
           var response = new PostResponse();

            byte[] firstFileBytes = null;

            var firstFileName = string.Empty;

            if (Request.Files.Count > 0)
            {
                var firstFile = Request.Files[0];
                int fileSize = firstFile.ContentLength;
                firstFileBytes = new byte[fileSize];
                firstFileName = firstFile.FileName;
                using (var stream = firstFile.InputStream)
                {
                    stream.Read(firstFileBytes, 0, fileSize);
                }
            }

            byte[] secondFileBytes = null;

            var secondFileName = string.Empty;

            if (Request.Files.Count > 1)
            {
                var secondFile = Request.Files[1];
                int secondFileSize = secondFile.ContentLength;
                secondFileBytes = new byte[secondFileSize];
                secondFileName = secondFile.FileName;
                using (var stream = secondFile.InputStream)
                {
                    stream.Read(secondFileBytes, 0, secondFileSize);
                }
            }

            model.Contract.ContractBasicInfo.ContractNo = ContractService.Instance.GenerateContractNo();
            model.Contract.ContractBasicInfo.BusinessOwner = LoginHelper.GetUserName();
            model.Contract.ContractBasicInfo.ContractType = (int)Dchien.Legal.Entity.CMS.Contract.ContractType.OTH;
            model.Contract.ContractBasicInfo.ContractMoney = 0;
            model.Contract.ContractBasicInfo.TaxRate = 0;
            model.Contract.ContractBasicInfo.ContractStatus = ContractStatus.A;
            model.Contract.ContractBasicInfo.AuditFlowId = AuditFlowNodeEntity.DEFAULT_FLOWID;
            model.Contract.ContractBasicInfo.ContractBeginDate = DateTime.Now;
            model.Contract.ContractBasicInfo.ContractEndDate = DateTime.Now.AddYears(20);
            model.Contract.ContractBasicInfo.AuditDate = DateTime.Now;
            //model.Contract.ContractBasicInfo.Remark = model.Remark;
            model.Contract.ContractBasicInfo.IsChanged = false;
            model.Contract.ContractBasicInfo.IsActived = true;
            model.Contract.ContractBasicInfo.Submiter = LoginHelper.GetUserName();

            model.Contract.ContractFileList = new List<BizContractFile>();

            if (firstFileBytes != null)
            {
                var contractFirstFile = new BizContractFile();
                contractFirstFile.ContractNo = model.Contract.ContractBasicInfo.ContractNo;
                contractFirstFile.FileBytes = firstFileBytes;
                contractFirstFile.FileName = firstFileName;

                model.Contract.ContractFileList.Add(contractFirstFile);
            }

            if (secondFileBytes != null)
            {
                var contractSecondFile = new BizContractFile();
                contractSecondFile.ContractNo = model.Contract.ContractBasicInfo.ContractNo;
                contractSecondFile.FileBytes = secondFileBytes;
                contractSecondFile.FileName = secondFileName;
                model.Contract.ContractFileList.Add(contractSecondFile);
            }

            bool result = ContractService.Instance.Create(model.Contract);

            if (result)
            {
                response.Data = model.Contract.ContractBasicInfo.ContractNo;
                response.Message = string.Format("合同创建成功，合同编号{0}.", model.Contract.ContractBasicInfo.ContractNo);
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "合同创建失败.";
                response.IsSuccess = false;
            }

            return Json(response);
        }

    }
}
