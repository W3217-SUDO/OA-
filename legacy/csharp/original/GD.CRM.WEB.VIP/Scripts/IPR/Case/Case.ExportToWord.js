/*案件*/

var cases = {
    List: function() {
        $("#postForm").ajaxPost(AP_ROOT + "Case/CaseList", function(response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.CaseList, function (i, c) {
                        $("tbody", "#tblCaseList").addRow(c.CaseBasicInfo.CaseNo,
                            c.CaseBasicInfo.CaseTypeId,
                            c.CaseBasicInfo.CasePhaseId,
                            c.CaseBasicInfo.CaseRequestNo,
                            getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseRequestDate)),
                            getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseAcceptDate)),
                            c.CaseBasicInfo.CaseOriginPeople,
                            getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseOriginDate)),
                            getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseRegisterDate)),
                            c.CaseBasicInfo.CaseRegisterNo,
                            getDate(convertJsonDateToJSDate(c.CaseBasicInfo.AuthorizationDate)),
                            c.CaseBasicInfo.Procurator,
                            c.CaseBasicInfo.Copywriter,
                            c.CaseBasicInfo.CaseSubmitter,
                            getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseSubmitDate)),
                            c.CaseBasicInfo.CaseOfficer,
                            getDate(convertJsonDateToJSDate( c.CaseBasicInfo.Deadline)),
                            "<span class=\"judge\">" + (c.CaseBasicInfo.HasPriority ? "&radic;" : "&times;") + "</span>",
                            "<span class=\"judge\">" + (c.CaseBasicInfo.HasForeign ? "&radic;" : "&times;") + "</span>",
                            "<a href='javascript:void(0)' onclick='javascript:cases.Open(" + c.CaseBasicInfo.CaseId + ")'>导出</a>");
                    });

                    $("tfoot", "#tblCaseList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.Caselist").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: cases.List,
                        callBackArgs: null
                    });
                } else {
                    $("tfoot", "#tblCaseList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },
}

$(document).ready(function () {
    cases.List();
});


