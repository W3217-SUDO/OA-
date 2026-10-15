
var contracts = {
    ApprovedList: function() {
        $("#postForm").ajaxPost(AP_ROOT + "CMS/ContractAudit/ApprovedList", function(response) {
            if (response.IsSuccess) {
                $("tbody", "#tblContractList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.ContractList, function(i, c) {
                        $("tbody", "#tblContractList").addRow(
                            i + 1,
                            c.ContractBasicInfo.ContractNo,
                            "<span style='width: 200px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.ContractBasicInfo.CustomerName + "</span>",
                            "<span style='width: 200px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.ContractBasicInfo.ContractName + "</span>",
                            c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                            c.ContractBasicInfo.ContractStateName,
                            c.ContractBasicInfo.BusinessOwnerName,
                            c.CurrectContractFlowAudit.AuditorName,
                            "<a href='javascript:void(0)' onclick='javascript:contracts.ViewContractFile(" + c.ContractBasicInfo.ContractId + ")'>合同附件</a> &nbsp; ",
                            "<a href='javascript:void(0)' onclick='javascript:contracts.ContractFlowAudit.ViewAudit(" + c.ContractBasicInfo.ContractId + ",\"" + c.ContractBasicInfo.ContractNo + "\")'>审批信息</a> &nbsp; "
                        );
                    });

                    $("tfoot", "#tblContractList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.contractlist").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: contracts.List,
                        callBackArgs: null
                    });
                } else {

                    $("tfoot", "#tblContractList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },
    RejectedList: function() {
        $("#postForm").ajaxPost(AP_ROOT + "CMS/ContractAudit/RejectedList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblContractList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.ContractList, function(i, c) {
                        $("tbody", "#tblContractList").addRow(
                            i + 1,
                            c.ContractBasicInfo.ContractNo,
                            "<span style='width: 200px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.ContractBasicInfo.CustomerName + "</span>",
                            "<span style='width: 200px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.ContractBasicInfo.ContractName + "</span>",
                            c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                            c.ContractBasicInfo.ContractStateName,
                            c.ContractBasicInfo.BusinessOwnerName,
                            c.CurrectContractFlowAudit.AuditorName,
                            "<a href='javascript:void(0)' onclick='javascript:contracts.ViewContractFile(" + c.ContractBasicInfo.ContractId + ")'>合同附件</a> &nbsp; ",
                            "<a href='javascript:void(0)' onclick='javascript:contracts.ContractFlowAudit.ViewAudit(" + c.ContractBasicInfo.ContractId + ",\"" + c.ContractBasicInfo.ContractNo + "\")'>审批信息</a> &nbsp; "
                        );
                    });

                    $("tfoot", "#tblContractList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.contractlist").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: contracts.List,
                        callBackArgs: null
                    });
                } else {

                    $("tfoot", "#tblContractList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },
    PendingList: function() {
        $("#postForm").ajaxPost(AP_ROOT + "CMS/ContractAudit/PendingList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblContractList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.ContractList, function(i, c) {
                        $("tbody", "#tblContractList").addRow(
                            i + 1,
                            c.ContractBasicInfo.ContractNo,
                            "<span style='width: 200px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.ContractBasicInfo.CustomerName + "</span>",
                            "<span style='width: 200px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.ContractBasicInfo.ContractName + "</span>",
                            c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                            c.ContractBasicInfo.ContractStateName,
                            c.ContractBasicInfo.BusinessOwnerName,
                            c.CurrectContractFlowAudit.AuditorName,
                            "<a href='javascript:void(0)' onclick='javascript:contracts.ViewContractFile(" + c.ContractBasicInfo.ContractId + ")'>合同附件</a> &nbsp; ",
                            "<a href='javascript:void(0)' onclick='javascript:contracts.ContractFlowAudit.Open(" + c.ContractBasicInfo.ContractId + ",\"" + c.ContractBasicInfo.ContractNo + "\")'>审批</a> &nbsp; "
                        );
                    });

                    $("tfoot", "#tblContractList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.contractlist").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: contracts.List,
                        callBackArgs: null
                    });
                } else {

                    $("tfoot", "#tblContractList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    OpenGL: function(contractId) {
        window.location = AP_ROOT + "CMS/GL?contractId=" + contractId;
    },

    /*审核*/
    ContractFlowAudit: {

        ViewAudit: function (contractId, contractNo) {

            var data =
            {
                contractId: contractId,
                contractNo: contractNo
            };

            var url = AP_ROOT + "CMS/ContractAudit/ContractFlowAuditList";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#contractFlowAuditListModal').modal({ backdrop: 'static', keyboard: false });
                $('#contractFlowAuditListModal').on('hidden.bs.modal', function () {
                    $("#contractFlowAuditListModal").remove();
                });
            });

        },

        AuditClose: function () {
            $('#contractFlowAuditListModal').modal('hide');
        },

        /*审核信息*/
        Open: function (contractId, contractNo) {

            var data =
            {
                contractId: contractId,
                contractNo: contractNo
            };

            var url = AP_ROOT + "CMS/ContractAudit/ContractFlowAudit";
            $.openLoading();

            $("<div></div>").load(url, data, function(result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#contractFlowAuditModal').modal({ backdrop: 'static', keyboard: false });
                $('#contractFlowAuditModal').on('hidden.bs.modal', function () {
                    $("#contractFlowAuditModal").remove();
                });
            });

        },

        /*审核信息*/
        Close: function() {
            $('#contractFlowAuditModal').modal('hide');
        },
        CreateUpdate: function(auditStatus) {
            if ($("#ContractFlowAudit_AuditContent").val() == '') {
                $.showModalMessageBox("请输入审批内容");
                return false;
            }

            var data = {};

            data["ContractFlowAudit.AuditId"] = $("#AuditId").val();
            data["ContractFlowAudit.ContractId"] = $("#ContractId").val();
            data["ContractFlowAudit.ContractNo"] = $("#ContractNo").val();
            data["ContractFlowAudit.AuditContent"] = $("#ContractFlowAudit_AuditContent").val();
            data["ContractFlowAudit.AuditStatus"] = auditStatus;

            $.ajaxPost(AP_ROOT + "CMS/ContractAudit/ContractFlowAuditCreate", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("审批成功.");
                    $('#contractFlowAuditModal').modal('hide');
 
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
    },
};


$(document).ready(function () {
    $("#btnPendingSearch").click(function () {
        contracts.PendingList();
    });

    $("#btnRejectSearch").click(function () {
        contracts.RejectedList();
    });

    $("#btnApprovedSearch").click(function () {
        contracts.ApprovedList();
    });

    //$("#btnApprovedSearch").click(function () {
    //    contracts.ApprovedList();
    //});

    $("#btnContractFlowAuditClose,#btnContractFlowAuditCancel").die().live("click", function () {
        contracts.ContractFlowAudit.Close();
    });

    $("#btnContractFlowAuditApproved").die().live("click", function () {
        contracts.ContractFlowAudit.CreateUpdate(3);
    });

    $("#btnContractFlowAuditReject").die().live("click", function () {
        contracts.ContractFlowAudit.CreateUpdate(4);
    });

    $("#btnContractFlowAuditListClose,#btnContractFlowAuditListCancel").die().live("click", function () {
        contracts.ContractFlowAudit.AuditClose();
    });

});