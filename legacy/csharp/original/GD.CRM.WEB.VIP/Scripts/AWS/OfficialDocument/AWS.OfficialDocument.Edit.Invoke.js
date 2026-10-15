function initSealType() {
    if ($("#OfficialDocument_Basic_OfficialDocumentType_1").attr("checked") == "checked") {
        $(".case").hide();
        $(".contract").show();
        $(".customer").show();
    }
    else if ($("#OfficialDocument_Basic_OfficialDocumentType_2").attr("checked") == "checked") {
        $(".case").show();
        $(".contract").hide();
        $(".customer").show();
    }
    else {
        $(".case").hide();
        $(".contract").hide();
        $(".customer").hide();
    }
}
function init()
{
    var data = {
        officialDocumentNo: $("#OfficialDocument_Basic_OfficialDocumentNo").val(),
    };
    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocument/GetOfficialDocument", data, function (response) {
        if (response.IsSuccess) {
            var document = response.Data.Basic;
            var officialDocumentFileList = response.Data.OfficialDocumentFileList;
            
            if (document.IsElectronicSeal) {
                $("#OfficialDocument_Basic_IsElectronicSeal_0").parents(".radio-item").click()
            }
            else {
                $("#OfficialDocument_Basic_IsElectronicSeal_1").parents(".radio-item").click()
            }

            if (document.IsOfflinePrint) {
                $("#OfficialDocument_Basic_IsOfflinePrint_1").parents(".radio-item").click()
            }
            else {
                $("#OfficialDocument_Basic_IsOfflinePrint_0").parents(".radio-item").click()
            }

            if (document.OfficialDocumentType == "10") {
                $("#OfficialDocument_Basic_OfficialDocumentType_1").parents(".radio-item").click();
                contract.Contracts.Contract.ContractNo.AddIn(document.ContractNo);
           }
            else if (document.OfficialDocumentType == "20") {
                $("#OfficialDocument_Basic_OfficialDocumentType_2").parents(".radio-item").click();
                c.Cases.Case.CaseNo.AddIn(document.CaseNo);
            }
            else if (document.OfficialDocumentType == "30") {
                $("#OfficialDocument_Basic_OfficialDocumentType_3").parents(".radio-item").click()
            }

            debugger
            $("#OfficialDocument_Basic_Remark").val(document.Remark);
            
            if (officialDocumentFileList != null && officialDocumentFileList.length > 0) {
                $.each(officialDocumentFileList, function (i, file) {
                    officialDocument.OfficialDocuments.OfficialDocument.Files.File.AddIn(file);
                });
            }
        } else {
            $.showModalMessageBox(response.Message);
        }
    });
}

$(document).ready(function () {
    init();
    initSealType();
    $(document).off('click', 'div#officialDocumentType .radio-item")').on('click', 'div#officialDocumentType .radio-item', function () {
        $('div#officialDocumentType .radio-item').each(function (i, e) {
            $(e).find("label").removeClass("checked");
            $(e).find("label>span").removeClass("checked");
            $(e).find("label>span>input").attr("checked", false);
        });

        $(this).find("label").addClass("checked");
        $(this).find("label>span").addClass("checked");
        $(this).find("label>span>input").attr("checked", true);

        initSealType();
    });

    $(document).off('click', 'div#offlineprint .radio-item")').on('click', 'div#offlineprint .radio-item', function () {
        $('div#offlineprint .radio-item').each(function (i, e) {
            $(e).find("label").removeClass("checked");
            $(e).find("label>span").removeClass("checked");
            $(e).find("label>span>input").attr("checked", false);
        });

        $(this).find("label").addClass("checked");
        $(this).find("label>span").addClass("checked");
        $(this).find("label>span>input").attr("checked", true);

        initSealType();
    });

    $(document).off('click', 'div#electronicseal .radio-item")').on('click', 'div#electronicseal .radio-item', function () {
        $('div#electronicseal .radio-item').each(function (i, e) {
            $(e).find("label").removeClass("checked");
            $(e).find("label>span").removeClass("checked");
            $(e).find("label>span>input").attr("checked", false);
        });

        $(this).find("label").addClass("checked");
        $(this).find("label>span").addClass("checked");
        $(this).find("label>span>input").attr("checked", true);

        initSealType();
    });
});