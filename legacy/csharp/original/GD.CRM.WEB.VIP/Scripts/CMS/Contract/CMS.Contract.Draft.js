$(document).ready(function () {
    contract.Draft.Objects.Layout();
});

$("#btnContractObjectList").die().live("click", function () {

    $("#liContractObjectList").removeClass("active");
    $("#liContractEventList").removeClass("active");
    $("#liContractFileList").removeClass("active");
    $("#liContractAuditList").removeClass("active");

    $("#liContractObjectList").addClass("active");

    $("#dv_ContractObjectList").css('display', 'block');
    $("#dv_List").css('display', 'none');
    contract.ResetSize();
    //contract.Draft.Objects.Layout();
});

$("#btnContractEventList").die().live("click", function () {

    $("#liContractObjectList").removeClass("active");
    $("#liContractEventList").removeClass("active");
    $("#liContractFileList").removeClass("active");
    $("#liContractAuditList").removeClass("active");

    $("#liContractEventList").addClass("active");

    $("#dv_ContractObjectList").css('display', 'none');
    $("#dv_List").css('display', 'block');

    contract.Draft.Events.Layout();
});

$("#btnContractFileList").die().live("click", function () {
    $("#liContractObjectList").removeClass("active");
    $("#liContractEventList").removeClass("active");
    $("#liContractFileList").removeClass("active");

    if ($("#liContractAuditList").length > 1) {
        $("#liContractAuditList").removeClass("active");
    }

    $("#liContractFileList").addClass("active");

    $("#dv_ContractObjectList").css('display', 'none');
    $("#dv_List").css('display', 'block');

    contract.Draft.Files.Layout();
});

$("#btnContractAuditList").die().live("click", function () {
    $("#liContractObjectList").removeClass("active");
    $("#liContractEventList").removeClass("active");
    $("#liContractFileList").removeClass("active");
    $("#liContractAuditList").removeClass("active");

    $("#liContractAuditList").addClass("active");

    $("#dv_ContractObjectList").css('display', 'none');
    $("#dv_List").css('display', 'block');

    contract.Draft.Audits.Layout();
});

 

$(".item_CaseNo").die().live("keypress", function () {
    if (event.keyCode == 13) {
        if ($(this).val() == '') return false;
        $.case.getCaseBasicByCaseNo($(this), $(this).val(), contract.Draft.Objects.ObjectItem.getCaseBasicCallBack);
        event.stopPropagation();

        return false;
    }
});

$("#flContractFile").die().live("change", function () {
    $("#txtContractFilePath").val($("#flContractFile").val());
});

$("#btnContractFileUpload").die().live("click", function () {
    contract.Draft.Files.File.Upload();
});

$(".btn_contractfile_add").die().live("click", function () {
    contract.Draft.Files.File.Open();
});

$(".btn_contractfile_remove").die().live("click", function () {
    //contract.Draft.Files.File.Delete();
});

$("#btnContractFileCreate").die().live("click", function () {
    contract.Draft.Files.File.Open();
});

$("#btnContractEvent").die().live("click", function () {
    contract.Draft.Events.Event.Create();
});

$("#btnContractEventCreate").die().live("click", function () {
    contract.Draft.Events.Event.Open();
});

$("#btnContractEventCancel,#btnContractEventClose").die().live("click", function () {
    contract.Draft.Events.Event.Close();
});

$(".btn_contractevent_add").die().live("click", function () {
    contract.Draft.Events.Event.Open(this);
});

$(".btn_contractevent_remove").die().live("click", function () {
    contract.Draft.Events.Event.Delete(this);
});

$("#btnContractCreateUpdate").die().live("click", function () {
    contract.Draft.CreateUpdate(true);
});

$("#btnCustomerCaseCancel,#btnCustomerCaseClose").die().live("click", function () {
    caseInfo.Close();
});

$("#btnQuickCreateCaseCancel,#btnQuickCreateCaseClose").die().live("click", function () {
    caseInfo.QuickCase.Close();
});

$("#btnCustomerCase").die().live("click", function () {
    caseInfo.Selected();
});

$("#btnQuickCreateCase").die().live("click", function () {
    caseInfo.QuickCase.CreateUpdate();
});

$("#item_CaseOfficeFeeTypeId").die().live("change", function () {
    contract.Draft.Objects.ObjectItem.InitCaseOfficeFeeAnnualYear(this);
});

$("#btnContractFileUploadCancel,#btnContractFileUploadClose").die().live("click", function () {
    contract.Draft.Files.File.Close();
});