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

$(document).ready(function () {
    $('#investigationClue_district').citys();
    initBusinessType();
    var investigator = new AssociateAvailableUserForClue(
      $("#div_investigatorlist"),
      $("#InvestigationClue_Investigator_Input"),
      $("#InvestigationClue_Investigator_Input"),
       investigation.Investigations.Investigation.Clues.Clue.Investigators.Investigator.AddIn
  );

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
 