/// <reference path="FAM.AR.Detail.List.js" />

var ar = {

    ResetSize: function () {

        $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top);

        $(function () {
            $('#divContextList').slimScroll({
                height: $("#divContextList").height()
        });
        });
    },

    List: function () {

        if ($("#SearchCondition_CustomerName").val() == '' &&  $("#SearchCondition_ContractNo").val() == '') {
            $.showModalMessageBox("请输入客户或合同号查询条件.");
            return false;
        }

        $("#postForm").ajaxPost(AP_ROOT + "FAM/AR/Details", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblARList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.ContractList, function (i, c) {
                        $("tbody", "#tblARList").addRow(
                            c.ContractBasicInfo.ContractNo,
                            "<span style='width: 180px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.ContractBasicInfo.CustomerName + "</span>",
                            c.CaseList.length,
                            c.ContractBasicInfo.TotalAmount,
                            c.ContractBasicInfo.ARAmount,
                            c.ContractBasicInfo.ARCaseOfficeFeeAmount,
                            c.ContractBasicInfo.ARCaseNonOfficeFeeAmount,
                            c.ContractBasicInfo.CashedAmount,
                            c.ContractBasicInfo.BusinessOwnerName,
                            c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate))
                        );

                        $.each(c.CaseList, function (j, caseInfo) {
          
                                $("tbody", "#tblARList").addRow(
                                    '',
                                   '',
                                   caseInfo.CaseBasicInfo.CaseNo,
                                    caseInfo.CaseBasicInfo.TotalAmount,
                                    caseInfo.CaseBasicInfo.ARAmount,
                                    caseInfo.CaseBasicInfo.ARCaseOfficeFeeAmount,
                                    caseInfo.CaseBasicInfo.ARCaseNonOfficeFeeAmount,
                                    caseInfo.CaseBasicInfo.CashedAmount,
                                    c.ContractBasicInfo.BusinessOwnerName,
                                    c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate))
                                );
                        });
                    });

                    $("tfoot", "#tblARList").hide();
                    $(".simple-grid-none-data-wrap").hide();

                } else {

                    $("tfoot", "#tblARList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },
};
 

$(document).ready(function () {
    ar.ResetSize();
    $("#btnSearch").die().live("click", function () {
        ar.List();
    });

    if ($("#SearchCondition_ContractNo").val() != '') {
        ar.List();
    }
});