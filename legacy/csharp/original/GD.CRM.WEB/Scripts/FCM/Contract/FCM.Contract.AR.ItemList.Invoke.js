$(document).ready(function () {

    $(document).click(function () {
        //$("#divCaseFeeTypeCheckBoxList").off().hide();
    });

    contract.List.ARItemList();

    contract.ResetSize();

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

        contract.List.ARItemList();
    });
});