$(document).ready(function () {
    $(document).click(function () {
        $("#divCasePhaseCheckBoxList").off().hide();
    });
    caseFee.RefundList();
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

        caseFee.RefundList();
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

        if ($("#SearchCondition_PageId").val() == '5001010001') {
            //debugger
            caseFee.RefundList();
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
    $(document).off('click', '#btnRefundStatusChange').on('click', '#btnRefundStatusChange', function () {

        var caseFeeIds = [];
        $("input[name='chkCaseId']:checked").each(
            function (i) { caseFeeIds[i] = $(this).attr("caseFeeId"); }
        );

        if (caseFeeIds.length < 1) {
            $.showModalMessageBox("请选择需要跟进的费用.");
            return false;
        }

        c.Cases.Case.CaseFees.RefundStatus.Open(caseFeeIds);
    });
    $(document).off('click', '#btnRefundStatusUpdate').on('click', '#btnRefundStatusUpdate', function () {
        var caseFeeIds = [];
        $("input[name='chkCaseId']:checked").each(
            function (i) { caseFeeIds[i] = $(this).attr("caseFeeId"); }
        );
        if (caseFeeIds.length < 1) {
            $.showModalMessageBox("请选择需要跟进的费用.");
            return false;
        }
        c.Cases.Case.CaseFees.RefundStatus.Change(caseFeeIds, $("#RefundStatus").val());
    });

    $(document).off('click', '#btnRefundNotRequired').on('click', '#btnRefundNotRequired', function () {
        var caseFeeIds = [];
        $("input[name='chkCaseId']:checked").each(
            function (i) { caseFeeIds[i] = $(this).attr("caseFeeId"); }
        );
        if (caseFeeIds.length < 1) {
            $.showModalMessageBox("请选择需要跟进的费用.");
            return false;
        }
        c.Cases.Case.CaseFees.RefundStatus.NotRequired(caseFeeIds);
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
        caseFee.RefundList();
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
        caseFee.RefundList();
    });
});
