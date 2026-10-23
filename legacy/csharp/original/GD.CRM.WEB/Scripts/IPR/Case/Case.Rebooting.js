var caseInfo = {
    View: function (caseId, caseNo) {

        var search = {};

        search.CaseId = 0;
        search.PageId = 1;
        search.PageNo = 1;
        search.PageSize = 100;
        search.PageName = "案件查看";
        search.Keyword = caseNo;

        var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CreateUpdate?typeId=1&caseId=" + caseId + "&k=" + escape(JSON.stringify(search));

        window.open(url);

        //window.open( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CreateUpdate?CaseId=" + caseId);
    },
    CreateUpdate: function () {
        var data = {
            caseNo: $("#OriginalCase_CaseBasicInfo_CaseNo").val()
        };

        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseRebootingCreate", data, function (response) {
            if (response.IsSuccess) {

                $(".step.col-md-4.step-first").removeClass("step-active");
                $(".step.col-md-4.step-todo").removeClass("step-active");
                $(".step.col-md-4.step-end").addClass("step-active");

                $("#divCaseRebootingStep1").hide();
                $("#divCaseRebootingStep2").hide();
                $("#divCaseRebootingStep3").show();

                $("#TargetCase_CaseNo").val(response.Data.CaseBasicInfo.CaseNo);
                $("#TargetCase_CaseBasicInfo_CaseId").val(response.Data.CaseBasicInfo.CaseId);

                $.showModalMessageBox("创建案件成功.");

            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    GetCaseBasicByCaseNo: function (trigger, caseNo, functionCallback) {
        var data = { caseNo: caseNo };
        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/GetRebootingCaseByCaseNo", data, function (response) {
            if (response.IsSuccess && response.Data && response.Data != "") {
                setTimeout(functionCallback(response, trigger), 200);
                return false;
            }
        }, false);
    },

    getCaseBasicCallBack: function (response, trigger) {
        if (typeof (response) == "undefined" || response == null) {
            $("#help-info-step1").text("未找到案件信息,请确认输入的案件是否准确.");
            return false;
        }

        $("#OriginalCase_CaseBasicInfo_CaseNo").val(response.Data.CaseBasicInfo.CaseNo);
        $("#OriginalCase_CaseBasicInfo_ApplicantName").val(response.Data.CaseBasicInfo.ApplicantName);
        $("#OriginalCase_CaseBasicInfo_CaseRequestNo").val(response.Data.CaseBasicInfo.CaseRequestNo);
        if(response.Data.CaseBasicInfo.CaseRequestDate != null)
        {
            $("#OriginalCase_CaseBasicInfo_CaseRequestDate").val(getDate(convertJsonDateToJSDate(response.Data.CaseBasicInfo.CaseRequestDate)));
        }
        $("#OriginalCase_CaseBasicInfo_CaseName").val(response.Data.CaseBasicInfo.CaseName);
        $("#OriginalCase_CaseBasicInfo_CaseOriginPeopleName").val(response.Data.CaseBasicInfo.CaseOriginPeopleName);
        $("#TargetCase_CaseBasicInfo_CaseNo").val(response.Data.CaseBasicInfo.RebootingCaseNo);

        $(".step.col-md-4.step-first").removeClass("step-active");
        $(".step.col-md-4.step-todo").addClass("step-active");
        $("#divCaseRebootingStep1").hide();
        $("#divCaseRebootingStep2").show();

    },
};

$(document).ready(function () {
    $("#btnCaseRebootingStep1").off().on("click", function () {
        if ($.trim($("#CaseNo").val()) != "")
        {
            caseInfo.GetCaseBasicByCaseNo($("#CaseNo"), $("#CaseNo").val(), caseInfo.getCaseBasicCallBack);
        }
    });

    $("#btnCaseRebootingStep2").off().on("click", function () {
        caseInfo.CreateUpdate();
    });

    $("#btnCaseView").off().on("click", function () {

        if ($("#TargetCase_CaseBasicInfo_CaseId").val() != "")
        {
            var caseId = $("#TargetCase_CaseBasicInfo_CaseId").val();
            var caseNo = $("#TargetCase_CaseBasicInfo_CaseNo").val();

            caseInfo.View(caseId,caseNo);
        }

    });
 });