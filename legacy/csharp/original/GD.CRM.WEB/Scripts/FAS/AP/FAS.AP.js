
function AssociateCustomer(div, ctlid, ctlname) {
    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;

    this.Customer = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") { return false; }
        var curobj = new Object();
        curobj.keyword = name;
        $.ajaxPost(AP_ROOT + "CRM/Customer/CustomerList", curobj, function (response) {
            $(div).find(".i_common_list").empty();
            if (response.IsSuccess) {
                if (response.Data) {
                    var html = "";
                    $.each(response.Data.Customers, function (i, c) {
                        html += '<a href="javascript:void(0)" customerid=' + c.CustomerId + ' >' + c.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").click(function () {
                        $(ctlid).val($(this).attr("customerId"));
                        $(ctlname).val($(this).text());
                        $(div).hide();
                    });
                }
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        }, false);

        $(div).css({
            "position": "absolute",
            "left": $(ctlname).position().left + 15,
            "top": $(ctlname).position().top + 110
        }).toggle();
    }

    $(ctlname).bind('keyup', { obj: this }, function (event) {
        if (event.keyCode == 38) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).prev().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).prev().addClass("hover");
                        $(hover).prev().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 40) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).next().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).next().addClass("hover");
                        $(hover).next().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 13) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    $(hover).click();
                }
            }
        } else {
            clearTimeout(event.data.obj.Event);
            event.data.obj.Event = setTimeout(function () { event.data.obj.Customer(event.data.obj); }, 500);
        }
    });

    $(ctlname).bind('blur', { obj: this }, function (event) {
        if ($(this).val() == "" || ($(this).val() == $(this).attr("mod-notice-tip"))) {
            event.data.obj.GlobalName = "";
            $(ctlid).val("");
        }
        if ($(ctlid).val() == "") {
            if ($(this).attr("mod-notice-tip")) {
                $(this).val($(this).attr("mod-notice-tip"));
            } else {
                $(this).val("");
            }
        }
        //        if (event.data.obj.GlobalName != "") {
        //            $(this).val(event.data.obj.GlobalName);
        //            $(ctlid).val(event.data.obj.GlobalID);
        //        }
    });

    return this;
}

