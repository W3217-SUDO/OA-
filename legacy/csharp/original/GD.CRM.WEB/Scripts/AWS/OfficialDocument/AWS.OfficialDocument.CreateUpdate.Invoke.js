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

$(document).ready(function () {
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
 