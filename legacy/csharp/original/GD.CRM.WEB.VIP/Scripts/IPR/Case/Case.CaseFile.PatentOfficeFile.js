var caseFile = {
    In: {
        List: function(response) {
            $("tbody", "#tblCaseList").clearRow();

            var primaryFileJson = JSON.stringify({ CaseOfficePrimaryFile: response.CaseOfficePrimaryFile });

            primaryFileJson = primaryFileJson.replace(/\n/g, "\\\\n");
            primaryFileJson = primaryFileJson.replace(/\s+/g, "");

            $("#tblCaseList").attr("metaFile", primaryFileJson);

            if (response.Cases.length > 0) {
                var j = 0;
                $.each(response.Cases, function(i, e) {
                    var caseIdHtml = '';
                    var caseJosn = JSON.stringify({ Case: e });

                    caseJosn = caseJosn.replace(/\n/g, "\\\\n");
                    caseJosn = caseJosn.replace(/\s+/g, "");
                    var TONGZHISID = '';

                    $.each(e.CaseFileList, function(k, c) {
                        if (!c.HasError) {
                            var fwr = c.FAWENR == null ? '' : getDate(convertJsonDateToJSDate(c.FAWENR));
                            var caseFeesJson = JSON.stringify({ caseFees: e.CaseFees });

                            var caseFeeHtml = e.CaseFees != null && e.CaseFees.length > 0 ? "<a href='javascript:void(0)' casefees=" + caseFeesJson + " onclick=\"javascript:caseFile.In.Detail(this)\">明细</a> &nbsp;" : "无";

                            if (e.CaseFees != null && e.CaseFees.length > 0) {
                                e.CaseFees = null;
                            }

                            if (TONGZHISID != c.TONGZHISID) {
                                caseIdHtml = "<input type='checkbox' Id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' case=" + caseJosn + "  value='" + e.CaseBasicInfo.CaseId + "'>";
                            } else {
                                caseIdHtml = '';
                            }

                            TONGZHISID = c.TONGZHISID;

                            $("tbody", "#tblCaseList").addRow(
                                caseIdHtml,
                                "<span id='TONGZHISID' >" + c.TONGZHISID + "</span>",
                                "<span id='TONGZHISID' >" + c.PatentOfficeFileStatusName + "</span>",
                                "<span id='CaseNo'  >" + e.CaseBasicInfo.CaseNo + "</span>",
                                "<span id='SHENQINGH' >" + c.SHENQINGH + "</span>",
                                "<span id='TONGZHISMC' >" + c.TONGZHISMC + "</span>",
                                "<span id='FAWENR' >" + fwr + "</span>",
                                "<span id='QIXIAN' >" + c.QIXIAN + "</span>",
                                "<span id='CaseOfficer' >" + e.CaseBasicInfo.CaseOfficerName + "</span>",
                                caseFeeHtml
                            );
                        } else {
                            $('#tblCaseList>tbody>tr:last').after("<tr><td colspan='11'><span id='message' >" + c.FileOfficialName + "," + c.Message + "</span></td></tr>");
                        }
                        j++;
                    });
                });

            } else {
            }
        },

        Detail: function(e) {

            if ($(e).attr("casefees") == '') {
                return false;
            }
            var c = JSON.parse($(e).attr("casefees"));

            if (c != null && c.caseFees.length > 0) {
                var table = "<table id='tblCaseFeeList' class='table table-hover' style='padding:0px;margin:0px'>"
                    + "                 <colgroup>"
                    + "                     <col style='width: 30%'>"
                    + "                     <col style='width:15%'>"
                    + "                     <col style='width: 20%'>"
                    + "                     <col style='width: 35%'>"
                    + "                </colgroup>"
                    + "              <thead> "
                    + "                  <tr> "
                    + "                     <th style='text-align: center'>费用类型</th> "
                    + "                    <th style='text-align: center'>金额</th>"
                    + "                    <th style='text-align: center'>缴费截止日期</th> "
                    + "                    <th style='text-align: center'>备注</th> "
                    + "           </tr> "
                    + "        </thead> "
                    + "      <tbody> ";

                $.each(c.caseFees, function(i, f) {
                    var tr = "    <tr style=''> "
                        + "            <td style='text-align:center'>" + f.CaseFeeTypeName + "</td>"
                        + "            <td style='text-align:center'>" + f.Amount + "</td>"
                        + "           <td style='text-align:center'>" + (f.DeadlineDate == null ? '' : getDate(convertJsonDateToJSDate(f.DeadlineDate))) + "</td>"
                        + "           <td style='text-align:center;color:red'>" + (f.Message == null ? '' : f.Message) + "</td>"
                        + "       </tr>";

                    table += tr;
                });

                table += "   </tbody>";
                table += " </table>";
                $(e).attr("casefees", '');
                $(e).parent().parent().after("<tr><td colspan='11' style='text-align:right;padding-left:50%;padding-top:0px;padding-bottom:0px;padding-right:0%;'>" + table + "</td></tr>");
            }

        },

        Upload: function() {
            if ($("#flZip").val() == '') {
                $.showModalMessageBox("请选择上传的文件.");
                return false;
            }
            $("#uploadingForm").attr("action",  AP_ROOT + AP_PAGE_ID + "/IPR/CaseFile/PatentOfficeFileUploading");

            $.openLoading();

            $('#uploadingForm').ajaxSubmit({
                success: function(response) {
                    $.closeLoading();
                    if (response.IsSuccess) {
                        caseFile.In.List(response.Data);
                        $.showModalMessageBox("上传成功.");
                    } else {
                        $.showModalMessageBox(response.Message);
                    }

                }
            });
            return true;
        },

        Import: function() {
            var caseIds = $.checkbox.vals("chkCaseId");
            if (caseIds.length == 0) {
                $.showModalMessageBox("请选择导入的案件.");
                return;
            }

            var cases = [];
            var j = 0;

            var result = true;

            $("#tblCaseList tbody tr").each(function(i, e) {
                if ($(e).css("display") != 'none') {
                    if ($(e).find("#chkCaseId").attr('checked') == 'checked') {

                        if ($(e).find("#chkCaseId").val() == '') {
                            result = false;
                            $.showModalMessageBox("第" + (i) + "行，文件存在错误，解决错误后,重新上传文件.");
                            return false;
                        }

                        var caseJosn = $(e).find("#chkCaseId").attr("case");
                        var c = JSON.parse(caseJosn);

                        $.each(c.Case.CaseFileList, function (k, f) {
                            f.FAWENR = f.FAWENR == null ? '' : getDate(convertJsonDateToJSDate(f.FAWENR));
                        });

                        $.each(c.Case.CaseFees, function (k, f) {

                        });

                        cases[j] = c.Case;

                        j++;
                    }
                }
            });

            var primaryFileJosn = $("#tblCaseList").attr("metaFile");
            var primaryFile = JSON.parse(primaryFileJosn);

            if (result == true) {
                $.ajaxPostJson( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFile/PatentOfficeFileImport", JSON.stringify({ cases: cases, primaryFile: primaryFile.CaseOfficePrimaryFile }), function(response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("导入成功.");
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            }
        },

        Selected: function(e) {
            if ($(e).prop("checked") == true) {
                $.checkbox.all("chkCaseId");
            } else {
                $.checkbox.not("chkCaseId");
            }
        },
    },

    Query : {
        List: function () {
            $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/CasePatentOfficeFile/CasePatentOfficeFiles", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblCaseFileList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.CaseFiles, function (i, f) {

                            var fwr = f.FAWENR == null ? '' : getDate(convertJsonDateToJSDate(f.FAWENR));
                            $("tbody", "#tblCaseFileList").addRow(
                               "<span style='width:130px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + f.PrimaryFileName + "</span>",
                               f.TONGZHISID,
                               f.StatusName,
                               f.CaseNo ,
                               f.CaseRequestNo ,
                              "<span style='width:120px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + f.TONGZHISMC + "</span>",
                               fwr,
                               f.QIXIAN,
                               ''
                           );
                        });

                        $("tfoot", "#tblCaseFileList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.caseFileList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: caseFile.Query.List,
                            callBackArgs: null
                        });


                    } else {
                        $("tfoot", "#tblCaseFileList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
    }
}
$(document).ready(function () {

    $(document).click(function () {
        $("#divUserList").hide();
        $("#divUsers").hide();
        $("#divCaseFeeTypeList").hide();
    });

    $("#btnFileUpload").click(function () {
        caseFile.In.Upload();
    });

    $("#btnImport").click(function () {
        caseFile.In.Import();
    });

    $("#flZip").change(function () {
        $("#txtFilePath").val($("#flZip").val());
    });

    $("#chkCaseAll").off().on("click", function () {
        caseFile.In.Selected(this);
    });

    $(".CaseOfficer").off().on("click", function () {

        var tirgger = this;
        var parent = this.parentElement;
        $("#divUserList").css({
            "position": "absolute",
            "left": $(tirgger).position().left,
            "top": $(tirgger).position().top + 150
        }).toggle();
        $("#hidUserName").val($(tirgger).attr("id")); //名称
        $("#hidUserId").val($(parent).find(":hidden").attr("id"));//Id
        return false;
    });

    $(".CaseFeeResponseUser").off().on("click", function () {
        var tirgger = this;
        var parent = this.parentElement;
        $("#divUsers").css({
            "position": "absolute",
            "left": $(tirgger).position().left,
            "top": $(tirgger).position().top + 150
        }).toggle();
        $("#hidUserName").val($(tirgger).attr("id")); //名称
        $("#hidUserId").val($(parent).find(":hidden").attr("id"));//Id
        return false;
    });

    $(".CaseFeeTypeName").off().on("click", function () {

        var tirgger = this;
        var parent = this.parentElement;
        var caseTypeId = $($(this).parent()).parent().find("#CaseTypeId").text();
        $(".divCaseFeeTypeList").html($.caseFeeType.getCaseFeeTypeListHtml(caseTypeId));

        $("#divCaseFeeTypeList").css({
            "position": "absolute",
            "left": $(tirgger).position().left,
            "top": $(tirgger).position().top + 150
        }).toggle();

        $("#hidCaseFeeTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFeeTypeId").val($(parent).find(":hidden").attr("id"));//Id

        return false;
    });

    $("#divCaseFeeTypeList").find("li").off().on("click", function () {
        var caseFeeTypeId = $(this).find("a").attr("id");
        var caseFeeTypeName = $(this).find("a").text();
        var currentSelectedControlId = $("#hidCaseFeeTypeId").val();
        var currentSelectedControlName = $("#hidCaseFeeTypeName").val();
        $("#" + currentSelectedControlId).val(caseFeeTypeId);
        $("#" + currentSelectedControlName).val(caseFeeTypeName);
        $("#divCaseFeeTypeList").hide();
    });

    $("#divUserList").find("li").off().on("click", function () {
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        var currentSelectedControlId = $("#hidUserId").val();
        var currentSelectedControlName = $("#hidUserName").val();
        $("#" + currentSelectedControlId).val(userId);
        $("#" + currentSelectedControlName).val(userName);
        $("#divUserList").hide();
    });

    $("#divUsers").find("li").off().on("click", function () {
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        var currentSelectedControlId = $("#hidUserId").val();
        var currentSelectedControlName = $("#hidUserName").val();
        $("#" + currentSelectedControlId).val(userId);
        $("#" + currentSelectedControlName).val(userName);
        $("#divUsers").hide();
    });

    $("#btnCaseFileSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        caseFile.Query.List();
    });

});