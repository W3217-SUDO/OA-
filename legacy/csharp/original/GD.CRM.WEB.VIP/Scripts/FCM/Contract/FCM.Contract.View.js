$(document).ready(function () {
    contract.Contract.Objects.Layout();
});

$(document).off('click', '#btnContractObjectList').on('click', '#btnContractObjectList', function () {
    $("#liContractObjectList").removeClass("active");
    $("#liContractEventList").removeClass("active");
    $("#liContractFileList").removeClass("active");
    $("#liContractAuditList").removeClass("active");

    $("#liContractObjectList").addClass("active");

    contract.Contract.Objects.Layout();
});

$(document).off('click', '#btnContractEventList').on('click', '#btnContractEventList', function () {
    $("#liContractObjectList").removeClass("active");
    $("#liContractEventList").removeClass("active");
    $("#liContractFileList").removeClass("active");
    $("#liContractAuditList").removeClass("active");

    $("#liContractEventList").addClass("active");

    contract.Draft.Events.Layout();
    //contract.Contract.Events.Layout();
});

$(document).off('click', '#btnContractFileList').on('click', '#btnContractFileList', function () {
    $("#liContractObjectList").removeClass("active");
    $("#liContractEventList").removeClass("active");
    $("#liContractFileList").removeClass("active");
    $("#liContractAuditList").removeClass("active");

    $("#liContractFileList").addClass("active");

    contract.Contract.Files.Layout();
});


$(document).off('click', '#btnContractAuditList').on('click', '#btnContractAuditList', function () {
    $("#liContractObjectList").removeClass("active");
    $("#liContractEventList").removeClass("active");
    $("#liContractFileList").removeClass("active");
    $("#liContractAuditList").removeClass("active");

    $("#liContractAuditList").addClass("active");

    contract.Contract.Audits.Layout();
});

$(document).off('click', '#btnContractExportToExcel').on('click', '#btnContractExportToExcel', function () {
    contract.Contract.ExportToExcel();
});

$(document).off('click', '#btnContractEvent').on('click', '#btnContractEvent', function () {
    contract.Draft.Events.Event.Create();
});

$(document).off('click', '#btnContractEventCreate').on('click', '#btnContractEventCreate', function () {
    contract.Draft.Events.Event.Open();
});

$(document).off('click', '#btnContractEventCancel,#btnContractEventClose').on('click', '#btnContractEventCancel,#btnContractEventClose', function () {
    contract.Draft.Events.Event.Close();
});

$(document).off('click', '.btn_contractevent_add').on('click', '.btn_contractevent_add', function () {
    contract.Draft.Events.Event.Open(this);
});

$(document).off('click', '.btn_contractevent_remove').on('click', '.btn_contractevent_remove', function () {
    contract.Draft.Events.Event.Delete(this);
});