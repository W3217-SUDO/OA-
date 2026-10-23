function initBusinessType() {
    $("#InvestigationClue_Basic_StoreName").attr("placeholder", "请输入店铺名称");
    $("#InvestigationClue_Basic_StoreName").parent().parent().prev().find("label").text("店铺名称：");

    if ($("#InvestigationClue_Basic_BusinessType").val() == 'E_EC' || $("#InvestigationClue_Basic_BusinessType").val() == 'E_WL') {
        if ($("#InvestigationClue_Basic_BusinessType").val() == 'E_EC') {
            $("#InvestigationClue_Basic_StoreUrl").attr("placeholder", "请输入店铺链接");
            $("#InvestigationClue_Basic_StoreUrl").parent().parent().prev().find("label").text("店铺链接：");
        }

        if ($("#InvestigationClue_Basic_BusinessType").val() == 'E_WL') {
            $("#InvestigationClue_Basic_StoreUrl").attr("placeholder", "请输入网页链接");
            $("#InvestigationClue_Basic_StoreUrl").parent().parent().prev().find("label").text("网页链接：");
        }

        if ($("#InvestigationClue_Basic_HasProduct_0").attr("checked") == "checked") {
            $(".e_ec_production").show();
            $(".production").show();
            $(".producer").show();

            if ($("#InvestigationClue_Product_HasProducer_0").attr("checked") == "checked") {
                $(".producerinfo").show();
            }
            else {
                $(".producerinfo").hide();
            }
        }
        else {
            $(".e_ec_production").hide();
            $(".production").hide();
            $(".producer").hide();
            $(".producerinfo").hide();

        }
       
        $(".e_ec").show();
        $(".s_st").hide();
    }
    else if ($("#InvestigationClue_Basic_BusinessType").val() == 'S_ST' || $("#InvestigationClue_Basic_BusinessType").val() == 'S_FA' || $("#InvestigationClue_Basic_BusinessType").val() == 'S_OT') {

        if ($("#InvestigationClue_Basic_BusinessType").val() == 'S_FA') {
            $("#InvestigationClue_Basic_StoreName").attr("placeholder", "请输入工厂名称");
            $("#InvestigationClue_Basic_StoreName").parent().parent().prev().find("label").text("工厂名称：");
        }

        if ($("#InvestigationClue_Basic_HasProduct_0").attr("checked") == "checked") {
            $(".e_ec_production").hide();
            $(".production").show();
            $(".producer").show();

            if ($("#InvestigationClue_Product_HasProducer_0").attr("checked") == "checked") {
                $(".producerinfo").show();
            }
            else {
                $(".producerinfo").hide();
            }
        }
        else {
            $(".production").hide();
            $(".producer").hide();
            $(".producerinfo").hide();
            $(".e_ec_production").hide();
        }

       
        $(".e_ec").hide();
        $(".s_st").show();
    }
}

