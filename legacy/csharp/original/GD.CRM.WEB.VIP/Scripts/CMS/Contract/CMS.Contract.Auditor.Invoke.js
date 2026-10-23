$(document).ready(function () {
    if (window.location.href.toLowerCase().indexOf("ApprovedList".toLowerCase()) > 0) {
        contract.Auditor.ApprovedList();
    } else if (window.location.href.toLowerCase().indexOf("PendingList".toLowerCase()) > 0) {
        contract.Auditor.PendingList();
    } else if (window.location.href.toLowerCase().indexOf("RejectedList".toLowerCase()) > 0) {
        contract.Auditor.RejectedList();
    } 
});