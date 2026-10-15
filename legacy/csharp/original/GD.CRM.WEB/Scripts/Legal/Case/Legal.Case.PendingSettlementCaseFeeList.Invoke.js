$(document).ready(function () {
    caseFee.PendingSettlementCaseFeeList();

    $(document).off('click', '#SearchCondition_CaseFeeTypeName').on('click', '#SearchCondition_CaseFeeTypeName', function () {
        var tirgger = this;
        var html = $.lsCaseFeeType.getCaseFeeTypeListTreeHtml();
        $("#divCaseFeeTypeCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left + 9,
            "top": $(tirgger).parent().position().top + 25,
            "z-index": 9999
        }).toggle();

        return false;
    });

    $(document).off('click', '#btnCaseFeeTypeCancel').on('click', '#btnCaseFeeTypeCancel', function () {
        $("#divCaseFeeTypeCheckBoxList").off().hide();
    });

    $(document).off('click', '#btnCaseFeeTypeSelected').on('click', '#btnCaseFeeTypeSelected', function () {

        var treeObj = $.fn.zTree.getZTreeObj("caseFeeTypeTree");
        var nodes = treeObj.getCheckedNodes(true);

        var feeTypeIds = new Array();
        var feeTypeNames = new Array();

        if (nodes.length > 0) {
            $.each(nodes, function (j, node) {
                feeTypeIds.push(node.id);
                feeTypeNames.push(node.name);
            });
            $("#SearchCondition_CaseFeeTypeId").val(feeTypeIds.join(','));
            $("#SearchCondition_CaseFeeTypeName").val(feeTypeNames.join(','));
        }
        else {
            $("#SearchCondition_CaseFeeTypeId").val('');
            $("#SearchCondition_CaseFeeTypeName").val('');
        }

        $("#divCaseFeeTypeCheckBoxList").off().hide();

        caseFee.PendingSettlementCaseFeeList();
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

    $(document).off('click', '#SearchCondition_CasePhaseName').on('click', '#SearchCondition_CasePhaseName', function () {
        var tirgger = this;

        //if ($("#SearchCondition_CaseTypeId").val() == "") {
        //    $.showTips("请选择案件类型.", 0, 3);
        //    return false;
        //};
        //var html = $.lsCasePhase.getcasePhaseListTreeHtml($("#SearchCondition_CaseTypeId").val());

        //var html = $.lsCasePhase.getcasePhaseListTreeHtml('110');

        var html = $.lsCasePhase.getAllCasePhaseListTreeHtml();

        $("#divCasePhaseCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left + 9,
            "top": $(tirgger).parent().position().top + 25,
            "z-index": 9999
        }).toggle();

        return false;
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

        caseFee.PendingSettlementCaseFeeList();
  
    });
 
    $(document).off('click', '#btnCaseFeeSearch').on('click', '#btnCaseFeeSearch', function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(15);

        caseFee.PendingSettlementCaseFeeList();
    });

    $(document).off('click', '#btnSettlemented').on('click', '#btnSettlemented', function () {
        caseFee.Settlemented();
    });
});


