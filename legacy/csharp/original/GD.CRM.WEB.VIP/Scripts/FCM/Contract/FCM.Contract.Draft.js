$(document).ready(function () {
    contract.Draft.Objects.Layout();
});

$("#btnContractObjectList").off().on("click", function () {

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

$("#btnContractEventList").off().on("click", function () {

    $("#liContractObjectList").removeClass("active");
    $("#liContractEventList").removeClass("active");
    $("#liContractFileList").removeClass("active");
    $("#liContractAuditList").removeClass("active");

    $("#liContractEventList").addClass("active");

    $("#dv_ContractObjectList").css('display', 'none');
    $("#dv_List").css('display', 'block');

    contract.Draft.Events.Layout();
});

$("#btnContractFileList").off().on("click", function () {
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

$("#btnContractAuditList").off().on("click", function () {
    $("#liContractObjectList").removeClass("active");
    $("#liContractEventList").removeClass("active");
    $("#liContractFileList").removeClass("active");
    $("#liContractAuditList").removeClass("active");

    $("#liContractAuditList").addClass("active");

    $("#dv_ContractObjectList").css('display', 'none');
    $("#dv_List").css('display', 'block');

    contract.Draft.Audits.Layout();
});

$(".item_CaseNo").off().on("keypress", function () {
    if (event.keyCode == 13) {
        if ($(this).val() == '') return false;
        $.case.getCaseBasicByCaseNoByOwner($(this), $(this).val(), contract.Draft.Objects.ObjectItem.getCaseBasicCallBack);
        event.stopPropagation();

        return false;
    }
});

$(".item_CaseRequestNo").off().on("keypress", function () {
    if (event.keyCode == 13) {
        if ($(this).val() == '') return false;
        $.case.getCaseBasicByCaseRequestNoByOwner($(this), $(this).val(), contract.Draft.Objects.ObjectItem.getCaseBasicCallBack);
        event.stopPropagation();

        return false;
    }
});

//$(".item_CaseNo").off().on("blur", function () {
//    if ($(this).val() == '') return false;
//    $.case.getCaseBasicByCaseNoByOwner($(this), $(this).val(), contract.Draft.Objects.ObjectItem.getCaseBasicCallBack);
//    event.stopPropagation();
//});

//$(".item_CaseRequestNo").off().on("blur", function () {
//    if ($(this).val() == '') return false;
//    $.case.getCaseBasicByCaseRequestNoByOwner($(this), $(this).val(), contract.Draft.Objects.ObjectItem.getCaseBasicCallBack);
//    event.stopPropagation();
//});

$("#flContractFile").off().on("change", function () {
    $("#txtContractFilePath").val($("#flContractFile").val());
});

$("#btnContractFileUpload").off().on("click", function () {
    contract.Draft.Files.File.Upload();
});

$(".btn_contractfile_add").off().on("click", function () {
    contract.Draft.Files.File.Open();
});

$(".btn_contractfile_remove").off().on("click", function () {
    //contract.Draft.Files.File.Delete();
});

$("#btnContractFileCreate").off().on("click", function () {
    contract.Draft.Files.File.Open();
});

$("#btnContractEvent").off().on("click", function () {
    contract.Draft.Events.Event.Create();
});

$("#btnContractEventCreate").off().on("click", function () {
    contract.Draft.Events.Event.Open();
});

$("#btnContractEventCancel,#btnContractEventClose").off().on("click", function () {
    contract.Draft.Events.Event.Close();
});

$(".btn_contractevent_add").off().on("click", function () {
    contract.Draft.Events.Event.Open(this);
});

$(".btn_contractevent_remove").off().on("click", function () {
    contract.Draft.Events.Event.Delete(this);
});

$(document).off('click', '#btnContractCreateUpdate').on('click', '#btnContractCreateUpdate', function () {
    contract.Draft.CreateUpdate(true);
});

$("#btnCustomerCaseCancel,#btnCustomerCaseClose").off().on("click", function () {
    caseInfo.Close();
});

$("#btnCustomerCase").off().on("click", function () {
    caseInfo.Selected();
});

$("#btnCaseSearch").off().on("click", function () {
    caseInfo.BulidCaseTreeView();
});

$("#item_CaseOfficeFeeTypeId").off().on("change", function () {
    contract.Draft.Objects.ObjectItem.InitCaseOfficeFeeAnnualYear(this);
});

$("#btnContractFileUploadCancel,#btnContractFileUploadClose").off().on("click", function () {
    contract.Draft.Files.File.Close();
});

$("#btnCaseCopy").off().on("click", function () {
    caseInfo.CaseCopy.Open();
});

$("#btnQuickCopyCaseClose,#btnQuickCopyCaseCancel").off().on("click", function () {
    caseInfo.CaseCopy.Close();
});

$("#btnQuickCopyCase").off().on("click", function () {
    caseInfo.CaseCopy.Copy();
});

 
$(document).off('click', '.btn_customer_add').on('click', '.btn_customer_add', function () {
    $.customer.Open(contract.Contract.Customer.AddIn);
});



