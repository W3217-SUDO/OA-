$(document).ready(function () {
    $("#btnEvidenceFileUpload").click(function () {
        investigation.Investigations.Investigation.Evidences.Evidence.Files.File.InUpload();
    });

    $("#btnEvidenceAddInFileUpload").click(function () {
        investigation.Investigations.Investigation.Evidences.Evidence.AddIn.FileUpload();
    });

    $("#btnEvidenceInvoiceFileUpload").click(function () {
        investigation.Investigations.Investigation.Evidences.Evidence.Files.InvoiceFile.Upload();
    });

    $("#flZip").change(function () {
        $("#txtFilePath").val($("#flZip").val());
    });

    $(document).off('click', '#chkInvestigationClueEvidenceAll').on('click', '#chkInvestigationClueEvidenceAll', function () {
        if ($(this).prop('checked') == true) {
            $.checkbox.all("chkInvestigationClueEvidenceId");

        } else {
            $.checkbox.not("chkInvestigationClueEvidenceId");
        }
    });

    $(document).off('click', '#btnEvidenceFileIn').on('click', '#btnEvidenceFileIn', function () {
        investigation.Investigations.Investigation.Evidences.Evidence.Files.File.In();
    });
    
    $(document).off('click', '#btnEvidenceAddInFileIn').on('click', '#btnEvidenceAddInFileIn', function () {
        investigation.Investigations.Investigation.Evidences.Evidence.AddIn.In();
    });

    $(document).off('click', '#btnEvidenceInvoiceFileIn').on('click', '#btnEvidenceInvoiceFileIn', function () {
        investigation.Investigations.Investigation.Evidences.Evidence.Files.InvoiceFile.In();
    });

});