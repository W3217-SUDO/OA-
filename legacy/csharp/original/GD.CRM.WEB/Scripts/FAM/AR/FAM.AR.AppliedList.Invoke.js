$(document).ready(function () {
    payment.Payment.Objects.AppliedList();

    $(document).click(function () {
        $("#divUserList").off().hide();
        $("#divPaymentTypeList").off().hide();
        $("#divAssociateUserList").off().hide();
        $("#divCasePhaseCheckBoxList").off().hide();
        $("#divCaseTypeCheckBoxList").off().hide();
        $("#divCaseFeeTypeCheckBoxList").off().hide();
    });
});

$(document).off('click', '#SearchCondition_CaseFeeTypeName').on('click', '#SearchCondition_CaseFeeTypeName', function () {
    var tirgger = this;
    var html = $.lsCaseFeeType.getCaseFeeTypeListTreeHtml();
    $("#divCaseFeeTypeCheckBoxList").css({
        "position": "absolute",
        "left": $(tirgger).parent().position().left + 9,
        "top": $(tirgger).parent().position().top + 260,
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

    caseFee.RefundList();
});

$(document).off('click', '#SearchCondition_CasePhaseName').on('click', '#SearchCondition_CasePhaseName', function () {
    debugger
    var tirgger = this;

    var html = $.lsCasePhase.getAllCasePhaseListTreeHtml();

    $("#divCasePhaseCheckBoxList").css({
        "position": "absolute",
        "left": $(tirgger).parent().position().left + 9,
        "top": $(tirgger).parent().position().top + 260,
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
});

$("#SearchCondition_CasePhaseName").off().on("click", function () {

    debugger
    var tirgger = this;
    var html = $.lsCasePhase.getCasePhaseCheckBoxListHtml();
    $(".divcaseconditioncasephases").html(html);
    $("#hidCasePhaseId").val("SearchCondition_CasePhaseId");
    $("#hidCasePhaseName").val("SearchCondition_CasePhaseName");
    $("#divCasePhaseCheckBoxList").css({
        "position": "absolute",
        "left": $(tirgger).parent().position().left + 16,
        "top": $(tirgger).parent().top + 25,
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

$("#SearchCondition_CaseTypeName").off().on("click", function () {
    var tirgger = this;
    var html = $.lsCaseType.getCaseTypeCheckBoxListHtml();
    $(".divcaseconditioncasetypes").html(html);
    $("#hidCaseTypeId").val("SearchCondition_CaseTypeId");
    $("#hidCaseTypeName").val($(tirgger).attr("id"));
    $("#divCaseTypeCheckBoxList").css({
        "position": "absolute",
        "left": $(tirgger).parent().position().left + 16,
        "top": $(tirgger).parent().top + 25,
        "z-index": 9999
    }).toggle();

    return false;
});

$(document).off('click', '#divCaseTypeCheckBoxList ul li').on('click', '#divCaseTypeCheckBoxList ul li', function (e) {
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
    $("#" + currentSelectedIdControl).val('');

    var caseTypeNames = '';
    var caseTypeIds = '';

    $("#divCaseTypeCheckBoxList").find("input:checkbox").each(function () {
        if ($(this).prop("checked") == true) {
            caseTypeNames += $(this).attr("casetypename") + ",";
            caseTypeIds += $(this).attr("casetypeid") + ",";
        }
    });

    $("#" + currentSelectedControl).val(caseTypeNames.substring(0, caseTypeNames.length - 1));
    $("#" + currentSelectedIdControl).val(caseTypeIds.substring(0, caseTypeIds.length - 1));

    e.stopPropagation();

    return true;
});

$(document).off('click', '#divCaseFeeTypeCheckBoxList ul li').on('click', '#divCaseFeeTypeCheckBoxList ul li', function (e) {
    //$("#divCaseFeeTypeCheckBoxList").find("li").off().on("click", function (e) {

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
    $("#" + currentSelectedIdControl).val('');

    var caseFeeTypeNames = '';
    var caseFeeTypeIds = '';

    $("#divCaseFeeTypeCheckBoxList").find("input:checkbox").each(function () {
        if ($(this).prop("checked") == true) {
            caseFeeTypeNames += $(this).attr("casefeetypename") + ",";
            caseFeeTypeIds += $(this).attr("casefeetypeid") + ",";
        }
    });

    $("#" + currentSelectedControl).val(caseFeeTypeNames.substring(0, caseFeeTypeNames.length - 1));
    $("#" + currentSelectedIdControl).val(caseFeeTypeIds.substring(0, caseFeeTypeIds.length - 1));

    e.stopPropagation();

    return true;
});
$("#SearchCondition_CaseFeeTypeName").off().on("click", function () {

    var tirgger = this;
    var html = $.lsCaseFeeType.getCaseFeeTypeCheckBoxListHtml();
    $(".divcaseconditioncasefeetypes").html(html);
    $("#hidCaseFeeTypeId").val("SearchCondition_CaseFeeTypeId");
    $("#hidCaseFeeTypeName").val($(tirgger).attr("id"));
    $("#divCaseFeeTypeCheckBoxList").css({
        "position": "absolute",
        "left": $(tirgger).parent().position().left + 16,
        "top": $(tirgger).parent().top + 25,
        "z-index": 9999
    }).toggle();

    return false;
});