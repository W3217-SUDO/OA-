var caseInfo = {
    View: function (caseId, caseNo) {

        var search = {};

        search.CaseId = 0;
        search.PageId = 1;
        search.PageNo = 1;
        search.PageSize = 100;
        search.PageName = "案件查看";
        search.Keyword = caseNo;

        var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CreateUpdate?typeId=1&caseId=" + caseId + "&k=" + escape(JSON.stringify(search));

        window.open(url);
    },
   
    /*日志*/
    CaseLog: {
        List: function () {
            var data = { caseId: $("#CaseId").val() };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseLogList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $(".caselogs").empty();
                    $(".caselogs").html(response.Data);
                    $.closeLoading();
                }
            }, true);
        },

        /*打开案件日志*/
        Open: function (caseId,caseNo,caseFileName) {

            var data =
            {
                caseId: caseId,
                caseNo: caseNo,
             };

            var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseLog";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseLogModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseLogModal').on('hidden.bs.modal', function () {
                    $("#caseLogModal").remove();
                });

                $("#CaseLog_Content").val(caseFileName + ":");
            });

        },

        /*关闭案件日志*/
        Close: function () {
            $('#caseLogModal').modal('hide');
        },
        CreateUpdate: function () {
            if ($("#CaseLog_Content").val() == '') {
                $.showModalMessageBox("请输入日志内容");
                return false;
            }

            $("#caseLog").ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseLogCreate", function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("保存成功.");
                    $('#caseLogModal').modal('hide');

                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        Delete: function () {
            var data = { caseLogId: $("#CaseLog_LogId").val() };
            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/CaseLog/CaseLogDelete", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("删除成功.");
                    caseInfo.CaseLog.List();
                    caseInfo.CaseLog.Close();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
    },
}

