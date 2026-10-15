function AssociateCustomer(div, ctlid, ctlno, ctlname) {
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

                        var defaultContactsContacts = c.DefaultContacts == null ? "" : c.DefaultContacts.Contacts;
                        var defaultContactsContactTelphone = c.DefaultContacts == null ? "" : c.DefaultContacts.ContactTelphone;
                        var defaultContactsContactEmail = c.DefaultContacts == null ? "" : c.DefaultContacts.ContactEmail;
                        var defaultContactsContactAddress = c.DefaultContacts == null ? "" : c.DefaultContacts.ContactAddress;

                        html += '<a href="javascript:void(0)" customerid=' + c.CustomerId
                            + ' customerno=' + c.CustomerNo
                            + ' defaultContactsContacts=' + defaultContactsContacts
                            + ' defaultContactsContactTelphone=' + defaultContactsContactTelphone
                            + ' defaultContactsContactEmail=' + defaultContactsContactEmail
                            + ' defaultContactsContactAddress=' + defaultContactsContactAddress
                            + ' >' + c.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").click(function () {
                        $(ctlid).val($(this).attr("customerid"));
                        $(ctlno).val($(this).attr("customerno"));
                        $(ctlname).val($(this).text());

                        $("#ACustomer_DefaultContacts_Contacts").val($(this).attr("defaultContactsContacts"));
                        $("#ACustomer_DefaultContacts_ContactTelphone").val($(this).attr("defaultContactsContactTelphone"));
                        $("#ACustomer_DefaultContacts_ContactEmail").val($(this).attr("defaultContactsContactEmail"));
                        $("#ACustomer_DefaultContacts_ContactAddress").val($(this).attr("defaultContactsContactAddress"));

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
            "left": $(ctlname).offsetParent().position().left,
            "top": $(ctlname).offsetParent().position().top + 32,
            "z-index": 9999
        }).show();
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
    });

    return this;
}

