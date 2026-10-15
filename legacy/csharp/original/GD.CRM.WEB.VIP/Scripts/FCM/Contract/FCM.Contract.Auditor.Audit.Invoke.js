$(document).ready(function () {
    contract.Draft.Files.Layout();

    $(document).off('click', '#btnContractAuditApproved').on('click', '#btnContractAuditApproved', function () {
        contract.Contract.Audits.Audit.CreateUpdate(3);
    });

    $(document).off('click', '#btnContractAuditRejected').on('click', '#btnContractAuditRejected', function () {
        contract.Contract.Audits.Audit.CreateUpdate(4);
    });
});