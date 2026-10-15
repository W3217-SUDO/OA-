$(document).ready(function () {
    contract.Archive.Objects.Layout();
});

$("#btnContractArchived").die().live("click", function () {
    contract.Archive.Archived(true);
});
