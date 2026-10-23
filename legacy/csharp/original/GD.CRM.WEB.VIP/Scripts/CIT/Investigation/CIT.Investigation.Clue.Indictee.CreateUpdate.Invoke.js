function initBusinessNatureType()
{
    if ($("#InvestigationClueIndictee_BusinessNatureType").val() == 'E') {
        $(".divlegalRepresentative").show();
        $(".indicteeLicenseNo").text("证照号码：");
        $(".legalRepresentative").text("法人：");
        $("#InvestigationClueIndictee_LegalRepresentative").attr("placeholder", "请输入法定代表人");
        $("#InvestigationClueIndictee_IndicteeLicenseNo").attr("placeholder", "请输入统一社会信用代码");
     }
    else if ($("#InvestigationClueIndictee_BusinessNatureType").val() == 'P') {
        $(".divlegalRepresentative").hide();
        $(".indicteeLicenseNo").text("身份证号：");
        $("#InvestigationClueIndictee_IndicteeLicenseNo").attr("placeholder", "请输入身份证号");
    }
    else if ($("#InvestigationClueIndictee_BusinessNatureType").val() == 'I') {
        $(".divlegalRepresentative").show();
        $(".indicteeLicenseNo").text("证照号码：");
        $(".legalRepresentative").text("经营者：");
        
        $("#InvestigationClueIndictee_LegalRepresentative").attr("placeholder", "请输入经营者");
        $("#InvestigationClueIndictee_IndicteeLicenseNo").attr("placeholder", "请输入统一社会信用代码");
    }
}

$(document).ready(function () {

    $(document).off('change', '#InvestigationClueIndictee_BusinessNatureType').on('change', '#InvestigationClueIndictee_BusinessNatureType', function () {
        initBusinessNatureType()
    });
});