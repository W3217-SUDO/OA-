$(document).ready(function () {
    $(document).click(function () {
        $("#divCasePhaseCheckBoxList").off().hide();
        $("#divAssociatePaymentTypeList_CaseFee").off().hide();
        $("#divCaseTaskTypeList").off().hide();
    });
    c.Cases.ExecutionList();
    c.Cases.ListWebUploader.Setting();
    $(document).off('click', '#SearchCondition_CasePhaseName').on('click', '#SearchCondition_CasePhaseName', function () {
        var tirgger = this;
        var html = $.lsCasePhase.getcasePhaseListTreeHtml($("#SearchCondition_CaseTypeId").val(), 1010140);
        $("#divCasePhaseCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left + 9,
            "top": $(tirgger).parent().position().top + 25,
            "z-index": 9999
        }).toggle();

        return false;
    });
    $(document).off('click', '#divCasePhaseCheckBoxList ul li').on('click', '#divCasePhaseCheckBoxList ul li', function (e) {

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
        $("#" + currentSelectedIdControl).val('');

        var casePhaseNames = '';
        var casePhaseIds = '';

        $("#divCasePhaseCheckBoxList").find("input:checkbox").each(function () {
            if ($(this).prop("checked") == true) {
                casePhaseNames += $(this).attr("casephasename") + ",";
                casePhaseIds += $(this).attr("casephaseid") + ",";
            }
        });

        $("#" + currentSelectedControl).val(casePhaseNames.substring(0, casePhaseNames.length - 1));
        $("#" + currentSelectedIdControl).val(casePhaseIds.substring(0, casePhaseIds.length - 1));

        e.stopPropagation();

        return true;
    });
    $(document).off('click', '#btnCaseSearch').on('click', '#btnCaseSearch', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(10);
        c.Cases.ExecutionList();
    });
    $(document).off('click', '#btnCasePhaseSelected').on('click', '#btnCasePhaseSelected', function () {
        var treeObj = $.fn.zTree.getZTreeObj("casePhaseTree");
        var nodes = treeObj.getCheckedNodes(true);
        var phaseIds = new Array();
        var phaseNames = new Array();
        if (nodes.length > 0) {
            $.each(nodes, function (j, node) {
                phaseIds.push(node.id);
                phaseNames.push(node.name);
            });
            $("#SearchCondition_CasePhaseId").val(phaseIds.join(','));
            $("#SearchCondition_CasePhaseName").val(phaseNames.join(','));
        }
        else {
            $("#SearchCondition_CasePhaseId").val('');
            $("#SearchCondition_CasePhaseName").val('');
        }
        c.Cases.ExecutionList();
    });
    $(document).off('click', '#btnAllCaseExportToExcel').on('click', '#btnAllCaseExportToExcel', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);
        c.Cases.ExportAllToExcel();
    });
    $(document).off('click', '#btnCaseExportToExcel').on('click', '#btnCaseExportToExcel', function () {
        c.Cases.ExportSelectedToExcel();
    });
    $(document).off('click', '#btnCaseListExportToExcelForManifest').on('click', '#btnCaseListExportToExcelForManifest', function () {
        c.Cases.ExportSelectedToExcelForManifest();
    });
    $(document).off('click', '#btnCaseDelete').on('click', '#btnCaseDelete', function () {
        var chkCaseIds = $.checkbox.vals("chkCaseId");
        if (chkCaseIds.length == 0) {
            //$.showModalMessageBox("请选择案件.");
            $.showTips('请选择案件.', 0, 3);
            return false;
        }
        c.Cases.Case.Delete(chkCaseIds);
        
    });
    $(document).off('click', '#btnParticipantCreateUpdate').on('click', '#btnParticipantCreateUpdate', function () {
        c.Cases.Case.Participant.CreateUpdate(c.Cases.ExecutionList);
    })
    $(document).off('click', '#btnCaseSearchReset').on('click', '#btnCaseSearchReset', function () {
        c.Cases.Reset();
    });
    $(document).off('click', '#chkCaseAll').on('click', '#chkCaseAll', function () {
        c.Cases.Selected(this);
    });
    $(document).off('change', '.internalFeeType').on('change', '.internalFeeType', function (e) {
        var target = $(this).parent().parent();
        $(target).find(".item_PaymentObjectName_Input").removeAttr("disabled");
        $(target).find(".item_PaymentObjectName_Input").css("width","100%");
        $(target).find(".item_PaymentObjectName_Input").prevAll().remove();
        if ($(this).val() == '11040040' || $(this).val() == '11040041') {
            if ($(this).attr("caselawyer") == '' || $(this).attr("caselawyer") == null) {
                $(target).find(".item_PaymentObjectName_Input").attr("disabled", "disabled");
                return false;
            }
            else {
                var caseLawyers = $(this).attr("caselawyer").split(",");
                var caseLawyerNames = $(this).attr("caselawyername").split(",");
                $.each(caseLawyers, function (i, lawyer) {
                    c.Cases.Case.InternalFees.InternalFee.Objects.PaymentObject.AddIn(target, lawyer, caseLawyerNames[i], false)
                });
            }
        }
        else if ($(this).val() == '11040030' || $(this).val() == '11040031') {
            if ($(this).attr("caseassistant") == '' || $(this).attr("caseassistant") == null) {
                $(target).find(".item_PaymentObjectName_Input").attr("disabled", "disabled");
                return false;
            }
            else {
                var caseAssistants = $(this).attr("caseassistant").split(",");
                var caseAssistantNames = $(this).attr("caseassistantname").split(",");
                $.each(caseAssistants, function (i, assistant) {
                    c.Cases.Case.InternalFees.InternalFee.Objects.PaymentObject.AddIn(target, assistant, caseAssistantNames[i], false)
                });
            }
        }
        else if ($(this).val() == '11040070' || $(this).val() == '11040071') {

            if ($(this).attr("caseinvestigator") == '' || $(this).attr("caseinvestigator") == null) {
                $(target).find(".item_PaymentObjectName_Input").attr("disabled", "disabled");
                return false;
            }
            else {
                var caseInvestigators = $(this).attr("caseinvestigator").split(",");
                var caseInvestigatorNames = $(this).attr("caseinvestigatorname").split(",");
                $.each(caseInvestigators, function (i, investigator) {
                    c.Cases.Case.InternalFees.InternalFee.Objects.PaymentObject.AddIn(target, investigator, caseInvestigatorNames[i], false)
                });
            }
        }
        else if ($(this).val() == '11040020' || $(this).val() == '11040021') {
            if ($(this).attr("casebusinessowner") == '' || $(this).attr("casebusinessowner") == null) {
                $(target).find(".item_PaymentObjectName_Input").attr("disabled", "disabled");
                return false;
            }
            else {
                var caseBusinessOwners = $(this).attr("casebusinessowner").split(",");
                var caseBusinessOwnerNames = $(this).attr("casebusinessownername").split(",");
                $.each(caseBusinessOwners, function (i, businessOwner) {
                    c.Cases.Case.InternalFees.InternalFee.Objects.PaymentObject.AddIn(target, businessOwner, caseBusinessOwnerNames[i], false)
                });
            }
        }
    });
    $(document).off('click', '.paymentobjectremove').on('click', '.paymentobjectremove', function () {
        //if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
        //    return false;
        //}
        c.Cases.Case.InternalFees.InternalFee.Objects.PaymentObject.Remove(this);
    });
    $(document).off('click', '.casefeepaymentobjectremove').on('click', '.casefeepaymentobjectremove', function () {
        //if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
        //    return false;
        //}
        
        c.Cases.Case.CaseFees.Payment.Objects.PaymentObject.Remove(this);
    });
    $(document).off('click', '.aps-icon-shangjiantou').on('click', '.aps-icon-shangjiantou', function () {
        var sorting = $(this).parent().attr("data-field");
        if (sorting != null && sorting != '') {
            $(".aps-sort").each(function (i, e) {
                $(e).removeClass("aps-asc");
                $(e).removeClass("aps-desc");
            });

            $(this).parent().addClass("aps-asc");
            $("#SearchCondition_Sorting").val(sorting + " asc");
        }
        c.Cases.ExecutionList();
    });
    $(document).off('click', '.aps-icon-xiajiantou').on('click', '.aps-icon-xiajiantou', function () {
        var sorting = $(this).parent().attr("data-field");
        if (sorting != null && sorting != '') {
            $(".aps-sort").each(function (i, e) {
                $(e).removeClass("aps-asc");
                $(e).removeClass("aps-desc");
            });
            $(this).parent().addClass("aps-desc");
            $("#SearchCondition_Sorting").val(sorting + " desc");
        }
        c.Cases.ExecutionList();
    });
    $(document).off('change', '.caseFeeType').on('change', '.caseFeeType', function (e) {
        var target = $(this).parent().parent();
        if ($(this).val() == '11010020' || $(this).val() == '11010030' || $(this).val() == '11010040' || $(this).val() == '11010090') {
            var remark = "法院号:" + ($(this).attr("officialNo") == '' ? "无" : $(this).attr("officialNo")) + ";费用类型: " + $(this).find("option:selected").text();
            $(target).find(".item_Remark").val(remark);
        }
        else if ($(this).val() == '11010050') {
            var remark = "公证号:" + ($(this).attr("notarialnos") == '' ? "无" : $(this).attr("notarialnos")) + ";费用类型: " + $(this).find("option:selected").text();
            $(target).find(".item_Remark").val(remark);
        }
        else {
            $(target).find(".item_Remark").val('');
        }
    });
    $(document).off('click', '#btnCasePhaseTypeChanged').on('click', '#btnCasePhaseTypeChanged', function (e) {
        var caseNos = $.checkbox.vals("chkCaseId");
        c.Cases.Case.CasePhases.CasePhase.Change(caseNos);
        c.Cases.ExecutionList();
    });

    $(document).off('click', '#btnExecutionStatusChange').on('click', '#btnExecutionStatusChange', function () {
        var caseIds = [];
        $("input[name='chkCaseId']:checked").each(
            function (i) { caseIds[i] = $(this).attr("caseno"); }
        );
        if (caseIds.length < 1) {
            //$.showModalMessageBox("请选择需要跟进的案件.");
            $.showTips('请选择需要跟进的案件.', 0, 3);
            return false;
        }
        c.Cases.Case.Basic.ExecutionStatus.Open(caseIds.join(","));
    });
    $(document).off('click', '#btnExecutionStatusUpdate').on('click', '#btnExecutionStatusUpdate', function () {
        if ($("#ExecutionStatus").val() == '')
        {
            $.showTips('请选择执行进度.', 0, 3);
            return false;
        }
        var caseNos = $("#CaseNos").val();
        c.Cases.Case.Basic.ExecutionStatus.Change(caseNos, $("#ExecutionStatus").val());
    });

    $(document).off('click', '#btnCourtUpdate').on('click', '#btnCourtUpdate', function (e) {
        c.Cases.Case.Court.CreateUpdate(c.Cases.ExecutionList);
    });

    c.ResetSize();
    $(window).resize(function () {
        c.ResetSize();
    })
});