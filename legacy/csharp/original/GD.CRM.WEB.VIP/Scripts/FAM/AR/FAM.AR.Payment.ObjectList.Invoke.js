$(document).ready(function () {
    
    if ($("#SearchCondition_PageId").val() == '5001008001') {
        debugger
        payment.Payment.ArchiveSettlement.PendingList();
    }
    else if ($("#SearchCondition_PageId").val() == '5001008002') {
        payment.Payment.ArchiveSettlement.ProcessingList();;
    }
    else if ($("#SearchCondition_PageId").val() == '5001008003') {
        payment.Payment.ArchiveSettlement.ProcessedList();
    }
    else if ($("#SearchCondition_PageId").val() == '5001008004') {
        payment.Payment.ArchiveSettlement.RejectedList();
    }

    $(document).click(function () {
        $("#divCasePhaseCheckBoxList").off().hide();
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

        if ($("#SearchCondition_CaseTypeId").val() == "") {
            $.showTips("请选择案件类型.", 0, 3);
            return false;
        };
        var html = $.lsCasePhase.getcasePhaseListTreeHtml($("#SearchCondition_CaseTypeId").val());

        $("#divCasePhaseCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left + 16,
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

        if ($("#SearchCondition_PageId").val() == '5001008001') {
            debugger
            payment.Payment.ArchiveSettlement.PendingList();
        }
        else if ($("#SearchCondition_PageId").val() == '5001008002') {
            payment.Payment.ArchiveSettlement.ProcessingList();;
        }
        else if ($("#SearchCondition_PageId").val() == '5001008003') {
            payment.Payment.ArchiveSettlement.ProcessedList();
        }
        else if ($("#SearchCondition_PageId").val() == '5001008004') {
            payment.Payment.ArchiveSettlement.RejectedList();
        }
    });

    $(document).off('click', '#btnPaymentObjectPendingListSearch').on('click', '#btnPaymentObjectPendingListSearch', function () {
        payment.Payment.ArchiveSettlement.PendingList();
    });
    $(document).off('click', '#btnPaymentObjectProcessingListSearch').on('click', '#btnPaymentObjectProcessingListSearch', function () {
        payment.Payment.ArchiveSettlement.ProcessingList();
    });
    $(document).off('click', '#btnPaymentObjectProcessedListSearch').on('click', '#btnPaymentObjectProcessedListSearch', function () {
        payment.Payment.ArchiveSettlement.ProcessedList();
    });
    $(document).off('click', '#btnPaymentObjectRejectedListSearch').on('click', '#btnPaymentObjectRejectedListSearch', function () {
        payment.Payment.ArchiveSettlement.RejectedList();
    });
});

