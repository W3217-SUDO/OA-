$(document).ready(function () {
    
    $("#Contract_ContractBasicInfo_Auditor").chosen({
        width: '100%',
        disable_search: false,
        search_contains: true
    });

    contract.Draft.Files.Layout();
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


$(document).off('click', '#Contract_ContractBasicInfo_AuditorName').on('click', '#Contract_ContractBasicInfo_AuditorName', function () {
    $("#hidUserId").val("Contract_ContractBasicInfo_Auditor");
    $("#hidUserName").val("Contract_ContractBasicInfo_AuditorName");
    $("#divAuditorList").css({
        "position": "absolute",
        "left": $("#Contract_ContractBasicInfo_AuditorName").position().left + 1,
        "top": $("#Contract_ContractBasicInfo_AuditorName").position().top + 28,
        "z-index": 1200
    }).toggle();
    return false;
});


$(document).off('click', '#divAuditorList ul li').on('click', '#divAuditorList ul li', function (i, e) {
    var currentSelectedControl = $("#hidUserName").val();
    var currentSelectedIdControl = $("#hidUserId").val();
    if ($(this).attr("id") == 'btnClear') {
        $("#" + currentSelectedControl).val('');
        $("#" + currentSelectedIdControl).val('');
        return false;
    }
    var userId = $(this).find("a").attr("name");
    var userName = $(this).find("a").text();
    $("#" + currentSelectedControl).val(userName);
    $("#" + currentSelectedIdControl).val(userId);
    $("#divAuditorList").hide();
    return false;
});


$(document).off('click', '#btnContractToAudit').on('click', '#btnContractToAudit', function () {
    contract.Contract.Audits.Audit.ToAudit();
});


$(document).off('click', '#flContractFile').on('change', '#flContractFile', function () {
    $("#txtContractFilePath").val($("#flContractFile").val());
});

$(document).off('click', '#btnContractFileUpload').on('click', '#btnContractFileUpload', function () {
    contract.Draft.Files.File.Upload();
});

$(document).off('click', '.btn_contractfile_add').on('click', '.btn_contractfile_add', function () {
    contract.Draft.Files.File.Open();
});

$(document).off('click', '#btnContractFileCreate').on('click', '#btnContractFileCreate', function () {
    contract.Draft.Files.File.Open();
});

$(document).off('click', '#btnContractFileUploadCancel,#btnContractFileUploadClose').on('click', '#btnContractFileUploadCancel,#btnContractFileUploadClose', function () {
    contract.Draft.Files.File.Close();
});