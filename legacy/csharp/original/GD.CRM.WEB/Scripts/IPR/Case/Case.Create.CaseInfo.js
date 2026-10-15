//基本信息操作

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

var contract = {
    Contract: {
        View: function (contractId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FCM/Contract/ContractView?contractId=" + contractId;
            window.open(url);
        },
        Files: {
            List: function (contractId) {
                var data = {
                    contractId: contractId
                };

                var url = AP_ROOT + AP_PAGE_ID + "/FCM/ContractFile/ContractFileListOnModal";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#contractFileListModal').modal({ backdrop: 'static', keyboard: false });
                    $('#contractFileListModal').on('hidden.bs.modal', function () {
                        $("#contractFileListModal").remove();
                    });
                });
            },
            Close: function () {
                $('#contractFileListModal').modal('hide');
            },
            File: {

                View: function (contractFileId, contractNo, contractFileName) {

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
                        contract.Draft.ContractFile.Download(contractFileId);
                    }

                    return true;
                },
                Download: function (contractFileId) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/FCM/ContractFile/ContractFileDownloadByGuid?contractFileGuid=" + contractFileId);
                    return true;
                },
            }
        },
    }
}

var caseInfo = {

    Init: function () {
        caseInfo.InitCaseType();

        if ($("#CurrentSelectedListTypeId").val() == '2') {
            jQuery($("#btnARCaseFeeList")).click();
        }
        else if ($("#CurrentSelectedListTypeId").val() == '3') {
            jQuery($("#btnAPCaseFeeList")).click();
        }
        else if ($("#CurrentSelectedListTypeId").val() == '4') {
            jQuery($("#btnCaseAssistedFeeList")).click();
        }
        else if ($("#CurrentSelectedListTypeId").val() == '5') {
            jQuery($("#btnCaseCustomerContactsList")).click();
        }
        else if ($("#CurrentSelectedListTypeId").val() == '6') {
            jQuery($("#btnCaseLogList")).click();
        }
        else if ($("#CurrentSelectedListTypeId").val() == '7') {
            jQuery($("#btnCaseTaskList")).click();
        }
        else {
            jQuery($("#btnCaseFileList")).click();
        }
    },

    ViewOnly: function () {
        $(":input", "#caseForm").each(function () {
            $(this).attr("disabled", "disabled");
        });

        $("#btnCaseCreateNew").attr("disabled", "disabled");
        $("#btnCaseRenewal").attr("disabled", "disabled");
        $("#btnCaseCreateUpdate").attr("disabled", "disabled");

        if ($("#btnCaseCreateNew").length) {
            //有新建权限
            $("#btnCaseCreateNew").removeAttr("disabled");
        }

        if ($("#btnCaseRenewal").length) {
            //有更新权限
            $("#btnCaseRenewal").removeAttr("disabled");
        }
    },

    Edit: function () {
        $(":input", "#caseForm").each(function () {
            $(this).removeAttr("disabled");
        });

        if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) > 0) {
            $("#Case_CaseBasicInfo_CaseTypeId").attr("disabled", "disabled");
            $("#Case_CaseBasicInfo_CaseOfficerName").attr("disabled", "disabled");
            $("#Case_CaseBasicInfo_Deadline").attr("disabled", "disabled");
        }

        $("#Case_CaseBasicInfo_HasPriority").removeAttr("disabled");
        $("#Case_CaseBasicInfo_HasForeign").removeAttr("disabled");

        $("#btnCaseCreateNew").removeAttr("disabled");
        $("#btnCaseCreateUpdate").removeAttr("disabled");
        $("#btnCaseRenewal").attr("disabled", "disabled");

        $("#ulApplicant>li>div>i").each(function () {
            $(this).attr("class", "unlink fa fa-times");
        });
    },

    CreateCompletedNew: function () {
        var caseId = { caseId: 0 };
        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseInfo", caseId, function (response) {
            $(".viewFramework-product-body").html("");
            if (!response.IsSuccess) {
                $.showModalMessageBox(response.Message);
                return false;
            }
            if (response.Data == null) {
                return false;
            }
            $(".viewFramework-product-body").html(response.Data);

            caseInfo.Edit();
        }, false);
    },

    InitCaseBasic: function () {
        var data = { caseId: $("#Case_CaseBasicInfo_CaseId").val() };
        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/GetCaseBasic", data, function (response) {
            if (response.IsSuccess && response.Data && response.Data != "") {
                $("#Case_CaseBasicInfo_CasePhaseId").val(response.Data.CaseBasicInfo.CasePhaseId);
                $("#Case_CaseBasicInfo_CaseRequestDate").val(response.Data.CaseBasicInfo.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(response.Data.CaseBasicInfo.CaseRequestDate)));
                $("#Case_CaseBasicInfo_CaseRequestNo").val(response.Data.CaseBasicInfo.CaseRequestNo);
                $("#Case_CaseBasicInfo_AuthorizationDate").val(response.Data.CaseBasicInfo.AuthorizationDate == null ? '' : getDate(convertJsonDateToJSDate(response.Data.CaseBasicInfo.AuthorizationDate)));
                $("#Case_CaseBasicInfo_FirstInstanceDate").val(response.Data.CaseBasicInfo.FirstInstanceDate == null ? '' : getDate(convertJsonDateToJSDate(response.Data.CaseBasicInfo.FirstInstanceDate)));
                $("#Case_CaseBasicInfo_Deadline").val(response.Data.CaseBasicInfo.Deadline == null ? '' : getDate(convertJsonDateToJSDate(response.Data.CaseBasicInfo.Deadline)));
            } else {
            }
        });
    },

    InitCaseType: function () {

        var caseTypeId = $("#Case_CaseBasicInfo_CaseTypeId").val();

        $("#lblCaseInventor").html("发 明 人");
        $("#lbl_Case_CaseBasicInfo_HasPrivateInventor").html("不公发明人");

        $(".spanHasRelief").hide();
        $(".spanHasAdvanced").hide();
        $(".spanHasRequestView").hide();
        $(".spanHasPrivateInventor").hide();
        $(".spanHasIU").hide();

        $(".spanTrademarkIdsPriority").hide();

        $(".spanHasTradeColorProtected").hide();
        $(".spanHasTradeVoiceProtected").hide();
        $(".spanHasTrade3DProtected").hide();

        $("#divCaseIcon").hide();

        if (caseTypeId == '3') {
            $(".spanCaseInventor").hide();
            $(".spanCaseDesigner").show();
            $(".spanCaseCommon").show();
            $(".spanTrademarkIds").hide();
            $(".spanCaseCopyright").hide();
        } else if (caseTypeId == '4') {
            $(".spanCaseCommon").hide();
            $(".spanCaseInventor").hide();
            $(".spanCaseDesigner").hide();
            $(".spanCaseCopyright").hide();
            $(".spanTrademarkIds").show();
            $("#divCaseIcon").show();
            $(".spanPatent").hide();

        } else if (caseTypeId == '5') {
            $("#lblCaseRequestNo").html("受 理 号");
            $("#lblCaseRequestDate").html("受 理 日");
            //$("#lblCaseCardNo").html("登记号：");
            $(".spanCaseCommon").show();
            $(".spanCaseInventor").show();
            $(".spanCaseCommon.spanCardNo").hide();
            $(".spanTrademarkIds").hide();
            $(".spanCaseCopyright").show();

            $("#lblCaseInventor").html("作    者");
        }
        else {
            $(".spanCaseCommon").show();
            $(".spanCaseInventor").show();
            $(".spanCaseDesigner").hide();
            $(".spanTrademarkIds").hide();
            $(".spanCaseCopyright").hide();
            $(".spanPatent").hide();
            //$(".spanTrademarkIds").hide();
        }

        if (caseTypeId == '1') {
            $(".spanHasRelief").show();
            $(".spanHasAdvanced").show();
            $(".spanHasRequestView").show();
            $(".spanHasIU").show();
            $(".spanHasPrivateInventor").show();

        } else if (caseTypeId == '2') {
            $(".spanHasRelief").show();
            $(".spanHasIU").show();
            $(".spanHasPrivateInventor").show();
        }
        else if (caseTypeId == '3') {
            $(".spanHasRelief").show();
            $(".spanHasPrivateInventor").show();
            $(".spanHasTradeColorProtected").show();

            $("#lbl_Case_CaseBasicInfo_HasPrivateInventor").html("不公开设计人");
        }
        else if (caseTypeId == '4') {
            if ($("#Case_CaseBasicInfo_HasPriority").prop("checked") == true) {
                $(".spanTrademarkIdsPriority").show();
            }
            $(".spanHasTradeColorProtected").show();
            $(".spanHasTradeVoiceProtected").show();
            $(".spanHasTrade3DProtected").show();
        }

        if (caseTypeId == '1' || caseTypeId == '2' || caseTypeId == '3') {
            $("#lblCaseTypeIdName").html("专利名称");
        }
        else {
            $("#lblCaseTypeIdName").html($("#Case_CaseBasicInfo_CaseTypeId").find("option:selected").text() + "名称");
        }

        var casePhaseId = $("#Case_CaseBasicInfo_CasePhaseId").val();

        $("#Case_CaseBasicInfo_CasePhaseId").empty();

        $.each(GV_IPR.CaseTypes, function (i, c) {
            if (c.CaseTypeId == caseTypeId) {
                $.each(c.CasePhaseList, function (j, f) {
                    if (casePhaseId == f.CasePhaseId) {
                        $("#Case_CaseBasicInfo_CasePhaseId").append("<option selected value='" + f.CasePhaseId + "'>" + f.CasePhaseName + "</option>");
                    } else {
                        $("#Case_CaseBasicInfo_CasePhaseId").append("<option value='" + f.CasePhaseId + "'>" + f.CasePhaseName + "</option>");
                    }
                });

                return true;
            }
        });

        if ($("#Case_CaseBasicInfo_CaseId").val() != '' && parseInt($("#Case_CaseBasicInfo_CaseId").val()) > 0) {
            //$("#Case_CaseBasicInfo_CaseTypeId")
            $("#Case_CaseBasicInfo_CaseTypeId").attr("disabled", "disabled");
        }

        caseInfo.ResetSize();
    },

    InitCasePhaseType: function () {
        var casePhaseTypeId = $("#Case_CaseBasicInfo_CasePhaseId").val();
        if (casePhaseTypeId == "1" && $("#Case_CaseBasicInfo_CaseRegisterDate").val() == '') {
            //立案待处理
            var today = new Date();
            $("#Case_CaseBasicInfo_CaseRegisterDate").val(today.getFullYear() + "-" + (today.getMonth() + 1) + "-" + today.getDate());
        }
    },

    CreateUpdateBefore: function () {
        var data = { caseId: $("#Case_CaseBasicInfo_CaseId").val() };
        var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseDeadLine";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);

            //设置
            if ($("#Case_CaseBasicInfo_Deadline").val() != '') {
                $("#Case_Deadline").val($("#Case_CaseBasicInfo_Deadline").val());
            }

            if ($("#Case_CaseBasicInfo_CaseOfficer").val() != '') {
                $("#Case_CaseOfficer").val($("#Case_CaseBasicInfo_CaseOfficer").val());
                $("#Case_CaseOfficerName").val($("#Case_CaseBasicInfo_CaseOfficerName").val());
            }

            var caseOfficer = new AssociateUser(
                    $("#divAssociateUserList_DeadLine"),
                    $("#Case_CaseOfficer"),
                    $("#Case_CaseOfficerName"),
                    null
                );

            $('#caseDeadLineModal').modal({ backdrop: 'static', keyboard: false });
            $('#caseDeadLineModal').on('hidden.bs.modal', function () {
                $("#caseDeadLineModal").remove();
            });
        });
    },

    CreateUpdateDeadline: function () {

        if ($("#Case_Deadline").val() == '') {
            $.showModalMessageBox("请输入截止日期.");
            return false;
        }

        if ($("#Case_CaseOfficer").val() == '') {
            $.showModalMessageBox("请选择处理人.");
            return false;
        }

        if ($("#Case_CaseBasicInfo_ReminderDate").val() != '' &&
            $("#Case_Deadline").val() >= $("#Case_CaseBasicInfo_ReminderDate").val()) {
            $.showModalMessageBox("截止日期应小于最近提醒日期.");
            return false;
        }

        $("#Case_CaseBasicInfo_Deadline").val($("#Case_Deadline").val());
        $("#Case_CaseBasicInfo_CaseOfficer").val($("#Case_CaseOfficer").val());
        $("#Case_CaseBasicInfo_CaseOfficerName").val($("#Case_CaseOfficerName").val());
        $("#Case_CaseBasicInfo_PushOfficerRemak").val($("#Case_PushOfficerRemak").val());

        caseInfo.Close();

        caseInfo.CreateUpdate(true);
    },

    CreateUpdate: function (isSubmit) {
        try {

            var regd = /^.*[-—；，\\\'\"<>]+.*$/;

            if ($("#Case_CaseBasicInfo_CaseTypeId").val() == 1
            || $("#Case_CaseBasicInfo_CaseTypeId").val() == 2
            || $("#Case_CaseBasicInfo_CaseTypeId").val() == 3) {

                var caseName = $("#Case_CaseBasicInfo_CaseName").val().replace(/\s+/g, "");
                if (caseName == '') {
                    $("#Case_CaseBasicInfo_CaseName").val(caseName);
                    $.showModalMessageBox("请输入专利名称.");
                    return false;
                }

                if ($("#Case_CaseBasicInfo_Procurator").val() == '') {
                    $.showModalMessageBox("请选择代理人.");
                    return false;
                }

                if ($("#Case_CaseBasicInfo_Copywriter").val() == '') {
                    $.showModalMessageBox("请选择撰稿人.");
                    return false;
                }

                if ($("#Case_CaseBasicInfo_CardNo").val() == '') {
                    $.showModalMessageBox("请输入证件号码.");
                    return false;
                }

                if (regd.test($("#Case_CaseBasicInfo_CardNo").val())) {
                    $.showModalMessageBox("证件号码禁止输入 <  >  \"   \'  \\ 半角字符，请检查.");
                    return false;
                }
              

                if ($("#Case_CaseBasicInfo_CaseTypeId").val() == 1
                || $("#Case_CaseBasicInfo_CaseTypeId").val() == 2) {
 
                    var caseInventor = $("#CaseInventor").val().replace(/\s+/g, "");
                    if (caseInventor == '') {
                        $("#Case_CaseBasicInfo_CaseInventor").val(caseInventor);
                        $.showModalMessageBox("请输入发明人.");
                        return false;
                    }
                    if (regd.test($("#CaseInventor").val())) {
                        $.showModalMessageBox("发明人禁止输入 <  >  \"   \'  \\ 半角字符，请检查.");
                        return false;
                    }
                }
                else if ($("#Case_CaseBasicInfo_CaseTypeId").val() == 3) {
                    var caseDesigner = $("#CaseDesigner").val().replace(/\s+/g, "");
                    if (caseDesigner == '') {
                        $("#CaseDesigner").val(caseDesigner);
                        $.showModalMessageBox("请输入设计人.");
                        return false;
                    }
                    if (regd.test($("#CaseDesigner").val())) {
                        $.showModalMessageBox("设计人禁止输入 <  >  \"   \'  \\ 半角字符，请检查.");
                        return false;
                    }
                }
            }


            var data = {};
 
            if ($("#Case_CaseBasicInfo_HasIU").attr('checked') == 'checked' && $("#Case_CaseBasicInfo_RefCaseNo").val() == '') {
                $.showModalMessageBox("请输入关联案号.");
                return false;
            }

            var customers = [];
            var customernames = [];
            
            $("a[name='casecustomer']").each(function () {
                customers.push($(this).attr("customerid"));
                customernames.push($(this).attr("customername"));
            });

            if (customers.length == 0) {
                $.showModalMessageBox("请按顺序录入申请人.");
                $("#Case_CaseBasicInfo_ApplicantInput").focus();
                return false;
            }

            //客户
            data["Case.CaseBasicInfo.CustomerId"] = $("#Case_CaseBasicInfo_CustomerId").val();
            data["Case.CaseBasicInfo.FirstApplicantId"] = customers[0];
            data["Case.CaseBasicInfo.ApplicantName"] = customernames.join(",");

            //data["Case.CaseBasicInfo.ApplicantName"] = $("#Case_CaseBasicInfo_ApplicantName").val();

            data["CustomerIds"] = customers;

            data["Case.CaseBasicInfo.CaseId"] = $("#Case_CaseBasicInfo_CaseId").val();
            data["Case.CaseBasicInfo.CaseNo"] = $("#Case_CaseBasicInfo_CaseNo").val();
            data["Case.CaseBasicInfo.CompanyId"] = $("#Case_CaseBasicInfo_CompanyId").val();
            data["Case.CaseBasicInfo.CaseTypeId"] = $("#Case_CaseBasicInfo_CaseTypeId").val();
            data["Case.CaseBasicInfo.CaseOriginPeople"] = $("#Case_CaseBasicInfo_CaseOriginPeople").val();
            data["Case.CaseBasicInfo.CaseOriginDate"] = $("#Case_CaseBasicInfo_CaseOriginDate").val();
            data["Case.CaseBasicInfo.CasePhaseId"] = $("#Case_CaseBasicInfo_CasePhaseId").val();
            data["Case.CaseBasicInfo.CaseRegisterDate"] = $("#Case_CaseBasicInfo_CaseRegisterDate").val();
            data["Case.CaseBasicInfo.CaseRequestNo"] = $("#Case_CaseBasicInfo_CaseRequestNo").val();
            data["Case.CaseBasicInfo.CaseRequestDate"] = $("#Case_CaseBasicInfo_CaseRequestDate").val();
            data["Case.CaseBasicInfo.AuthorizationDate"] = $("#Case_CaseBasicInfo_AuthorizationDate").val();
            data["Case.CaseBasicInfo.CaseName"] = $("#Case_CaseBasicInfo_CaseName").val().trim();
            data["Case.CaseBasicInfo.Procurator"] = $("#Case_CaseBasicInfo_Procurator").val();
            data["Case.CaseBasicInfo.CardNo"] = $("#Case_CaseBasicInfo_CardNo").val();
            data["Case.CaseBasicInfo.CaseRegisterNo"] = $("#Case_CaseBasicInfo_CaseRegisterNo").val();
            data["Case.CaseBasicInfo.Copywriter"] = $("#Case_CaseBasicInfo_Copywriter").val();
            data["Case.CaseBasicInfo.CaseInventor"] = $("#CaseInventor").val().trim();
            data["Case.CaseBasicInfo.CaseDesigner"] = $("#CaseDesigner").val();

            
            data["Case.CaseBasicInfo.TrademarkIds"] = $("#Case_CaseBasicInfo_TrademarkIds").val();
            data["Case.CaseBasicInfo.CaseSubmitter"] = $("#Case_CaseBasicInfo_CaseSubmitter").val();
            data["Case.CaseBasicInfo.CaseSubmitDate"] = $("#Case_CaseBasicInfo_CaseSubmitDate").val();
            data["Case.CaseBasicInfo.CaseOfficer"] = $("#Case_CaseBasicInfo_CaseOfficer").val();
            data["Case.CaseBasicInfo.Deadline"] = $("#Case_CaseBasicInfo_Deadline").val();
            data["Case.CaseBasicInfo.Customer"] = customers.join(";");
            data["Case.CaseBasicInfo.LawFirm"] = $("#Case_CaseBasicInfo_LawFirm").val();
            data["Case.CaseBasicInfo.ReliefNo"] = $("#Case_CaseBasicInfo_ReliefNo").val();

            data["Case.CaseBasicInfo.HasPriority"] = $("#Case_CaseBasicInfo_HasPriority").prop("checked") == true;
            data["Case.CaseBasicInfo.HasForeign"] = $("#Case_CaseBasicInfo_HasForeign").prop("checked") == true;
            data["Case.CaseBasicInfo.HasRelief"] = $("#Case_CaseBasicInfo_HasRelief").prop("checked") == true;
            data["Case.CaseBasicInfo.HasAdvanced"] = $("#Case_CaseBasicInfo_HasAdvanced").prop("checked") == true;
            data["Case.CaseBasicInfo.HasRequestView"] = $("#Case_CaseBasicInfo_HasRequestView").prop("checked") == true;
            data["Case.CaseBasicInfo.HasPrivateInventor"] = $("#Case_CaseBasicInfo_HasPrivateInventor").prop("checked") == true;
            data["Case.CaseBasicInfo.HasIU"] = $("#Case_CaseBasicInfo_HasIU").prop("checked") == true;

            data["Case.CaseBasicInfo.RefCaseNo"] = $("#Case_CaseBasicInfo_RefCaseNo").val();
            data["Case.CaseBasicInfo.FirstInstanceDate"] = $("#Case_CaseBasicInfo_FirstInstanceDate").val();
            data["Case.CaseBasicInfo.TradeTypeId"] = $("#Case_CaseBasicInfo_TradeTypeId").val();
            data["Case.CaseBasicInfo.TradeProductService"] = $("#Case_CaseBasicInfo_TradeProductService").val();

            data["Case.CaseBasicInfo.HasTradeColorProtected"] = $("#Case_CaseBasicInfo_HasTradeColorProtected").prop("checked") == true;
            data["Case.CaseBasicInfo.HasTradeVoiceProtected"] = $("#Case_CaseBasicInfo_HasTradeVoiceProtected").prop("checked") == true;
            data["Case.CaseBasicInfo.HasTrade3DProtected"] = $("#Case_CaseBasicInfo_HasTrade3DProtected").prop("checked") == true;
            data["Case.CaseBasicInfo.HasTradeFirstRequest"] = $("#Case_CaseBasicInfo_HasTradeFirstRequest").prop("checked") == true;
            data["Case.CaseBasicInfo.HasTradeBaseOnExhibition"] = $("#Case_CaseBasicInfo_HasTradeBaseOnExhibition").prop("checked") == true;
            data["Case.CaseBasicInfo.HasTradeReplenish"] = $("#Case_CaseBasicInfo_HasTradeReplenish").prop("checked") == true;

            data["Case.CaseBasicInfo.PushOfficerRemak"] = $("#Case_CaseBasicInfo_PushOfficerRemak").val();
            data["Case.CaseBasicInfo.FirstAnnualYear"] = $("#Case_CaseBasicInfo_FirstAnnualYear").val();
            data["Case.CaseBasicInfo.CostSlowRate"] = $("#Case_CaseBasicInfo_CostSlowRate").val();


            data["isSubmit"] = isSubmit;

            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseCreateUpdate", data, function (response) {
                if (response.IsSuccess) {
                    //$("#CaseId").val(response.Data.CaseBasicInfo.CaseId);
                    //$("#Case_CaseBasicInfo_CaseNo").val(response.Data.CaseBasicInfo.CaseNo);
                    //$("#Case_CaseBasicInfo_CaseSubmitter").val(response.Data.CaseBasicInfo.CaseSubmitter);
                    //$("#Case_CaseBasicInfo_CaseSubmitDate").val(getDate(convertJsonDateToJSDate(response.Data.CaseBasicInfo.CaseSubmitDate)));

                    if (isSubmit) {
                        $.showModalMessageBox("提交成功.");

                    } else {
                        $.showModalMessageBox("保存成功.");
                    }

                    caseInfo.LoadCase(response.Data.CaseBasicInfo.CaseId);

                    //var caseId = {
                    //    caseId: response.Data.CaseBasicInfo.CaseId
                    //}
                    //$.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseInfo", caseId, function (responsedata) {
                    //    $(".viewFramework-product-body").html("");
                    //    if (!responsedata.IsSuccess) {
                    //        $.showModalMessageBox(responsedata.Message);
                    //        return false;
                    //    }
                    //    if (responsedata.Data == null) {
                    //        return false;
                    //    }
                    //    $(".viewFramework-product-body").html(responsedata.Data);
                    //});

                } else if (response.IsRedirect) {
                    window.location =  AP_ROOT + 'Home/Index';
                } else {
                    $.showModalMessageBox(response.Message);

                }
            });
        } catch (e) {
            alert(e);
        }
    },

    Close: function () {
        $('#caseDeadLineModal').modal('hide');
    },

    LoadCase: function (caseInfoId) {

        if ($("#liARCaseFeeList").attr("class") == 'active') {
            caseListSelectedTypeId = 2;
        }
        else if ($("#liAPCaseFeeList").attr("class") == 'active') {
            caseListSelectedTypeId = 3;
        }
        else if ($("#liCaseAssistedFeeList").attr("class") == 'active') {
            caseListSelectedTypeId = 4;
        }
        else if ($("#liCaseCustomerContactsList").attr("class") == 'active') {
            caseListSelectedTypeId = 5;
        }
        else if ($("#liCaseLogList").attr("class") == 'active') {
            caseListSelectedTypeId = 6;
        }
        else if ($("#liCaseTaskList").attr("class") == 'active') {
            caseListSelectedTypeId = 7;
        }
        else if ($("#liInternalFeeList").attr("class") == 'active') {
            caseListSelectedTypeId = 8;
        }
        else {
            caseListSelectedTypeId = 1;
        }

        var caseId = {
            caseId: caseInfoId,
            caseListSelectedTypeId: caseListSelectedTypeId
        };
        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseInfo", caseId, function (responsedata) {
            $(".viewFramework-product-body").html("");
            if (!responsedata.IsSuccess) {
                $.showModalMessageBox(responsedata.Message);
                return false;
            }
            if (responsedata.Data == null) {
                return false;
            }
            $(".viewFramework-product-body").html(responsedata.Data);

            if ($("#spanCaseBasicInfoCaseId_" + caseInfoId).length) {
                $("#spanCaseBasicInfoCaseId_" + caseInfoId).text($("#Case_CaseBasicInfo_DeadlineLeftDays").val());
            }
        });

    },

    getDeadlineHtml: function () {

        var html = "<div class='i_common_box' style='width:400px'>"
            + "<div class='i_common_hd'>"
            + "<input type='hidden' id='hidControlId'> 截止日期设定"
            + "</div>"
            + "<div class='i_common_bd'>"
            + "    <fieldset>"
            + "        <div class='form-group'>"
            + "            <label class='col-sm-1 control-label label-width' style='width:6%;padding: 1px; padding-top: 7px ;text-align: center'>"
            + "                 <span>于</span>"
            + "             </label>"
            + "             <div class='col-sm-3 ' style='padding: 1px;'>"
            + "                <input class='input_time form-control' unselectable='on' id='Cfg_Case_CaseBasicInfo_Deadline_Date' onfocus=\"WdatePicker({doubleCalendar:true,dateFmt:'yyyy-MM-dd'})\" type='text' >"
            + "             </div>"
            + "              <label class='col-sm-1 control-label label-width' style='width: 8%; padding: 1px; padding-top: 7px; text-align: center'>"
            + "                  <span>后(</span>"
            + "             </label>"
            + "             <div class='col-sm-1 ' style='width: 8%; padding: 1px;'>"
            + "                 <input class='form-control' id='Cfg_Case_CaseBasicInfo_Deadline_Year' onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\""
            + "     onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" style='width: 100%' type='text' value='0'>"
            + "</div>"
            + "<label class='col-sm-1 control-label label-width' style='width: 6%; padding: 1px; padding-top: 7px;; text-align: center'>年</label>"
            + "<div class='col-sm-1 ' style='width: 8%; padding: 1px;'>"
            + "    <input class='form-control' id='Cfg_Case_CaseBasicInfo_Deadline_Month' onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\""
            + "     onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" style='width: 100%' value='0'>"
            + "</div>"
            + "<label class='col-sm-1 control-label label-width' style='width: 6%; padding: 1px; padding-top: 7px; text-align: center'>月</label>"
            + "<div class='col-sm-1 ' style='width: 8%; padding: 1px;'>"
            + "    <input class='form-control' id='Cfg_Case_CaseBasicInfo_Deadline_Day' onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\""
            + "    onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" style='width: 100%' value='0'>"
            + "</div>"
            + "<label class='col-sm-1 control-label label-width' style='width: 6%; padding: 1px; padding-top: 7px; text-align: center'>日)</label>"
            + "</div>"
            + "</fieldset>"
            + "<div class='form-group'>"
            + "     <div class='col-sm-12 row clearfix'>"
            + "        <input class='btn btn-primary ng-binding' type='button' id='btnCfgDeadlineCreateUpdate' value='确定' />"
            + "        <input class='btn btn-default ng-binding' type='button' id='btnCfgDeadlineCreateUpdateCancel' value='取消' />"
            + "    </div>"
            + "</div>"
            + "</div>"
            + "</div>";

        return html;
    },

    ResetSize: function () {
        if ($("#divContextList").length > 0)
        {
            $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 14);
        }
        if ($("#divCaseEvents").length > 0)
        {
            $("#divCaseEvents").css("height", $('.case-section-main').height() - 2);
        }
        if ($("#divCaseLogs").length > 0) {
            $("#divCaseLogs").css("height", $(window).height() - $("#divCaseLogs").offset().top - 14 + 8);
        }
    },

    /*客户*/
    CaseCustomer: {

        AddIn: function (customerId, customerNo, customerName) {

            var existsApplicant = false;

            $("a[name='casecustomer']").each(function () {
                if ($(this).attr("customerid") == customerId) {
                    existsApplicant = true;
                    return true;
                }
            });

            //重复

            if (existsApplicant) return true;

            var $tag = $("<span class='tag label label-info'>"
                         + "<a name='casecustomer' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                         + " customerid='" + customerId + "'"
                         + " customerno='" + customerNo + "'"
                         + " customername='" + customerName + "'"
                         + " title='' data-toggle='tooltip' data-container='body' href='javascript:caseInfo.CaseCustomer.ViewCustomer(" + customerId + ");' target='_blank' data-original-title=" + customerName + " '>" + customerName + "</a>"
                         + "<span class='customerremove' data-role='remove'></span>"
                       + "</span>");

            $("#Case_CaseBasicInfo_ApplicantInput").before($tag);
            $tag.after(' ');

        },

        //加载客户
        List: function (customerIds) {
            var data = { customerIds: customerIds };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/CaseCustomer/CaseCustomerList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $(".casecustomers").empty();
                    $(".casecustomers").html(response.Data);
                    $.closeLoading();
                }
            }, true);
        },

        Open: function () {
            var data = {};
            var url = AP_ROOT + AP_PAGE_ID + "/IPR/CaseCustomer/Customer";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#customerModal').modal({ backdrop: 'static', keyboard: false });
                $('#customerModal').on('hidden.bs.modal', function () {
                    $("#customerModal").remove();
                });
            });
        },

        /*关闭客户*/
        Close: function () {
            $('#caseCustomerModal').modal('hide');
            $('#customerModal').modal('hide');
        },

        CreateUpdate: function () {
            var customerIds = $.checkbox.vals("chkCustomerId");
            if (customerIds.length == 0) {
                $.showModalMessageBox("请选择申请人.");
                return false;
            }

            var firstApplicantIds = $.checkbox.vals("chkFirstApplicantId");
            if (firstApplicantIds.length == 0 && customerIds.length > 1) {
                $.showModalMessageBox("请选择第一申请人.");
                return false;
            }
            else if (firstApplicantIds.length == 0 && customerIds.length == 1) {
                firstApplicantIds.push(customerIds[0]);
            }

            //if ($.inArray(firstApplicantId, customerIds)) {
            //    $.showModalMessageBox("第一申请人不在选择的申请人中，请选择第一申请人.");
            //    return false;
            //}

            var customerNames = [];
            var customerNos = [];
            $("input[name=chkCustomerId]:checked").each(
                function (i) {
                    customerNos[i] = $(this).attr("customerno");
                    customerNames[i] = $(this).attr("customername");
                }
            );

            //$("#Case_CaseBasicInfo_Customer").val(customerIds.join(";"));
            $("#Case_CaseBasicInfo_FirstApplicantId").val(firstApplicantIds[0]);


            //Case_CaseBasicInfo_CustomerId

            var html = '';
            $("#ulApplicant").find("li[name='liCustomer']").remove();
            for (var i = 0; i < customerIds.length; i++) {
                html = "<li name='liCustomer' customerId=" + customerIds[i] + " customername='" + customerNames[i] + "' ><div class='element' style=''><a style='width: 150px;  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; ' title='" + customerNames[i] + "' data-toggle='tooltip' href='javascript:caseInfo.CaseCustomer.ViewCustomer(" + customerIds[i] + " );'>" + customerNames[i] + "</a><i class='unlink fa fa-times' data-toggle='tooltip' onclick='caseInfo.CaseCustomer.Remove(this)'  tabindex='0'></i></div></li>";
                if (firstApplicantIds[0] == customerIds[i]) {
                    $("#ulApplicant").prepend(html);
                } else {
                    $("#ulApplicant").find("li[name='liCustomerAdd']").before(html);
                }
            }

            caseInfo.CaseCustomer.Close();
        },

        /*查看客户*/
        ViewCustomer: function (customerId) {
            var data = { customerId: customerId };
            var url = AP_ROOT + AP_PAGE_ID + "/IPR/CaseCustomer/Customer";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#customerModal').modal({ backdrop: 'static', keyboard: false });
                $('#customerModal').on('hidden.bs.modal', function () {
                    $("#customerModal").remove();
                });

                $(":input", "#customerForm").each(function () {
                    $(this).attr("disabled", "disabled");
                });
            });
        },

        Remove: function (e) {
            $(e).parent().remove();
        },

        CustomerContacts: {

            BindMenu: function () {
                $('#customerContactsGridSection').contextMenu('contactsMenu', {
                    menuStyle: {
                        width: '152px'
                    },

                    itemStyle: {
                        width: '150px'
                    },

                    bindings: {
                        'select': function (t, e) {
                            caseInfo.CaseCustomer.CustomerContacts.Open();
                            return true;
                        },
                    },
                    onContextMenu: function (e) {
                        return true;
                    },
                    onShowMenu: function (e, menu) {
                        return menu;
                    }
                });
            },

            List: function () {
                var data = {
                    caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                    pageNo: $("#PageNo").val(),
                    pageSize: $("#PageSize").val()
                };

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/CaseCustomer/CaseContactsList", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_List").empty();
                        $("#dv_List").html(response.Data);

                        $(".pull-right.page-box.contacts").cPaging({
                            totalCount: parseInt($("#TotalCount").val()),
                            pageNo: parseInt($("#PageNo").val()),
                            pageSize: parseInt($("#PageSize").val()),
                            callBack: caseInfo.CaseCustomer.CustomerContacts.List,
                            callBackArgs: null
                        });

                        var totalCount = parseInt($("#TotalCount").val());

                        if (totalCount > 0) {
                            $("tfoot", "#tblContactsList").show();
                            $(".simple-grid-none-data-wrap").hide();
                        } else {
                            $("tfoot", "#tblContactsList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }

                        caseInfo.ResetSize();

                        caseInfo.CaseCustomer.CustomerContacts.BindMenu();

                        $.closeLoading();
                    }
                }, true);
            },

            Open: function () {

                var data = {
                    customerId: $("#Case_CaseBasicInfo_CustomerId").val()
                };

                var url = AP_ROOT + AP_PAGE_ID + "/IPR/CaseCustomer/CaseCustomerContactsSelected";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#caseCustomerContactsModal').modal({ backdrop: 'static', keyboard: false });
                    $('#caseCustomerContactsModal').on('hidden.bs.modal', function () {
                        $("#caseCustomerContactsModal").remove();
                    });
                });
            },

            /*关闭客户*/
            Close: function () {
                $('#caseCustomerContactsModal').modal('hide');
                $('#caseCustomerContactsModal').modal('hide');
            },

            CreateUpdate: function () {
                var documentContactsIds = $.checkbox.vals("chkDocumentContactsId");
                //if (documentContactsIds.length == 0) {
                //    $.showModalMessageBox("请选择文件联系人.");
                //    return false;
                //}

                var technologyContactsIds = $.checkbox.vals("chkTechnologyContactsId");
                if (technologyContactsIds.length == 0) {
                    $.showModalMessageBox("请选择技术联系人.");
                    return false;
                }

                var data =
                {
                    caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                    customerId: $("#Case_CaseBasicInfo_CustomerId").val(),
                    documentContactsIds: documentContactsIds,
                    technologyContactsIds: technologyContactsIds,
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/CaseCustomer/CreateCaseCustomerContacts", data, function (response) {
                    if (response.IsSuccess) {
                        caseInfo.CaseCustomer.CustomerContacts.List();
                        caseInfo.CaseCustomer.CustomerContacts.Close();
                    } else {
                    }
                });
            },
        }
    },

    /*律所*/
    CaseLawFirm: {
        //加载律所
        List: function () {
            var data = { caseId: $("#Case_CaseBasicInfo_CaseId").val() };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseLawFirmList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $(".caselawfirms").empty();
                    $(".caselawfirms").html(response.Data);
                    $.closeLoading();
                }
            }, true);
        },

        Open: function () {
            //if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
            //    $.showModalMessageBox("请先保存案件基本资料.");
            //    return false;
            //}
            var data = { caseId: $("#Case_CaseBasicInfo_CaseId").val() };
            var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseLawFirmSelected";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                caseInfo.CaseLawFirm.SelectedList();
                $('#caseLawFirmModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseLawFirmModal').on('hidden.bs.modal', function () {
                    $("#caseLawFirmModal").remove();
                });
            });
        },

        /*关闭律所*/
        Close: function () {
            $('#caseLawFirmModal').modal('hide');
        },

        CreateUpdate: function () {

            var lawFirmIds = $.checkbox.vals("chkLawFirmId");
            if (lawFirmIds.length == 0) {
                caseInfo.CaseLawFirm.Close();
                return false;
            }

            var lawFirmNames = [];
            $("input[name=chkLawFirmId]:checked").each(
                function (i) { lawFirmNames[i] = $(this).attr("lawFirmname"); }
            );

            $("#Case_CaseBasicInfo_LawFirm").val(lawFirmIds.join(";"));
            $("#Case_CaseBasicInfo_LawFirmName").val(lawFirmNames.join(";"));

            caseInfo.CaseLawFirm.Close();
        },

        Selected: function (e) {
            if ($(e).prop("checked") == true) {
                $.checkbox.all("chkLawFirmId");
            } else {
                $.checkbox.not("chkLawFirmId");
            }
        },

        SelectedList: function () {
            $("#caseLawFirmListForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseLawFirmListSelected", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblLawFirmList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.LawFirms, function (i, e) {

                            if ($.inArray(e.LawFirmId, response.Data.SelectedLawFirms) > -1) {
                                $("tbody", "#tblLawFirmList").addRow("<input type='checkbox' checked name='chkLawFirmId' class='ng-pristine ng-valid' value='" + e.LawFirmId + "'lawFirmName='" + e.LawFirmName + "'>",
                                    e.LawFirmNo, e.LawFirmName, e.RegisteredAddress, e.Zip,
                                    e.Telphone, e.Fax, e.Email, e.Country, e.CompanyCode,
                                    e.LawFirmCode, e.BusinessAddress);
                            } else {
                                $("tbody", "#tblLawFirmList").addRow("<input type='checkbox' name='chkLawFirmId' class='ng-pristine ng-valid' value='" + e.LawFirmId + "'lawFirmName='" + e.LawFirmName + "'>",
                                    e.LawFirmNo, e.LawFirmName, e.RegisteredAddress, e.Zip,
                                    e.Telphone, e.Fax, e.Email, e.Country, e.CompanyCode,
                                    e.LawFirmCode, e.BusinessAddress);
                            }
                        });

                        $("tfoot", "#tblLawFirmList").show();

                        $(".pull-right.page-box").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: caseInfo.CaseLawFirm.SelectedList,
                            callBackArgs: null
                        });
                    } else {
                        $("tfoot", "#tblLawFirmList").hide();
                    }
                }
            });
        },
    },

    /*案件事件提醒*/
    CaseEvent: {
        List: function () {
            var data = { caseId: $("#Case_CaseBasicInfo_CaseId").val() };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseEventList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $(".caseevents").empty();
                    $(".caseevents").html(response.Data);
                    $.closeLoading();
                }
            }, true);
        },

        /*打开案件提醒*/
        Open: function (eventId,eventTypeId,eventOperator, eventTime, deadline, eventContent) {
            if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }
            var data =
            {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                companyId: $("#Case_CaseBasicInfo_CompanyId").val(),
                eventId: eventId
            };

            data["CaseEvent.EventId"] = eventId;
            data["CaseEvent.EventTypeId"] = eventTypeId;
            data["CaseEvent.Operator"] = eventOperator;
            data["CaseEvent.EventTime"] = eventTime;
            data["CaseEvent.Deadline"] = deadline;
            data["CaseEvent.EventContent"] = eventContent;

            var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseEvent";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseEventModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseEventModal').on('hidden.bs.modal', function () {
                    $("#caseEventModal").remove();
                });
            });
        },

        /*关闭案件提醒*/
        Close: function () {
            $('#caseEventModal').modal('hide');
        },
        CreateUpdate: function () {

            if ($("#CaseEvent_Deadline").val() == '') {
                $.showModalMessageBox("请输入截止日期.");
                return false;
            }

            if ($("#CaseEvent_EventTime").val() == '') {
                $.showModalMessageBox("请输入提醒日期.");
                return false;
            }

            if ($("#CaseEvent_EventContent").val() == '') {
                $.showModalMessageBox("请输入提醒内容.");
                return false;
            }

            if ($("#CaseEvent_Deadline").val() >= $("#CaseEvent_EventTime").val()) {
                $.showModalMessageBox("截止日期不应大于提醒日期.");
                return false;
            }

            $("#caseEvent").ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseEventCreate", function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("保存成功.");
                    $('#caseEventModal').modal('hide');
                    //if (caseInfo.CaseEvent) {
                    //    caseInfo.CaseEvent.List();
                    //}
                    caseInfo.LoadCase($("#Case_CaseBasicInfo_CaseId").val());

                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        Delete: function () {
            var data = { caseEventId: $("#EventId").val() };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseEventDelete", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("删除成功.");
                    caseInfo.CaseEvent.List();
                    caseInfo.CaseEvent.Close();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
    },

    /*案件事件提醒*/
    CaseEventNotIn: {
 
        /*打开案件提醒*/
        Open: function () {
            if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }
            var data =
            {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                caseNo: $("#Case_CaseBasicInfo_CaseNo").val(),
            };
            var url =  AP_ROOT + AP_PAGE_ID + "/IPR/CaseEvent/CaseEventNotIn";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseEventNotInModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseEventNotInModal').on('hidden.bs.modal', function () {
                    $("#caseEventNotInModal").remove();
                });
            });
        },

        /*关闭案件提醒*/
        Close: function () {
            $('#caseEventNotInModal').modal('hide');
        },
        CreateUpdate: function () {

            var data = {
                CaseId: parseInt($("#Case_CaseBasicInfo_CaseId").val()),
                CaseNo: $("#CaseNo").val(),
            }
            var i = 0;
            $("input[type='checkbox']:checked").each(function () {
                data["EventTypeIds[" + i + "]"] = parseInt(this.value);
                i++;
            });

            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/CaseEvent/CaseEventNotInCreate", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("设定成功.");
                    $('#caseEventNotInModal').modal('hide');
                    caseInfo.LoadCase($("#Case_CaseBasicInfo_CaseId").val());
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });

        },
    },

    /*日志*/
    CaseLog: {
        List: function () {
            var data = { caseId: $("#Case_CaseBasicInfo_CaseId").val() };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseLogList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $(".caselogs").empty();
                    $(".caselogs").html(response.Data);
                    $.closeLoading();
                }
            }, true);
        },

        OperatingLogList: function () {
            var data = {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                pageNo: $("#PageNo").val(),
                pageSize: $("#PageSize").val()
            };

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseOperatingLogList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $("#dv_List").empty();
                    $("#dv_List").html(response.Data);

                    $(".pull-right.page-box.caselog").cPaging({
                        totalCount: parseInt($("#TotalCount").val()),
                        pageNo: parseInt($("#PageNo").val()),
                        pageSize: parseInt($("#PageSize").val()),
                        callBack: caseInfo.CaseLog.OperatingLogList,
                        callBackArgs: null
                    });

                    var totalCount = parseInt($("#TotalCount").val());

                    caseInfo.ResetSize();

                    if (totalCount > 0) {
                        $("tfoot", "#tblCaseLog").show();
                        $(".simple-grid-none-data-wrap").hide();
                    } else {
                        $("tfoot", "#tblCaseLog").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
  
                    $.closeLoading();
                }
            }, true);
        },

        /*打开案件日志*/
        Open: function (logId) {

            if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }

            var data =
            {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                caseNo: $("#Case_CaseBasicInfo_CaseNo").val(),
                logId : logId
            };

            var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseLog";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseLogModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseLogModal').on('hidden.bs.modal', function () {
                    $("#caseLogModal").remove();
                });
            });

        },

        /*关闭案件日志*/
        Close: function () {
            $('#caseLogModal').modal('hide');
        },
        CreateUpdate: function () {
            if ($("#CaseLog_Content").val() == '') {
                $.showModalMessageBox("请输入日志内容");
                return false;
            }

            $("#caseLog").ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseLogCreate", function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("保存成功.");
                    $('#caseLogModal').modal('hide');

                    if (caseInfo.CaseLog) {
                        caseInfo.CaseLog.List();
                    }
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        Delete: function () {
            var data = { caseLogId: $("#CaseLog_LogId").val() };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/CaseLog/CaseLogDelete", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("删除成功.");
                    caseInfo.CaseLog.List();
                    caseInfo.CaseLog.Close();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
    },

    /*应收账款*/
    ARCaseFee: {
        Objects: {
            List: function () {
                var data = {
                    customerId: $("#Case_CaseBasicInfo_CustomerId").val()
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/Contract/GetContractListByCustomerId", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();

                        tr = "<tr>"
                                 + "<td><select class='form-control' disable id='item_ContractId' ><option value='-1'>请选择</option></select></td>"
                                         + "<td><input class='item_CaseRequestDate form-control' id='item_CaseRequestDate' readonly='True' type='text' value='" + $("#Case_CaseBasicInfo_CaseRequestDate").val() + "'></td>"
                                         + "<td><select class='form-control' disable id='item_CaseOfficeFeeTypeId' ><option value='-100'>请选择</option></select></td>"
                                         + "<td><input class='item_CaseOfficeFeeAmount form-control'  id='item_CaseOfficeFeeAmount' name='item_CaseOfficeFeeAmount' onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\" onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" type='text' value='0'></td>"
                                         + "<td><select class='form-control' id='item_CaseFeeAnnualYear' disabled='disabled'><option value='-1'>无</option></select></td>"
                                         + "<td><input class='item_IsFirstYear' disabled='disabled' id='item_IsFirstYear' style='height:20px;width:20px ' type='checkbox'  ></td>"
                                         + "<td><input class='item_PaymentByCustomer'   id='item_PaymentByCustomer' style='height:20px;width:20px ' type='checkbox' ></td>"
                                         + "<td><select class='form-control'  id='item_CaseNonOfficeFeeTypeId'><option value='-200'>请选择</option></select></td>"
                                         + "<td><input class='item_CaseNonOfficeFeeAmount form-control'  id='item_CaseNonOfficeFeeAmount' name='item_CaseNonOfficeFeeAmount'  onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\" onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" type='text' value='0'>"
                                         + "<td><input class='item_CaseCommissionFeeAmount form-control'  id='item_CaseCommissionFeeAmount' name='item_CaseCommissionFeeAmount'  onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\" onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" type='text' value='0'>"
                                        + "<td><input class='item_Remark form-control' id='item_Remark'  type='text' value=''></td>"
                                         + "<td><a style='color:green;' href='javascript:void(0);'><span class='btn_ar_add glyphicon glyphicon-plus'></span></a>&nbsp;&nbsp;&nbsp;<a  style='color:red;' href='javascript:void(0);'><span class='btn_ar_remove glyphicon glyphicon-remove'></span></a></td>"
                          + "</tr>";

                        $('#tblContractObjectList>tbody>tr:last').after(tr);

                        var caseTypeId = $("#Case_CaseBasicInfo_CaseTypeId").val();

                        $("#tblContractObjectList tbody tr").each(function (i, e) {

                            if ($(e).find("#item_ContractId option").length == 1) {
                                $(e).find("#item_ContractId").empty();
                                $.each(response.Data, function (i, c) {
                                    $(e).find("#item_ContractId").append('<option value=' + c.ContractBasicInfo.ContractId + '>' + c.ContractBasicInfo.ContractNo + '</option>');
                                });
                            }

                            if ($(e).find("#item_CaseOfficeFeeTypeId option").length == 1) {
                                $.each(GV_IPR.CaseFeeTypes, function (j, f) {
                                    if (f.TypeId == '1' && f.FeeTypeId != -100 && f.CaseTypeId == caseTypeId) {
                                        $(e).find("#item_CaseOfficeFeeTypeId").append('<option value=' + f.FeeTypeId + '>' + f.FeeTypeName + '</option>');
                                    }
                                });

                                $(e).find("#item_CaseOfficeFeeTypeId").val($(e).find("#item_CaseOfficeFeeTypeId").attr("caseOfficeFeeTypeId"));
                            }

                            if ($(e).find("#item_CaseNonOfficeFeeTypeId option").length == 1) {
                                $.each(GV_IPR.CaseFeeTypes, function (j, f) {
                                    if (f.TypeId == '2' && f.FeeTypeId != -200 && f.CaseTypeId == caseTypeId) {
                                        $(e).find("#item_CaseNonOfficeFeeTypeId").append('<option value=' + f.FeeTypeId + '>' + f.FeeTypeName + '</option>');
                                    }
                                });

                                $(e).find("#item_CaseNonOfficeFeeTypeId").val($(e).find("#item_CaseNonOfficeFeeTypeId").attr("caseNonOfficeFeeTypeId"));
                            }

                            var caseOfficeFeeTypeId = $(e).find("#item_CaseOfficeFeeTypeId");
                            caseInfo.ARCaseFee.Objects.ObjectItem.InitCaseOfficeFeeAnnualYear(caseOfficeFeeTypeId);

                            $(e).find("#item_CaseFeeAnnualYear").val($(e).find("#item_CaseOfficeFeeTypeId").attr("AnnualYear"));
                            $(e).find("#item_CaseFeeAnnualYear").attr("disabled", "disabled");
                        });

                        caseInfo.ARCaseFee.Objects.ObjectItem.BindEvent();

                        $.closeLoading();
                    }
                }, true);
            },
            Open: function () {
                if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                    $.showModalMessageBox("请先保存案件基本资料.");
                    return false;
                }

                var data = {};

                var url = AP_ROOT + AP_PAGE_ID + "/IPR/ARCaseFee/Create";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#createModal').modal({ backdrop: 'static', keyboard: false });
                    $('#createModal').on('hidden.bs.modal', function () {
                        $("#createModal").remove();
                    });

                    caseInfo.ARCaseFee.Objects.List();
                });

            },
            Edit: function (seqno) {
                if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                    $.showModalMessageBox("请先保存案件基本资料.");
                    return false;
                }

                var data = {
                    seqno: seqno
                };

                var url = AP_ROOT + AP_PAGE_ID + "/IPR/ARCaseFee/Edit";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#createModal').modal({ backdrop: 'static', keyboard: false });
                    $('#createModal').on('hidden.bs.modal', function () {
                        $("#createModal").remove();
                    });
                    $("#tblContractObjectList tbody tr").each(function (i, e) {

                        var caseOfficeFeeTypeId = $(e).find("#item_CaseOfficeFeeTypeId");
                        caseInfo.ARCaseFee.Objects.ObjectItem.InitCaseOfficeFeeAnnualYear(caseOfficeFeeTypeId);

                        $(e).find("#item_CaseFeeAnnualYear").val($(e).find("#item_CaseOfficeFeeTypeId").attr("AnnualYear"));
                        //$(e).find("#item_CaseFeeAnnualYear").attr("disabled", "disabled");
                    });
                });
            },

            Close: function () {
                $('#createModal').modal('hide');
            },
            CreateUpdate: function () {
                try {

                    var data = {};
                    var dataIsNOk = false;
                    var i = 0;
                    $("#tblContractObjectList>tbody>tr").each(function (j, e) {
                        if ($(e).css("display") != 'none') {

                            if ($(e).find("#item_ContractId").val() == '-1' || $(e).find("#item_ContractId").val() == '0') {
                                dataIsNOk = true;
                                $.showModalMessageBox("第" + (j) + "行,请选择合同,如无合同请联系案源人创建新合同.");
                                return false;
                            }

                            if ($(e).find("#item_CaseOfficeFeeTypeId").val() == '-1' && $(e).find("#item_CaseNonOfficeFeeTypeId").val() == '-1') {
                                dataIsNOk = true;
                                $.showModalMessageBox("第" + (j) + "行,请选择官费或代理费.");
                                return false;
                            }

                            data["ContractObjects[" + i + "].ContractId"] = $(e).find("#item_ContractId").val();
                            data["ContractObjects[" + i + "].ContractNo"] = $(e).find("#item_ContractId").find("option:selected").text();

                            data["ContractObjects[" + i + "].CaseId"] = $("#Case_CaseBasicInfo_CaseId").val();
                            data["ContractObjects[" + i + "].CaseNo"] = $("#Case_CaseBasicInfo_CaseNo").val();
                       
                            data["ContractObjects[" + i + "].CustomerId"] = $("#Case_CaseBasicInfo_CustomerId").val();
                            data["ContractObjects[" + i + "].CustomerNo"] = $("#Case_CaseBasicInfo_CustomerNo").val();

                            data["ContractObjects[" + i + "].CaseOfficeFeeId"] = $(e).find("#item_CaseOfficeFeeTypeId").attr("CaseOfficeFeeId");
                            data["ContractObjects[" + i + "].CaseOfficeFeeTypeId"] = $(e).find("#item_CaseOfficeFeeTypeId").val();
                            data["ContractObjects[" + i + "].CaseOfficeFeeAmount"] = $(e).find("#item_CaseOfficeFeeAmount").val();

                            data["ContractObjects[" + i + "].CaseNonOfficeFeeId"] = $(e).find("#item_CaseNonOfficeFeeTypeId").attr("CaseNonOfficeFeeId");
                            data["ContractObjects[" + i + "].CaseNonOfficeFeeTypeId"] = $(e).find("#item_CaseNonOfficeFeeTypeId").val();
                            data["ContractObjects[" + i + "].CaseNonOfficeFeeAmount"] = $(e).find("#item_CaseNonOfficeFeeAmount").val();
                            data["ContractObjects[" + i + "].CaseCommissionFeeId"] = $(e).find("#item_CaseCommissionFeeAmount").attr("casecommissionfeeid");
                            data["ContractObjects[" + i + "].CaseCommissionFeeAmount"] = $(e).find("#item_CaseCommissionFeeAmount").val();

                            if (data["ContractObjects[" + i + "].CaseOfficeFeeTypeId"] == '11020'
                             || data["ContractObjects[" + i + "].CaseOfficeFeeTypeId"] == '21020'
                             || data["ContractObjects[" + i + "].CaseOfficeFeeTypeId"] == '31020')
                            {
                               
                                //年费时需要
                                data["ContractObjects[" + i + "].AnnualYear"] = $(e).find("#item_CaseFeeAnnualYear").val();
                                data["ContractObjects[" + i + "].AnnualFrom"] = $(e).find("#item_CaseFeeAnnualYear option:selected").attr("annualfrom");
                                data["ContractObjects[" + i + "].AnnualEnd"] = $(e).find("#item_CaseFeeAnnualYear option:selected").attr("annualend");
                                data["ContractObjects[" + i + "].IsFirstYear"] = $(e).find("#item_IsFirstYear").prop("checked") == true;
                            }

                            data["ContractObjects[" + i + "].PaymentByCustomer"] = $(e).find("#item_PaymentByCustomer").prop("checked") == true;

                            if (data["ContractObjects[" + i + "].CaseOfficeFeeTypeId"] == '-100' && parseInt(data["ContractObjects[" + i + "].CaseOfficeFeeAmount"]) != '0') {
                                dataIsNOk = true;
                                $.showModalMessageBox("第" + (j) + "行，选择官费类型.");
                                return false;
                            }

                            if (data["ContractObjects[" + i + "].CaseNonOfficeFeeTypeId"] == '-200' && parseInt(data["ContractObjects[" + i + "].CaseNonOfficeFeeAmount"]) != '0') {
                                dataIsNOk = true;
                                $.showModalMessageBox("第" + (j) + "行，选择代理费类型.");
                                return false;
                            }

                            if (data["ContractObjects[" + i + "].CaseOfficeFeeTypeId"] != '-100' && parseInt(data["ContractObjects[" + i + "].CaseOfficeFeeAmount"]) == '0') {
                                dataIsNOk = true;
                                $.showModalMessageBox("第" + (j) + "行，输入官费金额.");
                                return false;
                            }

                            if (data["ContractObjects[" + i + "].CaseNonOfficeFeeTypeId"] != '-200' && parseInt(data["ContractObjects[" + i + "].CaseNonOfficeFeeAmount"]) == '0') {
                                dataIsNOk = true;
                                $.showModalMessageBox("第" + (j) + "行，输入代理费金额.");
                                return false;
                            }

                            data["ContractObjects[" + i + "].Remark"] = $(e).find("#item_Remark").val();

                            data["ContractObjects[" + i + "].IsChanged"] = true;

                            i++;
                        }
                    });

                    if (dataIsNOk) return false;

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractDraft/ContractObjectsCreate", data, function (response) {
                        if (response.IsSuccess) {
                            $.showModalMessageBox("提交成功.");
                            caseInfo.ARCaseFee.Objects.Close();
                            caseInfo.ARCaseFee.List();
                            caseInfo.LoadCase($("#Case_CaseBasicInfo_CaseId").val())
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {
                    alert(e);
                }
            },
            ObjectItem: {
                BindEvent: function () {

                    $(".btn_ar_add").unbind("click");
                    $(".btn_ar_add").click(function () {
                        caseInfo.ARCaseFee.Objects.ObjectItem.Add(this);
                    });

                    $(".btn_ar_remove").unbind("click");
                    $(".btn_ar_remove").click(function () {
                        caseInfo.ARCaseFee.Objects.ObjectItem.Remove(this);
                    });

                    $(".btn_ar_edit").unbind("click");
                    $(".btn_ar_edit").click(function () {
                        caseInfo.ARCaseFee.Objects.ObjectItem.Edit(this);
                    });
                },
                Add: function (e) {
                    var tr = $(e).parents("tr").clone().show();

                    //$(tr).find(":input[type='text']").val('');
                    $(tr).find(":input[type='hidden']").val('');
                    $(tr).find(":input[type='checkbox']").attr("checked", false);

                    $(tr).find("#item_CaseOfficeFeeAmount").val('0');
                    $(tr).find("#item_CaseOfficeFeeTypeId").removeAttr("caseofficefeetypeid");
                    $(tr).find("#item_CaseOfficeFeeTypeId").removeAttr("caseofficefeeid");
                    $(tr).find("#item_CaseNonOfficeFeeTypeId").removeAttr("casenonofficefeetypeid");
                    $(tr).find("#item_CaseNonOfficeFeeTypeId").removeAttr("casenonofficetypeid");
                    $(tr).find("#item_CaseNonOfficeFeeAmount").val('0');
                    $(tr).find("#item_CaseCommissionFeeAmount").val('0');

                    $("#tblContractObjectList").append(tr);

                    caseInfo.ARCaseFee.Objects.ObjectItem.BindEvent();

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
            },
        },

        PaymentApply: {
            /*垫付款申请*/
            Open: function () {
                if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                    $.showModalMessageBox("请先保存案件基本资料.");
                    return false;
                }
                var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
                if (caseFeeIds.length == 0) {
                    $.showModalMessageBox("请选择费用进行付款申请.");
                    return false;
                }
                var contractIds = new Array();
                var batchNos = new Array();

                $("input[name='chkCaseFeeId']:checked").each(
                    function () {
                        if ($.inArray($(this).attr("contractid"), contractIds) > -1) {
                        } else {
                            contractIds.push($(this).attr("contractid"));
                        }
                        batchNos.push($(this).attr("batchNo"));
                    }
                );
                if (contractIds.length > 1) {
                    $.showModalMessageBox("请选择同一合同下的费用进行付款申请.");
                    return false;
                }
                var url = AP_ROOT + AP_PAGE_ID + '/FAM/AP/PaymentCreate?contractId=' + contractIds[0] + '&batchNos=' + batchNos.join(",");
                window.open(url);
            },
        },

        /*案件费用列表*/
        List: function () {
            var data = {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                pageNo: $("#PageNo").val(),
                pageSize: $("#PageSize").val()
            };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/ARCaseFee/CaseFeeList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $("#dv_List").empty();
                    $("#dv_List").html(response.Data);

                    $("tfoot", "#tblCaseFee").show();

                    $(".pull-right.page-box.casefee").cPaging({
                        totalCount: parseInt($("#TotalCount").val()),
                        pageNo: parseInt($("#PageNo").val()),
                        pageSize: parseInt($("#PageSize").val()),
                        callBack: caseInfo.ARCaseFee.List,
                        callBackArgs: null
                    });

                    var totalCount = parseInt($("#TotalCount").val());

                    caseInfo.ResetSize();

                    if (totalCount > 0) {
                        $("tfoot", "#tblCaseFee").show();
                        $(".simple-grid-none-data-wrap").hide();
                    } else {
                        $("tfoot", "#tblCaseFee").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }

                    caseInfo.ARCaseFee.BindMenu();

                    $.closeLoading();
                }
            }, true);
        },

        BindMenu: function () {
            $('#casegridSection').contextMenu('feeMenu', {
                menuStyle: {
                    width: '152px'
                },
                itemStyle: {
                    width: '150px'
                },
                bindings: {
                    'create': function (t, e) {
                        caseInfo.ARCaseFee.Objects.Open();
                    },
                    'paymentapply': function (t, e) {
                        caseInfo.ARCaseFee.PaymentApply.Open();
                    },
                    'contractfileview': function (t, e) {
                        var contractId = $(e).find("span").html();
                        contract.Contract.Files.List(contractId);
                    },
                    'feeYearlyConfirm': function (t, e) {
                        var feeId = $(e).find("span").html();
                        caseInfo.ARCaseFee.OpenYearlyInform(feeId);
                    },
                    'feeConfirm': function (t, e) {
                        var feeId = $(e).find("span").html();
                        caseInfo.ARCaseFee.OpenConfirm(feeId);
                    },
                    'invoiceConfirm': function (t, e) {
                        //var feeId = $(e).find("span").html();
                        caseInfo.ARCaseFee.Invoice.Open();
                    },
                    'view': function (t, e) {
                        var caseFeeId = $(e).find("span").text();
                        if (caseFeeId == '') {
                            $.showModalMessageBox("请选择查看的票据文件.");
                            return false;
                        }

                        var caseFileName = $(e).find("lable").text();
                        if (caseFileName == '') {
                            $.showModalMessageBox("无票据文件.");
                            return false;
                        }

                        var caseno = $(e).find("div").text();

                        var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                        var picfiles = new Array('jpg', 'tif', 'pdf');
                        var extName = caseFileName.substring(caseFileName.lastIndexOf('.') + 1, caseFileName.length);

                        if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                            var path = GV_IPR.OfficeOnlineUrl + GV_IPR.IPROnlineUrl + "CaseFeeFiles/" + caseno + "/" + caseFileName;
                            window.open(path);
                        }
                        else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                            var path = GV_IPR.IPROnlineUrl + "CaseFeeFiles/" + caseno + "/" + caseFileName;
                            window.open(path);
                        } else {
                            caseInfo.ARCaseFee.Invoice.Download(caseFeeId);
                        }

                        return true;
                    },
                    'download': function (t, e) {
                        var feeId = $(e).find("span").html();

                        var caseFileName = $(e).find("lable").text();
                        if (caseFileName == '') {
                            $.showModalMessageBox("无票据文件.");
                            return false;
                        }

                        caseInfo.ARCaseFee.Invoice.Download(feeId);
                    },
                    'nolock': function (t, e) {
                        var feeId = $(e).find("span").html();
                        caseInfo.ARCaseFee.Unlock(feeId);
                    },
                    'removefeehedgingfile': function (t, e) {
                        var feeId = $(e).find("span").text();
                        if (feeId == '') {
                            $.showModalMessageBox("请选择待转票文件.");
                            return false;
                        }
                        caseInfo.ARCaseFee.RemoveFeeHedgingFile(feeId);
                        return true;
                    },
                    'feeConfirmClear': function (t, e) {
                        var feeId = $(e).find("span").html();
                        caseInfo.ARCaseFee.CaseFeeConfirmClear(feeId);
                    },
                    'feeInvoiceConfirmClear': function (t, e) {
                        var feeId = $(e).find("span").html();
                        caseInfo.ARCaseFee.CaseFeeInvoiceConfirmClear(feeId);
                    },
                    'delete': function (t, e) {
                        var feeId = $(e).find("span").html();
                        caseInfo.ARCaseFee.Delete(feeId);
                    },

                    'edit': function (t, e) {
                        var seqno = $(e).find("span").html();
                        caseInfo.ARCaseFee.Objects.Edit(seqno);
                    },

                    'linked': function (t, e) {
                        caseInfo.ARCaseFee.Linked();
                    },
                    'paymentbycustomer': function (t, e) {
                        var feeId = $(e).find("span").html();
                        if (feeId == '') {
                            $.showModalMessageBox("请选择记录.");
                            return false;
                        }
                        caseInfo.ARCaseFee.PaymentByCustomer(feeId);
                    },
                    'firstyear': function (t, e) {
                        var feeId = $(e).find("span").html();
                        if (feeId == '') {
                            $.showModalMessageBox("请选择记录.");
                            return false;
                        }
                        caseInfo.ARCaseFee.LabelFirstYear(feeId);
                    },
                    'refresh': function (t, e) {
                        caseInfo.ARCaseFee.List();
                    }
                },
                onContextMenu: function (e) {
                    return true;
                },
                onShowMenu: function (e, menu) {
                    if ($(e.target).parents("tr").find(".feeId").hasClass("feeId")) {
                        var feeItemId = $(e.target).parents("tr").find("#item_CaseFeeId").val();
                        var feeId = $(e.target).parents("tr").find("#item_CaseFeeId").val();
                        var caseNo = $(e.target).parents("tr").find("#item_CaseNo").val();
                        var fileName = $(e.target).parents("tr").find("#item_Invoice_InvoiceFileName").val();
                        var contractId = $(e.target).parents("tr").find("#item_ContractId").val();
                        var seqNo = $(e.target).parents("tr").find("#item_BatchNo").val();

                        $('#feeConfirm', menu).append("<span style='display:none'>" + feeId + "</span>");
                        $('#feeYearlyConfirm', menu).append("<span style='display:none'>" + feeId + "</span>");
                        $('#invoiceConfirm', menu).append("<span style='display:none'>" + feeId + "</span>");
                        $('#view', menu).append("<span style='display:none'>" + feeId + "</span><lable style='display:none'>" + fileName + "</lable><div style='display:none'>" + caseNo + "</div>");
                        $('#download', menu).append("<span style='display:none'>" + feeId + "</span><lable style='display:none'>" + fileName + "</lable><div style='display:none'>" + caseNo + "</div>");
                        $('#nolock', menu).append("<span style='display:none'>" + feeId + "</span>");
                        $('#removefeehedgingfile', menu).append("<span style='display:none'>" + feeId + "</span>");
                        $('#delete', menu).append("<span style='display:none'>" + feeId + "</span>");
                        $('#feeConfirmClear', menu).append("<span style='display:none'>" + feeId + "</span>");
                        $('#feeInvoiceConfirmClear', menu).append("<span style='display:none'>" + feeId + "</span>");
                        $('#paymentbycustomer', menu).append("<span style='display:none'>" + feeId + "</span>");
                        $('#firstyear', menu).append("<span style='display:none'>" + feeId + "</span>");
                        $('#feeYearlyConfirm', menu).append("<span style='display:none'>" + feeId + "</span>");
                        $('#contractfileview', menu).append("<span style='display:none'>" + contractId + "</span>");
                        $('#edit', menu).append("<span style='display:none'>" + seqNo + "</span>");

                    } else {
                        $('#view,#download,#linked', menu).remove();
                        $('#feeConfirm,#feeYearlyConfirm', menu).remove();
                        $('#invoiceConfirm', menu).remove();
                        $('#nolock', menu).remove();
                        $('#removefeehedgingfile', menu).remove();
                        $('#delete,#feeConfirmClear,#feeInvoiceConfirmClear', menu).remove();
                        $('#paymentbycustomer', menu).remove();
                        $('#firstyear', menu).remove();
                        $('#contractfileview', menu).remove();
                        $('#edit', menu).remove();
                    }
                    return menu;
                }
            });
        },

        /*案件应收账款*/
        OpenInform: function (caseFileTypeId) {
            if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }
            var data =
            {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                caseNo: $("#Case_CaseBasicInfo_CaseNo").val(),
                caseTypeId: $("#Case_CaseBasicInfo_CaseTypeId").val(),
                caseFileTypeId: caseFileTypeId
            };
            var url =  AP_ROOT + AP_PAGE_ID + "/IPR/ARCaseFee/CaseFeeInform";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseFeeInformModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseFeeInformModal').on('hidden.bs.modal', function () {
                    $("#caseFeeInformModal").remove();
                });
            });

            //$('.caseFeeInform').load(url, data, function(result) {
            //    $.closeLoading();
            //    $('#caseFeeInformModal').modal({ backdrop: 'static', keyboard: false });
            //});
        },
        CloseInform: function () {
            $('#caseFeeInformModal').modal('hide');
        },
        CreateUpdateInform: function () {

            if ($("#DefaultCaseFee_CaseFeeTypeId").val() == '') {
                $.showModalMessageBox("请选择费用类型.");
                return false;
            }

            if ($("#DefaultCaseFee_CaseFeeTypeName").val() == '') {
                $.showModalMessageBox("请选择费用类型.");
                return false;
            }

            //if ($("#DefaultCaseFee_RequestUser").val() == '') {
            //    $.showModalMessageBox("请选择收费人.");
            //    return false;
            //}

            //if ($("#DefaultCaseFee_FeeTypeId").val() == '3' && ($("#DefaultCaseFee_Yealy").val() == '' || parseInt($("#DefaultCaseFee_Yealy").val()) < 1)) {
            //    //年费必填,且大于0
            //    $.showModalMessageBox("请输入年限，年限为大于0的正整数.");
            //    return false;
            //}

            var data = {};

            var j = 0;
            var dataIsNOk = false;

            $("#tblCaseFeeItemList>tbody>tr").each(function (i, e) {

                if ($(e).css("display") != 'none') {
                    if (i == 0) {
                        data["CaseFeeList[" + j + "].CaseId"] = $("#Case_CaseBasicInfo_CaseId").val();
                        data["CaseFeeList[" + j + "].CaseNo"] = $("#CaseNo").val();
                        data["CaseFeeList[" + j + "].CaseFeeTypeId"] = $("#DefaultCaseFee_CaseFeeTypeId").val();
                        data["CaseFeeList[" + j + "].CaseFeeTypeName"] = $("#DefaultCaseFee_CaseFeeTypeName").val();
                        data["CaseFeeList[" + j + "].RequestUser"] = $("#DefaultCaseFee_RequestUser").val();

                        if ($("#DefaultCaseFee_CaseFeeTypeId").val() == 3) {
                            //年费
                            data["CaseFeeList[" + j + "].AnnualYear"] = $("#Case_CaseFeeInformYearly").val();
                            data["CaseFeeList[" + j + "].IsFirstYear"] = $("#DefaultCaseFee_IsFirstYear").attr("checked") == 'checked';
                            data["CaseFeeList[" + j + "].AnnualFrom"] = $("#Case_CaseFeeInformYearly").find("option:selected").attr("annualFrom");
                            data["CaseFeeList[" + j + "].AnnualEnd"] = $("#Case_CaseFeeInformYearly").find("option:selected").attr("annualEnd");
                        }

                        data["CaseFeeList[" + j + "].PaymentByCustomer"] = $(e).find("#item_PaymentByCustomer").prop("checked") == true;
                        data["CaseFeeList[" + j + "].Amount"] = $(e).find("#item_Amount").val();
                    } else {
                        data["CaseFeeList[" + j + "].CaseId"] = $("#Case_CaseBasicInfo_CaseId").val();
                        data["CaseFeeList[" + j + "].CaseNo"] = $("#CaseNo").val();
                        data["CaseFeeList[" + j + "].CaseFeeTypeId"] = $(e).find("#hidCaseFee_CaseFeeTypeId" + j).val();
                        data["CaseFeeList[" + j + "].CaseFeeTypeName"] = $(e).find("#CaseFee_CaseFeeTypeName" + j).val();
                        //data["CaseFeeList[" + j + "].RequestUser"] = $("#DefaultCaseFee_RequestUser").val();
                        data["CaseFeeList[" + j + "].PaymentByCustomer"] = $(e).find("#item_PaymentByCustomer").prop("checked") == true;
                        data["CaseFeeList[" + j + "].Amount"] = $(e).find("#item_Amount").val();

                        if ($(e).find("#hidCaseFee_CaseFeeTypeId" + j).val() == $("#DefaultCaseFee_CaseFeeTypeId").val()) {
                            dataIsNOk = true;
                            $.showModalMessageBox("第" + (j + 1) + "行，<br>费用类型不能与主费用类型一致.");
                            return false;
                        }

                        if (data["CaseFeeList[" + j + "].CaseFeeTypeId"] == '') {
                            dataIsNOk = true;
                            $.showModalMessageBox("第" + (j + 1) + "行，请选择费用类型.");
                            return false;
                        }
                    }
                    j++;
                }
            });

            if (dataIsNOk) return false;
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/ARCaseFee/CaseFeeInformCreate", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("保存成功.");
                    $('#caseFeeInformModal').modal('hide');

                    caseInfo.ARCaseFee.List();
                    caseInfo.CaseEvent.List();
     
                } else {

                    $.showModalMessageBox(response.Message);
                }
            });
        },

        /*案件费用确认*/
        OpenConfirm: function (caseFeeId) {
            if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }
            var data =
            {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                caseNo: $("#Case_CaseBasicInfo_CaseNo").val(),
                caseTypeId: $("#Case_CaseBasicInfo_CaseTypeId").val(),
                caseFeeId: caseFeeId
            };
            var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseFeeConfirm";
            $.openLoading();


            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseFeeConfirmModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseFeeConfirmModal').on('hidden.bs.modal', function () {
                    $("#caseFeeConfirmModal").remove();
                });
            });

            //$('.caseFeeConfirm').load(url, data, function(result) {
            //    $.closeLoading();
            //    $('#caseFeeConfirmModal').modal({ backdrop: 'static', keyboard: false });
            //});
        },
        CloseConfirm: function () {
            $('#caseFeeConfirmModal').modal('hide');
        },
        CreateUpdateConfirm: function () {

            if ($("#DefaultCaseFee_ActualAmount").val() == '') {
                $.showModalMessageBox("请输入需交金额.");
                return false;
            }

            if ($("#DefaultCaseFee_ActualAmount").val() == '') {
                $.showModalMessageBox("请输入实交金额.");
                return false;
            }

            if ($("#DefaultCaseFee_GainedDate").val() == '') {
                $.showModalMessageBox("请输入到帐日期.");
                return false;
            }

            if ($("#DefaultCaseFee_Amount").val() != $("#DefaultCaseFee_ActualAmount").val()) {
                $.showModalMessageBox("需交金额与实交金额不一致.");
                return false;
            }

            $("#caseFeeConfirm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseFeeConfirmCreate", function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("保存成功.");
                    $('#caseFeeConfirmModal').modal('hide');

                    if (caseInfo.CaseFee) {
                        caseInfo.ARCaseFee.List();
                    }
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        /*费用年度*/
        OpenYearlyInform: function (caseFeeId) {
            if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }
            var data =
            {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                caseFeeId: caseFeeId
            };
            var url =  AP_ROOT + AP_PAGE_ID + "/IPR/ARCaseFee/CaseFeeInformAnnualYear";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseFeeInformYearlyModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseFeeInformYearlyModal').on('hidden.bs.modal', function () {
                    $("#caseFeeInformYearlyModal").remove();
                });
            });

            //$('.caseFeeConfirm').load(url, data, function(result) {
            //    $.closeLoading();
            //    $('#caseFeeConfirmModal').modal({ backdrop: 'static', keyboard: false });
            //});
        },
        CreateUpdateYearlyInform: function () {

            if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }

            if ($("#Case_CaseFeeInformYearly").val() == '') {
                $.showModalMessageBox("申请日为空，不允许设定年度.");
                return false;
            }

            var data =
            {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                caseFeeId: $("#CaseFeeId").val(),
                yearly: $("#Case_CaseFeeInformYearly").val(),
                annualFrom: $("#Case_CaseFeeInformYearly").find("option:selected").attr("annualFrom"),
                annualEnd: $("#Case_CaseFeeInformYearly").find("option:selected").attr("annualEnd"),
            };

            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/ARCaseFee/LabelAnnualYear", data, function (response) {
                if (response.IsSuccess) {
                    caseInfo.ARCaseFee.List();
                    caseInfo.CaseEvent.List();
                    $.showModalMessageBox("年度设定成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        CloseYearlyInform: function () {
            $('#caseFeeInformYearlyModal').modal('hide');
        },

        Invoice: {
            /*案件票据确认*/
            Open: function () {

                if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                    $.showModalMessageBox("请先保存案件基本资料.");
                    return false;
                }
                var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
                if (caseFeeIds.length == 0) {
                    $.showModalMessageBox("请选择需要确认的应收款.");
                    return false;
                }

                var caseTypeIds = new Array('4','5');

                var caseClassType = '';

                //商标以外的案件，除代理费发票允许上传外，其他类型发票不允许上传
                if ($.inArray($("#Case_CaseBasicInfo_CaseTypeId").val(), caseTypeIds) <= -1) {
                    caseClassType = 'Patent';
                    var caseFeeTypeIds = new Array('0');
                    var caseTypeName = $("#Case_CaseBasicInfo_CaseTypeId").find("option:selected").text();

                    var result = true;
                    $("input[name='chkCaseFeeId']:checked").each(
                        function (i) {
                            if ($.inArray($(this).attr("casefeetypeid"), caseFeeTypeIds) <= -1) {
                                $.showModalMessageBox(caseTypeName + "案件不允上传" + $(this).attr("casefeetypename") + "的发票文件.");
                                result = false;
                                return false;
                            }
                        }
                    );

                    if (!result) return false;
                } else {
                    caseClassType = 'TradeCopyright';
                }

                var data =  
                {
                    caseFeeIds: caseFeeIds,
                    caseClassType: caseClassType,
                    invoiceType: 'Invoice'
                };

                var url =  AP_ROOT + AP_PAGE_ID + "/IPR/CaseFeeInvoice/CaseFeeInvoiceConfirm";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#caseFeeInvoiceConfirmModal').modal({ backdrop: 'static', keyboard: false });
                    $('#caseFeeInvoiceConfirmModal').on('hidden.bs.modal', function () {
                        $("#caseFeeInvoiceConfirmModal").remove();
                    });
                });

            },

            Download: function (caseFeeId) {
                window.open( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseFeeFileDownload?caseFeeId=" + caseFeeId);
                return true;
            },

            Close: function () {
                $('#caseFeeInvoiceConfirmModal').modal('hide');
            },

            Confirm: function () {

                if ($("#Invoice_InvoiceNo").val() == '') {
                    $.showModalMessageBox("请输入票据编号.");
                    return false;
                }

                if ($("#Invoice_InvoiceDate").val() == '') {
                    $.showModalMessageBox("请输入票据日期.");
                    return false;
                }

                if ($("#flInvoiceFile").val() == '') {
                    $.showModalMessageBox("请选择上传文件.");
                    return false;
                }

                //专利发票不需要付款方式,付款人
                if ($("#CaseClassType").val() == 'Patent' && $("#InvoiceType").val() == 'Invoice') {

                } else {
                    if ($("#PaymentMode").val() == '') {
                        $.showModalMessageBox("付款方式.");
                        return false;
                    }

                    if ($("#PayerName").val() == '') {
                        $.showModalMessageBox("付款人.");
                        return false;
                    }
                }

                $.openLoading();
                $('#caseFeeInvoiceConfirm').ajaxSubmit({
                    success: function (response) {
                        $.closeLoading();
                        if (response.IsSuccess) {
                            $.showModalMessageBox("保存成功.");
                            $('#caseFeeInvoiceConfirmModal').modal('hide');

                            caseInfo.ARCaseFee.List();
                            caseInfo.CaseEvent.List();

                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    }
                });
            },

            /*票据文件*/
            File: {
                Open: function (caseFeeGuid) {
                    var data = {
                        caseFeeGuid: caseFeeGuid,
                    };
  
                    var url =  AP_ROOT + AP_PAGE_ID + "/FAM/InvoiceFile/List";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#invoiceFileListModal').modal({ backdrop: 'static', keyboard: false });
                        $('#invoiceFileListModal').on('hidden.bs.modal', function () {
                            $("#invoiceFileListModal").remove();
                        });
                    });
                },

              
            },
        },

        CaseFeeTypeItem: {
            Add: function () {
                var tr = $($('#tblCaseFeeItemList>tbody>tr')[0]).clone().show();
                $($("td", tr)[0]).html("<input type='hidden' value='' id='hidCaseFee_CaseFeeTypeId" + $("#tblCaseFeeItemList>tbody>tr").length + "' /><input class='CaseFee_CaseFeeTypeName form-control' sytle='text-align:center;width:100px' id='CaseFee_CaseFeeTypeName" + $("#tblCaseFeeItemList>tbody>tr").length + "' readonly type='text' value='' />");
                $("#tblCaseFeeItemList").append(tr);
                $('.btn_remove', tr).removeAttr('disabled');
                return tr;
            },
            Clear: function (e) {
                $(e).parents("tr").find(":input[type='text']").val('');
                $(e).parents("tr").find(":input[type='hidden']").val('');
                $(e).parents("tr").find(":input[type='checkbox']").attr("checked", false);
            },
            Remove: function (e) {
                $(e).parents("tr").remove();
            }
        },

        CaseFeeConfirmClearCallBack: function (caseFeeId) {
            var data = { caseFeeId: caseFeeId };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseFeeConfirmClear", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("清除到帐成功");
                    caseInfo.ARCaseFee.List();
                    caseInfo.CaseEvent.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        CaseFeeConfirmClear: function (caseFeeId) {
            $.showModalConfirmDialog("确定清除到帐？", "caseInfo.ARCaseFee.CaseFeeConfirmClearCallBack", caseFeeId);
            return true;
        },

        CaseFeeInvoiceConfirmClear: function (caseFeeId) {
            $.showModalConfirmDialog("确定清除票据？", "caseInfo.ARCaseFee.CaseFeeInvoiceConfirmClearCallBack", caseFeeId);
            return true;
        },

        CaseFeeInvoiceConfirmClearCallBack: function (caseFeeId) {
            var data = { caseFeeId: caseFeeId };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/ARCaseFee/CaseFeeInvoiceConfirmClear", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("清除票据成功");
                    caseInfo.ARCaseFee.List();
                    caseInfo.CaseEvent.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        Unlock: function (caseFeeId) {
            $.showModalConfirmDialog("确定解锁应收账款？", "caseInfo.ARCaseFee.UnlockCallBack", caseFeeId);
            return true;
        },

        UnlockCallBack: function (caseFeeId) {
            var data = { caseFeeId: caseFeeId };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/ARCaseFee/CaseFeeUnlock", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("解锁成功");
                    caseInfo.ARCaseFee.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        Delete: function (caseFeeId) {
            $.showModalConfirmDialog("确定删除应收账款？", "caseInfo.ARCaseFee.DeleteCallBack", caseFeeId);
            return true;
        },

        DeleteCallBack: function (caseFeeId) {
            var data = { caseFeeId: caseFeeId };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/ARCaseFee/CaseFeeDelete", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("删除成功.");
                    caseInfo.ARCaseFee.List();
                    caseInfo.CaseEvent.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        RemoveFeeHedgingFile: function (caseFeeId) {
            var data = { caseFeeId: caseFeeId };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/ARCaseFee/RemoveFeeHedgingFile", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("解除待转票成功.");
                    caseInfo.ARCaseFee.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        //客户自缴
        PaymentByCustomer: function (caseFeeId) {
            var data = { caseFeeId: caseFeeId };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/ARCaseFee/CaseFeePaymentByCustomer", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("设定客户自缴成功.");
                    caseInfo.ARCaseFee.List();
                    caseInfo.CaseEvent.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        /*首年年费*/
        LabelFirstYear: function (caseFeeId) {

            var data = {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                caseFeeId: caseFeeId
            };

            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/ARCaseFee/LabelFirstYear", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("设定首年年费成功.");
                    caseInfo.ARCaseFee.List();
                    caseInfo.CaseEvent.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
    },
    /*应付账款*/
    APCaseFee: {
        /*案件费用列表*/
        List: function () {
            var data = {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                pageNo: $("#PageNo").val(),
                pageSize: $("#PageSize").val()
            };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/APCaseFee/CaseFeeList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $("#dv_List").empty();
                    $("#dv_List").html(response.Data);

                    $("tfoot", "#tblCaseFee").show();

                    $(".pull-right.page-box.casefee").cPaging({
                        totalCount: parseInt($("#TotalCount").val()),
                        pageNo: parseInt($("#PageNo").val()),
                        pageSize: parseInt($("#PageSize").val()),
                        callBack: caseInfo.APCaseFee.List,
                        callBackArgs: null
                    });

                    var totalCount = parseInt($("#TotalCount").val());

                    caseInfo.ResetSize();

                    if (totalCount > 0) {
                        $("tfoot", "#tblCaseFee").show();
                        $(".simple-grid-none-data-wrap").hide();
                    } else {
                        $("tfoot", "#tblCaseFee").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }

                    caseInfo.APCaseFee.BindMenu();

                    $.closeLoading();
                }
            }, true);
        },

        BindMenu: function () {
            $('#casegridSection').contextMenu('feeMenu', {
                menuStyle: {
                    width: '152px'
                },
                itemStyle: {
                    width: '150px'
                },
                bindings: {
                    'invoiceConfirm': function (t, e) {
                        caseInfo.APCaseFee.Invoice.Open();
                    },
                    'view': function (t, e) {
                        var caseFeeId = $(e).find("span").text();
                        if (caseFeeId == '') {
                            $.showModalMessageBox("请选择查看的付款凭证文件.");
                            return false;
                        }

                        var caseFileName = $(e).find("lable").text();
                        if (caseFileName == '') {
                            $.showModalMessageBox("无付款凭证文件.");
                            return false;
                        }

                        var caseno = $(e).find("div").text();

                        var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                        var picfiles = new Array('jpg', 'tif', 'pdf');
                        var extName = caseFileName.substring(caseFileName.lastIndexOf('.') + 1, caseFileName.length);

                        if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                            var path = GV_IPR.OfficeOnlineUrl + GV_IPR.IPROnlineUrl + "CaseFeeFiles/" + caseno + "/" + caseFileName;
                            window.open(path);
                        }
                        else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                            var path = GV_IPR.IPROnlineUrl + "CaseFeeFiles/" + caseno + "/" + caseFileName;
                            window.open(path);
                        } else {
                            caseInfo.APCaseFee.Invoice.Download(caseFeeId);
                        }

                        return true;
                    },
                    'download': function (t, e) {

                        var caseFileName = $(e).find("lable").text();
                        if (caseFileName == '') {
                            $.showModalMessageBox("无付款凭证文件.");
                            return false;
                        }

                        var feeId = $(e).find("span").html();
                        caseInfo.APCaseFee.Invoice.Download(feeId);
                    },
                    'refresh': function (t, e) {
                        caseInfo.APCaseFee.List();
                    },
                    'paymentapply': function (t, e) {
                        caseInfo.APCaseFee.PaymentApply.Open();
                    }
                },
                onContextMenu: function (e) {
                    return true;
                },
                onShowMenu: function (e, menu) {
                    if ($(e.target).parents("tr").find(".feeId").hasClass("feeId")) {
                        var feeId = $(e.target).parents("tr").find("#item_CaseFeeId").val();
                        var feeGuid = $(e.target).parents("tr").find("#item_CaseFeeGuid").val();
                        var caseNo = $(e.target).parents("tr").find("#item_CaseNo").val();
                        var fileName = $(e.target).parents("tr").find("#item_Invoice_InvoiceFileName").val();

                        $('#invoiceConfirm', menu).append("<span style='display:none'>" + feeId + "</span>");
                        $('#view', menu).append("<span style='display:none'>" + feeId + "</span><lable style='display:none'>" + fileName + "</lable><div style='display:none'>" + caseNo + "</div>");
                        $('#download', menu).append("<span style='display:none'>" + feeId + "</span><lable style='display:none'>" + fileName + "</lable><div style='display:none'>" + caseNo + "</div>");
                        $('#paymentapply', menu).append("<span style='display:none'>" + feeId + "</span>");

 
                    } else {
                        $('#view,#download', menu).remove();
                        $('#invoiceConfirm', menu).remove();
                        $('#paymentapply', menu).remove();
                     }
                    return menu;
                }
            });
        },

        Invoice: {

            /*案件票据确认*/
            Open: function () {

                if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                    $.showModalMessageBox("请先保存案件基本资料.");
                    return false;
                }
                var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
                if (caseFeeIds.length == 0) {
                    $.showModalMessageBox("请选择需要确认的应付款.");
                    return false;
                }

               
                var caseTypeIds = new Array('4');

                if ($.inArray($("#Case_CaseBasicInfo_CaseTypeId").val(), caseTypeIds) > -1) {

                    var caseFeeTypeIds = new Array('51', '52', '53');
                    var caseTypeName = $("#Case_CaseBasicInfo_CaseTypeId").find("option:selected").text();

                    var result = true;
                    $("input[name='chkCaseFeeId']:checked").each(
                        function (i) {
                            if ($.inArray($(this).attr("casefeetypeid"), caseFeeTypeIds) <= -1) {
                                $.showModalMessageBox(caseTypeName + "案件不允上传" + $(this).attr("casefeetypename") + "的付款凭证.");
                                result = false;
                                return false;
                            }
                        }
                    );

                    if (!result) return false;
                }


                var data =
                {
                    caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                    caseNo: $("#Case_CaseBasicInfo_CaseNo").val(),
                    caseTypeId: $("#Case_CaseBasicInfo_CaseTypeId").val(),
                    caseFeeIds: caseFeeIds
                };

                var url =  AP_ROOT + AP_PAGE_ID + "/IPR/APCaseFee/CaseFeeInvoiceConfirm";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#caseFeeInvoiceConfirmModal').modal({ backdrop: 'static', keyboard: false });
                    $('#caseFeeInvoiceConfirmModal').on('hidden.bs.modal', function () {
                        $("#caseFeeInvoiceConfirmModal").remove();
                    });
                });

            },

            Close: function () {
                $('#caseFeeInvoiceConfirmModal').modal('hide');
            },

            CreateUpdate: function () {

                if ($("#DefaultCaseFee_InvoiceNo").val() == '') {
                    $.showModalMessageBox("请输入付款票据号.");
                    return false;
                }

                if ($("#DefaultCaseFee_InvoiceAmount").val() == '') {
                    $.showModalMessageBox("请输入付款金额.");
                    return false;
                }

                if ($("#DefaultCaseFee_InvoiceDate").val() == '') {
                    $.showModalMessageBox("请输入付款日期.");
                    return false;
                }

                if ($("#flInvoiceFile").val() == '') {
                    $.showModalMessageBox("请选择付款凭证文件.");
                    return false;
                }

                $.openLoading();
                $('#caseFeeInvoiceConfirm').ajaxSubmit({
                    success: function (response) {
                        $.closeLoading();
                        if (response.IsSuccess) {
                            $.showModalMessageBox("保存成功.");
                            $('#caseFeeInvoiceConfirmModal').modal('hide');

                            caseInfo.APCaseFee.List();
                            caseInfo.CaseEvent.List();

                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    }
                });
            },

            View: function () {
            
            },

            Download: function (caseFeeId) {
                window.open( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/APCaseFeeFileDownload?caseFeeId=" + caseFeeId);
                return true;
            },
        },

        PaymentApply: {
            /*垫付款申请*/
            Open: function() {

                if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                    $.showModalMessageBox("请先保存案件基本资料.");
                    return false;
                }
                var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
                if (caseFeeIds.length == 0) {
                    $.showModalMessageBox("请选择需要垫付的应付款.");
                    return false;
                }

                var data =
                {
                    caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                    caseNo: $("#Case_CaseBasicInfo_CaseNo").val(),
                    caseTypeId: $("#Case_CaseBasicInfo_CaseTypeId").val(),
                    caseFeeIds: caseFeeIds
                };

                var url =  AP_ROOT + AP_PAGE_ID + "/IPR/APCaseFee/PaymentApply";
                $.openLoading();

                $("<div></div>").load(url, data, function(result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#paymentApplyModal').modal({ backdrop: 'static', keyboard: false });
                    $('#paymentApplyModal').on('hidden.bs.modal', function() {
                        $("#paymentApplyModal").remove();
                    });
                });
            },

            Close: function() {
                $('#paymentApplyModal').modal('hide');
            },

            Apply: function() {
                /*垫付款申请*/

                if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                    $.showModalMessageBox("请先保存案件基本资料.");
                    return false;
                }
                var data =
                {
                    caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                    caseNo: $("#Case_CaseBasicInfo_CaseNo").val(),
                    caseFeeIds: $.checkbox.vals("chkCaseFeeId"),
                    remark: $("#Remark").val()
                };
                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/APCaseFee/PaymentApplyCreate", data, function(response) {
                    if (response.IsSuccess) {
                        caseInfo.APCaseFee.List();
                        caseInfo.APCaseFee.PaymentApply.Close();
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },

            Cancel: function() {

            },

            Audit: {
                Open: function (applicationId) {
                    var data =
                    {
                        applicationId: applicationId,
                    };

                    var url =  AP_ROOT + AP_PAGE_ID + "/FAM/AP/CaseFeeApplicationAuditList";
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
                Close: function () {
                    $('#caseFeeApplicationAuditListModal').modal('hide');
                },
            }
        }
    },

    CaseFile: {
        Init: function () {
            caseInfo.CaseFile.List();
            //caseInfo.CaseFile.BindMenu();
        },

        /*文档类表*/
        List: function () {
            var data = {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                pageNo: $("#PageNo").val(),
                pageSize: $("#PageSize").val()
            };

            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseFileList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $("#dv_List").empty();
                    $("#dv_List").html(response.Data);

                    $(".pull-right.page-box.casefile").cPaging({
                        totalCount: parseInt($("#TotalCount").val()),
                        pageNo: parseInt($("#PageNo").val()),
                        pageSize: parseInt($("#PageSize").val()),
                        callBack: caseInfo.CaseFile.List,
                        callBackArgs: null
                    });

                    var totalCount = parseInt($("#TotalCount").val());

                    caseInfo.ResetSize();

                    if (totalCount > 0) {
                        $("tfoot", "#tblCaseFile").show();
                        $(".simple-grid-none-data-wrap").hide();
                    } else {
                        $("tfoot", "#tblCaseFile").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }

                    caseInfo.CaseFile.BindMenu();

                    $.closeLoading();
                }
            }, true);
        },

        /*上传文件*/
        //isTransformedFile 导出专文文档
        Open: function (isTransformedFile) {

            if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }
            var data =
            {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                caseNo: $("#Case_CaseBasicInfo_CaseNo").val(),
                caseTypeId: $("#Case_CaseBasicInfo_CaseTypeId").val(),
                hedgingFileTypeId: 0,
                isTransformedFile: isTransformedFile
            };

            var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseFileUpload";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseFileUploadingModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseFileUploadingModal').on('hidden.bs.modal', function () {
                    $("#caseFileUploadingModal").remove();
                });

                var caseFileType = new AssociateCaseFileType(
                    $("#div_CaseFileTypeList"),
                    $("#CaseFileTypeId"),
                    $("#CaseFileTypeName"),
                    $("#Case_CaseBasicInfo_CaseTypeId").val(),
                    $("#IsTransformedFile").val() == 'true',
                    caseInfo.CaseFile.ProcessFileTypeSelectedCallBack
                );
            });
        },

        Close: function () {
            $('#caseFileUploadingModal').modal('hide');
        },

        CreateUpdate: function () {

            var caseFileTypeId = $("#CaseFileTypeId").val();

            if ($("#CaseFileTypeId").val() == '' || $("#CaseFileTypeId").val() == '0') {
                $.showModalMessageBox("请选择文件类型.");
                return false;
            }

            if ($("#flCaseFile").val() == "") {
                $.showModalMessageBox("请选择文档文件.");
                return false;
            }

            if ($("#UploadingTime").val() == "") {
                $.showModalMessageBox("请输入" + $(".spanreferencedate").text());
                return false;
            }
            $.openLoading();
            $('#uploadingForm').ajaxSubmit({
                success: function (response) {
                    $.closeLoading();
                    if (response.IsSuccess) {
                        $('#caseFileUploadingModal').modal('hide');
                        caseInfo.LoadCase($("#Case_CaseBasicInfo_CaseId").val())
                        return true;
                    } else {
                        $.showModalMessageBox(response.Message);
                        return false;
                    }
                }
            });
        },

        Download: function (caseFileId) {
            window.open( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseFileDownload?caseFileId=" + caseFileId);
            return true;
        },

        UnLock: function (caseFileId) {
            $.showModalConfirmDialog("确定解锁文件？", "caseInfo.CaseFile.UnLockCallBack", caseFileId);
            return true;
        },

        UnLockCallBack: function (caseFileId) {
            var data = { caseFileId: caseFileId };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseFileUnlock", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("解锁成功");
                    caseInfo.CaseFile.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        Delete: function (caseFileId) {
            $.showModalConfirmDialog("确定删除文件？", "caseInfo.CaseFile.DeleteCallBack", caseFileId);
            return true;
        },

        DeleteCallBack: function (caseFileId) {
            var data = { caseFileId: caseFileId };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseFileDelete", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("删除成功.");
                    caseInfo.LoadCase($("#Case_CaseBasicInfo_CaseId").val())
                    caseInfo.CaseFile.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        ToWord: function () {

            if ($("#CustomerId").val() == '' || $("#CustomerId").val() == '0') {
                $.showModalMessageBox("该案件未选择客户，请先选择客户.");
                return false;
            }

            if ($("#CaseFileTypeId").val() == '') {
                $.showModalMessageBox("请选择文件类型.");
                return false;
            }

            var caseIds = [];
            caseIds[0] = $("#Case_CaseBasicInfo_CaseId").val();
            //long customerId, int caseFileTypeId, long[] caseIds
            var data = {
                customerId: $("#CustomerId").val(),
                caseFileTypeId: $("#CaseFileTypeId").val(),
                caseIds: caseIds,
            };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/ExportCaseListToWord", data, function (response) {
                if (response.IsSuccess) {
                    var customerId = response.Data.split('|')[0];
                    var fileName = response.Data.split('|')[1];
                    window.open( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseExportFileDownload?customerId=" + customerId + "&fileName=" + fileName);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        ProcessFileTypeSelectedCallBack: function (caseFileTypeId, caseFileTypeNameText, hedgingFileTypeId, hedgingFeeTypeId) {
            $(".spanreferencedate").text(caseFileTypeNameText + "日期");

            if (caseFileTypeId == '8'
                || caseFileTypeId == '38'
                || caseFileTypeId == '126'
                || caseFileTypeId == '127'
                || caseFileTypeId == '157') {
                //$(".spanreferencedate").text("申请日期");
                if (caseFileTypeId == '8') {
                    $(".caserequestno").css("display", 'block');
                }
            } else if (caseFileTypeId == '253'
                    || caseFileTypeId == '239'
                    || caseFileTypeId == '249'
                    || caseFileTypeId == '42'
            ) {
                //$(".spanreferencedate").text("授权日期");
            } else {
                // $(".spanreferencedate").text("参考日期");
            }

            $(".caseHedgingFile").css("display", 'none');
            $(".caseHedgingFee").css("display", 'none');
            $("#HedgingFileId").empty();
            $("#HedgingFeeId").empty();

            if (hedgingFileTypeId != '' || hedgingFeeTypeId != '') {
                //存在对冲文件或对冲发票
                var data = {
                    caseId: parseInt($("#Case_CaseBasicInfo_CaseId").val()),
                    caseFileTypeId: caseFileTypeId
                };

                $.ajaxSetup({
                    async: false
                });

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/GetHedgingFileAndFeeList", data, function (response) {
                    if (response.IsSuccess) {
                        if (response.Data.Item1.length > 0) {

                            $(".caseHedgingFile").css("display", 'block');

                            $.each(response.Data.Item1, function (i, c) {
                                if (i == 0) {
                                    $("#HedgingFileId").append("<option selected value='" + c.FileId + "'>" + c.FileTypeId + c.FileTypeName + "</option>");
                                } else {
                                    $("#HedgingFileId").append("<option value='" + c.FileId + "'>" + c.FileTypeId + c.FileTypeName + "</option>");
                                }
                            });

                        } else {
                            $("#HedgingFileId").append("<option selected value=''>" + "无" + "</option>");
                        }

                        if (response.Data.Item2.length > 0) {

                            $(".caseHedgingFee").css("display", 'block');

                            $.each(response.Data.Item2, function (i, c) {
                                if (i == 0) {
                                    $("#HedgingFeeId").append("<option selected value='" + c.CaseFeeId + "'>" + c.CaseFeeTypeId + c.CaseFeeTypeName + "</option>");
                                } else {
                                    $("#HedgingFeeId").append("<option value='" + c.CaseFeeId + "'>" + c.CaseFeeTypeId + c.CaseFeeTypeName + "</option>");
                                }
                            });

                        } else {
                            $("#HedgingFeeId").append("<option selected value=''>" + "无" + "</option>");
                        }

                    } else {
                        $("#HedgingFileId").append("<option selected value=''>" + "无" + "</option>");
                        $("#HedgingFeeId").append("<option selected value=''>" + "无" + "</option>");
                    }
                });
                $.ajaxSetup({
                    async: true
                });

            } else {
                $("#HedgingFileId").append("<option selected value=''>" + "无" + "</option>");
                $("#HedgingFeeId").append("<option selected value=''>" + "无" + "</option>");
            }
        },

        TagTransformed: function (caseFileId) {
            var caseFileIds = new Array();
            caseFileIds.push(caseFileId);
            var data = { caseFileIds: caseFileIds };

            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/TagTransformed", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("标记已转成功.");
                    caseInfo.CaseFile.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        BindMenu: function () {
            $('#casegridSection').contextMenu('fileMenu', {
                menuStyle: {
                    width: '152px'
                },

                itemStyle: {
                    width: '150px'
                },

                bindings: {
                    'create': function (t, e) {
                        caseInfo.CaseFile.Open(false);
                    },
                    'view': function (t, e) {
                        var caseFileId = $(e).find("span").text();
                        if (caseFileId == '') {
                            $.showModalMessageBox("请选择查看的文件.");
                            return false;
                        }

                        var caseFileName = $(e).find("lable").text();
                        if (caseFileName == '') {
                            $.showModalMessageBox("无文件.");
                            return false;
                        }

                        var caseno = $(e).find("div").text();

                        var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                        var picfiles = new Array('jpg', 'tif', 'pdf');
                        var extName = caseFileName.substring(caseFileName.lastIndexOf('.') + 1, caseFileName.length);

                        if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                            var path = GV_IPR.OfficeOnlineUrl + GV_IPR.IPROnlineUrl + "CaseFiles/" + caseno + "/" + caseFileName;
                            window.open(path);
                        }
                        else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                            var path = GV_IPR.IPROnlineUrl + "CaseFiles/" + caseno + "/" + caseFileName;
                            window.open(path);
                        } else {
                            caseInfo.CaseFile.Download(caseFileId);
                        }

                        return true;
                    },
                    'download': function (t, e) {
                        var caseFileId = $(e).find("span").text();
                        if (caseFileId == '') {
                            $.showModalMessageBox("请选择查看的文件.");
                            return false;
                        }
                        caseInfo.CaseFile.Download(caseFileId);
                        return true;
                    },
                    'unlock': function (t, e) {
                        var caseFileId = $(e).find("span").text();
                        if (caseFileId == '') {
                            $.showModalMessageBox("请选择解锁的文件.");
                            return false;
                        }
                        caseInfo.CaseFile.UnLock(caseFileId);
                        return true;
                    },
                    'tagTransformed': function (t, e) {
                        var caseFileId = $(e).find("span").text();
                        if (caseFileId == '') {
                            $.showModalMessageBox("请选择待转文文件.");
                            return false;
                        }
                        caseInfo.CaseFile.TagTransformed(caseFileId);
                        return true;
                    },
                    'delete': function (t, e) {
                        var caseFileId = $(e).find("span").text();
                        if (caseFileId == '') {
                            $.showModalMessageBox("请选择解锁的文件.");
                            return false;
                        }
                        caseInfo.CaseFile.Delete(caseFileId);
                        return true;
                    },
                    'toword': function (t, e) {
                        //var caseFileId = $(e).find("span").text();
                        //if (caseFileId == '') {
                        //    $.showModalMessageBox("请选择导出的文件.");
                        //    return false;
                        //}
                        //caseInfo.CaseFile.ToWord(caseFileId);
                        caseInfo.CaseFile.Open(true);
                        return true;
                    },
                    'cpc': function (t, e) {
                        caseInfo.CaseFile.CPC.Create();
                        return true;
                    },
                    'refresh': function (t, e) {
                        caseInfo.CaseFile.List();
                    },

                },
                onContextMenu: function (e) {
                    return true;
                },
                onShowMenu: function (e, menu) {
                    
                    if ($("#Case_CaseBasicInfo_CaseTypeId").val() == "1" || $("#Case_CaseBasicInfo_CaseTypeId").val() == "2" || $("#Case_CaseBasicInfo_CaseTypeId").val() == "3") {
                        $('#cpc', menu).append("<span style='display:none'></span>");
                    }
                    else {
                        $('#cpc', menu).remove();
                    }
                    if ($(e.target).parents("tr").find(".fileId").hasClass("fileId")) {
                        var fileId = $(e.target).parents("tr").find(".fileId").text();
                        var caseNo = $(e.target).parents("tr").find(".caseNo").text();
                        var fileName = $(e.target).parents("tr").find(".fileName").text();
                        $('#view', menu).append("<span style='display:none'>" + fileId + "</span><lable style='display:none'>" + fileName + "</lable><div style='display:none'>" + caseNo + "</div>");
                        $('#download', menu).append("<span style='display:none'>" + fileId + "</span>");
                        $('#unlock', menu).append("<span style='display:none'>" + fileId + "</span>");
                        $('#tagTransformed', menu).append("<span style='display:none'>" + fileId + "</span>");
                        $('#toword', menu).append("<span style='display:none'>" + fileId + "</span>");
                        $('#delete', menu).append("<span style='display:none'>" + fileId + "</span>");
                    } else {
                        $('#view,#download', menu).remove();
                        $('#unlock', menu).remove();
                        $('#tagTransformed', menu).remove();
                        $('#delete', menu).remove();
                    }
                    return menu;
                }
            });
        },

        CPC: {
            Create: function ()
            {
                if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                    $.showModalMessageBox("请先保存案件基本资料.");
                    return false;
                }

                var data = {
                    caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                };

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/CPC/GeneratePatentApplication", data, function (response) {
                    if (response.IsSuccess) {
                        window.open(AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CPCFileDownload?&fileName=" + response.Data);
                        $.showModalMessageBox("生成成功.");
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });

            }
        }
    },

    CaseTask: {

        BindEvent: function () {
            /*案件任务*/
            $("#btnCaseTaskCreate").off().on("click", function () {
                caseInfo.CaseTask.Open();
            });

            $("#btnCaseTaskClose,#btnCaseTaskCancel").off().on("click", function () {
                caseInfo.CaseTask.Close();
            });

            $("#btnCaseTask").off().on("click", function () {
                caseInfo.CaseTask.CreateUpdate();
            });
        },

        List: function () {
            var data = {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                pageNo: $("#PageNo").val(),
                pageSize: $("#PageSize").val()
            };

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseTask/CaseTaskList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $("#dv_List").empty();
                    $("#dv_List").html(response.Data);

                    $(".pull-right.page-box.casetask").cPaging({
                        totalCount: parseInt($("#TotalCount").val()),
                        pageNo: parseInt($("#PageNo").val()),
                        pageSize: parseInt($("#PageSize").val()),
                        callBack: caseInfo.CaseTask.List,
                        callBackArgs: null
                    });

                    var totalCount = parseInt($("#TotalCount").val());

                    caseInfo.ResetSize();

                    if (totalCount > 0) {
                        $("tfoot", "#tblCaseTask").show();
                        $(".simple-grid-none-data-wrap").hide();
                    } else {
                        $("tfoot", "#tblCaseTask").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }

                    caseInfo.CaseTask.BindEvent();
                    caseInfo.CaseTask.BindMenu();

                    $.closeLoading();
                }
            }, true);
        },

        View: function (taskId) {
            var url = AP_ROOT + AP_PAGE_ID + "/TP/Task/TaskDetail?taskId=" + taskId;
            window.open(url);
        },

        Open: function (taskId) {

            if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }

            if ($("#Case_CaseBasicInfo_CustomerId").val() == '') {
                $.showModalMessageBox("请完善案件客户信息.");
                return false;
            }

            var data =
            {
                taskId: taskId
            };

            var url = AP_ROOT + AP_PAGE_ID + "/Legal/CaseTask/CaseTask";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseTaskModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseTaskModal').on('hidden.bs.modal', function () {
                    $("#caseTaskModal").remove();
                });

                var caseTaskOfficer = new AssociateAvailableUser(
                    $("#divAssociateUserList_CaseTask"),
                    $("#CaseTask_Officer"),
                    $("#CaseTask_OfficerName"),
                    null
                );

                /*任务类型*/
                $("#CaseTask_TaskTitle").unbind("click");
                $("#CaseTask_TaskTitle").click(function () {
                    var tirgger = this;
                    var html = $.caseTaskType.getCaseTaskTypeListHtml($("#Case_CaseBasicInfo_CaseTypeId").val());
                    $(".divCaseTaskType").html(html);
                    $("#hidCaseTaskTypeName").val($(tirgger).attr("id"));
                    $("#divCaseTaskTypeList").css({
                        "position": "absolute",
                        "left": $(this).position().left,
                        "top": $(this).position().top + 25,
                        "z-index": 1200
                    }).show();

                    return false;
                });

                $("#divCaseTaskTypeList").find("li").off().on("click", function (e) {
                    var taskTypeName = $(this).find("a").text();
                    var currentSelectedControl = $("#hidCaseTaskTypeName").val();
                    $("#" + currentSelectedControl).val(taskTypeName);
                    $("#divCaseTaskTypeList").hide();
                });
            });
        },

        Close: function () {
            $('#caseTaskModal').modal('hide');
        },

        CreateUpdate: function () {

            if ($("#CaseTask_TaskTitle").val().trim() == '') {
                $.showModalMessageBox("请输入任务标题");
                return false;
            }
            if ($("#CaseTask_Officer").val().trim() == '') {
                $.showModalMessageBox("请输入负责人");
                return false;
            }
            //if ($("#CaseTask_TaskBeginTime").val() == '') {
            //    $.showModalMessageBox("请输入任务开始时间");
            //    return false;
            //}
            if ($("#CaseTask_TaskEndTime").val() == '') {
                $.showModalMessageBox("请输入任务结束时间");
                return false;
            }

            if ($("#CaseTask_TaskEndTime").val() == '') {
                $.showModalMessageBox("请输入任务结束时间");
                return false;
            }

            var data = {};

            data["CaseTask.TaskId"] = $("#CaseTask_TaskId").val();
            data["CaseTask.CaseId"] = $("#Case_CaseBasicInfo_CaseId").val();
            data["CaseTask.CaseNo"] = $("#Case_CaseBasicInfo_CaseNo").val();
            data["CaseTask.CustomerId"] = $("#Case_CaseBasicInfo_CustomerId").val();
            data["CaseTask.CustomerNo"] = $("#Case_CaseBasicInfo_CustomerNo").val();

            data["CaseTask.TaskPriority"] = $("#CaseTask_TaskPriority").val();
            data["CaseTask.TaskTitle"] = $("#CaseTask_TaskTitle").val();
            data["CaseTask.Officer"] = $("#CaseTask_Officer").val();
            //data["CaseTask.TaskBeginTime"] = $("#CaseTask_TaskBeginTime").val();
            data["CaseTask.TaskEndTime"] = $("#CaseTask_TaskEndTime").val();
            data["CaseTask.TaskContent"] = $("#CaseTask_TaskContent").val();

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseTask/CaseTaskCreate", data, function (response) {
                if (response.IsSuccess) {
                    $('#caseTaskModal').modal('hide');
                    //if (caseInfo.CaseTask) {
                    //    caseInfo.CaseTask.List();
                    //}
                    caseInfo.LoadCase($("#Case_CaseBasicInfo_CaseId").val())
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        BindMenu: function () {
            $('#taskgridSection').contextMenu('taskMenu', {
                menuStyle: {
                    width: '152px'
                },

                itemStyle: {
                    width: '150px'
                },

                bindings: {
                    'create': function (t, e) {
                        caseInfo.CaseTask.Open();
                    },

                    'edit': function (t, e) {
                        var caseTaskId = $(e).find("span").text();
                        if (caseTaskId == '') {
                            $.showModalMessageBox("请选择任务.");
                            return false;
                        }
                        caseInfo.CaseTask.Open(caseTaskId);

                        return true;
                    },

                    'refresh': function (t, e) {
                        caseInfo.CaseTask.List();
                    },

                },
                onContextMenu: function (e) {
                    return true;
                },
                onShowMenu: function (e, menu) {
                    if ($(e.target).parents("tr").find("#taskId")) {
                        var caseTaskId = $(e.target).parents("tr").find("#taskId").text();
                        var canModify = $(e.target).parents("tr").find("#canModify").text();

                        if (canModify == 'True') {
                            $('#edit', menu).append("<span style='display:none'>" + caseTaskId + "</span>");
                        } else {
                            $('#edit', menu).remove();
                        }

                    } else {
                        $('#view', menu).remove();
                    }
                    return menu;
                }
            });
        },
    },

    /*案件资费*/
    CaseAssistedFee: {

        /*打开案件资费*/
        Open: function () {
            var data =
            {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                caseNo: $("#Case_CaseBasicInfo_CaseNo").val(),
            };

            if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }

            var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseAssistedFee";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseAssistedFeeModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseAssistedFeeModal').on('hidden.bs.modal', function () {
                    $("#caseAssistedFeeModal").remove();
                });
            });
        },

        /*关闭案件资费*/
        Close: function () {
            $('#caseAssistedFeeModal').modal('hide');
        },

        /*关闭案件资费*/
        ConfirmClose: function () {
            $('#caseAssistedFeeConfirmModal').modal('hide');
        },

        /*资费列表*/
        List: function () {
            var data = {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                pageNo: $("#PageNo").val(),
                pageSize: $("#PageSize").val()
            };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseAssistedFeeList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $("#dv_List").empty();
                    $("#dv_List").html(response.Data);

                    $(".pull-right.page-box.caseAssistedFee").cPaging({
                        totalCount: parseInt($("#TotalCount").val()),
                        pageNo: parseInt($("#PageNo").val()),
                        pageSize: parseInt($("#PageSize").val()),
                        callBack: caseInfo.CaseAssistedFee.List,
                        callBackArgs: null
                    });

                    var totalCount = parseInt($("#TotalCount").val());

                    caseInfo.ResetSize();

                    if (totalCount > 0) {
                        $("tfoot", "#tblCaseAssistedFee").show();
                        $(".simple-grid-none-data-wrap").hide();
                    } else {
                        $("tfoot", "#tblCaseAssistedFee").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }

                    caseInfo.CaseAssistedFee.BindMenu();

                    $.closeLoading();
                }
            }, true);
        },

        BindMenu: function () {
            $('#casegridSection').contextMenu('feeMenu', {
                menuStyle: {
                    width: '152px'
                },

                itemStyle: {
                    width: '150px'
                },
                bindings: {
                    'create': function (t, e) {
                        caseInfo.CaseAssistedFee.Open();
                    },
                    'transact': function (t, e) {
                        var feeId = $(e).find("span").html();
                        caseInfo.CaseAssistedFee.ConfirmOpen(feeId);
                    },
                    'view': function (t, e) {
                        var caseFileId = $(e).find("span").text();
                        if (caseFileId == '') {
                            $.showModalMessageBox("请选择查看的回执文件.");
                            return false;
                        }

                        var caseFileName = $(e).find("lable").text();
                        if (caseFileName == '') {
                            $.showModalMessageBox("无回执文件.");
                            return false;
                        }

                        var caseno = $(e).find("div").text();

                        var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                        var picfiles = new Array('jpg', 'tif', 'pdf');
                        var extName = caseFileName.substring(caseFileName.lastIndexOf('.') + 1, caseFileName.length);

                        if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                            var path = GV_IPR.OfficeOnlineUrl + GV_IPR.IPROnlineUrl + "CaseAssistedFeeFiles/" + caseno + "/" + caseFileName;
                            window.open(path);
                        }
                        else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                            var path = GV_IPR.IPROnlineUrl + "CaseAssistedFeeFiles/" + caseno + "/" + caseFileName;
                            window.open(path);
                        } else {
                            caseInfo.CaseAssistedFee.Download(caseFileId);
                        }

                        return true;
                    },
                    'download': function (t, e) {
                        var feeId = $(e).find("span").text();
                        if (feeId == '') {
                            $.showModalMessageBox("请选择查看的回执文件.");
                            return false;
                        }
                        caseInfo.CaseAssistedFee.Download(feeId);
                        return true;
                    },
                    'delete': function (t, e) {
                        var feeId = $(e).find("span").html();
                        caseInfo.CaseAssistedFee.Delete(feeId);
                    },
                    'refresh': function (t, e) {
                        caseInfo.CaseAssistedFee.List();
                    }
                },
                onContextMenu: function (e) {
                    return true;
                },
                onShowMenu: function (e, menu) {
                    if ($(e.target).parents("tr").find(".assistedFeeId").hasClass("assistedFeeId")) {
                        var feeId = $(e.target).parents("tr").find("#item_AssistedFeeId").val();
                        var caseNo = $(e.target).parents("tr").find("#item_CaseNo").val();
                        var fileName = $(e.target).parents("tr").find("#item_FileName").val();
                        $('#transact,#delete', menu).append("<span style='display:none'>" + feeId + "</span>");
                        $('#view,#download', menu).append("<span style='display:none'>" + feeId + "</span><lable style='display:none'>" + fileName + "</lable><div style='display:none'>" + caseNo + "</div>");
                    } else {
                        $('#transact, #delete', menu).remove();
                        $('#view,#download', menu).remove();
                    }
                    return menu;
                }
            });
        },

        /*资费新建*/
        CreateUpdate: function () {
            if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }
            var data =
            {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                caseNo: $("#Case_CaseBasicInfo_CaseNo").val(),
                caseAssistedFeeTypeId: $("#Case_CaseAssistedFeeType").val()
            };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseAssistedFeeCreate", data, function (response) {
                if (response.IsSuccess) {
                    caseInfo.CaseAssistedFee.List();
                    caseInfo.CaseAssistedFee.Close();
                }
            });
        },

        /*资费确认*/
        ConfirmOpen: function (caseAssistedFeeId) {
            if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }
            var data =
            {
                caseAssistedFeeId: caseAssistedFeeId
            };
            var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseAssistedFeeConfirm";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseAssistedFeeConfirmModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseAssistedFeeConfirmModal').on('hidden.bs.modal', function () {
                    $("#caseAssistedFeeConfirmModal").remove();
                });
            });
        },

        /*资费确认*/
        Transact: function () {

            if ($("#ResponseDate").val() == '') {
                $.showModalMessageBox("请输入办理日期.");
                return false;
            }

            if ($("#flCaseAssistedFeeFile").val() == '') {
                $.showModalMessageBox("请选择回执文件.");
                return false;
            }

            $.openLoading();
            $('#caseAssistedFeeTransact').ajaxSubmit({
                success: function (response) {
                    $.closeLoading();
                    if (response.IsSuccess) {
                        $.showModalMessageBox("保存成功.");
                        $('#caseAssistedFeeConfirm').modal('hide');

                        if (caseInfo.CaseAssistedFee) {
                            caseInfo.CaseAssistedFee.List();
                            caseInfo.CaseLog.List();
                        }
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                }
            });
        },

        Delete: function (caseAssistedFeeId) {
            $.showModalConfirmDialog("确定删除资费？", "caseInfo.CaseAssistedFee.DeleteCallBack", caseAssistedFeeId);
            return true;
        },

        /*资费删除*/
        DeleteCallBack: function (caseAssistedFeeId) {
            var data =
            {
                caseAssistedFeeId: caseAssistedFeeId
            };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseAssistedFeeDelete", data, function (response) {
                if (response.IsSuccess) {
                    caseInfo.CaseAssistedFee.List();
                    caseInfo.CaseLog.List();
                }
            }, true);
        },

        /*查看*/
        Download: function (caseAssistedFeeId) {
            window.open( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseAssistedFeeFileDownload?caseAssistedFeeId=" + caseAssistedFeeId);
            return true;
        },
    },

    CaseRate: {
        /*提成比例*/
        Open: function () {

            var data =
            {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                caseNo: $("#Case_CaseBasicInfo_CaseNo").val(),
            };

            if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }

            var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseRate";
            $.openLoading();

            $("<div></div>").load(url, data, function(result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseRateModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseRateModal').on('hidden.bs.modal', function () {
                    $("#caseRateModal").remove();
                });
            });
        },

        /*资费新建*/
        CreateUpdate: function () {
            if (parseInt($("#Case_CaseBasicInfo_CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }
            var data =
            {
                caseId: $("#Case_CaseBasicInfo_CaseId").val(),
                leadRate: $("#LeadRate").val(),
                copyRate: $("#CopyRate").val()
            };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseRateCreateUpdate", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("提成比例设定成功.");
                    caseInfo.CaseRate.Close();
                } else {
                    $.showModalMessageBox("提成比例设定失败.");
                }
            });
        },

        /*关闭按钮*/
        Close: function () {
            $('#caseRateModal').modal('hide');
        },
    }
};