var contract = {
    Draft: {
        CreateUpdate: function(isSubmit) {
            try {

                if ($("#Contract_ContractBasicInfo_CustomerId").val() == '') {
                    $.showModalMessageBox("请输入客户名称.");
                    $("#Contract_ContractBasicInfo_CustomerName").focus();
                    return false;
                }

                if ($("#Contract_ContractBasicInfo_CustomerName").val() == '') {
                    $.showModalMessageBox("请输入客户名称.");
                    $("#Contract_ContractBasicInfo_CustomerName").focus();
                    return false;
                }

                if ($("#Contract_ContractBasicInfo_ContractName").val() == '') {
                    $.showModalMessageBox("请输入合同名称.");
                    $("#Contract_ContractBasicInfo_ContractName").focus();
                    return false;
                }

                $("#contractForm").attr("action", AP_ROOT + "FCM/Contract/DraftCreate");

                $.openLoading();

                $('#contractForm').ajaxSubmit({
                    success: function (response) {
                        $.closeLoading();
                        if (response.IsSuccess) {

                            $("#Contract_ContractBasicInfo_ContractNo").val(response.Data);

                            if (isSubmit) {
                                $.showModalConfirmDialog(response.Message, 'contract.Draft.CreateUpdateCallBack', isSubmit, true);

                            } else {
                                $.showModalConfirmDialog(response.Message, 'contract.Draft.CreateUpdateCallBack', isSubmit, true);
                            }
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    }
                });

            } catch (e) {
            }
        },
        CreateUpdateCallBack: function (isSubmit) {
            if (isSubmit) {
                window.location = AP_ROOT + "FCM/Contract/ContractList/2";
            } else {
                window.location = AP_ROOT + "FCM/Contract/DraftList";
            }
        },

        TotalAmountSet: function() {
            var totalAmount = 0;
            var caseOfficeFeeAmount = 0;
            var caseNonOfficeFeeAmount = 0;
            var caseCommissionFeeAmount = 0;
            $("input[name='item_CaseOfficeFeeAmount']").each(
                function() {
                    if ($(this).val() == '') {
                        $(this).val(0);
                    }
                    caseOfficeFeeAmount += parseFloat($(this).val());
                }
            );
            $("input[name='item_CaseNonOfficeFeeAmount']").each(
                function() {
                    if ($(this).val() == '') {
                        $(this).val(0);
                    }
                    caseNonOfficeFeeAmount += parseFloat($(this).val());
                }
            );
            $("input[name='item_CaseCommissionFeeAmount']").each(
                function() {
                    if ($(this).val() == '') {
                        $(this).val(0);
                    }
                    caseCommissionFeeAmount += parseFloat($(this).val());
                }
            );

            totalAmount = caseOfficeFeeAmount + caseNonOfficeFeeAmount + caseCommissionFeeAmount;

            $("#Contract_ContractBasicInfo_TotalAmount").val(totalAmount);
            $("#Contract_ContractBasicInfo_ARAmount").val(totalAmount);
            $("#Contract_ContractBasicInfo_APAmount").val(caseOfficeFeeAmount + caseCommissionFeeAmount);
            $("#Contract_ContractBasicInfo_UnPaidCaesFeeAmount").val(caseOfficeFeeAmount + caseCommissionFeeAmount);
            $("#Contract_ContractBasicInfo_InvoiceAmount").val(totalAmount);
            
        },
    },

    /*合同列表 我发起的合同*/
    Sponsor: {
        DraftList: function () {
            $("#postForm").ajaxPost(AP_ROOT + "FCM/Contract/DraftList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.ContractList, function (i, c) {

                            var contractFileId = c.DefalutContractFile == null ? '' : c.DefalutContractFile.FileId;
                            var contractFileName = c.DefalutContractFile == null ? '' : c.DefalutContractFile.FileName;

                            $("tbody", "#tblContractList").addRow(
                                i + 1,
                                c.ContractBasicInfo.ContractNo,
                                "<span>" + c.ContractBasicInfo.CustomerName + "</span>",
                                "<span>" + c.ContractBasicInfo.ContractName + "</span>",
                                c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.BusinessOwnerName,
                                "<a href='javascript:void(0)' onclick='javascript:contract.ContractFile.View(\"" + contractFileId + "\",\"" + c.ContractBasicInfo.ContractNo + "\",\"" + contractFileName + "\")'>查看附件</a> &nbsp;"+
                                "<a href='javascript:void(0)' onclick='javascript:contract.ContractFile.Open(" + c.ContractBasicInfo.ContractId + ",\"" + c.ContractBasicInfo.ContractNo + "\")'>重新上传</a> &nbsp; ",
                                "<a href='javascript:void(0)' onclick='javascript:contract.Audit.ToAudit(" + c.ContractBasicInfo.ContractId + ",true)'>提交审批</a> &nbsp; "
                            );
                        });

                        $("tfoot", "#tblContractList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.contractlist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: contract.Sponsor.DraftList,
                            callBackArgs: null
                        });
                    } else {

                        $("tfoot", "#tblContractList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        ApprovedList: function () {
            $("#postForm").ajaxPost(AP_ROOT + "FCM/Contract/ApprovedList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.ContractList, function (i, c) {
                            var contractFileId = c.DefalutContractFile == null ? '' : c.DefalutContractFile.FileId;
                            var contractFileName = c.DefalutContractFile == null ? '' : c.DefalutContractFile.FileName;

                            $("tbody", "#tblContractList").addRow(
                                i + 1,
                                c.ContractBasicInfo.ContractNo,
                                "<span>" + c.ContractBasicInfo.CustomerName + "</span>",
                                "<span>" + c.ContractBasicInfo.ContractName + "</span>",
                                c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.BusinessOwnerName,
                                c.ContractAudit == null ? '' : c.ContractAudit.AuditorName,
                                "<a href='javascript:void(0)' onclick='javascript:contract.ContractFile.View(\"" + contractFileId + "\",\"" + c.ContractBasicInfo.ContractNo + "\",\"" + contractFileName + "\")'>查看附件</a> &nbsp;",
                                "<a href='javascript:void(0)' onclick='javascript:contract.Audit.ViewAudit(" + c.ContractBasicInfo.ContractId + ",\"" + c.ContractBasicInfo.ContractNo + "\")'>审批信息</a> &nbsp; "
                            );
                        });

                        $("tfoot", "#tblContractList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.contractlist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: contract.Sponsor.ApprovedList,
                            callBackArgs: null
                        });
                    } else {

                        $("tfoot", "#tblContractList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        RejectedList: function () {
            $("#postForm").ajaxPost(AP_ROOT + "FCM/Contract/RejectedList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.ContractList, function (i, c) {
                            var contractFileId = c.DefalutContractFile == null ? '' : c.DefalutContractFile.FileId;
                            var contractFileName = c.DefalutContractFile == null ? '' : c.DefalutContractFile.FileName;
                            $("tbody", "#tblContractList").addRow(
                                i + 1,
                                c.ContractBasicInfo.ContractNo,
                                "<span>" + c.ContractBasicInfo.CustomerName + "</span>",
                                "<span>" + c.ContractBasicInfo.ContractName + "</span>",
                                c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.BusinessOwnerName,
                                 c.ContractAudit == null ? '' : c.ContractAudit.AuditorName,
                                "<a href='javascript:void(0)' onclick='javascript:contract.ContractFile.View(\"" + contractFileId + "\",\"" + c.ContractBasicInfo.ContractNo + "\",\"" + contractFileName + "\")'>查看附件</a> &nbsp;"+
                                "<a href='javascript:void(0)' onclick='javascript:contract.ContractFile.Open(" + c.ContractBasicInfo.ContractId + ",\"" + c.ContractBasicInfo.ContractNo + "\")'>重新上传</a> &nbsp; ",
                                "<a href='javascript:void(0)' onclick='javascript:contract.Audit.ViewAudit(" + c.ContractBasicInfo.ContractId + ",\"" + c.ContractBasicInfo.ContractNo + "\")'>审批信息</a> &nbsp; "+
                                "<a href='javascript:void(0)' onclick='javascript:contract.Audit.ToAudit(" + c.ContractBasicInfo.ContractId + ",false)'>提交审批</a> &nbsp; "

                            );
                        });

                        $("tfoot", "#tblContractList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.contractlist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: contract.Sponsor.RejectedList,
                            callBackArgs: null
                        });
                    } else {

                        $("tfoot", "#tblContractList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        PendingList: function () {
            $("#postForm").ajaxPost(AP_ROOT + "FCM/Contract/PendingList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.ContractList, function (i, c) {
                            var contractFileId = c.DefalutContractFile == null ? '' : c.DefalutContractFile.FileId;
                            var contractFileName = c.DefalutContractFile == null ? '' : c.DefalutContractFile.FileName;

                            $("tbody", "#tblContractList").addRow(
                                i + 1,
                                c.ContractBasicInfo.ContractNo,
                                "<span>" + c.ContractBasicInfo.CustomerName + "</span>",
                                "<span>" + c.ContractBasicInfo.ContractName + "</span>",
                                c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.BusinessOwnerName,
                                 c.ContractAudit == null ? '' : c.ContractAudit.AuditorName,
                                "<a href='javascript:void(0)' onclick='javascript:contract.ContractFile.View(\"" + contractFileId + "\",\"" + c.ContractBasicInfo.ContractNo + "\",\"" + contractFileName + "\")'>查看附件</a> &nbsp;",
                                "<a href='javascript:void(0)' onclick='javascript:contract.Audit.ViewAudit(" + c.ContractBasicInfo.ContractId + ",\"" + c.ContractBasicInfo.ContractNo + "\")'>审批信息</a> &nbsp; "
                            );
                        });

                        $("tfoot", "#tblContractList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.contractlist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: contract.Sponsor.PendingList,
                            callBackArgs: null
                        });
                    } else {

                        $("tfoot", "#tblContractList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
    },

    /*合同列表 我审批的合同*/
    Auditor: {
        ApprovedList: function () {
            $("#postForm").ajaxPost(AP_ROOT + "FCM/ContractAudit/ApprovedList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.ContractList, function (i, c) {
                            var contractFileId = c.DefalutContractFile == null ? '' : c.DefalutContractFile.FileId;
                            var contractFileName = c.DefalutContractFile == null ? '' : c.DefalutContractFile.FileName;

                            $("tbody", "#tblContractList").addRow(
                                i + 1,
                                c.ContractBasicInfo.ContractNo,
                                "<span>" + c.ContractBasicInfo.CustomerName + "</span>",
                                "<span>" + c.ContractBasicInfo.ContractName + "</span>",
                                c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.BusinessOwnerName,
                                 c.ContractAudit == null ? '' : c.ContractAudit.AuditorName,
                                "<a href='javascript:void(0)' onclick='javascript:contract.ContractFile.View(\"" + contractFileId + "\",\"" + c.ContractBasicInfo.ContractNo + "\",\"" + contractFileName + "\")'>查看附件</a> &nbsp;",
                                "<a href='javascript:void(0)' onclick='javascript:contract.Audit.ViewAudit(" + c.ContractBasicInfo.ContractId + ",\"" + c.ContractBasicInfo.ContractNo + "\")'>审批信息</a> &nbsp; "
                            );
                        });

                        $("tfoot", "#tblContractList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.contractlist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: contract.Auditor.ApprovedList,
                            callBackArgs: null
                        });
                    } else {

                        $("tfoot", "#tblContractList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        RejectedList: function () {
            $("#postForm").ajaxPost(AP_ROOT + "FCM/ContractAudit/RejectedList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.ContractList, function (i, c) {
                            var contractFileId = c.DefalutContractFile == null ? '' : c.DefalutContractFile.FileId;
                            var contractFileName = c.DefalutContractFile == null ? '' : c.DefalutContractFile.FileName;

                            $("tbody", "#tblContractList").addRow(
                                i + 1,
                                c.ContractBasicInfo.ContractNo,
                                "<span>" + c.ContractBasicInfo.CustomerName + "</span>",
                                "<span>" + c.ContractBasicInfo.ContractName + "</span>",
                                c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.BusinessOwnerName,
                                 c.ContractAudit == null ? '' : c.ContractAudit.AuditorName,
                                "<a href='javascript:void(0)' onclick='javascript:contract.ContractFile.View(\"" + contractFileId + "\",\"" + c.ContractBasicInfo.ContractNo + "\",\"" + contractFileName + "\")'>查看附件</a> &nbsp;",
                                "<a href='javascript:void(0)' onclick='javascript:contract.Audit.ViewAudit(" + c.ContractBasicInfo.ContractId + ",\"" + c.ContractBasicInfo.ContractNo + "\")'>审批信息</a> &nbsp; "
                            );
                        });

                        $("tfoot", "#tblContractList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.contractlist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: contract.Auditor.RejectedList,
                            callBackArgs: null
                        });
                    } else {

                        $("tfoot", "#tblContractList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        PendingList: function () {
            $("#postForm").ajaxPost(AP_ROOT + "FCM/ContractAudit/PendingList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.ContractList, function (i, c) {
                            var contractFileId = c.DefalutContractFile == null ? '' : c.DefalutContractFile.FileId;
                            var contractFileName = c.DefalutContractFile == null ? '' : c.DefalutContractFile.FileName;

                            $("tbody", "#tblContractList").addRow(
                                i + 1,
                                c.ContractBasicInfo.ContractNo,
                                "<span>" + c.ContractBasicInfo.CustomerName + "</span>",
                                "<span>" + c.ContractBasicInfo.ContractName + "</span>",
                                c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.BusinessOwnerName,
                                c.ContractAudit == null ? '' : c.ContractAudit.AuditorName,
                                "<a href='javascript:void(0)' onclick='javascript:contract.ContractFile.View(\"" + contractFileId + "\",\"" + c.ContractBasicInfo.ContractNo + "\",\"" + contractFileName + "\")'>查看附件</a> &nbsp;",
                                "<a href='javascript:void(0)' onclick='javascript:contract.Audit.Open(" + c.ContractBasicInfo.ContractId + ",\"" + c.ContractBasicInfo.ContractNo + "\")'>审批</a> &nbsp; "
                            );
                        });

                        $("tfoot", "#tblContractList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.contractlist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: contract.Auditor.PendingList,
                            callBackArgs: null
                        });
                    } else {

                        $("tfoot", "#tblContractList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
    },

    /*合同台帐*/
    GeneralLedger: {
        Open: function (contractId) {
            window.location = AP_ROOT + "FCM/GL/index?contractId=" + contractId;
        },

        List: function () {
            $("#postForm").ajaxPost(AP_ROOT + "FCM/Contract/GeneralLedgerList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.ContractList, function (i, c) {
                            var contractFileId = c.DefalutContractFile == null ? '' : c.DefalutContractFile.FileId;
                            var contractFileName = c.DefalutContractFile == null ? '' : c.DefalutContractFile.FileName;

                            $("tbody", "#tblContractList").addRow(
                                i + 1,
                                c.ContractBasicInfo.ContractNo,
                                "<span>" + c.ContractBasicInfo.CustomerName + "</span>",
                                "<span>" + c.ContractBasicInfo.ContractName + "</span>",
                                c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.BusinessOwnerName,
                                c.ContractAudit==null ? '':c.ContractAudit.AuditorName,
                                "<a href='javascript:void(0)' onclick='javascript:contract.ContractFile.View(\"" + contractFileId + "\",\"" + c.ContractBasicInfo.ContractNo + "\",\"" + contractFileName + "\")'>查看附件</a> &nbsp;",
                                "<a href='javascript:void(0)' onclick='javascript:contract.GeneralLedger.Open(" + c.ContractBasicInfo.ContractId +")'>查看</a> &nbsp; "
                            );
                        });

                        $("tfoot", "#tblContractList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.contractlist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: contract.GeneralLedger.List,
                            callBackArgs: null
                        });
                    } else {

                        $("tfoot", "#tblContractList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
    },

    /*合同文件*/
    ContractFile: {
        Open: function(contractId, contractNo) {
            var data =
            {
                contractId: contractId,
                contractNo: contractNo
            };
            var url = AP_ROOT + "FCM/ContractFile/ContractFileUpload";
            $.openLoading();

            $("<div></div>").load(url, data, function(result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#contractFileUploadModal').modal({ backdrop: 'static', keyboard: false });
                $('#contractFileUploadModal').on('hidden.bs.modal', function () {
                    $("#contractFileUploadModal").remove();
                });
            });
        },
        Close: function () {
            $('#contractFileUploadModal').modal('hide');
        },
        /*上传*/
        Upload: function () {

            if ($("#flContractFile").val() == '') {
                $.showModalMessageBox("请选择上传文件.");
                return false;
            }

            $('#uploadForm').ajaxSubmit({
                success: function (response) {
                    $.showModalMessageBox("上传成功.");
                    contract.ContractFile.Close();

                    if (window.location.href.toLowerCase().indexOf("DraftList".toLowerCase()) > 0) {
                        contract.Sponsor.DraftList();
                    } else {
                        contract.Sponsor.RejectedList();
                    }
                }
            });
        },

        /*查看*/
        View: function (contractFileId, contractNo,contractFileName) {

            if (contractFileId == '' || contractFileName == '') {
                $.showModalMessageBox("无合同文件.");
                return false;
            }

            var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
            var picfiles = new Array('jpg', 'tif', 'pdf');
            var extName = contractFileName.substring(contractFileName.lastIndexOf('.') + 1, contractFileName.length);

            if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                var path = GV_IPR.OfficeOnlineUrl + GV_IPR.OnlineUrl + "ContractFiles/ContractFiles/" + contractNo + "/" + contractFileName;
                window.open(path);
            }
            else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                var path = GV_IPR.OnlineUrl + "ContractFiles/ContractFiles/" + contractNo + "/" + contractFileName;
                window.open(path);
            } else {
                contract.ContractFile.Download(contractFileId);
            }

            return true;
        },

        Download: function (contractFileId) {
            window.open(AP_ROOT + "FCM/ContractFile/ContractFileDownload?contractFileId=" + contractFileId);
            return true;
        },
    },

    /*审核*/
    Audit: {

        ToAudit: function (contractId, isDraft) {
            var data = {};
            data["ContractId"] = contractId;

            $.ajaxPost(AP_ROOT + "FCM/Contract/ToAudit", data, function (response) {
                if (response.IsSuccess) {
                    if (isDraft) {
                        contract.Sponsor.DraftList();
                    } else {
                        contract.Sponsor.RejectedList();
                    }

                    $.showModalMessageBox("提交成功.");

                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        ViewAudit: function(contractId, contractNo) {

            var data =
            {
                contractId: contractId,
                contractNo: contractNo
            };

            var url = AP_ROOT + "FCM/ContractAudit/ContractAuditList";
            $.openLoading();

            $("<div></div>").load(url, data, function(result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#contractAuditListModal').modal({ backdrop: 'static', keyboard: false });
                $('#contractAuditListModal').on('hidden.bs.modal', function() {
                    $("#contractAuditListModal").remove();
                });
            });

        },

        AuditClose: function() {
            $('#contractAuditListModal').modal('hide');
        },

        /*审核信息*/
        Open: function(contractId, contractNo) {

            var data =
            {
                contractId: contractId,
                contractNo: contractNo
            };

            var url = AP_ROOT + "FCM/ContractAudit/ContractAudit";
            $.openLoading();

            $("<div></div>").load(url, data, function(result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#contractAuditModal').modal({ backdrop: 'static', keyboard: false });
                $('#contractAuditModal').on('hidden.bs.modal', function() {
                    $("#contractAuditModal").remove();
                });
            });

        },

        /*审核信息*/
        Close: function() {
            $('#contractAuditModal').modal('hide');
        },

        /*审核*/
        CreateUpdate: function(auditStatus) {
            if ($("#ContractAudit_AuditContent").val() == '' && auditStatus == '4') {
                $.showModalMessageBox("请输入审批内容");
                return false;
            }

            if ($("#ContractAudit_AuditContent").val() == '' && auditStatus == '3') {
                $("#ContractAudit_AuditContent").val('同意');
            }

            var data = {};

            data["ContractAudit.AuditId"] = $("#AuditId").val();
            data["ContractAudit.ContractId"] = $("#Contract_ContractBasicInfo_ContractId").val();
            data["ContractAudit.ContractNo"] = $("#Contract_ContractBasicInfo_ContractNo").val();
            data["ContractAudit.AuditContent"] = $("#ContractAudit_AuditContent").val();
            data["ContractAudit.AuditStatus"] = auditStatus;

            $.ajaxPost(AP_ROOT + "FCM/ContractAudit/ContractAuditCreate", data, function(response) {
                if (response.IsSuccess) {
                    $.showModalConfirmDialog("审批成功.");
                } else {
                    $.showModalMessageBox(response.Message,);
                }
            });
        },

    },
};


$(document).ready(function () {

    var customter = new AssociateCustomer(
        $("#div_customer"),
        $("#Contract_ContractBasicInfo_CustomerId"),
        $("#Contract_ContractBasicInfo_CustomerNo"),
        $("#Contract_ContractBasicInfo_CustomerName")
    );

    $("#btnPendingSearch").click(function () {
        contract.Auditor.PendingList();
    });

    $("#btnRejectSearch").click(function () {
        contract.Auditor.RejectedList();
    });

    $("#btnApprovedSearch").click(function () {
        contract.Auditor.ApprovedList();
    });

    $("#btnSearch").click(function () {
        if ($("#SearchCondition_ContractStatus").val() == 'P') {
            contract.Sponsor.PendingList();
        }
        else if ($("#SearchCondition_ContractStatus").val() == 'A') {
            contract.Sponsor.ApprovedList();
        }
        else if ($("#SearchCondition_ContractStatus").val() == 'R') {
            contract.Sponsor.RejectedList();
        }
        else if ($("#SearchCondition_ContractStatus").val() == 'D') {
            contract.Sponsor.DraftList();
        }
    });

    $("#btnGLSearch").click(function () {
        contract.GeneralLedger.List();
    });

    $("#btnContractAuditClose,#btnContractAuditCancel").die().live("click", function () {
        contract.Audit.Close();
    });

    $("#btnContractAuditApproved").die().live("click", function () {
        contract.Audit.CreateUpdate(3);
    });

    $("#btnContractAuditRejected").die().live("click", function () {
        contract.Audit.CreateUpdate(4);
    });

    $("#btnContractAuditListClose,#btnContractAuditListCancel").die().live("click", function () {
        contract.Audit.AuditClose();
    });

    $("#btnContractFileUploadCancel,#btnContractFileUploadClose").die().live("click", function () {
        contract.ContractFile.Close();
    });

    $("#flContractFile").die().live("change", function () {
        $("#txtContractFilePath").val($("#flContractFile").val());
    });

    $("#flCaseFileFirst").die().live("change", function () {
        $("#txtCaseFilePathFirst").val($("#flCaseFileFirst").val());
    });

    $("#flCaseFileSecond").die().live("change", function () {
        $("#txtCaseFilePathSecond").val($("#flCaseFileSecond").val());
    });
 
    $("#btnContractFileUpload").die().live("click", function () {
        contract.ContractFile.Upload();
    });

    $("#btnContractCreateUpdate,#btnContractCreateUpdateSubmit").die().live("click", function () {
        contract.Draft.CreateUpdate(true);
    });

    $("#item_CaseOfficeFeeAmount").die().live("change", function () {
        contract.Draft.TotalAmountSet();
    });

    $("#item_CaseNonOfficeFeeAmount").die().live("change", function () {
        contract.Draft.TotalAmountSet();
    });

    $("#item_CaseCommissionFeeAmount").die().live("change", function () {
        contract.Draft.TotalAmountSet();
    });
});