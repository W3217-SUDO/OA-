var caseInfo = {
    View: function (caseId, caseNo) {

        var search = {};

        search.CaseId = 0;
        search.PageId = 1;
        search.PageNo = 1;
        search.PageSize = 100;
        search.PageName = "案件查看";
        search.Keyword = caseNo;

        var url = AP_ROOT + AP_PAGE_ID + "/IPR/Case/CreateUpdate?typeId=1&caseId=" + caseId + "&k=" + escape(JSON.stringify(search));

        window.open(url);
    },
    Open: function (e) {

        if ($("#Contract_ContractBasicInfo_CustomerId").val() == '') {
            $.showModalMessageBox("请选择客户.");
            return false;
        }

        $(e).parents("tr").attr("selected", "true");

        var data =
        {
            customerId: $("#Contract_ContractBasicInfo_CustomerId").val(),
        };

        var url = AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseTreeView";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);
            $('#treeviewModal').modal({ backdrop: 'static', keyboard: false });
            $('#treeviewModal').on('hidden.bs.modal', function () {
                $("#treeviewModal").remove();
            });

            caseInfo.BulidCaseTreeView();
        });
    },
    Close: function () {
        $('#treeviewModal').modal('hide');
    },
    BulidCaseTreeView: function () {
        var data1 = {
            customerId: $("#Contract_ContractBasicInfo_CustomerId").val(),
            Keyword: $("#SearchKeyword").val()
        };

        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseListByCustomerId", data1, function (response) {
            if (response.IsSuccess) {
                $('#treeview').treeview({
                    data: response.Data, // 数据源
                    showCheckbox: false, //是否显示复选框
                    highlightSelected: true, //是否高亮选中
                    //nodeIcon: 'glyphicon glyphicon-user',    //节点上的图标
                    nodeIcon: '',
                    emptyIcon: 'icon expand-icon glyphicon glyphicon-minus', //没有子节点的节点图标
                    multiSelect: false, //多选
                    onNodeChecked: function (event, data) {
                        if (data.parentId != null) {
                            $('#treeview').treeview('checkNode', [data.parentId, { silent: true }]);
                        }
                        if (data.nodes != null) {
                            $.each(data.nodes, function (i, c) {
                                $('#treeview').treeview('checkNode', [c.nodeId, { silent: true }]);
                            });
                        }
                    },
                    onNodeUnchecked: function (event, data) {
                        if (data.nodes != null) {
                            $.each(data.nodes, function (i, c) {
                                $('#treeview').treeview('uncheckNode', [c.nodeId, { silent: true }]);
                            });
                        }
                    },
                    onNodeSelected: function (event, data) {

                        if (data.parentId != null) {
                            $('#treeview').treeview('checkNode', [data.parentId, { silent: true }]);
                        }
                        if (data.nodes != null) {
                            $.each(data.nodes, function (i, c) {
                                $('#treeview').treeview('checkNode', [c.nodeId, { silent: true }]);
                            });
                        }
                    }
                });
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },
    Selected: function () {
        var nodes = $('#treeview').treeview('getSelected');
        var data = {};
        if (nodes != null && nodes.length > 0) {
            if (nodes[0].nodeType == 'A') {
                data["CaseId"] = nodes[0].nodeOriginalId;
                data["CaseNo"] = nodes[0].nodeCode;

            } else {
                $.showModalMessageBox("请选择案件.");
                return false;
            }
        }

        $("#tblContractObjectList tbody tr").each(function (i, e) {
            if (typeof ($(e).attr("selected")) != "undefined") {
                $(e).find("#item_CaseNo").val(data["CaseNo"]);
                $.case.getCaseBasicByCaseNo($(e).find("#item_CaseNo"), $(e).find("#item_CaseNo").val(), contract.Draft.Objects.ObjectItem.getCaseBasicCallBack);
                event.stopPropagation();
            }
            $(e).removeAttr("selected");
            caseInfo.Close();
        });
    },
    QuickCase: {
        Open: function (e) {

            if ($("#Contract_ContractBasicInfo_CustomerId").val() == '') {
                $.showModalMessageBox("请选择客户.");
                return false;
            }

            $("input[name='item_CaseNo']").each(
                function () {
                    $(this).removeAttr("selected");
                }
            );

            $(e).parents("tr").find("#item_CaseNo").attr("selected", "true");

            var data =
            {
                customerId: $("#Contract_ContractBasicInfo_CustomerId").val(),
            };

            var url = AP_ROOT + AP_PAGE_ID + "/IPR/Case/QuickCreate";
            $.openLoading();

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

            //$("#tblContractObjectList tbody tr").each(function (i, e) {
            //    $(e).removeAttr("selected");
            //});
            $("input[name='item_CaseNo']").each(
                function () {
                    $(this).removeAttr("selected");
                }
            );

            $('#quickCreateModel').modal('hide');


        },
        CreateUpdate: function () {
            try {
                var data = {};
                //第一申请人
                data["Case.CaseBasicInfo.FirstApplicantId"] = $("#Contract_ContractBasicInfo_CustomerId").val();

                data["Case.CaseBasicInfo.CaseTypeId"] = $("#CaseInfo_CaseBasicInfo_CaseTypeId").val();
                data["Case.CaseBasicInfo.Customer"] = $("#Contract_ContractBasicInfo_CustomerId").val();

                data["isSubmit"] = true;

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseQuickCreateUpdate", data, function (response) {
                    if (response.IsSuccess) {
                        $("#tblContractObjectList tbody tr").each(function (i, e) {
                            if (typeof ($(e).find("#item_CaseNo").attr("selected")) != "undefined") {
                                contract.Draft.Objects.ObjectItem.getCaseBasicCallBack(response, $(e).find("#item_CaseNo"));
                                //event.stopPropagation();
                            }
                        });

                        caseInfo.QuickCase.Close();

                    } else if (response.IsRedirect) {
                        window.location = AP_ROOT + 'Home/Index';
                    } else {
                        $.showModalMessageBox(response.Message);

                    }
                });
            } catch (e) {
                alert(e);
            }
        },
    },
    Case: {
        BindEvent: function () {
            var caseOfficer = new AssociateUser(
               $("#divAssociateUserList"),
               $("#Case_CaseBasicInfo_CaseOfficer"),
               $("#Case_CaseBasicInfo_CaseOfficerName"),
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

            $("#Case_CaseBasicInfo_CaseTypeId").die().live("change", function () {
                caseInfo.Case.InitCaseType();
            });

            $("#Case_CaseBasicInfo_CasePhaseId").die().live("change", function () {
                caseInfo.Case.InitCasePhaseType();
            });

            $("#Case_CaseBasicInfo_HasForeign").die().live("change", function () {
                if ($(this).attr("checked") == "checked") {
                    $(".Case_CaseBasic_LawFirm").show();

                } else {
                    $(".Case_CaseBasic_LawFirm").hide();
                }
            });

            $("#Case_CaseBasicInfo_HasPriority").die().live("change", function () {
                if ($(this).attr("checked") == "checked" && $("#Case_CaseBasicInfo_CaseTypeId").val() == '4') {
                    $(".spanTrademarkIdsPriority").show();

                } else {
                    $(".spanTrademarkIdsPriority").hide();
                }
            });

            //$("#Case_CaseBasicInfo_ProcuratorName").die().live("click", function () {
            //    $("#hidUserId").val("Case_CaseBasicInfo_Procurator");
            //    $("#hidUserName").val("Case_CaseBasicInfo_ProcuratorName");
            //    $("#divUserList").css({
            //        "position": "absolute",
            //        "left": $("#Case_CaseBasicInfo_ProcuratorName").position().left + 1,
            //        "top": $("#Case_CaseBasicInfo_ProcuratorName").position().top + 28,
            //        "z-index": 1200
            //    }).toggle();
            //    return false;
            //});

            //$("#Case_CaseBasicInfo_CopywriterName").die().live("click", function () {
            //    $("#hidUserId").val("Case_CaseBasicInfo_Copywriter");
            //    $("#hidUserName").val("Case_CaseBasicInfo_CopywriterName");
            //    $("#divUserList").die().css({
            //        "position": "absolute",
            //        "left": $("#Case_CaseBasicInfo_CopywriterName").position().left + 1,
            //        "top": $("#Case_CaseBasicInfo_CopywriterName").position().top + 28,
            //        "z-index": 1200
            //    }).toggle();
            //    return false;
            //});

            //$("#Case_CaseBasicInfo_CaseOfficerName").die().live("click", function () {
            //    $("#hidUserId").val("Case_CaseBasicInfo_CaseOfficer");
            //    $("#hidUserName").val("Case_CaseBasicInfo_CaseOfficerName");
            //    $("#divUserList").die().css({
            //        "position": "absolute",
            //        "left": $("#Case_CaseBasicInfo_CaseOfficerName").position().left + 1,
            //        "top": $("#Case_CaseBasicInfo_CaseOfficerName").position().top + 28,
            //        "z-index": 1200
            //    }).show();
            //    return false;
            //});


            //$("#Case_CaseOfficerName").die().live("click", function () {
            //    $("#hidUserId").val("Case_CaseOfficer");
            //    $("#hidUserName").val("Case_CaseOfficerName");
            //    $("#divUsers").die().css({
            //        "position": "absolute",
            //        "left": $("#Case_CaseOfficerName").offsetParent().position().left + 15,
            //        "top": $("#Case_CaseOfficerName").offsetParent().position().top + 32,
            //        "z-index": 1200
            //    }).show();
            //    return false;
            //});

            //$("#Case_CaseBasicInfo_CaseOriginPeopleName").die().live("click", function () {
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

            $("#Case_Deadline").die().live("click", function () {
                $("#Cfg_Case_CaseBasicInfo_Deadline").html(caseInfo.getDeadlineHtml());
                var date = new Date();

                $("#Cfg_Case_CaseBasicInfo_Deadline_Date").val(date.getFullYear() + "-" + (date.getMonth() + 1) + "-" + date.getDate());

                $("#hidControlId").val("Case_Deadline");
                $("#Cfg_Case_CaseBasicInfo_Deadline").die().css({
                    "position": "absolute",
                    "left": $("#Case_Deadline").offsetParent().position().left + 15,
                    "top": $("#Case_Deadline").offsetParent().position().top + 80,
                    "z-index": 1200
                }).show();
                return false;
            });

            $("#Case_CaseBasicInfo_Deadline").die().live("click", function () {
                $("#div_Case_CaseBasicInfo_Deadline").html(caseInfo.getDeadlineHtml());
                var date = new Date();

                $("#Cfg_Case_CaseBasicInfo_Deadline_Date").val(date.getFullYear() + "-" + (date.getMonth() + 1) + "-" + date.getDate());

                $("#hidControlId").val("Case_CaseBasicInfo_Deadline");
                $("#div_Case_CaseBasicInfo_Deadline").die().css({
                    "position": "absolute",
                    "left": $("#Case_CaseBasicInfo_Deadline").position().left + 8,
                    "top": $("#Case_CaseBasicInfo_Deadline").position().top + 40,
                    "z-index": 1200
                }).show();

                return false;
            });


            $("#btnCaseCancle,#btnCaseClose").die().live("click", function () {
                caseInfo.Case.Close();
            });

            $("#btnCaseCreateUpdate").die().live("click", function () {
                
                caseInfo.Case.CreateUpdate();
            });
        },
        Init: function () {
            caseInfo.Case.InitCaseType();
        },
        Edit: function () {
            $(":input", "#caseForm").each(function () {
                $(this).removeAttr("disabled");
            });

            if (parseInt($("#CaseId").val()) > 0) {
                $("#Case_CaseBasicInfo_CaseTypeId").attr("disabled", "disabled");
            }

            $("#Case_CaseBasicInfo_HasPriority").removeAttr("disabled");
            $("#Case_CaseBasicInfo_HasForeign").removeAttr("disabled");

            $("#btnCaseCreateNew").removeAttr("disabled");
            $("#btnCaseCreateUpdate").removeAttr("disabled");
            $("#btnCaseRenewal").attr("disabled", "disabled");

            $("#ulCustomer>li>div>i").each(function () {
                $(this).attr("class", "unlink fa fa-times");
            });
        },
        InitCaseBasic: function () {
            var data = { caseId: $("#CaseId").val() };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/Case/GetCaseBasic", data, function (response) {
                if (response.IsSuccess && response.Data && response.Data != "") {
                    $("#Case_CaseBasicInfo_CasePhaseId").val(response.Data.CaseBasicInfo.CasePhaseId);
                    $("#Case_CaseBasicInfo_CaseRequestDate").val(response.Data.CaseBasicInfo.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(response.Data.CaseBasicInfo.CaseRequestDate)));
                    $("#Case_CaseBasicInfo_CaseRequestNo").val(response.Data.CaseBasicInfo.CaseRequestNo);
                    $("#Case_CaseBasicInfo_AuthorizationDate").val(response.Data.CaseBasicInfo.AuthorizationDate == null ? '' : getDate(convertJsonDateToJSDate(response.Data.CaseBasicInfo.AuthorizationDate)));
                    $("#Case_CaseBasicInfo_FirstInstanceDate").val(response.Data.CaseBasicInfo.FirstInstanceDate == null ? '' : getDate(convertJsonDateToJSDate(response.Data.CaseBasicInfo.FirstInstanceDate)));
                    $("#Case_CaseBasicInfo_Deadline").val(response.Data.CaseBasicInfo.Deadline == null ? '' : getDate(convertJsonDateToJSDate(response.Data.CaseBasicInfo.Deadline)));
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
                if ($("#Case_CaseBasicInfo_HasPriority").attr("checked") == "checked") {
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

            if ($("#CaseId").val() != '' && parseInt($("#CaseId").val()) > 0) {
                //$("#Case_CaseBasicInfo_CaseTypeId")
                $("#Case_CaseBasicInfo_CaseTypeId").attr("disabled", "disabled");
            }

        },
        InitCasePhaseType: function () {
            var casePhaseTypeId = $("#Case_CaseBasicInfo_CasePhaseId").val();
            if (casePhaseTypeId == "1" && $("#Case_CaseBasicInfo_CaseRegisterDate").val() == '') {
                //立案待处理
                var today = new Date();
                $("#Case_CaseBasicInfo_CaseRegisterDate").val(today.getFullYear() + "-" + (today.getMonth() + 1) + "-" + today.getDate());
            }
        },

        Open: function (e) {

            if ($("#Contract_ContractBasicInfo_CustomerId").val() == '') {
                $.showModalMessageBox("请选择客户.");
                return false;
            }

            $("input[name='item_CaseNo']").each(
                function () {
                    $(this).removeAttr("selected");
                }
            );

            $(e).parents("tr").find("#item_CaseNo").attr("selected", "true");

            var data =
            {
                customerId: $("#Contract_ContractBasicInfo_CustomerId").val(),
            };

            var url = AP_ROOT + AP_PAGE_ID + "/IPR/Case/Create";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseModal').on('hidden.bs.modal', function () {
                    $("#caseModal").remove();
                });

                caseInfo.Case.InitCaseType();
                caseInfo.Case.BindEvent();
            });
        },
        Close: function () {

            //$("#tblContractObjectList tbody tr").each(function (i, e) {
            //    $(e).removeAttr("selected");
            //});
            $("input[name='item_CaseNo']").each(
                function () {
                    $(this).removeAttr("selected");
                }
            );

            $('#caseModal').modal('hide');

        },
        CreateUpdate: function () {
            try {
                var data = {};

                if ($("#Case_CaseBasicInfo_CaseTypeId").val() == 1
                    || $("#Case_CaseBasicInfo_CaseTypeId").val() == 2
                    || $("#Case_CaseBasicInfo_CaseTypeId").val() == 3) {
                    if ($("#Case_CaseBasicInfo_CaseName").val() == '') {
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

                    if ($("#Case_CaseBasicInfo_CaseInventor").val() == '') {
                        $.showModalMessageBox("请输入发明人.");
                        return false;
                    }
                }

                if ($("#Case_CaseBasicInfo_CaseTypeId").val() == 4) {
                    if ($("#Case_CaseBasicInfo_CaseName").val() == '') {
                        $.showModalMessageBox("请输入商标名称.");
                        return false;
                    }

                    if ($("#Case_CaseBasicInfo_TradeTypeId").val() == '') {
                        $.showModalMessageBox("请选择商标类型.");
                        return false;
                    }

                    if ($("#Case_CaseBasicInfo_TrademarkIds").val() == '') {
                        $.showModalMessageBox("请输入商标类别.");
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

                    if ($("#Case_CaseBasicInfo_TradeProductService").val() == '') {
                        $.showModalMessageBox("请输入商品服务.");
                        return false;
                    }
                }

                //第一申请人
                data["Case.CaseBasicInfo.FirstApplicantId"] = $("#Contract_ContractBasicInfo_CustomerId").val();

                data["Case.CaseBasicInfo.CaseTypeId"] = $("#Case_CaseBasicInfo_CaseTypeId").val();
                data["Case.CaseBasicInfo.Customer"] = $("#Contract_ContractBasicInfo_CustomerId").val();

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
                data["Case.CaseBasicInfo.CaseInventor"] = $("#Case_CaseBasicInfo_CaseInventor").val().trim();
                data["Case.CaseBasicInfo.TrademarkIds"] = $("#Case_CaseBasicInfo_TrademarkIds").val();
                data["Case.CaseBasicInfo.CaseDesigner"] = $("#Case_CaseBasicInfo_CaseDesigner").val();
                data["Case.CaseBasicInfo.CaseSubmitter"] = $("#Case_CaseBasicInfo_CaseSubmitter").val();
                data["Case.CaseBasicInfo.CaseSubmitDate"] = $("#Case_CaseBasicInfo_CaseSubmitDate").val();
                data["Case.CaseBasicInfo.CaseOfficer"] = $("#Case_CaseBasicInfo_CaseOfficer").val();
                data["Case.CaseBasicInfo.Deadline"] = $("#Case_CaseBasicInfo_Deadline").val();
                data["Case.CaseBasicInfo.LawFirm"] = $("#Case_CaseBasicInfo_LawFirm").val();
                data["Case.CaseBasicInfo.ReliefNo"] = $("#Case_CaseBasicInfo_ReliefNo").val();

                data["Case.CaseBasicInfo.HasPriority"] = $("#Case_CaseBasicInfo_HasPriority").attr("checked") == "checked";
                data["Case.CaseBasicInfo.HasForeign"] = $("#Case_CaseBasicInfo_HasForeign").attr("checked") == "checked";
                data["Case.CaseBasicInfo.HasRelief"] = $("#Case_CaseBasicInfo_HasRelief").attr("checked") == "checked";
                data["Case.CaseBasicInfo.HasAdvanced"] = $("#Case_CaseBasicInfo_HasAdvanced").attr("checked") == "checked";
                data["Case.CaseBasicInfo.HasRequestView"] = $("#Case_CaseBasicInfo_HasRequestView").attr("checked") == "checked";
                data["Case.CaseBasicInfo.HasPrivateInventor"] = $("#Case_CaseBasicInfo_HasPrivateInventor").attr("checked") == "checked";
                data["Case.CaseBasicInfo.HasIU"] = $("#Case_CaseBasicInfo_HasIU").attr("checked") == "checked";

                data["Case.CaseBasicInfo.RefCaseNo"] = $("#Case_CaseBasicInfo_RefCaseNo").val();
                data["Case.CaseBasicInfo.FirstInstanceDate"] = $("#Case_CaseBasicInfo_FirstInstanceDate").val();
                data["Case.CaseBasicInfo.TradeTypeId"] = $("#Case_CaseBasicInfo_TradeTypeId").val();
                data["Case.CaseBasicInfo.TradeProductService"] = $("#Case_CaseBasicInfo_TradeProductService").val();

                data["Case.CaseBasicInfo.HasTradeColorProtected"] = $("#Case_CaseBasicInfo_HasTradeColorProtected").attr("checked") == "checked";
                data["Case.CaseBasicInfo.HasTradeVoiceProtected"] = $("#Case_CaseBasicInfo_HasTradeVoiceProtected").attr("checked") == "checked";
                data["Case.CaseBasicInfo.HasTrade3DProtected"] = $("#Case_CaseBasicInfo_HasTrade3DProtected").attr("checked") == "checked";
                data["Case.CaseBasicInfo.HasTradeFirstRequest"] = $("#Case_CaseBasicInfo_HasTradeFirstRequest").attr("checked") == "checked";
                data["Case.CaseBasicInfo.HasTradeBaseOnExhibition"] = $("#Case_CaseBasicInfo_HasTradeBaseOnExhibition").attr("checked") == "checked";
                data["Case.CaseBasicInfo.HasTradeReplenish"] = $("#Case_CaseBasicInfo_HasTradeReplenish").attr("checked") == "checked";

                data["isSubmit"] = true;
                data["orgCaseId"] = $("#OrgCase_CaseBasicInfo_CaseId").val();

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseQuickCreateUpdate", data, function (response) {
                    if (response.IsSuccess) {
                        $("#tblContractObjectList tbody tr").each(function (i, e) {
                            if (typeof ($(e).find("#item_CaseNo").attr("selected")) != "undefined") {
                                contract.Draft.Objects.ObjectItem.getCaseBasicCallBack(response, $(e).find("#item_CaseNo"));
                                //event.stopPropagation();
                            }
                        });

                        caseInfo.Case.Close();

                    } else if (response.IsRedirect) {
                        window.location = AP_ROOT + 'Home/Index';
                    } else {
                        $.showModalMessageBox(response.Message);

                    }
                });
            } catch (e) {
                alert(e);
            }
        },
    },
    CaseCopy: {
        Open: function () {

            if ($("#Contract_ContractBasicInfo_CustomerId").val() == '') {
                $.showModalMessageBox("请选择客户.");
                return false;
            }

            var data =
            {
                customerId: $("#Contract_ContractBasicInfo_CustomerId").val(),
            };

            var url = AP_ROOT + AP_PAGE_ID + "/IPR/Case/QuickCopy";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#quickCopyModel').modal({ backdrop: 'static', keyboard: false });
                $('#quickCopyModel').on('hidden.bs.modal', function () {
                    $("#quickCopyModel").remove();
                });
            });
        },

        Copy: function () {
            var data = { caseNo: $("#OrgCaseInfo_CaseBasicInfo_CaseNo").val() };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/Case/GetCaseBasicByCaseNo", data, function (response) {
                if (response.IsSuccess) {
                    if (response.Data.CaseBasicInfo.FirstApplicantId != $("#Contract_ContractBasicInfo_CustomerId").val()) {
                        $("#casecopymessage").text("案件客户不一致,请重新输入.");
                        return false;
                    }

                    $("#OrgCase_CaseBasicInfo_CaseId").val(response.Data.CaseBasicInfo.CaseId);
                    $("#Case_CaseBasicInfo_CaseTypeId").val(response.Data.CaseBasicInfo.CaseTypeId);
                    caseInfo.Case.InitCaseType();
                    $("#Case_CaseBasicInfo_CasePhaseId").val(response.Data.CaseBasicInfo.CasePhaseId);
                    $("#Case_CaseBasicInfo_Procurator").val(response.Data.CaseBasicInfo.Procurator);
                    $("#Case_CaseBasicInfo_ProcuratorName").val(response.Data.CaseBasicInfo.ProcuratorName);
                    $("#Case_CaseBasicInfo_Copywriter").val(response.Data.CaseBasicInfo.Copywriter);
                    $("#Case_CaseBasicInfo_CopywriterName").val(response.Data.CaseBasicInfo.CopywriterName);
                    $("#Case_CaseBasicInfo_CardNo").val(response.Data.CaseBasicInfo.CardNo);
                    $("#Case_CaseBasicInfo_CaseInventor").val(response.Data.CaseBasicInfo.CaseInventor);
                    $("#Case_CaseBasicInfo_TrademarkIds").val(response.Data.CaseBasicInfo.TrademarkIds);
                    $("#Case_CaseBasicInfo_TradeTypeId").val(response.Data.CaseBasicInfo.TradeTypeId);
                    $("#Case_CaseBasicInfo_TradeProductService").val(response.Data.CaseBasicInfo.TradeProductService);


                    if (response.Data.CaseBasicInfo.HasPriority) {
                        $("#Case_CaseBasicInfo_HasPriority").attr("checked", "checked");
                    }
                    else {
                        $("#Case_CaseBasicInfo_HasPriority").removeAttr("checked");
                    }

                    if (response.Data.CaseBasicInfo.HasTradeFirstRequest) {
                        $("#Case_CaseBasicInfo_HasTradeFirstRequest").attr("checked", "checked");
                    }
                    else {
                        $("#Case_CaseBasicInfo_HasTradeFirstRequest").removeAttr("checked");
                    }

                    if (response.Data.CaseBasicInfo.HasTradeBaseOnExhibition) {
                        $("#Case_CaseBasicInfo_HasTradeBaseOnExhibition").attr("checked", "checked");
                    }
                    else {
                        $("#Case_CaseBasicInfo_HasTradeBaseOnExhibition").removeAttr("checked");
                    }

                    if (response.Data.CaseBasicInfo.HasTradeReplenish) {
                        $("#Case_CaseBasicInfo_HasTradeReplenish").attr("checked", "checked");
                    }
                    else {
                        $("#Case_CaseBasicInfo_HasTradeReplenish").removeAttr("checked");
                    }

                    if (response.Data.CaseBasicInfo.HasForeign) {
                        $("#Case_CaseBasicInfo_HasForeign").attr("checked", "checked");
                    }
                    else {
                        $("#Case_CaseBasicInfo_HasForeign").removeAttr("checked");
                    }

                    if (response.Data.CaseBasicInfo.HasRelief) {
                        $("#Case_CaseBasicInfo_HasRelief").attr("checked", "checked");
                    }
                    else {
                        $("#Case_CaseBasicInfo_HasRelief").removeAttr("checked");
                    }

                    if (response.Data.CaseBasicInfo.HasAdvanced) {
                        $("#Case_CaseBasicInfo_HasAdvanced").attr("checked", "checked");
                    }
                    else {
                        $("#Case_CaseBasicInfo_HasAdvanced").removeAttr("checked");
                    }

                    if (response.Data.CaseBasicInfo.HasRequestView) {
                        $("#Case_CaseBasicInfo_HasRequestView").attr("checked", "checked");
                    }
                    else {
                        $("#Case_CaseBasicInfo_HasRequestView").removeAttr("checked");
                    }
                    if (response.Data.CaseBasicInfo.HasPrivateInventor) {
                        $("#Case_CaseBasicInfo_HasPrivateInventor").attr("checked", "checked");
                    }
                    else {
                        $("#Case_CaseBasicInfo_HasPrivateInventor").removeAttr("checked");
                    }

                    if (response.Data.CaseBasicInfo.HasIU) {
                        $("#Case_CaseBasicInfo_HasIU").attr("checked", "checked");
                    }
                    else {
                        $("#Case_CaseBasicInfo_HasIU").removeAttr("checked");
                    }

                    if (response.Data.CaseBasicInfo.HasTradeColorProtected) {
                        $("#Case_CaseBasicInfo_HasTradeColorProtected").attr("checked", "checked");
                    }
                    else {
                        $("#Case_CaseBasicInfo_HasTradeColorProtected").removeAttr("checked");
                    }

                    if (response.Data.CaseBasicInfo.HasTradeVoiceProtected) {
                        $("#Case_CaseBasicInfo_HasTradeVoiceProtected").attr("checked", "checked");
                    }
                    else {
                        $("#Case_CaseBasicInfo_HasTradeVoiceProtected").removeAttr("checked");
                    }

                    if (response.Data.CaseBasicInfo.HasTrade3DProtected) {
                        $("#Case_CaseBasicInfo_HasTrade3DProtected").attr("checked", "checked");
                    }
                    else {
                        $("#Case_CaseBasicInfo_HasTrade3DProtected").removeAttr("checked");
                    }

                    caseInfo.CaseCopy.Close();
                }
                else {
                    $("#casecopymessage").text("未能找到输入的案号，请确认案件有效.");
                }
            });

        },

        Close: function () {
            $('#quickCopyModel').modal('hide');
        },
    }
}
 