//document.onkeydown = function (event) {
//    var target, code, tag;
//    if (!event) {
//        event = window.event; //针对ie浏览器  
//        target = event.srcElement;
//        code = event.keyCode;
//        if (code == 13) {
//            tag = target.tagName;
//            if (tag == "TEXTAREA") { return true; }
//            else { return false; }
//        }
//    }
//    else {
//        target = event.target; //针对遵循w3c标准的浏览器，如Firefox  
//        code = event.keyCode;
//        if (code == 13) {
//            tag = target.tagName;
//            if (tag == "INPUT") { return false; }
//            else { return true; }
//        }
//    }
//};

$(document).ready(function () {

    $(window).resize(function() {
        caseInfo.ResetSize();
    });

    $(document).click(function() {
        $("#divCaseFeeTypeList").off().hide();
        $("#divUserList").off().hide();
        $("#divUsers").off().hide();
        $("#divCaseFileTypeList").off().hide();
        $("#divUserListForProcurator").off().hide();
        $("#divAssociateUserList").off().hide();
        $("#divCaseTaskTypeList").off().hide();
        $("#divAssociateApplicantList").off().hide();

        //$("#div_Case_CaseBasicInfo_Deadline").off().hide();
    });

    $(function() {
        //$('.product-nav-list').css("top", "0");
        //$('.product-nav-list').slimScroll({
        //    height: '100%'
        //});

        $('.viewFramework-product-body').slimScroll({
            height: '100%'
        });
    });

    var caseOfficer = new AssociateUser(
        $("#divAssociateUserList"),
        $("#Case_CaseBasicInfo_CaseOfficer"),
        $("#Case_CaseBasicInfo_CaseOfficerName"),
        null
    );

    var caseApplicant = new AssociateApplicant(
        $("#divAssociateApplicantList"),
        $("#Case_CaseBasicInfo_ApplicantInput"),
        $("#Case_CaseBasicInfo_ApplicantInput"),
        $("#Case_CaseBasicInfo_ApplicantInput"),
        null
    );

    var caseProcurator = new AssociateUser(
        $("#divAssociateUserList"),
        $("#Case_CaseBasicInfo_Procurator"),
        $("#Case_CaseBasicInfo_ProcuratorName"),
        null
    );

    var caseCopywriter = new AssociateUser(
        $("#divAssociateUserList"),
        $("#Case_CaseBasicInfo_Copywriter"),
        $("#Case_CaseBasicInfo_CopywriterName"),
        null
    );

    var caseOriginPeople = new AssociateUser(
        $("#divAssociateUserList"),
        $("#Case_CaseBasicInfo_CaseOriginPeople"),
        $("#Case_CaseBasicInfo_CaseOriginPeopleName"),
        null
    );

    $("#Case_CaseBasicInfo_CaseTypeId").change(function () {
        caseInfo.InitCaseType();
    });

    $("#Case_CaseBasicInfo_CasePhaseId").change(function() {
        caseInfo.InitCasePhaseType();
    });

    $("#Case_CaseBasicInfo_HasForeign").change(function() {
        if ($(this).prop("checked") == true) {
            $(".Case_CaseBasic_LawFirm").show();

        } else {
            $(".Case_CaseBasic_LawFirm").hide();
        }
    });

    $("#Case_CaseBasicInfo_HasPriority").change(function() {
        if ($(this).prop("checked") == true && $("#Case_CaseBasicInfo_CaseTypeId").val() == '4') {
            $(".spanTrademarkIdsPriority").show();

        } else {
            $(".spanTrademarkIdsPriority").hide();
        }

        caseInfo.ResetSize();
    });

    $("#btnARCaseFeeList").off().on("click", function () {

        $("#liARCaseFeeList").removeClass("active");
        $("#liAPCaseFeeList").removeClass("active");
        $("#liCaseFileList").removeClass("active");
        $("#liCaseAssistedFeeList").removeClass("active");
        $("#liCaseLogList").removeClass("active");
        $("#liCaseCustomerContactsList").removeClass("active");
        $("#liCaseTaskList").removeClass("active");

        $("#liARCaseFeeList").addClass("active");

        if ($("#PageNo").length) {
            $("#PageNo").val(1);
            $("#PageSize").val(15);
        }

        caseInfo.ARCaseFee.List();
    });

    $("#btnAPCaseFeeList").off().on("click", function () {


        $("#liARCaseFeeList").removeClass("active");
        $("#liAPCaseFeeList").removeClass("active");
        $("#liCaseFileList").removeClass("active");
        $("#liCaseAssistedFeeList").removeClass("active");
        $("#liCaseLogList").removeClass("active");
        $("#liCaseCustomerContactsList").removeClass("active");
        $("#liCaseTaskList").removeClass("active");

        $("#liAPCaseFeeList").addClass("active");

        if ($("#PageNo").length) {
            $("#PageNo").val(1);
            $("#PageSize").val(15);
        }

        caseInfo.APCaseFee.List();
    });

    $("#btnCaseAssistedFeeList").click(function() {


        $("#liARCaseFeeList").removeClass("active");
        $("#liAPCaseFeeList").removeClass("active");
        $("#liCaseFileList").removeClass("active");
        $("#liCaseAssistedFeeList").removeClass("active");
        $("#liCaseLogList").removeClass("active");
        $("#liCaseCustomerContactsList").removeClass("active");
        $("#liCaseTaskList").removeClass("active");

        $("#liCaseAssistedFeeList").addClass("active");

        if ($("#PageNo").length) {
            $("#PageNo").val(1);
            $("#PageSize").val(15);
        }

        caseInfo.CaseAssistedFee.List();
    });

    $("#btnCaseLogList").click(function () {


        $("#liARCaseFeeList").removeClass("active");
        $("#liAPCaseFeeList").removeClass("active");
        $("#liCaseFileList").removeClass("active");
        $("#liCaseAssistedFeeList").removeClass("active");
        $("#liCaseLogList").removeClass("active");
        $("#liCaseCustomerContactsList").removeClass("active");
        $("#liCaseTaskList").removeClass("active");

        $("#liCaseLogList").addClass("active");

        if ($("#PageNo").length) {
            $("#PageNo").val(1);
            $("#PageSize").val(15);
        }

        caseInfo.CaseLog.OperatingLogList();
    });

    $("#btnCaseFileList").off().on("click", function () {

        $("#liARCaseFeeList").removeClass("active");
        $("#liAPCaseFeeList").removeClass("active");
        $("#liCaseFileList").removeClass("active");
        $("#liCaseAssistedFeeList").removeClass("active");
        $("#liCaseLogList").removeClass("active");
        $("#liCaseCustomerContactsList").removeClass("active");
        $("#liCaseTaskList").removeClass("active");

        $("#liCaseFileList").addClass("active");

        if ($("#PageNo").length) {
            $("#PageNo").val(1);
            $("#PageSize").val(15);
        }

        caseInfo.CaseFile.List();

    });

    $("#btnCaseTaskList").off().on("click", function () {

        $("#liARCaseFeeList").removeClass("active");
        $("#liAPCaseFeeList").removeClass("active");
        $("#liCaseFileList").removeClass("active");
        $("#liCaseAssistedFeeList").removeClass("active");
        $("#liCaseLogList").removeClass("active");
        $("#liCaseCustomerContactsList").removeClass("active");
        $("#liCaseTaskList").removeClass("active");
        
        $("#liCaseTaskList").addClass("active");

        if ($("#PageNo").length) {
            $("#PageNo").val(1);
            $("#PageSize").val(15);
        }

        caseInfo.CaseTask.List();

    });

    $("#btnCaseCustomerContactsList").off().on("click", function () {

        $("#liARCaseFeeList").removeClass("active");
        $("#liAPCaseFeeList").removeClass("active");
        $("#liCaseFileList").removeClass("active");
        $("#liCaseAssistedFeeList").removeClass("active");
        $("#liCaseLogList").removeClass("active");
        $("#liCaseCustomerContactsList").removeClass("active");
        $("#liCaseTaskList").removeClass("active");

        $("#liCaseCustomerContactsList").addClass("active");

        if ($("#PageNo").length) {
            $("#PageNo").val(1);
            $("#PageSize").val(15);
        }

        caseInfo.CaseCustomer.CustomerContacts.List();

    });

    //费用信息
    $("#btnCaseFeeInformCreate").off().on("click", function() {
        caseInfo.ARCaseFee.OpenInform();
    });

    $("#btnCaseFeeCreateClose,#btnCaseFeeCreateCancel").off().on("click", function () {
        caseInfo.ARCaseFee.Objects.Close();
    });

    $("#btnCaseFeeCreateUpdate").off().on("click", function () {
        caseInfo.ARCaseFee.Objects.CreateUpdate();
    });

    $("#btnCaseFeeInformYearlyCancel,#btnCaseFeeInformYearlyClose").off().on("click", function() {
        caseInfo.ARCaseFee.CloseYearlyInform();
    });
    $("#btnCaseFeeInformYearly").off().on("click", function() {
        caseInfo.ARCaseFee.CreateUpdateYearlyInform();
    });

    $("#btnCaseFeeConfirmCancel,#btnCaseFeeConfirmClose").off().on("click", function() {
        caseInfo.ARCaseFee.CloseConfirm();
    });
    $("#btnCaseFeeConfirm").off().on("click", function() {
        caseInfo.ARCaseFee.CreateUpdateConfirm();
    });

    $("#btnCaseFeeInvoiceConfirmCancel,#btnCaseFeeInvoiceConfirmClose").off().on("click", function() {
        caseInfo.ARCaseFee.Invoice.Close();
    });
    $("#btnCaseFeeInvoiceConfirm,#btnCaseFeeInvoiceConfirmCreate").off().on("click", function () {
        caseInfo.ARCaseFee.Invoice.Confirm();
    });

    /*合同文件*/
    $("#btnContractFileListCancel,#btnContractFileListClose").off().on("click", function () {
        contract.Contract.Files.Close();
    });

    //上传文件
    $("#btnCaseFileCreate").off().on("click", function() {
        caseInfo.CaseFile.Open();
    });
    $("#btnCaseFileUploadingClose,#btnCaseFileUploadingCancel").off().on("click", function() {
        caseInfo.CaseFile.Close();
    });
    $("#btnCaseFileUploading").off().on("click", function() {
        caseInfo.CaseFile.CreateUpdate();
    });
    $("#btnCaseFileToWord").off().on("click", function() {
        caseInfo.CaseFile.ToWord();
    });
    $("#lnkCaseFileTypeId").off().on("click", function() {
        var tirgger = $("#CaseFileTypeName");
        if ($("#IsTransformedFile").val() == 'true') {
            $(".divCaseFileTypeList").html($.caseFileType.getCaseTransformedFileTypeListHtml($("#CaseTypeId").val()));
        } else {
            $(".divCaseFileTypeList").html($.caseFileType.getCaseFileTypeListHtml($("#CaseTypeId").val()));
        }
        $("#divCaseFileTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left + 15,
            "top": $(tirgger).offsetParent().position().top + 32,
            "z-index": 1200
        }).toggle();

        $("#hidCaseFileTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFileTypeId").val($("#CaseFileTypeId").attr("id")); //Id

        return false;
    });
    $("#lnkCaseFileTypeIdForOffice").off().on("click", function () {
        var tirgger = $("#CaseFileTypeName");
        $(".divCaseFileTypeList").html($.caseFileType.getCaseOfficeFileTypeListHtml($("#CaseTypeId").val()));
        $("#divCaseFileTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left + 15,
            "top": $(tirgger).offsetParent().position().top + 32,
            "z-index": 1200
        }).toggle();

        $("#hidCaseFileTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFileTypeId").val($("#CaseFileTypeId").attr("id")); //Id

        return false;
    });

    $("#lnkCaseFileTypeIdForNonOffice").off().on("click", function () {
        var tirgger = $("#CaseFileTypeName");
        $(".divCaseFileTypeList").html($.caseFileType.getCaseNonOfficeFileTypeListHtml($("#CaseTypeId").val()));
        $("#divCaseFileTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left + 15,
            "top": $(tirgger).offsetParent().position().top + 32,
            "z-index": 1200
        }).toggle();

        $("#hidCaseFileTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFileTypeId").val($("#CaseFileTypeId").attr("id")); //Id

        return false;
    });

    $("#lnkCaseFileTypeIdForTransformed").off().on("click", function () {
        var tirgger = $("#CaseFileTypeName");
        $(".divCaseFileTypeList").html($.caseFileType.getCaseTransformedFileTypeListHtml($("#CaseTypeId").val()));
        $("#divCaseFileTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left + 15,
            "top": $(tirgger).offsetParent().position().top + 32,
            "z-index": 1200
        }).toggle();

        $("#hidCaseFileTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFileTypeId").val($("#CaseFileTypeId").attr("id")); //Id

        return false;
    });

    $("#divCaseFileTypeList").find("li").off().on("click", function() {
        var caseFileTypeId = $(this).find("a").attr("id");
        var caseFileTypeName = $(this).find("a").text();
        var caseFileTypeNameText = $(this).find("a").attr("text");
        var currentSelectedControl = $("#hidCaseFileTypeName").val();
        var currentSelectedIdControl = $("#hidCaseFileTypeId").val();
        $("#" + currentSelectedControl).val(caseFileTypeName);
        $("#" + currentSelectedIdControl).val(caseFileTypeId);

        var hedgingFileTypeId = $(this).find("a").attr("hedgingFileTypeId");
        var hedgingFeeTypeId = $(this).find("a").attr("hedgingFeeTypeId");

        caseInfo.CaseFile.ProcessFileTypeSelectedCallBack(caseFileTypeId, caseFileTypeNameText, hedgingFileTypeId, hedgingFeeTypeId);

        $("#divCaseFileTypeList").hide();
    });

    //资助费用
    $("#btnCaseAssistedFeeCreate").off().on("click", function() {
        caseInfo.CaseAssistedFee.Open();
    });
    $("#btnCaseAssistedFeeClose,#btnCaseAssistedFeeCancel").off().on("click", function() {
        caseInfo.CaseAssistedFee.Close();
    });
    $("#btnCaseAssistedFee").off().on("click", function() {
        caseInfo.CaseAssistedFee.CreateUpdate();
    });
    $("#btnCaseAssistedFeeConfirm").off().on("click", function() {
        caseInfo.CaseAssistedFee.Transact();
    });
    $("#btnCaseAssistedFeeConfirmCancel,#btnCaseAssistedFeeConfirmClose").off().on("click", function() {
        caseInfo.CaseAssistedFee.ConfirmClose();
    });

    //新增日志
    $("#btnCaseLogCreate").off().on("click", function () {
        caseInfo.CaseLog.Open();
    });

    $("#btnCaseLogClose,#btnCaseLogCancel").off().on("click", function() {
        caseInfo.CaseLog.Close();
    });
    $("#btnCaseLog").off().on("click", function() {
        caseInfo.CaseLog.CreateUpdate();
    });

    $("#btnCaseLogDelete").off().on("click", function () {
        caseInfo.CaseLog.Delete();
    });

    //新增事件提醒
    $("#btnCaseEventCreate").off().on("click", function () {
        caseInfo.CaseEvent.Open();
    });

    $("#btnCaseEventNotInCreate").click(function () {
        caseInfo.CaseEventNotIn.Open();
    });

    $("#btnCaseEventClose,#btnCaseEventCancel").off().on("click", function() {
        caseInfo.CaseEvent.Close();
    });
    $("#btnCaseEvent").off().on("click", function() {
        caseInfo.CaseEvent.CreateUpdate();
    });

    $("#btnCaseEventDelete").off().on("click", function() {
        caseInfo.CaseEvent.Delete();
    });

    $("#btnCaseEventNotInClose,#btnCaseEventNotInCancel").off().on("click", function () {
        caseInfo.CaseEventNotIn.Close();
    });
    $("#btnCaseEventNotIn").off().on("click", function () {
        caseInfo.CaseEventNotIn.CreateUpdate();
    });

    //客户
    $("#btnCustomerSearch").off().on("click", function () {
        //if ( $.trim($("#SearchCondition_CustomerName").val()) == '' ) {
        //    $.showModalMessageBox("请输入客户名称.");
        //    return false;
        //}
        caseInfo.CaseCustomer.SelectedList();
    });

    $("#SearchCondition_CustomerName").off().on("keypress", function (e) {
        if (e.which == 13) {
            if ($("#SearchCondition_CustomerName").val() == '')
                return false;
            caseInfo.CaseCustomer.SelectedList();
            return false;
        }
    });

    $("#btnCustomerSelected").off().on("click", function () {
        caseInfo.CaseCustomer.Open();
    });

    $("#btnCustomerClose,#btnCustomerCancle").off().on("click", function() {
        caseInfo.CaseCustomer.Close();
    });

    $("#btnCustomerConfirm").off().on("click", function() {
        caseInfo.CaseCustomer.CreateUpdate();
    });

    $("#chkCustomerAll").off().on("click", function() {
        caseInfo.CaseCustomer.Selected(this);
    });

    $("input[name='chkFirstApplicantId']").off().on("click", function () {
        caseInfo.CaseCustomer.ApplicantSelected(this);
    });


    /*客户*/
    $("#Case_CaseBasicInfo_ApplicantSelect").unbind("click");
    $("#Case_CaseBasicInfo_ApplicantSelect").bind("click", function () {
        caseInfo.CaseCustomer.Open();
    });

    $("#Case_CaseBasicInfo_LawFirmName").unbind("click");
    $("#Case_CaseBasicInfo_LawFirmName").bind("click", function() {
        caseInfo.CaseLawFirm.Open();
    });

    /*客户联系人*/
    $("#btnCustomerContactsCancle,#btnCustomerContactsClose").off().on("click", function () {
        caseInfo.CaseCustomer.CustomerContacts.Close();
    });

    $("#btnCustomerContactsCreate").off().on("click", function () {
        caseInfo.CaseCustomer.CustomerContacts.Open();
    });

    $("#btnCustomerContactsSelected").off().on("click", function () {
        caseInfo.CaseCustomer.CustomerContacts.CreateUpdate();
    });

     /*案件任务*/  
    $("#btnCaseTaskCreate").off().on("click", function () {
        caseInfo.CaseTask.Open();
    });

    $("#btnCaseTaskClose,#btnCaseTaskCancel").off().on("click", function () {
        caseInfo.CaseTask.Close();
    });

    $("#btnCaseTask").off().on("click", function () {
        caseInfo.CaseTask.CreateUpdate();
    });
    
    //律所
    $("#btnLawFirmSelected").off().on("click", function () {
        caseInfo.CaseLawFirm.Open();
    });

    $("#btnLawFirmClose,#btnLawFirmCancel").off().on("click", function() {
        caseInfo.CaseLawFirm.Close();
    });

    $("#btnLawFirmConfirm").off().on("click", function() {
        caseInfo.CaseLawFirm.CreateUpdate();
    });

    $("#chkLawFirmAll").off().on("click", function() {
        caseInfo.CaseLawFirm.Selected(this);
    });

    $("#btnCaseCreateUpdate").off().on("click", function () {
        caseInfo.CreateUpdate(false);
    });

    $("#Case_CaseBasicInfo_ProcuratorName").off().on("click", function() {
        $("#hidUserId").val("Case_CaseBasicInfo_Procurator");
        $("#hidUserName").val("Case_CaseBasicInfo_ProcuratorName");
        $("#divUserListForProcurator").css({
            "position": "absolute",
            "left": $("#Case_CaseBasicInfo_ProcuratorName").position().left + 0,
            "top": $("#Case_CaseBasicInfo_ProcuratorName").position().top + 32,
            "z-index": 1200
        }).toggle();
        return false;
    });

    //$("#Case_CaseBasicInfo_CopywriterName").off().on("click", function() {
    //    $("#hidUserId").val("Case_CaseBasicInfo_Copywriter");
    //    $("#hidUserName").val("Case_CaseBasicInfo_CopywriterName");
    //    $("#divUserListForDepartment1").off().css({
    //        "position": "absolute",
    //        "left": $("#Case_CaseBasicInfo_CopywriterName").position().left + 1,
    //        "top": $("#Case_CaseBasicInfo_CopywriterName").position().top + 28,
    //        "z-index": 1200
    //    }).toggle();
    //    return false;
    //});

    //$("#Case_CaseBasicInfo_CaseOfficerName").off().on("click", function() {
    //    $("#hidUserId").val("Case_CaseBasicInfo_CaseOfficer");
    //    $("#hidUserName").val("Case_CaseBasicInfo_CaseOfficerName");
    //    $("#divUserList").off().css({
    //        "position": "absolute",
    //        "left": $("#Case_CaseBasicInfo_CaseOfficerName").position().left+1,
    //        "top": $("#Case_CaseBasicInfo_CaseOfficerName").position().top + 28,
    //        "z-index": 1200
    //    }).show();
    //    return false;
    //});

    $("#Case_Deadline").off().on("click", function() {
        $("#Cfg_Case_CaseBasicInfo_Deadline").html(caseInfo.getDeadlineHtml());
        var date = new Date();

        $("#Cfg_Case_CaseBasicInfo_Deadline_Date").val(date.getFullYear() + "-" + (date.getMonth() + 1) + "-" + date.getDate());

        $("#hidControlId").val("Case_Deadline");
        $("#Cfg_Case_CaseBasicInfo_Deadline").off().css({
            "position": "absolute",
            "left": $("#Case_Deadline").offsetParent().position().left + 15,
            "top": $("#Case_Deadline").offsetParent().position().top + 80,
            "z-index": 1200
        }).show();
        return false;
    });

    $("#Case_CaseBasicInfo_Deadline").off().on("click", function() {
        $("#div_Case_CaseBasicInfo_Deadline").html(caseInfo.getDeadlineHtml());
        var date = new Date();

        $("#Cfg_Case_CaseBasicInfo_Deadline_Date").val(date.getFullYear() + "-" + (date.getMonth() + 1) + "-" + date.getDate());

        $("#hidControlId").val("Case_CaseBasicInfo_Deadline");
        $("#div_Case_CaseBasicInfo_Deadline").off().css({
            "position": "absolute",
            "left": $("#Case_CaseBasicInfo_Deadline").position().left + 2,
            "top": $("#Case_CaseBasicInfo_Deadline").position().top + 28,
            "z-index": 1200
        }).show();

        return false;
    });

    //$("#Case_CaseOfficerName").off().on("click", function() {
    //    $("#hidUserId").val("Case_CaseOfficer");
    //    $("#hidUserName").val("Case_CaseOfficerName");
    //    $("#divUsers").off().css({
    //        "position": "absolute",
    //        "left": $("#Case_CaseOfficerName").offsetParent().position().left + 15,
    //        "top": $("#Case_CaseOfficerName").offsetParent().position().top + 32,
    //        "z-index": 1200
    //    }).show();
    //    return false;
    //});

    //$("#Case_CaseBasicInfo_CaseOriginPeopleName").off().on("click", function() {
    //    $("#hidUserId").val("Case_CaseBasicInfo_CaseOriginPeople");
    //    $("#hidUserName").val("Case_CaseBasicInfo_CaseOriginPeopleName");
    //    $("#divUserList").css({
    //        "position": "absolute",
    //        "left": $("#Case_CaseBasicInfo_CaseOriginPeopleName").position().left + 1,
    //        "top": $("#Case_CaseBasicInfo_CaseOriginPeopleName").position().top + 28,
    //        "z-index": 1200
    //    }).toggle();
    //    return false;
    //});

    $("#DefaultCaseFee_RequestUserName").off().on("click", function () {
        $("#hidUserId").val("DefaultCaseFee_RequestUser");
        $("#hidUserName").val("DefaultCaseFee_RequestUserName");

        $("#divUsers").css({
            "position": "absolute",
            "left": $("#DefaultCaseFee_RequestUserName").offsetParent().position().left + 15,
            "top": $("#DefaultCaseFee_RequestUserName").offsetParent().position().top + 32,
            "z-index": 1200
        }).toggle();

        return false;
    });

    $("#DefaultCaseFee_PayerName").off().on("click", function () {
        $("#hidUserId").val("DefaultCaseFee_Payer");
        $("#hidUserName").val("DefaultCaseFee_PayerName");

        $("#divUsers").css({
            "position": "absolute",
            "left": $("#DefaultCaseFee_PayerName").offsetParent().position().left + 15,
            "top": $("#DefaultCaseFee_PayerName").offsetParent().position().top + 32,
            "z-index": 1200
        }).toggle();

        return false;
    });

    $("#PayerName").off().on("click", function () {
        $("#hidUserId").val("Payer");
        $("#hidUserName").val("PayerName");

        $("#divUsers").css({
            "position": "absolute",
            "left": $("#PayerName").offsetParent().position().left + 15,
            "top": $("#PayerName").offsetParent().position().top + 32,
            "z-index": 1200
        }).toggle();

        return false;
    });

    $("#DefaultCaseFee_CaseFeeTypeName").off().on("click", function() {
        var tirgger = this;
        var caseTypeId = $("#CaseTypeId").val();
        $(".divCaseFeeTypeList").html($.caseFeeType.getCaseFeeTypeListHtml(caseTypeId));
        $("#divCaseFeeTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left + 15,
            "top": $(tirgger).offsetParent().position().top + 32,
            "z-index": 1200
        }).toggle();

        $("#hidCaseFeeTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFeeTypeId").val("DefaultCaseFee_CaseFeeTypeId"); //Id
        return false;
    });

    $(".CaseFee_CaseFeeTypeName").off().on("click", function() {
        var tirgger = this;
        var caseTypeId = $("#CaseTypeId").val();
        $(".divCaseFeeTypeList").html($.caseFeeType.getCaseFeeTypeListHtml(caseTypeId));

        $("#divCaseFeeTypeList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 5,
            "top": $(tirgger).position().top + 138,
            "z-index": 1200
        }).toggle();

        $("#hidCaseFeeTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFeeTypeId").val($(this).parent().find(":hidden").attr("id")); //Id
        return false;
    });

    $("#divCaseFeeTypeList").find("li").off().on("click", function() {

        var caseFeeTypeId = $(this).find("a").attr("id");
        var caseFeeTypeName = $(this).find("a").text();
        var currentSelectedControlId = $("#hidCaseFeeTypeId").val();
        var currentSelectedControlName = $("#hidCaseFeeTypeName").val();
        $("#" + currentSelectedControlId).val(caseFeeTypeId);
        $("#" + currentSelectedControlName).val(caseFeeTypeName);

        if ($("#DefaultCaseFee_CaseFeeTypeId").val() == "3") {
            //年费
            $(".yearly").show();
        } else {
            $(".yearly").hide();
        }

        $($('#tblCaseFeeItemList>tbody>tr:first>td')[0]).html("<span class='spanCaseFeeTypeName'>" + $("#DefaultCaseFee_CaseFeeTypeName").val() + "</span>");

        $("#divCaseFeeTypeList").hide();
    });

    $("#divUsers").find("li").off().on("click", function() {
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        var currentSelectedControl = $("#hidUserName").val();
        var currentSelectedIdControl = $("#hidUserId").val();
        $("#" + currentSelectedControl).val(userName);
        $("#" + currentSelectedIdControl).val(userId);
        $("#divUsers").hide();
    });

    $("#divUserList").find("li").off().on("click", function(e) {
        var currentSelectedControl = $("#hidUserName").val();
        var currentSelectedIdControl = $("#hidUserId").val();
        if ($(this).attr("id") == 'btnClear') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        $("#" + currentSelectedControl).val(userName);
        $("#" + currentSelectedIdControl).val(userId);
        $("#divUserList").hide();
        return false;
    });

    $("#divUserListForProcurator").find("li").off().on("click", function (e) {
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

        $("#divUserListForProcurator").find("input:checkbox").each(function () {
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

    $("#btnCaseCreateNew").off().on("click", function (){
 
        //$.showModalMessageBox("确定重新创建案件?");

        if ($("#Case_CaseBasicInfo_CaseNo").val() != '') {
            $.showModalConfirmDialog("确定重新创建案件？", "caseInfo.CreateCompletedNew", null, false, true);
            return true;
        } else {
            caseInfo.CreateCompletedNew();
            return true;
        }
    });

    $("#btnCaseRenewal").off().on("click", function () {
        caseInfo.Edit();
    });

    $("#btnCaseSubmit").off().on("click", function () {
        caseInfo.CreateUpdate(true);
    });

    $("#btnFeeInformConfirmItemAdd").off().on("click", function() {
        caseInfo.ARCaseFee.CaseFeeTypeItem.Add();
    });

    $(".btn_clear").off().on("click", function() {
        caseInfo.ARCaseFee.CaseFeeTypeItem.Clear(this);
    });

    $(".btn_remove").off().on("click", function() {
        caseInfo.ARCaseFee.CaseFeeTypeItem.Remove(this);
    });

    $("#flInvoiceFile").off().on("change", function() {
        $("#txtInvoiceFilePath").val($("#flInvoiceFile").val());
    });

    $("#flCaseAssistedFeeFile").off().on("change", function() {
        $("#txtCaseAssistedFeeFilePath").val($("#flCaseAssistedFeeFile").val());
    });

    $("#flCaseFile").off().on("change", function() {
        $("#txtCaseFilePath").val($("#flCaseFile").val());
    });

    $("#btnCaseDeadLineClose,#btnCaseDeadLineCancel").off().on("click", function() {
        caseInfo.Close();
    });

    $("#btnCaseDeadLine").off().on("click", function() {
        caseInfo.CreateUpdateDeadline();
    });

    $("#btnCfgDeadlineCreateUpdate").off().on("click", function() {

        if ($("#Cfg_Case_CaseBasicInfo_Deadline_Date").val() == '') {
            $("#Cfg_Case_CaseBasicInfo_Deadline_Date").val(new Date().Format("yyyy-MM-dd"));
        };

        var currentSelectedIdControl = $("#hidControlId").val();

        var deadline = new Date($("#Cfg_Case_CaseBasicInfo_Deadline_Date").val());
        var deadlineyear = $("#Cfg_Case_CaseBasicInfo_Deadline_Year").val();
        var deadlinemonth = $("#Cfg_Case_CaseBasicInfo_Deadline_Month").val();
        var deadlineday = $("#Cfg_Case_CaseBasicInfo_Deadline_Day").val();

        deadline = deadline.addYears(deadlineyear == '' ? 0 : parseInt(deadlineyear));
        deadline = deadline.addMonths(deadlinemonth == '' ? 0 : parseInt(deadlinemonth));
        deadline = deadline.addDays(deadlineday == '' ? 0 : parseInt(deadlineday));

        $("#" + currentSelectedIdControl).val(deadline.Format("yyyy-MM-dd"));

        $("#div_Case_CaseBasicInfo_Deadline").empty();
        $("#Cfg_Case_CaseBasicInfo_Deadline").empty();

        $("#div_Case_CaseBasicInfo_Deadline").hide();
        $("#Cfg_Case_CaseBasicInfo_Deadline").hide();

        return false;
    });

    $("#btnCfgDeadlineCreateUpdateCancel").off().on("click", function() {
        $("#div_Case_CaseBasicInfo_Deadline").empty();
        $("#Cfg_Case_CaseBasicInfo_Deadline").empty();
        $("#div_Case_CaseBasicInfo_Deadline").hide();
        $("#Cfg_Case_CaseBasicInfo_Deadline").hide();
    });

    //提成
    $("#btnCaseRateSet").off().on("click", function () {
        caseInfo.CaseRate.Open();
    });

    $("#btnCaseRateClose,#btnCaseRateCancel").off().on("click", function () {
        caseInfo.CaseRate.Close();
    });

    $("#btnCaseRateCreate").off().on("click", function () {
        caseInfo.CaseRate.CreateUpdate();
    });

    //预付款申请
    $("#btnPaymentApply").off().on("click", function () {
        caseInfo.APCaseFee.PaymentApply.Apply();
    });

    $("#btnPaymentApplyClose,#btnPaymentApplyCancel").off().on("click", function () {
        caseInfo.APCaseFee.PaymentApply.Close();
    });

    $("#btnCaseFeeApplicationAuditListCancel,#btnCaseFeeApplicationAuditListClose").off().on("click", function () {
        caseInfo.APCaseFee.PaymentApply.Audit.Close();
    });

    $("#item_CaseOfficeFeeTypeId").off().on("change", function () {
        caseInfo.ARCaseFee.Objects.ObjectItem.InitCaseOfficeFeeAnnualYear(this);
    });

    $(".customerremove").off().on("click", function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled')
        {
            return false;
        }
        caseInfo.CaseCustomer.Remove(this);
    });

    $(".btn_applicant_add").off().on("click", function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        caseInfo.CaseCustomer.Open();
    });

    caseInfo.Init();
});