var ap = {

    /*申请开票*/
    Application : {
        List: function () {
            $("#postForm").ajaxPost(AP_ROOT + "FAM/CaseFee/CaseFees", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblCaseFeeList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.CaseFeeList, function (i, c) {

                            $("tbody", "#tblCaseFeeList").addRow(
                                "<input type='checkbox' name='chkCaseFeeId' class='ng-pristine ng-valid' customerid='" + c.CustomerId + "' value='" + c.CaseFeeId + "'>",
                                "<a href='javascript:void(0)' onclick='javascript:caseFeeList.Open(" + c.CaseId + ")'>" + c.CaseNo + "</a>",
                                c.CaseRequestNo,
                                c.CustomerName,
                                c.CaseFeeTypeName,
                                c.Amount,
                                c.RequestUserName,
                                c.CashedAmount,
                                c.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.CashedDate)),
                                c.InformDate == null ? '' : getDate(convertJsonDateToJSDate(c.InformDate)),
                                c.CaseFeeDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseFeeDate)),
                                c.CaseFeeNo
                                );
                        });

                        $("tfoot", "#tblCaseFeeList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.caseFeeList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: ap.Application.List,
                            callBackArgs: null
                        });


                    } else {
                        $("tfoot", "#tblCaseFeeList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        CaseFeeList: function () {
            $("#postForm").ajaxPost(AP_ROOT + "FAM/CaseFee/CaseFeeList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblCaseFeeList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.CaseFeeList, function (i, c) {

                            var caseFeeFileId = c.CaseFeeFile == null ? '' : c.CaseFeeFile.FileId;
                            var caseFeeFileName = c.CaseFeeFile == null ? '' : c.CaseFeeFile.FileName;

                            $("tbody", "#tblCaseFeeList").addRow(
                                c.CaseFeeBasic.CustomerNo,
                                c.CaseFeeBasic.CustomerName,
                                c.CaseFeeBasic.CaseFeeAmount,
                                c.CaseFeeBasic.CustomerCompanyCode,
                                c.CaseFeeBasic.CustomerPhone,
                                c.CaseFeeBasic.CustomerBankName,
                                c.CaseFeeBasic.CustomerBankAccount,
                                c.CaseFeeBasic.CaseFeeDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseFeeBasic.CaseFeeDate)),
                                c.CaseFeeBasic.CaseFeeApplicantName,
                                c.CaseFeeBasic.CaseFeeStatusName,
                                "<a href='javascript:void(0)' onclick='javascript:caseFee.Processor.Open(\"" + c.CaseFeeBasic.CaseFeeId + "\",\"" + null + "\")'>发票信息</a> &nbsp; "+
                                "<a href='javascript:void(0)' onclick='javascript:caseFee.Auditor.Audit.ViewAudit(\"" + c.CaseFeeBasic.CaseFeeId + "\")'>审批信息</a> &nbsp; " +
                                "<a href='javascript:void(0)' onclick='javascript:caseFee.File.View(\"" + caseFeeFileId + "\",\"" + c.CaseFeeBasic.CustomerNo + "\",\"" + caseFeeFileName + "\")'>发票文件</a> &nbsp;"
                                );
                        });

                        $("tfoot", "#tblCaseFeeList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.caseFeeList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: ap.Application.CaseFeeList,
                            callBackArgs: null
                        });


                    } else {
                        $("tfoot", "#tblCaseFeeList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        Selected: function (e) {

            if ($(e).attr("checked") == "checked") {
                $.checkbox.all("chkCaseFeeId");
            } else {
                $.checkbox.not("chkCaseFeeId");
            }
        },
        Open: function () {

            var customerIds = new Array();

            $("input[name='chkCaseFeeId']:checked").each(
                function () {
                    if ($.inArray($(this).attr("customerid"), customerIds) > -1) {
                    } else {
                        customerIds.push($(this).attr("customerid"));
                    }
                }
            );

            if (customerIds.length > 1) {
                $.showModalMessageBox("客户不一致.");
                return false;
            }

            var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
            if (caseFeeIds.length == 0) {
                $.showModalMessageBox("请选择需要开票的应收账款.");
                return false;
            }

            var url = AP_ROOT + "FAM/CaseFee/Create";
            var data = {
                customerId: customerIds[0],
                caseFeeIds: caseFeeIds
            };

            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseFeeModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseFeeModal').on('hidden.bs.modal', function () {
                    $("#caseFeeModal").remove();
                });
            });
        },
        Close: function () {
            $('#caseFeeModal').modal('hide');
        },
        Create: function () {

            if ($("#CaseFee_CaseFeeBasic_CustomerName").val() == '') {
                $.showModalMessageBox("请输入客户名称.");
                return false;
            }
            if ($("#CaseFee_CaseFeeBasic_CustomerCompanyCode").val() == '') {
                $.showModalMessageBox("请输入客户纳税人识别码.");
                return false;
            }
            if ($("#CaseFee_CaseFeeBasic_CustomerBankName").val() == '') {
                $.showModalMessageBox("请输入客户开户银行.");
                return false;
            }
            if ($("#CaseFee_CaseFeeBasic_CustomerBankAccount").val() == '') {
                $.showModalMessageBox("请输入客户开户账号.");
                return false;
            }
            if ($("#CaseFee_CaseFeeBasic_CaseFeeDate").val() == '') {
                $.showModalMessageBox("请输入票据日期.");
                return false;
            }

            if ($("#CaseFee_CaseFeeBasic_DeliveryMode").val() == '2') {

                if ($("#CaseFee_CaseFeeBasic_DeliveryRecipients").val() == '') {
                    $.showModalMessageBox("请输入收件人");
                    return false;
                }
                if ($("#CaseFee_CaseFeeBasic_DeliveryAddress").val() == '') {
                    $.showModalMessageBox("请输入收件地址");
                    return false;
                }

                if ($("#CaseFee_CaseFeeBasic_DeliveryPhone").val() == '') {
                    $.showModalMessageBox("请输入收件电话");
                    return false;
                }
            }

            $("#caseFeeForm").ajaxPost(AP_ROOT + "FAM/CaseFee/CaseFeeCreate", function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("开票申请成功.");
                    ap.Application.Close();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },
    },

    /*审批*/
    Auditor: {
        List: {
            PendingList: function() {
                $("#postForm").ajaxPost(AP_ROOT + "FAM/AP/PendingList", function (response) {
                    if (response.IsSuccess) {
                        $("tbody", "#tblCaseFeeList").clearRow();
                        if (response.Data.TotalItemCount > 0) {
                            $(".info_inall.layoutfix").show();
                            $.each(response.Data.CaseFeeList, function (i, c) {

                                $("tbody", "#tblCaseFeeList").addRow(
                                    "<input type='checkbox' name='chkApplicationId' class='ng-pristine ng-valid' value='" + c.Application.ApplicationId + "'>",
                                    c.CaseFeeTypeName,
                                    c.Amount,
                                    c.CaseNo,
                                    c.ContractNo,
                                    c.CustomerName,
                                    c.Application.ApplicationStatusName,
                                    c.Application.Audit.AuditorName,
                                    c.Application.ApplicantName,
                                    c.Application.ApplicationDate == null ? '' : getDate(convertJsonDateToJSDate(c.Application.ApplicationDate)),
                                    c.Application.ApplicationNo,
                                    c.Application.Remark,
                                    "<a href='javascript:void(0)' onclick='javascript:ap.Auditor.Audit.ViewAudit(\"" + c.Application.ApplicationId + "\")'>审批信息</a> &nbsp; " +
                                    "<a href='javascript:void(0)' onclick='javascript:ap.Auditor.Audit.Open(\"" + c.Application.Audit.AuditId + "\")'>审批</a> &nbsp; "
                                    );
                            });

                            $("tfoot", "#tblCaseFeeList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.caseFeeList").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: ap.Auditor.List.PendingList,
                                callBackArgs: null
                            });
                        } else {
                            $("tfoot", "#tblCaseFeeList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                    }
                });
            },
            ApprovedList: function () {
                $("#postForm").ajaxPost(AP_ROOT + "FAM/AP/ApprovedList", function (response) {
                    if (response.IsSuccess) {
                        $("tbody", "#tblCaseFeeList").clearRow();
                        if (response.Data.TotalItemCount > 0) {
                            $(".info_inall.layoutfix").show();
                            $.each(response.Data.CaseFeeList, function (i, c) {

                                $("tbody", "#tblCaseFeeList").addRow(
                                    "<input type='checkbox' name='chkApplicationId' class='ng-pristine ng-valid' value='" + c.Application.ApplicationId + "'>",
                                    c.CaseFeeTypeName,
                                    c.Amount,
                                    c.CaseNo,
                                    c.ContractNo,
                                    //c.InformDate == null ? '' : getDate(convertJsonDateToJSDate(c.InformDate)),
                                    //c.RequestUserName,
                                     c.CustomerName,
                                    c.Application.ApplicationStatusName,
                                    c.Application.Audit.AuditorName,
                                    c.Application.ApplicantName,
                                    c.Application.ApplicationDate == null ? '' : getDate(convertJsonDateToJSDate(c.Application.ApplicationDate)),
                                    c.Application.ApplicationNo,
                                    c.Application.Remark,
                                    "<a href='javascript:void(0)' onclick='javascript:ap.Auditor.Audit.ViewAudit(\"" + c.Application.ApplicationId + "\")'>审批信息</a> &nbsp; "
                                    );
                            });

                            $("tfoot", "#tblCaseFeeList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.caseFeeList").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: ap.Auditor.List.ApprovedList,
                                callBackArgs: null
                            });
                        } else {
                            $("tfoot", "#tblCaseFeeList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                    }
                });
            },
            RejectedList: function () {
                $("#postForm").ajaxPost(AP_ROOT + "FAM/AP/RejectedList", function (response) {
                    if (response.IsSuccess) {
                        $("tbody", "#tblCaseFeeList").clearRow();
                        if (response.Data.TotalItemCount > 0) {
                            $(".info_inall.layoutfix").show();
                            $.each(response.Data.CaseFeeList, function (i, c) {

                                $("tbody", "#tblCaseFeeList").addRow(
                                    "<input type='checkbox' name='chkApplicationId' class='ng-pristine ng-valid' value='" + c.Application.ApplicationId + "'>",
                                    c.CaseFeeTypeName,
                                    c.Amount,
                                    c.CaseNo,
                                    c.ContractNo,
                                    //c.InformDate == null ? '' : getDate(convertJsonDateToJSDate(c.InformDate)),
                                    //c.RequestUserName,
                                     c.CustomerName,
                                    c.Application.ApplicationStatusName,
                                    c.Application.Audit.AuditorName,
                                    c.Application.ApplicantName,
                                    c.Application.ApplicationDate == null ? '' : getDate(convertJsonDateToJSDate(c.Application.ApplicationDate)),
                                    c.Application.ApplicationNo,
                                    c.Application.Remark,
                                    "<a href='javascript:void(0)' onclick='javascript:ap.Auditor.Audit.ViewAudit(\"" + c.Application.ApplicationId + "\")'>审批信息</a> &nbsp; " 
                                    );
                            });

                            $("tfoot", "#tblCaseFeeList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.caseFeeList").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: ap.Auditor.List.RejectedList,
                                callBackArgs: null
                            });
                        } else {
                            $("tfoot", "#tblCaseFeeList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                    }
                });
            }
        },

        Audit: {
            Open: function (auditId) {
                var url = AP_ROOT + "FAM/AP/CaseFeeApplicationAudit";
 
                var data = {
                    auditId: auditId
                };

                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#caseFeeApplicationAuditModal').modal({ backdrop: 'static', keyboard: false });
                    $('#caseFeeApplicationAuditModal').on('hidden.bs.modal', function () {
                        $("#caseFeeApplicationAuditModal").remove();
                    });
                });
            },
            Close: function () {
                $('#caseFeeApplicationAuditModal').modal('hide');
            },
            CreateUpdate: function (auditStatus) {
                if ($("#CaseFeeAudit_AuditContent").val() == '') {
                    $.showModalMessageBox("请输入审批内容");
                    return false;
                }

                var data = {};

                data["Audit.AuditId"] = $("#Audit_AuditId").val();
                data["Audit.ApplicationId"] = $("#Audit_ApplicationId").val();
                data["Audit.AuditContent"] = $("#Audit_AuditContent").val();
                data["Audit.AuditStatus"] = auditStatus;

                $.ajaxPost(AP_ROOT + "FAM/AP/CaseFeeApplicationAuditCreate", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("审批成功.");
                        ap.Auditor.List.PendingList();
                        ap.Auditor.Audit.Close();
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },
            Approved: function () {
                ap.Auditor.Audit.CreateUpdate('A');
            },
            Rejected: function () {
                ap.Auditor.Audit.CreateUpdate('R');
            },
            ViewAudit: function (applicationId) {
                var data =
                {
                    applicationId: applicationId,
                };

                var url = AP_ROOT + "FAM/AP/CaseFeeApplicationAuditList";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#caseFeeApplicationAuditListModal').modal({ backdrop: 'static', keyboard: false });
                    $('#caseFeeApplicationAuditListModal').on('hidden.bs.modal', function () {
                        $("#caseFeeApplicationAuditListModal").remove();
                    });
                });
            },
            ViewAuditClose: function () {
                $('#caseFeeApplicationAuditListModal').modal('hide');
            },
        }
    },
}

