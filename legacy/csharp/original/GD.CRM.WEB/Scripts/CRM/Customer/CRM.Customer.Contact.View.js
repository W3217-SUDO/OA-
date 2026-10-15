$(document).ready(function () {
    $(":input", "#customerContactsForm").each(function () {
        $(this).attr("disabled", "disabled");
    });
});
 