$(document).ready(function () {
    contract.Archive.Objects.Layout();
});

$("#btnContractArchived").off().on("click", function () {
    contract.Archive.Archived(true);
});
