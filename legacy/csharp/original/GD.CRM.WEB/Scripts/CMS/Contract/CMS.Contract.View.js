$(document).ready(function () {
    contract.Contract.Objects.Layout();
});

$("#btnContractObjectList").die().live("click", function () {

    $("#liContractObjectList").removeClass("active");
    $("#liContractEventList").removeClass("active");
    $("#liContractFileList").removeClass("active");
    $("#liContractAuditList").removeClass("active");

    $("#liContractObjectList").addClass("active");

    contract.Contract.Objects.Layout();
});

$("#btnContractEventList").die().live("click", function () {
    $("#liContractObjectList").removeClass("active");
    $("#liContractEventList").removeClass("active");
    $("#liContractFileList").removeClass("active");
    $("#liContractAuditList").removeClass("active");

    $("#liContractEventList").addClass("active");

    contract.Contract.Events.Layout();
});


$("#btnContractFileList").die().live("click", function () {
    $("#liContractObjectList").removeClass("active");
    $("#liContractEventList").removeClass("active");
    $("#liContractFileList").removeClass("active");
    $("#liContractAuditList").removeClass("active");

    $("#liContractFileList").addClass("active");

    contract.Contract.Files.Layout();
});

$("#btnContractAuditList").die().live("click", function () {
    $("#liContractObjectList").removeClass("active");
    $("#liContractEventList").removeClass("active");
    $("#liContractFileList").removeClass("active");
    $("#liContractAuditList").removeClass("active");

    $("#liContractAuditList").addClass("active");

    contract.Contract.Audits.Layout();
});

$("#btnContractExportToExcel").die().live("click", function () {
    contract.Contract.ExportToExcel();
});