$(document).ready(function () {

    $(document).click(function (e) {
        $("#divCasePhaseCheckBoxList").die().hide();
        $("#divCaseFeeTypeCheckBoxList").die().hide();
        $("#divUserList").die().hide();
    });

    var customter = new AssociateCustomer(
     $("#div_customer"),
     $("#CaseFeeSearchCondition_CustomerId"),
     $("#CaseFeeSearchCondition_CustomerName")
    );

    $("#btnCaseFeeApplicationAuditCancel,#btnCaseFeeApplicationAuditClose").die().live("click", function () {
        ap.Auditor.Audit.Close();
    });

    $("#btnCaseFeeApplicationAuditApproved").die().live("click", function () {
        ap.Auditor.Audit.Approved();
    });

    $("#btnCaseFeeApplicationAuditRejected").die().live("click", function () {
        ap.Auditor.Audit.Rejected();
    });

    $("#btnCaseFeeApplicationAuditListCancel,#btnCaseFeeApplicationAuditListClose").die().live("click", function () {
        ap.Auditor.Audit.ViewAuditClose();
    });

    $("#btnCaseFeePendingSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        ap.Auditor.List.PendingList();
    });

    $("#btnCaseFeeRejectedSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        ap.Auditor.List.RejectedList();
    });

    $("#btnCaseFeeApprovedSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        ap.Auditor.List.ApprovedList();
    });
});


