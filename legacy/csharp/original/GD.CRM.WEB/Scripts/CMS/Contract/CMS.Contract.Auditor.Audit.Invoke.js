$(document).ready(function () {
    contract.Contract.Objects.Layout();

    $("#btnContractAuditApproved").die().live("click", function () {
        contract.Contract.Audits.Audit.CreateUpdate(3);
    });

    $("#btnContractAuditRejected").die().live("click", function () {
        contract.Contract.Audits.Audit.CreateUpdate(4);
    });
});