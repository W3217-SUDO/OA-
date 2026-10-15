function AssociateApplicant(div, ctlid, ctlno, ctlname) {
    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;

    this.Customer = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") { return false; }
        var curobj = new Object();
        curobj.keyword = name;
        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CRM/Customer/AllCustomerList", curobj, function (response) {
            $(div).find(".i_common_list").empty();
            if (response.IsSuccess) {
                if (response.Data) {
                    var html = "";
                    $.each(response.Data.Customers, function (i, c) {

                        var defaultContactsContacts = c.DefaultContacts == null ? "" : c.DefaultContacts.Contacts;
                        var defaultContactsContactTelphone = c.DefaultContacts == null ? "" : c.DefaultContacts.OfficePhone;
                        var defaultContactsContactEmail = c.DefaultContacts == null ? "" : c.DefaultContacts.Email;
                        var defaultContactsContactAddress = c.DefaultContacts == null ? "" : c.DefaultContacts.ContactAddress;

                        html += '<a href="javascript:void(0)" customerid=' + c.CustomerBasic.CustomerId
                            + ' customerno=' + c.CustomerBasic.CustomerNo
                            + ' defaultContactsContacts=' + defaultContactsContacts
                            + ' defaultContactsContactTelphone=' + defaultContactsContactTelphone
                            + ' defaultContactsContactEmail=' + defaultContactsContactEmail
                            + ' defaultContactsContactAddress=' + defaultContactsContactAddress
                            + ' >' + c.CustomerBasic.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").click(function () {
                        caseInfo.CaseCustomer.AddIn($(this).attr("customerid"), $(this).attr("customerno"), $(this).text());
                        $(ctlname).val('');
                        $(ctlname).focus();
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
            "left": $(ctlname).position().left + 6,
            "top": $(ctlname).position().top + 32,
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
function AssociateCustomer(div, ctlid, ctlno, ctlname) {
    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;
    this.Customer = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") { return false; }
        var curobj = new Object();
        curobj.keyword = name;
        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CustomerList", curobj, function (response) {

            $(div).find(".i_common_list").empty();
            if (response.IsSuccess) {
                if (response.Data.Customers.length > 0) {
                    var html = "";
                    $.each(response.Data.Customers, function (i, c) {

                        var defaultContactsContacts = c.DefaultContacts == null ? "" : c.DefaultContacts.Contacts;
                        var defaultContactsContactTelphone = c.DefaultContacts == null ? "" : c.DefaultContacts.OfficePhone;
                        var defaultContactsContactEmail = c.DefaultContacts == null ? "" : c.DefaultContacts.Email;
                        var defaultContactsContactAddress = c.DefaultContacts == null ? "" : c.DefaultContacts.ContactAddress;

                        html += '<a href="javascript:void(0)"  customerid=' + c.CustomerBasic.CustomerId
                            + ' customerno=' + c.CustomerBasic.CustomerNo
                            + ' defaultContactsContacts=' + defaultContactsContacts
                            + ' defaultContactsContactTelphone=' + defaultContactsContactTelphone
                            + ' defaultContactsContactEmail=' + defaultContactsContactEmail
                            + ' defaultContactsContactAddress=' + defaultContactsContactAddress
                            + ' >' + c.CustomerBasic.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);

                    $(div).find(".i_common_list a").css({
                        "height": $(ctlname).outerHeight(),
                        "line-height": ($(ctlname).outerHeight() - 4) + "px"
                    });

                    $(div).find(".i_common_list a").click(function () {
                        $(ctlid).val($(this).attr("customerid"));
                        $(ctlno).val($(this).attr("customerno"));
                        $(ctlname).val($(this).text());
                        $("#Contract_ContractBasicInfo_ContractName").val($(this).text() + "_合同");
                        $(div).hide();
                    });
                }
                else {

                    var html = "";
                    html += '<a href="javascript:void(0)" >没有查询到符合条件的记录.</a>';
                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").css({
                        "height": $(ctlname).outerHeight(),
                        "line-height": ($(ctlname).outerHeight() - 4) + "px"
                    });
                }
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        }, false);
        $(div).css({
            "position": "absolute",
            "left": $(ctlname).position().left + 0,
            "top": $(ctlname).position().top + 32,
            "width": $(ctlname).outerWidth(),
            "height": $(ctlname).outerHeight(),
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

var caseInfo = {
    View: function (caseId, caseNo) {
        var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + caseNo;

        addtabs(url, caseNo);
        //window.open(url);
    },
    QuickCase: {
        Open: function (contractId) {
            
            var chkContractObject = $("input[name='chkContractId']:checked")[0];
            var contractStatus = $(chkContractObject).parents("tr").find(".contractStatus").text();

            if (contractStatus == contract.ContractStatus.Archived) {
                $.showTips("合同已归档,不允许新建案子.", 0, 3)
                return false;
            }

            var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/QuickCreate";
            $.openLoading();

            var data = {
                contractId: contractId
            };

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#quickCreateModel').modal({ backdrop: 'static', keyboard: false });
                $('#quickCreateModel').on('hidden.bs.modal', function () {
                    $("#quickCreateModel").remove();
                });
            });
        },
        Close: function () {
            $('#quickCreateModel').modal('hide');
        },

        Create: function (contractId,caseTypeId)
        {
            var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/Create?contractId=" + contractId + "&caseTypeId=" + caseTypeId;
            window.location = url;
        }
    },
}
var contract = {
    ContractStatus: {
        D: 1,
        P: 2,
        A: 3,
        R: 4,
        Archived:5
    },
    Contract: {
        View: function (contractId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FCM/Contract/ContractView?contractId=" + contractId;
            addtabs(url, "合同查看");
        },
        ViewItem: function (contractNo, paidCaseOfficeFeeAmount, cashedCaseOfficeFeeAmount,unCashedCaseOfficeFeeAmount, deficitCaseOfficeFeeAmount, caseNonOfficeFeeAmount,cashedCaseNonOfficeFeeAmount, unCashedCaseNonOfficeFeeAmount) {
            var url = AP_ROOT + AP_PAGE_ID + "/FCM/AR/ItemList?contractNo=" + contractNo
                + "&PaidCaseOfficeFeeAmount=" + paidCaseOfficeFeeAmount
                + "&cashedCaseOfficeFeeAmount=" + cashedCaseOfficeFeeAmount
                + "&unCashedCaseOfficeFeeAmount=" + unCashedCaseOfficeFeeAmount
                + "&deficitCaseOfficeFeeAmount=" + deficitCaseOfficeFeeAmount
                + "&caseNonOfficeFeeAmount=" + caseNonOfficeFeeAmount
                + "&cashedCaseNonOfficeFeeAmount=" + cashedCaseNonOfficeFeeAmount
                + "&unCashedCaseNonOfficeFeeAmount=" + unCashedCaseNonOfficeFeeAmount
            addtabs(url, "应收账款明细");
        },
        ViewItem_TotalPaidCaseOfficeFeeAmount: function (_paidCaseOfficeFeeAmount) {
            var contractNo = '', paidCaseOfficeFeeAmount = '', cashedCaseOfficeFeeAmount = '', unCashedCaseOfficeFeeAmount = '', deficitCaseOfficeFeeAmount = '', caseNonOfficeFeeAmount = '', cashedCaseNonOfficeFeeAmount = '', unCashedCaseNonOfficeFeeAmount = '';
            paidCaseOfficeFeeAmount = _paidCaseOfficeFeeAmount;
            contract.Contract.ViewItem(contractNo, paidCaseOfficeFeeAmount, cashedCaseOfficeFeeAmount, unCashedCaseOfficeFeeAmount, deficitCaseOfficeFeeAmount, caseNonOfficeFeeAmount, cashedCaseNonOfficeFeeAmount, unCashedCaseNonOfficeFeeAmount);
        },
        ViewItem_TotalCashedCaseOfficeFeeAmount: function (_cashedCaseOfficeFeeAmount) {
            var contractNo = '', paidCaseOfficeFeeAmount = '', cashedCaseOfficeFeeAmount = '', unCashedCaseOfficeFeeAmount = '', deficitCaseOfficeFeeAmount = '', caseNonOfficeFeeAmount = '', cashedCaseNonOfficeFeeAmount = '', unCashedCaseNonOfficeFeeAmount = '';
            cashedCaseOfficeFeeAmount = _cashedCaseOfficeFeeAmount;
            contract.Contract.ViewItem(contractNo, paidCaseOfficeFeeAmount, cashedCaseOfficeFeeAmount, unCashedCaseOfficeFeeAmount, deficitCaseOfficeFeeAmount, caseNonOfficeFeeAmount, cashedCaseNonOfficeFeeAmount, unCashedCaseNonOfficeFeeAmount);
        },
        ViewItem_TotalUnCashedCaseOfficeFeeAmount: function (_unCashedCaseOfficeFeeAmount) {
            var contractNo = '', paidCaseOfficeFeeAmount = '', cashedCaseOfficeFeeAmount = '', unCashedCaseOfficeFeeAmount = '', deficitCaseOfficeFeeAmount = '', caseNonOfficeFeeAmount = '', cashedCaseNonOfficeFeeAmount = '', unCashedCaseNonOfficeFeeAmount = '';
            unCashedCaseOfficeFeeAmount = _unCashedCaseOfficeFeeAmount;
            contract.Contract.ViewItem(contractNo, paidCaseOfficeFeeAmount, cashedCaseOfficeFeeAmount, unCashedCaseOfficeFeeAmount, deficitCaseOfficeFeeAmount, caseNonOfficeFeeAmount, cashedCaseNonOfficeFeeAmount, unCashedCaseNonOfficeFeeAmount);
        },
        ViewItem_TotalDeficitCaseOfficeFeeAmount: function (_deficitCaseOfficeFeeAmount) {
            var contractNo = '', paidCaseOfficeFeeAmount = '', cashedCaseOfficeFeeAmount = '', unCashedCaseOfficeFeeAmount = '', deficitCaseOfficeFeeAmount = '', caseNonOfficeFeeAmount = '', cashedCaseNonOfficeFeeAmount = '', unCashedCaseNonOfficeFeeAmount = '';
            deficitCaseOfficeFeeAmount = _deficitCaseOfficeFeeAmount;
            contract.Contract.ViewItem(contractNo, paidCaseOfficeFeeAmount, cashedCaseOfficeFeeAmount, unCashedCaseOfficeFeeAmount, deficitCaseOfficeFeeAmount, caseNonOfficeFeeAmount, cashedCaseNonOfficeFeeAmount, unCashedCaseNonOfficeFeeAmount);
        },
        ViewItem_TotalCaseNonOfficeFeeAmount: function (_caseNonOfficeFeeAmount) {
            var contractNo = '', paidCaseOfficeFeeAmount = '', cashedCaseOfficeFeeAmount = '', unCashedCaseOfficeFeeAmount = '', deficitCaseOfficeFeeAmount = '', caseNonOfficeFeeAmount = '', cashedCaseNonOfficeFeeAmount = '', unCashedCaseNonOfficeFeeAmount = '';
            caseNonOfficeFeeAmount = _caseNonOfficeFeeAmount;
            contract.Contract.ViewItem(contractNo, paidCaseOfficeFeeAmount, cashedCaseOfficeFeeAmount, unCashedCaseOfficeFeeAmount, deficitCaseOfficeFeeAmount, caseNonOfficeFeeAmount, cashedCaseNonOfficeFeeAmount, unCashedCaseNonOfficeFeeAmount);
        },
        ViewItem_TotalCashedCaseNonOfficeFeeAmount: function (_cashedCaseNonOfficeFeeAmount) {
            var contractNo = '', paidCaseOfficeFeeAmount = '', cashedCaseOfficeFeeAmount = '', unCashedCaseOfficeFeeAmount = '', deficitCaseOfficeFeeAmount = '', caseNonOfficeFeeAmount = '', cashedCaseNonOfficeFeeAmount = '', unCashedCaseNonOfficeFeeAmount = '';
            cashedCaseNonOfficeFeeAmount = _cashedCaseNonOfficeFeeAmount;
            contract.Contract.ViewItem(contractNo, paidCaseOfficeFeeAmount, cashedCaseOfficeFeeAmount, unCashedCaseOfficeFeeAmount, deficitCaseOfficeFeeAmount, caseNonOfficeFeeAmount, cashedCaseNonOfficeFeeAmount, unCashedCaseNonOfficeFeeAmount);
        },
        ViewItem_TotalUnCashedCaseNonOfficeFeeAmount: function (_unCashedCaseNonOfficeFeeAmount) {
            var contractNo = '', paidCaseOfficeFeeAmount = '', cashedCaseOfficeFeeAmount = '', unCashedCaseOfficeFeeAmount = '', deficitCaseOfficeFeeAmount = '', caseNonOfficeFeeAmount = '', cashedCaseNonOfficeFeeAmount = '', unCashedCaseNonOfficeFeeAmount = '';
            unCashedCaseNonOfficeFeeAmount = _unCashedCaseNonOfficeFeeAmount;
            contract.Contract.ViewItem(contractNo, paidCaseOfficeFeeAmount, cashedCaseOfficeFeeAmount, unCashedCaseOfficeFeeAmount, deficitCaseOfficeFeeAmount, caseNonOfficeFeeAmount, cashedCaseNonOfficeFeeAmount, unCashedCaseNonOfficeFeeAmount);
        },
        ViewItem_PaidCaseOfficeFeeAmount: function (_contractNo, _paidCaseOfficeFeeAmount) {
            var contractNo = '', paidCaseOfficeFeeAmount = '', cashedCaseOfficeFeeAmount = '', unCashedCaseOfficeFeeAmount = '', deficitCaseOfficeFeeAmount = '', caseNonOfficeFeeAmount = '', cashedCaseNonOfficeFeeAmount = '', unCashedCaseNonOfficeFeeAmount = '';
            contractNo = _contractNo;
            paidCaseOfficeFeeAmount = _paidCaseOfficeFeeAmount;
            contract.Contract.ViewItem(contractNo, paidCaseOfficeFeeAmount, cashedCaseOfficeFeeAmount, unCashedCaseOfficeFeeAmount, deficitCaseOfficeFeeAmount, caseNonOfficeFeeAmount, cashedCaseNonOfficeFeeAmount, unCashedCaseNonOfficeFeeAmount);
        },
        ViewItem_CashedCaseOfficeFeeAmount: function (_contractNo, _cashedCaseOfficeFeeAmount) {
            var contractNo = '', paidCaseOfficeFeeAmount = '', cashedCaseOfficeFeeAmount = '', unCashedCaseOfficeFeeAmount = '', deficitCaseOfficeFeeAmount = '', caseNonOfficeFeeAmount = '', cashedCaseNonOfficeFeeAmount = '', unCashedCaseNonOfficeFeeAmount = '';
            contractNo = _contractNo;
            cashedCaseOfficeFeeAmount = _cashedCaseOfficeFeeAmount;
            contract.Contract.ViewItem(contractNo, paidCaseOfficeFeeAmount, cashedCaseOfficeFeeAmount, unCashedCaseOfficeFeeAmount, deficitCaseOfficeFeeAmount, caseNonOfficeFeeAmount, cashedCaseNonOfficeFeeAmount, unCashedCaseNonOfficeFeeAmount);
        },
        ViewItem_UnCashedCaseOfficeFeeAmount: function (_contractNo, _unCashedCaseOfficeFeeAmount) {
            var contractNo = '', paidCaseOfficeFeeAmount = '', cashedCaseOfficeFeeAmount = '', unCashedCaseOfficeFeeAmount = '', deficitCaseOfficeFeeAmount = '', caseNonOfficeFeeAmount = '', cashedCaseNonOfficeFeeAmount = '', unCashedCaseNonOfficeFeeAmount = '';
            contractNo = _contractNo;
            unCashedCaseOfficeFeeAmount = _unCashedCaseOfficeFeeAmount;
            contract.Contract.ViewItem(contractNo, paidCaseOfficeFeeAmount, cashedCaseOfficeFeeAmount, unCashedCaseOfficeFeeAmount, deficitCaseOfficeFeeAmount, caseNonOfficeFeeAmount, cashedCaseNonOfficeFeeAmount, unCashedCaseNonOfficeFeeAmount);
        },
        ViewItem_DeficitCaseOfficeFeeAmount: function (_contractNo, _deficitCaseOfficeFeeAmount) {
            var contractNo = '', paidCaseOfficeFeeAmount = '', cashedCaseOfficeFeeAmount = '', unCashedCaseOfficeFeeAmount = '', deficitCaseOfficeFeeAmount = '', caseNonOfficeFeeAmount = '', cashedCaseNonOfficeFeeAmount = '', unCashedCaseNonOfficeFeeAmount = '';
            contractNo = _contractNo;
            deficitCaseOfficeFeeAmount = _deficitCaseOfficeFeeAmount;
            contract.Contract.ViewItem(contractNo, paidCaseOfficeFeeAmount, cashedCaseOfficeFeeAmount, unCashedCaseOfficeFeeAmount, deficitCaseOfficeFeeAmount, caseNonOfficeFeeAmount, cashedCaseNonOfficeFeeAmount, unCashedCaseNonOfficeFeeAmount);
        },
        ViewItem_CaseNonOfficeFeeAmount: function (_contractNo, _caseNonOfficeFeeAmount) {
            var contractNo = '', paidCaseOfficeFeeAmount = '', cashedCaseOfficeFeeAmount = '', unCashedCaseOfficeFeeAmount = '', deficitCaseOfficeFeeAmount = '', caseNonOfficeFeeAmount = '', cashedCaseNonOfficeFeeAmount = '', unCashedCaseNonOfficeFeeAmount = '';
            contractNo = _contractNo;
            caseNonOfficeFeeAmount = _caseNonOfficeFeeAmount;
            contract.Contract.ViewItem(contractNo, paidCaseOfficeFeeAmount, cashedCaseOfficeFeeAmount, unCashedCaseOfficeFeeAmount, deficitCaseOfficeFeeAmount, caseNonOfficeFeeAmount, cashedCaseNonOfficeFeeAmount, unCashedCaseNonOfficeFeeAmount);
        },
        ViewItem_CashedCaseNonOfficeFeeAmount: function (_contractNo, _cashedCaseNonOfficeFeeAmount) {
            var contractNo = '', paidCaseOfficeFeeAmount = '', cashedCaseOfficeFeeAmount = '', unCashedCaseOfficeFeeAmount = '', deficitCaseOfficeFeeAmount = '', caseNonOfficeFeeAmount = '', cashedCaseNonOfficeFeeAmount = '', unCashedCaseNonOfficeFeeAmount = '';
            contractNo = _contractNo;
            cashedCaseNonOfficeFeeAmount = _cashedCaseNonOfficeFeeAmount;
            contract.Contract.ViewItem(contractNo, paidCaseOfficeFeeAmount, cashedCaseOfficeFeeAmount, unCashedCaseOfficeFeeAmount, deficitCaseOfficeFeeAmount, caseNonOfficeFeeAmount, cashedCaseNonOfficeFeeAmount, unCashedCaseNonOfficeFeeAmount);
        },
        ViewItem_UnCashedCaseNonOfficeFeeAmount: function (_contractNo, _unCashedCaseNonOfficeFeeAmount) {
            var contractNo = '', paidCaseOfficeFeeAmount = '', cashedCaseOfficeFeeAmount = '', unCashedCaseOfficeFeeAmount = '', deficitCaseOfficeFeeAmount = '', caseNonOfficeFeeAmount = '', cashedCaseNonOfficeFeeAmount = '', unCashedCaseNonOfficeFeeAmount = '';
            contractNo = _contractNo;
            unCashedCaseNonOfficeFeeAmount = _unCashedCaseNonOfficeFeeAmount;
            contract.Contract.ViewItem(contractNo, paidCaseOfficeFeeAmount, cashedCaseOfficeFeeAmount, unCashedCaseOfficeFeeAmount, deficitCaseOfficeFeeAmount, caseNonOfficeFeeAmount, cashedCaseNonOfficeFeeAmount, unCashedCaseNonOfficeFeeAmount);
        },
        Delete: function (contractIds) {
            $.showModalConfirmDialog("确定删除？", "contract.Contract.DeleteCallBack", contractIds);
            return true;
        },
        DeleteCallBack: function (contractIds) {
            var data = {
                contractIds: contractIds
            }
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/Contract/ContractDelete", data, function (response) {
                if (response.IsSuccess) {
                    contract.List.ContractList();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });

        },
        Edit: function (contractId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FCM/ContractDraft/Create?contractId=" + contractId;
            addtabs(url, "合同变更");
            //window.open(url);
        },
        ExportToExcel: function () {
            var url = AP_ROOT + AP_PAGE_ID + "/FCM/ContractFileCenter/ContractExportToExcel?contractId=" + $("#Contract_ContractBasicInfo_ContractId").val();
            window.open(url);
        },
        PaymentApply: function (contractId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/AP/PaymentCreate?contractId=" + contractId;
            addtabs(url, "合同付款");
            //window.open(url);
        },
        InvoiceApply: function (customerNo, contractNos) {

            var chkContractObject = $("input[name='chkContractId']:checked")[0];
            var contractStatus = $(chkContractObject).parents("tr").find(".contractStatus").text();

            if (contractStatus == contract.ContractStatus.Archived) {
                $.showTips("合同已归档,不允许开票.", 0, 3)
                return false;
            }

            var url = AP_ROOT + AP_PAGE_ID + "/FAM/Invoice/InvoiceDetailCreate?customerNo=" + customerNo + "&contractNos=" + contractNos;
            addtabs(url, "合同开票");
        },
        Objects: {
            Layout: function () {
                
                var data = {
                    contractId: $("#Contract_ContractBasicInfo_ContractId").val()
                };

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/Contract/ContractObjectList", data, function (response) {
                    if (response.IsSuccess) {
                        ;
                        $("#dv_List").empty();
                        $("#dv_List").html(response.Data);
                        contract.Contract.Objects.List();
                        //contract.ResetSize();

                    }
                });
            },
            List: function () {
                var data = {
                    contractId: $("#Contract_ContractBasicInfo_ContractId").val(),
                    pageNo: $("#PageNo").val(),
                    pageSize: $("#PageSize").val()
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/Contract/ContractObjects", data, function (response) {
                    if (response.IsSuccess) {

                        $("#divContractObjectList").empty();
                        $("#divContractObjectList").html(response.Data);

                        $(".pull-right.page-box.contractObjects").cPaging({
                            totalCount: parseInt($("#TotalCount").val()),
                            pageNo: parseInt($("#PageNo").val()),
                            pageSize: parseInt($("#PageSize").val()),
                            callBack: contract.Contract.Objects.List,
                            callBackArgs: null
                        });

                        var totalCount = parseInt($("#TotalCount").val());

                        if (totalCount > 0) {
                            $("tfoot", "#tblContractObjectList").show();
                        } else {
                            $("tfoot", "#tblContractObjectList").hide();
                        }

                        contract.ResetSize();
                    }
                });
            },
        },
        Files: {
            Layout: function () {
                var data = {
                    contractId: $("#Contract_ContractBasicInfo_ContractId").val()
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFile/ViewContractFileList", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_List").empty();
                        $("#dv_List").html(response.Data);
                        contract.Contract.Files.List();
                        //contract.ResetSize();
                        $.closeLoading();
                    }
                }, true);
            },
            List: function () {
                var data = {
                    contractGuid: $("#Contract_ContractBasicInfo_ContractGuid").val(),
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFile/ContractFiles", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("tbody", "#tblContractFileList").clearRow();
                        $.each(response.Data, function (i, file) {

                            if (AP_PAGE_ID == '4001007') {
                                $("tbody", "#tblContractFileList").addRow(
                                    ++i,
                                    file.UploadUserName,
                                    file.FileName,
                                    file.UploadTime == null ? '' : getDate(convertJsonDateToJSDate(file.UploadTime)),
                                    "<a style='color: #039' href='javascript:void(0);' onclick='javascript:contract.Contract.Files.File.Delete(\"" + file.FileId + "\");'><span>删除</span></a>&nbsp;&nbsp;&nbsp;" +
                                    "<a style='color: #039' href='javascript:void(0);' onclick='javascript:contract.Contract.Files.File.View(\"" + file.ContractGuid + "\",\"" + file.FileGuid + "\",\"" + file.FileName + "\");'><span>查看</span></a>&nbsp;&nbsp;&nbsp;" +
                                    "<a style='color: #039' href='javascript:void(0);' onclick='javascript:contract.Contract.Files.File.Download(\"" + file.FileGuid + "\");'><span>下载</span></a>"
                                );
                            }
                            else {
                                $("tbody", "#tblContractFileList").addRow(
                                    ++i,
                                    file.UploadUserName,
                                    file.FileName,
                                    file.UploadTime == null ? '' : getDate(convertJsonDateToJSDate(file.UploadTime)),
                                    "<a style='color: #039' href='javascript:void(0);' onclick='javascript:contract.Contract.Files.File.View(\"" + file.ContractGuid + "\",\"" + file.FileGuid + "\",\"" + file.FileName + "\");'><span>查看</span></a>&nbsp;&nbsp;&nbsp;" +
                                    "<a style='color: #039' href='javascript:void(0);' onclick='javascript:contract.Contract.Files.File.Download(\"" + file.FileGuid + "\");'><span>下载</span></a>"
                                );
                            }
                        });
                        contract.ResetSize();
                        $.closeLoading();
                    }
                }, true);
            },
            File: {
                Open: function () {
                    var data =
                    {
                        contractGuid: $("#Contract_ContractBasicInfo_ContractGuid").val(),
                    };
                    var url = AP_ROOT + AP_PAGE_ID + "/FCM/ContractFile/ContractFileUpload";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
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
                Upload: function () {

                    if ($("#flContractFile").val() == '') {
                        $.showModalMessageBox("请选择上传文件.");
                        return false;
                    }

                    $('#uploadForm').ajaxSubmit({
                        success: function (response) {
                            $.showModalMessageBox("上传成功.");
                            contract.Draft.Files.File.Close();
                        }
                    });
                },
                View: function (contractId, contractFileId, contractFileName) {

                    if (contractFileId == '' || contractFileName == '') {
                        $.showModalMessageBox("无合同文件.");
                        return false;
                    }

                    var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                    var picfiles = new Array('jpg', 'tif', 'pdf');
                    var extName = contractFileName.substring(contractFileName.lastIndexOf('.') + 1, contractFileName.length);

                    if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                        var path = GV_LS.OfficeOnlineUrl + GV_LS.OnlineUrl + "ContractFiles/ContractFiles/" + contractId + "/" + contractFileName;
                        window.open(path);
                    }
                    else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                        var path = GV_LS.OnlineUrl + "ContractFiles/ContractFiles/" + contractId + "/" + contractFileName;
                        window.open(path);
                    } else {
                        contract.Contract.Files.File.Download(contractFileId);
                    }

                    return true;
                },
                Download: function (contractFileId) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFile/ContractFileDownloadByGuid?contractFileGuid=" + contractFileId);
                    return true;
                },
                Delete: function (fileId) {
                    $.showModalConfirmDialog("确定删除？", "contract.Contract.Files.File.DeleteCallBack", fileId);
                    return true;
                },
                DeleteCallBack: function (fileId) {
                    var data = {
                        fileIds: new Array(fileId)
                    }
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFile/Delete", data, function (response) {
                        if (response.IsSuccess) {
                            contract.Contract.Files.List();
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                },
            }
        },
        Events: {
            Layout: function () {
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractEvent/ContractEventList", null, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_List").empty();
                        $("#dv_List").html(response.Data);
                        contract.Contract.Events.List();
                        $.closeLoading();
                    }
                }, true);
            },
            List: function () {
                var data = {
                    contractGuid: $("#Contract_ContractBasicInfo_ContractGuid").val()
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractEvent/ContractEvents", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $.each(response.Data, function (i, event) {
                            $("tbody", "#tblContractEventList").addRow(
                                ++i,
                                event.Content,
                                event.OperatorName,
                                event.OperateTime == null ? '' : getDate(convertJsonDateToJSDate(event.OperateTime))
                            );
                        });

                        contract.ResetSize();
                        $.closeLoading();
                    }
                }, true);
            },
            Event: {
                Open: function () {

                    var url = AP_ROOT + AP_PAGE_ID + "/FCM/ContractEvent/ContractEvent";
                    $.openLoading();

                    $("<div></div>").load(url, null, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#contractEventModal').modal({ backdrop: 'static', keyboard: false });
                        $('#contractEventModal').on('hidden.bs.modal', function () {
                            $("#contractEventModal").remove();
                        });
                    });
                },
                Close: function () {
                    $('#contractEventModal').modal('hide');
                },
                Create: function () {
                    if ($("#ContractEvent_Content").val() == '') {
                        $.showModalMessageBox("请输入事项内容.");
                        return false;
                    }

                    var data = {
                        contractGuid: $("#Contract_ContractBasicInfo_ContractGuid").val(),
                        content: $("#ContractEvent_Content").val(),
                    }

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractEvent/ContractEventCreate", data, function (response) {
                        if (response.IsSuccess) {
                            $('#contractEventModal').modal('hide');
                            contract.Events.List();
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                }
            },
        },
        Audits: {
            Layout: function () {
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractAudit/ViewContractAuditList", null, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_List").empty();
                        $("#dv_List").html(response.Data);
                        contract.Contract.Audits.List();
                        $.closeLoading();
                    }
                }, true);
            },
            List: function () {
                var data = {
                    contractId: $("#Contract_ContractBasicInfo_ContractId").val()
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractAudit/ContractAudits", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $.each(response.Data, function (i, audit) {
                            $("tbody", "#tblContractAuditList").addRow(
                                ++i,
                                audit.AuditorName,
                                audit.AuditStatusName,
                                audit.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(audit.AuditDate)),
                                audit.AuditContent
                            );
                        });

                        contract.ResetSize();
                        $.closeLoading();
                    }
                }, true);
            },
            Audit: {
                ToAudit: function () {
                    if ($("#Contract_ContractBasicInfo_Auditor").val() == '')
                    {
                        $.showModalMessageBox("请选择审批人.");
                        return false;
                    }
                    var data =
                    {
                        contractId: $("#Contract_ContractBasicInfo_ContractId").val(),
                        auditor: $("#Contract_ContractBasicInfo_Auditor").val(),
                    };
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/Contract/ToAudit", data, function (response) {
                        if (response.IsSuccess) {
                            $.showTips("提交成功.", 0, 3)
                            if ($("#Contract_OfficialDocument_ToAudit").val() == 'true') {
                                window.location = AP_ROOT + "4001001/FCM/ContractDraft/ToOfficialDocumentAudit?contractId=" + $("#Contract_ContractBasicInfo_ContractId").val();
                            }
                            else {
                                window.location = AP_ROOT + "4001001/FCM/Contract/ContractView?contractId=" + $("#Contract_ContractBasicInfo_ContractId").val();
                            }
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                },
                ToAuditCallBack: function (toOfficialDocumentAudit) {
                 
                },
                ViewAudit: function (contractId, contractNo) {

                    var data =
                    {
                        contractId: contractId,
                        contractNo: contractNo
                    };

                    var url = AP_ROOT + AP_PAGE_ID + "/FCM/ContractAudit/ContractAuditList";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#contractAuditListModal').modal({ backdrop: 'static', keyboard: false });
                        $('#contractAuditListModal').on('hidden.bs.modal', function () {
                            $("#contractAuditListModal").remove();
                        });
                    });

                },
                AuditClose: function () {
                    $('#contractAuditListModal').modal('hide');
                },
                Open: function (contractId, contractNo) {

                    var data =
                    {
                        contractId: contractId,
                        contractNo: contractNo
                    };

                    var url = AP_ROOT + AP_PAGE_ID + "/FCM/ContractAudit/ContractAudit";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#contractAuditModal').modal({ backdrop: 'static', keyboard: false });
                        $('#contractAuditModal').on('hidden.bs.modal', function () {
                            $("#contractAuditModal").remove();
                        });
                    });

                },
                Close: function () {
                    $('#contractAuditModal').modal('hide');
                },
                CreateUpdate: function (auditStatus) {
                    if ($("#ContractAudit_AuditContent").val() == '' && auditStatus == '4') {
                        $.showModalMessageBox("请输入审批内容");
                        return false;
                    }

                    if ($("#ContractAudit_AuditContent").val() == '' && auditStatus == '3') {
                        $("#ContractAudit_AuditContent").val('同意');
                    }

                    var data = {};

                    data["ContractAudit.AuditId"] = $("#ContractAudit_AuditId").val();
                    data["ContractAudit.ContractId"] = $("#Contract_ContractBasicInfo_ContractId").val();
                    data["ContractAudit.ContractNo"] = $("#Contract_ContractBasicInfo_ContractNo").val();
                    data["ContractAudit.AuditContent"] = $("#ContractAudit_AuditContent").val();
                    data["ContractAudit.AuditStatus"] = auditStatus;

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractAudit/ContractAuditCreate", data, function (response) {
                        if (response.IsSuccess) {
                            contract.Auditor.PendingList();
                            $.showModalConfirmDialog("审批成功.", 'contract.Contract.Audits.Audit.CreateUpdateCallBack', true, true);

                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                },
                CreateUpdateCallBack: function () {
                    window.location = AP_ROOT + "REDACTED_ARCHIVE_ONLY";
                },
            },
        },
        Selected: function (e) {
            if ($(e).prop('checked') == true) {
                $.checkbox.all("chkContractId");
                $.checkbox.all("chkContractAll");

            } else {
                $.checkbox.not("chkContractId");
                $.checkbox.not("chkContractAll");
            }
        },
        Customer: {

            AddIn: function (customerId,customerNo,customerName)
            {
                $("#Contract_ContractBasicInfo_CustomerId").val(customerId);
                $("#Contract_ContractBasicInfo_CustomerNo").val(customerNo);
                $("#Contract_ContractBasicInfo_CustomerName").val(customerName);
                $("#Contract_ContractBasicInfo_ContractName").val(customerName + "_合同");
            }
        },
    },
    Contracts: {
        List: function () {
            var data = {};
            var url = AP_ROOT + AP_PAGE_ID + "/FCM/Contract/ContractSelectedList";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#contractListModal').modal({ backdrop: 'static', keyboard: false });
                $('#contractListModal').on('hidden.bs.modal', function () {
                    $("#contractListModal").remove();
                });
                $(document).ready(function () {
                    contract.Contracts.ContractSelectedList();
                });
            });
        },
        ContractSelectedList: function () {
            $("#contractListForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/Contract/List", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.ContractList, function (i, c) {
                            $("tbody", "#tblContractList").addRow(
                                "<span class='contractId' style='display:none'>" + c.ContractBasicInfo.ContractId + "</span>"
                                + "<span class='contractStatus' style='display:none'>" + c.ContractBasicInfo.ContractStatus + "</span>"
                                + "<a style='color: #039' href='javascript:void(0);' "
                                + " onclick = 'javascript:contract.Contracts.Contract.Selected(\"" + c.ContractBasicInfo.ContractNo + "\",\"" + c.ContractBasicInfo.CustomerNo + "\",\"" + c.ContractBasicInfo.CustomerName + "\")' > "
                                + c.ContractBasicInfo.ContractNo + "</a>",
                                c.ContractBasicInfo.ContractName,
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.CoordinatorName,
                                c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate))
                            );
                        });

                        $("tfoot", "#tblContractList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.contractlist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: contract.Contracts.ContractSelectedList,
                            callBackArgs: null
                        });

                    } else {

                        $("tfoot", "#tblContractList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        Contract: {
            Selected: function (contractNo,customerNo,customeName) {
                contract.Contracts.Contract.ContractNo.AddIn(contractNo);
                $("#OfficialDocument_Basic_CustomerNo").val(customerNo);
                $("#OfficialDocument_Basic_CustomerName").val(customeName);
                $('#contractListModal').modal('hide');
            },
            ContractNo: {
                AddIn: function (contractNo) {
                    var existsContractNo = false;
                    if ($("a[name='contractno']").length > 0) {
                        return false;
                    }
                    $("a[name='contractno']").each(function () {
                        if ($(this).attr("contractno") == contractno) {
                            existsContractNo = true;
                            return true;
                        }
                    });
                    if (existsContractNo) return true;
                    var $tag = $("<span class='tag label label-info'>"
                        + "<a name='contractno' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                        + " contractno='" + contractNo + "'"
                        + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);'   data-original-title=" + contractNo + " '>" + contractNo + "</a>"
                        + "<span class='contractremove' data-role='remove'></span>"
                        + "</span>");
                    $("#OfficialDocument_ContractNo_Input").before($tag);
                    $tag.after(' ');
                },
                Remove: function (e) {
                    $(e).parent().remove();
                },
                Clear: function () {
                    $("#OfficialDocument_ContractNo_Input").parent().find("span").remove();
                }
            },
        }
    },
    ResetSize: function () {
        if ($("#divContextList").length > 0) {
            $('#divContextList').slimScroll({
                height: '100%'
            });
            $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 22);
        }
        if ($("#divList").length > 0) {
            $("#divList").css("height", $(window).height() - $("#divList").offset().top - 12);
        }
    },
    /**/
    Draft: {
        TotalAmountSet: function () {
            var totalAmount = parseFloat(0);
            var caseOfficeFeeAmount = parseFloat(0);
            var caseNonOfficeFeeAmount = parseFloat(0);
            var caseCommissionFeeAmount = parseFloat(0);
            $("input[name='item_CaseOfficeFeeAmount']").each(
                function () {
                    if ($(this).val() == '' || !$(this).isMoney()) {
                        if ($(this).attr("caseofficefeeamount")) {
                            $(this).val(parseFloat($(this).attr("caseofficefeeamount")));
                        }
                        else {
                            $(this).val(0);
                        }
                    }
                    else {
                        if ($(this).parents("tr").find("#item_PaymentByCustomer").attr("checked") == 'checked') {}
                        else {

                            if ($(this).attr("caseofficefeeinvoicedamount")) {
                                if (parseFloat($(this).attr("caseofficefeeinvoicedamount")) > parseFloat($(this).val()))
                                {
                                    $(this).val(parseFloat($(this).attr("caseofficefeeamount")));
                                }
                            }

                            if ($(this).attr("caseofficefeepaidamount")) {
                                if (parseFloat($(this).attr("caseofficefeepaidamount")) > parseFloat($(this).val())) {
                                    $(this).val(parseFloat($(this).attr("caseofficefeeamount")));
                                }
                            }

                            if ($(this).attr("caseofficefeecashedamount")) {
                                if (parseFloat($(this).attr("caseofficefeecashedamount")) > parseFloat($(this).val())) {
                                    $(this).val(parseFloat($(this).attr("caseofficefeeamount")));
                                }
                            }

                            caseOfficeFeeAmount =  parseFloat(caseOfficeFeeAmount) + parseFloat($(this).val());
                        }
                    }
                }
            );
            $("input[name='item_CaseNonOfficeFeeAmount']").each(
                function () {
                    if ($(this).val() == '' || !$(this).isMoney()) {
                        if ($(this).attr("casenonofficefeeamount")) {
                            $(this).val(parseFloat($(this).attr("casenonofficefeeamount")));
                        }
                        else {
                            $(this).val(0);
                        }
                    }
                    else {
                        if ($(this).parents("tr").find("#item_PaymentByCustomer").attr("checked") == 'checked') { }
                        else {

                            if ($(this).attr("casenonofficefeeinvoicedamount")) {
                                if (parseFloat($(this).attr("casenonofficefeeinvoicedamount")) > parseFloat($(this).val())) {
                                    $(this).val(parseFloat($(this).attr("casenonofficefeeamount")));
                                }
                            }

                            if ($(this).attr("casenonofficefeepaidamount")) {
                                if (parseFloat($(this).attr("casenonofficefeepaidamount")) > parseFloat($(this).val())) {
                                    $(this).val(parseFloat($(this).attr("casenonofficefeeamount")));
                                }
                            }

                            if ($(this).attr("casenonofficefeecashedamount")) {
                                if (parseFloat($(this).attr("casenonofficefeecashedamount")) > parseFloat($(this).val())) {
                                    $(this).val(parseFloat($(this).attr("casenonofficefeeamount")));
                                }
                            }
                            caseNonOfficeFeeAmount += parseFloat($(this).val());
                        }
                    }
                }
            );
            $("input[name='item_CaseCommissionFeeAmount']").each(
                function () {
                    if ($(this).val() == '' || !$(this).isMoney()) {
                        if ($(this).attr("casecommissionfeeamount")) {
                            $(this).val(parseFloat($(this).attr("casecommissionfeeamount")));
                        }
                        else {
                            $(this).val(0);
                        }
                    }
                    else {
                        if ($(this).parents("tr").find("#item_PaymentByCustomer").attr("checked") == 'checked') { }
                        else {

                            if ($(this).attr("casecommissionfeeinvoicedamount")) {
                                if (parseFloat($(this).attr("casecommissionfeeinvoicedamount")) > parseFloat($(this).val())) {
                                    $(this).val(parseFloat($(this).attr("casecommissionfeeamount")));
                                }
                            }

                            if ($(this).attr("casecommissionfeepaidamount")) {
                                if (parseFloat($(this).attr("casecommissionfeepaidamount")) > parseFloat($(this).val())) {
                                    $(this).val(parseFloat($(this).attr("casecommissionfeeamount")));
                                }
                            }

                            if ($(this).attr("casecommissionfeecashedamount")) {
                                if (parseFloat($(this).attr("casecommissionfeecashedamount")) > parseFloat($(this).val())) {
                                    $(this).val(parseFloat($(this).attr("casecommissionfeeamount")));
                                }
                            }

                            caseCommissionFeeAmount += parseFloat($(this).val());
                        }
                    }
                }
            );

            caseOfficeFeeAmount = Math.round(caseOfficeFeeAmount * 100) / 100;
            caseNonOfficeFeeAmount = Math.round(caseNonOfficeFeeAmount * 100) / 100;
            caseCommissionFeeAmount = Math.round(caseCommissionFeeAmount * 100) / 100;
            totalAmount = caseOfficeFeeAmount + caseNonOfficeFeeAmount + caseCommissionFeeAmount;
            totalAmount = Math.round(totalAmount * 100) / 100;
           
            $("#Contract_ContractBasicInfo_TotalAmount").val(totalAmount);
            $("#Contract_ContractBasicInfo_CaseOfficeFeeAmount").val(caseOfficeFeeAmount);
            $("#Contract_ContractBasicInfo_CaseNonOfficeFeeAmount").val(caseNonOfficeFeeAmount);
            $("#Contract_ContractBasicInfo_CaseCommissionAmount").val(caseCommissionFeeAmount);

            $("#Contract_ContractBasicInfo_ARAmount").val(totalAmount);
            $("#Contract_ContractBasicInfo_APAmount").val(caseOfficeFeeAmount + caseCommissionFeeAmount);
            $("#Contract_ContractBasicInfo_UnPaidCaesFeeAmount").val(caseOfficeFeeAmount + caseCommissionFeeAmount);
            $("#Contract_ContractBasicInfo_InvoiceAmount").val(totalAmount);


        },
        CreateUpdate: function (isSubmit) {
            try {

                var dataIsNOk = false;

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

                var data = {};

                data["Contract.ContractBasicInfo.ContractGuid"] = $("#Contract_ContractBasicInfo_ContractGuid").val();
                data["Contract.ContractBasicInfo.AuditDate"] = $("#Contract_ContractBasicInfo_AuditDate").val();
                data["Contract.ContractBasicInfo.GroupId"] = $("#Contract_ContractBasicInfo_GroupId").val();
                data["Contract.ContractBasicInfo.ContractType"] = $("#Contract_ContractBasicInfo_ContractType").val();
                data["Contract.ContractBasicInfo.ChargingType"] = $("#Contract_ContractBasicInfo_ChargingType").val();
                data["Contract.ContractBasicInfo.ContractId"] = $("#Contract_ContractBasicInfo_ContractId").val();
                data["Contract.ContractBasicInfo.ContractNo"] = $("#Contract_ContractBasicInfo_ContractNo").val();
                data["Contract.ContractBasicInfo.ContractName"] = $("#Contract_ContractBasicInfo_ContractName").val();
                data["Contract.ContractBasicInfo.CustomerId"] = $("#Contract_ContractBasicInfo_CustomerId").val();
                data["Contract.ContractBasicInfo.CustomerNo"] = $("#Contract_ContractBasicInfo_CustomerNo").val();
                data["Contract.ContractBasicInfo.RefContractNo"] = $("#Contract_ContractBasicInfo_RefContractNo").val();
                data["Contract.ContractBasicInfo.Remark"] = $("#Contract_ContractBasicInfo_Remark").val();

                if (dataIsNOk) return false;

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractDraft/DraftCreate", data, function (response) {
                    if (response.IsSuccess) {
                        
                        window.location = AP_ROOT + "4001001/FCM/ContractDraft/ToAudit?contractId=" + response.Data.Contract.ContractBasicInfo.ContractId;
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });

            } catch (e) {

            }
        },
        CreateUpdateCallBack: function (isSubmit) {
            window.location = AP_ROOT + "4001002/FCM/Contract/ContractList/";
        },
        Objects: {
            Layout: function () {
                var data = {
                    contractId: $("#Contract_ContractBasicInfo_ContractId").val()
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractDraft/ContractObjectList", data, function (response) {
                    if (response.IsSuccess) {
                        $("#dv_ContractObjectList").empty();
                        $("#dv_ContractObjectList").html(response.Data);
                        contract.Draft.Objects.List();
                    }
                });
            },
            List: function () {

                var data = {
                    contractId: $("#Contract_ContractBasicInfo_ContractId").val(),
                    pageNo: $("#PageNo").val(),
                    pageSize: $("#PageSize").val()
                };

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractDraft/ContractObjects", data, function (response) {
                    if (response.IsSuccess) {
                        $("tbody", "#tblContractObjectList").clearRow();

                        if (response.Data.TotalItemCount > 0) {
                            $.each(response.Data.ContractObjectList, function (i, c) {
                                var tr = '';
                                
                                if (c.CaseOfficeFeeTypeId != null || c.CaseNonOfficeFeeTypeId != null || c.CaseCommissionFeeId != null) {
                                    tr = "<tr>"
                                             + "<td>" + (++i) + "</td>"
                                             + "<td><a style='color:#06C;' href='javascript:void(0);' onclick='javascript:caseInfo.View(" + c.CaseId + ',\"' + c.CaseNo + "\");'>查看案件</a></td>"
                                             + "<td><input class='item_CaseNo form-control' id='item_CaseNo' disabled type='text' value='" + c.CaseNo + "'/><input class='item_CaseId form-control' id='item_CaseId' style='display:none' type='text' caseTypeId=" + c.CaseTypeId + " value='" + (c.CaseId == null ? '' : c.CaseId) + "'></td>"
                                             + "<td><input class='item_CaseRequestNo form-control' disabled id='item_CaseRequestNo' type='text' value='" + (c.CaseRequestNo == null ? '' : c.CaseRequestNo) + "'></td>"
                                             + "<td><input class='item_CaseRequestDate form-control' disabled id='item_CaseRequestDate'  type='text' value='" + (c.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseRequestDate))) + "'></td>"
                                             + "<td><select class='form-control' disabled id='item_CaseOfficeFeeTypeId' caseOfficeFeeTypeId=" + c.CaseOfficeFeeTypeId + " AnnualYear=" + c.AnnualYear + " caseOfficeFeeId=" + c.CaseOfficeFeeId + "><option value='-100'>请选择</option></select></td>"
                                             + "<td><input class='item_CaseOfficeFeeAmount form-control' disabled id='item_CaseOfficeFeeAmount' name='item_CaseOfficeFeeAmount' type='text' value='" + (c.CaseOfficeFeeAmount == null ? 0 : c.CaseOfficeFeeAmount)
                                             + "'  CaseOfficeFeeAmount='" + (c.CaseOfficeFeeAmount == null ? 0 : c.CaseOfficeFeeAmount)
                                             + "'  CaseOfficeFeePaidAmount='" + (c.CaseOfficeFeePaidAmount == null ? 0 : c.CaseOfficeFeePaidAmount)
                                             + "'  CaseOfficeFeeInvoicedAmount='" + (c.CaseOfficeFeeInvoicedAmount == null ? 0 : c.CaseOfficeFeeInvoicedAmount)
                                             + "'  CaseOfficeFeeCashedAmount='" + (c.CaseOfficeFeeCashedAmount == null ? 0 : c.CaseOfficeFeeCashedAmount) + "'></td>"
                                             + "<td><select class='form-control' id='item_CaseFeeAnnualYear' disabled='disabled'><option value='-1'>无</option></select></td>"
                                             + "<td><input class='item_IsFirstYear' disabled='disabled' id='item_IsFirstYear' style='height:20px;width:20px ' type='checkbox' " + (c.IsFirstYear == true ? 'checked' : '') + "></td>"
                                             + "<td><input class='item_PaymentByCustomer' disabled='disabled' id='item_PaymentByCustomer' style='height:20px;width:20px ' type='checkbox' PaymentByCustomer=" + (c.PaymentByCustomer == true ? 'true checked' : 'false') + "></td>"
                                             + "<td><select class='form-control'  id='item_CaseNonOfficeFeeTypeId' disabled caseNonOfficeFeeTypeId=" + c.CaseNonOfficeFeeTypeId + " caseNonOfficeFeeId=" + c.CaseNonOfficeFeeId + "><option value='-200'>请选择</option></select></td>"
                                             + "<td><input class='item_CaseNonOfficeFeeAmount form-control' disabled id='item_CaseNonOfficeFeeAmount'  name='item_CaseNonOfficeFeeAmount'  type='text' value='" + (c.CaseNonOfficeFeeAmount == null ? 0 : c.CaseNonOfficeFeeAmount)
                                             + "' CaseNonOfficeFeeAmount='" + (c.CaseNonOfficeFeeAmount == null ? 0 : c.CaseNonOfficeFeeAmount)
                                             + "' CaseNonOfficeFeePaidAmount='" + (c.CaseNonOfficeFeePaidAmount == null ? 0 : c.CaseNonOfficeFeePaidAmount)
                                             + "' CaseNonOfficeFeeInvoicedAmount='" + (c.CaseNonOfficeFeeInvoicedAmount == null ? 0 : c.CaseNonOfficeFeeInvoicedAmount)
                                             + "' CaseNonOfficeFeeCashedAmount='" + (c.CaseNonOfficeFeeCashedAmount == null ? 0 : c.CaseNonOfficeFeeCashedAmount) + "'>"
                                             + "<td><input class='item_CaseCommissionFeeAmount form-control' disabled id='item_CaseCommissionFeeAmount'  caseCommissionFeeId=" + c.CaseCommissionFeeId + " name='item_CaseCommissionFeeAmount'   type='text' value='" + (c.CaseCommissionFeeAmount == null ? 0 : c.CaseCommissionFeeAmount)
                                             + "'  CaseCommissionFeeAmount='" + (c.CaseCommissionFeeAmount == null ? 0 : c.CaseCommissionFeeAmount)
                                             + "'  CaseCommissionFeePaidAmount='" + (c.CaseCommissionFeePaidAmount == null ? 0 : c.CaseCommissionFeePaidAmount)
                                             + "'  CaseCommissionFeeInvoicedAmount='" + (c.CaseCommissionInvoicedAmount == null ? 0 : c.CaseCommissionFeeInvoicedAmount)
                                             + "'  CaseCommissionFeeCashedAmount='" + (c.CaseCommissionFeeCashedAmount == null ? 0 : c.CaseCommissionFeeCashedAmount) + "'></td>"
                                             + "<td><input class='item_Remark form-control' id='item_Remark'  disabled type='text' value='" + c.Remark + "'></td>"
                                             + "<td><a style='color:green;'  title= '修改' href='javascript:void(0);'><span class='btn_ar_edit glyphicon glyphicon-edit'></span></a>&nbsp;&nbsp;&nbsp;<a  style='color:#06C;' text-overflow: ellipsis; white-space: nowrap;' title= '查看历史' data-toggle='tooltip' data-container='body' data-placement='bottom'  href='javascript:void(0);' batchNo=" + c.BatchNo + " onclick=\"javascript:contract.Draft.Objects.ObjectItem.Log.List(this);\"><span class='btn_ar_history  glyphicon glyphicon-list'></span></a></td>"
                                      + "</tr>";

                                } else {
                                    tr = "<tr>"
                                             + "<td>" + (++i) + "</td>"
                                             + "<td><a style='color:#06C;' href='javascript:void(0);' class='btnCaseSelected' >选择</a>&nbsp;&nbsp;&nbsp;<a  style='color:green;' href='javascript:void(0);' class='btnCaseQuickCreate' >新建</a> </td>"
                                             + "<td><input class='item_CaseNo form-control' id='item_CaseNo' name='item_CaseNo' placeholder='回车' type='text' value=''/><input class='item_CaseId form-control' id='item_CaseId' style='display:none' type='text' value=''></td>"
                                             + "<td><input class='item_CaseRequestNo form-control' id='item_CaseRequestNo' placeholder='回车' type='text' value=''></td>"
                                             + "<td><input class='item_CaseRequestDate form-control' id='item_CaseRequestDate' readonly='True' type='text' value=''></td>"
                                             + "<td><select class='form-control' disable id='item_CaseOfficeFeeTypeId' ><option value='-100'>请选择</option></select></td>"
                                             + "<td><input class='item_CaseOfficeFeeAmount form-control'  id='item_CaseOfficeFeeAmount' name='item_CaseOfficeFeeAmount'  type='text' value='0'></td>"
                                             + "<td><select class='form-control' id='item_CaseFeeAnnualYear' disabled='disabled'><option value='-1'>无</option></select></td>"
                                             + "<td><input class='item_IsFirstYear' disabled='disabled' id='item_IsFirstYear' style='height:20px;width:20px ' type='checkbox'  ></td>"
                                             + "<td><input class='item_PaymentByCustomer'   id='item_PaymentByCustomer' style='height:20px;width:20px ' type='checkbox' ></td>"
                                             + "<td><select class='form-control'  id='item_CaseNonOfficeFeeTypeId'><option value='-200'>请选择</option></select></td>"
                                             + "<td><input class='item_CaseNonOfficeFeeAmount form-control'  id='item_CaseNonOfficeFeeAmount' name='item_CaseNonOfficeFeeAmount'   type='text' value='0'>"
                                             + "<td><input class='item_CaseCommissionFeeAmount form-control'  id='item_CaseCommissionFeeAmount' name='item_CaseCommissionFeeAmount'  type='text' value='0'>"
                                            + "<td><input class='item_Remark form-control' id='item_Remark'  type='text' value=''></td>"
                                             + "<td><a style='color:green;' href='javascript:void(0);'><span class='btn_ar_add glyphicon glyphicon-plus'></span></a>&nbsp;&nbsp;&nbsp;<a  style='color:red;' href='javascript:void(0);'><span class='btn_ar_remove glyphicon glyphicon-remove'></span></a></td>"
                                      + "</tr>";
                                }

                                $('#tblContractObjectList>tbody>tr:last').after(tr);

                            });

                            $("#tblContractObjectList tbody tr").each(function (i, e) {

                                var caseTypeId = $(e).find("#item_CaseId").attr("caseTypeId");

                                if ($(e).find("#item_CaseOfficeFeeTypeId option").length == 1) {
                                    $.each(GV_IPR.CaseFeeTypes, function (j, f) {
                                        if (f.TypeId == '1' && f.FeeTypeId != '-100' && f.CaseTypeId == caseTypeId) {
                                            $(e).find("#item_CaseOfficeFeeTypeId").append('<option value=' + f.FeeTypeId + '>' + f.FeeTypeName + '</option>');
                                        }
                                    });

                                    $(e).find("#item_CaseOfficeFeeTypeId").append('<option value=9999>' + "原官费" + '</option>');
                                    $(e).find("#item_CaseOfficeFeeTypeId").val($(e).find("#item_CaseOfficeFeeTypeId").attr("caseOfficeFeeTypeId"));
                                }

                                if ($(e).find("#item_CaseNonOfficeFeeTypeId option").length == 1) {
                                    $.each(GV_IPR.CaseFeeTypes, function (j, f) {
                                        if (f.TypeId == '2' && f.FeeTypeId != '-200' && f.CaseTypeId == caseTypeId) {
                                            $(e).find("#item_CaseNonOfficeFeeTypeId").append('<option value=' + f.FeeTypeId + '>' + f.FeeTypeName + '</option>');
                                        }
                                    });
                                    $(e).find("#item_CaseNonOfficeFeeTypeId").append('<option value=0>' + "原代理费" + '</option>');
                                    $(e).find("#item_CaseNonOfficeFeeTypeId").val($(e).find("#item_CaseNonOfficeFeeTypeId").attr("caseNonOfficeFeeTypeId"));
                                }

                                var caseOfficeFeeTypeId = $(e).find("#item_CaseOfficeFeeTypeId");
                                contract.Draft.Objects.ObjectItem.InitCaseOfficeFeeAnnualYear(caseOfficeFeeTypeId);

                                $(e).find("#item_CaseFeeAnnualYear").val($(e).find("#item_CaseOfficeFeeTypeId").attr("AnnualYear"));
                                $(e).find("#item_CaseFeeAnnualYear").attr("disabled", "disabled");
                            });

                            contract.Draft.Objects.ObjectItem.BindEvent();

                            if (response.Data.TotalItemCount > 10) {
                                $("tfoot", "#tblContractObjectList").show();

                                $(".pull-right.page-box.contractObjects").cPaging({
                                    totalCount: response.Data.TotalItemCount,
                                    pageNo: response.Data.PageNo,
                                    pageSize: response.Data.PageSize,
                                    callBack: contract.Draft.Objects.List,
                                    callBackArgs: null
                                });
                            }

                        }
                        else {
                            $("tfoot", "#tblContractObjectList").hide();
                        }

                        contract.ResetSize();
                    }
                });
            },
            ObjectItem: {

                BindEvent: function () {
                    /*更新案件按钮*/

                    $(".btnCaseSelected").unbind("click");
                    $(".btnCaseSelected").click(function () {
                        caseInfo.Open(this);
                    });

                    $(".btnCaseQuickCreate").unbind("click");
                    $(".btnCaseQuickCreate").click(function () {
                        //caseInfo.QuickCase.Open(this);
                        caseInfo.Case.Open(this);
                    });

                    $(".btn_ar_add").unbind("click");
                    $(".btn_ar_add").click(function () {
                        contract.Draft.Objects.ObjectItem.Add(this);
                    });

                    $(".btn_ar_remove").unbind("click");
                    $(".btn_ar_remove").click(function () {
                        contract.Draft.Objects.ObjectItem.Remove(this);
                    });

                    $(".btn_ar_edit").unbind("click");
                    $(".btn_ar_edit").click(function () {
                        contract.Draft.Objects.ObjectItem.Edit(this);
                    });

                },
                Add: function (e) {
                    var tr = $(e).parents("tr").clone().show();

                    var index = $($(tr).find("td")[0]).html();

                    $($(tr).find("td")[0]).html(parseInt(index) + 1);
                    $(tr).find(":input[type='text']").val('');
                    $(tr).find(":input[type='hidden']").val('');
                    $(tr).find(":input[type='checkbox']").attr("checked", false);

                    //$(tr).find("#item_CaseTypeId").val($(e).parents("tr").find("#item_CaseTypeId").val());
                    $(tr).find("#item_CaseOfficeFeeAmount").val('0');
                    $(tr).find("#item_CaseOfficeFeeTypeId").removeAttr("caseofficefeetypeid");
                    $(tr).find("#item_CaseOfficeFeeTypeId").removeAttr("caseofficefeeid");
                    $(tr).find("#item_CaseNonOfficeFeeTypeId").removeAttr("casenonofficefeetypeid");
                    $(tr).find("#item_CaseNonOfficeFeeTypeId").removeAttr("casenonofficetypeid");
                    $(tr).find("#item_CaseNonOfficeFeeAmount").val('0');
                    $(tr).find("#item_CaseCommissionFeeAmount").val('0');

                    //$(tr).find("#item_IsFirstYear").removeAttr("checked");
                    //$(tr).find("#item_Remark").val('');

                    //contract.Objects.ObjectItem.InitCaseOfficeFeeType($(tr).find("#item_CaseFeeAnnualYear"));
                    $("#tblContractObjectList").append(tr);

                    contract.Draft.Objects.ObjectItem.BindEvent();

                    return tr;
                },
                Edit: function (e) {
                    var tr = $(e).parents("tr");

                    var caseOfficeFeeInvoicedAmount = parseFloat($(tr).find("#item_CaseOfficeFeeAmount").attr("caseofficefeeinvoicedamount"));
                    var caseOfficeFeePaidAmount = parseFloat($(tr).find("#item_CaseOfficeFeeAmount").attr("caseofficefeepaidamount"));

                    if (caseOfficeFeeInvoicedAmount == 0 && caseOfficeFeePaidAmount == 0) {
                        $(tr).find("#item_PaymentByCustomer").removeAttr("disabled");
                    }

                    $(tr).find("#item_CaseOfficeFeeAmount").removeAttr("disabled");
                    $(tr).find("#item_CaseNonOfficeFeeAmount").removeAttr("disabled");
                    $(tr).find("#item_CaseCommissionFeeAmount").removeAttr("disabled");
                    $(tr).find("#item_CaseOfficeFeeTypeId").removeAttr("disabled");
                    $(tr).find("#item_CaseNonOfficeFeeTypeId").removeAttr("disabled");
                    $(tr).find("#item_CaseFeeAnnualYear").removeAttr("disabled");
                    $(tr).find("#item_Remark").removeAttr("disabled");

                    return tr;
                },
                Clear: function (e) {
                    $(e).parents("tr").find(":input[type='text']").val('');
                    $(e).parents("tr").find(":input[type='hidden']").val('');
                    $(e).parents("tr").find(":input[type='checkbox']").attr("checked", false);
                },
                Remove: function (e) {
                    $(e).parents("tr").remove();
                },
                getCaseBasicCallBack: function (response, trigger) {
                    if (typeof (response) == "undefined" || response == null || !response.IsSuccess) {
                        $.showModalMessageBox(response.Message, null, true);
                        $(trigger).parents("tr").find("#item_CaseId").val('');
                        $(trigger).parents("tr").find("#item_CaseNo").val('');
                        $(trigger).parents("tr").find("#item_CaseRequestNo").val('');
                        return false;
                    }

                    if (typeof (trigger) == "undefined" || trigger == null) {
                        $.showModalMessageBox(response.Message, null, true);
                        $(trigger).parents("tr").find("#item_CaseId").val('');
                        $(trigger).parents("tr").find("#item_CaseNo").val('');
                        $(trigger).parents("tr").find("#item_CaseRequestNo").val('');
                        return false;
                    }
                    //$(trigger).parents("tr").find("#item_CaseTypeId").val(response.Data.CaseBasicInfo.CaseTypeId);
                    $(trigger).parents("tr").find("#item_CaseId").val(response.Data.CaseBasicInfo.CaseId);
                    $(trigger).parents("tr").find("#item_CaseId").attr("caseno", response.Data.CaseBasicInfo.CaseNo);
                    $(trigger).parents("tr").find("#item_CaseNo").val(response.Data.CaseBasicInfo.CaseNo);
                    $(trigger).parents("tr").find("#item_CaseRequestNo").val(response.Data.CaseBasicInfo.CaseRequestNo);

                    var caseFeeTypeId = $(trigger).parents("tr").find("#item_CaseOfficeFeeTypeId");
                    var caseNonFeeTypeId = $(trigger).parents("tr").find("#item_CaseNonOfficeFeeTypeId");

                    contract.Draft.Objects.ObjectItem.InitCaseOfficeFeeType(caseFeeTypeId, response.Data.CaseBasicInfo.CaseTypeId);
                    contract.Draft.Objects.ObjectItem.InitCaseNonOfficeFeeType(caseNonFeeTypeId, response.Data.CaseBasicInfo.CaseTypeId);

                    if (response.Data.CaseBasicInfo.CaseRequestDate == null) {
                        $(trigger).parents("tr").find("#item_CaseRequestDate").val('');
                    } else {
                        $(trigger).parents("tr").find("#item_CaseRequestDate").val(getDate(convertJsonDateToJSDate(response.Data.CaseBasicInfo.CaseRequestDate)));
                    }

                    if (response.Data.CaseBasicInfo.CustomerId != null
                        && response.Data.CaseBasicInfo.CustomerId != ''
                        && $("#Contract_ContractBasicInfo_CustomerId").val() != ''
                        && $("#Contract_ContractBasicInfo_CustomerId").val() != response.Data.CaseBasicInfo.CustomerId) {
                        $.showModalMessageBox("输入的案号,不属该客户下的案件,请确认.", null, true);
                        return false;
                    }
                },

                InitCaseOfficeFeeAnnualYear: function (e) {

                    if (($(e).val() == "11020" || $(e).val() == "21020" || $(e).val() == "31020") && $(e).parents("tr").find("#item_CaseRequestDate").val() == '') {
                        return false;
                    }

                    var selected = $(e).parents("tr").find("#item_CaseFeeAnnualYear");
                    var caseRequestDateStr = $(e).parents("tr").find("#item_CaseRequestDate").val();

                    $(selected).empty();
                    $(selected).removeAttr("disabled");
                    $($(e).parents("tr").find("#item_IsFirstYear")).removeAttr("disabled");
                    if ($(e).val() == "11020" || $(e).val() == "21020" || $(e).val() == "31020") {
                        if (caseRequestDateStr != '') {
                            $(selected).removeAttr("disabled");
                            var caseRequestDate = new Date(caseRequestDateStr);
                            if ($(e).val() == "11020") {
                                for (var i = 1; i <= 20; i++) {
                                    $(selected).append('<option value=' + i + ' annualfrom=' + caseRequestDate.addYears(i - 1).Format("yyyy-MM-dd") + ' annualend=' + caseRequestDate.addYears(i).addDays(-1).Format("yyyy-MM-dd") + '>第' + i + '年度 ' + caseRequestDate.addYears(i - 1).Format("yyyy-MM-dd") + '~' + caseRequestDate.addYears(i).addDays(-1).Format("yyyy-MM-dd") + '</option>');
                                }
                            }
                            else {
                                for (var i = 1; i <= 10; i++) {
                                    $(selected).append('<option value=' + i + ' annualfrom=' + caseRequestDate.addYears(i - 1).Format("yyyy-MM-dd") + ' annualend=' + caseRequestDate.addYears(i).addDays(-1).Format("yyyy-MM-dd") + '>第' + i + '年度 ' + caseRequestDate.addYears(i - 1).Format("yyyy-MM-dd") + '~' + caseRequestDate.addYears(i).addDays(-1).Format("yyyy-MM-dd") + '</option>');
                                }
                            }

                        }
                    } else {
                        $($(e).parents("tr").find("#item_IsFirstYear")).attr("disabled", "disabled");
                        $(selected).attr("disabled", "disabled");
                        $(selected).append('<option value=-1>无</option>');
                    }
                },

                InitCaseOfficeFeeType: function (e, caseTypeId) {
                    $(e).empty();
                    //$(e).removeAttr("disabled");

                    $(e).append('<option value=-100>请选择</option>');


                    $.each(GV_IPR.CaseFeeTypes, function (i, c) {
                        if (c.CaseTypeId == caseTypeId) {
                            if (c.TypeId == 1 && c.FeeTypeId != -100) {
                                $(e).append('<option value=' + c.FeeTypeId + '>' + c.FeeTypeName + '</option>');
                            }
                        }
                    });

                    //$.each(GV_IPR.CaseTypes, function (i, c) {
                    //    if (c.CaseTypeId == caseTypeId) {
                    //        $.each(c.CaseFeeTypeList, function (j, f) {
                    //            if (f.TypeId == 1 &&  f.FeeTypeId != -100)
                    //            {
                    //                $(e).append('<option value=' + f.FeeTypeId + '>' + f.FeeTypeName + '</option>');
                    //            }
                    //        });
                    //    }
                    //});
                },

                InitCaseNonOfficeFeeType: function (e, caseTypeId) {
                    $(e).empty();
                    $(e).append('<option value=-200>请选择</option>');

                    $.each(GV_IPR.CaseFeeTypes, function (i, c) {
                        if (c.CaseTypeId == caseTypeId) {
                            if (c.TypeId == 2 && c.FeeTypeId != -200) {
                                $(e).append('<option value=' + c.FeeTypeId + '>' + c.FeeTypeName + '</option>');
                            }
                        }
                    });
                },

                Log: {
                    List: function (e) {
                        var data = {
                            contractId: $("#Contract_ContractBasicInfo_ContractId").val(),
                            batchNo: $(e).attr("batchNo")
                        };

                        if ($(e).parent().parent().next().find("#tblCaseFeeLogList").length > 0) {
                            $(e).parent().parent().next().remove();
                            return false;
                        }

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/Contract/ContractObjectLogs", data, function (response) {
                            if (response.IsSuccess) {
                                $.openLoading();

                                var table = "<table id='tblCaseFeeLogList' class='table table-hover' style='padding:0px;margin:0px'>"
                                    + "                 <colgroup>"
                                    + "                     <col style='width: 20%'>"
                                    + "                     <col style='width: 10%'>"
                                    + "                     <col style='width: 10%'>"
                                    + "                     <col style='width: 10%'>"
                                    + "                     <col style='width: 10%'>"
                                    + "                     <col style='width: 10%'>"
                                    + "                     <col style='width: 10%'>"
                                    + "                     <col style='width: 10%'>"
                                    + "                     <col style='width: 10%'>"
                                    + "                     <col style='width: 10%'>"
                                    + "                </colgroup>"
                                    + "              <thead> "
                                    + "                  <tr> "
                                    + "                     <th style='text-align: center'>操作时间</th> "
                                    + "                     <th style='text-align: center'>原官费</th> "
                                    + "                     <th style='text-align: center'>原代理费费</th>"
                                    + "                     <th style='text-align: center'>原其他费用</th> "
                                    + "                     <th style='text-align: center'>回款官费</th> "
                                    + "                     <th style='text-align: center'>回款代理费</th> "
                                    + "                     <th style='text-align: center'>回款其他费用</th> "
                                    + "                     <th style='text-align: center'>已付官费</th> "
                                    + "                     <th style='text-align: center'>已付代理费</th> "
                                    + "                     <th style='text-align: center'>已付其他费用</th> "
                                    + "                  </tr> "
                                    + "        </thead> "
                                    + "      <tbody> ";

                                $.each(response.Data, function (i, c) {
                                    var tr = '';
                                    tr = "<tr>"
                                            + "<td>" + (c.OperateTime == null ? 0 : getDateTime(convertJsonDateToJSDate(c.OperateTime))) + "</td>"
                                             + "<td>" + (c.CaseOfficeFeeAmount == null ? 0 : c.CaseOfficeFeeAmount) + "</td>"
                                             + "<td>" + (c.CaseNonOfficeFeeAmount == null ? 0 : c.CaseNonOfficeFeeAmount) + "</td>"
                                             + "<td>" + (c.CaseCommissionFeeAmount == null ? 0 : c.CaseCommissionFeeAmount) + "</td>"
                                             + "<td>" + (c.CaseOfficeFeeCashedAmount == null ? 0 : c.CaseOfficeFeeCashedAmount) + "</td>"
                                             + "<td>" + (c.CaseNonOfficeFeeCashedAmount == null ? 0 : c.CaseNonOfficeFeeCashedAmount) + "</td>"
                                             + "<td>" + (c.CaseCommissionFeeCashedAmount == null ? 0 : c.CaseCommissionFeeCashedAmount) + "</td>"
                                             + "<td>" + (c.CaseOfficeFeePaidAmount == null ? 0 : c.CaseOfficeFeePaidAmount) + "</td>"
                                             + "<td>" + (c.CaseNonOfficeFeePaidAmount == null ? 0 : c.CaseNonOfficeFeePaidAmount) + "</td>"
                                             + "<td>" + (c.CaseCommissionFeePaidAmount == null ? 0 : c.CaseCommissionFeePaidAmount) + "</td>"
                                      + "</tr>";

                                    table += tr;
                                });


                                table += "   </tbody>";
                                table += " </table>";

                                $(e).parent().parent().after("<tr><td colspan='16' style='text-align:right;padding-left:40%;padding-top:0px;padding-bottom:0px;padding-right:0%;'>" + table + "</td></tr>");

                                $.closeLoading();
                            }
                        }, true);
                    },
                }
            },
        },
        Files: {
            Layout: function () {
                var data = {
                    contractId: $("#Contract_ContractBasicInfo_ContractId").val()
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFile/ContractFileList", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_List").empty();
                        $("#dv_List").html(response.Data);
                        contract.Draft.Files.List();
                        //contract.ResetSize();
                        $.closeLoading();
                    }
                }, true);
            },
            List: function () {
                var data = {
                    contractGuid: $("#Contract_ContractBasicInfo_ContractGuid").val(),
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFile/ContractFiles", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        if (response.Data.length > 0) {
                            $.each(response.Data, function (i, file) {
                                $("tbody", "#tblContractFileList").addRow(
                                   "<input type='checkbox' id='chkContractFileId' name='chkContractFileId' class='' name=" + file.FileGuid + "' value=" + file.FileGuid + ">",
                                    ++i,
                                    file.UploadUserName,
                                    file.FileName,
                                    file.UploadTime == null ? '' : getDate(convertJsonDateToJSDate(file.UploadTime)),
                                    "<a style='color: #039' href='javascript:void(0);' onclick='javascript:contract.Contract.Files.File.View(\"" + file.ContractGuid + "\",\"" + file.FileGuid + "\",\"" + file.FileName + "\");'><span>查看</span></a>&nbsp;&nbsp;&nbsp;" +
                                    "<a style='color: #039' href='javascript:void(0);' onclick='javascript:contract.Contract.Files.File.Download(\"" + file.FileGuid + "\");'><span>下载</span></a>",
                                    "<a style='color:green;' href='javascript:void(0);'><span class='btn_contractfile_add glyphicon glyphicon-plus'></span></a>    "
                                );
                            });
                            $(".simple-grid-none-data-wrap").hide();
                        } else {
                            $(".simple-grid-none-data-wrap").show();
                        }
                        contract.ResetSize();
                        $.closeLoading();
                    }
                }, true);
            },
            File: {
                Open: function () {
                    var data =
                    {
                        contractGuid: $("#Contract_ContractBasicInfo_ContractGuid").val(),
                    };
                    var url = AP_ROOT + AP_PAGE_ID + "/FCM/ContractFile/ContractFileUpload";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
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
                Upload: function () {

                    if ($("#flContractFile").val() == '') {
                        $.showModalMessageBox("请选择上传文件.");
                        return false;
                    }

                    $('#uploadForm').ajaxSubmit({
                        success: function (response) {
                            $.showModalMessageBox("上传成功.");
                            contract.Draft.Files.File.Close();
                            
                            contract.Draft.Files.Layout();
                        }
                    });
                },
                FileUpload: function () {
                    if ($("#flContractFile").val() == '') {
                        $.showModalMessageBox("请选择上传文件.");
                        return false;
                    }

                    $('#uploadForm').ajaxSubmit({
                        success: function (response) {
                            if (response.IsSuccess) {
                                $.showModalMessageBox("上传成功.");
                                $.each(response.Data, function (i, f) {
                                    $("#attachments").append("<div  class='margin-top'><span>" + f.FileName + "</span> "
                                        + "<a id='attachmentfile' href='javascript:void(0);' onclick='javascript:contract.Draft.Files.File.DeleteFile(this," + f.FileId + ")'>删除</a>" 
                                        + " <a id='attachmentfile' href='javascript:void(0);' onclick='javascript:contract.Draft.Files.File.View(\"" + f.FileGuid + '\",\"' + f.ContractGuid + '\",\"' + f.FileName + "\")'>查看</a> "
                                        + "</div>");
                                });
                                $("#help-block").hide()
                            } else {
                                $("#help-block").show();
                            }
                        }
                    });
                },
                View: function (contractFileId, contractNo, contractFileName) {
                    if (contractFileId == '' || contractFileName == '') {
                        $.showModalMessageBox("无合同文件.");
                        return false;
                    }

                    var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                    var picfiles = new Array('jpg', 'tif', 'pdf');
                    var extName = contractFileName.substring(contractFileName.lastIndexOf('.') + 1, contractFileName.length);

                    if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                        var path = GV_LS.OfficeOnlineUrl + GV_LS.OnlineUrl + "ContractFiles/ContractFiles/" + contractNo + "/" + contractFileName;
                        window.open(path);
                    }
                    else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                        var path = GV_LS.OnlineUrl + "ContractFiles/ContractFiles/" + contractNo + "/" + contractFileName;
                        window.open(path);
                    } else {
                        contract.Draft.Files.File.Download(contractFileId);
                    }

                    return true;
                },
                Download: function (contractFileId) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFile/ContractFileDownloadByGuid?contractFileGuid=" + contractFileId);
                    return true;
                },
                DeleteFile: function (e, fileId) {
                    var fileIds = new Array();
                    fileIds.push(fileId);
                    var data = {
                        fileIds: fileIds,
                    };
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFile/Delete", data, function (response) {
                        if (response.IsSuccess) {
                            $(e).parent().remove();
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                }
            },
            Selected: function (e) {
                if ($(e).prop('checked') == true) {
                    $.checkbox.all("chkContractFileId");
                    $.checkbox.all("chkContractFileAll");

                } else {
                    $.checkbox.not("chkContractFileId");
                    $.checkbox.not("chkContractFileAll");
                }
            },
        },
        Events: {
            Layout: function () {

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractEvent/ContractEventList", null, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_List").empty();
                        $("#dv_List").html(response.Data);
                        contract.Draft.Events.List();
                        $.closeLoading();
                    }
                }, true);
            },
            List: function () {
                var data = {
                    contractGuid: $("#Contract_ContractBasicInfo_ContractGuid").val()
                };

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractEvent/ContractEvents", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        if (response.Data.length > 0) {
                            $.each(response.Data, function (i, event) {
                                $("tbody", "#tblContractEventList").addRow(
                                    ++i,
                                   event.Content,
                                    event.OperatorName,
                                    event.OperateTime == null ? '' : getDate(convertJsonDateToJSDate(event.OperateTime)),
                                    "<a style='color:green;' href='javascript:void(0);'><span class='btn_contractevent_add glyphicon glyphicon-plus'></span></a>    "
                                );
                            });
                            $(".simple-grid-none-data-wrap").hide();
                        } else {
                            $(".simple-grid-none-data-wrap").show();
                        }
                        contract.ResetSize();
                        $.closeLoading();
                    }
                }, true);
            },
            Event: {
                Open: function () {

                    var url = AP_ROOT + AP_PAGE_ID + "/FCM/ContractEvent/ContractEvent";
                    $.openLoading();

                    $("<div></div>").load(url, null, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#contractEventModal').modal({ backdrop: 'static', keyboard: false });
                        $('#contractEventModal').on('hidden.bs.modal', function () {
                            $("#contractEventModal").remove();
                        });
                    });
                },
                Close: function () {
                    $('#contractEventModal').modal('hide');
                },
                Create: function () {
                    if ($("#ContractEvent_Content").val() == '') {
                        $.showModalMessageBox("请输入事项内容.");
                        return false;
                    }

                    var data = {
                        contractGuid: $("#Contract_ContractBasicInfo_ContractGuid").val(),
                        content: $("#ContractEvent_Content").val(),
                    }

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractEvent/ContractEventCreate", data, function (response) {
                        if (response.IsSuccess) {
                            $('#contractEventModal').modal('hide');
                            contract.Draft.Events.Layout();
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                }
            },
        },
    },

    /*合同归档*/
    Archive: {
        Archive: function (contractId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FCM/ContractArchive/Archive?contractId=" + contractId;
            window.open(url);
        },
        Objects: {
            Layout: function () {
                var data = {
                    contractId: $("#Contract_ContractBasicInfo_ContractId").val()
                };

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractArchive/ContractObjectList", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_ContractObjectList").empty();
                        $("#dv_ContractObjectList").html(response.Data);
                        //contract.ResetSize();
                        $.closeLoading();
                    }
                }, true);
            },

            ObjectItem: {
                Add: function (e) {
                    var tr = $(e).parents("tr").clone().show();

                    var index = $($(tr).find("td")[0]).html();

                    $($(tr).find("td")[0]).html(parseInt(index) + 1);
                    $(tr).find(":input[type='text']").val('');
                    $(tr).find(":input[type='hidden']").val('');
                    $(tr).find(":input[type='checkbox']").attr("checked", false);

                    //$(tr).find("#item_CaseTypeId").val($(e).parents("tr").find("#item_CaseTypeId").val());
                    $(tr).find("#item_CaseOfficeFeeAmount").val('0');
                    $(tr).find("#item_CaseOfficeFeeTypeId").removeAttr("caseofficefeetypeid");
                    $(tr).find("#item_CaseOfficeFeeTypeId").removeAttr("caseofficefeeid");
                    $(tr).find("#item_CaseNonOfficeFeeTypeId").removeAttr("casenonofficefeetypeid");
                    $(tr).find("#item_CaseNonOfficeFeeTypeId").removeAttr("casenonofficetypeid");
                    $(tr).find("#item_CaseNonOfficeFeeAmount").val('0');
                    $(tr).find("#item_CaseCommissionFeeAmount").val('0');

                    //$(tr).find("#item_IsFirstYear").removeAttr("checked");
                    //$(tr).find("#item_Remark").val('');

                    //contract.Objects.ObjectItem.InitCaseOfficeFeeType($(tr).find("#item_CaseFeeAnnualYear"));

                    $("#tblContractObjectList").append(tr);
                    return tr;
                },
                Edit: function (e) {
                    var tr = $(e).parents("tr");

                    $(tr).find("#item_CaseOfficeFeeAmount").removeAttr("disabled");
                    $(tr).find("#item_CaseNonOfficeFeeAmount").removeAttr("disabled");
                    $(tr).find("#item_CaseCommissionFeeAmount").removeAttr("disabled");

                    return tr;
                },
                Clear: function (e) {
                    $(e).parents("tr").find(":input[type='text']").val('');
                    $(e).parents("tr").find(":input[type='hidden']").val('');
                    $(e).parents("tr").find(":input[type='checkbox']").attr("checked", false);
                },
                Remove: function (e) {
                    $(e).parents("tr").remove();
                },
                getCaseBasicCallBack: function (response, trigger) {

                     if (typeof (response) == "undefined" || response == null) {
                        return false;
                    }

                    if (typeof (trigger) == "undefined" || trigger == null) {
                        return false;
                    }
                    //$(trigger).parents("tr").find("#item_CaseTypeId").val(response.Data.CaseBasicInfo.CaseTypeId);
                    $(trigger).parents("tr").find("#item_CaseId").val(response.Data.CaseBasicInfo.CaseId);
                    $(trigger).parents("tr").find("#item_CaseNo").val(response.Data.CaseBasicInfo.CaseNo);
                    $(trigger).parents("tr").find("#item_CaseRequestNo").val(response.Data.CaseBasicInfo.CaseRequestNo);

                    if (response.Data.CaseBasicInfo.CaseRequestDate == null) {
                        $(trigger).parents("tr").find("#item_CaseRequestDate").val('');
                    } else {
                        $(trigger).parents("tr").find("#item_CaseRequestDate").val(getDate(convertJsonDateToJSDate(response.Data.CaseBasicInfo.CaseRequestDate)));
                    }

                    if (response.Data.CaseBasicInfo.CustomerId != null
                        && response.Data.CaseBasicInfo.CustomerId != ''
                        && $("#Contract_ContractBasicInfo_CustomerId").val() != ''
                        && $("#Contract_ContractBasicInfo_CustomerId").val() != response.Data.CaseBasicInfo.CustomerId) {
                        $.showModalMessageBox("输入的案号,不属该客户下的案件,请重新输入.", null, true);
                        return false;
                    }
                },
                InitCaseOfficeFeeType: function (e) {

                    if ((($(e).val() == "11020" || $(e).val() == "21020" || $(e).val() == "31020")) && $(e).parents("tr").find("#item_CaseRequestDate").val() == '') {
                        return false;
                    }

                    var selected = $(e).parents("tr").find("#item_CaseFeeAnnualYear");
                    var caseRequestDateStr = $(e).parents("tr").find("#item_CaseRequestDate").val();

                    $(selected).empty();
                    $(selected).removeAttr("disabled");
                    $($(e).parents("tr").find("#item_IsFirstYear")).removeAttr("disabled");
                    if (($(e).val() == "11020" || $(e).val() == "21020" || $(e).val() == "31020")) {
                        if (caseRequestDateStr != '') {
                            $(selected).removeAttr("disabled");
                            var caseRequestDate = new Date(caseRequestDateStr);
                            for (var i = 1; i <= 20; i++) {
                                $(selected).append('<option value=' + i + ' annualfrom=' + caseRequestDate.addYears(i - 1).Format("yyyy-MM-dd") + ' annualend=' + caseRequestDate.addYears(i).addDays(-1).Format("yyyy-MM-dd") + '>第' + i + '年度 ' + caseRequestDate.addYears(i - 1).Format("yyyy-MM-dd") + '~' + caseRequestDate.addYears(i).addDays(-1).Format("yyyy-MM-dd") + '</option>');
                            }
                        }
                    } else {
                        $($(e).parents("tr").find("#item_IsFirstYear")).attr("disabled", "disabled");
                        $(selected).attr("disabled", "disabled");
                        $(selected).append('<option value=-1>无</option>');
                    }
                },
            },
        },
        List: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/Contract/List", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.ContractList, function (i, c) {
                            $("tbody", "#tblContractList").addRow(
                                "<a href='javascript:void(0);' onclick='javascript:contract.Archive.Archive(" + c.ContractBasicInfo.ContractId + ")'>完结</a>&nbsp;&nbsp;",
                                c.ContractBasicInfo.ContractNo,
                                c.ContractBasicInfo.ContractName,
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.TotalAmount,
                                c.ContractBasicInfo.CashedAmount,
                                c.ContractBasicInfo.ARAmount,
                                c.ContractBasicInfo.BusinessOwnerName,
                                c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                                //c.ContractBasicInfo.CustomerNo,
                                c.ContractBasicInfo.CustomerName
                            );
                        });

                        $("tfoot", "#tblContractList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.contractlist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: contract.Archive.List,
                            callBackArgs: null
                        });
                    } else {

                        $("tfoot", "#tblContractList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        Archived: function (contractId) {
            $.showModalConfirmDialog("归档后,该合同将不允许继续新增案件及费用,确认归档?.", 'contract.Archive.ArchivedCallBack', contractId);
        },
        ArchivedCallBack: function (contractId) {
            try {
                var data = { contractId: contractId };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractArchive/Archived", data, function (response) {
                    if (response.IsSuccess) {
                        contract.List.ContractList();
                        $.showTips("归档成功.", 0, 3)
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });

            } catch (e) {
            }
        },
    },

    /*合同列表*/
    List: {
        BindMenu: function () {

            $('#contractgridSection').contextMenu('contractMenu', {
                menuStyle: {
                    width: '152px'
                },

                itemStyle: {
                    width: '150px'
                },

                bindings: {
                    'view': function (t, e) {
                        var contractId = $(e).find("span").text();
                        if (contractId == '') {
                            $.showModalMessageBox("请选择合同.");
                            return false;
                        }

                        contract.Contract.View(contractId);
                    },
                    'edit': function (t, e) {
                        var contractId = $(e).find("span").text();
                        if (contractId == '') {
                            $.showModalMessageBox("请选择合同.");
                            return false;
                        }

                        contract.Contract.Edit(contractId);

                        return true;
                    },

                    'paymentapply': function (t, e) {
                        var contractId = $(e).find("span").text();
                        if (contractId == '') {
                            $.showModalMessageBox("请选择合同.");
                            return false;
                        }

                        contract.Contract.PaymentApply(contractId);

                        return true;
                    },

                    'invoiceapply': function (t, e) {
                        var contractId = $(e).find("span").text();
                        if (contractId == '') {
                            $.showModalMessageBox("请选择合同.");
                            return false;
                        }

                        contract.Contract.InvoiceApply(contractId);

                        return true;
                    },
                },
                onContextMenu: function (e) {
                    return true;
                },
                onShowMenu: function (e, menu) {

                    if ($(e.target).parents("tr").find(".contractId").hasClass("contractId")) {

                        var contractId = $(e.target).parents("tr").find(".contractId").text();
                        var contractStatus = $(e.target).parents("tr").find(".contractStatus").text();
                        if (contractStatus == contract.ContractStatus.A) {
                            $('#view', menu).append("<span style='display:none'>" + contractId + "</span>");
                            $('#edit', menu).append("<span style='display:none'>" + contractId + "</span>");
                            $('#paymentapply', menu).append("<span style='display:none'>" + contractId + "</span>");
                            $('#invoiceapply', menu).append("<span style='display:none'>" + contractId + "</span>");
                        }
                        else {
                            $('#view', menu).append("<span style='display:none'>" + contractId + "</span>");
                            $('#edit', menu).append("<span style='display:none'>" + contractId + "</span>");
                            $('#invoiceapply', menu).append("<span style='display:none'>" + contractId + "</span>");
                            $('#paymentapply', menu).remove();
                        }
                        //if ($("#SearchCondition_PageId").val() == '4001002') {
                        //    var contractId = $(e.target).parents("tr").find(".contractId").text();
                        //    var contractStatus = $(e.target).parents("tr").find(".contractStatus").text();
                        //    if (contractStatus == contract.ContractStatus.A) {
                        //        $('#view', menu).append("<span style='display:none'>" + contractId + "</span>");
                        //        $('#edit', menu).append("<span style='display:none'>" + contractId + "</span>");
                        //        $('#paymentapply', menu).append("<span style='display:none'>" + contractId + "</span>");
                        //        $('#invoiceapply', menu).append("<span style='display:none'>" + contractId + "</span>");
                        //    }
                        //    else {
                        //        $('#view', menu).append("<span style='display:none'>" + contractId + "</span>");
                        //        $('#edit', menu).append("<span style='display:none'>" + contractId + "</span>");
                        //        //$('#paymentapply,#invoiceapply', menu).remove();
                        //    }
                        //}
                        //else {
                        //    var contractId = $(e.target).parents("tr").find(".contractId").text();
                        //    $('#view', menu).append("<span style='display:none'>" + contractId + "</span>");
                        //    $('#edit,#paymentapply,#invoiceapply', menu).remove();
                        //}
                    }
                    else {
                        $('#view,#edit,#paymentapply,#invoiceapply', menu).remove();
                    }

                    return menu;
                }
            });
        },
        ContractList: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/Contract/List", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $("tbody", "#tblContractList").addRow(
                            '',
                            '',
                            '',
                            '',
                            '',
                            '',
                            "<span style='font-weight:bold'>" + response.Data.TotalPaidCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + response.Data.TotalCashedCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + response.Data.TotalUnCashedCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + response.Data.TotalDeficitCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + response.Data.TotalCaseNonOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + response.Data.TotalCashedCaseNonOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + response.Data.TotalUnCashedCaseNonOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + response.Data.TotalCaseCommissionFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + response.Data.TotalPaidCaseCommissionFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + response.Data.TotalUnPaidCaseCommissionFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + response.Data.TotalInvoicedAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + response.Data.TotalUnInvoicedAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + response.Data.TotalInvoiceOverAmount.toFixed(2) + "</span>"

                        );
                        var totalPaidCaseOfficeFeeAmount = 0;
                        var totalCashedCaseOfficeFeeAmount = 0;
                        var totalUnCashedCaseOfficeFeeAmount = 0;
                        var totalDeficitCaseOfficeFeeAmount = 0;
                        var totalCaseNonOfficeFeeAmount = 0;
                        var totalCashedCaseNonOfficeFeeAmount = 0;
                        var totalUnCashedCaseNonOfficeFeeAmount = 0;
                        var totalCaseCommissionFeeAmount = 0;
                        var totalCashedCaseCommissionFeeAmount = 0;
                        var totalPaidCaseCommissionFeeAmount = 0;
                        var totalUnPaidCaseCommissionFeeAmount = 0;
                        var totalInvoicedAmount = 0;
                        var totalInvoiceOverAmount = 0;
                        var totalUnInvoicedAmount = 0;
                        $.each(response.Data.ContractList, function (i, c) {
                            totalPaidCaseOfficeFeeAmount += c.ContractBasicInfo.PaidCaseOfficeFeeAmount;
                            totalCashedCaseOfficeFeeAmount += c.ContractBasicInfo.CashedCaseOfficeFeeAmount;
                            totalUnCashedCaseOfficeFeeAmount += c.ContractBasicInfo.UnCashedCaseOfficeFeeAmount;
                            totalDeficitCaseOfficeFeeAmount += c.ContractBasicInfo.DeficitCaseOfficeFeeAmount;
                            totalCaseNonOfficeFeeAmount += c.ContractBasicInfo.CaseNonOfficeFeeAmount;
                            totalCashedCaseNonOfficeFeeAmount += c.ContractBasicInfo.CashedCaseNonOfficeFeeAmount;
                            totalUnCashedCaseNonOfficeFeeAmount += c.ContractBasicInfo.UnCashedCaseNonOfficeFeeAmount;
                            totalCaseCommissionFeeAmount += c.ContractBasicInfo.CaseCommissionFeeAmount;
                            totalPaidCaseCommissionFeeAmount += c.ContractBasicInfo.PaidCaseCommissionFeeAmount;
                            totalUnPaidCaseCommissionFeeAmount += c.ContractBasicInfo.UnPaidCaseCommissionFeeAmount;
                            totalInvoicedAmount += c.ContractBasicInfo.InvoicedAmount;
                            totalInvoiceOverAmount += c.ContractBasicInfo.InvoiceOverAmount;
                            totalUnInvoicedAmount += c.ContractBasicInfo.UnInvoicedAmount;
 
                            $("tbody", "#tblContractList").addRow(
                               "<input id='chkContractId' name='chkContractId'  type='checkbox'  value=" + c.ContractBasicInfo.ContractId + "  customerNo='" + c.ContractBasicInfo.CustomerNo + "'  contractNo='" + c.ContractBasicInfo.ContractNo + "'>",
                               "<span class='contractId' style='display:none'>" + c.ContractBasicInfo.ContractId + "</span>"
                               + "<span class='contractStatus' style='display:none'>" + c.ContractBasicInfo.ContractStatus + "</span>"
                               + "<a style='color: #039' href='javascript:void(0);' onclick='javascript:contract.Contract.View(" + c.ContractBasicInfo.ContractId + ")' >" + c.ContractBasicInfo.ContractNo + "</a>",
                                c.ContractBasicInfo.ContractName,
                                c.ContractBasicInfo.GroupIdName,
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.BusinessOwnerName,
                                c.ContractBasicInfo.PaidCaseOfficeFeeAmount,
                                c.ContractBasicInfo.CashedCaseOfficeFeeAmount,
                                c.ContractBasicInfo.UnCashedCaseOfficeFeeAmount,
                                c.ContractBasicInfo.DeficitCaseOfficeFeeAmount,
                                c.ContractBasicInfo.CaseNonOfficeFeeAmount,
                                c.ContractBasicInfo.CashedCaseNonOfficeFeeAmount,
                                c.ContractBasicInfo.UnCashedCaseNonOfficeFeeAmount,
                                c.ContractBasicInfo.CaseCommissionFeeAmount,
                                c.ContractBasicInfo.PaidCaseCommissionFeeAmount,
                                c.ContractBasicInfo.UnPaidCaseCommissionFeeAmount,
                                c.ContractBasicInfo.InvoicedAmount,
                                c.ContractBasicInfo.UnInvoicedAmount,
                                c.ContractBasicInfo.InvoiceOverAmount
                            );
                        });

                        $("tbody", "#tblContractList").addRow(
                            '',
                            '',
                            '',
                            '',
                            '',
                            '',
                            "<span style='font-weight:bold'>" + totalPaidCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + totalCashedCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + totalUnCashedCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + totalDeficitCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + totalCaseNonOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + totalCashedCaseNonOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + totalUnCashedCaseNonOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + totalCaseCommissionFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + totalPaidCaseCommissionFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + totalUnPaidCaseCommissionFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + totalInvoicedAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + totalUnInvoicedAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + totalInvoiceOverAmount.toFixed(2) + "</span>"
                        );


                        $("tfoot", "#tblContractList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.contractlist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: contract.List.ContractList,
                            callBackArgs: null
                        });

                        contract.List.BindMenu();

                    } else {

                        $("tfoot", "#tblContractList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        ContractListExportToExcel: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFileCenter/ContractListExportToExcel", function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFileCenter/ContractListExportToExcelDownload?fileName=" + response.Data);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        ARList: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/AR/List", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();

                        var total_Amount = 0;
                        var total_CashedAmount = 0;
                        var total_ARCaseNonOfficeFeeAmount = 0;
                        var total_UnCashedAdvancedCaseOfficeFeeAmount = 0;

                        $("tbody", "#tblContractList").addRow(
                        '',
                        '',
                        '',
                        '',
                        "<span style='font-weight:bold'> " + response.Data.TotalPaidCaseOfficeFeeAmount.toFixed(2) + "</span>",
                        "<span style='font-weight:bold'> " + response.Data.TotalCashedCaseOfficeFeeAmount.toFixed(2) + "</span>",
                        "<span style='font-weight:bold'><a href='javascript:void(0);' onclick='javascript:contract.Contract.ViewItem_TotalUnCashedCaseOfficeFeeAmount(\"" + response.Data.TotalUnCashedCaseOfficeFeeAmount.toFixed(2) + "\")'>" + response.Data.TotalUnCashedCaseOfficeFeeAmount.toFixed(2) + "</a></span>",
                        "<span style='font-weight:bold'><a href='javascript:void(0);' onclick='javascript:contract.Contract.ViewItem_TotalDeficitCaseOfficeFeeAmount(\"" + response.Data.TotalDeficitCaseOfficeFeeAmount.toFixed(2) + "\")'>" + response.Data.TotalDeficitCaseOfficeFeeAmount.toFixed(2) + "</a></span>",
                        "<span style='font-weight:bold'> " + response.Data.TotalCaseNonOfficeFeeAmount.toFixed(2) + "</span>",
                        "<span style='font-weight:bold'> " + response.Data.TotalCashedCaseNonOfficeFeeAmount.toFixed(2) + "</span>",
                        "<span style='font-weight:bold'><a href='javascript:void(0);' onclick='javascript:contract.Contract.ViewItem_TotalUnCashedCaseNonOfficeFeeAmount(\"" + response.Data.TotalUnCashedCaseNonOfficeFeeAmount.toFixed(2) + "\")'>" + response.Data.TotalUnCashedCaseNonOfficeFeeAmount.toFixed(2) + "</a></span>",
                        '',
                        '',
                        '',
                        ''
                    );

                        var totalPaidCaseOfficeFeeAmount = 0;
                        var totalCashedCaseOfficeFeeAmount = 0;
                        var totalUnCashedCaseOfficeFeeAmount = 0;
                        var totalDeficitCaseOfficeFeeAmount = 0;
                        var totalCaseNonOfficeFeeAmount = 0;
                        var totalCashedCaseNonOfficeFeeAmount = 0;
                        var totalUnCashedCaseNonOfficeFeeAmount = 0;
                        var totalCaseCommissionFeeAmount = 0;
                        var totalCashedCaseCommissionFeeAmount = 0;
                        var totalPaidCaseCommissionFeeAmount = 0;
                        var totalUnPaidCaseCommissionFeeAmount = 0;
                        var totalInvoicedAmount = 0;
                        var totalInvoiceOverAmount = 0;
                        var totalUnInvoicedAmount = 0;

                        $.each(response.Data.ContractList, function (i, c) {

                            totalPaidCaseOfficeFeeAmount += c.ContractBasicInfo.PaidCaseOfficeFeeAmount;
                            totalCashedCaseOfficeFeeAmount += c.ContractBasicInfo.CashedCaseOfficeFeeAmount;
                            totalUnCashedCaseOfficeFeeAmount += c.ContractBasicInfo.UnCashedCaseOfficeFeeAmount;
                            totalDeficitCaseOfficeFeeAmount += c.ContractBasicInfo.DeficitCaseOfficeFeeAmount;
                            totalCaseNonOfficeFeeAmount += c.ContractBasicInfo.CaseNonOfficeFeeAmount;
                            totalCashedCaseNonOfficeFeeAmount += c.ContractBasicInfo.CashedCaseNonOfficeFeeAmount;
                            totalUnCashedCaseNonOfficeFeeAmount += c.ContractBasicInfo.UnCashedCaseNonOfficeFeeAmount;
                            totalCaseCommissionFeeAmount += c.ContractBasicInfo.CaseCommissionFeeAmount;
                            totalPaidCaseCommissionFeeAmount += c.ContractBasicInfo.PaidCaseCommissionFeeAmount;
                            totalUnPaidCaseCommissionFeeAmount += c.ContractBasicInfo.UnPaidCaseCommissionFeeAmount;
                            totalInvoicedAmount += c.ContractBasicInfo.InvoicedAmount;
                            totalInvoiceOverAmount += c.ContractBasicInfo.InvoiceOverAmount;
                            totalUnInvoicedAmount += c.ContractBasicInfo.UnInvoicedAmount;

                            $("tbody", "#tblContractList").addRow(

                                "<input id='chkContractId' name='chkContractId'  type='checkbox' value=" + c.ContractBasicInfo.ContractId + ">",
                                "<a href='javascript:void(0);' onclick='javascript:contract.Contract.ViewItem(\"" + c.ContractBasicInfo.ContractNo + "\")'>" + c.ContractBasicInfo.ContractNo + "</a>",
                                c.ContractBasicInfo.ContractName,
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.PaidCaseOfficeFeeAmount.toFixed(2),
                                c.ContractBasicInfo.CashedCaseOfficeFeeAmount.toFixed(2),
                                "<a href='javascript:void(0);' onclick='javascript:contract.Contract.ViewItem_UnCashedCaseOfficeFeeAmount(\"" + c.ContractBasicInfo.ContractNo + "\",\"" + c.ContractBasicInfo.UnCashedCaseOfficeFeeAmount.toFixed(2) + "\")'>" + c.ContractBasicInfo.UnCashedCaseOfficeFeeAmount.toFixed(2) + "</a>",
                                "<a href='javascript:void(0);' onclick='javascript:contract.Contract.ViewItem_DeficitCaseOfficeFeeAmount(\"" + c.ContractBasicInfo.ContractNo + "\",\"" + c.ContractBasicInfo.DeficitCaseOfficeFeeAmount.toFixed(2) + "\")'>" + c.ContractBasicInfo.DeficitCaseOfficeFeeAmount.toFixed(2) + "</a>",
                                c.ContractBasicInfo.CaseNonOfficeFeeAmount.toFixed(2),
                                c.ContractBasicInfo.CashedCaseNonOfficeFeeAmount.toFixed(2),
                                "<a href='javascript:void(0);' onclick='javascript:contract.Contract.ViewItem_UnCashedCaseNonOfficeFeeAmount(\"" + c.ContractBasicInfo.ContractNo + "\",\"" + c.ContractBasicInfo.UnCashedCaseNonOfficeFeeAmount.toFixed(2) + "\")'>" + c.ContractBasicInfo.UnCashedCaseNonOfficeFeeAmount.toFixed(2) + "</a>",
                                c.ContractBasicInfo.BusinessOwnerName,
                                c.ContractBasicInfo.CoordinatorName,
                                c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                                c.ContractBasicInfo.CustomerName
                            );
                        });

                        $("tbody", "#tblContractList").addRow(
                            '',
                            '',
                            '',
                            '',
                            "<span style='font-weight:bold'>" + totalPaidCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + totalCashedCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + totalUnCashedCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + totalDeficitCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + totalCaseNonOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + totalCashedCaseNonOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold'>" + totalUnCashedCaseNonOfficeFeeAmount.toFixed(2) + "</span>",
                            '',
                            '',
                            '',
                            ''
                        );


                        $("tfoot", "#tblContractList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.contractlist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: contract.List.ARList,
                            callBackArgs: null
                        });
                    } else {

                        $("tfoot", "#tblContractList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        ARListExportToExcel: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFileCenter/ContractARListExportToExcel", function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFileCenter/ContractARListExportToExcelDownload?fileName=" + response.Data);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        ARItemList: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/AR/ItemList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0 ) {
                        $(".info_inall.layoutfix").show();
                        var contractNo = '';
                        $("tbody", "#tblContractList").addRow(
                            '',
                            '',
                            '',
                            "<span style='font-weight:bold;text-align:right'>" + response.Data.TotalPaidCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold;text-align:right'>" + response.Data.TotalCashedCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold;text-align:right'>" + response.Data.TotalUnCashedCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold;text-align:right'>" + response.Data.TotalDeficitCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold;text-align:right'>" + response.Data.TotalCaseNonOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold;text-align:right'>" + response.Data.TotalCashedCaseNonOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold;text-align:right'>" + response.Data.TotalUnCashedCaseNonOfficeFeeAmount.toFixed(2) + "</span>",
                            '',
                            '',
                            '',
                            '',
                            '',
                            '',
                            '',
                            '',
                            ''
                        );

                        var totalPaidCaseOfficeFeeAmount = 0;
                        var totalCashedCaseOfficeFeeAmount = 0;
                        var totalUnCashedCaseOfficeFeeAmount = 0;
                        var totalDeficitCaseOfficeFeeAmount = 0;
                        var totalCaseNonOfficeFeeAmount = 0;
                        var totalCashedCaseNonOfficeFeeAmount = 0;
                        var totalUnCashedCaseNonOfficeFeeAmount = 0;
                        var totalCaseCommissionFeeAmount = 0;
                        var totalCashedCaseCommissionFeeAmount = 0;
                        var totalPaidCaseCommissionFeeAmount = 0;
                        var totalUnPaidCaseCommissionFeeAmount = 0;
                        var totalInvoicedAmount = 0;
                        var totalInvoiceOverAmount = 0;
                        var totalUnInvoicedAmount = 0;

                        if (response.Data.ContractList != null && response.Data.ContractList.length >0)
                        {
                            $.each(response.Data.ContractList, function (i, c) {
                                $.each(c.ContractObjectList, function (j, contractObject) {

                                    var tr = '';
                                    var caseTypeName = contractObject.CaseTypeId == null ? '' : $.lsCaseType.getCaseTypeName(contractObject.CaseTypeId);
                                    var caseFeeTypeName = contractObject.CaseFeeTypeId == null ? '' : $.lsCaseFeeType.getCaseFeeTypeName(contractObject.CaseFeeTypeId);
                                    var casePhaseName = contractObject.CasePhaseId == null ? '' : $.lsCasePhase.getcasePhaseName(contractObject.CasePhaseId);
                                    if (contractNo != c.ContractBasicInfo.ContractNo) {

                                        totalPaidCaseOfficeFeeAmount += c.ContractBasicInfo.PaidCaseOfficeFeeAmount;
                                        totalCashedCaseOfficeFeeAmount += c.ContractBasicInfo.CashedCaseOfficeFeeAmount;
                                        totalUnCashedCaseOfficeFeeAmount += c.ContractBasicInfo.UnCashedCaseOfficeFeeAmount;
                                        totalDeficitCaseOfficeFeeAmount += c.ContractBasicInfo.DeficitCaseOfficeFeeAmount;
                                        totalCaseNonOfficeFeeAmount += c.ContractBasicInfo.CaseNonOfficeFeeAmount;
                                        totalCashedCaseNonOfficeFeeAmount += c.ContractBasicInfo.CashedCaseNonOfficeFeeAmount;
                                        totalUnCashedCaseNonOfficeFeeAmount += c.ContractBasicInfo.UnCashedCaseNonOfficeFeeAmount;
                                        totalCaseCommissionFeeAmount += c.ContractBasicInfo.CaseCommissionFeeAmount;
                                        totalPaidCaseCommissionFeeAmount += c.ContractBasicInfo.PaidCaseCommissionFeeAmount;
                                        totalUnPaidCaseCommissionFeeAmount += c.ContractBasicInfo.UnPaidCaseCommissionFeeAmount;
                                        totalInvoicedAmount += c.ContractBasicInfo.InvoicedAmount;
                                        totalInvoiceOverAmount += c.ContractBasicInfo.InvoiceOverAmount;
                                        totalUnInvoicedAmount += c.ContractBasicInfo.UnInvoicedAmount;

                                        tr = "<tr>"
                                            + "<td><input type='checkbox'' id='chkContractId' name='chkContractId'></td>"
                                            + "<td><a style='color: #039' href='javascript:void(0);' onclick='javascript:contract.Contract.View(" + c.ContractBasicInfo.ContractId + ")' >" + c.ContractBasicInfo.ContractNo + "</a></td>"
                                            + "<td style='text-align: left'>" + c.ContractBasicInfo.ContractName + "</td>"
                                            + "<td style='text-align: right'>" + c.ContractBasicInfo.PaidCaseOfficeFeeAmount.toFixed(2) + "</td>"
                                            + "<td style='text-align: right'>" + c.ContractBasicInfo.CashedCaseOfficeFeeAmount.toFixed(2) + "</td>"
                                            + "<td style='text-align: right'>" + c.ContractBasicInfo.UnCashedCaseOfficeFeeAmount.toFixed(2) + "</td>"
                                            + "<td style='text-align: right'>" + c.ContractBasicInfo.DeficitCaseOfficeFeeAmount.toFixed(2) + "</td>"
                                            + "<td style='text-align: right'>" + c.ContractBasicInfo.CaseNonOfficeFeeAmount.toFixed(2) + "</td>"
                                            + "<td style='text-align: right'>" + c.ContractBasicInfo.CashedCaseNonOfficeFeeAmount.toFixed(2) + "</td>"
                                            + "<td style='text-align: right'>" + c.ContractBasicInfo.UnCashedCaseNonOfficeFeeAmount.toFixed(2) + "</td>"
                                            + "<td style='text-align: center'>" + "<a href='javascript:void(0)' onclick='javascript:$.case.View(\"" + contractObject.CaseNo + "\")'>" + contractObject.CaseNo + "</a>" + "</td>"
                                            + "<td style='text-align: center'>" + casePhaseName + "</td>"
                                            + "<td style='text-align: center'>" + caseTypeName + "</td>"
                                            + "<td style='text-align: center'>" + caseFeeTypeName + "</td>"
                                            + "<td style='text-align: right'>" + (contractObject.CaseFeeAmount == null ? 0 : contractObject.CaseFeeAmount.toFixed(2)) + "</td>"
                                            + "<td style='text-align: right'>" + contractObject.CaseFeeCashedAmount.toFixed(2) + "</td>"
                                            + "<td style='text-align: right'>" + (contractObject.CaseFeeAmount - contractObject.CaseFeeCashedAmount).toFixed(2) + "</td>"
                                            + "</tr>";
                                        contractNo = c.ContractBasicInfo.ContractNo;
                                    } else {
                                        tr = "<tr>"
                                            + "<td></td>"
                                            + "<td></td>"
                                            + "<td></td>"
                                            + "<td></td>"
                                            + "<td></td>"
                                            + "<td></td>"
                                            + "<td></td>"
                                            + "<td></td>"
                                            + "<td></td>"
                                            + "<td></td>"
                                            + "<td>" + "<a href='javascript:void(0)' onclick='javascript:$.case.View(\"" + contractObject.CaseNo + "\")'>" + contractObject.CaseNo + "</a>" + "</td>"
                                            + "<td style='text-align: center'>" + casePhaseName + "</td>"
                                            + "<td>" + caseTypeName + "</td>"
                                            + "<td>" + caseFeeTypeName + "</td>"
                                            + "<td style='text-align: right'>" + (contractObject.CaseFeeAmount == null ? 0 : contractObject.CaseFeeAmount.toFixed(2)) + "</td>"
                                            + "<td style='text-align: right'>" + contractObject.CaseFeeCashedAmount.toFixed(2) + "</td>"
                                            + "<td style='text-align: right'>" + (contractObject.CaseFeeAmount - contractObject.CaseFeeCashedAmount).toFixed(2) + "</td>"
                                            + "</tr>";
                                    }

                                    $("tbody", "#tblContractList").append(tr);

                                });
                            });
                        }

                        $("tbody", "#tblContractList").addRow(
                            '',
                            '',
                            '',
                            "<span style='font-weight:bold;text-align:right'>" + totalPaidCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold;text-align:right'>" + totalCashedCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold;text-align:right'>" + totalUnCashedCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold;text-align:right'>" + totalDeficitCaseOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold;text-align:right'>" + totalCaseNonOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold;text-align:right'>" + totalCashedCaseNonOfficeFeeAmount.toFixed(2) + "</span>",
                            "<span style='font-weight:bold;text-align:right'>" + totalUnCashedCaseNonOfficeFeeAmount.toFixed(2) + "</span>",
                            '',
                            '',
                            '',
                            '',
                            '',
                            '',
                            '',
                            '',
                            ''
                        );

                        $("tfoot", "#tblContractList").show();
                        $(".simple-grid-none-data-wrap").hide();
                        $(".pull-right.page-box.contractlist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: contract.List.ARItemList,
                            callBackArgs: null
                        });
                    } else {
                        $("tfoot", "#tblContractList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        ARItemListExportToExcel: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFileCenter/ContractARItemListExportToExcel", function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFileCenter/ContractARItemListExportToExcelDownload?fileName=" + response.Data);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
    },

    /*合同列表 我审批的合同*/
    Auditor: {
        Audit: function (contractId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FCM/ContractAudit/Audit?contractId=" + contractId;
            window.open(url);
        },
        ApprovedList: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractAudit/ApprovedList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.ContractList, function (i, c) {
                            $("tbody", "#tblContractList").addRow(
                                 "<input id='chkContractId' name='chkContractId'  type='checkbox' value=" + c.ContractBasicInfo.ContractId + ">",
                                c.ContractBasicInfo.ContractNo,
                                c.ContractBasicInfo.ContractName,
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.TotalAmount,
                                c.ContractBasicInfo.CashedAmount,
                                c.ContractBasicInfo.ARCaseNonOfficeFeeAmount,
                                c.ContractBasicInfo.UnCashedAdvancedCaseOfficeFeeAmount,
                                c.ContractBasicInfo.BusinessOwnerName,
                                c.ContractBasicInfo.CoordinatorName,
                                c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                                c.ContractBasicInfo.CustomerNo,
                                c.ContractBasicInfo.CustomerName
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
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractAudit/RejectedList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.ContractList, function (i, c) {
                            $("tbody", "#tblContractList").addRow(
                                 "<input id='chkContractId' name='chkContractId'  type='checkbox' value=" + c.ContractBasicInfo.ContractId + ">",
                                c.ContractBasicInfo.ContractNo,
                                c.ContractBasicInfo.ContractName,
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.TotalAmount,
                                c.ContractBasicInfo.CashedAmount,
                                c.ContractBasicInfo.ARCaseNonOfficeFeeAmount,
                                c.ContractBasicInfo.UnCashedAdvancedCaseOfficeFeeAmount,
                                c.ContractBasicInfo.BusinessOwnerName,
                                c.ContractBasicInfo.CoordinatorName,
                                c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                                c.ContractBasicInfo.CustomerNo,
                                c.ContractBasicInfo.CustomerName
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
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractAudit/PendingList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.ContractList, function (i, c) {
                            $("tbody", "#tblContractList").addRow(
                                 "<input id='chkContractId' name='chkContractId'  type='checkbox' value=" + c.ContractBasicInfo.ContractId + ">",
                                "<a href='javascript:void(0);' onclick='javascript:contract.Auditor.Audit(" + c.ContractBasicInfo.ContractId + ")'>" + c.ContractBasicInfo.ContractNo + "</a>",
                                c.ContractBasicInfo.ContractName,
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.TotalAmount,
                                c.ContractBasicInfo.CashedAmount,
                                c.ContractBasicInfo.ARCaseNonOfficeFeeAmount,
                                c.ContractBasicInfo.UnCashedAdvancedCaseOfficeFeeAmount,
                                c.ContractBasicInfo.BusinessOwnerName,
                                c.ContractBasicInfo.CoordinatorName,
                                c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                                c.ContractBasicInfo.CustomerNo,
                                c.ContractBasicInfo.CustomerName
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

        ContractPendingListExportToExcel: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFileCenter/ContractPendingListExportToExcel", function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFileCenter/ContractListExportToExcelDownload?fileName=" + response.Data);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        ContractRejectedListExportToExcel: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFileCenter/ContractRejectedListExportToExcel", function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFileCenter/ContractListExportToExcelDownload?fileName=" + response.Data);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        ContractApprovedListExportToExcel: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFileCenter/ContractApprovedListExportToExcel", function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFileCenter/ContractListExportToExcelDownload?fileName=" + response.Data);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
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

    var businessOwner = new AssociateUser(
        $("#divAssociateUserList"),
        $("#SearchCondition_BusinessOwner"),
        $("#SearchCondition_BusinessOwnerName"),
        null
    );

    $("#Case_CaseBasicInfo_ProcuratorName").off().on("click", function () {
        $("#hidUserId").val("Case_CaseBasicInfo_Procurator");
        $("#hidUserName").val("Case_CaseBasicInfo_ProcuratorName");
        $("#divUserList").find("input:checkbox").each(function () {
            $(this).removeAttr("checked");
        });

        $("#divUserList").off().css({
            "position": "absolute",
            "left": $(this).position().left + 2,
            "top": $(this).position().top + 32,
            "z-index": 1200
        }).show();
        return false;
    });

    $(".customerremove").off().on("click", function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        caseInfo.CaseCustomer.Remove(this);
    });

    //    
    //    $("#hidUserId").val("Case_CaseBasicInfo_Procurator");
    //    $("#hidUserName").val("Case_CaseBasicInfo_ProcuratorName");
    //    $("#divUserList").css({
    //        "position": "absolute",
    //        "left": $("#Case_CaseBasicInfo_ProcuratorName").position().left + 16,
    //        "top": $("#Case_CaseBasicInfo_ProcuratorName").position().top + 70,
    //        "z-index": 1200
    //    }).toggle();
    //    return false;
    //});

    $("#divUserList").find("li").off().on("click", function (e) {
        if ($(e.target).is("lable")) {
            e.stopPropagation();
            return false;
        }
        var currentSelectedControl = $("#hidUserName").val();
        var currentSelectedIdControl = $("#hidUserId").val();

        if ($(this).attr("id") == 'btnAllUnSelected') {
            $("#" + currentSelectedControl).val('');
            return false;
        } else if ($(this).attr("id") == 'btnAllSelected') {
            $("#" + currentSelectedControl).val('');
            return false;
        }

        $("#" + currentSelectedControl).val('');
        $("#" + currentSelectedIdControl).val('');

        var usernames = '';
        var userids = '';

        $("#divUserList").find("input:checkbox").each(function () {
            if ($(this).attr("checked") == 'checked') {
                usernames += $(this).attr("username") + ";";
                userids += $(this).attr("userid") + ";";
            }
        });

        $("#" + currentSelectedControl).val(usernames.substring(0, usernames.length - 1));
        $("#" + currentSelectedIdControl).val(userids.substring(0, userids.length - 1));

        e.stopPropagation();

        return true;
    });

    $(document).click(function () {
        $("#divUserList").off().hide();
        $("#divAuditorList").off().hide();
        
        $("#divAssociateUserList").off().hide();
        $("#divAssociateApplicantList").off().hide();

    });

    $(window).resize(function () {
        contract.ResetSize();
    });

    contract.ResetSize();

    $("#btnContractSearch").click(function () {
        contract.List.ContractList();
    });

    $("#btnContractListExportToExcel").click(function () {
        contract.List.ContractListExportToExcel();
    });

    $("#btnPendingSearch").click(function () {
        contract.Auditor.PendingList();
    });

    $("#btnContractPendingListExportToExcel").click(function () {
        contract.Auditor.ContractPendingListExportToExcel();
    });

    $("#btnRejectedSearch").click(function () {
        contract.Auditor.RejectedList();
    });

    $("#btnContractRejectedListExportToExcel").click(function () {
        contract.Auditor.ContractRejectedListExportToExcel();
    });

    $("#btnApprovedSearch").click(function () {
        contract.Auditor.ApprovedList();
    });

    $("#btnContractApprovedListExportToExcel").click(function () {
        contract.Auditor.ContractApprovedListExportToExcel();
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

    $("#btnContractArchiveListSearch").off().on("click", function () {
        contract.Archive.List();
    });

    $("#btnARListSearch").click(function () {
        contract.List.ARList();
    });

    $("#btnARListExportToExcel").click(function () {
        contract.List.ARListExportToExcel();
    });

    $("#btnARItemListSearch").click(function () {
        contract.List.ARItemList();
    });

    $("#btnARItemListExportToExcel").click(function () {
        contract.List.ARItemListExportToExcel();
    });

    $("#btnContractAuditClose,#btnContractAuditCancel").off().on("click", function () {
        contract.Audit.Close();
    });

    $("#btnContractAuditListClose,#btnContractAuditListCancel").off().on("click", function () {
        contract.Audit.AuditClose();
    });

    $("#item_CaseOfficeFeeAmount").off().on("change", function () {
        contract.Draft.TotalAmountSet();
    });

    $("#item_CaseNonOfficeFeeAmount").off().on("change", function () {
        contract.Draft.TotalAmountSet();
    });

    $("#item_CaseCommissionFeeAmount").off().on("change", function () {
        contract.Draft.TotalAmountSet();
    });

    $("#item_PaymentByCustomer").off().on("change", function () {
        contract.Draft.TotalAmountSet();
    });

    $(document).off('change', '#flDraftContractFile').on('change', '#flDraftContractFile', function () {
        contract.Draft.Files.File.FileUpload();
    });

    $(document).off('change', '#flFile').on('change', '#flFile', function () {
        $("#txtFilePath").val($("#flFile").val());
    });

    $(document).off('click', '#btnFileUpload').on('click', '#btnFileUpload', function () {
        $("#flDraftContractFile").trigger("click");
    });

    $(document).off('click', '#btnContractView').on('click', '#btnContractView', function () {
        var contractIds = $.checkbox.vals("chkContractId");
        if (contractIds.length == 0) {
            $.showModalMessageBox("请选择合同.");
            return false;
        }
        contract.Contract.View(contractIds[0]);
    });

    $(document).off('click', '#btnContractDelete').on('click', '#btnContractDelete', function () {
        var contractIds = $.checkbox.vals("chkContractId");
        if (contractIds.length == 0) {
            $.showModalMessageBox("请选择合同.");
            return false;
        }
        contract.Contract.Delete(contractIds);
    });

    $(document).off('click', '#btnContractEdit').on('click', '#btnContractEdit', function () {
        var contractIds = $.checkbox.vals("chkContractId");
        if (contractIds.length == 0) {
            $.showModalMessageBox("请选择合同.");
            return false;
        }

        var chkContractObject = $("input[name='chkContractId']:checked")[0];
        var contractStatus = $(chkContractObject).parents("tr").find(".contractStatus").text();

        if (contractStatus == contract.ContractStatus.Archived) {
            $.showTips("合同已归档,不允许变更.", 0, 3)
            return false;
        }

        contract.Contract.Edit(contractIds[0]);
    });

    $(document).off('click', '#btnContractPaymentApply').on('click', '#btnContractPaymentApply', function () {
        var contractIds = $.checkbox.vals("chkContractId");
        if (contractIds.length == 0) {
            $.showModalMessageBox("请选择合同.");
            return false;
        }

        var chkContractObject = $("input[name='chkContractId']:checked")[0];
        var contractStatus = $(chkContractObject).parents("tr").find(".contractStatus").text();

        if (contractStatus == contract.ContractStatus.Archived) {
            $.showTips("合同已归档,不允许付款.", 0, 3)
            return false;
        }
        contract.Contract.PaymentApply(contractIds[0]);
    });

    $(document).off('click', '#btnContractInvoiceApply').on('click', '#btnContractInvoiceApply', function () {
        var contractIds = $.checkbox.vals("chkContractId");
        if (contractIds.length == 0) {
            $.showModalMessageBox("请选择合同.");
            return false;
        }

        var chkContractObject = $("input[name='chkContractId']:checked")[0];
        var contractStatus = $(chkContractObject).parents("tr").find(".contractStatus").text();

        if (contractStatus == contract.ContractStatus.Archived) {
            $.showTips("合同已归档,不允许开票.", 0, 3)
            return false;
        }
        
        var customerNos = [];
        var contractNos = [];

        $("input[name='chkContractId']:checked").each(
            function () {
                if ($.inArray($(this).attr("customerNo"), customerNos) > -1) {
                } else {
                    customerNos.push($(this).attr("customerNo"));
                }
                contractNos.push($(this).attr("contractNo"));
            }
        );

        if (customerNos.length > 1)
        {
            $.showModalMessageBox("请选择同一客户下的合同.");
            return false;
        }

        contract.Contract.InvoiceApply(customerNos[0], contractNos.join(","));
    });

    $(document).off('click', '#btnCaseCreate').on('click', '#btnCaseCreate', function () {
        var contractIds = $.checkbox.vals("chkContractId");
        if (contractIds.length == 0) {
            $.showModalMessageBox("请选择合同.");
            return false;
        }

        var chkContractObject = $("input[name='chkContractId']:checked")[0];
        var contractStatus = $(chkContractObject).parents("tr").find(".contractStatus").text();

        if (contractStatus == contract.ContractStatus.Archived) {
            $.showTips("合同已归档,不允许新建案件.", 0, 3)
            return false;
        }

        caseInfo.QuickCase.Open(contractIds[0]);
    });

    $(document).off('click', '#btnTaskCreate').on('click', '#btnTaskCreate', function () {
        var contractIds = $.checkbox.vals("chkContractId");
        if (contractIds.length == 0) {
            $.showModalMessageBox("请选择合同.");
            return false;
        }
        var chkContractObject = $("input[name='chkContractId']:checked")[0];
        var contractStatus = $(chkContractObject).parents("tr").find(".contractStatus").text();

        if (contractStatus == contract.ContractStatus.Archived) {
            $.showTips("合同已归档,不允许新建调查任务.", 0, 3)
            return false;
        }

        var url = AP_ROOT + "1401001001/CIT/Investigation/Create?contractId=" + contractIds[0];
        addtabs(url, "新建调查任务");
    });

    $(document).off('click', '#btnQuickCreateCase').on('click', '#btnQuickCreateCase', function () {
        var contractIds = $.checkbox.vals("chkContractId");
        if (contractIds.length == 0) {
            $.showModalMessageBox("请选择合同.");
            return false;
        }
        var caseTypeId = $("#Case_Basic_CaseTypeId").val();

        var chkContractObject = $("input[name='chkContractId']:checked")[0];
        var contractStatus = $(chkContractObject).parents("tr").find(".contractStatus").text();

        if (contractStatus == contract.ContractStatus.Archived) {
            $.showTips("合同已归档,不允许新建案件.", 0, 3)
            return false;
        }

        caseInfo.QuickCase.Create(contractIds[0], caseTypeId);
    });

    $(document).off('click', '#btnContractArchive').on('click', '#btnContractArchive', function () {
        var contractIds = $.checkbox.vals("chkContractId");
        if (contractIds.length == 0) {
            $.showModalMessageBox("请选择合同.");
            return false;
        }

        var chkContractObject = $("input[name='chkContractId']:checked")[0];
        var contractStatus = $(chkContractObject).parents("tr").find(".contractStatus").text();

        if (contractStatus == contract.ContractStatus.Archived) {
            $.showTips("合同已是归档状态.", 0, 3)
            return false;
        }

        contract.Archive.Archived(contractIds[0], contract.Archive.ArchivedCallBack);
    });
});