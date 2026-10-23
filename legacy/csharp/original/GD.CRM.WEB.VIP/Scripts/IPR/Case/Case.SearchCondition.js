var searchCondition = {
    Init: function () {
        $(":input", "#caseSearchForm").each(function () {
            $(this).attr("disabled", "disabled");
            $(this).removeAttr("checked");
            $(this).val('');
        });

        $("#Search_HasCaseBasicSearchCondition").on("click", function () {
            var checked = $(this).attr("checked");
            $("input[type='checkbox']", "#casebasicsearchcondition").each(function () {
                if (checked == 'checked') {
                    if (!$(this).hasClass("notin")) {
                        $(this).removeAttr("disabled");
                    }
                    if ($(this).hasClass("has")) {
                        $(this).on("click", function () {
                            var itemChecked = $(this).attr("checked");

                            $(":input", $($(this).parent()).parent()).each(function () {
                                if (itemChecked == 'checked')
                                    $(this).removeAttr("disabled");
                                else
                                    $(this).attr("disabled", "disabled");
                            });

                            $(this).removeAttr("disabled");
                        });
                    }

                    $("#Search_IsUnionCaseBasicSearchCondition").attr("checked", 'checked');
                    $("#Search_IsNotUnionCaseBasicSearchCondition").removeAttr("checked");

                } else {
                    $(this).attr("disabled", "disabled");
                }
            });
            $(this).removeAttr("disabled");
        });

        $("#Search_HasCaseAssistedFeeSearchCondition").on("click", function () {
            var checked = $(this).attr("checked");
            $("input[type='checkbox']", "#caseassistedfeesearchcondition").each(function () {
                if (checked == 'checked') {
                    if (!$(this).hasClass("notin")) {
                        $(this).removeAttr("disabled");
                    }

                    if ($(this).hasClass("has")) {
                        $(this).on("click", function () {
                            var itemChecked = $(this).attr("checked");
                            $(":input", $($(this).parent()).parent()).each(function () {
                                if (itemChecked == 'checked')
                                    $(this).removeAttr("disabled");
                                else
                                    $(this).attr("disabled", "disabled");
                            })

                            $(this).removeAttr("disabled");
                        });
                    }

                    $("#Search_IsUnionCaseAssistedFeeSearchCondition").attr("checked", 'checked');
                    $("#Search_IsNotUnionCaseAssistedFeeSearchCondition").removeAttr("checked");

                } else {
                    $(this).attr("disabled", "disabled");
                }
            });

            $(this).removeAttr("disabled");
        });
        $("#Search_HasCaseFeeSearchCondition").on("click", function () {
            var checked = $(this).attr("checked");
            $("input[type='checkbox']", "#casefeesearchcondition").each(function () {
                if (checked == 'checked') {
                    if (!$(this).hasClass("notin")) {
                        $(this).removeAttr("disabled");
                    }

                    if ($(this).hasClass("has")) {
                        $(this).on("click", function () {
                            var itemChecked = $(this).attr("checked");
                            $(":input", $($(this).parent()).parent()).each(function () {
                                if (itemChecked == 'checked')
                                    $(this).removeAttr("disabled");
                                else
                                    $(this).attr("disabled", "disabled");
                            });

                            $(this).removeAttr("disabled");
                        });
                    }

                    $("#Search_IsUnionCaseFeeSearchCondition").attr("checked", 'checked');
                    $("#Search_IsNotUnionCaseFeeSearchCondition").removeAttr("checked");

                } else {
                    $(this).attr("disabled", "disabled");
                }
            });

            $(this).removeAttr("disabled");
        });
        $("#Search_HasCaseFileSearchCondition").on("click", function () {
            var checked = $(this).attr("checked");
            $("input[type='checkbox']", "#casefilesearchcondition").each(function () {
                if (checked == 'checked') {
                    if (!$(this).hasClass("notin")) {
                        $(this).removeAttr("disabled");
                    }

                    if ($(this).hasClass("has")) {
                        $(this).on("click", function () {
                            var itemChecked = $(this).attr("checked");
                            $(":input", $($(this).parent()).parent()).each(function () {
                                if (itemChecked == 'checked')
                                    $(this).removeAttr("disabled");
                                else
                                    $(this).attr("disabled", "disabled");
                            });

                            $(this).removeAttr("disabled");
                        });
                    }

                    $("#Search_IsUnionCaseFileSearchCondition").attr("checked", 'checked');
                    $("#Search_IsNotUnionCaseFileSearchCondition").removeAttr("checked");

                } else {
                    $(this).attr("disabled", "disabled");
                }
            });

            $(this).removeAttr("disabled");
        });

        $("#btnSearchCondition").off().on("click", function () {
            searchCondition.Search();
        });

        $("#btnSearchConditionCreateUpdate").off().on("click", function () {
            searchCondition.CreateUpdate();
        });

        $("#btnSearchConditionCancel,#btnSearchConditionClose").off().on("click", function () {
            $('.caseadvancedsearch').closeWin();
        });

        $("#Search_CaseBasicSearchCondition_CaseRequestNoName").off().on("click", function () {
            var tirgger = this;
            $("#hidUserId").val('Search_CaseBasicSearchCondition_CaseRequestNo');
            $("#hidUserName").val($(tirgger).attr("id"));
            $("#divcaseconditionusers").css({
                "position": "absolute",
                 "left": $(tirgger).position().left + 52,
                "top": $(tirgger).position().top + 166
            }).toggle();
            return false;
        });

        $("#Search_CaseBasicSearchCondition_ProcuratorName").off().on("click", function () {
            var tirgger = this;
            $("#hidUserId").val('Search_CaseBasicSearchCondition_Procurator');
            $("#hidUserName").val($(tirgger).attr("id"));
            $("#divcaseconditionusers").css({
                "position": "absolute",
                 "left": $(tirgger).position().left + 52,
                "top": $(tirgger).position().top + 166
            }).toggle();
            return false;
        });

        $("#Search_CaseBasicSearchCondition_CaseOfficerName").off().on("click", function () {
            var tirgger = this;
            $("#hidUserId").val('Search_CaseBasicSearchCondition_CaseOfficer');
            $("#hidUserName").val($(tirgger).attr("id"));
            $("#divcaseconditionusers").css({
                "position": "absolute",
                 "left": $(tirgger).position().left + 52,
                "top": $(tirgger).position().top + 166
            }).toggle();
            return false;
        });
        
        $("#Search_CaseBasicSearchCondition_CaseOriginPeopleName").off().on("click", function () {
            var tirgger = this;
            $("#hidUserId").val('Search_CaseBasicSearchCondition_CaseOriginPeople');
            $("#hidUserName").val($(tirgger).attr("id"));
            $("#divcaseconditionusers").css({
                "position": "absolute",
                 "left": $(tirgger).position().left + 52,
                "top": $(tirgger).position().top + 166
            }).toggle();
            return false;
        });

        $("#Search_CaseBasicSearchCondition_CopywriterName").off().on("click", function () {
            var tirgger = this;
            $("#hidUserId").val('Search_CaseBasicSearchCondition_Copywriter');
            $("#hidUserName").val($(tirgger).attr("id"));
            $("#divcaseconditionusers").css({
                "position": "absolute",
                "left": $(tirgger).position().left + 52,
                "top": $(tirgger).position().top + 166
            }).toggle();
            return false;
        });


        $("#Search_CaseAssistedFeeSearchCondition_ResponseUserName").off().on("click", function () {
            var tirgger = this;
            $("#hidUserId").val('Search_CaseAssistedFeeSearchCondition_ResponseUser');
            $("#hidUserName").val($(tirgger).attr("id"));
            $("#divcaseconditionusers").css({
                "position": "absolute",
                 "left": $(tirgger).position().left + 52,
                "top": $(tirgger).position().top + 166
            }).toggle();
            return false;
        });

        $("#Search_CaseFeeSearchCondition_ResponseUserName").off().on("click", function () {
            var tirgger = this;
            $("#hidUserId").val('Search_CaseFeeSearchCondition_ResponseUser');
            $("#hidUserName").val($(tirgger).attr("id"));
            $("#divcaseconditionusers").css({
                "position": "absolute",
                 "left": $(tirgger).position().left + 52,
                "top": $(tirgger).position().top + 166
            }).toggle();
            return false;
        });

        $("#Search_CaseFileSearchCondition_UploadingUserName").off().on("click", function () {
            var tirgger = this;
            $("#hidUserId").val('Search_CaseFileSearchCondition_UploadingUser');
            $("#hidUserName").val($(tirgger).attr("id"));
            $("#divcaseconditionusers").css({
                "position": "absolute",
                 "left": $(tirgger).position().left + 52,
                "top": $(tirgger).position().top + 166
            }).toggle();
            return false;
        });

        $("#Search_CaseBasicSearchCondition_CaseType").off().on("click", function () {
            var tirgger = this;
            var html = $.caseType.getCaseTypeCheckBoxListHtml();
            $(".divcaseconditioncasetypes").html(html);
            $("#hidCaseTypeId").val("hid_" + $(tirgger).attr("id"));
            $("#hidCaseTypeName").val($(tirgger).attr("id"));
            $("#divCaseTypeCheckBoxList").css({
                "position": "absolute",
                 "left": $(tirgger).position().left + 52,
                "top": $(tirgger).position().top + 166
            }).toggle();

            return false;
        });

        $("#Search_CaseBasicSearchCondition_CasePhase").off().on("click", function () {
            var tirgger = this;
            var html = $.casePhase.getCasePhaseCheckBoxListHtml();
            $(".divcaseconditioncasephases").html(html);
            $("#hidCasePhaseId").val("hid_" + $(tirgger).attr("id"));
            $("#hidCasePhaseName").val($(tirgger).attr("id"));
            $("#divCasePhaseCheckBoxList").css({
                "position": "absolute",
                "left": $(tirgger).position().left + 52,
                "top": $(tirgger).position().top + 166
            }).toggle();

            return false;
        });

        $("#Search_CaseFileSearchCondition_CaseFileType").off().on("click", function () {
            var tirgger = this;
            var html = $.caseFileType.getCaseFileTypeCheckBoxListHtml();
            $(".divcaseconditioncasefiletypes").html(html);
            $("#hidCaseFileTypeId").val("hid_" + $(tirgger).attr("id"));
            $("#hidCaseFileTypeName").val($(tirgger).attr("id"));
            $("#divCaseFileTypeCheckBoxList").css({
                "position": "absolute",
                "left": $(tirgger).position().left + 52,
                "top": $(tirgger).position().top + 166
            }).toggle();

            return false;
        });

        $("#Search_CaseFeeSearchCondition_CaseFeeType").off().on("click", function () {
            var tirgger = this;
            var html = $.caseFeeType.getCaseFeeTypeCheckBoxListHtml();
            $(".divcaseconditioncasefeetypes").html(html);
            $("#hidCaseFeeTypeId").val("hid_" + $(tirgger).attr("id"));
            $("#hidCaseFeeTypeName").val($(tirgger).attr("id"));
            $("#divCaseFeeTypeCheckBoxList").css({
                "position": "absolute",
                "left": $(tirgger).position().left + 52,
                "top": $(tirgger).position().top + 166
            }).toggle();

            return false;
        });
      
        $("#Search_CaseFeeSearchCondition_BillStatus").off().on("click", function () {
            var tirgger = this;
            var html = $.caseFeeInvoiceStatus.getCaseFeeInvoiceStatusCheckBoxListHtml();
            $(".divcaseconditioncasefeebillstatus").html(html);
            $("#hidCaseFeeInvoiceStatusId").val("hid_" + $(tirgger).attr("id"));
            $("#hidCaseFeeInvoiceStatusName").val($(tirgger).attr("id"));
            $("#divCaseFeeInvoiceStatusCheckBoxList").css({
                "position": "absolute",
                "left": $(tirgger).position().left + 52,
                "top": $(tirgger).position().top + 166
            }).toggle();

            return false;
        });

        $("#divCaseFeeInvoiceStatusCheckBoxList").find("li").off().on("click", function (e) {

            if ($(e.target).is("lable")) {
                e.stopPropagation();
                return false;
            }

            var currentSelectedControl = $("#hidCaseFeeInvoiceStatusName").val();
            var currentSelectedIdControl = $("#hidCaseFeeInvoiceStatusId").val();

            if ($(this).attr("id") == 'btnAllUnSelected') {
                $("#" + currentSelectedControl).val('');
                $("#" + currentSelectedIdControl).val('');
                return false;
            }
            else if ($(this).attr("id") == 'btnAllSelected') {
                $("#" + currentSelectedControl).val('');
                $("#" + currentSelectedIdControl).val('');
                return false;
            }

            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedControl).val('');

            var caseFeeInvoiceStatusNames = '';
            var caseFeeInvoiceStatusIds = '';

            $("#divCaseFeeInvoiceStatusCheckBoxList").find("input:checkbox").each(function () {
                if ($(this).attr("checked") == 'checked') {
                    caseFeeInvoiceStatusNames += $(this).attr("casefeebillstatusname") + ",";
                    caseFeeInvoiceStatusIds += $(this).attr("casefeebillstatusid") + ",";
                }
            });

            $("#" + currentSelectedControl).val(caseFeeInvoiceStatusNames.substring(0, caseFeeInvoiceStatusNames.length - 1));
            $("#" + currentSelectedIdControl).val(caseFeeInvoiceStatusIds.substring(0, caseFeeInvoiceStatusIds.length - 1));

            e.stopPropagation();

            return true;
        });

        $("#divCaseFeeTypeCheckBoxList").find("li").off().on("click", function (e) {

            if ($(e.target).is("lable")) {
                e.stopPropagation();
                return false;
            }

            var currentSelectedControl = $("#hidCaseFeeTypeName").val();
            var currentSelectedIdControl = $("#hidCaseFeeTypeId").val();

            if ($(this).attr("id") == 'btnAllUnSelected') {
                $("#" + currentSelectedControl).val('');
                $("#" + currentSelectedIdControl).val('');
                return false;
            }
            else if ($(this).attr("id") == 'btnAllSelected') {
                $("#" + currentSelectedControl).val('');
                $("#" + currentSelectedIdControl).val('');
                return false;
            }

            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedControl).val('');

            var caseFeeTypeNames = '';
            var caseFeeTypeIds = '';

            $("#divCaseFeeTypeCheckBoxList").find("input:checkbox").each(function () {
                if ($(this).attr("checked") == 'checked') {
                    caseFeeTypeNames += $(this).attr("caseFeeTypename") + ",";
                    caseFeeTypeIds += $(this).attr("caseFeeTypeid") + ",";
                }
            });

            $("#" + currentSelectedControl).val(caseFeeTypeNames.substring(0, caseFeeTypeNames.length - 1));
            $("#" + currentSelectedIdControl).val(caseFeeTypeIds.substring(0, caseFeeTypeIds.length - 1));

            e.stopPropagation();

            return true;
        });

        $("#divCaseFileTypeCheckBoxList").find("li").off().on("click", function (e) {

            if ($(e.target).is("lable")) {
                e.stopPropagation();
                return false;
            }

            var currentSelectedControl = $("#hidCaseFileTypeName").val();
            var currentSelectedIdControl = $("#hidCaseFileTypeId").val();

            if ($(this).attr("id") == 'btnAllUnSelected') {
                $("#" + currentSelectedControl).val('');
                $("#" + currentSelectedIdControl).val('');
                return false;
            }
            else if ($(this).attr("id") == 'btnAllSelected') {
                $("#" + currentSelectedControl).val('');
                $("#" + currentSelectedIdControl).val('');
                return false;
            }

            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedControl).val('');

            var caseFileTypeNames = '';
            var caseFileTypeIds = '';

            $("#divCaseFileTypeCheckBoxList").find("input:checkbox").each(function () {
                if ($(this).attr("checked") == 'checked') {
                    caseFileTypeNames += $(this).attr("caseFileTypename") + ",";
                    caseFileTypeIds += $(this).attr("caseFileTypeid") + ",";
                }
            });

            $("#" + currentSelectedControl).val(caseFileTypeNames.substring(0, caseFileTypeNames.length - 1));
            $("#" + currentSelectedIdControl).val(caseFileTypeIds.substring(0, caseFileTypeIds.length - 1));

            e.stopPropagation();

            return true;
        });

        $("#divCasePhaseCheckBoxList").find("li").off().on("click", function (e) {

            if ($(e.target).is("lable")) {
                e.stopPropagation();
                return false;
            }

            var currentSelectedControl = $("#hidCasePhaseName").val();
            var currentSelectedIdControl = $("#hidCasePhaseId").val();

            if ($(this).attr("id") == 'btnAllUnSelected') {
                $("#" + currentSelectedControl).val('');
                $("#" + currentSelectedIdControl).val('');
                return false;
            }
            else if ($(this).attr("id") == 'btnAllSelected') {
                $("#" + currentSelectedControl).val('');
                $("#" + currentSelectedIdControl).val('');
                return false;
            }

            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedControl).val('');

            var casePhaseNames = '';
            var casePhaseIds = '';

            $("#divCasePhaseCheckBoxList").find("input:checkbox").each(function () {
                if ($(this).attr("checked") == 'checked') {
                    casePhaseNames += $(this).attr("casephasename") + ",";
                    casePhaseIds += $(this).attr("casephaseid") + ",";
                }
            });

            $("#" + currentSelectedControl).val(casePhaseNames.substring(0, casePhaseNames.length - 1));
            $("#" + currentSelectedIdControl).val(casePhaseIds.substring(0, casePhaseIds.length - 1));

            e.stopPropagation();

            return true;
        });
        
        $("#divCaseTypeCheckBoxList").find("li").off().on("click", function (e) {

            if ($(e.target).is("lable")) {
                e.stopPropagation();
                return false;
            }

            var currentSelectedControl = $("#hidCaseTypeName").val();
            var currentSelectedIdControl = $("#hidCaseTypeId").val();

            if ($(this).attr("id") == 'btnAllUnSelected') {
                $("#" + currentSelectedControl).val('');
                $("#" + currentSelectedIdControl).val('');
                return false;
            }
            else if ($(this).attr("id") == 'btnAllSelected') {
                $("#" + currentSelectedControl).val('');
                $("#" + currentSelectedIdControl).val('');
                return false;
            }

            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedControl).val('');

            var caseTypeNames = '';
            var caseTypeIds = '';

            $("#divCaseTypeCheckBoxList").find("input:checkbox").each(function () {
                if ($(this).attr("checked") == 'checked') {
                    caseTypeNames += $(this).attr("casetypename") + ",";
                    caseTypeIds += $(this).attr("casetypeid") + ",";
                }
            });

            $("#" + currentSelectedControl).val(caseTypeNames.substring(0, caseTypeNames.length - 1));
            $("#" + currentSelectedIdControl).val(caseTypeIds.substring(0, caseTypeIds.length - 1));

            e.stopPropagation();

            return true;
        });

        $("#divcaseconditionusers").find("li").off().on("click", function () {
            var userId = $(this).find("a").attr("name");
            var userName = $(this).find("a").text();
            var currentSelectedControl = $("#hidUserName").val();
            var currentSelectedIdControl = $("#hidUserId").val();
            $("#" + currentSelectedControl).val(userName);
            $("#" + currentSelectedIdControl).val(userId);
            $("#divcaseconditionusers").hide();
        });

        $("#Search_HasCaseBasicSearchCondition").removeAttr("disabled");
        $("#Search_HasCaseAssistedFeeSearchCondition").removeAttr("disabled");
        $("#Search_HasCaseFeeSearchCondition").removeAttr("disabled");
        $("#Search_HasCaseFileSearchCondition").removeAttr("disabled");

    },
    InitCaseSearchCondition: function (caseSearch) {

        if (typeof (caseSearch) != "undefined" && caseSearch != null) {

            $("#Search_Name").val(caseSearch.Name);
            $("#Search_SearchConditionId").val(caseSearch.SearchConditionId);

            if (caseSearch.HasCaseBasicSearchCondition) {
                $("#Search_HasCaseBasicSearchCondition").attr("checked", "checked");
                $('#Search_HasCaseBasicSearchCondition').trigger("click");
                $("#Search_HasCaseBasicSearchCondition").attr("checked", "checked");

                if (caseSearch.IsUnionCaseBasicSearchCondition) {
                    $("#Search_IsUnionCaseBasicSearchCondition").attr("checked", "checked");
                    $("#Search_IsNotUnionCaseBasicSearchCondition").removeAttr("checked");
                } else {
                    $("#Search_IsNotUnionCaseBasicSearchCondition").attr("checked", "checked");
                    $("#Search_IsUnionCaseBasicSearchCondition").removeAttr("checked");
                }

                if (caseSearch.CaseBasicSearchCondition != null) {
                    searchCondition.InitCaseBasicSearchCondition(caseSearch.CaseBasicSearchCondition);
                }
            }

            if (caseSearch.HasCaseAssistedFeeSearchCondition) {
                $("#Search_HasCaseAssistedFeeSearchCondition").attr("checked", "checked");
                $('#Search_HasCaseAssistedFeeSearchCondition').trigger("click");
                $("#Search_HasCaseAssistedFeeSearchCondition").attr("checked", "checked");

                if (caseSearch.IsUnionCaseAssistedFeeSearchCondition) {
                    $("#Search_IsUnionCaseAssistedFeeSearchCondition").attr("checked", "checked");
                    $("#Search_IsNotUnionCaseAssistedFeeSearchCondition").removeAttr("checked");
                } else {
                    $("#Search_IsNotUnionCaseAssistedFeeSearchCondition").attr("checked", "checked");
                    $("#Search_IsUnionCaseAssistedFeeSearchCondition").removeAttr("checked");
                }

                if (caseSearch.CaseAssistedFeeSearchCondition != null) {
                    searchCondition.InitCaseAssistedFeeSearchCondition(caseSearch.CaseAssistedFeeSearchCondition);
                }
            }

            if (caseSearch.HasCaseFeeSearchCondition) {
                $("#Search_HasCaseFeeSearchCondition").attr("checked", "checked");
                $('#Search_HasCaseFeeSearchCondition').trigger("click");
                $("#Search_HasCaseFeeSearchCondition").attr("checked", "checked");

                if (caseSearch.IsUnionCaseFeeSearchCondition) {
                    $("#Search_IsUnionCaseFeeSearchCondition").attr("checked", "checked");
                    $("#Search_IsNotUnionCaseFeeSearchCondition").removeAttr("checked");
                } else {
                    $("#Search_IsNotUnionCaseFeeSearchCondition").attr("checked", "checked");
                    $("#Search_IsUnionCaseFeeSearchCondition").removeAttr("checked");
                }

                if (caseSearch.CaseFeeSearchCondition != null) {
                    searchCondition.InitCaseFeeSearchCondition(caseSearch.CaseFeeSearchCondition);
                }
            }

            if (caseSearch.HasCaseFileSearchCondition) {
                $("#Search_HasCaseFileSearchCondition").attr("checked", "checked");
                $('#Search_HasCaseFileSearchCondition').trigger("click");
                $("#Search_HasCaseFileSearchCondition").attr("checked", "checked");

                if (caseSearch.IsUnionCaseFileSearchCondition) {
                    $("#Search_IsUnionCaseFileSearchCondition").attr("checked", "checked");
                    $("#Search_IsNotUnionCaseFileSearchCondition").removeAttr("checked");
                } else {
                    $("#Search_IsNotUnionCaseFileSearchCondition").attr("checked", "checked");
                    $("#Search_IsUnionCaseFileSearchCondition").removeAttr("checked");
                }

                if (caseSearch.CaseFileSearchCondition != null) {
                    searchCondition.InitCaseFileSearchCondition(caseSearch.CaseFileSearchCondition);
                }
            }
        }
    },
    InitCaseBasicSearchCondition: function(caseBasicSearch) {

        if (caseBasicSearch.HasCaseType) {
            $("#Search_CaseBasicSearchCondition_HasCaseType").attr("checked", "checked");
            $('#Search_CaseBasicSearchCondition_HasCaseType').trigger("click");
            $("#Search_CaseBasicSearchCondition_HasCaseType").attr("checked", "checked");
            $("#hid_Search_CaseBasicSearchCondition_CaseType").val(caseBasicSearch.CaseTypeId == null ? '': caseBasicSearch.CaseTypeId.join(','));
            $("#Search_CaseBasicSearchCondition_CaseType").val(caseBasicSearch.CaseTypeName == null ? '' : caseBasicSearch.CaseTypeName.join(','));
            if (caseBasicSearch.NotInCaseType) {
                $("#Search_CaseBasicSearchCondition_NotInCaseType").attr("checked", "checked");
            }
        }
 
        if (caseBasicSearch.HasCaseOriginPeople) {
            $("#Search_CaseBasicSearchCondition_HasCaseOriginPeople").attr("checked", "checked");
            $('#Search_CaseBasicSearchCondition_HasCaseOriginPeople').trigger("click");
            $("#Search_CaseBasicSearchCondition_HasCaseOriginPeople").attr("checked", "checked");
            $("#Search_CaseBasicSearchCondition_CaseOriginPeople").val(caseBasicSearch.CaseOriginPeople);
            $("#Search_CaseBasicSearchCondition_CaseOriginPeopleName").val(caseBasicSearch.CaseOriginPeopleName);
            if (caseBasicSearch.NotInCaseOriginPeople) {
                $("#Search_CaseBasicSearchCondition_NotInCaseOriginPeople").attr("checked", "checked");
            }
        }

        if (caseBasicSearch.HasCasePhase) {
            $("#Search_CaseBasicSearchCondition_HasCasePhase").attr("checked", "checked");
            $('#Search_CaseBasicSearchCondition_HasCasePhase').trigger("click");
            $("#Search_CaseBasicSearchCondition_HasCasePhase").attr("checked", "checked");
            $("#hid_Search_CaseBasicSearchCondition_CasePhase").val(caseBasicSearch.CasePhaseId == null ? '' : caseBasicSearch.CasePhaseId.join(','));
            $("#Search_CaseBasicSearchCondition_CasePhase").val(caseBasicSearch.CasePhaseName == null ? '' : caseBasicSearch.CasePhaseName.join(','));
            if (caseBasicSearch.NotInCasePhase) {
                $("#Search_CaseBasicSearchCondition_NotInCasePhase").attr("checked", "checked");
            }
        }

        if (caseBasicSearch.HasCaseOfficer) {
            $("#Search_CaseBasicSearchCondition_HasCaseOfficer").attr("checked", "checked");
            $('#Search_CaseBasicSearchCondition_HasCaseOfficer').trigger("click");
            $("#Search_CaseBasicSearchCondition_HasCaseOfficer").attr("checked", "checked");
            $("#Search_CaseBasicSearchCondition_CaseOfficer").val(caseBasicSearch.CaseOfficer);
            $("#Search_CaseBasicSearchCondition_CaseOfficerName").val(caseBasicSearch.CaseOfficerName);
            if (caseBasicSearch.NotInCaseOfficer) {
                $("#Search_CaseBasicSearchCondition_NotInCaseOfficer").attr("checked", "checked");
            }
        }

        if (caseBasicSearch.HasProcurator) {
            $("#Search_CaseBasicSearchCondition_HasProcurator").attr("checked", "checked");
            $('#Search_CaseBasicSearchCondition_HasProcurator').trigger("click");
            $("#Search_CaseBasicSearchCondition_HasProcurator").attr("checked", "checked");
            $("#Search_CaseBasicSearchCondition_Procurator").val(caseBasicSearch.Procurator);
            $("#Search_CaseBasicSearchCondition_ProcuratorName").val(caseBasicSearch.ProcuratorName);
            if (caseBasicSearch.NotInProcurator) {
                $("#Search_CaseBasicSearchCondition_NotInProcurator").attr("checked", "checked");
            }
        }

        if (caseBasicSearch.HasCopywriter) {
            $("#Search_CaseBasicSearchCondition_HasCopywriter").attr("checked", "checked");
            $('#Search_CaseBasicSearchCondition_HasCopywriter').trigger("click");
            $("#Search_CaseBasicSearchCondition_HasCopywriter").attr("checked", "checked");
            $("#Search_CaseBasicSearchCondition_Copywriter").val(caseBasicSearch.Copywriter);
            $("#Search_CaseBasicSearchCondition_CopywriterName").val(caseBasicSearch.CopywriterName);
            
            if (caseBasicSearch.NotInProcurator) {
                $("#Search_CaseBasicSearchCondition_NotInCopywriter").attr("checked", "checked");
            }
        }
        if (caseBasicSearch.HasCaseInventor) {
            $("#Search_CaseBasicSearchCondition_HasCaseInventor").attr("checked", "checked");
            $('#Search_CaseBasicSearchCondition_HasCaseInventor').trigger("click");
            $("#Search_CaseBasicSearchCondition_HasCaseInventor").attr("checked", "checked");
            $("#Search_CaseBasicSearchCondition_CaseInventor").val(caseBasicSearch.CaseInventor);
            $("#Search_CaseBasicSearchCondition_CaseInventorName").val(caseBasicSearch.CaseInventorName);
            if (caseBasicSearch.NotInCaseInventor) {
                $("#Search_CaseBasicSearchCondition_NotInCaseInventor").attr("checked", "checked");
            }
        }
      
        if (caseBasicSearch.HasCaseRequestNo) {
            $("#Search_CaseBasicSearchCondition_HasCaseRequestNo").attr("checked", "checked");
            $('#Search_CaseBasicSearchCondition_HasCaseRequestNo').trigger("click");
            $("#Search_CaseBasicSearchCondition_HasCaseRequestNo").attr("checked", "checked");
            $("#Search_CaseBasicSearchCondition_CaseRequestNo").val(caseBasicSearch.CaseRequestNo);
            if (caseBasicSearch.NotInCaseRequestNo) {
                $("#Search_CaseBasicSearchCondition_NotInCaseRequestNo").attr("checked", "checked");
            }
        }

        if (caseBasicSearch.HasCaseProposer) {
            $("#Search_CaseBasicSearchCondition_HasCaseProposer").attr("checked", "checked");
            $('#Search_CaseBasicSearchCondition_HasCaseProposer').trigger("click");
            $("#Search_CaseBasicSearchCondition_HasCaseProposer").attr("checked", "checked");
            $("#Search_CaseBasicSearchCondition_CaseProposer").val(caseBasicSearch.CaseProposer);
            if (caseBasicSearch.NotInCaseProposer) {
                $("#Search_CaseBasicSearchCondition_NotInCaseProposer").attr("checked", "checked");
            }
        }

        if (caseBasicSearch.HasCaseCustomerNo) {
            $("#Search_CaseBasicSearchCondition_HasCaseCustomerNo").attr("checked", "checked");
            $('#Search_CaseBasicSearchCondition_HasCaseCustomerNo').trigger("click");
            $("#Search_CaseBasicSearchCondition_HasCaseCustomerNo").attr("checked", "checked");
            $("#Search_CaseBasicSearchCondition_CaseCustomerNo").val(caseBasicSearch.CaseCustomerNo);
            if (caseBasicSearch.NotInCaseCustomerNo) {
                $("#Search_CaseBasicSearchCondition_NotInCaseCustomerNo").attr("checked", "checked");
            }
        }

        if (caseBasicSearch.HasPriority) {
            $("#Search_CaseBasicSearchCondition_HasPriority").attr("checked", "checked");
            $('#Search_CaseBasicSearchCondition_HasPriority').trigger("click");
            $("#Search_CaseBasicSearchCondition_HasPriority").attr("checked", "checked");
            if (caseBasicSearch.NotInHasPriority) {
                $("#Search_CaseBasicSearchCondition_NotInHasPriority").attr("checked", "checked");
            }
        }

        if (caseBasicSearch.HasCaseRegisterDate) {
            $("#Search_CaseBasicSearchCondition_HasCaseRegisterDate").attr("checked", "checked");
            $('#Search_CaseBasicSearchCondition_HasCaseRegisterDate').trigger("click");
            $("#Search_CaseBasicSearchCondition_HasCaseRegisterDate").attr("checked", "checked");
            
            $("#Search_CaseBasicSearchCondition_CaseRegisterDateFrom").val(caseBasicSearch.CaseRegisterDateFrom == '' ? '' : new Date(caseBasicSearch.CaseRegisterDateFrom).Format("yyyy-MM-dd"));
            $("#Search_CaseBasicSearchCondition_CaseRegisterDateTo").val(caseBasicSearch.CaseRegisterDateTo == '' ? '' : new Date(caseBasicSearch.CaseRegisterDateTo).Format("yyyy-MM-dd"));
            if (caseBasicSearch.NotInCaseRegisterDate) {
                $("#Search_CaseBasicSearchCondition_NotInCaseRegisterDate").attr("checked", "checked");
            }
        }

        if (caseBasicSearch.HasCaseRequestDate) {
            $("#Search_CaseBasicSearchCondition_HasCaseRequestDate").attr("checked", "checked");
            $('#Search_CaseBasicSearchCondition_HasCaseRequestDate').trigger("click");
            $("#Search_CaseBasicSearchCondition_HasCaseRequestDate").attr("checked", "checked");
            $("#Search_CaseBasicSearchCondition_CaseRequestDateFrom").val(caseBasicSearch.CaseRequestDateFrom == '' ? '' : new Date(caseBasicSearch.CaseRequestDateFrom).Format("yyyy-MM-dd"));
            $("#Search_CaseBasicSearchCondition_CaseRequestDateTo").val(caseBasicSearch.CaseRequestDateTo == '' ? '' : new Date(caseBasicSearch.CaseRequestDateTo).Format("yyyy-MM-dd"));
            if (caseBasicSearch.NotInCaseRequestDate) {
                $("#Search_CaseBasicSearchCondition_NotInCaseRequestDate").attr("checked", "checked");
            }
        }

        if (caseBasicSearch.HasAuthorizationDate) {
            $("#Search_CaseBasicSearchCondition_HasAuthorizationDate").attr("checked", "checked");
            $('#Search_CaseBasicSearchCondition_HasAuthorizationDate').trigger("click");
            $("#Search_CaseBasicSearchCondition_HasAuthorizationDate").attr("checked", "checked");

            $("#Search_CaseBasicSearchCondition_AuthorizationDateFrom").val(caseBasicSearch.AuthorizationDateFrom == '' ? '' : new Date(caseBasicSearch.AuthorizationDateFrom).Format("yyyy-MM-dd"));
            $("#Search_CaseBasicSearchCondition_AuthorizationDateTo").val(caseBasicSearch.AuthorizationDateTo == '' ? '' : new Date(caseBasicSearch.AuthorizationDateTo).Format("yyyy-MM-dd"));
            if (caseBasicSearch.NotInAuthorizationDate) {
                $("#Search_CaseBasicSearchCondition_NotInAuthorizationDate").attr("checked", "checked");
            }
        }

        if (caseBasicSearch.HasDeadline) {
            $("#Search_CaseBasicSearchCondition_HasDeadline").attr("checked", "checked");
            $('#Search_CaseBasicSearchCondition_HasDeadline').trigger("click");
            $("#Search_CaseBasicSearchCondition_HasDeadline").attr("checked", "checked");
            $("#Search_CaseBasicSearchCondition_DeadlineFrom").val(caseBasicSearch.DeadlineFrom == '' ? '' : new Date(caseBasicSearch.DeadlineFrom).Format("yyyy-MM-dd"));
            $("#Search_CaseBasicSearchCondition_DeadlineTo").val(caseBasicSearch.DeadlineTo == '' ? '' : new Date(caseBasicSearch.DeadlineTo).Format("yyyy-MM-dd"));
            if (caseBasicSearch.NotInDeadline) {
                $("#Search_CaseBasicSearchCondition_NotInDeadline").attr("checked", "checked");
            }
        }

        if (caseBasicSearch.HasCaseSubmitDate) {
            $("#Search_CaseBasicSearchCondition_HasCaseSubmitDate").attr("checked", "checked");
            $('#Search_CaseBasicSearchCondition_HasCaseSubmitDate').trigger("click");
            $("#Search_CaseBasicSearchCondition_HasCaseSubmitDate").attr("checked", "checked");
            $("#Search_CaseBasicSearchCondition_CaseSubmitDateFrom").val(caseBasicSearch.CaseSubmitDateFrom == '' ? '' : new Date(caseBasicSearch.CaseSubmitDateFrom).Format("yyyy-MM-dd"));
            $("#Search_CaseBasicSearchCondition_CaseSubmitDateTo").val(caseBasicSearch.CaseSubmitDateTo == '' ? '' : new Date(caseBasicSearch.CaseSubmitDateTo).Format("yyyy-MM-dd"));
            if (caseBasicSearch.NotInCaseSubmitDate) {
                $("#Search_CaseBasicSearchCondition_NotInCaseSubmitDate").attr("checked", "checked");
            }
        }
    },
    InitCaseAssistedFeeSearchCondition: function (caseAssistedFeeSearchCondition) {

        if (caseAssistedFeeSearchCondition.HasResponseUser) {
            $("#Search_CaseAssistedFeeSearchCondition_HasResponseUser").attr("checked", "checked");
            $('#Search_CaseAssistedFeeSearchCondition_HasResponseUser').trigger("click");
            $("#Search_CaseAssistedFeeSearchCondition_HasResponseUser").attr("checked", "checked");
            $("#Search_CaseAssistedFeeSearchCondition_ResponseUser").val(caseAssistedFeeSearchCondition.ResponseUser );
            $("#Search_CaseAssistedFeeSearchCondition_ResponseUserName").val(caseAssistedFeeSearchCondition.ResponseUserName);
            if (caseAssistedFeeSearchCondition.NotInResponseUser) {
                $("#Search_CaseAssistedFeeSearchCondition_NotInResponseUser").attr("checked", "checked");
            }
        }

        if (caseAssistedFeeSearchCondition.HasRequestDate) {
            $("#Search_CaseAssistedFeeSearchCondition_HasRequestDate").attr("checked", "checked");
            $('#Search_CaseAssistedFeeSearchCondition_HasRequestDate').trigger("click");
            $("#Search_CaseAssistedFeeSearchCondition_HasRequestDate").attr("checked", "checked");
            $("#Search_CaseAssistedFeeSearchCondition_RequestDateFrom").val(caseAssistedFeeSearchCondition.RequestDateFrom == '' ? '' : new Date(caseAssistedFeeSearchCondition.RequestDateFrom).Format("yyyy-MM-dd"));
            $("#Search_CaseAssistedFeeSearchCondition_RequestDateTo").val(caseAssistedFeeSearchCondition.RequestDateTo == '' ? '' : new Date(caseAssistedFeeSearchCondition.RequestDateTo).Format("yyyy-MM-dd"));
            if (caseAssistedFeeSearchCondition.NotInRequestDate) {
                $("#Search_CaseAssistedFeeSearchCondition_NotInRequestDate").attr("checked", "checked");
            }
        }

        if (caseAssistedFeeSearchCondition.HasResponseDate) {
            $("#Search_CaseAssistedFeeSearchCondition_HasResponseDate").attr("checked", "checked");
            $('#Search_CaseAssistedFeeSearchCondition_HasResponseDate').trigger("click");
            $("#Search_CaseAssistedFeeSearchCondition_HasResponseDate").attr("checked", "checked");
            $("#Search_CaseAssistedFeeSearchCondition_ResponseDateFrom").val(caseAssistedFeeSearchCondition.ResponseDateFrom == '' ? '' : new Date(caseAssistedFeeSearchCondition.ResponseDateFrom).Format("yyyy-MM-dd"));
            $("#Search_CaseAssistedFeeSearchCondition_ResponseDateTo").val(caseAssistedFeeSearchCondition.ResponseDateTo == '' ? '' : new Date(caseAssistedFeeSearchCondition.ResponseDateTo).Format("yyyy-MM-dd"));
            if (caseAssistedFeeSearchCondition.NotInResponseDate) {
                $("#Search_CaseAssistedFeeSearchCondition_NotInResponseDate").attr("checked", "checked");
            }
        }
         
    },
    InitCaseFeeSearchCondition: function (caseFeeSearchCondition) {
        
        if (caseFeeSearchCondition.HasInformDate) {
            $("#Search_CaseFeeSearchCondition_HasInformDate").attr("checked", "checked");
            $('#Search_CaseFeeSearchCondition_HasInformDate').trigger("click");
            $("#Search_CaseFeeSearchCondition_HasInformDate").attr("checked", "checked");
            $("#Search_CaseFeeSearchCondition_InformDateFrom").val(caseFeeSearchCondition.InformDateFrom == '' ? '' : new Date(caseFeeSearchCondition.InformDateFrom).Format("yyyy-MM-dd"));
            $("#Search_CaseFeeSearchCondition_InformDateTo").val(caseFeeSearchCondition.InformDateTo == '' ? '' : new Date(caseFeeSearchCondition.InformDateTo).Format("yyyy-MM-dd"));
            if (caseFeeSearchCondition.NotInInformDate) {
                $("#Search_CaseFeeSearchCondition_NotInInformDate").attr("checked", "checked");
            }
        }

        if (caseFeeSearchCondition.HasGainedDate) {
            $("#Search_CaseFeeSearchCondition_HasGainedDate").attr("checked", "checked");
            $('#Search_CaseFeeSearchCondition_HasGainedDate').trigger("click");
            $("#Search_CaseFeeSearchCondition_HasGainedDate").attr("checked", "checked");
            $("#Search_CaseFeeSearchCondition_GainedDateFrom").val(caseFeeSearchCondition.GainedDateFrom == '' ? '' : new Date(caseFeeSearchCondition.GainedDateFrom).Format("yyyy-MM-dd"));
            $("#Search_CaseFeeSearchCondition_GainedDateTo").val(caseFeeSearchCondition.GainedDateTo == '' ? '' : new Date(caseFeeSearchCondition.GainedDateTo).Format("yyyy-MM-dd"));
            if (caseFeeSearchCondition.NotInGainedDate) {
                $("#Search_CaseFeeSearchCondition_NotInGainedDate").attr("checked", "checked");
            }
        }

        if (caseFeeSearchCondition.HasResponseUser) {
            $("#Search_CaseFeeSearchCondition_HasResponseUser").attr("checked", "checked");
            $('#Search_CaseFeeSearchCondition_HasResponseUser').trigger("click");
            $("#Search_CaseFeeSearchCondition_HasResponseUser").attr("checked", "checked");
            $("#Search_CaseFeeSearchCondition_ResponseUser").val(caseFeeSearchCondition.ResponseUser);
            $("#Search_CaseFeeSearchCondition_ResponseUserName").val(caseFeeSearchCondition.ResponseUserName);
            if (caseFeeSearchCondition.NotInResponseUser) {
                $("#Search_CaseFeeSearchCondition_NotInResponseUser").attr("checked", "checked");
            }
        }
        
        if (caseFeeSearchCondition.HasBillNo) {
            $("#Search_CaseFeeSearchCondition_HasBillNo").attr("checked", "checked");
            $('#Search_CaseFeeSearchCondition_HasBillNo').trigger("click");
            $("#Search_CaseFeeSearchCondition_HasBillNo").attr("checked", "checked");
            $("#Search_CaseFeeSearchCondition_BillNo").val(caseFeeSearchCondition.BillNo);
             if (caseFeeSearchCondition.NotInBillNo) {
                $("#Search_CaseFeeSearchCondition_NotInBillNo").attr("checked", "checked");
            }
        }

        if (caseFeeSearchCondition.HasBillStatus) {
            $("#Search_CaseFeeSearchCondition_HasBillStatus").attr("checked", "checked");
            $('#Search_CaseFeeSearchCondition_HasBillStatus').trigger("click");
            $("#Search_CaseFeeSearchCondition_HasBillStatus").attr("checked", "checked");
            $("#hid_Search_CaseFeeSearchCondition_BillStatus").val(caseFeeSearchCondition.BillStatusId == null ? '' : caseFeeSearchCondition.BillStatusId.join(','));
            $("#Search_CaseFeeSearchCondition_BillStatus").val(caseFeeSearchCondition.BillStatusName == null ? '' : caseFeeSearchCondition.BillStatusName.join(','));
            if (caseFeeSearchCondition.NotInBillStatus) {
                $("#Search_CaseFeeSearchCondition_NotInBillStatus").attr("checked", "checked");
            }
        }

        if (caseFeeSearchCondition.HasBillDate) {
            $("#Search_CaseFeeSearchCondition_HasBillDate").attr("checked", "checked");
            $('#Search_CaseFeeSearchCondition_HasBillDate').trigger("click");
            $("#Search_CaseFeeSearchCondition_HasBillDate").attr("checked", "checked");
            $("#Search_CaseFeeSearchCondition_BillDateFrom").val(caseFeeSearchCondition.BillDateFrom == '' ? '' : new Date(caseFeeSearchCondition.BillDateFrom).Format("yyyy-MM-dd"));
            $("#Search_CaseFeeSearchCondition_BillDateTo").val(caseFeeSearchCondition.BillDateTo == '' ? '' : new Date(caseFeeSearchCondition.BillDateTo).Format("yyyy-MM-dd"));
            if (caseFeeSearchCondition.NotInBillDate) {
                $("#Search_CaseFeeSearchCondition_NotInBillDate").attr("checked", "checked");
            }
        }
         

        if (caseFeeSearchCondition.HasFeeTypeId) {
            $("#Search_CaseFeeSearchCondition_HasFeeTypeId").attr("checked", "checked");
            $('#Search_CaseFeeSearchCondition_HasFeeTypeId').trigger("click");
            $("#Search_CaseFeeSearchCondition_HasFeeTypeId").attr("checked", "checked");
            $("#hid_Search_CaseFeeSearchCondition_CaseFeeType").val(caseFeeSearchCondition.FeeTypeId == null ? '' : caseFeeSearchCondition.FeeTypeId.join(','));
            $("#Search_CaseFeeSearchCondition_CaseFeeType").val(caseFeeSearchCondition.FeeTypeName == null ? '' : caseFeeSearchCondition.FeeTypeName.join(','));
            if (caseFeeSearchCondition.NotInFeeTypeId) {
                $("#Search_CaseFeeSearchCondition_NotInFeeTypeId").attr("checked", "checked");
            }
        }
    },
    InitCaseFileSearchCondition: function (caseFileSearchCondition) {

        if (caseFileSearchCondition.HasUploadingUser) {
            $("#Search_CaseFileSearchCondition_HasUploadingUser").attr("checked", "checked");
            $('#Search_CaseFileSearchCondition_HasUploadingUser').trigger("click");
            $("#Search_CaseFileSearchCondition_HasUploadingUser").attr("checked", "checked");
            $("#Search_CaseFileSearchCondition_UploadingUser").val(caseFileSearchCondition.UploadingUser);
            $("#Search_CaseFileSearchCondition_UploadingUserName").val(caseFileSearchCondition.UploadingUserName);
            if (caseFileSearchCondition.NotInUploadingUser) {
                $("#Search_CaseFileSearchCondition_NotInUploadingUser").attr("checked", "checked");
            }
        }

        if (caseFileSearchCondition.HasUploadingTime) {
            $("#Search_CaseFileSearchCondition_HasUploadingTime").attr("checked", "checked");
            $('#Search_CaseFileSearchCondition_HasUploadingTime').trigger("click");
            $("#Search_CaseFileSearchCondition_HasUploadingTime").attr("checked", "checked");
            $("#Search_CaseFileSearchCondition_UploadingTimeFrom").val(caseFileSearchCondition.UploadingTimeFrom == '' ? '' : new Date(caseFileSearchCondition.UploadingTimeFrom).Format("yyyy-MM-dd"));
            $("#Search_CaseFileSearchCondition_UploadingTimeTo").val(caseFileSearchCondition.UploadingTimeTo == '' ? '' : new Date(caseFileSearchCondition.UploadingTimeTo).Format("yyyy-MM-dd"));
            if (caseFileSearchCondition.NotInUploadingTime) {
                $("#Search_CaseFileSearchCondition_NotInUploadingTime").attr("checked", "checked");
            }
        }


        if (caseFileSearchCondition.HasFileTypeId) {
            
            
            $("#Search_CaseFileSearchCondition_HasFileTypeId").attr("checked", "checked");
            $('#Search_CaseFileSearchCondition_HasFileTypeId').trigger("click");
            $("#Search_CaseFileSearchCondition_HasFileTypeId").attr("checked", "checked");
            $("#hid_Search_CaseFileSearchCondition_CaseFileType").val(caseFileSearchCondition.FileTypeId == null ? '' : caseFileSearchCondition.FileTypeId.join(','));
            $("#Search_CaseFileSearchCondition_CaseFileType").val(caseFileSearchCondition.FileTypeName == null ? '' : caseFileSearchCondition.FileTypeName.join(','));
            if (caseFileSearchCondition.NotInFileTypeId) {
                $("#Search_CaseFileSearchCondition_NotInFileTypeId").attr("checked", "checked");
            }
        }

    },

    CaseBasicSearchCondition: function (data) {

        if ($("#Search_HasCaseBasicSearchCondition").attr("checked") == 'checked') {
            data["Search.HasCaseBasicSearchCondition"] = true;
            data["Search.IsUnionCaseBasicSearchCondition"] = $("#Search_IsUnionCaseBasicSearchCondition").prop("checked") == true;
            data["Search.IsNotUnionCaseBasicSearchCondition"] = $("#Search_IsNotUnionCaseBasicSearchCondition").prop("checked") == true;

            data["Search.CaseBasicSearchCondition.HasCaseType"] = $("#Search_CaseBasicSearchCondition_HasCaseType").prop("checked") == true;
            data["Search.CaseBasicSearchCondition.NotInCaseType"] = $("#Search_CaseBasicSearchCondition_NotInCaseType").prop("checked") == true;
            var caseTypeIds = $("#hid_Search_CaseBasicSearchCondition_CaseType").val().split(',');
            var caseTypeIdNames = $("#Search_CaseBasicSearchCondition_CaseType").val().split(',');

            for (var i = 0; i < caseTypeIds.length; i++) {
                data["Search.CaseBasicSearchCondition.CaseTypeId[" + i + "]"] = parseInt(caseTypeIds[i]);
                data["Search.CaseBasicSearchCondition.CaseTypeName[" + i + "]"] = caseTypeIdNames[i];
            }

            //data["Search.CaseBasicSearchCondition.CaseType"] = $("#hid_Search_CaseBasicSearchCondition_CaseType").val();

            data["Search.CaseBasicSearchCondition.HasCaseOriginPeople"] = $("#Search_CaseBasicSearchCondition_HasCaseOriginPeople").prop("checked") == true;
            data["Search.CaseBasicSearchCondition.CaseOriginPeople"] = $("#Search_CaseBasicSearchCondition_CaseOriginPeople").val();
            data["Search.CaseBasicSearchCondition.CaseOriginPeopleName"] = $("#Search_CaseBasicSearchCondition_CaseOriginPeopleName").val();
            data["Search.CaseBasicSearchCondition.NotInCaseOriginPeople"] = $("#Search_CaseBasicSearchCondition_NotInCaseOriginPeople").prop("checked") == true;

            data["Search.CaseBasicSearchCondition.HasCaseOfficer"] = $("#Search_CaseBasicSearchCondition_HasCaseOfficer").prop("checked") == true;
            data["Search.CaseBasicSearchCondition.CaseOfficer"] = $("#Search_CaseBasicSearchCondition_CaseOfficer").val();
            data["Search.CaseBasicSearchCondition.CaseOfficerName"] = $("#Search_CaseBasicSearchCondition_CaseOfficerName").val();
            data["Search.CaseBasicSearchCondition.NotInCaseOfficer"] = $("#Search_CaseBasicSearchCondition_NotInCaseOfficer").prop("checked") == true;

            data["Search.CaseBasicSearchCondition.HasProcurator"] = $("#Search_CaseBasicSearchCondition_HasProcurator").prop("checked") == true;
            data["Search.CaseBasicSearchCondition.Procurator"] = $("#Search_CaseBasicSearchCondition_Procurator").val();
            data["Search.CaseBasicSearchCondition.ProcuratorName"] = $("#Search_CaseBasicSearchCondition_ProcuratorName").val();
            data["Search.CaseBasicSearchCondition.NotInProcurator"] = $("#Search_CaseBasicSearchCondition_NotInProcurator").prop("checked") == true;

            data["Search.CaseBasicSearchCondition.HasCopywriter"] = $("#Search_CaseBasicSearchCondition_HasCopywriter").prop("checked") == true;
            data["Search.CaseBasicSearchCondition.Copywriter"] = $("#Search_CaseBasicSearchCondition_Copywriter").val();
            data["Search.CaseBasicSearchCondition.CopywriterName"] = $("#Search_CaseBasicSearchCondition_CopywriterName").val();
            data["Search.CaseBasicSearchCondition.NotInCopywriter"] = $("#Search_CaseBasicSearchCondition_NotInCopywriter").prop("checked") == true;

            data["Search.CaseBasicSearchCondition.HasCaseInventor"] = $("#Search_CaseBasicSearchCondition_HasCaseInventor").prop("checked") == true;
            data["Search.CaseBasicSearchCondition.CaseInventor"] = $("#Search_CaseBasicSearchCondition_CaseInventor").val();
            data["Search.CaseBasicSearchCondition.NotInCaseInventor"] = $("#Search_CaseBasicSearchCondition_NotInCaseInventor").prop("checked") == true;

            data["Search.CaseBasicSearchCondition.HasCaseRequestNo"] = $("#Search_CaseBasicSearchCondition_HasCaseRequestNo").prop("checked") == true;
            data["Search.CaseBasicSearchCondition.CaseRequestNo"] = $("#Search_CaseBasicSearchCondition_CaseRequestNo").val();
            data["Search.CaseBasicSearchCondition.NotInCaseRequestNo"] = $("#Search_CaseBasicSearchCondition_NotInCaseRequestNo").prop("checked") == true;

            data["Search.CaseBasicSearchCondition.HasCaseProposer"] = $("#Search_CaseBasicSearchCondition_HasCaseProposer").prop("checked") == true;
            data["Search.CaseBasicSearchCondition.CaseProposer"] = $("#Search_CaseBasicSearchCondition_CaseProposer").val();
            data["Search.CaseBasicSearchCondition.NotInCaseProposer"] = $("#Search_CaseBasicSearchCondition_NotInCaseProposer").prop("checked") == true;

            data["Search.CaseBasicSearchCondition.HasCaseCustomerNo"] = $("#Search_CaseBasicSearchCondition_HasCaseCustomerNo").prop("checked") == true;
            data["Search.CaseBasicSearchCondition.CaseCustomerNo"] = $("#Search_CaseBasicSearchCondition_CaseCustomerNo").val();
            data["Search.CaseBasicSearchCondition.NotInCaseCustomerNo"] = $("#Search_CaseBasicSearchCondition_NotInCaseCustomerNo").prop("checked") == true;

            data["Search.CaseBasicSearchCondition.HasPriority"] = $("#Search_CaseBasicSearchCondition_HasPriority").prop("checked") == true;
            data["Search.CaseBasicSearchCondition.NotInHasPriority"] = $("#Search_CaseBasicSearchCondition_NotInHasPriority").prop("checked") == true;

            data["Search.CaseBasicSearchCondition.HasCasePhase"] = $("#Search_CaseBasicSearchCondition_HasCasePhase").prop("checked") == true;

            var casePhaseIds = $("#hid_Search_CaseBasicSearchCondition_CasePhase").val().split(',');
            var casePhaseNames = $("#Search_CaseBasicSearchCondition_CasePhase").val().split(',');

            for (i = 0; i < casePhaseIds.length; i++) {
                data["Search.CaseBasicSearchCondition.CasePhaseId[" + i + "]"] = parseInt(casePhaseIds[i]);
                data["Search.CaseBasicSearchCondition.CasePhaseName[" + i + "]"] = casePhaseNames[i];
            }

            data["Search.CaseBasicSearchCondition.NotInCasePhase"] = $("#Search_CaseBasicSearchCondition_NotInCasePhase").prop("checked") == true;

            data["Search.CaseBasicSearchCondition.HasCaseRegisterDate"] = $("#Search_CaseBasicSearchCondition_HasCaseRegisterDate").prop("checked") == true;
            data["Search.CaseBasicSearchCondition.CaseRegisterDateFrom"] = $("#Search_CaseBasicSearchCondition_CaseRegisterDateFrom").val();
            data["Search.CaseBasicSearchCondition.CaseRegisterDateTo"] = $("#Search_CaseBasicSearchCondition_CaseRegisterDateTo").val();
            data["Search.CaseBasicSearchCondition.NotInCaseRegisterDate"] = $("#Search_CaseBasicSearchCondition_NotInCaseRegisterDate").prop("checked") == true;

            data["Search.CaseBasicSearchCondition.HasCaseRequestDate"] = $("#Search_CaseBasicSearchCondition_HasCaseRequestDate").prop("checked") == true;
            data["Search.CaseBasicSearchCondition.CaseRequestDateFrom"] = $("#Search_CaseBasicSearchCondition_CaseRequestDateFrom").val();
            data["Search.CaseBasicSearchCondition.CaseRequestDateTo"] = $("#Search_CaseBasicSearchCondition_CaseRequestDateTo").val();
            data["Search.CaseBasicSearchCondition.NotInCaseRequestDate"] = $("#Search_CaseBasicSearchCondition_NotInCaseRequestDate").prop("checked") == true;

            data["Search.CaseBasicSearchCondition.HasAuthorizationDate"] = $("#Search_CaseBasicSearchCondition_HasAuthorizationDate").prop("checked") == true;
            data["Search.CaseBasicSearchCondition.AuthorizationDateFrom"] = $("#Search_CaseBasicSearchCondition_AuthorizationDateFrom").val();
            data["Search.CaseBasicSearchCondition.AuthorizationDateTo"] = $("#Search_CaseBasicSearchCondition_AuthorizationDateTo").val();
            data["Search.CaseBasicSearchCondition.NotInAuthorizationDate"] = $("#Search_CaseBasicSearchCondition_NotInAuthorizationDate").prop("checked") == true;

            data["Search.CaseBasicSearchCondition.HasDeadlineFrom"] = $("#Search_CaseBasicSearchCondition_HasDeadlineFrom").prop("checked") == true;
            data["Search.CaseBasicSearchCondition.DeadlineFrom"] = $("#Search_CaseBasicSearchCondition_DeadlineFrom").val();
            data["Search.CaseBasicSearchCondition.DeadlineTo"] = $("#Search_CaseBasicSearchCondition_DeadlineTo").val();
            data["Search.CaseBasicSearchCondition.NotInDeadlineFrom"] = $("#Search_CaseBasicSearchCondition_NotInDeadlineFrom").prop("checked") == true;

            data["Search.CaseBasicSearchCondition.HasCaseSubmitDateFrom"] = $("#Search_CaseBasicSearchCondition_HasCaseSubmitDateFrom").prop("checked") == true;
            data["Search.CaseBasicSearchCondition.CaseSubmitDateFrom"] = $("#Search_CaseBasicSearchCondition_CaseSubmitDateFrom").val();
            data["Search.CaseBasicSearchCondition.CaseSubmitDateTo"] = $("#Search_CaseBasicSearchCondition_CaseSubmitDateTo").val();
            data["Search.CaseBasicSearchCondition.NotInCaseSubmitDateFrom"] = $("#Search_CaseBasicSearchCondition_NotInCaseSubmitDateFrom").prop("checked") == true;

            if ($("input[class='has']:checked", "#casebasicsearchcondition").length > 1) {
                data["Search.CaseBasicSearchCondition.HasMultipleSearchCondition"] = true;
            }
        }
    },
    CaseAssistedFeeSearchCondition: function (data) {

        if ($("#Search_HasCaseAssistedFeeSearchCondition").attr("checked") == 'checked') {
            data["Search.HasCaseAssistedFeeSearchCondition"] = true;
            data["Search.IsUnionCaseAssistedFeeSearchCondition"] = $("#Search_IsUnionCaseAssistedFeeSearchCondition").prop("checked") == true;
            data["Search.IsNotUnionCaseAssistedFeeSearchCondition"] = $("#Search_IsNotUnionCaseAssistedFeeSearchCondition").prop("checked") == true;

            data["Search.CaseAssistedFeeSearchCondition.HasResponseUser"] = $("#Search_CaseAssistedFeeSearchCondition_HasResponseUser").attr("checked") == 'checked';
            data["Search.CaseAssistedFeeSearchCondition.NotInResponseUser"] =$("#Search_CaseAssistedFeeSearchCondition_NotInResponseUser").attr("checked") == 'checked';
            data["Search.CaseAssistedFeeSearchCondition.ResponseUser"] = $("#Search_CaseAssistedFeeSearchCondition_ResponseUser").val();
            data["Search.CaseAssistedFeeSearchCondition.ResponseUserName"] = $("#Search_CaseAssistedFeeSearchCondition_ResponseUserName").val();

            data["Search.CaseAssistedFeeSearchCondition.HasRequestDate"] = $("#Search_CaseAssistedFeeSearchCondition_HasRequestDate").prop("checked") == true;
            data["Search.CaseAssistedFeeSearchCondition.RequestDateFrom"] = $("#Search_CaseAssistedFeeSearchCondition_RequestDateFrom").val();
            data["Search.CaseAssistedFeeSearchCondition.RequestDateTo"] = $("#Search_CaseAssistedFeeSearchCondition_RequestDateTo").val();
            data["Search.CaseAssistedFeeSearchCondition.NotInRequestDate"] = $("#Search_CaseAssistedFeeSearchCondition_NotInRequestDate").prop("checked") == true;

            data["Search.CaseAssistedFeeSearchCondition.HasResponseDate"] = $("#Search_CaseAssistedFeeSearchCondition_HasResponseDate").prop("checked") == true;
            data["Search.CaseAssistedFeeSearchCondition.ResponseDateFrom"] = $("#Search_CaseAssistedFeeSearchCondition_ResponseDateFrom").val();
            data["Search.CaseAssistedFeeSearchCondition.ResponseDateTo"] = $("#Search_CaseAssistedFeeSearchCondition_ResponseDateTo").val();
            data["Search.CaseAssistedFeeSearchCondition.NotInResponseDate"] = $("#Search_CaseAssistedFeeSearchCondition_NotInResponseDate").prop("checked") == true;

            if ($("input[class='has']:checked", "#caseassistedfeesearchcondition").length > 1) {
                data["Search.CaseAssistedFeeSearchCondition.HasMultipleSearchCondition"] = true;
            }
        }
    },
    CaseFeeSearchCondition: function (data) {
        if ($("#Search_HasCaseFeeSearchCondition").attr("checked") == 'checked') {
            data["Search.HasCaseFeeSearchCondition"] = true;

            data["Search.IsUnionCaseFeeSearchCondition"] = $("#Search_IsUnionCaseFeeSearchCondition").prop("checked") == true;
            data["Search.IsNotUnionCaseFeeSearchCondition"] = $("#Search_IsNotUnionCaseFeeSearchCondition").prop("checked") == true;

            data["Search.CaseFeeSearchCondition.HasInformDate"] = $("#Search_CaseFeeSearchCondition_HasInformDate").prop("checked") == true;
            data["Search.CaseFeeSearchCondition.InformDateFrom"] = $("#Search_CaseFeeSearchCondition_InformDateFrom").val();
            data["Search.CaseFeeSearchCondition.InformDateTo"] = $("#Search_CaseFeeSearchCondition_InformDateTo").val();
            data["Search.CaseFeeSearchCondition.NotInInformDate"] = $("#Search_CaseFeeSearchCondition_NotInInformDate").prop("checked") == true;

            data["Search.CaseFeeSearchCondition.HasGainedDate"] = $("#Search_CaseFeeSearchCondition_HasGainedDate").prop("checked") == true;
            data["Search.CaseFeeSearchCondition.GainedDateFrom"] = $("#Search_CaseFeeSearchCondition_GainedDateFrom").val();
            data["Search.CaseFeeSearchCondition.GainedDateTo"] = $("#Search_CaseFeeSearchCondition_GainedDateTo").val();
            data["Search.CaseFeeSearchCondition.NotInGainedDate"] = $("#Search_CaseFeeSearchCondition_NotInGainedDate").prop("checked") == true;

            data["Search.CaseFeeSearchCondition.HasResponseUser"] = $("#Search_CaseFeeSearchCondition_HasResponseUser").prop("checked") == true;
            data["Search.CaseFeeSearchCondition.ResponseUser"] = $("#Search_CaseFeeSearchCondition_ResponseUser").val();
            data["Search.CaseFeeSearchCondition.ResponseUserName"] = $("#Search_CaseFeeSearchCondition_ResponseUserName").val();
            data["Search.CaseFeeSearchCondition.NotInResponseUser"] = $("#Search_CaseFeeSearchCondition_NotInResponseUser").prop("checked") == true;

            data["Search.CaseFeeSearchCondition.HasBillNo"] = $("#Search_CaseFeeSearchCondition_HasBillNo").prop("checked") == true;
            data["Search.CaseFeeSearchCondition.BillNo"] = $("#Search_CaseFeeSearchCondition_BillNo").val();
            data["Search.CaseFeeSearchCondition.NotInBillNo"] = $("#Search_CaseFeeSearchCondition_NotInBillNo").prop("checked") == true;


            data["Search.CaseFeeSearchCondition.HasBillStatus"] = $("#Search_CaseFeeSearchCondition_HasBillStatus").prop("checked") == true;
            var caseFeeInvoiceStatusIds = $("#hid_Search_CaseFeeSearchCondition_BillStatus").val().split(',');
            var caseFeeInvoiceStatusNames = $("#Search_CaseFeeSearchCondition_BillStatus").val().split(',');
            for (var i = 0; i < caseFeeInvoiceStatusIds.length; i++) {
                data["Search.CaseFeeSearchCondition.BillStatusId[" + i + "]"] = parseInt(caseFeeInvoiceStatusIds[i]);
                data["Search.CaseFeeSearchCondition.BillStatusName[" + i + "]"] = caseFeeInvoiceStatusNames[i];
            }
            data["Search.CaseFeeSearchCondition.NotInBillStatus"] = $("#Search_CaseFeeSearchCondition_NotInBillStatus").prop("checked") == true;

            data["Search.CaseFeeSearchCondition.HasBillDate"] = $("#Search_CaseFeeSearchCondition_HasBillDate").prop("checked") == true;
            data["Search.CaseFeeSearchCondition.BillDateFrom"] = $("#Search_CaseFeeSearchCondition_BillDateFrom").val();
            data["Search.CaseFeeSearchCondition.BillDateTo"] = $("#Search_CaseFeeSearchCondition_BillDateTo").val();
            data["Search.CaseFeeSearchCondition.NotInBillDate"] = $("#Search_CaseFeeSearchCondition_NotInBillDate").prop("checked") == true;


            data["Search.CaseFeeSearchCondition.HasFeeTypeId"] = $("#Search_CaseFeeSearchCondition_HasFeeTypeId").prop("checked") == true;
            var caseFeeTypeIds = $("#hid_Search_CaseFeeSearchCondition_CaseFeeType").val().split(',');
            var caseFeeTypeNames = $("#Search_CaseFeeSearchCondition_CaseFeeType").val().split(',');

            for (i = 0; i < caseFeeTypeIds.length; i++) {
                data["Search.CaseFeeSearchCondition.FeeTypeId[" + i + "]"] = parseInt(caseFeeTypeIds[i]);
                data["Search.CaseFeeSearchCondition.FeeTypeName[" + i + "]"] = caseFeeTypeNames[i];
            }

            data["Search.CaseFeeSearchCondition.NotInFeeTypeId"] = $("#Search_CaseFeeSearchCondition_NotInFeeTypeId").prop("checked") == true;

            if ($("input[class='has']:checked", "#casefeesearchcondition").length > 1) {
                data["Search.CaseFeeSearchCondition.HasMultipleSearchCondition"] = true;
            }

        }
    },
    CaseFileSearchCondition: function (data) {

        if ($("#Search_HasCaseFileSearchCondition").attr("checked") == 'checked') {
            data["Search.HasCaseFileSearchCondition"] = true;

            data["Search.IsUnionCaseFileSearchCondition"] = $("#Search_IsUnionCaseFileSearchCondition").prop("checked") == true;
            data["Search.IsNotUnionCaseFileSearchCondition"] = $("#Search_IsNotUnionCaseFileSearchCondition").prop("checked") == true;

            data["Search.CaseFileSearchCondition.HasUploadingUser"] = $("#Search_CaseFileSearchCondition_HasUploadingUser").prop("checked") == true;
            data["Search.CaseFileSearchCondition.UploadingUser"] = $("#Search_CaseFileSearchCondition_UploadingUser").val();
            data["Search.CaseFileSearchCondition.UploadingUserName"] = $("#Search_CaseFileSearchCondition_UploadingUserName").val();
            data["Search.CaseFileSearchCondition.NotInUploadingUser"] = $("#Search_CaseFileSearchCondition_NotInUploadingUser").prop("checked") == true;

            data["Search.CaseFileSearchCondition.HasUploadingTime"] = $("#Search_CaseFileSearchCondition_HasUploadingTime").prop("checked") == true;
            data["Search.CaseFileSearchCondition.UploadingTimeFrom"] = $("#Search_CaseFileSearchCondition_UploadingTimeFrom").val();
            data["Search.CaseFileSearchCondition.UploadingTimeTo"] = $("#Search_CaseFileSearchCondition_UploadingTimeTo").val();
            data["Search.CaseFileSearchCondition.NotInUploadingTime"] = $("#Search_CaseFileSearchCondition_NotInUploadingTime").prop("checked") == true;
    
            data["Search.CaseFileSearchCondition.HasFileTypeId"] = $("#Search_CaseFileSearchCondition_HasFileTypeId").prop("checked") == true;
            var caseFileTypeIds = $("#hid_Search_CaseFileSearchCondition_CaseFileType").val().split(',');
            var caseFileTypeNames = $("#Search_CaseFileSearchCondition_CaseFileType").val().split(',');
            for (var i = 0; i < caseFileTypeIds.length; i++) {
                data["Search.CaseFileSearchCondition.FileTypeId[" + i + "]"] = parseInt(caseFileTypeIds[i]);
                data["Search.CaseFileSearchCondition.FileTypeName[" + i + "]"] = caseFileTypeNames[i];
            }
            
            data["Search.CaseFileSearchCondition.NotInFileTypeId"] = $("#Search_CaseFileSearchCondition_NotInFileTypeId").prop("checked") == true;

            if ($("input[class='has']:checked", "#casefilesearchcondition").length > 1) {
                data["Search.CaseFileSearchCondition.HasMultipleSearchCondition"] = true;
            }
        }
    },

    CreateUpdate: function () {

        if ($("#Search_Name").val() == '') {
            $.showModalMessageBox("配置名称不能为空.");
            return false;
        }

        if ($("#Search_HasCaseBasicSearchCondition").attr("checked") != 'checked'
            && $("#Search_HasCaseAssistedFeeSearchCondition").attr("checked") != 'checked'
            && $("#Search_HasCaseFeeSearchCondition").attr("checked") != 'checked'
            && $("#Search_HasCaseFileSearchCondition").attr("checked") != 'checked') {
            $.showModalMessageBox("请选择查询条件.");
            return false;
        }

        if ($("#Search_HasCaseBasicSearchCondition").attr("checked") == 'checked') {
            if ($("#Search_IsUnionCaseBasicSearchCondition").attr("checked") == 'checked'
                || $("#Search_IsNotUnionCaseBasicSearchCondition").attr("checked") == 'checked') {
            } else {
                $.showModalMessageBox("请选择基本信息并集或交集选项.");
                return false;
            }
        }

        if ($("#Search_HasCaseAssistedFeeSearchCondition").attr("checked") == 'checked') {
            if ($("#Search_IsUnionCaseAssistedFeeSearchCondition").attr("checked") == 'checked'
                || $("#Search_IsNotUnionCaseAssistedFeeSearchCondition").attr("checked") == 'checked') {
            } else {
                $.showModalMessageBox("请选择资助信息并集或交集选项.");
                return false;
            }
        }

        if ($("#Search_HasCaseFeeSearchCondition").attr("checked") == 'checked') {
            if ($("#Search_IsUnionCaseFeeSearchCondition").attr("checked") == 'checked'
                || $("#Search_IsNotUnionCaseFeeSearchCondition").attr("checked") == 'checked') {
            } else {
                $.showModalMessageBox("请选择财务信息并集或交集选项.");
                return false;
            }
        }

        if ($("#Search_HasCaseFileSearchCondition").attr("checked") == 'checked') {
            if ($("#Search_IsUnionCaseFileSearchCondition").attr("checked") == 'checked'
                || $("#Search_IsNotUnionCaseFileSearchCondition").attr("checked") == 'checked') {
            } else {
                $.showModalMessageBox("请选择文档信息并集或交集选项.");
                return false;
            }
        }

        var data = {};

        data["Search.SearchConditionId"] = $("#Search_SearchConditionId").val();
        data["Search.Name"] = $("#Search_Name").val();

        searchCondition.CaseBasicSearchCondition(data);
        searchCondition.CaseAssistedFeeSearchCondition(data);
        searchCondition.CaseFeeSearchCondition(data);
        searchCondition.CaseFileSearchCondition(data);

        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseSearchConditionCreateUpdate", data, function (response) {
            if (response.IsSuccess) {
                $.showModalMessageBox("保存成功.");
                $('#caseSearchModal').modal('hide');
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    Search: function () {

        if ($("#Search_HasCaseBasicSearchCondition").attr("checked") != 'checked'
            && $("#Search_HasCaseAssistedFeeSearchCondition").attr("checked") != 'checked'
            && $("#Search_HasCaseFeeSearchCondition").attr("checked") != 'checked'
            && $("#Search_HasCaseFileSearchCondition").attr("checked") != 'checked') {
            $.showModalMessageBox("请选择查询条件.");
            return false;
        }

        if ($("#Search_HasCaseBasicSearchCondition").attr("checked") == 'checked') {
            if ($("#Search_IsUnionCaseBasicSearchCondition").attr("checked") == 'checked'
                || $("#Search_IsNotUnionCaseBasicSearchCondition").attr("checked") == 'checked') {
            } else {
                $.showModalMessageBox("请选择基本信息并集或交集选项.");
                return false;
            }
        }

        if ($("#Search_HasCaseAssistedFeeSearchCondition").attr("checked") == 'checked') {
            if ($("#Search_IsUnionCaseAssistedFeeSearchCondition").attr("checked") == 'checked'
                || $("#Search_IsNotUnionCaseAssistedFeeSearchCondition").attr("checked") == 'checked') {
            } else {
                $.showModalMessageBox("请选择资助信息并集或交集选项.");
                return false;
            }
        }

        if ($("#Search_HasCaseFeeSearchCondition").attr("checked") == 'checked') {
            if ($("#Search_IsUnionCaseFeeSearchCondition").attr("checked") == 'checked'
                || $("#Search_IsNotUnionCaseFeeSearchCondition").attr("checked") == 'checked') {
            } else {
                $.showModalMessageBox("请选择财务信息并集或交集选项.");
                return false;
            }
        }

        if ($("#Search_HasCaseFileSearchCondition").attr("checked") == 'checked') {
            if ($("#Search_IsUnionCaseFileSearchCondition").attr("checked") == 'checked'
                || $("#Search_IsNotUnionCaseFileSearchCondition").attr("checked") == 'checked') {
            } else {
                $.showModalMessageBox("请选择文档信息并集或交集选项.");
                return false;
            }
        }
        $(":input", "#caseSearchForm").each(function () {
            $(this).removeAttr("disabled");
        });

        $("#Search_HasCaseBasicSearchCondition").val($("#Search_HasCaseBasicSearchCondition").attr("checked") == 'checked');
        $("#Search_IsUnionCaseBasicSearchCondition").val($("#Search_IsUnionCaseBasicSearchCondition").attr("checked") == 'checked');
        $("#Search_IsNotUnionCaseBasicSearchCondition").val($("#Search_IsNotUnionCaseBasicSearchCondition").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_HasCaseType").val($("#Search_CaseBasicSearchCondition_HasCaseType").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_NotInCaseType").val($("#Search_CaseBasicSearchCondition_NotInCaseType").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_HasCaseOriginPeople").val($("#Search_CaseBasicSearchCondition_HasCaseOriginPeople").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_NotInCaseOriginPeople").val($("#Search_CaseBasicSearchCondition_NotInCaseOriginPeople").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_HasCasePhase").val($("#Search_CaseBasicSearchCondition_HasCasePhase").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_NotInCasePhase").val($("#Search_CaseBasicSearchCondition_NotInCasePhase").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_HasCaseOfficer").val($("#Search_CaseBasicSearchCondition_HasCaseOfficer").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_NotInCaseOfficer").val($("#Search_CaseBasicSearchCondition_NotInCaseOfficer").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_HasProcurator").val($("#Search_CaseBasicSearchCondition_HasProcurator").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_NotInProcurator").val($("#Search_CaseBasicSearchCondition_NotInProcurator").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_HasCaseRequestNo").val($("#Search_CaseBasicSearchCondition_HasCaseRequestNo").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_NotInCaseRequestNo").val($("#Search_CaseBasicSearchCondition_NotInCaseRequestNo").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_HasCopywriter").val($("#Search_CaseBasicSearchCondition_HasCopywriter").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_NotInCopywriter").val($("#Search_CaseBasicSearchCondition_NotInCopywriter").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_HasCaseInventor").val($("#Search_CaseBasicSearchCondition_HasCaseInventor").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_NotInCaseInventor").val($("#Search_CaseBasicSearchCondition_NotInCaseInventor").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_HasCaseRequestNo").val($("#Search_CaseBasicSearchCondition_HasCaseRequestNo").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_NotInCaseRequestNo").val($("#Search_CaseBasicSearchCondition_NotInCaseRequestNo").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_HasCaseProposer").val($("#Search_CaseBasicSearchCondition_HasCaseProposer").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_NotInCaseProposer").val($("#Search_CaseBasicSearchCondition_NotInCaseProposer").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_HasCaseCustomerNo").val($("#Search_CaseBasicSearchCondition_HasCaseCustomerNo").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_NotInCaseCustomerNo").val($("#Search_CaseBasicSearchCondition_NotInCaseCustomerNo").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_HasPriority").val($("#Search_CaseBasicSearchCondition_HasPriority").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_NotInHasPriority").val($("#Search_CaseBasicSearchCondition_NotInHasPriority").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_HasCaseRegisterDate").val($("#Search_CaseBasicSearchCondition_HasCaseRegisterDate").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_NotInCaseRegisterDate").val($("#Search_CaseBasicSearchCondition_NotInCaseRegisterDate").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_HasCaseRequestDate").val($("#Search_CaseBasicSearchCondition_HasCaseRequestDate").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_NotInCaseRequestDate").val($("#Search_CaseBasicSearchCondition_NotInCaseRequestDate").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_HasAuthorizationDate").val($("#Search_CaseBasicSearchCondition_HasAuthorizationDate").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_NotInAuthorizationDate").val($("#Search_CaseBasicSearchCondition_NotInAuthorizationDate").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_HasDeadline").val($("#Search_CaseBasicSearchCondition_HasDeadline").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_NotInDeadline").val($("#Search_CaseBasicSearchCondition_NotInDeadline").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_HasCaseSubmitDate").val($("#Search_CaseBasicSearchCondition_HasCaseSubmitDate").attr("checked") == 'checked');
        $("#Search_CaseBasicSearchCondition_NotInCaseSubmitDate").val($("#Search_CaseBasicSearchCondition_NotInCaseSubmitDate").attr("checked") == 'checked');

        $("#Search_HasCaseAssistedFeeSearchCondition").val($("#Search_HasCaseAssistedFeeSearchCondition").attr("checked") == 'checked');
        $("#Search_IsUnionCaseAssistedFeeSearchCondition").val($("#Search_IsUnionCaseAssistedFeeSearchCondition").attr("checked") == 'checked');
        $("#Search_IsNotUnionCaseAssistedFeeSearchCondition").val($("#Search_IsNotUnionCaseAssistedFeeSearchCondition").attr("checked") == 'checked');
        $("#Search_CaseAssistedFeeSearchCondition_HasResponseUser").val($("#Search_CaseAssistedFeeSearchCondition_HasResponseUser").attr("checked") == 'checked');
        $("#Search_CaseAssistedFeeSearchCondition_NotInResponseUser").val($("#Search_CaseAssistedFeeSearchCondition_NotInResponseUser").attr("checked") == 'checked');
        $("#Search_CaseAssistedFeeSearchCondition_HasRequestDate").val($("#Search_CaseAssistedFeeSearchCondition_HasRequestDate").attr("checked") == 'checked');
        $("#Search_CaseAssistedFeeSearchCondition_NotInRequestDate").val($("#Search_CaseAssistedFeeSearchCondition_NotInRequestDate").attr("checked") == 'checked');
        $("#Search_CaseAssistedFeeSearchCondition_HasResponseDate").val($("#Search_CaseAssistedFeeSearchCondition_HasResponseDate").attr("checked") == 'checked');
        $("#Search_CaseAssistedFeeSearchCondition_NotInResponseDate").val($("#Search_CaseAssistedFeeSearchCondition_NotInResponseDate").attr("checked") == 'checked');
        
        $("#Search_HasCaseFeeSearchCondition").val($("#Search_HasCaseFeeSearchCondition").attr("checked") == 'checked');
        $("#Search_IsUnionCaseFeeSearchCondition").val($("#Search_IsUnionCaseFeeSearchCondition").attr("checked") == 'checked');
        $("#Search_IsNotUnionCaseFeeSearchCondition").val($("#Search_IsNotUnionCaseFeeSearchCondition").attr("checked") == 'checked');
        $("#Search_CaseFeeSearchCondition_HasInformDate").val($("#Search_CaseFeeSearchCondition_HasInformDate").attr("checked") == 'checked');
        $("#Search_CaseFeeSearchCondition_NotInInformDate").val($("#Search_CaseFeeSearchCondition_NotInInformDate").attr("checked") == 'checked');
        $("#Search_CaseFeeSearchCondition_HasGainedDate").val($("#Search_CaseFeeSearchCondition_HasGainedDate").attr("checked") == 'checked');
        $("#Search_CaseFeeSearchCondition_NotInGainedDate").val($("#Search_CaseFeeSearchCondition_NotInGainedDate").attr("checked") == 'checked');
        $("#Search_CaseFeeSearchCondition_HasResponseUser").val($("#Search_CaseFeeSearchCondition_HasResponseUser").attr("checked") == 'checked');
        $("#Search_CaseFeeSearchCondition_NotInResponseUser").val($("#Search_CaseFeeSearchCondition_NotInResponseUser").attr("checked") == 'checked');
        $("#Search_CaseFeeSearchCondition_HasBillNo").val($("#Search_CaseFeeSearchCondition_HasBillNo").attr("checked") == 'checked');
        $("#Search_CaseFeeSearchCondition_NotInBillNo").val($("#Search_CaseFeeSearchCondition_NotInBillNo").attr("checked") == 'checked');
        $("#Search_CaseFeeSearchCondition_HasBillStatus").val($("#Search_CaseFeeSearchCondition_HasBillStatus").attr("checked") == 'checked');
        $("#Search_CaseFeeSearchCondition_NotInBillStatus").val($("#Search_CaseFeeSearchCondition_NotInBillStatus").attr("checked") == 'checked');
        $("#Search_CaseFeeSearchCondition_HasBillDate").val($("#Search_CaseFeeSearchCondition_HasBillDate").attr("checked") == 'checked');
        $("#Search_CaseFeeSearchCondition_NotInBillDate").val($("#Search_CaseFeeSearchCondition_NotInBillDate").attr("checked") == 'checked');
        $("#Search_CaseFeeSearchCondition_HasFeeTypeId").val($("#Search_CaseFeeSearchCondition_HasFeeTypeId").attr("checked") == 'checked');
        $("#Search_CaseFeeSearchCondition_NotInFeeTypeId").val($("#Search_CaseFeeSearchCondition_NotInFeeTypeId").attr("checked") == 'checked');

        $("#Search_HasCaseFileSearchCondition").val($("#Search_HasCaseFileSearchCondition").attr("checked") == 'checked');
        $("#Search_IsUnionCaseFileSearchCondition").val($("#Search_IsUnionCaseFileSearchCondition").attr("checked") == 'checked');
        $("#Search_IsNotUnionCaseFileSearchCondition").val($("#Search_IsNotUnionCaseFileSearchCondition").attr("checked") == 'checked');
        $("#Search_CaseFileSearchCondition_HasUploadingUser").val($("#Search_CaseFileSearchCondition_HasUploadingUser").attr("checked") == 'checked');
        $("#Search_CaseFileSearchCondition_NotInUploadingUser").val($("#Search_CaseFileSearchCondition_NotInUploadingUser").attr("checked") == 'checked');
        $("#Search_CaseFileSearchCondition_HasUploadingTime").val($("#Search_CaseFileSearchCondition_HasUploadingTime").attr("checked") == 'checked');
        $("#Search_CaseFileSearchCondition_NotInUploadingTime").val($("#Search_CaseFileSearchCondition_NotInUploadingTime").attr("checked") == 'checked');
        $("#Search_CaseFileSearchCondition_HasFileTypeId").val($("#Search_CaseFileSearchCondition_HasFileTypeId").attr("checked") == 'checked');
        $("#Search_CaseFileSearchCondition_NotInFileTypeId").val($("#Search_CaseFileSearchCondition_NotInFileTypeId").attr("checked") == 'checked');

        if ($("input[class='has']:checked", "#casebasicsearchcondition").length > 1) {
            $("#Search_CaseBasicSearchCondition_HasMultipleSearchCondition").val(true);
        }

        if ($("input[class='has']:checked", "#caseassistedfeesearchcondition").length > 1) {
            $("#Search_CaseAssistedFeeSearchCondition_HasMultipleSearchCondition").val(true);
        }

        if ($("input[class='has']:checked", "#casefeesearchcondition").length > 1) {
            $("#Search_CaseFeeSearchCondition_HasMultipleSearchCondition").val(true);
        }

        if ($("input[class='has']:checked", "#casefilesearchcondition").length > 1) {
            $("#Search_CaseFileSearchCondition_HasMultipleSearchCondition").val(true);
        }

        $.openLoading();

        $("#caseSearchFormSubmit").submit();
    }
}

$(document).ready(function () {

    $(document).click(function (e) {
        $("#divCaseFeeTypeCheckBoxList").off().hide();
        $("#divCaseFileTypeCheckBoxList").off().hide();
        $("#divCasePhaseCheckBoxList").off().hide();
        $("#divCaseTypeCheckBoxList").off().hide();
        $("#divcaseconditionusers").off().hide();
        $("#divCaseFeeInvoiceStatusCheckBoxList").off().hide();
    });

    $("#btnCaseBasicSearchCondition").click(function () {
        $("#liCaseBasicSearchCondition").removeClass("active");
        $("#liCaseAssistedFeeSearchCondition").removeClass("active");
        $("#liCaseFeeSearchCondition").removeClass("active");
        $("#liCaseFileSearchCondition").removeClass("active");

        $("#liCaseBasicSearchCondition").addClass("active");

        $("#casebasicsearchcondition").css("display", "block");
        $("#caseassistedfeesearchcondition").css("display", "none");
        $("#casefeesearchcondition").css("display", "none");
        $("#casefilesearchcondition").css("display", "none");

    });

    $("#btnCaseAssistedFeeSearchCondition").click(function () {
        $("#liCaseBasicSearchCondition").removeClass("active");
        $("#liCaseAssistedFeeSearchCondition").removeClass("active");
        $("#liCaseFeeSearchCondition").removeClass("active");
        $("#liCaseFileSearchCondition").removeClass("active");

        $("#liCaseAssistedFeeSearchCondition").addClass("active");

        $("#casebasicsearchcondition").css("display", "none");
        $("#caseassistedfeesearchcondition").css("display", "block");
        $("#casefeesearchcondition").css("display", "none");
        $("#casefilesearchcondition").css("display", "none");
    });

    $("#btnCaseFeeSearchCondition").click(function () {

        $("#liCaseBasicSearchCondition").removeClass("active");
        $("#liCaseAssistedFeeSearchCondition").removeClass("active");
        $("#liCaseFeeSearchCondition").removeClass("active");
        $("#liCaseFileSearchCondition").removeClass("active");

        $("#liCaseFeeSearchCondition").addClass("active");

        $("#casebasicsearchcondition").css("display", "none");
        $("#caseassistedfeesearchcondition").css("display", "none");
        $("#casefeesearchcondition").css("display", "block");
        $("#casefilesearchcondition").css("display", "none");
    });

    $("#btnCaseFileSearchCondition").click(function () {
        $("#liCaseBasicSearchCondition").removeClass("active");
        $("#liCaseAssistedFeeSearchCondition").removeClass("active");
        $("#liCaseFeeSearchCondition").removeClass("active");
        $("#liCaseFileSearchCondition").removeClass("active");

        $("#liCaseFileSearchCondition").addClass("active");

        $("#casebasicsearchcondition").css("display", "none");
        $("#caseassistedfeesearchcondition").css("display", "none");
        $("#casefeesearchcondition").css("display", "none");
        $("#casefilesearchcondition").css("display", "block");
    });

    $("#Search_IsUnionCaseBasicSearchCondition").click(function () {
        if ($(this).attr("checked") == 'checked') {
            $("#Search_IsNotUnionCaseBasicSearchCondition").removeAttr("checked");
        }
    });

    $("#Search_IsNotUnionCaseBasicSearchCondition").click(function () {
        if ($(this).attr("checked") == 'checked') {
            $("#Search_IsUnionCaseBasicSearchCondition").removeAttr("checked");
        }
    });

    $("#Search_IsUnionCaseAssistedFeeSearchCondition").click(function () {
        if ($(this).attr("checked") == 'checked') {
            $("#Search_IsNotUnionCaseAssistedFeeSearchCondition").removeAttr("checked");
        }
    });

    $("#Search_IsNotUnionCaseAssistedFeeSearchCondition").click(function () {
        if ($(this).attr("checked") == 'checked') {
            $("#Search_IsUnionCaseAssistedFeeSearchCondition").removeAttr("checked");
        }
    });

    $("#Search_IsUnionCaseFeeSearchCondition").click(function () {
        if ($(this).attr("checked") == 'checked') {
            $("#Search_IsNotUnionCaseFeeSearchCondition").removeAttr("checked");
        }
    });

    $("#Search_IsNotUnionCaseFeeSearchCondition").click(function () {
        if ($(this).attr("checked") == 'checked') {
            $("#Search_IsUnionCaseFeeSearchCondition").removeAttr("checked");
        }
    });

    $("#Search_IsUnionCaseFileSearchCondition").click(function () {
        if ($(this).attr("checked") == 'checked') {
            $("#Search_IsNotUnionCaseFileSearchCondition").removeAttr("checked");
        }
    });

    $("#Search_IsNotUnionCaseFileSearchCondition").click(function () {
        if ($(this).attr("checked") == 'checked') {
            $("#Search_IsUnionCaseFileSearchCondition").removeAttr("checked");
        }
    });

    //searchCondition.Init();
});