function init()
{
    var data = {
        investigationClueNo: $("#InvestigationClue_Basic_ClueNo").val(),
    };
    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/GetInvestigationClue", data, function (response) {
        if (response.IsSuccess) {

            var investigationClue = response.Data.Basic;
            var investigationClueProduct = response.Data.Product;
            var investigationClueIndicteeList = response.Data.InvestigationClueIndicteeList;
            var investigationClueProducerList = response.Data.InvestigationClueProducerList;

            var investigationClueFileList = response.Data.InvestigationClueFileList;
            
            if (investigationClue.HasTort) {
                $("#InvestigationClue_Basic_HasTort_0").parents(".radio-item").click()
            }
            else {
                $("#InvestigationClue_Basic_HasTort_1").parents(".radio-item").click()
            }

            if (investigationClue.HasProduct) {
                $("#InvestigationClue_Basic_HasProduct_0").parents(".radio-item").click()
            }
            else {
                $("#InvestigationClue_Basic_HasProduct_1").parents(".radio-item").click()
            }

            if (investigationClueProduct.HasProducer) {
                $("#InvestigationClue_Product_HasProducer_0").parents(".radio-item").click()
            }
            else{
                $("#InvestigationClue_Product_HasProducer_1").parents(".radio-item").click()
            }

            $("#InvestigationClue_Product_ProductId").val(investigationClueProduct.ProductId);
            $("#InvestigationClue_Product_ProductName").val(investigationClueProduct.ProductName);
            $("#InvestigationClue_Product_SaleNum").val(investigationClueProduct.SaleNum);
            $("#InvestigationClue_Product_ProductUrl").val(investigationClueProduct.ProductUrl);

            $("#InvestigationClue_Basic_Remark").val(investigationClue.Remark);

            if (investigationClue.District != '' && investigationClue.District != null) {
                $('#investigationClue_district').citys({ code: investigationClue.District });
            }
            else if (investigationClue.City != '' && investigationClue.City != null) {
                $('#investigationClue_district').citys({ code: investigationClue.City });
            }
            else if (investigationClue.Province != '' && investigationClue.Province != null) {
                $('#investigationClue_district').citys({ code: investigationClue.Province });
            }

            if (investigationClueIndicteeList != null && investigationClueIndicteeList.length > 0) {
                $.each(investigationClueIndicteeList, function (i, indictee) {
                    investigation.Investigations.Investigation.Clues.Clue.Indictees.Indictee.AddIn(indictee);
                });
            }

            //debugger
            if (investigationClue.Investigators != null && investigationClue.Investigators.length > 0) {
                var investigatorNames = investigationClue.InvestigatorNames.split(",");
                $.each(investigationClue.Investigators.split(','), function (i, investigator) {
                    investigation.Investigations.Investigation.Clues.Clue.Investigators.Investigator.AddIn(investigator, investigatorNames[i]);
                });
            }
            
            if (investigationClueProducerList != null && investigationClueProducerList.length > 0) {
                $.each(investigationClueProducerList, function (i, producer) {
                    investigation.Investigations.Investigation.Clues.Clue.Producers.Producer.AddIn(producer);
                });
            }
            
            if (investigationClueFileList != null && investigationClueFileList.length > 0) {
                $.each(investigationClueFileList, function (i, file) {
                    investigation.Investigations.Investigation.Clues.Clue.Files.File.AddIn(file);
                });
            }

            initBusinessType();

        } else {
            $.showModalMessageBox(response.Message);
        }
    });
}

$(document).ready(function () {

    init();

    $(document).off('change', '#InvestigationClue_Basic_BusinessType').on('change', '#InvestigationClue_Basic_BusinessType', function () {
        initBusinessType()
    });

    $(document).off('click', 'div#producer .radio-item")').on('click', 'div#producer .radio-item', function () {

        $('div#producer .radio-item').each(function (i, e) {
            $(e).find("label").removeClass("checked");
            $(e).find("label>span").removeClass("checked");
            $(e).find("label>span>input").attr("checked", false);
        });


        $(this).find("label").addClass("checked");
        $(this).find("label>span").addClass("checked");
        $(this).find("label>span>input").attr("checked", true);

        initBusinessType();
    });

    $(document).off('click', 'div#production .radio-item")').on('click', 'div#production .radio-item', function () {

        $('div#production .radio-item').each(function (i, e) {
            $(e).find("label").removeClass("checked");
            $(e).find("label>span").removeClass("checked");
            $(e).find("label>span>input").attr("checked", false);
        });

        $(this).find("label").addClass("checked");
        $(this).find("label>span").addClass("checked");
        $(this).find("label>span>input").attr("checked", true);

        
        initBusinessType();


    });

    $(document).off('click', 'div#tort .radio-item")').on('click', 'div#tort .radio-item', function () {
        $('div#tort .radio-item').each(function (i, e) {
            $(e).find("label").removeClass("checked");
            $(e).find("label>span").removeClass("checked");
            $(e).find("label>span>input").attr("checked", false);
        });

        $(this).find("label").addClass("checked");
        $(this).find("label>span").addClass("checked");
        $(this).find("label>span>input").attr("checked", true);
    });
});