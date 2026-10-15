//基本信息操作

// if ($(e).is("input:checkbox")) {

var caseInfo = {

    Init: function () {
        caseInfo.BindEvent();
        caseInfo.InputBindEvent();
        caseInfo.CaseInvestigation.BindEvent(); //绑定调查界面的保存事件
        //caseInfo.InitCaseType();
        caseInfo.CaseFile.Init();
    },

    BindEvent: function () {

        /*更新案件按钮*/
        $("#btnCaseRenewal").unbind("click");
        $("#btnCaseRenewal").click(function () {
            enableEditForm = true;
            caseInfo.Edit();
        });

        /*新建案件*/
        $("#btnCaseCreateNew").unbind("click");
        $("#btnCaseCreateNew").click(function () {
            if ($("#Case_CaseBasicInfo_CaseNo").val() != '') {
                $.showModalConfirmDialog("确定重新创建案件？", "caseInfo.CreateCompletedNew");
                return true;
            } else {
                caseInfo.CreateCompletedNew();
                return true;
            }
        });

        /*新建提醒*/
        $("#btnCaseEventCreate").unbind("click");
        $("#btnCaseEventCreate").bind("click", function () {
            caseInfo.CaseEvent.Open();
        });

        $("#btnCaseLevelMore").unbind("click");
        $("#btnCaseLevelMore").bind("click", (function () {
            caseInfo.CaseInstance.Open(0);
        }));

        /*案件级别 调查，一审，二审，再审，执行*/
        $("#btnCaseLevel1").unbind("click");
        $("#btnCaseLevel1").bind("click", (function () {

            $("#liCaseLevel1").removeClass("active");
            $("#liCaseLevel2").removeClass("active");
            $("#liCaseLevel4").removeClass("active");
            $("#liCaseLevel8").removeClass("active");
            $("#liCaseLevel16").removeClass("active");

            $("#liCaseLevel1").addClass("active");

            caseInfo.InitCaseBasic(1);
        }));

        $("#btnCaseLevel2").unbind("click");
        $("#btnCaseLevel2").bind("click", (function () {

            $("#liCaseLevel1").removeClass("active");
            $("#liCaseLevel2").removeClass("active");
            $("#liCaseLevel4").removeClass("active");
            $("#liCaseLevel8").removeClass("active");
            $("#liCaseLevel16").removeClass("active");

            $("#liCaseLevel2").addClass("active");

            caseInfo.InitCaseBasic(2);
        }));

        $("#btnCaseLevel4").unbind("click");
        $("#btnCaseLevel4").bind("click", (function () {

            $("#liCaseLevel1").removeClass("active");
            $("#liCaseLevel2").removeClass("active");
            $("#liCaseLevel4").removeClass("active");
            $("#liCaseLevel8").removeClass("active");
            $("#liCaseLevel16").removeClass("active");

            $("#liCaseLevel4").addClass("active");

            caseInfo.InitCaseBasic(4);
        }));

        $("#btnCaseLevel8").unbind("click");
        $("#btnCaseLevel8").bind("click", (function () {

            $("#liCaseLevel1").removeClass("active");
            $("#liCaseLevel2").removeClass("active");
            $("#liCaseLevel4").removeClass("active");
            $("#liCaseLevel8").removeClass("active");
            $("#liCaseLevel16").removeClass("active");

            $("#liCaseLevel8").addClass("active");

            caseInfo.InitCaseBasic(8);
        }));

        $("#btnCaseLevel16").unbind("click");
        $("#btnCaseLevel16").bind("click", (function () {

            $("#liCaseLevel1").removeClass("active");
            $("#liCaseLevel2").removeClass("active");
            $("#liCaseLevel4").removeClass("active");
            $("#liCaseLevel8").removeClass("active");
            $("#liCaseLevel16").removeClass("active");

            $("#liCaseLevel16").addClass("active");

            caseInfo.InitCaseBasic(16);
        }));

        /*费用*/
        $("#btnCaseFeeList").unbind("click");
        $("#btnCaseFeeList").click(function () {

            $("#liCaseFeeList").removeClass("active");
            $("#liCaseFileList").removeClass("active");
            $("#liCaseLogList").removeClass("active");

            $("#liCaseFeeList").addClass("active");

            if ($("#PageNo").length) {
                $("#PageNo").val(1);
                $("#PageSize").val(10);
            }

            caseInfo.CaseFee.List();
        });

        /*文件*/
        $("#btnCaseFileList").unbind("click");
        $("#btnCaseFileList").click(function () {

            $("#liCaseFeeList").removeClass("active");
            $("#liCaseFileList").removeClass("active");
            $("#liCaseLogList").removeClass("active");

            $("#liCaseFileList").addClass("active");

            if ($("#PageNo").length) {
                $("#PageNo").val(1);
                $("#PageSize").val(10);
            }

            caseInfo.CaseFile.List();
        });

        /*日志*/
        $("#btnCaseLogList").unbind("click");
        $("#btnCaseLogList").click(function () {

            $("#liCaseFeeList").removeClass("active");
            $("#liCaseFileList").removeClass("active");
            $("#liCaseLogList").removeClass("active");

            $("#liCaseLogList").addClass("active");

            if ($("#PageNo").length) {
                $("#PageNo").val(1);
                $("#PageSize").val(10);
            }

            caseInfo.CaseLog.List();
        });

    },

    InputBindEvent: function () {

        /*案由*/
        $("#Case_CaseBasicInfo_CauseName").unbind("click");
        $("#Case_CaseBasicInfo_CauseName").click(function () {
            caseInfo.CaseCause.Open();
        });

        /*法院*/
        $("#Case_CaseFirstInstance_CourtName,#Case_CaseSecondInstance_CourtName,#Case_CaseLastInstance_CourtName,#Case_CaseExecution_CourtName").unbind("click");
        $("#Case_CaseFirstInstance_CourtName,#Case_CaseSecondInstance_CourtName,#Case_CaseLastInstance_CourtName,#Case_CaseExecution_CourtName").click(function () {
            var selectedId =  $(this).attr("id").replace("Name","Id");
            var selectedName = $(this).attr("id");
            caseInfo.CaseCourt.Open(selectedId, selectedName);
        });

        /*权利人*/
        $("#Case_CaseInvestigation_CaseProsecutorName").unbind("click");
        $("#Case_CaseInvestigation_CaseProsecutorName").click(function () {
            var selectedId = $(this).attr("id").replace("Name", "");
            var selectedName = $(this).attr("id");
            caseInfo.CaseCustomer.Open(1, selectedId, selectedName);
        });

        /*原告*/
        $("#Case_CaseFirstInstance_CaseProsecutorName,#Case_CaseSecondInstance_CaseProsecutorName,#Case_CaseLastInstance_CaseProsecutorName,#Case_CaseExecution_CaseProsecutorName").unbind("click");
        $("#Case_CaseFirstInstance_CaseProsecutorName,#Case_CaseSecondInstance_CaseProsecutorName,#Case_CaseLastInstance_CaseProsecutorName,#Case_CaseExecution_CaseProsecutorName").click(function () {
            var selectedId = $(this).attr("id").replace("Name", "");
            var selectedName = $(this).attr("id");
            caseInfo.CaseCustomer.Open(1, selectedId, selectedName);
        });

        /*被告*/
        $("#Case_CaseFirstInstance_CaseDefendantName,#Case_CaseSecondInstance_CaseDefendantName,#Case_CaseLastInstance_CaseDefendantName,#Case_CaseExecution_CaseDefendantName").unbind("click");
        $("#Case_CaseFirstInstance_CaseDefendantName,#Case_CaseSecondInstance_CaseDefendantName,#Case_CaseLastInstance_CaseDefendantName,#Case_CaseExecution_CaseDefendantName").click(function () {
            var selectedId = $(this).attr("id").replace("Name", "");
            var selectedName = $(this).attr("id");
            caseInfo.CaseCustomer.Open(2, selectedId, selectedName);
        });

        /*第三人*/
        $("#Case_CaseFirstInstance_TheThirdName,#Case_CaseSecondInstance_TheThirdName,#Case_CaseLastInstance_TheThirdName,#Case_CaseExecution_TheThirdName").unbind("click");
        $("#Case_CaseFirstInstance_TheThirdName,#Case_CaseSecondInstance_TheThirdName,#Case_CaseLastInstance_TheThirdName,#Case_CaseExecution_TheThirdName").click(function () {
            var selectedId = $(this).attr("id").replace("Name", "");
            var selectedName = $(this).attr("id");
            caseInfo.CaseCustomer.Open(3, selectedId, selectedName);
        });

        /*确定方式*/
        $("#Case_CaseFirstInstance_DetermineTheway,#Case_CaseSecondInstance_DetermineTheway,#Case_CaseLastInstance_DetermineTheway,#Case_CaseExecution_DetermineTheway").unbind("click");
        $("#Case_CaseFirstInstance_DetermineTheway,#Case_CaseSecondInstance_DetermineTheway,#Case_CaseLastInstance_DetermineTheway,#Case_CaseExecution_DetermineTheway").click(function () {
            var tirgger = this;
            var html = $.lsCaseDetermineTheway.getCaseDetermineThewayCheckBoxListHtml();
            $(".divCaseDetermineTheway").html(html);
            //$("#hidDetermineThewayId").val("hid_" + $(tirgger).attr("id"));
            $("#hidDetermineThewayName").val($(tirgger).attr("id"));
            $("#divCaseDetermineThewayCheckBoxList").css({
                "position": "absolute",
                "left": $(this).position().left + 10,
                "top": $(this).position().top + 36,
                "z-index": 1200
            }).show();

            return false;
        });

        $("#divCaseDetermineThewayCheckBoxList").find("li").off().on("click", function (e) {

            if ($(e.target).is("lable")) {
                e.stopPropagation();
                return false;
            }

            var currentSelectedControl = $("#hidDetermineThewayName").val();

            if ($(this).attr("id") == 'btnAllUnSelected') {
                $("#" + currentSelectedControl).val('');
                return false;
            } else if ($(this).attr("id") == 'btnAllSelected') {
                $("#" + currentSelectedControl).val('');
                return false;
            }

            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedControl).val('');

            var caseDetermineTheways = '';

            $("#divCaseDetermineThewayCheckBoxList").find("input:checkbox").each(function () {
                if ($(this).attr("checked") == 'checked') {
                    caseDetermineTheways += $(this).attr("determineThewayname") + ";";
                }
            });

            $("#" + currentSelectedControl).val(caseDetermineTheways.substring(0, caseDetermineTheways.length - 1));

            e.stopPropagation();

            return true;
        });

        /*权利关系*/
        $("#Case_CaseFirstInstance_HolderOfRelationship,#Case_CaseSecondInstance_HolderOfRelationship,#Case_CaseLastInstance_HolderOfRelationship,#Case_CaseExecution_HolderOfRelationship").unbind("click");
        $("#Case_CaseFirstInstance_HolderOfRelationship,#Case_CaseSecondInstance_HolderOfRelationship,#Case_CaseLastInstance_HolderOfRelationship,#Case_CaseExecution_HolderOfRelationship").click(function () {
            var tirgger = this;
            var html = $.lsCaseHolderOfRelationship.getCaseHolderOfRelationshipListHtml();
            $(".divCaseHolderOfRelationship").html(html);
            //$("#hidHolderOfRelationshipId").val("hid_" + $(tirgger).attr("id"));
            $("#hidCaseHolderOfRelationshipName").val($(tirgger).attr("id"));
            $("#divCaseHolderOfRelationshipList").css({
                "position": "absolute",
                "left": $(this).position().left + 10,
                "top": $(this).position().top + 36,
                "z-index": 1200
            }).show();

            return false;
        });

        $("#divCaseHolderOfRelationshipList").find("li").off().on("click", function (e) {
            //var userId = $(this).find("a").attr("name");
            var userName = $(this).find("a").text();
            var currentSelectedControl = $("#hidCaseHolderOfRelationshipName").val();
            //var currentSelectedIdControl = $("#hidUserId").val();
            $("#" + currentSelectedControl).val(userName);
            //$("#" + currentSelectedIdControl).val(userId);
            $("#divCaseHolderOfRelationshipList").hide();
        });

        /*关联关系*/
        $("#Case_CaseFirstInstance_TheThirdRelationship,#Case_CaseSecondInstance_TheThirdRelationship,#Case_CaseLastInstance_TheThirdRelationship,#Case_CaseExecution_TheThirdRelationship").unbind("click");
        $("#Case_CaseFirstInstance_TheThirdRelationship,#Case_CaseSecondInstance_TheThirdRelationship,#Case_CaseLastInstance_TheThirdRelationship,#Case_CaseExecution_TheThirdRelationship").click(function () {
            var tirgger = this;
            var html = $.lsCaseTheThirdRelationship.getCaseTheThirdRelationshipListHtml();
            $(".divCaseTheThirdRelationship").html(html);
            //$("#hidTheThirdRelationshipId").val("hid_" + $(tirgger).attr("id"));
            $("#hidCaseTheThirdRelationshipName").val($(tirgger).attr("id"));
            $("#divCaseTheThirdRelationshipList").css({
                "position": "absolute",
                "left": $(this).position().left + 10,
                "top": $(this).position().top + 36,
                "z-index": 1200
            }).show();

            return false;
        });

        $("#divCaseTheThirdRelationshipList").find("li").off().on("click", function (e) {
            //var userId = $(this).find("a").attr("name");
            var userName = $(this).find("a").text();
            var currentSelectedControl = $("#hidCaseTheThirdRelationshipName").val();
            //var currentSelectedIdControl = $("#hidUserId").val();
            $("#" + currentSelectedControl).val(userName);
            //$("#" + currentSelectedIdControl).val(userId);
            $("#divCaseTheThirdRelationshipList").hide();
        });

        /*经办律师,代理律师,助理律师,当前处理人*/
        $("#Case_CaseFirstInstance_CaseLawyerName," +
            "#Case_CaseInvestigation_InvestigatorName," +
            "#Case_CaseFirstInstance_AssistantName," +
            "#Case_CaseBasicInfo_CaseOfficerName," +
            "#Case_CaseSecondInstance_CaseLawyerName," +
            "#Case_CaseSecondInstance_AssistantName," +
            "#Case_CaseLastInstance_CaseLawyerName," +
            "#Case_CaseLastInstance_AssistantName," +
            "#Case_CaseExecution_CaseLawyerName," +
            "#Case_CaseExecution_AssistantName," +
            "#Case_CaseBasicInfo_CaseOriginPeopleName").unbind("click");

        $("#Case_CaseFirstInstance_CaseLawyerName," +
           "#Case_CaseInvestigation_InvestigatorName," +
           "#Case_CaseFirstInstance_AssistantName," +
           "#Case_CaseBasicInfo_CaseOfficerName," +
           "#Case_CaseSecondInstance_CaseLawyerName," +
           "#Case_CaseSecondInstance_AssistantName," +
           "#Case_CaseLastInstance_CaseLawyerName," +
           "#Case_CaseLastInstance_AssistantName," +
           "#Case_CaseExecution_CaseLawyerName," +
           "#Case_CaseExecution_AssistantName," +
           "#Case_CaseBasicInfo_CaseOriginPeopleName").bind("click", function () {
               $("#hidUserId").val($(this).attr("id").replace("Name", ""));
               $("#hidUserName").val($(this).attr("id"));
               $("#divUserList").find("input:checkbox").each(function () {
                   $(this).removeAttr("checked");
               });

               $("#divUserList").off().css({
                   "position": "absolute",
                   "left": $(this).position().left + 10,
                   "top": $(this).position().top + 36,
                   "z-index": 1200
               }).show();
               return false;
           });

        var caseFirstInstanceCaseLawyer = new AssociateUser($("#divAssociateUserList"), $("#Case_CaseFirstInstance_CaseLawyer"), $("#Case_CaseFirstInstance_CaseLawyerName"), null);
        var caseInvestigationCaseInvestigator = new AssociateUser($("#divAssociateUserList"), $("#Case_CaseInvestigation_Investigator"), $("#Case_CaseInvestigation_InvestigatorName"), null);
        var caseFirstInstanceCaseAssistant = new AssociateUser($("#divAssociateUserList"), $("#Case_CaseFirstInstance_Assistant"), $("#Case_CaseFirstInstance_AssistantName"), null);
        var caseBasicInfoCaseCaseOfficer = new AssociateUser($("#divAssociateUserList"), $("#Case_CaseBasicInfo_CaseOfficer"), $("#Case_CaseBasicInfo_CaseOfficerName"), null);
        var caseSecondInstanceCaseLawyer = new AssociateUser($("#divAssociateUserList"), $("#Case_CaseSecondInstance_CaseLawyer"), $("#Case_CaseSecondInstance_CaseLawyerName"), null);
        var caseSecondInstanceAssistant = new AssociateUser($("#divAssociateUserList"), $("#Case_CaseSecondInstance_Assistant"), $("#Case_CaseSecondInstance_AssistantName"), null);
        var caseLastInstanceCaseLawyer = new AssociateUser($("#divAssociateUserList"), $("#Case_CaseLastInstance_CaseLawyer"), $("#Case_CaseLastInstance_CaseLawyerName"), null);
        var caseLastInstanceAssistant = new AssociateUser($("#divAssociateUserList"), $("#Case_CaseLastInstance_Assistant"), $("#Case_CaseLastInstance_AssistantName"), null);
        var caseExecutionCaseLawyer = new AssociateUser($("#divAssociateUserList"), $("#Case_CaseExecution_CaseLawyer"), $("#Case_CaseExecution_CaseLawyerName"), null);
        var caseExecutionCaseAssistant = new AssociateUser($("#divAssociateUserList"), $("#Case_CaseExecution_Assistant"), $("#Case_CaseExecution_AssistantName"), null);
        var caseBasicInfoCaseOriginPeople = new AssociateUser($("#divAssociateUserList"), $("#Case_CaseBasicInfo_CaseOriginPeople"), $("#Case_CaseBasicInfo_CaseOriginPeopleName"), null);


        $("#divUserList").unbind("click");
        $("#divUserList").find("li").click(function (e) {
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

        $("#divUserList").unbind("click");
        $("#divUserList").find("li").click(function (e) {
            if ($(e.target).is("lable")) {
                e.stopPropagation();
                return false;
            }
            var currentSelectedControl = $("#hidUserName").val();
            var currentSelectedIdControl = $("#hidUserId").val();

            if ($(this).attr("id") == 'btnAllUnSelected') {
                $("#" + currentSelectedControl).val('');
                return false;
            }
            else if ($(this).attr("id") == 'btnAllSelected') {
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

        if (parseInt($("#CaseId").val()) > 0) {
            $("#Case_CaseBasicInfo_CaseTypeId").attr("disabled", "disabled");
        }

        $("#btnCaseCreateNew").removeAttr("disabled");
        $("#btnCaseCreateUpdate").removeAttr("disabled");
        $("#btnCaseRenewal").attr("disabled", "disabled");
    },

    CreateCompletedNew: function () {
        var caseId = {
            caseId: 0
        }
        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/CaseInfo", caseId, function (response) {
            $(".viewFramework-product-body").html("");
            if (!response.IsSuccess) {
                $.showModalMessageBox(response.Message);
                return false;
            }
            if (response.Data == null) {
                return false;
            }
            $(".viewFramework-product-body").html(response.Data);

            enableEditForm = true;
            caseInfo.Edit();

        });
    },

    InitCaseBasic: function (caseLevelId) {

        var data = {
            caseId: $("#CaseId").val(),
            caseLevelId: caseLevelId,
        }
        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/GetCaseBasic", data, function (response) {
            if (response.IsSuccess) {
                $.openLoading();
                $("#casebasicInfo").empty();
                $("#casebasicInfo").html(response.Data);
                caseInfo.ViewOnly();
                caseInfo.ResetSize();
                caseInfo.InputBindEvent();
                if (caseLevelId == 1) {
                    //调查取证
                    caseInfo.CaseInvestigation.BindEvent();

                } else if (caseLevelId == 2) {
                    //一审                       
                    caseInfo.CaseFirstInstance.BindEvent();

                } else if (caseLevelId == 4) {
                    //二审
                    caseInfo.CaseSecondInstance.BindEvent();
                } else if (caseLevelId == 8) {
                    //再审
                    caseInfo.CaseLastInstance.BindEvent();
                } else if (caseLevelId == 16) {
                    //执行
                    caseInfo.CaseExecution.BindEvent();
                }

                if (enableEditForm) {
                    caseInfo.Edit();
                }

                $.closeLoading();
            }
        });
    },

    InitCaseType: function () {

        var caseTypeId = $("#Case_CaseBasicInfo_CaseTypeId").val();

        $("#lblCaseTypeIdName").html($("#Case_CaseBasicInfo_CaseTypeId").find("option:selected").text() + "名称：");

        var casePhaseId = $("#Case_CaseBasicInfo_CasePhaseId").val();

        $("#Case_CaseBasicInfo_CasePhaseId").empty();

        $.each(GV_LS.CaseTypes, function (i, c) {
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

    CreateUpdateBefore: function () {
        var data = { caseId: $("#CaseId").val() };
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

        caseInfo.Close();

        caseInfo.CreateUpdate(true);
    },

    CreateUpdate: function (isSubmit) {
        try {
            var data = {};

            if ($("#Case_CasePart_Cause").val() == '') {
                $.showModalMessageBox("请选择案由.");
                return false;
            }

            if ($("#Case_CasePart_Court").val() == '') {
                $.showModalMessageBox("请选择受诉法院.");
                return false;
            }


            if ($("#Case_CaseBasicInfo_CaseOfficer").val() == '') {
                $.showModalMessageBox("请选择处理人.");
                return false;
            }


            if ($("#Case_CaseBasicInfo_Deadline").val() == '') {
                $.showModalMessageBox("请输入截止日期.");
                return false;
            }

            if ($("#Case_CaseBasicInfo_ReminderDate").val() != '' &&
                $("#Case_CaseBasicInfo_Deadline").val() >= $("#Case_CaseBasicInfo_ReminderDate").val()) {
                $.showModalMessageBox("截止日期应小于最近提醒日期.");
                return false;
            }

            if ($("#Case_CasePart_CaseIndicter").val() == '') {
                $.showModalMessageBox("请选择原告.");
                return false;
            }

            if ($("#Case_CasePart_CaseIndictee").val() == '') {
                $.showModalMessageBox("请选择被告.");
                return false;
            }

            data["Case.CaseBasicInfo.CaseId"] = $("#CaseId").val();
            data["Case.CaseBasicInfo.CaseNo"] = $("#Case_CaseBasicInfo_CaseNo").val();
            data["Case.CaseBasicInfo.CompanyId"] = $("#Case_CaseBasicInfo_CompanyId").val();
            data["Case.CaseBasicInfo.CaseTypeId"] = $("#Case_CaseBasicInfo_CaseTypeId").val();
            data["Case.CaseBasicInfo.CasePhaseId"] = $("#Case_CaseBasicInfo_CasePhaseId").val();
            data["Case.CaseBasicInfo.CaseOriginPeople"] = $("#Case_CaseBasicInfo_CaseOriginPeople").val();
            data["Case.CaseBasicInfo.CaseSubmitter"] = $("#Case_CaseBasicInfo_CaseSubmitter").val();
            data["Case.CaseBasicInfo.CaseOfficer"] = $("#Case_CaseBasicInfo_CaseOfficer").val();
            data["Case.CaseBasicInfo.Deadline"] = $("#Case_CaseBasicInfo_Deadline").val();

            data["Case.CasePart.CaseId"] = $("#CaseId").val();
            data["Case.CasePart.CaseNo"] = $("#Case_CaseBasicInfo_CaseNo").val();
            data["Case.CasePart.CompanyId"] = $("#Case_CaseBasicInfo_CompanyId").val();
            data["Case.CasePart.CaseTypeId"] = $("#Case_CaseBasicInfo_CaseTypeId").val();
            data["Case.CasePart.CasePhaseId"] = $("#Case_CaseBasicInfo_CasePhaseId").val();
            data["Case.CasePart.Cause"] = $("#Case_CasePart_Cause").val();
            data["Case.CasePart.CaseLawyer"] = $("#Case_CasePart_CaseLawyer").val();
            data["Case.CasePart.Court"] = $("#Case_CasePart_Court").val();
            data["Case.CasePart.CourtCasetNo"] = $("#Case_CasePart_CourtCasetNo").val();
            data["Case.CasePart.CaseJudge"] = $("#Case_CasePart_CaseJudge").val();
            data["Case.CasePart.Procurator"] = $("#Case_CasePart_Procurator").val();
            data["Case.CasePart.CaseLevel"] = $("#Case_CasePart_CaseLevel").val();
            data["Case.CasePart.CaseLawfulDate"] = $("#Case_CasePart_CaseLawfulDate").val();
            data["Case.CasePart.Assistant"] = $("#Case_CasePart_Assistant").val();
            data["Case.CasePart.CaseRegisterDate"] = $("#Case_CasePart_CaseRegisterDate").val();
            data["Case.CasePart.CaseEvidenceDate"] = $("#Case_CasePart_CaseEvidenceDate").val();
            data["Case.CasePart.TheThird"] = $("#Case_CasePart_TheThird").val();
            data["Case.CasePart.TheThirdRelationship"] = $("#Case_CasePart_TheThirdRelationship").val();
            data["Case.CasePart.CaseIndicter"] = $("#Case_CasePart_CaseIndicter").val();
            data["Case.CasePart.HolderOfRelationship"] = $("#Case_CasePart_HolderOfRelationship").val();
            data["Case.CasePart.CaseIndictee"] = $("#Case_CasePart_CaseIndictee").val();
            data["Case.CasePart.DetermineTheway"] = $("#Case_CasePart_DetermineTheway").val();

            data["isSubmit"] = isSubmit;

            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/CaseCreateUpdate", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("保存成功.");
                    caseInfo.LoadCase(response.Data.CaseBasicInfo.CaseId, $("#Case_CasePart_CaseLevel").val());
                }
                else if (response.IsRedirect) {
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

    LoadCase: function (caseInfoId, caseLevelId) {

        var caseId = {
            caseId: caseInfoId,
            caseLevelId: caseLevelId
        }
        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/CaseInfo", caseId, function (responsedata) {
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
            + "                <input class='input_time form-control' readonly unselectable='on' id='Cfg_Case_CaseBasicInfo_Deadline_Date' onfocus=\"WdatePicker({doubleCalendar:true,dateFmt:'yyyy-MM-dd'})\" type='text' >"
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
        $(function () {
            $('#divContextList,#divCaseEvents').slimScroll({
                height: '100%'
            });
        });
        $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 22);
        $("#divCaseEvents").css("height", $('.case-section-main').height() - 8);
    },

    CaseInstance: {

        /*事件绑定*/
        BindEvent: function () {
            $("#btnCaseInstanceClose,#btnCaseInstanceCancel").unbind("click");
            $("#btnCaseInstanceClose,#btnCaseInstanceCancel").bind("click", function () {
                caseInfo.CaseInstance.Close();
            });
            $("#btnCaseInstance").unbind("click");
            $("#btnCaseInstance").bind("click", function () {
                caseInfo.CaseInstance.CreateUpdate();
            });
        },

        /*新建审级*/
        Open: function () {
            //if (parseInt($("#CaseId").val()) == 0) {
            //    $.showModalMessageBox("请先保存案件基本资料.");
            //    return false;
            //}
            var data =
            {
                caseId: $("#CaseId").val(),
            };
            var url =  AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/CaseInstance";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                caseInfo.CaseInstance.BindEvent();
                $('#caseInstanceModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseInstanceModal').on('hidden.bs.modal', function () {
                    $("#caseInstanceModal").remove();
                });
            });

        },

        /*关闭*/
        Close: function () {
            $('#caseInstanceModal').modal('hide');
        },

        CreateUpdate: function () {
            var caseLevelId = $("#Case_CurrentCaseLevel").val();
            $("#liCaseLevel" + caseLevelId).css('display', 'block');
            $("#btnCaseLevel" + caseLevelId).trigger("click");
            caseInfo.CaseInstance.Close();
        }
    },

    CaseInvestigation: {

        BindEvent: function () {
            /*保存按钮*/
            $("#btnCaseCreateUpdate").unbind("click");
            $("#btnCaseCreateUpdate").bind("click", function () {
                caseInfo.CaseInvestigation.CreateUpdate(true);
            });
        },

        CreateUpdate: function (isSubmit) {
            try {
                var data = {};

                data["Case.CurrentCaseLevel"] = 1;//调查
                data["Case.CaseInvestigation.CaseInvestigationId"] = $("#Case_CaseInvestigation_CaseInvestigationId").val();
                data["Case.CaseInvestigation.CaseProsecutor"] = $("#Case_CaseInvestigation_CaseProsecutor").val();
                data["Case.CaseInvestigation.CopyrightType"] = $("#Case_CaseInvestigation_CopyrightTypeId").val();
                data["Case.CaseInvestigation.CaseAuthorizationDateFrom"] = $("#Case_CaseInvestigation_CaseAuthorizationDateFrom").val();
                data["Case.CaseInvestigation.CaseAuthorizationDateEnd"] = $("#Case_CaseInvestigation_CaseAuthorizationDateEnd").val();
                data["Case.CaseInvestigation.Investigator"] = $("#Case_CaseInvestigation_Investigator").val();
                data["Case.CaseInvestigation.InvestigateScope"] = $("#Case_CaseInvestigation_InvestigateScope").val();
                data["Case.CaseInvestigation.InvestigateDateFrom"] = $("#Case_CaseInvestigation_InvestigateDateFrom").val();
                data["Case.CaseInvestigation.InvestigateDateEnd"] = $("#Case_CaseInvestigation_InvestigateDateEnd").val();
                data["Case.CaseInvestigation.Defendant"] = $("#Case_CaseInvestigation_Defendant").val();
                data["Case.CaseInvestigation.InfringementAddress"] = $("#Case_CaseInvestigation_InfringementAddress").val();
                data["Case.CaseInvestigation.RegisteredAddress"] = $("#Case_CaseInvestigation_RegisteredAddress").val();
                data["Case.CaseInvestigation.InfringementWay"] = $("#Case_CaseInvestigation_InfringementWay").val();
                data["Case.CaseInvestigation.Notary"] = $("#Case_CaseInvestigation_Notary").val();
                data["Case.CaseInvestigation.NotarizationDate"] = $("#Case_CaseInvestigation_NotarizationDate").val();
                data["Case.CaseInvestigation.NotarialNo"] = $("#Case_CaseInvestigation_NotarialNo").val();
                data["Case.CaseInvestigation.NotarialParticulars"] = $("#Case_CaseInvestigation_NotarialParticulars").val();

                data["Case.CaseBasicInfo.CaseId"] = $("#CaseId").val();
                data["Case.CaseBasicInfo.CaseNo"] = $("#Case_CaseBasicInfo_CaseNo").val();
                data["Case.CaseBasicInfo.CauseId"] = $("#Case_CaseBasicInfo_CauseId").val();
                data["Case.CaseBasicInfo.CasePhaseId"] = $("#Case_CaseBasicInfo_CasePhaseId").val();
                data["Case.CaseBasicInfo.Deadline"] = $("#Case_CaseBasicInfo_Deadline").val();
                data["Case.CaseBasicInfo.CaseSubmitter"] = $("#Case_CaseBasicInfo_CaseSubmitter").val();
                data["Case.CaseBasicInfo.CaseOfficer"] = $("#Case_CaseBasicInfo_CaseOfficer").val();
                data["Case.CaseBasicInfo.CompanyId"] = $("#Case_CaseBasicInfo_CompanyId").val();
                data["Case.CaseBasicInfo.CaseOriginPeople"] = $("#Case_CaseBasicInfo_CaseOriginPeople").val();
                data["Case.CaseBasicInfo.ContractNo"] = $("#Case_CaseBasicInfo_ContractNo").val();


                data["isSubmit"] = isSubmit;

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/CaseCreateUpdate", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("保存成功.");

                        $("#CaseId").val(response.Data.CaseBasicInfo.CaseId);
                        $("#Case_CaseBasicInfo_CaseNo").val(response.Data.CaseBasicInfo.CaseNo);
                        $("#Case_CaseInvestigation_CaseInvestigationId").val(response.Data.CaseInvestigation.CaseInvestigationId);

                        caseInfo.CaseEvent.List();
                    }
                    else if (response.IsRedirect) {
                        window.location =  AP_ROOT + 'Home/Index';
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            } catch (e) {
                alert(e);
            }
        },
    },

    CaseFirstInstance: {

        BindEvent: function () {
            /*保存按钮*/
            $("#btnCaseCreateUpdate").unbind("click");
            $("#btnCaseCreateUpdate").bind("click", function () {
                caseInfo.CaseFirstInstance.CreateUpdate(true);
            });
        },

        CreateUpdate: function (isSubmit) {
            try {
                var data = {};

                data["Case.CurrentCaseLevel"] = 2;//调查
                data["Case.CaseFirstInstance.CaseFirstInstanceId"] = $("#Case_CaseFirstInstance_CaseFirstInstanceId").val();
                data["Case.CaseFirstInstance.CaseLawyer"] = $("#Case_CaseFirstInstance_CaseLawyer").val();
                data["Case.CaseFirstInstance.Assistant"] = $("#Case_CaseFirstInstance_Assistant").val();
                data["Case.CaseFirstInstance.CourtId"] = $("#Case_CaseFirstInstance_CourtId").val();
                data["Case.CaseFirstInstance.CaseJudge"] = $("#Case_CaseFirstInstance_CaseJudge").val();
                data["Case.CaseFirstInstance.CourtCasetNo"] = $("#Case_CaseFirstInstance_CourtCasetNo").val();
                data["Case.CaseFirstInstance.CaseRegisterDate"] = $("#Case_CaseFirstInstance_CaseRegisterDate").val();
                data["Case.CaseFirstInstance.CaseProsecutor"] = $("#Case_CaseFirstInstance_CaseProsecutor").val();
                data["Case.CaseFirstInstance.HolderOfRelationship"] = $("#Case_CaseFirstInstance_HolderOfRelationship").val();
                data["Case.CaseFirstInstance.CaseDefendant"] = $("#Case_CaseFirstInstance_CaseDefendant").val();
                data["Case.CaseFirstInstance.DetermineTheway"] = $("#Case_CaseFirstInstance_DetermineTheway").val();
                data["Case.CaseFirstInstance.CaseLawfulDate"] = $("#Case_CaseFirstInstance_CaseLawfulDate").val();

                data["Case.CaseFirstInstance.TheThird"] = $("#Case_CaseFirstInstance_TheThird").val();
                data["Case.CaseFirstInstance.TheThirdRelationship"] = $("#Case_CaseFirstInstance_TheThirdRelationship").val();
                data["Case.CaseFirstInstance.CaseCustomerAs"] = $("#Case_CaseFirstInstance_CaseCustomerTypeId").val();

                data["Case.CaseBasicInfo.CaseId"] = $("#CaseId").val();
                data["Case.CaseBasicInfo.CaseNo"] = $("#Case_CaseBasicInfo_CaseNo").val();
                data["Case.CaseBasicInfo.CauseId"] = $("#Case_CaseBasicInfo_CauseId").val();
                data["Case.CaseBasicInfo.CasePhaseId"] = $("#Case_CaseBasicInfo_CasePhaseId").val();
                data["Case.CaseBasicInfo.Deadline"] = $("#Case_CaseBasicInfo_Deadline").val();
                data["Case.CaseBasicInfo.CaseSubmitter"] = $("#Case_CaseBasicInfo_CaseSubmitter").val();
                data["Case.CaseBasicInfo.CaseOfficer"] = $("#Case_CaseBasicInfo_CaseOfficer").val();
                data["Case.CaseBasicInfo.CompanyId"] = $("#Case_CaseBasicInfo_CompanyId").val();
                data["Case.CaseBasicInfo.CaseOriginPeople"] = $("#Case_CaseBasicInfo_CaseOriginPeople").val();

                data["isSubmit"] = isSubmit;

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/CaseCreateUpdate", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("保存成功.");

                        $("#CaseId").val(response.Data.CaseBasicInfo.CaseId);
                        $("#Case_CaseBasicInfo_CaseNo").val(response.Data.CaseBasicInfo.CaseNo);
                        $("#Case_CaseFirstInstance_CaseFirstInstanceId").val(response.Data.CaseFirstInstance.CaseFirstInstanceId);

                        caseInfo.CaseEvent.List();
                    }
                    else if (response.IsRedirect) {
                        window.location =  AP_ROOT + 'Home/Index';
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            } catch (e) {
                alert(e);
            }
        },
    },

    CaseSecondInstance: {

        BindEvent: function () {
            /*保存按钮*/
            $("#btnCaseCreateUpdate").unbind("click");
            $("#btnCaseCreateUpdate").bind("click", function () {
                caseInfo.CaseSecondInstance.CreateUpdate(true);
            });
        },

        CreateUpdate: function (isSubmit) {
            try {
                var data = {};

                data["Case.CaseSecondInstance.CaseSecondInstanceId"] = $("#Case_CaseSecondInstance_CaseSecondInstanceId").val();
                data["Case.CaseSecondInstance.CourtId"] = $("#Case_CaseSecondInstance_CourtId").val();
                data["Case.CaseSecondInstance.CaseJudge"] = $("#Case_CaseSecondInstance_CaseJudge").val();
                data["Case.CaseSecondInstance.CourtCasetNo"] = $("#Case_CaseSecondInstance_CourtCasetNo").val();
                data["Case.CaseSecondInstance.FirstInstanceDeliveryDate"] = $("#Case_CaseSecondInstance_FirstInstanceDeliveryDate").val();
                data["Case.CaseSecondInstance.CaseRegisterDate"] = $("#Case_CaseSecondInstance_CaseRegisterDate").val();
                data["Case.CaseSecondInstance.CaseLawyer"] = $("#Case_CaseSecondInstance_CaseLawyer").val();
                data["Case.CaseSecondInstance.Assistant"] = $("#Case_CaseSecondInstance_Assistant").val();
                data["Case.CaseSecondInstance.CaseProsecutor"] = $("#Case_CaseSecondInstance_CaseProsecutor").val();
                data["Case.CaseSecondInstance.HolderOfRelationship"] = $("#Case_CaseSecondInstance_HolderOfRelationship").val();
                data["Case.CaseSecondInstance.CaseDefendant"] = $("#Case_CaseSecondInstance_CaseDefendant").val();
                data["Case.CaseSecondInstance.DetermineTheway"] = $("#Case_CaseSecondInstance_DetermineTheway").val();
                data["Case.CaseSecondInstance.CaseLawfulDate"] = $("#Case_CaseSecondInstance_CaseLawfulDate").val();
				
				data["Case.CaseSecondInstance.TheThird"] = $("#Case_CaseSecondInstance_TheThird").val();
                data["Case.CaseSecondInstance.TheThirdRelationship"] = $("#Case_CaseSecondInstance_TheThirdRelationship").val();
                data["Case.CaseSecondInstance.CaseCustomerAs"] = $("#Case_CaseSecondInstance_CaseCustomerTypeId").val();

                data["Case.CaseSecondInstance.CaseProsecutorLitigationStatus"] = $("#Case_CaseSecondInstance_CaseProsecutorLitigationStatusId").val();
                data["Case.CaseSecondInstance.CaseDefendantLitigationStatus"] = $("#Case_CaseSecondInstance_CaseDefendantLitigationStatusId").val();

                data["Case.CurrentCaseLevel"] = 4;//调查

                data["Case.CaseBasicInfo.CaseId"] = $("#CaseId").val();
                data["Case.CaseBasicInfo.CompanyId"] = $("#Case_CaseBasicInfo_CompanyId").val();
                data["Case.CaseBasicInfo.CaseNo"] = $("#Case_CaseBasicInfo_CaseNo").val();
                data["Case.CaseBasicInfo.CauseId"] = $("#Case_CaseBasicInfo_CauseId").val();
                data["Case.CaseBasicInfo.CasePhaseId"] = $("#Case_CaseBasicInfo_CasePhaseId").val();
                data["Case.CaseBasicInfo.Deadline"] = $("#Case_CaseBasicInfo_Deadline").val();
                data["Case.CaseBasicInfo.CaseSubmitter"] = $("#Case_CaseBasicInfo_CaseSubmitter").val();
                data["Case.CaseBasicInfo.CaseOfficer"] = $("#Case_CaseBasicInfo_CaseOfficer").val();
                data["Case.CaseBasicInfo.CaseOriginPeople"] = $("#Case_CaseBasicInfo_CaseOriginPeople").val();

                data["isSubmit"] = isSubmit;

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/CaseCreateUpdate", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("保存成功.");

                        $("#CaseId").val(response.Data.CaseBasicInfo.CaseId);
                        $("#Case_CaseBasicInfo_CaseNo").val(response.Data.CaseBasicInfo.CaseNo);
                        $("#Case_CaseSecondInstance_CaseSecondInstanceId").val(response.Data.CaseSecondInstance.CaseSecondInstanceId);

                        caseInfo.CaseEvent.List();
                    }
                    else if (response.IsRedirect) {
                        window.location =  AP_ROOT +  'Home/Index';
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            } catch (e) {
                alert(e);
            }
        },
    },

    CaseLastInstance: {

        BindEvent: function () {
            /*保存按钮*/
            $("#btnCaseCreateUpdate").unbind("click");
            $("#btnCaseCreateUpdate").bind("click", function () {
                caseInfo.CaseLastInstance.CreateUpdate(true);
            });
        },

        CreateUpdate: function (isSubmit) {
            try {
                var data = {};

                data["Case.CaseLastInstance.CourtId"] = $("#Case_CaseLastInstance_CourtId").val();
                data["Case.CaseLastInstance.CaseLastInstanceId"] = $("#Case_CaseLastInstance_CaseLastInstanceId").val();
                data["Case.CaseLastInstance.CaseJudge"] = $("#Case_CaseLastInstance_CaseJudge").val();
                data["Case.CaseLastInstance.CourtCasetNo"] = $("#Case_CaseLastInstance_CourtCasetNo").val();
                data["Case.CaseLastInstance.LegalRedTapeEffectiveDate"] = $("#Case_CaseLastInstance_LegalRedTapeEffectiveDate").val();
                data["Case.CaseLastInstance.CaseRegisterDate"] = $("#Case_CaseLastInstance_CaseRegisterDate").val();
                data["Case.CaseLastInstance.CaseLawyer"] = $("#Case_CaseLastInstance_CaseLawyer").val();
                data["Case.CaseLastInstance.Assistant"] = $("#Case_CaseLastInstance_Assistant").val();
                data["Case.CaseLastInstance.CaseProsecutor"] = $("#Case_CaseLastInstance_CaseProsecutor").val();
                data["Case.CaseLastInstance.HolderOfRelationship"] = $("#Case_CaseLastInstance_HolderOfRelationship").val();
                data["Case.CaseLastInstance.CaseDefendant"] = $("#Case_CaseLastInstance_CaseDefendant").val();
                data["Case.CaseLastInstance.DetermineTheway"] = $("#Case_CaseLastInstance_DetermineTheway").val();
                data["Case.CaseLastInstance.CaseLawfulDate"] = $("#Case_CaseLastInstance_CaseLawfulDate").val();

				data["Case.CaseLastInstance.TheThird"] = $("#Case_CaseLastInstance_TheThird").val();
                data["Case.CaseLastInstance.TheThirdRelationship"] = $("#Case_CaseLastInstance_TheThirdRelationship").val();
                data["Case.CaseLastInstance.CaseCustomerAs"] = $("#Case_CaseLastInstance_CaseCustomerTypeId").val();

                data["Case.CaseLastInstance.CaseProsecutorLitigationStatus"] = $("#Case_CaseLastInstance_CaseProsecutorLitigationStatusId").val();
                data["Case.CaseLastInstance.CaseDefendantLitigationStatus"] = $("#Case_CaseLastInstance_CaseDefendantLitigationStatusId").val();
 
                data["Case.CurrentCaseLevel"] = 8;//再审

                data["Case.CaseBasicInfo.CaseId"] = $("#CaseId").val();
                data["Case.CaseBasicInfo.CompanyId"] = $("#Case_CaseBasicInfo_CompanyId").val();
                data["Case.CaseBasicInfo.CaseNo"] = $("#Case_CaseBasicInfo_CaseNo").val();
                data["Case.CaseBasicInfo.CauseId"] = $("#Case_CaseBasicInfo_CauseId").val();
                data["Case.CaseBasicInfo.CasePhaseId"] = $("#Case_CaseBasicInfo_CasePhaseId").val();
                data["Case.CaseBasicInfo.Deadline"] = $("#Case_CaseBasicInfo_Deadline").val();
                data["Case.CaseBasicInfo.CaseSubmitter"] = $("#Case_CaseBasicInfo_CaseSubmitter").val();
                data["Case.CaseBasicInfo.CaseOfficer"] = $("#Case_CaseBasicInfo_CaseOfficer").val();
                data["Case.CaseBasicInfo.CaseOriginPeople"] = $("#Case_CaseBasicInfo_CaseOriginPeople").val();

                data["isSubmit"] = isSubmit;

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/CaseCreateUpdate", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("保存成功.");

                        $("#CaseId").val(response.Data.CaseBasicInfo.CaseId);
                        $("#Case_CaseBasicInfo_CaseNo").val(response.Data.CaseBasicInfo.CaseNo);
                        $("#Case_CaseLastInstance_CaseLastInstanceId").val(response.Data.CaseLastInstance.CaseLastInstanceId);

                        caseInfo.CaseEvent.List();
                    }
                    else if (response.IsRedirect) {
                        window.location =  AP_ROOT +  'Home/Index';
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            } catch (e) {
                alert(e);
            }
        },
    },

    CaseExecution: {

        BindEvent: function () {
            /*保存按钮*/
            $("#btnCaseCreateUpdate").unbind("click");
            $("#btnCaseCreateUpdate").bind("click", function () {
                caseInfo.CaseExecution.CreateUpdate(true);
            });
        },

        CreateUpdate: function (isSubmit) {
            try {
                var data = {};

                data["Case.CaseExecution.CaseExecutionId"] = $("#Case_CaseExecution_CaseExecutionId").val();
                data["Case.CaseExecution.CourtId"] = $("#Case_CaseExecution_CourtId").val();
                data["Case.CaseExecution.CaseJudge"] = $("#Case_CaseExecution_CaseJudge").val();
                data["Case.CaseExecution.CourtCasetNo"] = $("#Case_CaseExecution_CourtCasetNo").val();
                data["Case.CaseExecution.LegalRedTapeEffectiveDate"] = $("#Case_CaseExecution_LegalRedTapeEffectiveDate").val();
                data["Case.CaseBasicInfo.CasePhaseId"] = $("#Case_CaseBasicInfo_CasePhaseId").val();
                data["Case.CaseExecution.CaseRegisterDate"] = $("#Case_CaseExecution_CaseRegisterDate").val();
                data["Case.CaseExecution.CaseLawyer"] = $("#Case_CaseExecution_CaseLawyer").val();
                data["Case.CaseExecution.Assistant"] = $("#Case_CaseExecution_Assistant").val();
                data["Case.CaseExecution.CaseProsecutor"] = $("#Case_CaseExecution_CaseProsecutor").val();
                data["Case.CaseExecution.HolderOfRelationship"] = $("#Case_CaseExecution_HolderOfRelationship").val();
                data["Case.CaseExecution.CaseDefendant"] = $("#Case_CaseExecution_CaseDefendant").val();
                data["Case.CaseExecution.DetermineTheway"] = $("#Case_CaseExecution_DetermineTheway").val();
                data["Case.CaseExecution.CaseLawfulDate"] = $("#Case_CaseExecution_CaseLawfulDate").val();
                data["Case.CaseExecution.PropertyClues"] = $("#Case_CaseExecution_PropertyClues").val();
				
				data["Case.CaseExecution.TheThird"] = $("#Case_CaseExecution_TheThird").val();
                data["Case.CaseExecution.TheThirdRelationship"] = $("#Case_CaseExecution_TheThirdRelationship").val();
                data["Case.CaseExecution.CaseCustomerAs"] = $("#Case_CaseExecution_CaseCustomerTypeId").val();

                data["Case.CaseExecution.CaseProsecutorLitigationStatus"] = $("#Case_CaseExecution_CaseProsecutorLitigationStatusId").val();
                data["Case.CaseExecution.CaseDefendantLitigationStatus"] = $("#Case_CaseExecution_CaseDefendantLitigationStatusId").val();


                data["Case.CurrentCaseLevel"] = 16;//再审

                data["Case.CaseBasicInfo.CaseId"] = $("#CaseId").val();
                data["Case.CaseBasicInfo.CompanyId"] = $("#Case_CaseBasicInfo_CompanyId").val();
                data["Case.CaseBasicInfo.CaseNo"] = $("#Case_CaseBasicInfo_CaseNo").val();
                data["Case.CaseBasicInfo.CauseId"] = $("#Case_CaseBasicInfo_CauseId").val();
                data["Case.CaseBasicInfo.CasePhaseId"] = $("#Case_CaseBasicInfo_CasePhaseId").val();
                data["Case.CaseBasicInfo.Deadline"] = $("#Case_CaseBasicInfo_Deadline").val();
                data["Case.CaseBasicInfo.CaseSubmitter"] = $("#Case_CaseBasicInfo_CaseSubmitter").val();
                data["Case.CaseBasicInfo.CaseOfficer"] = $("#Case_CaseBasicInfo_CaseOfficer").val();
                data["Case.CaseBasicInfo.CaseOriginPeople"] = $("#Case_CaseBasicInfo_CaseOriginPeople").val();

                data["isSubmit"] = isSubmit;

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/CaseCreateUpdate", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("保存成功.");

                        $("#CaseId").val(response.Data.CaseBasicInfo.CaseId);
                        $("#Case_CaseBasicInfo_CaseNo").val(response.Data.CaseBasicInfo.CaseNo);
                        $("#Case_CaseExecution_CaseExecutionId").val(response.Data.CaseExecution.CaseExecutionId);

                        caseInfo.CaseEvent.List();

                    }
                    else if (response.IsRedirect) {
                        window.location =  AP_ROOT +  'Home/Index';
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            } catch (e) {
                alert(e);
            }
        },
    },

    CaseCause: {

        Open: function () {
            var data = { caseId: $("#CaseId").val() };
            var url =  AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseCause/CaseCause";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                caseInfo.CaseCause.Init();
                $('#caseCauseModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseCauseModal').on('hidden.bs.modal', function () {
                    $("#caseCauseModal").remove();
                });
            });
        },

        Close: function () {
            $('#caseCauseModal').modal('hide');
        },

        Init: function () {
            caseInfo.CaseCause.BulidTreeView();
            caseInfo.CaseCause.BindEvent();
        },

        BindEvent: function () {
            $("#btnCaseCauseClose,#btnCaseCauseCancel").unbind("click");
            $("#btnCaseCauseClose,#btnCaseCauseCancel").click(function () {
                caseInfo.CaseCause.Close();
            });

            $("#btnCaseCause").unbind("click");
            $("#btnCaseCause").click(function () {
                caseInfo.CaseCause.Selected();
            });
        },

        BulidTreeView: function () {
            var roleId = {
                roleId: $("#RoleId").val()
            };

            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseCause/GetCaseCauses", roleId, function (response) {
                if (response.IsSuccess) {

                    $('#treeview').treeview({
                        data: response.Data, // 数据源
                        showCheckbox: true, //是否显示复选框
                        highlightSelected: false, //是否高亮选中
                        //nodeIcon: 'glyphicon glyphicon-user',    //节点上的图标
                        nodeIcon: '',
                        emptyIcon: 'icon expand-icon glyphicon glyphicon-minus', //没有子节点的节点图标
                        multiSelect: false, //多选
                        onNodeChecked: function (event, data) {
                            //if (data.parentId != null) {
                            //    $('#treeview').treeview('checkNode', [data.parentId, { silent: true }]);
                            //}
                            //if (data.nodes != null) {
                            //    $.each(data.nodes, function (i, c) {
                            //        $('#treeview').treeview('checkNode', [c.nodeId, { silent: true }]);
                            //    });
                            //}
                        },
                        onNodeUnchecked: function (event, data) {
                            //if (data.nodes != null) {
                            //    $.each(data.nodes, function (i, c) {
                            //        $('#treeview').treeview('uncheckNode', [c.nodeId, { silent: true }]);
                            //    });
                            //}
                        },
                        onNodeSelected: function (event, data) {
                        }
                    });
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        Selected: function () {
            var nodes = $('#treeview').treeview('getChecked');
            var dataIds = new Array();
            var dataNames = new Array();

            if (nodes != null) {
                $.each(nodes, function (i) {
                    dataIds.push(nodes[i].nodeOriginalId);
                    dataNames.push(nodes[i].text);
                });

                if (dataIds.length > 3) {
                    $.showModalMessageBox("案由不能多于3条.");
                    return false;
                }
                $("#Case_CaseBasicInfo_CauseId").empty();
                $("#Case_CaseBasicInfo_CauseName").empty();
                $("#Case_CaseBasicInfo_CauseId").val(dataIds.join(";"));
                $("#Case_CaseBasicInfo_CauseName").val(dataNames.join(";"));
                caseInfo.CaseCause.Close();
            }
        },
    },

    /*法院*/
    CaseCourt: {

        Open: function (selectedId, selectedName) {
            var data = { caseId: $("#CaseId").val() };
            var url =  AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseCourt/CaseCourtSelected";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                caseInfo.CaseCourt.Init();

                $("#selectedId").val(selectedId);
                $("#selectedName").val(selectedName);
                $('#caseCourtModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseCourtModal').on('hidden.bs.modal', function () {
                    $("#caseCourtModal").remove();
                });

                $.fn.modal.Constructor.prototype.enforceFocus = function () {
                    $("#SearchCondition_CourtName").focus();
                };
            });
        },

        Close: function () {
            $('#caseCourtModal').modal('hide');
        },

        Init: function () {
            caseInfo.CaseCourt.List();
            caseInfo.CaseCourt.BindEvent();
        },

        BindEvent: function () {
            $("#btnCaseCourtClose,#btnCaseCourtCancle").unbind("click");
            $("#btnCaseCourtClose,#btnCaseCourtCancle").click(function () {
                caseInfo.CaseCourt.Close();
            });

            $("#btnCaseCourtConfirm").unbind("click");
            $("#btnCaseCourtConfirm").click(function () {
                caseInfo.CaseCourt.Selected();
            });

            $("#chkCourtAll").unbind("click");
            $("#chkCourtAll").click(function () {
                caseInfo.CaseCourt.SelectedAll(this);
            });

            $("#chkCourtAll").unbind("click");
            $("#chkCourtAll").bind("click", function () {
                caseInfo.CaseCourt.SelectedAll(this);
            });

            $("#btnCourtSearch").unbind("click");
            $("#btnCourtSearch").bind("click", function () {
                caseInfo.CaseCourt.List();
            });

            $("#SearchCondition_CourtName").unbind("keypress");
            $("#SearchCondition_CourtName").bind("keypress", function (e) {
                if (e.which == 13) {
                    if ($("#SearchCondition_CourtName").val() == '')
                        return false;
                    caseInfo.CaseCourt.List();
                    return false;
                }
            });
        },

        SelectedAll: function (e) {
            if ($(e).prop("checked") == true) {
                $.checkbox.all("chkCourtId");
            } else {
                $.checkbox.not("chkCourtId");
            }
        },

        Selected: function(e) {
            var courtIds = $.checkbox.vals("chkCourtId");

            var courtNames = [];
            $("input[name=chkCourtId]:checked").each(
                function(i) { courtNames[i] = $(this).attr("courtName"); }
            );

            caseInfo.CaseCourt.Close();
            if (courtIds.length == 0) {
                return false;
            }
            var selectedId = $("#selectedId").val();
            var selectedName = $("#selectedName").val();
            $("#" + selectedId).empty();
            $("#" + selectedName).empty();
            $("#" + selectedId).val(courtIds.join(";"));
            $("#" + selectedName).val(courtNames.join(";"));
        },

        List: function () {
            $("#caseCourtListForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseCourt/CaseCourtList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblCourtList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.Courts, function (i, e) {

                            if ($.inArray(e.CourtId, response.Data.SelectedCourts) > -1) {
                                $("tbody", "#tblCourtList").addRow("<input type='checkbox' checked name='chkCourtId' class='ng-pristine ng-valid' value='" + e.CourtId + "' courtName='" + e.CourtName + "'>",
                                    e.CourtCode, e.CourtName, e.DistrictCode, e.DistrictName,
                                    e.CourtType);
                            } else {
                                $("tbody", "#tblCourtList").addRow("<input type='checkbox'  name='chkCourtId' class='ng-pristine ng-valid' value='" + e.CourtId + "' courtName='" + e.CourtName + "'>",
                                          e.CourtCode, e.CourtName, e.DistrictCode, e.DistrictName,
                                          e.CourtType);
                            }
                        });

                        $("tfoot", "#tblCourtList").show();

                        $(".pull-right.page-box.courts").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: caseInfo.CaseCourt.List,
                            callBackArgs: null
                        });
                    } else {
                        $("tfoot", "#tblCourtList").hide();
                    }
                }
            });
        },
    },

    /*客户*/
    CaseCustomer: {
        //加载客户
        List: function (customerIds) {
            var data = { customerIds: customerIds };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/CaseCustomerList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $(".casecustomers").empty();
                    $(".casecustomers").html(response.Data);
                    $.closeLoading();
                }
            }, true);
        },

        BindEvent: function () {

            $("#SearchCondition_CustomerName").off().on("keypress", function (e) {
                if (e.which == 13) {
                    if ($("#SearchCondition_CustomerName").val() == '')
                        return false;
                    caseInfo.CaseCustomer.SelectedList();
                    return false;
                }
            });

            $("#btnCustomerClose,#btnCustomerCancle").off().on("click", function () {
                caseInfo.CaseCustomer.Close();
            });
            $("#btnCustomerConfirm").off().on("click", function () {
                caseInfo.CaseCustomer.CreateUpdate();
            });
            $("#chkCustomerAll").off().on("click", function () {
                caseInfo.CaseCustomer.Selected(this);
            });

            $("#btnCustomerSearch").unbind("click");
            $("#btnCustomerSearch").bind("click", function () {
                caseInfo.CaseCustomer.SelectedList();
            });
        },

        Open: function (customerTypeId,selectedId,selectedName) {
            var data = {
                caseId: $("#CaseId").val(),
                customerTypeId: customerTypeId
            };
            var url =  AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/CaseCustomerSelected";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                caseInfo.CaseCustomer.SelectedList();
                caseInfo.CaseCustomer.BindEvent();

                $("#selectedId").val(selectedId);
                $("#selectedName").val(selectedName);

                $('#caseCustomerModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseCustomerModal').on('hidden.bs.modal', function () {
                    $("#caseCustomerModal").remove();
                });

                $.fn.modal.Constructor.prototype.enforceFocus = function () {
                    $("#SearchCondition_CustomerName").focus();
                };
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
                caseInfo.CaseCustomer.Close();
                return false;
            }

            var customerNames = [];
            $("input[name=chkCustomerId]:checked").each(
                function (i) { customerNames[i] = $(this).attr("customername"); }
            );

            var selectedId = $("#selectedId").val();
            var selectedName = $("#selectedName").val();
            $("#" + selectedId).empty();
            $("#" + selectedName).empty();
            $("#" + selectedId).val(customerIds.join(";"));
            $("#" + selectedName).val(customerNames.join(";"));

            caseInfo.CaseCustomer.Close();
        },

        /*查看客户*/
        ViewCustomer: function (customerId) {

            var data = { customerId: customerId };
            var url =  AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/Customer";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                caseInfo.CaseCustomer.SelectedList();
                $('#customerModal').modal({ backdrop: 'static', keyboard: false });
                $('#customerModal').on('hidden.bs.modal', function () {
                    $("#customerModal").remove();
                });

                $(":input", "#customerForm").each(function () {
                    $(this).attr("disabled", "disabled");
                });
            });
        },

        Selected: function (e) {
            if ($(e).prop("checked") == true) {
                $.checkbox.all("chkCustomerId");
            } else {
                $.checkbox.not("chkCustomerId");
            }
        },

        SelectedList: function () {
            $("#caseCustomerListForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/CaseCustomerListSelected", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblCustomerList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.Customers, function (i, e) {

                            if ($.inArray(e.CustomerId, response.Data.SelectedCustomers) > -1) {
                                $("tbody", "#tblCustomerList").addRow("<input type='checkbox' checked name='chkCustomerId' class='ng-pristine ng-valid' value='" + e.CustomerId + "'customerName='" + e.CustomerName + "'>",
                                    e.CustomerNo, e.CustomerName, e.RegisteredAddress, e.CompanyCode,
                                    e.CustomerCode);
                            } else {
                                $("tbody", "#tblCustomerList").addRow("<input type='checkbox' name='chkCustomerId' class='ng-pristine ng-valid' value='" + e.CustomerId + "'customerName='" + e.CustomerName + "'>",
                                    e.CustomerNo, e.CustomerName, e.RegisteredAddress,
                                    e.CustomerCode);
                            }
                        });

                        $("tfoot", "#tblCustomerList").show();

                        $(".pull-right.page-box.customers").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: caseInfo.CaseCustomer.SelectedList,
                            callBackArgs: null
                        });
                    } else {
                        $("tfoot", "#tblCustomerList").hide();
                    }
                }
            });
        },
    },


    /*案件事件提醒*/
    CaseEvent: {
        List: function () {
            var data = { caseId: $("#CaseId").val() };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseEvent/CaseEventList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $(".caseevents").empty();
                    $(".caseevents").html(response.Data);
                    $.closeLoading();
                }
            }, true);
        },

        BindEvent: function () {

            $("#btnCaseEventClose,#btnCaseEventCancel").unbind("click");
            $("#btnCaseEventClose,#btnCaseEventCancel").bind("click", function () {
                caseInfo.CaseEvent.Close();
            });
            $("#btnCaseEvent").unbind("click");
            $("#btnCaseEvent").bind("click", function () {
                caseInfo.CaseEvent.CreateUpdate();
            });

            $("#btnCaseEventDelete").unbind("click");
            $("#btnCaseEventDelete").bind("click", function () {
                caseInfo.CaseEvent.Delete();
            });
        },

        /*打开案件提醒*/
        Open: function (eventId) {
            if (parseInt($("#CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }
            var data =
            {
                caseId: $("#CaseId").val(),
                companyId: $("#Case_CaseBasicInfo_CompanyId").val(),
                eventId: eventId
            };
            var url =  AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseEvent/CaseEvent";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);

                caseInfo.CaseEvent.BindEvent();
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

            $("#caseEvent").ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseEvent/CaseEventCreate", function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("保存成功.");
                    $('#caseEventModal').modal('hide');

                    caseInfo.LoadCase($("#CaseId").val());

                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        Delete: function () {
            var data = { caseEventId: $("#EventId").val() };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseEvent/CaseEventDelete", data, function (response) {
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


    /*日志*/
    CaseLog: {
        List: function () {
            var data = {
                caseId: $("#CaseId").val(),
                pageNo: $("#PageNo").val(),
                pageSize: $("#PageSize").val()
            };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseLog/CaseLogList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $("#dv_List").empty();
                    $("#dv_List").html(response.Data);

                    $("tfoot", "#tblCaseLog").show();

                    $(".pull-right.page-box.caselog").cPaging({
                        totalCount: parseInt($("#TotalCount").val()),
                        pageNo: parseInt($("#PageNo").val()),
                        pageSize: parseInt($("#PageSize").val()),
                        callBack: caseInfo.CaseLog.List,
                        callBackArgs: null
                    });

                    caseInfo.ResetSize();

                    var totalCount = parseInt($("#TotalCount").val());

                    if (totalCount > 0) {
                        $("tfoot", "#tblCaseLog").show();
                        $(".simple-grid-none-data-wrap").hide();
                    } else {
                        $("tfoot", "#tblCaseLog").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }

                    //caseInfo.CaseFee.BindEvent();
                    $.closeLoading();
                }
            });
        },

        /*打开案件日志*/
        Open: function () {
            var data =
            {
                caseId: $("#CaseId").val(),
            };

            if (parseInt($("#CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }

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

            //$('.caselog').load(url, data, function (result) {
            //    $.closeLoading();
            //    $('#caseLogModal').modal({ backdrop: 'static', keyboard: false });
            //});
        },

        /*关闭案件日志*/
        Close: function () {
            $('#caseLogModal').modal('hide');
        }
    },

    /*费用通知*/
    CaseFee: {
        /*案件费用列表*/
        List: function () {
            var data = {
                caseId: $("#CaseId").val(),
                pageNo: $("#PageNo").val(),
                pageSize: $("#PageSize").val()
            };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseFee/CaseFeeList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $("#dv_List").empty();
                    $("#dv_List").html(response.Data);

                    $("tfoot", "#tblCaseFee").show();

                    $(".pull-right.page-box.casefee").cPaging({
                        totalCount: parseInt($("#TotalCount").val()),
                        pageNo: parseInt($("#PageNo").val()),
                        pageSize: parseInt($("#PageSize").val()),
                        callBack: caseInfo.CaseFee.List,
                        callBackArgs: null
                    });

                    caseInfo.ResetSize();

                    var totalCount = parseInt($("#TotalCount").val());

                    if (totalCount > 0) {
                        $("tfoot", "#tblCaseFee").show();
                        $(".simple-grid-none-data-wrap").hide();
                    } else {
                        $("tfoot", "#tblCaseFee").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }

                    caseInfo.CaseFee.BindEvent();
                    caseInfo.CaseFee.BindMenu();

                    $.closeLoading();
                }
            }, true);
        },

        /*案件费用*/
        BindEvent: function () {

            /*费用通知*/
            $("#btnCaseFeeInformCreate").unbind("click");
            $("#btnCaseFeeInformCreate").bind("click", function () {
                caseInfo.CaseFee.OpenInform();
            });

            $("#btnCaseFeeInformCreate").unbind("click");
            $("#btnCaseFeeInformCreate").bind("click", function () {
                caseInfo.CaseFee.OpenInform();
            });

            $("#btnFeeInformClose,#btnFeeInformCancel").unbind("click");
            $("#btnFeeInformClose,#btnFeeInformCancel").bind("click", function () {
                caseInfo.CaseFee.CloseInform();
            });

            $("#DefaultCaseFee_FeeTypeName").unbind("click");
            $("#DefaultCaseFee_FeeTypeName").bind("click", function () {
                var tirgger = this;
                var caseTypeId = $("#CaseTypeId").val();
                $(".divCaseFeeTypeList").html($.lsCaseFeeType.getCaseFeeTypeListHtml(caseTypeId));

                $("#divCaseFeeTypeList").css({
                    "position": "absolute",
                    "left": $(tirgger).offsetParent().position().left + 15,
                    "top": $(tirgger).offsetParent().position().top + 32
                }).show();

                $("#hidCaseFeeTypeName").val($(tirgger).attr("id")); //名称
                $("#hidCaseFeeTypeId").val("DefaultCaseFee_FeeTypeId");//Id
                return false;
            });

            $(".CaseFeeItem_FeeTypeName").off().on("click", function () {
                var tirgger = this;
                var caseTypeId = $("#CaseTypeId").val();
                $(".divCaseFeeTypeList").html($.lsCaseFeeType.getCaseFeeTypeListHtml(caseTypeId));

                $("#divCaseFeeTypeList").css({
                    "position": "absolute",
                    "left": $(tirgger).position().left + 5,
                    "top": $(tirgger).position().top + 108

                }).toggle();


                $("#hidCaseFeeTypeName").val($(tirgger).attr("id")); //名称
                $("#hidCaseFeeTypeId").val($(this).parent().find(":hidden").attr("id"));//Id
                return false;
            });

            $("#DefaultCaseFee_ResponseUserName").unbind("click");
            $("#DefaultCaseFee_ResponseUserName").bind("click", function () {
                $("#hidUserId").val("DefaultCaseFee_ResponseUser");
                $("#hidUserName").val("DefaultCaseFee_ResponseUserName");

                $("#divUsers").css({
                    "position": "absolute",
                    "left": $("#DefaultCaseFee_ResponseUserName").offsetParent().position().left + 15,
                    "top": $("#DefaultCaseFee_ResponseUserName").offsetParent().position().top + 32
                }).toggle();

                return false;
            });

            $("#divUsers").find("li").off().unbind("click");
            $("#divUsers").find("li").off().bind("click", function () {
                var userId = $(this).find("a").attr("name");
                var userName = $(this).find("a").text();
                var currentSelectedControl = $("#hidUserName").val();
                var currentSelectedIdControl = $("#hidUserId").val();
                $("#" + currentSelectedControl).val(userName);
                $("#" + currentSelectedIdControl).val(userId);
                $("#divUsers").hide();
            });

            $("#divCaseFeeTypeList").find("li").off().on("click", function () {
                var caseFeeTypeId = $(this).find("a").attr("id");
                var caseFeeTypeName = $(this).find("a").text();
                var currentSelectedControlId = $("#hidCaseFeeTypeId").val();
                var currentSelectedControlName = $("#hidCaseFeeTypeName").val();
                $("#" + currentSelectedControlId).val(caseFeeTypeId);
                $("#" + currentSelectedControlName).val(caseFeeTypeName);

                //if ($("#DefaultCaseFee_FeeTypeId").val() == "3") {
                //    //年费
                //    $(".yearly").show();
                //} else {
                //    $(".yearly").hide();
                //}

                $($('#tblCaseFeeItemList>tbody>tr:first>td')[0]).html("<span class='spanCaseFeeTypeName'>" + $("#DefaultCaseFee_FeeTypeName").val() + "</span>");

                $("#divCaseFeeTypeList").hide();
            });

            $("#btnFeeInformConfirmItemAdd").unbind("click");
            $("#btnFeeInformConfirmItemAdd").bind("click", function () {
                caseInfo.CaseFee.CaseFeeTypeItem.Add();
            });

            $(".btn_clear").off().on("click", function () {
                caseInfo.CaseFee.CaseFeeTypeItem.Clear(this);
            });
            $(".btn_remove").off().on("click", function () {
                caseInfo.CaseFee.CaseFeeTypeItem.Remove(this);
            });

            $("#btnFeeInformConfirm").unbind("click");
            $("#btnFeeInformConfirm").bind("click", function () {
                caseInfo.CaseFee.CreateUpdateInform();
            });

            /*财务到帐*/
            $("#btnCaseFeeConfirmCancel,#btnCaseFeeConfirmClose").off().on("click", function () {
                caseInfo.CaseFee.CloseConfirm();
            });
            $("#btnCaseFeeConfirm").off().on("click", function () {
                caseInfo.CaseFee.CreateUpdateConfirm();
            });


            /*票据确认*/
            $("#flBillFile").off().on("change", function () {
                $("#txtBillFilePath").val($("#flBillFile").val());
            });

            $("#btnCaseFeeBillConfirmCancel,#btnCaseFeeBillConfirmClose").off().on("click", function () {
                caseInfo.CaseFee.CloseBillConfirm();
            });
            $("#btnCaseFeeBillConfirm").off().on("click", function () {
                caseInfo.CaseFee.CreateUpdateBillConfirm();
            });

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
                        caseInfo.CaseFee.OpenInform();
                    },
                    'feeConfirm': function (t, e) {
                        var feeId = $(e).find("span").html();
                        caseInfo.CaseFee.OpenConfirm(feeId);
                    },
                    'billConfirm': function (t, e) {
                        var feeId = $(e).find("span").html();
                        caseInfo.CaseFee.OpenBillConfirm(feeId);
                    },
                    'download': function (t, e) {
                        var feeId = $(e).find("span").html();
                        caseInfo.CaseFee.Download(feeId);
                    },
                    'nolock': function (t, e) {
                        var feeId = $(e).find("span").html();
                        caseInfo.CaseFee.Unlock(feeId);
                    },
                    'delete': function (t, e) {
                        var feeId = $(e).find("span").html();
                        caseInfo.CaseFee.Delete(feeId);
                    },
                    'linked': function (t, e) {
                        caseInfo.CaseFee.Linked();
                    },
                    'refresh': function (t, e) {
                        caseInfo.CaseFee.List();
                    }
                },
                onContextMenu: function (e) {
                    // 
                    //if ($(e.target).attr('id') == 'dontShow') return false;
                    //else return true;
                    return true;
                },
                onShowMenu: function (e, menu) {
                    if ($(e.target).parents("tr").find(".feeId").hasClass("feeId")) {
                        var feeItemId = $(e.target).parents("tr").find("#item_FeeItemId").val();
                        var feeId = $(e.target).parents("tr").find("#item_FeeId").val();
                        $('#feeConfirm', menu).append("<span style='display:none'>" + feeItemId + "</span>");
                        $('#billConfirm', menu).append("<span style='display:none'>" + feeItemId + "</span>");
                        $('#download', menu).append("<span style='display:none'>" + feeItemId + "</span>");
                        $('#nolock', menu).append("<span style='display:none'>" + feeId + "</span>");
                        $('#delete', menu).append("<span style='display:none'>" + feeId + "</span>");
                    } else {
                        $('#feeConfirm', menu).remove();
                        $('#billConfirm', menu).remove();
                        $('#nolock', menu).remove();
                        $('#delete', menu).remove();
                    }
                    return menu;
                }
            });
        },

        /*案件费用通知*/
        OpenInform: function (caseFileTypeId) {
            if (parseInt($("#CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }
            var data =
            {
                caseId: $("#CaseId").val(),
                caseNo: $("#Case_CaseBasicInfo_CaseNo").val(),
                caseTypeId: $("#Case_CaseBasicInfo_CaseTypeId").val(),
                caseFileTypeId: caseFileTypeId
            };
            var url =  AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseFee/CaseFeeInform";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                caseInfo.CaseFee.BindEvent();
                $('#caseFeeInformModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseFeeInformModal').on('hidden.bs.modal', function () {
                    $("#caseFeeInformModal").remove();
                });
            });

        },
        CloseInform: function () {
            $('#caseFeeInformModal').modal('hide');
        },
        CreateUpdateInform: function () {

            if ($("#DefaultCaseFee_FeeTypeId").val() == '') {
                $.showModalMessageBox("请选择费用类型.");
                return false;
            }

            if ($("#DefaultCaseFee_ResponseUser").val() == '') {
                $.showModalMessageBox("请选择收费人.");
                return false;
            }

            if ($("#DefaultCaseFee_FeeTypeId").val() == '3' && ($("#DefaultCaseFee_Yealy").val() == '' || parseInt($("#DefaultCaseFee_Yealy").val()) < 1)) {
                //年费必填,且大于0
                $.showModalMessageBox("请输入年限，年限为大于0的正整数.");
                return false;
            }
            var data = {};

            data["CaseFee.CaseId"] = $("#CaseId").val();
            data["CaseFee.CaseNo"] = $("#CaseNo").val();
            data["CaseFee.FeeTypeId"] = $("#DefaultCaseFee_FeeTypeId").val();
            data["CaseFee.FeeTypeName"] = $("#DefaultCaseFee_FeeTypeName").val();

            var j = 0;
            var dataIsNOk = false;

            $("#tblCaseFeeItemList>tbody>tr").each(function (i, e) {

                if ($(e).css("display") != 'none') {
                    if (i == 0) {
                        data["CaseFee.CaseFeeItems[" + j + "].CaseId"] = $("#CaseId").val();
                        data["CaseFee.CaseFeeItems[" + j + "].CaseNo"] = $("#CaseNo").val();
                        data["CaseFee.CaseFeeItems[" + j + "].FeeTypeId"] = $("#DefaultCaseFee_FeeTypeId").val();
                        data["CaseFee.CaseFeeItems[" + j + "].FeeTypeName"] = $("#DefaultCaseFee_FeeTypeName").val();
                        data["CaseFee.CaseFeeItems[" + j + "].ResponseUser"] = $("#DefaultCaseFee_ResponseUser").val();
                        data["CaseFee.CaseFeeItems[" + j + "].Yearly"] = $("#DefaultCaseFee_Yearly").val();
                        data["CaseFee.CaseFeeItems[" + j + "].IsFeeMitigation"] = $(e).find("#item_IsFeeMitigation").prop("checked") == true;
                        data["CaseFee.CaseFeeItems[" + j + "].Amount"] = $(e).find("#item_Amount").val();
                    } else {
                        data["CaseFee.CaseFeeItems[" + j + "].CaseId"] = $("#CaseId").val();
                        data["CaseFee.CaseFeeItems[" + j + "].CaseNo"] = $("#CaseNo").val();
                        data["CaseFee.CaseFeeItems[" + j + "].FeeTypeId"] = $(e).find("#hidCaseFeeItem_FeeTypeId" + j).val();
                        data["CaseFee.CaseFeeItems[" + j + "].FeeTypeName"] = $(e).find("#CaseFeeItem_FeeTypeName" + j).val();
                        data["CaseFee.CaseFeeItems[" + j + "].ResponseUser"] = $("#DefaultCaseFee_ResponseUser").val();
                        data["CaseFee.CaseFeeItems[" + j + "].Yearly"] = $("#DefaultCaseFee_Yearly").val();
                        data["CaseFee.CaseFeeItems[" + j + "].IsFeeMitigation"] = $(e).find("#item_IsFeeMitigation").prop("checked") == true;
                        data["CaseFee.CaseFeeItems[" + j + "].Amount"] = $(e).find("#item_Amount").val();

                        if ($(e).find("#hidCaseFeeItem_FeeTypeId" + j).val() == $("#CaseFee_FeeTypeId").val()) {
                            dataIsNOk = true;
                            $.showModalMessageBox("第" + (j + 1) + "行，<br>费用类型不能与主费用类型一致.");
                            return false;
                        }

                        if (data["CaseFee.CaseFeeItems[" + j + "].FeeTypeId"] == '') {
                            dataIsNOk = true;
                            $.showModalMessageBox("第" + (j + 1) + "行，请选择费用类型.");
                            return false;
                        }
                    }
                    j++;
                }
            });

            if (dataIsNOk) return false;
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseFee/CaseFeeInformCreate", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("保存成功.");
                    $('#caseFeeInformModal').modal('hide');

                    if (caseInfo.CaseFee) {
                        caseInfo.CaseFee.List();
                        caseInfo.CaseEvent.List();
                    }
                } else {

                    $.showModalMessageBox(response.Message);
                }
            });
        },

        /*案件费用确认*/
        OpenConfirm: function (caseFeeId) {
            if (parseInt($("#CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }
            var data =
            {
                caseId: $("#CaseId").val(),
                caseNo: $("#Case_CaseBasicInfo_CaseNo").val(),
                caseTypeId: $("#Case_CaseBasicInfo_CaseTypeId").val(),
                caseFeeId: caseFeeId
            };
            var url =  AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseFee/CaseFeeConfirm";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseFeeConfirmModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseFeeConfirmModal').on('hidden.bs.modal', function () {
                    $("#caseFeeConfirmModal").remove();
                });
            });
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

            $("#caseFeeConfirm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseFee/CaseFeeConfirmCreate", function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("保存成功.");
                    $('#caseFeeConfirmModal').modal('hide');

                    if (caseInfo.CaseFee) {
                        caseInfo.CaseFee.List();
                    }
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        /*案件票据确认*/
        OpenBillConfirm: function (caseFeeId) {

            if (parseInt($("#CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }
            var data =
            {
                caseId: $("#CaseId").val(),
                caseNo: $("#Case_CaseBasicInfo_CaseNo").val(),
                caseTypeId: $("#Case_CaseBasicInfo_CaseTypeId").val(),
                caseFeeId: caseFeeId
            };
            var url =  AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseFee/CaseFeeBillConfirm";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                caseInfo.CaseFee.BindEvent();
                $('#caseFeeBillConfirmModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseFeeBillConfirmModal').on('hidden.bs.modal', function () {
                    $("#caseFeeBillConfirmModal").remove();
                });
            });
        },

        Download: function (caseFeeId) {
            window.open( AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseFileCenter/CaseFeeFileDownload?caseFeeId=" + caseFeeId);
            return true;
        },

        CloseBillConfirm: function () {
            $('#caseFeeBillConfirmModal').modal('hide');
        },
        CreateUpdateBillConfirm: function () {

            if ($("#DefaultCaseFee_BillNo").val() == '') {
                $.showModalMessageBox("请输入票据编号.");
                return false;
            }

            if ($("#DefaultCaseFee_BillAmount").val() == '') {
                $.showModalMessageBox("请输入票据金额.");
                return false;
            }

            if ($("#DefaultCaseFee_BillDate").val() == '') {
                $.showModalMessageBox("请输入票据日期.");
                return false;
            }

            if ($("#flBillFile").val() == '') {
                $.showModalMessageBox("请选择上传文件.");
                return false;
            }

            $.openLoading();
            $('#caseFeeBillConfirm').ajaxSubmit({
                success: function (response) {
                    $.closeLoading();
                    if (response.IsSuccess) {
                        $.showModalMessageBox("保存成功.");
                        $('#caseFeeBillConfirmModal').modal('hide');

                        if (caseInfo.CaseFee) {
                            caseInfo.CaseFee.List();
                        }

                        caseInfo.CaseEvent.List();

                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                }
            });
        },
        CaseFeeTypeItem: {
            Add: function () {
                var tr = $($('#tblCaseFeeItemList>tbody>tr')[0]).clone().show();
                $($("td", tr)[0]).html("<input type='hidden' value='' id='hidCaseFeeItem_FeeTypeId" + $("#tblCaseFeeItemList>tbody>tr").length + "' /><input class='CaseFeeItem_FeeTypeName form-control' sytle='text-align:center;width:100px' id='CaseFeeItem_FeeTypeName" + $("#tblCaseFeeItemList>tbody>tr").length + "' readonly type='text' value='' />");
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

        Unlock: function (caseFeeId) {
            var data = { caseFeeId: caseFeeId };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseFee/CaseFeeUnlock", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("解锁成功");
                    caseInfo.CaseFee.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        Delete: function (caseFeeId) {
            var data = { caseFeeId: caseFeeId };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseFee/CaseFeeDelete", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("删除成功.");
                    caseInfo.CaseFee.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        Linked: function () {
            var caseFeeItemIds = $.checkbox.vals("chkCaseFeeItemId");
            if (caseFeeItemIds.length < 2) {
                $.showModalMessageBox("至少选择两项进行关联.");
                return false;
            }

            var data = { caseFeeItemIds: caseFeeItemIds };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseFee/CaseFeeLinked", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("关联费用信息成功.");
                    caseInfo.CaseFee.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        }
    },

    CaseFile: {
        Init: function () {
            caseInfo.CaseFile.List();
        },

        BindEvent: function () {
            $("#btnCaseFileCreate").unbind("click");
            $("#btnCaseFileCreate").bind("click", function () {
                caseInfo.CaseFile.Open(false);
            });

            $("#btnCaseFileUploadingClose,#btnCaseFileUploadingCancel").off().on("click", function () {
                caseInfo.CaseFile.Close();
            });

            $("#btnCaseFileUploading").off().on("click", function () {
                caseInfo.CaseFile.CreateUpdate();
            });

            $("#flCaseFile").unbind("change");
            $("#flCaseFile").bind("change", function () {
                $("#txtCaseFilePath").val($("#flCaseFile").val());
            });

            $("#lnkCaseFileTypeId").unbind("click");
            $("#lnkCaseFileTypeId").bind("click", function () {
                var tirgger = $("#CaseFileTypeName");
                if ($("#IsTransformedFile").val() == 'true') {
                    $(".divCaseFileTypeList").html($.lsCaseFileType.getCaseTransformedFileTypeListHtml($("#CaseTypeId").val()));
                } else {
                    $(".divCaseFileTypeList").html($.lsCaseFileType.getCaseFileTypeListHtml($("#CaseTypeId").val()));
                }
                $("#divCaseFileTypeList").css({
                    "position": "absolute",
                    "left": $(tirgger).offsetParent().position().left + 15,
                    "top": $(tirgger).offsetParent().position().top + 32
                }).toggle();

                $("#hidCaseFileTypeName").val($(tirgger).attr("id")); //名称
                $("#hidCaseFileTypeId").val($("#CaseFileTypeId").attr("id")); //Id

                return false;
            });

            $("#divCaseFileTypeList").find("li").unbind("click");
            $("#divCaseFileTypeList").find("li").off().on("click", function () {
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
        },

        /*文档类表*/
        List: function () {
            var data = {
                caseId: $("#CaseId").val(),
                pageNo: $("#PageNo").val(),
                pageSize: $("#PageSize").val()
            };

            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseFile/CaseFileList", data, function (response) {
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

                    caseInfo.ResetSize();

                    var totalCount = parseInt($("#TotalCount").val());

                    if (totalCount > 0) {
                        $("tfoot", "#tblCaseFile").show();
                        $(".simple-grid-none-data-wrap").hide();
                    } else {
                        $("tfoot", "#tblCaseFile").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                    caseInfo.CaseFile.BindEvent();
                    caseInfo.CaseFile.BindMenu();

                    $.closeLoading();
                }
            }, true);
        },

        /*上传文件*/
        //isTransformedFile 导出专文文档
        Open: function (isTransformedFile) {

            if (parseInt($("#CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }
            var data =
            {
                caseId: $("#CaseId").val(),
                caseNo: $("#Case_CaseBasicInfo_CaseNo").val(),
                caseTypeId: 1,
                hedgingFileTypeId: 0,
                isTransformedFile: isTransformedFile
            };

            var url =  AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseFile/CaseFileUpload";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseFileUploadingModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseFileUploadingModal').on('hidden.bs.modal', function () {
                    $("#caseFileUploadingModal").remove();
                });

                caseInfo.CaseFile.BindEvent();
                //var caseFileType = new AssociateCaseFileType(
                // $("#div_CaseFileTypeList"),
                // $("#CaseFileTypeId"),
                // $("#CaseFileTypeName"),
                // $("#Case_CaseBasicInfo_CaseTypeId").val(),
                // $("#IsTransformedFile").val() == 'true',
                // caseInfo.CaseFile.ProcessFileTypeSelectedCallBack
                //);
            });
        },

        Close: function () {
            $('#caseFileUploadingModal').modal('hide');
        },

        CreateUpdate: function () {

            var caseFileTypeId = $("#CaseFileTypeId").val();

            if ($("#CaseFileTypeName").val() == '') {
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
                        //caseInfo.InitCaseBasic();
                        $.showModalMessageBox("上传成功.");
                        caseInfo.CaseFile.List();
                        caseInfo.CaseEvent.List();
                        return true;
                    } else {
                        $.showModalMessageBox(response.Message);
                        return false;
                    }
                }
            });
        },

        Download: function (caseFileId) {
            window.open( AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseFileCenter/CaseFileDownload?caseFileId=" + caseFileId);
            return true;
        },

        UnLock: function (caseFileId) {
            var data = { caseFileId: caseFileId };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseFile/CaseFileUnlock", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("解锁成功");
                    caseInfo.CaseFile.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        Delete: function (caseFileId) {
            var data = { caseFileId: caseFileId };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/Lawsuit/CaseFile/CaseFileDelete", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("删除成功.");
                    caseInfo.CaseFile.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        ProcessFileTypeSelectedCallBack: function (caseFileTypeId, caseFileTypeNameText, hedgingFileTypeId, hedgingFeeTypeId) {
            $(".spanreferencedate").text(caseFileTypeNameText + "日期");
            $(".caseHedgingFile").css("display", 'none');
            $(".caseHedgingFee").css("display", 'none');
            $("#HedgingFileId").empty();
            $("#HedgingFeeId").empty();
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
                    'refresh': function (t, e) {
                        caseInfo.CaseFile.List();
                    },

                },
                onContextMenu: function (e) {
                    // 
                    //if ($(e.target).attr('id') == 'dontShow') return false;
                    //else return true;
                    return true;
                },
                onShowMenu: function (e, menu) {
                    if ($(e.target).parents("tr").find(".fileId").hasClass("fileId")) {
                        var fileId = $(e.target).parents("tr").find(".fileId").text();
                        $('#view', menu).append("<span style='display:none'>" + fileId + "</span>");
                        $('#unlock', menu).append("<span style='display:none'>" + fileId + "</span>");
                        $('#toword', menu).append("<span style='display:none'>" + fileId + "</span>");
                        $('#delete', menu).append("<span style='display:none'>" + fileId + "</span>");
                    }
                    else {
                        $('#view', menu).remove();
                        $('#unlock', menu).remove();
                        $('#delete', menu).remove();
                    }
                    return menu;
                }
            });
        },
    },

    /*案件资费*/
    CaseAssistedFee: {

        /*资费列表*/
        List: function () {
            var data = {
                caseId: $("#CaseId").val(),
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
                        caseInfo.CaseAssistedFee.Create();
                    },
                    'transact': function (t, e) {
                        var feeId = $(e).find("span").html();
                        caseInfo.CaseAssistedFee.Transact(feeId);
                    },
                    'delete': function (t, e) {
                        var feeId = $(e).find("span").html();
                        caseInfo.CaseFee.Delete(feeId);
                    },
                    'refresh': function (t, e) {
                        caseInfo.CaseAssistedFee.List();
                    }
                },
                onContextMenu: function (e) {
                    // 
                    //if ($(e.target).attr('id') == 'dontShow') return false;
                    //else return true;
                    return true;
                },
                onShowMenu: function (e, menu) {
                    if ($(e.target).parents("tr").find(".assistedFeeId").hasClass("assistedFeeId")) {
                        var feeId = $(e.target).parents("tr").find("#item_AssistedFeeId").val();
                        $('#transact,#delete', menu).append("<span style='display:none'>" + feeId + "</span>");
                    }
                    else {
                        $('#transact, #delete', menu).remove();
                    }
                    return menu;
                }
            });
        },

        /*资费新建*/
        Create: function () {
            if (parseInt($("#CaseId").val()) == 0) {
                $.showModalMessageBox("请先保存案件基本资料.");
                return false;
            }
            var data =
            {
                caseId: $("#CaseId").val(),
                caseNo: $("#Case_CaseBasicInfo_CaseNo").val(),
                caseAssistedFeeTypeId: 1
            };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseAssistedFeeCreate", data, function (response) {
                if (response.IsSuccess) {
                    caseInfo.CaseAssistedFee.List();
                }
            }, true);
        },

        /*资费处理*/
        Transact: function (caseAssistedFeeId) {
            var data =
            {
                caseAssistedFeeId: caseAssistedFeeId
            };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseAssistedFeeTransact", data, function (response) {
                if (response.IsSuccess) {
                    caseInfo.CaseAssistedFee.List();
                }
            }, true);
        },

        /*资费删除*/
        Delete: function (caseAssistedFeeId) {
            var data =
            {
                caseAssistedFeeId: caseAssistedFeeId
            };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseAssistedFeeDelete", data, function (response) {
                if (response.IsSuccess) {
                    caseInfo.CaseAssistedFee.List();
                }
            }, true);
        },
    }
}

var enableEditForm = false;

$(document).ready(function () {

    $(function () {
        $('.product-nav-list').css("top", "0");
        $('.product-nav-list').slimScroll({
            height: '100%'
        });
    });

    $('.viewFramework-product-body').slimScroll({
        height: '100%'
    });

    $(window).resize(function () {
        caseInfo.ResetSize();
    });

    $(document).click(function () {
        $("#divCaseFeeTypeList").off().hide();
        $("#divUserList").off().hide();
        $("#divUsers").off().hide();
        $("#divCaseFileTypeList").off().hide();
        $("#divUserListForDepartment1").off().hide();
        $("#divCaseDetermineThewayCheckBoxList").off().hide();
        $("#divCaseHolderOfRelationshipList").off().hide();
        //$("#divCaseHolderOfRelationship").off().hide();
        $("#divCaseTheThirdRelationshipList").off().hide();

    });

    //caseInfo.Init();

    caseInfo.ResetSize();

    caseInfo.CaseFile.Init();
});