var patentFile = {

    List: function (response) {
        if (response.Cases.length > 0) {
            var j = 0;
            $.each(response.Cases, function (i, c) {
                var caseIdHtml = '';
                var caseJosn = JSON.stringify({ Case: c });

                caseJosn = caseJosn.replace(/\n/g, "\\\\n");
                caseJosn = caseJosn.replace(/\s+/g, "");
                var TONGZHISID = '';

                var requestDate = c.CaseBasicInfo.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseRequestDate));

                var parentCaseIdHtml = "<input type='checkbox' Id='chkParentCaseId' name='chkParentCaseId' class='ng-pristine ng-valid' caserequestno='" + c.CaseBasicInfo.CaseRequestNo + "' case=" + caseJosn + " value='" + c.CaseGuid + "'>&nbsp;&nbsp;";

                var partentCaseNoHtml = '';

                if (c.CaseBasicInfo.CaseId == '0') {
                    partentCaseNoHtml = "<span  style='color:red;'>" + c.CaseBasicInfo.CaseNo + "</span>";;
                } else {
                    partentCaseNoHtml = "<span>" + (c.CaseBasicInfo.CaseRequestNo == '' || c.CaseBasicInfo.CaseRequestNo == null ? c.CaseBasicInfo.CaseNo : c.CaseBasicInfo.CaseRequestNo) + "</span>";;
                }

                var caseNoInputHtml = "<input  style='width:100%' id='item_caseid' class='inputcaseno form-control' type='text' name='input' placeholder='新案号(回车)' />";

                $("tbody", "#tblCaseFileList").addRow(
                    parentCaseIdHtml + partentCaseNoHtml,
                    "<span id='CaseNo'>" + (c.CaseBasicInfo.CaseId == '0' ? caseNoInputHtml : c.CaseBasicInfo.CaseNo) + "</span>",
                    "<span id='CaseRequestDate'>" + requestDate + "</span>",
                    "<span id='CustomerName'>" + (c.CaseBasicInfo.CustomerName == null ? '' : c.CaseBasicInfo.CustomerName) + "</span>",
                    "<span id='ApplicantName'>" + (c.CaseBasicInfo.ApplicantName == null ? '' : c.CaseBasicInfo.ApplicantName) + "</span>",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    ""
                );

                $.each(c.CaseFileList, function (k, f) {
                    var fwr = f.FAWENR == null ? '' : getDate(convertJsonDateToJSDate(f.FAWENR));
                    var caseFeesJson = JSON.stringify({ caseFees: f.CaseFees });

                    var caseFeeHtml = f.CaseFees != null && f.CaseFees.length > 0 ? "<a href='javascript:void(0)' casefees=" + caseFeesJson + " onclick=\"javascript:patentFile.Detail(this)\">明细</a> &nbsp;" : "无";

                    if (f.CaseFees != null && f.CaseFees.length > 0) {
                        f.CaseFees = null;
                    }

                    var message = '';

                    if (f.Errors != null && f.Errors.length > 0) {
                        $.each(f.Errors, function (m, err) {
                            message += (m + 1) + ". " + err.Message + "<br>";
                        });
                    }

                    var filePath = f.MetaFile.FileGuid + "/" + f.TONGZHISID + "/" + f.FileOfficialName;

                    if (TONGZHISID != f.TONGZHISID) {
                        caseIdHtml = "<span>&nbsp;&nbsp;&nbsp;&nbsp;</span><input type='checkbox' Id='chkCaseId' name='chkCaseId'  class='ng-pristine ng-valid' TONGZHISID='" + f.TONGZHISID + "' caseid=" + c.CaseBasicInfo.CaseId + " caserequestno='" + c.CaseBasicInfo.CaseRequestNo + "'  value='" + c.CaseGuid + "'>&nbsp;&nbsp;<span>" + (k + 1) + "</span>";

                        var tr = "<tr>"
                            + "<td>" + caseIdHtml + "</td>"
                            + "<td colspan='4' style='color:red;text-align:left'>" + message + "</td>"
                            + "<td><span id='PatentOfficeFileImportStatus'>" + f.PatentOfficeFileStatusName + "</span></td>"
                            + "<td>" + f.FAMINGMC + "</td>"
                            + "<td>" + "<span id='TONGZHISMC'> <a  id='fileId' fileId=" + f.FileId + " href='javascript:void(0)' filePath=" + filePath + " onclick=\"javascript:patentFile.View(this)\"> " + f.TONGZHISMC + "</a> &nbsp;</span>" + "</td>"
                            + "<td>" + f.TONGZHISID + "</td>"
                            + "<td>" + f.TONGZHISBM + "</td>"
                            + "<td>" + fwr + "</td>"
                            + "<td>" + caseFeeHtml + "</td>"
                            + "</tr>";

                        $('#tblCaseFileList>tbody>tr:last').after(tr);

                    } else {
                        var selector = $('#tblCaseFileList>tbody>tr:last').find("#TONGZHISMC");
                        $(selector).append("<br> <a id='fileId' fileId=" + f.FileId + " href='javascript:void(0)' filePath=" + filePath + " onclick=\"javascript:patentFile.View(this)\"> " + f.TONGZHISMC + "</a> &nbsp;");
                    }

                    TONGZHISID = f.TONGZHISID;

                    j++;
                });
            });
        }
        else {
        }
    },

    Detail: function (e) {

        if ($(e).attr("casefees") == '') {
            return false;
        }
        var c = JSON.parse($(e).attr("casefees"));

        if ($(e).parent().parent().next().find("#tblCaseFeeList").length > 0) {
            $(e).parent().parent().next().remove();
            return false;
        }

        if (c != null && c.caseFees.length > 0) {
            var table = "<table id='tblCaseFeeList' class='table table-hover' style='padding:0px;margin:0px'>"
                + "                 <colgroup>"
                + "                     <col style='width: 40%'>"
                + "                     <col style='width:20%'>"
                + "                     <col style='width: 40%'>"
                + "                </colgroup>"
                + "              <thead> "
                + "                  <tr> "
                + "                     <th style='text-align: center'>费用类型</th> "
                + "                    <th style='text-align: center'>金额</th>"
                + "                    <th style='text-align: center'>缴费截止日期</th> "
                + "           </tr> "
                + "        </thead> "
                + "      <tbody> ";

            $.each(c.caseFees, function (i, f) {
                var tr = "    <tr style=''> "
                    + "            <td style='text-align:center'>" + f.CaseFeeTypeName + "</td>"
                    + "            <td style='text-align:center'>" + f.Amount + "</td>"
                    + "           <td style='text-align:center'>" + (f.DeadlineDate == null ? '' : getDate(convertJsonDateToJSDate(f.DeadlineDate))) + "</td>"
                    + "       </tr>";

                table += tr;
            });

            table += "   </tbody>";
            table += " </table>";
            $(e).parent().parent().after("<tr><td colspan='11' style='text-align:right;padding-left:60%;padding-top:0px;padding-bottom:0px;padding-right:0%;'>" + table + "</td></tr>");
        }

    },

    View: function (e) {

        var filePath = $(e).attr("filePath");

        var path = GV_IPR.IPROnlineUrl + "PatentOfficeFiles/" + filePath;
        window.open(path);
    },

    Selected: function (e) {

        var n = 'chkCaseId';
        if ($(e).prop("checked") == true) {

            $("input[name=" + n + "]").each(
                function () {
                    if ($(this).val() == $(e).val()) {
                        $(this).attr("checked", "checked");
                    }
                }
            );
        } else {
            $("input[name=" + n + "]").each(
                function () {
                    if ($(this).val() == $(e).val()) {
                        $(this).removeAttr("checked");
                    }
                }
            );
        }
    },

    SelectedAll: function (e) {
        if ($(e).prop("checked") == true) {
            $.checkbox.all("chkCaseId");
            $.checkbox.all("chkParentCaseId");
        } else {
            $.checkbox.not("chkCaseId");
            $.checkbox.not("chkParentCaseId");
        }
    },

    SelectedParent: function (e) {

        var n = 'chkParentCaseId';
        if ($(e).prop("checked") == true) {

            $("input[name=" + n + "]").each(
                function () {
                    if ($(this).val() == $(e).val()) {
                        $(this).attr("checked", "checked");
                    }
                }
            );
        } else {
            $("input[name=" + n + "]").each(
                function () {
                    if ($(this).val() == $(e).val()) {
                        $(this).removeAttr("checked");
                    }
                }
            );
        }
    },

    getCaseBasicCallBack: function (response, trigger) {

        if (typeof (response) == "undefined" || response == null) {
            return false;
        }

        if (typeof (trigger) == "undefined" || trigger == null) {
            return false;
        }

        if (response.Data.CaseBasicInfo == null) {
            $.showModalMessageBox("未找到案件.", null, true);
            return false;
        }

        $(trigger).attr("caseid", response.Data.CaseBasicInfo.CaseId);
        $(trigger).attr("caseno", response.Data.CaseBasicInfo.CaseNo);
        $(trigger).attr("caserequestno", response.Data.CaseBasicInfo.CaseRequestNo);

        if (response.Data.CaseBasicInfo.CaseRequestDate == null) {
            $(trigger).parents("tr").find("#CaseRequestDate").text('');
        } else {
            $(trigger).parents("tr").find("#CaseRequestDate").text(getDate(convertJsonDateToJSDate(response.Data.CaseBasicInfo.CaseRequestDate)));
        }

        $(trigger).parents("tr").find("#CustomerName").text(response.Data.CaseBasicInfo.CustomerName);

        var chkParentCaseId = $(trigger).parents("tr").find("#chkParentCaseId");

        $(trigger).parents("tr").find("#chkParentCaseId").attr("caseid", response.Data.CaseBasicInfo.CaseId);
        $(trigger).parents("tr").find("#chkParentCaseId").attr("caseno", response.Data.CaseBasicInfo.CaseNo);
        $(trigger).parents("tr").find("#chkParentCaseId").attr("caserequestno", response.Data.CaseBasicInfo.CaseRequestNo);


        var n = "chkCaseId";
        $("input[name=" + n + "]").each(
            function () {
                if ($(this).val() == $(chkParentCaseId).val()) {
                    $(this).attr("caseid", response.Data.CaseBasicInfo.CaseId);
                    $(this).attr("caseno", response.Data.CaseBasicInfo.CaseNo);
                    $(this).attr("caserequestno", response.Data.CaseBasicInfo.CaseRequestNo);
                }
            }
        );

        if ($(trigger).parents("tr").find("#ApplicantName").text() != response.Data.CaseBasicInfo.CustomerName) {
            //$.showModalMessageBox("客户信息与申请人信息不一致.", null, true);
            $(trigger).parents("tr").find("#CustomerName").css("color", "red");
            $(trigger).parents("tr").find("#CustomerName").text(response.Data.CaseBasicInfo.CustomerName + "(客户与申请人不一致.)");

            return false;
        }
    },

    In: {
        Upload: function () {
            if ($("#flZip").val() == '') {
                $.showModalMessageBox("请选择上传的文件.");
                return false;
            }
            $("#uploadingForm").attr("action", AP_ROOT + AP_PAGE_ID + "/FIO/PatentOffice/PatentOfficeFileUploading");

            $.openLoading();

            $('#uploadingForm').ajaxSubmit({
                success: function (response) {
                    $.closeLoading();
                    if (response.IsSuccess) {
                        $("tbody", "#tblCaseFileList").clearRow();
                        patentFile.List(response.Data);
                        $.showModalMessageBox("上传成功.");
                    } else {
                        $.showModalMessageBox(response.Message);
                    }

                }
            });
            return true;
        },
        Import: function () {
            var caseIds = $.checkbox.vals("chkCaseId");
            if (caseIds.length == 0) {
                $.showModalMessageBox("请选择导入的案件.");
                return;
            }

            var selectedIds = new Array;
            var result = true;

            $("#tblCaseFileList tbody tr").each(function (i, e) {
                if ($(e).css("display") != 'none') {
                    //if ($(e).find("#chkParentCaseId").attr('checked') == 'checked') {

                    //    if ($(e).find("#item_caseid").length > 0 && typeof($(e).find("#item_caseid").attr("caseid")) == 'undefined') {
                    //        result = false;
                    //        $.showModalMessageBox("第" + (i) + "行，请输入正确的内部案号.");
                    //        return false;
                    //    }
                    //}

                    if ($(e).find("#chkCaseId").attr('checked') == 'checked') {

                        var caseId = $(e).find("#chkCaseId").attr("caseid");

                        if (caseId > 0) {
                            $.each($(e).find("#fileId"), function (m, n) {
                                var fileId = $(n).attr("fileid");
                                selectedIds.push(fileId + "," + caseId);
                            });
                        }
                    }
                }
            });

            if (result == true) {
                $.ajaxPostJson(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOffice/PatentOfficeFileImport", JSON.stringify({ selectedIds: selectedIds }), function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox(response.Message);
                        var fileIds = response.Data;
                        $("input[name='chkCaseId']:checked").each(
                              function () {
                                  var fileId = $(this).parents("tr").find("#fileId").attr("fileid");
                                  console.log($.inArray(fileId, fileIds));
                                  if ($.inArray(fileId, fileIds) > -1) {
                                      $(this).parents("tr").find("#PatentOfficeFileImportStatus").parent().css("background-color", "green");
                                      $(this).parents("tr").find("#PatentOfficeFileImportStatus").css("color", "white");
                                      $(this).parents("tr").find("#PatentOfficeFileImportStatus").text('已导入');
                                  }
                              }
                          );
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            }
        },
    },

    UnDisposed: {
        Search: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOffice/UnDisposedPatentOfficeFiles", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblCaseFileList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();

                        patentFile.List(response.Data);

                        $("tfoot", "#tblCaseFileList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.caseFileList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: patentFile.UnDisposed.Search,
                            callBackArgs: null
                        });

                    } else {
                        $("tfoot", "#tblCaseFileList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
                else {
                    $("tbody", "#tblCaseFileList").clearRow();
                    $("tfoot", "#tblCaseFileList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            });
        },
        ListExportToExcel: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOfficeFile/PatentOfficeFileListExportToExcel", function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOfficeFile/PatentOfficeFileListExportToExcelDownload?fileName=" + response.Data);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
    },

    Normal: {
        Search: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOffice/CasePatentOfficeFiles", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblCaseFileList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();

                        patentFile.List(response.Data);

                        $("tfoot", "#tblCaseFileList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.caseFileList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: patentFile.Normal.Search,
                            callBackArgs: null
                        });

                    } else {
                        $("tfoot", "#tblCaseFileList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
                else {
                    $("tbody", "#tblCaseFileList").clearRow();
                    $("tfoot", "#tblCaseFileList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            });
        },

    },

    Process: {
        List: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOffice/CasePatentOfficeFileInList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblCaseFileList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.Cases, function (i, c) {
                            $.each(c.CaseFileList, function (k, f) {
                                var caseTypeName = $.caseType.getCaseTypeName(c.CaseBasicInfo.CaseTypeId);
                                var filePath = f.MetaFile.FileGuid + "/" + f.TONGZHISID + "/" + f.FileOfficialName;
                                if ($("#SearchCondition_PageId").val() == "1101004") {
                                    $("tbody", "#tblCaseFileList").addRow(
                                       "<input type='checkbox'  id='chkCaseFileId' name='chkCaseFileId' class='ng-pristine ng-valid' value=" + f.FileId + " caseId=" + c.CaseBasicInfo.CaseId + " caseno='" + c.CaseBasicInfo.CaseNo + "'casefilename='" + f.TONGZHISMC + "'>",
                                       f.ServiceProcessStatusName,
                                       f.BusinessProcessStatusName,
                                       f.InDate == null ? '' : getDate(convertJsonDateToJSDate(f.InDate)),
                                       c.CaseBasicInfo.CaseId > 0 ? "<a href='javascript:void(0)' onclick=\"javascript:caseInfo.View(" + c.CaseBasicInfo.CaseId + ",'" + c.CaseBasicInfo.CaseNo + "')\"> " + c.CaseBasicInfo.CaseNo + "</a>" : c.CaseBasicInfo.CaseNo,
                                       caseTypeName,
                                       c.CaseBasicInfo.CustomerName == null ? '' : c.CaseBasicInfo.CustomerName,
                                       c.CaseBasicInfo.ApplicantName == null ? f.ApplicantName : c.CaseBasicInfo.ApplicantName,
                                       c.CaseBasicInfo.CaseRequestNo,
                                       f.FAMINGMC,
                                       c.CaseBasicInfo.CaseOriginPeopleName,
                                       f.FAWENR == null ? '' : getDate(convertJsonDateToJSDate(f.FAWENR)),
                                        f.FAWENXLH,
                                       "<span id='TONGZHISMC'> <a  id='fileId' fileId=" + f.FileId + " href='javascript:void(0)' filePath=" + filePath + " onclick=\"javascript:patentFile.View(this)\"> " + f.TONGZHISMC + "</a> &nbsp;</span>"
                                    );
                                }
                                else if ($("#SearchCondition_PageId").val() == "1101002" || $("#SearchCondition_PageId").val() == "1101006") {
                                    $("tbody", "#tblCaseFileList").addRow(
                                       "<input type='checkbox'  id='chkCaseFileId' name='chkCaseFileId' class='ng-pristine ng-valid' value=" + f.FileId + " caseId=" + c.CaseBasicInfo.CaseId + " caseno='" + c.CaseBasicInfo.CaseNo + "'casefilename='" + f.TONGZHISMC + "'>",
                                       f.BusinessProcessStatusName,
                                       f.InDate == null ? '' : getDate(convertJsonDateToJSDate(f.InDate)),
                                       c.CaseBasicInfo.CaseId > 0 ? "<a href='javascript:void(0)' onclick=\"javascript:caseInfo.View(" + c.CaseBasicInfo.CaseId + ",'" + c.CaseBasicInfo.CaseNo + "')\"> " + c.CaseBasicInfo.CaseNo + "</a>" : c.CaseBasicInfo.CaseNo,
                                       caseTypeName,
                                       c.CaseBasicInfo.CustomerName == null ? '' : c.CaseBasicInfo.CustomerName,
                                       c.CaseBasicInfo.ApplicantName == null ? f.ApplicantName : c.CaseBasicInfo.ApplicantName,
                                       c.CaseBasicInfo.CaseRequestNo,
                                       f.FAMINGMC,
                                       c.CaseBasicInfo.CaseOriginPeopleName,
                                       f.FAWENR == null ? '' : getDate(convertJsonDateToJSDate(f.FAWENR)),
                                        f.FAWENXLH,
                                       "<span id='TONGZHISMC'> <a  id='fileId' fileId=" + f.FileId + " href='javascript:void(0)' filePath=" + filePath + " onclick=\"javascript:patentFile.View(this)\"> " + f.TONGZHISMC + "</a> &nbsp;</span>"
                                    );
                                }

                            });
                        });

                        $("tfoot", "#tblCaseFileList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.caseFileList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: patentFile.Process.List,
                            callBackArgs: null
                        });

                        patentFile.Process.BindMenu();

                    } else {
                        $("tfoot", "#tblCaseFileList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
                else {
                    $("tbody", "#tblCaseFileList").clearRow();
                    $("tfoot", "#tblCaseFileList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            });
        },

        Packing: function () {
            var officeFileIds = $.checkbox.vals("chkCaseFileId");
            if (officeFileIds.length == 0) {
                $.showModalMessageBox("请勾选下载的文件.");
                return false;
            }

            //var dataIsOk = true;
            //$("input[name='chkCaseFileId']:checked").each(
            //    function () {
            //        if ($(this).attr("caseno") == '') {
            //            $.showModalMessageBox("所选择的文件找不到对应的案件,请重新选择.");

            //            dataIsOk = false;
            //            return false;
            //        }
            //    }
            //);

            //if (!dataIsOk) return false;

            var data = {
                officeFileIds: officeFileIds,
            }

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOfficeFile/PatentOfficeFilePacking", data, function (response) {
                if (response.IsSuccess) {
                    var fileName = response.Data;
                    window.open(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOfficeFile/PatentOfficeFileDownload?fileName=" + fileName);
                } else {

                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },

        BusinessProcess: function () {
            var officeFileIds = $.checkbox.vals("chkCaseFileId");
            if (officeFileIds.length == 0) {
                $.showModalMessageBox("请勾选文件.");
                return false;
            }

            var data = {
                officeFileIds: officeFileIds,
            }

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOffice/PatentOfficeFileBusinessProcess", data, function (response) {
                if (response.IsSuccess) {
                    patentFile.Process.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },

        BusinessOnProcess: function () {
            var officeFileIds = $.checkbox.vals("chkCaseFileId");
            if (officeFileIds.length == 0) {
                $.showModalMessageBox("请勾选文件.");
                return false;
            }

            var data = {
                officeFileIds: officeFileIds,
            }

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOffice/PatentOfficeFileBusinessOnProcess", data, function (response) {
                if (response.IsSuccess) {
                    patentFile.Process.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },

        BusinessUnProcess: function () {
            var officeFileIds = $.checkbox.vals("chkCaseFileId");
            if (officeFileIds.length == 0) {
                $.showModalMessageBox("请勾选文件.");
                return false;
            }

            var data = {
                officeFileIds: officeFileIds,
            }

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOffice/PatentOfficeFileBusinessUnProcess", data, function (response) {
                if (response.IsSuccess) {
                    patentFile.Process.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },

        ServiceProcess: function () {
            var officeFileIds = $.checkbox.vals("chkCaseFileId");
            if (officeFileIds.length == 0) {
                $.showModalMessageBox("请勾选文件.");
                return false;
            }

            var data = {
                officeFileIds: officeFileIds,
            }

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOffice/PatentOfficeFileServiceProcess", data, function (response) {
                if (response.IsSuccess) {
                    patentFile.Process.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },

        ServiceUnProcess: function () {
            var officeFileIds = $.checkbox.vals("chkCaseFileId");
            if (officeFileIds.length == 0) {
                $.showModalMessageBox("请勾选文件.");
                return false;
            }

            var data = {
                officeFileIds: officeFileIds,
            }

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOffice/PatentOfficeFileServiceUnProcess", data, function (response) {
                if (response.IsSuccess) {
                    patentFile.Process.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },

        ServiceOnProcess: function () {
            var officeFileIds = $.checkbox.vals("chkCaseFileId");
            if (officeFileIds.length == 0) {
                $.showModalMessageBox("请勾选文件.");
                return false;
            }

            var data = {
                officeFileIds: officeFileIds,
            }

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOffice/PatentOfficeFileServiceOnProcess", data, function (response) {
                if (response.IsSuccess) {
                    patentFile.Process.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },

        BindMenu: function () {
            $('#casegridSection').contextMenu('menu', {
                menuStyle: {
                    width: '152px'
                },

                itemStyle: {
                    width: '150px'
                },

                bindings: {
                    'logging': function (t, e) {
                        var caseId = $(e).find("span").text();
                        var caseNo = $(e).find("lable").text();
                        var caseFileName = $(e).find("div").text();

                        if (caseId == '' || caseId == '0') {
                            $.showModalMessageBox("未找到对应案件,无法记录案件日志.");
                            return false;
                        }

                        caseInfo.CaseLog.Open(caseId, caseNo, caseFileName);

                        return true;
                    },
                    'businessprocess': function (t, e) {

                        patentFile.Process.BusinessProcess(true);
                        return true;
                    },

                    'serviceprocess': function (t, e) {

                        patentFile.Process.ServiceProcess(true);
                        return true;
                    },

                    'businessunprocess': function (t, e) {

                        patentFile.Process.BusinessUnProcess(true);
                        return true;
                    },

                    'serviceunprocess': function (t, e) {

                        patentFile.Process.ServiceUnProcess(true);
                        return true;
                    },

                    'download': function (t, e) {
                        patentFile.Process.Packing(true);
                    },

                },
                onContextMenu: function (e) {
                    return true;
                },
                onShowMenu: function (e, menu) {

                    var caseId = $(e.target).parents("tr").find("#chkCaseFileId").attr("caseid");
                    var caseNo = $(e.target).parents("tr").find("#chkCaseFileId").attr("caseno");
                    var caseFileName = $(e.target).parents("tr").find("#chkCaseFileId").attr("casefilename");

                    var caseFileId = $(e.target).parents("tr").find("#chkCaseFileId").val();

                    $('#logging', menu).append("<span style='display:none'>" + caseId + "</span> <lable style='display:none'>" + caseNo + "</lable> <div style='display:none'>" + caseFileName + "</div>");
                    $('#download', menu).append("<span style='display:none'>" + caseFileId + "</span>");
                    $('#businessprocess', menu).append("<span style='display:none'>" + caseFileId + "</span>");
                    $('#serviceprocess', menu).append("<span style='display:none'>" + caseFileId + "</span>");

                    $('#businessunprocess', menu).append("<span style='display:none'>" + caseFileId + "</span>");
                    $('#serviceunprocess', menu).append("<span style='display:none'>" + caseFileId + "</span>");


                    return menu;
                }
            });
        },

        ListExportToExcel: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOfficeFile/PatentOfficeFileListExportToExcel", function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOfficeFile/PatentOfficeFileListExportToExcelDownload?fileName=" + response.Data);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
    },

    HistoryProcess: {
        List: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOffice/HistoryPatentOfficeFileAllList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblCaseFileList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.Cases, function (i, c) {
                            $.each(c.CaseFileList, function (k, f) {
                                var caseTypeName = $.caseType.getCaseTypeName(c.CaseBasicInfo.CaseTypeId);
                                var filePath = f.CaseRequestNo + "/" + f.FileOfficialName;
                                if ($("#SearchCondition_PageId").val() == "1101005") {
                                    $("tbody", "#tblCaseFileList").addRow(
                                       "<input type='checkbox'  id='chkCaseFileId' name='chkCaseFileId' class='ng-pristine ng-valid' value=" + f.FileId + " caseId=" + c.CaseBasicInfo.CaseId + " caseno='" + c.CaseBasicInfo.CaseNo + "'casefilename='" + f.TONGZHISMC + "'>",
                                       f.ServiceProcessStatusName,
                                       f.BusinessProcessStatusName,
                                       f.InDate == null ? '' : getDate(convertJsonDateToJSDate(f.InDate)),
                                       c.CaseBasicInfo.CaseId > 0 ? "<a href='javascript:void(0)' onclick=\"javascript:caseInfo.View(" + c.CaseBasicInfo.CaseId + ",'" + c.CaseBasicInfo.CaseNo + "')\"> " + c.CaseBasicInfo.CaseNo + "</a>" : c.CaseBasicInfo.CaseNo,
                                       caseTypeName,
                                       c.CaseBasicInfo.CustomerName == null ? '' : c.CaseBasicInfo.CustomerName,
                                       c.CaseBasicInfo.ApplicantName == null ? f.ApplicantName : c.CaseBasicInfo.ApplicantName,
                                       c.CaseBasicInfo.CaseRequestNo,
                                       f.FAMINGMC,
                                       c.CaseBasicInfo.CaseOriginPeopleName,
                                       f.FAWENR == null ? '' : getDate(convertJsonDateToJSDate(f.FAWENR)),
                                       f.FAWENXLH,
                                       "<span id='TONGZHISMC'> <a  id='fileId' fileId=" + f.FileId + " href='javascript:void(0)' filePath=" + filePath + " onclick=\"javascript:patentFile.History.View(this)\"> " + f.TONGZHISMC + "</a> &nbsp;</span>"
                                    );
                                }
                                else if ($("#SearchCondition_PageId").val() == "1101003") {
                                    $("tbody", "#tblCaseFileList").addRow(
                                       "<input type='checkbox'  id='chkCaseFileId' name='chkCaseFileId' class='ng-pristine ng-valid' value=" + f.FileId + " caseId=" + c.CaseBasicInfo.CaseId + " caseno='" + c.CaseBasicInfo.CaseNo + "'casefilename='" + f.TONGZHISMC + "'>",
                                       f.BusinessProcessStatusName,
                                       f.InDate == null ? '' : getDate(convertJsonDateToJSDate(f.InDate)),
                                       c.CaseBasicInfo.CaseId > 0 ? "<a href='javascript:void(0)' onclick=\"javascript:caseInfo.View(" + c.CaseBasicInfo.CaseId + ",'" + c.CaseBasicInfo.CaseNo + "')\"> " + c.CaseBasicInfo.CaseNo + "</a>" : c.CaseBasicInfo.CaseNo,
                                       caseTypeName,
                                       c.CaseBasicInfo.CustomerName == null ? '' : c.CaseBasicInfo.CustomerName,
                                       c.CaseBasicInfo.ApplicantName == null ? f.ApplicantName : c.CaseBasicInfo.ApplicantName,
                                       c.CaseBasicInfo.CaseRequestNo,
                                       f.FAMINGMC,
                                       c.CaseBasicInfo.CaseOriginPeopleName,
                                       f.FAWENR == null ? '' : getDate(convertJsonDateToJSDate(f.FAWENR)),
                                        f.FAWENXLH,
                                       "<span id='TONGZHISMC'> <a  id='fileId' fileId=" + f.FileId + " href='javascript:void(0)' filePath=" + filePath + " onclick=\"javascript:patentFile.History.View(this)\"> " + f.TONGZHISMC + "</a> &nbsp;</span>"
                                    );
                                }

                            });
                        });

                        $("tfoot", "#tblCaseFileList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.caseFileList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: patentFile.HistoryProcess.List,
                            callBackArgs: null
                        });

                        patentFile.HistoryProcess.BindMenu();

                    } else {
                        $("tfoot", "#tblCaseFileList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
                else {
                    $("tbody", "#tblCaseFileList").clearRow();
                    $("tfoot", "#tblCaseFileList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            });
        },

        Packing: function () {
            var officeFileIds = $.checkbox.vals("chkCaseFileId");
            if (officeFileIds.length == 0) {
                $.showModalMessageBox("请勾选下载的文件.");
                return false;
            }
            var data = {
                officeFileIds: officeFileIds,
            }

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOfficeFile/HistoryPatentOfficeFilePacking", data, function (response) {
                if (response.IsSuccess) {
                    var fileName = response.Data;
                    window.open(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOfficeFile/PatentOfficeFileDownload?fileName=" + fileName);
                } else {

                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },

        BusinessProcess: function () {
            var officeFileIds = $.checkbox.vals("chkCaseFileId");
            if (officeFileIds.length == 0) {
                $.showModalMessageBox("请勾选文件.");
                return false;
            }

            var data = {
                officeFileIds: officeFileIds,
            }

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOffice/HistoryPatentOfficeFileBusinessProcess", data, function (response) {
                if (response.IsSuccess) {
                    patentFile.HistoryProcess.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },

        ServiceProcess: function () {
            var officeFileIds = $.checkbox.vals("chkCaseFileId");
            if (officeFileIds.length == 0) {
                $.showModalMessageBox("请勾选文件.");
                return false;
            }

            var data = {
                officeFileIds: officeFileIds,
            }

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOffice/HistoryPatentOfficeFileServiceProcess", data, function (response) {
                if (response.IsSuccess) {
                    patentFile.HistoryProcess.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },

        BindMenu: function () {
            $('#casegridSection').contextMenu('menu', {
                menuStyle: {
                    width: '152px'
                },

                itemStyle: {
                    width: '150px'
                },

                bindings: {
                    'logging': function (t, e) {
                        var caseId = $(e).find("span").text();
                        var caseNo = $(e).find("lable").text();
                        var caseFileName = $(e).find("div").text();

                        if (caseId == '' || caseId == '0') {
                            $.showModalMessageBox("未找到对应案件,无法记录案件日志.");
                            return false;
                        }

                        caseInfo.CaseLog.Open(caseId, caseNo, caseFileName);

                        return true;
                    },
                    'businessprocess': function (t, e) {

                        patentFile.HistoryProcess.BusinessProcess(true);
                        return true;
                    },

                    'serviceprocess': function (t, e) {

                        patentFile.HistoryProcess.ServiceProcess(true);
                        return true;
                    },

                    'download': function (t, e) {
                        patentFile.HistoryProcess.Packing(true);
                    },

                },
                onContextMenu: function (e) {
                    return true;
                },
                onShowMenu: function (e, menu) {

                    var caseId = $(e.target).parents("tr").find("#chkCaseFileId").attr("caseid");
                    var caseNo = $(e.target).parents("tr").find("#chkCaseFileId").attr("caseno");
                    var caseFileName = $(e.target).parents("tr").find("#chkCaseFileId").attr("casefilename");

                    var caseFileId = $(e.target).parents("tr").find("#chkCaseFileId").val();

                    $('#logging', menu).append("<span style='display:none'>" + caseId + "</span> <lable style='display:none'>" + caseNo + "</lable> <div style='display:none'>" + caseFileName + "</div>");
                    $('#download', menu).append("<span style='display:none'>" + caseFileId + "</span>");
                    $('#businessprocess', menu).append("<span style='display:none'>" + caseFileId + "</span>");
                    $('#serviceprocess', menu).append("<span style='display:none'>" + caseFileId + "</span>");

                    return menu;
                }
            });
        },

        ListExportToExcel: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOfficeFile/HistoryPatentOfficeFileListExportToExcel", function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOfficeFile/PatentOfficeFileListExportToExcelDownload?fileName=" + response.Data);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
    },

    History: {
        List: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOffice/HistoryCasePatentOfficeFileInList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblCaseFileList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.Cases, function (i, c) {
                            $.each(c.CaseFileList, function (k, f) {
                                var caseTypeName = $.caseType.getCaseTypeName(c.CaseBasicInfo.CaseTypeId);
                                var filePath = f.CaseRequestNo + "/" + f.FileOfficialName;
                                $("tbody", "#tblCaseFileList").addRow(
                                   "<input type='checkbox'  id='chkCaseFileId' name='chkCaseFileId' class='ng-pristine ng-valid' value=" + f.FileId + " caseId=" + c.CaseBasicInfo.CaseId + " caseno='" + c.CaseBasicInfo.CaseNo + "'casefilename='" + f.TONGZHISMC + "'>",
                                   f.BusinessProcessStatusName,
                                   f.InDate == null ? '' : getDate(convertJsonDateToJSDate(f.InDate)),
                                   c.CaseBasicInfo.CaseId > 0 ? "<a href='javascript:void(0)' onclick=\"javascript:caseInfo.View(" + c.CaseBasicInfo.CaseId + ",'" + c.CaseBasicInfo.CaseNo + "')\"> " + c.CaseBasicInfo.CaseNo + "</a>" : c.CaseBasicInfo.CaseNo,
                                   caseTypeName,
                                   c.CaseBasicInfo.CustomerName == null ? '' : c.CaseBasicInfo.CustomerName,
                                   c.CaseBasicInfo.ApplicantName == null ? '' : c.CaseBasicInfo.ApplicantName,
                                   c.CaseBasicInfo.CaseRequestNo,
                                   c.CaseBasicInfo.CaseName,
                                   c.CaseBasicInfo.BusinessOwnerName,
                                   f.FAWENR == null ? '' : getDate(convertJsonDateToJSDate(f.FAWENR)),
                                   f.TONGZHISID,
                                   "<span id='TONGZHISMC'> <a  id='fileId' fileId=" + f.FileId + " href='javascript:void(0)' filePath=" + filePath + " onclick=\"javascript:patentFile.History.View(this)\"> " + f.TONGZHISMC + "</a> &nbsp;</span>"
                               );
                            });
                        });

                        $("tfoot", "#tblCaseFileList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.caseFileList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: patentFile.History.List,
                            callBackArgs: null
                        });


                    } else {
                        $("tfoot", "#tblCaseFileList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
                else {
                    $("tbody", "#tblCaseFileList").clearRow();
                    $("tfoot", "#tblCaseFileList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            });
        },

        View: function (e) {

            var filePath = $(e).attr("filePath");

            var path = GV_IPR.IPROnlineUrl + "HistoryPatentOfficeFiles/" + filePath;
            window.open(path);
        },
    },

    CheckList: {

        CheckListFile: {

            Open: function () {

                var url = AP_ROOT + AP_PAGE_ID + "/FIO/PatentOffice/PatentOfficeFileCheckListImport";
                $.openLoading();

                $("<div></div>").load(url, null, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#patentOfficeFileCheckListImport').modal({ backdrop: 'static', keyboard: false });
                    $('#patentOfficeFileCheckListImport').on('hidden.bs.modal', function () {
                        $("#patentOfficeFileCheckListImport").remove();
                    });

                });
            },

            Close: function () {
                $('#patentOfficeFileCheckListImport').modal('hide');
            },

            Upload: function () {
                if ($("#flCheckListFile").val() == '') {
                    $.showModalMessageBox("请选择上传的文件.");
                    return false;
                }
                $("#uploadingForm").attr("action", AP_ROOT + AP_PAGE_ID + "/FIO/PatentOffice/PatentOfficeFileCheckListUploading");

                $.openLoading();

                $('#uploadingForm').ajaxSubmit({
                    success: function (response) {
                        $.closeLoading();
                        if (response.IsSuccess) {
                            $("#SearchCondition_FileGuid").val(response.Data);
                            patentFile.CheckList.List();
                            patentFile.CheckList.CheckListFile.Close();
                            $("#message").text(response.Message);
                            $.showModalMessageBox("上传成功.");
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    }
                });
                return true;
            },

        },

        List: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOffice/CasePatentOfficeFileCheckList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblCaseFileList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.CheckFiles, function (i, f) {

                            var message = '';
                            var hasError = false;

                            if (f.Errors != null && f.Errors.length > 0) {
                                hasError = true;
                                $.each(f.Errors, function (m, err) {
                                    message += (m + 1) + ". " + err.Message + "<br>";
                                });
                            }

                            $("tbody", "#tblCaseFileList").addRow(
                                f.CaseRequestNo,
                                f.TONGZHISMC,
                                f.FAMINGMC,
                                f.FAWENXLH,
                                f.FAWENR == null ? '' : getDate(convertJsonDateToJSDate(f.FAWENR)),
                                f.DownloadStatus,
                                f.PatentOfficeFileStatusName,
                                f.CaseNo,
                                f.InDate == null ? '' : getDate(convertJsonDateToJSDate(f.InDate)),
                                "<span id='item_Errors' hasError=" + hasError + " style='color:red;text-align:left'>" + message + "</span>"
                            );
                        });

                        $("tfoot", "#tblCaseFileList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.caseFileList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: patentFile.CheckList.List,
                            callBackArgs: null
                        });

                    } else {
                        $("tfoot", "#tblCaseFileList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
                else {
                    $("tbody", "#tblCaseFileList").clearRow();
                    $("tfoot", "#tblCaseFileList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            });
        },

        ListExportToExcel: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOfficeFile/PatentOfficeFileCheckListExportToExcel", function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/FIO/PatentOfficeFile/PatentOfficeFileListExportToExcelDownload?fileName=" + response.Data);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        //List: function (response) {
        //    if (response.Data.length > 0) {
        //        var j = 0;
        //        $.each(response.Data, function (i, f) {

        //            var message = '';
        //            var hasError = false;

        //            if (f.Errors != null && f.Errors.length > 0) {
        //                hasError = true;
        //                $.each(f.Errors, function (m, err) {
        //                    message += (m + 1) + ". " + err.Message + "<br>";
        //                });
        //            }

        //            $("tbody", "#tblCaseFileList").addRow(
        //                f.CaseRequestNo,
        //                f.TONGZHISMC,
        //                f.FAMINGMC,
        //                f.FAWENXLH,
        //                f.FAWENR == null ? '' : getDate(convertJsonDateToJSDate(f.FAWENR)),
        //                f.DownloadStatus,
        //                f.PatentOfficeFileStatusName,
        //                f.CaseNo,
        //                f.InDate == null ? '' : getDate(convertJsonDateToJSDate(f.InDate)),
        //                "<span id='item_Errors' hasError=" + hasError + " style='color:red;text-align:left'>" + message + "</span>"
        //            );
        //        });
        //    }
        //},

        DisplayErrors: function () {

            $("#tblCaseFileList tbody tr").each(function (i, e) {
                var hasError = $(e).find("#item_Errors").attr("hasError");
                if (hasError == 'true') {
                    $(e).show();
                }
                else {
                    $(e).hide();
                }

            })
        }
    }
}

$(document).ready(function () {

    $(document).click(function () {
    });

    $("#btnFileUpload").click(function () {
        patentFile.In.Upload();
    });

    //$("#btnCheckListFileUpload").click(function () {
    //    patentFile.CheckList.Upload();
    //});

    $("#btnCheckListHasError").click(function () {
        patentFile.CheckList.DisplayErrors();
    });

    $("#btnImport").click(function () {
        patentFile.In.Import();
    });

    $("#flZip").change(function () {
        $("#txtFilePath").val($("#flZip").val());
    });

    $("#chkCaseIdAll").off().on("click", function () {
        patentFile.SelectedAll(this);
    });

    $("#chkCaseId").off().on("click", function () {
        patentFile.SelectedParent(this);
    });

    $("#chkParentCaseId").off().on("click", function () {
        patentFile.Selected(this);
    });

    $("#btnUnDisposedSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        patentFile.UnDisposed.Search();
    });

    $("#btnNormalSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        patentFile.Normal.Search();
    });

    $("#btnSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        patentFile.Process.List();
    });

    $("#btnHistorySearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        patentFile.HistoryProcess.List();
    });

    $("#btnPacking").click(function () {
        patentFile.Process.Packing();
    });

    $("#btnBusinessProcess").click(function () {
        patentFile.Process.BusinessProcess();
    });

    $("#btnServiceProcess").click(function () {
        patentFile.Process.ServiceProcess();
    });

    $("#btnBusinessUnProcess").click(function () {
        patentFile.Process.BusinessUnProcess();
    });

    $("#btnBusinessOnProcess").click(function () {
        patentFile.Process.BusinessOnProcess();
    });

    $("#btnServiceUnProcess").click(function () {
        patentFile.Process.ServiceUnProcess();
    });

    $("#btnServiceOnProcess").click(function () {
        patentFile.Process.ServiceOnProcess();
    });

    $("#btnHistoryPacking").click(function () {
        patentFile.HistoryProcess.Packing();
    });

    $("#btnHistoryBusinessProcess").click(function () {
        patentFile.HistoryProcess.BusinessProcess();
    });

    $("#btnHistoryServiceProcess").click(function () {
        patentFile.HistoryProcess.ServiceProcess();
    });

    $("#chkCaseFileAll").off().on("click", function () {
        if ($(this).prop("checked") == true) {
            $.checkbox.all("chkCaseFileId");
        }
        else {
            $.checkbox.not("chkCaseFileId");
        }
    });
    
    $(".inputcaseno").off().on("keypress", function () {
        if (event.keyCode == 13) {
            if ($(this).val() == '') return false;
            $.case.getCaseBasicByCaseNo($(this), $(this).val(), patentFile.getCaseBasicCallBack);
            return true;
        }
    });

    $(".inputcaseno").off().on("blur", function () {
        if ($(this).val() == '') return false;
        $.case.getCaseBasicByCaseNo($(this), $(this).val(), patentFile.getCaseBasicCallBack);
        return true;
    });

    $("#btnCaseLogClose,#btnCaseLogCancel").off().on("click", function () {
        caseInfo.CaseLog.Close();
    });

    $("#btnCaseLog").off().on("click", function () {
        caseInfo.CaseLog.CreateUpdate();
    });

    $("#btnPatentOfficeFileListExportToExcel").off().on("click", function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(200);

        patentFile.Process.ListExportToExcel();
    });

    $("#btnHisPatentOfficeFileListExportToExcel").off().on("click", function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(200);

        patentFile.HistoryProcess.ListExportToExcel();
    });

    $("#btnCheckListSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        patentFile.CheckList.List();
    });

    $("#btnCheckListFileUpload").click(function () {
        patentFile.CheckList.CheckListFile.Open();
    });

    $("#btnPatentOfficeFileCheckListImport").off().on("click", function () {
        patentFile.CheckList.CheckListFile.Upload();
    });

    $("#btnPatentOfficeFileCheckListImportClose,#btnPatentOfficeFileCheckListImportCancel").off().on("click", function () {
        patentFile.CheckList.CheckListFile.Close();
    });

    $("#flCheckListFile").off().on("change", function () {
        $("#txtCheckListFilePath").val($("#flCheckListFile").val());
    });

    $("#btnCheckListExport").off().on("click", function () {
        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(60000);

        patentFile.CheckList.ListExportToExcel();
    });
    
});