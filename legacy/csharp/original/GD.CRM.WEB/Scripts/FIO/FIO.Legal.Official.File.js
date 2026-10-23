var officialFile = {
    ResetSize: function () {
        if ($("#divList").length > 0) {
            $("#divList").css("height", $(window).height() - $("#divList").offset().top - 12);
        }
    },
    List: function (response) {
        $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/LegalOfficialFile/GetOfficialFiles", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseFileList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    if (response.Data.CaseFileList.length > 10) {
                        $(".divdropdown").removeClass("dropdown");
                        $(".divdropdown").addClass("dropup");
                    }
                    else {
                        $(".divdropdown").removeClass("dropup");
                        $(".divdropdown").addClass("dropdown");
                    }
                    $.each(response.Data.CaseFileList, function (i, f) {
                        $("tbody", "#tblCaseFileList").addRow(
                            "<input type='checkbox' name='chkCaseId' caseFileId =" + f.FileId + " value='" + f.Parent.Basic.CaseNo + "'>",
                            f.InformDate == null ? '' : getDate(convertJsonDateToJSDate(f.InformDate)),
                            "<a href='javascript:void(0)' onclick='javascript:c.Cases.Case.View(\"" + f.Parent.Basic.CaseNo + "\")'>" + f.Parent.Basic.CaseNo + "</a>",
                            f.Parent.Basic.OfficialNo,
                            f.Parent.Basic.AppellantNames,
                            f.Parent.Basic.AppelleeNames,
                            "<a style='color: #039' href='javascript:void(0);' onclick='javascript:c.Cases.Case.CaseFiles.CaseFile.View(" + f.FileId + ",\"" + 7 + "\",\"" + f.FileName + "\",\"" + f.OnlineUrl + "\"); '><span>"+ f.FileName +"</span></a>&nbsp;" ,
                            f.UploadingTime == null ? '' : getDate(convertJsonDateToJSDate(f.UploadingTime)),
                            f.Parent.Basic.CourtLawyerName,
                            f.Parent.Basic.CaseAssistantName,
                            f.Parent.Basic.CoordinatorName
                        );
                    });
                    $("tfoot", "#tblCaseFileList").show();
                    $(".simple-grid-none-data-wrap").hide();
                    $(".pull-right.page-box.caseFileList").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: officialFile.List,
                        callBackArgs: null
                    });
                } else {
                    $("tfoot", "#tblCaseFileList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },
    MetaFile: {
        Open: function () {
            debugger
            var url = AP_ROOT + AP_PAGE_ID + "/FIO/LegalOfficialFile/MetaFile";
            $.openLoading();
            $("<div></div>").load(url, null, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#metaFileUpload').modal({ backdrop: 'static', keyboard: false });
                $('#metaFileUpload').on('hidden.bs.modal', function () {
                    $("#metaFileUpload").remove();
                });
            });
        },
        Close: function () {
            $('#metaFileUpload').modal('hide');
        },
        Upload: function () {
            if ($("#flMetaFile").val() == '') {
                $.showModalMessageBox("请选择上传的文件.");
                return false;
            }
            $("#uploadingForm").attr("action", AP_ROOT + AP_PAGE_ID + "/FIO/LegalOfficialFile/MetaFileUpload");
            $.openLoading();
            $('#uploadingForm').ajaxSubmit({
                success: function (response) {
                    $.closeLoading();
                    if (response.IsSuccess) {
                        officialFile.MetaFile.List();
                        officialFile.MetaFile.Close();
                        $("#message").text(response.Message);
                        $.showModalMessageBox("上传成功.");
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                }
            });
            return true;
        },
        List: function (response) {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/LegalOfficialFile/GetMetaFiles", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblMetaFileList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        if (response.Data.MetaFileList.length > 10) {
                            $(".divdropdown").removeClass("dropdown");
                            $(".divdropdown").addClass("dropup");
                        }
                        else {
                            $(".divdropdown").removeClass("dropup");
                            $(".divdropdown").addClass("dropdown");
                        }
                        $.each(response.Data.MetaFileList, function (i, f) {
                            if (f.Parent != null) {
                                $("tbody", "#tblMetaFileList").addRow(
                                    "<input type='checkbox' name='chkMetaFileId' caseFileId =" + f.FileId + " value='" + f.FileId + "'>",
                                    "<a href='javascript:void(0)' onclick='javascript:c.Cases.Case.View(\"" + f.Parent.Basic.CaseNo + "\")'>" + f.Parent.Basic.CaseNo + "</a>",
                                    f.Parent == null ? '' : f.Parent.Basic.AppellantNames,
                                    f.Parent == null ? '' : f.Parent.Basic.AppelleeNames,
                                    "<a style='color: #039' href='javascript:void(0);' onclick='javascript:officialFile.MetaFile.View(\"" + f.OnlineUrl + "\"); '><span>" + f.FileName + "</span></a>&nbsp;",
                                    f.InformDate == null ? '' : getDate(convertJsonDateToJSDate(f.InformDate)),
                                    f.CreateTime == null ? '' : getDate(convertJsonDateToJSDate(f.CreateTime)),
                                    f.UploadUserName,
                                    f.StatusName
                                );
                            }
                            else {
                                $("tbody", "#tblMetaFileList").addRow(
                                    "<input type='checkbox' name='chkMetaFileId' caseFileId =" + f.FileId + " value='" + f.FileId + "'>",
                                    f.CaseNo,
                                    '未匹配',
                                    '未匹配',
                                    "<a style='color: #039' href='javascript:void(0);' onclick='javascript:officialFile.MetaFile.View(\"" + f.OnlineUrl + "\"); '><span>" + f.FileName + "</span></a>&nbsp;",
                                    f.InformDate == null ? '' : getDate(convertJsonDateToJSDate(f.InformDate)),
                                    f.CreateTime == null ? '' : getDate(convertJsonDateToJSDate(f.CreateTime)),
                                    f.UploadUserName,
                                    f.StatusName
                                );
                            }
                        });
                        $("tfoot", "#tblMetaFileList").show();
                        $(".simple-grid-none-data-wrap").hide();
                        $(".pull-right.page-box.metaFileList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: officialFile.MetaFile.List,
                            callBackArgs: null
                        });
                    } else {
                        $("tfoot", "#tblMetaFileList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        View: function (url) {
            window.open(url);
        },
        SelectedAll: function (e) {
            if ($(e).prop("checked") == true) {
                $.checkbox.all("chkMetaFileId");
                $.checkbox.all("chkMetaFileAll");
            } else {
                $.checkbox.not("chkMetaFileId");
                $.checkbox.not("chkMetaFileAll");
            }
        },
        Delete: function (metaFileIds) {
            $.showModalConfirmDialog("确定删除文件？", "officialFile.MetaFile.DeleteCallBack", metaFileIds);
            return true;
        },
        DeleteCallBack: function (metaFileIds) {
            var data = {
                metaFileIds: metaFileIds,
            };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/LegalOfficialFile/Delete", data, function (response) {
                if (response.IsSuccess) {
                    officialFile.MetaFile.List();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        InformDate: {
            Open: function (metaFileIds) {
                var data = {};
                var url = AP_ROOT + AP_PAGE_ID + "/FIO/LegalOfficialFile/InformDate";
                $.openLoading();
                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#metaFileInformDateModal').modal({ backdrop: 'static', keyboard: false });
                    $('#metaFileInformDateModal').on('hidden.bs.modal', function () {
                        $("#metaFileInformDateModal").remove();
                    });
                    $("#MetaFileIds").val(metaFileIds);
                });
            },
            Change: function (metaFileIds, informDate, callback_func) {
                var metaFileIds = metaFileIds.split(',');
                var data = {
                    metaFileIds: metaFileIds,
                    informDate: informDate
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FIO/LegalOfficialFile/InformDateChange", data, function (response) {
                    if (response.IsSuccess) {
                        callback_func();
                        $('#metaFileInformDateModal').modal('hide');
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },
        },
    },
}

$(document).ready(function () {
    $(document).click(function () {
    });

});