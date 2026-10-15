$(document).ready(function () {

    var province = $("#Customer_CustomerBasic_Province").val();
    var city = $("#Customer_CustomerBasic_City").val();
    $('#district').citys({ code: city });

    customer.Customer.CustomerContacts.List(false);
});

$(document).off('click', '#btnCustomerContactsList').on('click', '#btnCustomerContactsList', function () {
    $("#liCustomerContactsList").removeClass("active");
    $("#liCustomerEventList").removeClass("active");
    $("#liCustomerFileList").removeClass("active");
    $("#liCustomerContactsList").addClass("active");

    $("#dv_List").css('display', 'block');
    customer.ResetSize();
    customer.Customer.CustomerContacts.List(false);
});

$(document).off('click', '#btnCustomerEventList').on('click', '#btnCustomerEventList', function () {
    $("#liCustomerContactsList").removeClass("active");
    $("#liCustomerEventList").removeClass("active");
    $("#liCustomerFileList").removeClass("active");
    $("#liCustomerEventList").addClass("active");

    $("#dv_List").css('display', 'block');

    customer.Customer.Events.Layout();
});

$(document).off('click', '#btnCustomerFileList').on('click', '#btnCustomerFileList', function () {
    $("#liCustomerContactsList").removeClass("active");
    $("#liCustomerEventList").removeClass("active");
    $("#liCustomerFileList").removeClass("active");

    if ($("#liCustomerAuditList").length > 1) {
        $("#liCustomerAuditList").removeClass("active");
    }

    $("#liCustomerFileList").addClass("active");

    //$("#dv_CustomerContactsList").css('display', 'none');
    $("#dv_List").css('display', 'block');

    customer.Customer.Files.Layout();
});

$(document).off('click', '#btnCustomerAuditList').on('click', '#btnCustomerAuditList', function () {
    $("#liCustomerContactsList").removeClass("active");
    $("#liCustomerEventList").removeClass("active");
    $("#liCustomerFileList").removeClass("active");
    $("#liCustomerAuditList").removeClass("active");

    $("#liCustomerAuditList").addClass("active");

    //$("#dv_CustomerContactsList").css('display', 'none');
    $("#dv_List").css('display', 'block');

    customer.Customer.Audits.Layout();
});

$(document).off('click', '.btn_ar_add').on('click', '.btn_ar_add', function () {
    customer.Customer.Objects.ObjectItem.Add(this);
});

$(document).off('click', '.btn_ar_remove').on('click', '.btn_ar_remove', function () {
    customer.Customer.Objects.ObjectItem.Remove(this);
});

$(document).off('click', '.btn_ar_edit').on('click', '.btn_ar_edit', function () {
    customer.Customer.Objects.ObjectItem.Edit(this);
});

$(document).off('click', '#flCustomerFile').on('click', '#flCustomerFile', function () {
    $("#txtCustomerFilePath").val($("#flCustomerFile").val());
});

$(document).off('click', '#btnCustomerFileUpload').on('click', '#btnCustomerFileUpload', function () {
    customer.Customer.Files.File.Upload();
});

$(document).off('click', '.btn_customerfile_add').on('click', '.btn_customerfile_add', function () {
    customer.Customer.Files.File.Open();
});

$(document).off('click', '.btn_customerfile_remove').on('click', '.btn_customerfile_remove', function () {
    //customer.Customer.Files.File.Delete();
});

$(document).off('click', '#btnCustomerFileCreate').on('click', '#btnCustomerFileCreate', function () {
    customer.Customer.Files.File.Open();
});

$(document).off('click', '#btnCustomerEvent').on('click', '#btnCustomerEvent', function () {
    customer.Customer.Events.Event.Create();
});

$(document).off('click', '#btnCustomerEventCreate').on('click', '#btnCustomerEventCreate', function () {
    customer.Customer.Events.Event.Open();
});

$(document).off('click', '#btnCustomerEventCancel,#btnCustomerEventClose').on('click', '#btnCustomerEventCancel,#btnCustomerEventClose', function () {
    customer.Customer.Events.Event.Close();
});

$(document).off('click', '.btn_customerevent_add').on('click', '.btn_customerevent_add', function () {
    customer.Customer.Events.Event.Open(this);
});

$(document).off('click', '.btn_customerevent_remove').on('click', '.btn_customerevent_remove', function () {
    customer.Customer.Events.Event.Delete(this);
});

$(document).off('click', '#btnCustomerCreateUpdate').on('click', '#btnCustomerCreateUpdate', function () {
    customer.Customer.CreateUpdate(true);
});

$(document).off('click', '#btnCustomerCaseCancel,#btnCustomerCaseClose').on('click', '#btnCustomerCaseCancel,#btnCustomerCaseClose', function () {
    caseInfo.Close();
});

$(document).off('click', '#btnQuickCreateCaseCancel,#btnQuickCreateCaseClose').on('click', '#btnQuickCreateCaseCancel,#btnQuickCreateCaseClose', function () {
    caseInfo.QuickCase.Close();
});

$(document).off('click', '#btnCustomerCase').on('click', '#btnCustomerCase', function () {
    caseInfo.Selected();
});

$(document).off('click', '#btnQuickCreateCase').on('click', '#btnQuickCreateCase', function () {
    caseInfo.QuickCase.CreateUpdate();
});

$(document).off('change', '#item_CaseOfficeFeeTypeId').on('change', '#item_CaseOfficeFeeTypeId', function () {
    customer.Customer.Objects.ObjectItem.InitCaseOfficeFeeType(this);
});

$(document).off('click', '#btnCustomerFileUploadCancel,#btnCustomerFileUploadClose').on('click', '#btnCustomerFileUploadCancel,#btnCustomerFileUploadClose', function () {
    customer.Customer.Files.File.Close();
});