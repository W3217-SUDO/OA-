$(document).ready(function() {
    contract.List.ContractList();
    $(document).off('click', '#btnContractToOfficialDocumentAudit').on('click', '#btnContractToOfficialDocumentAudit', function () {
        var chkContractIds = $.checkbox.vals("chkContractId");
        if (chkContractIds.length < 1) {
            $.showTips("请选择合同.", 0, 3);
            return false;
        }
        var contractNo = $($("input[name='chkContractId']:checked")[0]).attr("contractno");
        officialDocument.OfficialDocuments.OfficialDocument.CreateByContract(contractNo, '');
    });
});
