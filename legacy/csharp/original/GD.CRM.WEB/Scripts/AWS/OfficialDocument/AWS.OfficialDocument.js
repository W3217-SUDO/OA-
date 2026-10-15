var officialDocument = {
    ResetSize: function () {
        if ($("#divList").length > 0) {
            $("#divList").css("height", $(window).height() - $("#divList").offset().top - 12);
        }
    },
    OfficialDocuments: {
        List: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocument/List", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblOfficialDocumentList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.OfficialDocuments, function (i, officialDocument) {
                            var fileHtml = "";
                            $.each(officialDocument.OfficialDocumentFileList, function (i, file) {
                                fileHtml += "<a href='javascript:void(0);' onclick='javascript:officialDocument.OfficialDocuments.OfficialDocument.Audits.Preview(\"" + officialDocument.Basic.OfficialDocumentNo + "\");'><span>" + file.FileName + "</span></a><br>";
                            });
                            if (AP_PAGE_ID == "8101002001") {
                                $("tbody", "#tblOfficialDocumentList").addRow(
                                  "<input type='checkbox' id='chkOfficialDocumentId' name='chkOfficialDocumentId'  customerNo=" + officialDocument.Basic.CustomerNo + " officialDocumentGuid=" + officialDocument.Basic.OfficialDocumentGuid + " value=" + officialDocument.Basic.OfficialDocumentNo + ">",
                                    "<a href='javascript:void(0);' onclick='javascript:officialDocument.OfficialDocuments.OfficialDocument.Audits.Audit.View(\"" + officialDocument.Basic.OfficialDocumentNo + "\");'><span>" + officialDocument.Basic.OfficialDocumentNo + "</span></a>",
                                    officialDocument.Basic.BusinessOwnerName,
                                    officialDocument.Basic.ApplicationDate == null ? '' : getDate(convertJsonDateToJSDate(officialDocument.Basic.ApplicationDate)),
                                    officialDocument.Basic.OfficialDocumentStatusName,
                                    officialDocument.Basic.OfficialDocumentTypeName,
                                    officialDocument.Basic.SealTypeName,
                                    "<a href='javascript:void(0);' onclick='javascript:officialDocument.OfficialDocuments.OfficialDocument.Files.Preview(\"" + officialDocument.Basic.OfficialDocumentGuid + "\");'><span>" + officialDocument.OfficialDocumentFileList.length + "</span></a>",
                                    officialDocument.Basic.CaseNo == null ? "" : "<a href='javascript:void(0);' onclick='javascript:$.case.View(\"" + officialDocument.Basic.CaseNo + "\");'><span>" + officialDocument.Basic.CaseNo + "</span></a>",
                                    officialDocument.Basic.ContractNo,
                                    officialDocument.Basic.CustomerName,
                                    officialDocument.Basic.AuditorName,
                                    officialDocument.Basic.AuditTime == null ? '' : getDate(convertJsonDateToJSDate(officialDocument.Basic.AuditTime)),
                                    officialDocument.Basic.AuditRemark
                                 );
                            }
                            else if (AP_PAGE_ID == "8101001001") {
                                $("tbody", "#tblOfficialDocumentList").addRow(
                                    "<input type='checkbox' id='chkOfficialDocumentId' name='chkOfficialDocumentId'  customerNo=" + officialDocument.Basic.CustomerNo + " officialDocumentGuid=" + officialDocument.Basic.OfficialDocumentGuid + " value=" + officialDocument.Basic.OfficialDocumentNo + ">",
                                    "<a href='javascript:void(0);' onclick='javascript:officialDocument.OfficialDocuments.OfficialDocument.Preview(\"" + officialDocument.Basic.OfficialDocumentNo + "\");'><span>" + officialDocument.Basic.OfficialDocumentNo + "</span></a>",
                                    officialDocument.Basic.BusinessOwnerName,
                                    officialDocument.Basic.ApplicationDate == null ? '' : getDate(convertJsonDateToJSDate(officialDocument.Basic.ApplicationDate)),
                                    officialDocument.Basic.OfficialDocumentStatusName,
                                    officialDocument.Basic.OfficialDocumentTypeName,
                                    officialDocument.Basic.SealTypeName,
                                    "<a href='javascript:void(0);' onclick='javascript:officialDocument.OfficialDocuments.OfficialDocument.Files.Preview(\"" + officialDocument.Basic.OfficialDocumentGuid + "\");'><span>" + officialDocument.OfficialDocumentFileList.length + "</span></a>",
                                    officialDocument.Basic.CaseNo == null ? "" : "<a href='javascript:void(0);' onclick='javascript:$.case.View(\"" + officialDocument.Basic.CaseNo + "\");'><span>" + officialDocument.Basic.CaseNo + "</span></a>",
                                    officialDocument.Basic.ContractNo,
                                    officialDocument.Basic.CustomerName,
                                    officialDocument.Basic.AuditorName,
                                    officialDocument.Basic.AuditTime == null ? '' : getDate(convertJsonDateToJSDate(officialDocument.Basic.AuditTime)),
                                    officialDocument.Basic.AuditRemark
                                );
                            }
                            else {
                                $("tbody", "#tblOfficialDocumentList").addRow(
                                    "<input type='checkbox' id='chkOfficialDocumentId' name='chkOfficialDocumentId'  customerNo=" + officialDocument.Basic.CustomerNo + " officialDocumentGuid=" + officialDocument.Basic.OfficialDocumentGuid + " value=" + officialDocument.Basic.OfficialDocumentNo + ">",
                                    "<a href='javascript:void(0);' onclick='javascript:officialDocument.OfficialDocuments.OfficialDocument.Preview(\"" + officialDocument.Basic.OfficialDocumentNo + "\");'><span>" + officialDocument.Basic.OfficialDocumentNo + "</span></a>",
                                    officialDocument.Basic.BusinessOwnerName,
                                    officialDocument.Basic.ApplicationDate == null ? '' : getDate(convertJsonDateToJSDate(officialDocument.Basic.ApplicationDate)),
                                    officialDocument.Basic.OfficialDocumentStatusName,
                                    officialDocument.Basic.OfficialDocumentTypeName,
                                    officialDocument.Basic.SealTypeName,
                                    "<a href='javascript:void(0);' onclick='javascript:officialDocument.OfficialDocuments.OfficialDocument.Files.Preview(\"" + officialDocument.Basic.OfficialDocumentGuid + "\");'><span>" + officialDocument.OfficialDocumentFileList.length + "</span></a>",
                                    officialDocument.Basic.CaseNo == null ? "" : "<a href='javascript:void(0);' onclick='javascript:$.case.View(\"" + officialDocument.Basic.CaseNo + "\");'><span>" + officialDocument.Basic.CaseNo + "</span></a>",
                                    officialDocument.Basic.ContractNo,
                                    officialDocument.Basic.CustomerName,
                                    officialDocument.Basic.AuditorName,
                                    officialDocument.Basic.AuditTime == null ? '' : getDate(convertJsonDateToJSDate(officialDocument.Basic.AuditTime)),
                                    officialDocument.Basic.AuditRemark
                                 );
                            }
                        });
                        $("tfoot", "#tblOfficialDocumentList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.officialdocument").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: officialDocument.OfficialDocuments.List,
                            callBackArgs: null
                        });
                    } else {
                        $("tfoot", "#tblOfficialDocumentList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        Layout: function () {
            var data = {
                investigationTaskNo: $("#InvestigationTask_Basic_TaskNo").val(),
            };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/ClueList", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $("#dv_ClueList").empty();
                    $("#dv_ClueList").html(response.Data);
                    investigation.Investigations.Investigation.Clues.List();
                    $.closeLoading();
                }
            }, true);
        },
        Selected: function (e) {
            if ($(e).prop('checked') == true) {
                $.checkbox.all("chkOfficialDocumentId");
                $.checkbox.all("chkOfficialDocumentAll");

            } else {
                $.checkbox.not("chkOfficialDocumentId");
                $.checkbox.not("chkOfficialDocumentAll");
            }
        },
       
        Download: function (officialDocumentNos) {
            var data = {
                officialDocumentNos: officialDocumentNos,
            };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocument/Download", data, function (response) {
                if (response.IsSuccess) {
                    $.showTips("打包下载成功.", 0, 3);
                    window.open(AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocumentFile/ExportTempFileDownload?fileName=" + response.Data.FileName);
                    return true;
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        OfficialDocument: {
            Preview: function (officialDocumentNo) {
                var data =
                {
                    officialDocumentNo: officialDocumentNo,
                };
                var url = AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocument/Preview";
                $.openLoading();
                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(".slide-panel-container").empty();
                    $(".slide-panel-container").append(result);
                    $(".slide-panel-container").addClass("show-panel");
                });
            },
            Create: function () {
                var data = {};
                var url = AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocument/Create";
                $.openLoading();
                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(".slide-panel-container").empty();
                    $(".slide-panel-container").append(result);
                    $(".slide-panel-container").addClass("show-panel");
                });
            },
            CreateByContract: function (contractNo,contractFileIds) {
                var data = {};
                var url = AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocument/CreateByContract?contractNo=" + contractNo + "&contractFileIds=" + contractFileIds;
                $.openLoading();
                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(".slide-panel-container").empty();
                    $(".slide-panel-container").append(result);
                    $(".slide-panel-container").addClass("show-panel");
                    $(document).ready(function () {
                        $("#OfficialDocument_Basic_OfficialDocumentType_1").parents(".radio-item").click();
                        contract.Contracts.Contract.ContractNo.AddIn(contractNo);
                    })
                });
            },
            CreateByCase: function (caseNo, caseFileIds) {
                var data = {};
                var url = AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocument/CreateByCase?caseNo=" + caseNo + "&caseFileIds=" + caseFileIds;
                $.openLoading();
                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(".slide-panel-container").empty();
                    $(".slide-panel-container").append(result);
                    $(".slide-panel-container").addClass("show-panel");
                    $(document).ready(function () {
                        $("#OfficialDocument_Basic_OfficialDocumentType_2").parents(".radio-item").click();
                        c.Cases.Case.CaseNo.AddIn(caseNo);
                    })
                });
            },
            Edit: function (officialDocumentNo) {
                var data = {
                    officialDocumentNo: officialDocumentNo,
                };
                var url = AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocument/Edit";
                $.openLoading();
                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(".slide-panel-container").empty();
                    $(".slide-panel-container").append(result);
                    $(".slide-panel-container").addClass("show-panel");
                });
            },
            checkIntput: function () {
                if ($("#OfficialDocument_Basic_OfficialDocumentType_1").attr("checked") == "checked") {
                    var contractNos = [];
                    $("a[name='contractno']").each(function () {
                        contractNos.push($(this).attr("contractno"));
                    });
                    if (contractNos.length == 0) {
                        $.showModalMessageBox("请选择合同.");
                        return false;
                    }
                }
                else if ($("#OfficialDocument_Basic_OfficialDocumentType_2").attr("checked") == "checked") {
                    var casenos = [];
                    $("a[name='caseno']").each(function () {
                        casenos.push($(this).attr("caseno"));
                    });
                    if (casenos.length == 0) {
                        $.showModalMessageBox("请选择案件.");
                        return false;
                    }
                }
     
                var sealTypeId = 0;
                $("input[name='OfficialDocument_Basic_SealType']:checked").each(
                    function (i) { sealTypeId = sealTypeId | parseInt($(this).val()) }
                );
                if (sealTypeId == 0) {
                    $.showTips("请选择印章类型.", 0, 3);
                    return false;
                }

                var filenames = [];
                $("a[name='attachmentfile']").each(function () {
                    filenames.push($(this).attr("filename"));
                });
                if (filenames.length == 0) {
                    $.showModalMessageBox("请上传用印文件.");
                    return false;
                }
                return true;
            },
            getIntput: function () {
                var officialDocument = {};
                officialDocument.OfficialDocumentGuid = $("#OfficialDocument_Basic_OfficialDocumentGuid").val();
                var sealTypeId = 0;
                $("input[name='OfficialDocument_Basic_SealType']:checked").each(
                    function (i) { sealTypeId = sealTypeId | parseInt($(this).val())  }
                );
                if (sealTypeId == 0) {
                    return false;
                }
                officialDocument.OfficialDocumentType = $('input:radio[name="OfficialDocument_Basic_OfficialDocumentType"]:checked').val();
                if ($("#OfficialDocument_Basic_OfficialDocumentType_1").attr("checked") == "checked") {
                    var contractNos = [];
                    $("a[name='contractno']").each(function () {
                        contractNos.push($(this).attr("contractno"));
                    });
                    officialDocument.ContractNo = contractNos[0];
                    officialDocument.CustomerNo = $("#OfficialDocument_Basic_CustomerNo").val();
                }
                else if ($("#OfficialDocument_Basic_OfficialDocumentType_2").attr("checked") == "checked") {
                    var casenos = [];
                    $("a[name='caseno']").each(function () {
                        casenos.push($(this).attr("caseno"));
                    });
                    officialDocument.CaseNo = casenos[0];
                    officialDocument.ContractNo = $("#OfficialDocument_Basic_ContractNo").val();
                    officialDocument.CustomerNo = $("#OfficialDocument_Basic_CustomerNo").val();
                }
               
                officialDocument.OfficialDocumentNo = $("#OfficialDocument_Basic_OfficialDocumentNo").val();
                officialDocument.OfficialDocumentId = $("#OfficialDocument_Basic_OfficialDocumentId").val();
                officialDocument.IsElectronicSeal = $('input:radio[name="OfficialDocument_Basic_IsElectronicSeal"]:checked').val();
                officialDocument.SealType = sealTypeId;
                officialDocument.IsOfflinePrint = $('input:radio[name="OfficialDocument_Basic_IsOfflinePrint"]:checked').val();
                officialDocument.PrintQuantity = $("#OfficialDocument_Basic_PrintQuantity").val();
                officialDocument.Remark = $("#OfficialDocument_Basic_Remark").val();

                var data = {
                    officialDocument: officialDocument,
                };
                return data;
            },
            CreateUpdate: function (needToAudit,callBackFunc) {
                try {
                    if (!officialDocument.OfficialDocuments.OfficialDocument.checkIntput()) return false;
                    var data = officialDocument.OfficialDocuments.OfficialDocument.getIntput();
                    $.ajaxPostJson(AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocument/CreateUpdate", JSON.stringify({ request: data, needToAudit: needToAudit }), function (response) {
                        if (response.IsSuccess) {
                            $.showTips((needToAudit ? "提交成功." : "保存成功"), 0, 3);
                            $('.slide-panel-container').empty();
                            $('.slide-panel-container').removeClass('show-panel');
                            if (callBackFunc != null) {
                                callBackFunc();
                            }
                            else {
                                officialDocument.OfficialDocuments.List();
                            }
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                    } catch (e) {
                }
            },
            CreateUpdateByContractCallBack: function () {
                //window.location = AP_ROOT + "REDACTED_ARCHIVE_ONLY";
                return true;
            },
            CreateUpdateByCaseCallBack: function () {
                //$.showTips("提交成功", 0, 3);
                return true;
            },
            Delete: function (clueNos) {
                $.showModalConfirmDialog("确定删除调查线索？", "investigation.Investigations.Investigation.Clues.Clue.DeleteCallBack", clueNos);
                return true;
            },
            DeleteCallBack: function (clueNos) {
                var data = {
                    clueNos: clueNos,
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/Delete", data, function (response) {
                    if (response.IsSuccess) {
                        investigation.Investigations.Investigation.Clues.ClueList();
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },
            ToAudit: function (clueNos) {
                $.showModalConfirmDialog("确定提交审批？", "investigation.Investigations.Investigation.Clues.Clue.ToAuditCallBack", clueNos);
                return true;
            },
            ToAuditCallBack: function (clueNos) {
                try {
                    var data = { clueNos: clueNos };
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueAudit/ToAudit", data, function (response) {
                        if (response.IsSuccess) {

                            $.showModalMessageBox("提交成功.");

                            try {
                                investigation.Investigations.Investigation.Clues.ClueList();
                            }
                            catch (e) {
                            }
                            try {
                                investigation.Investigations.Investigation.Clues.List();
                            }
                            catch (e) {
                            }

                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                } catch (e) {

                }
            },
            Audits: {
                Preview: function (officialDocumentNo) {
                    var data = { officialDocumentNo: officialDocumentNo };
                    var url = AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocumentAudit/AuditList";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#auditListModal').modal({ backdrop: 'static', keyboard: false });
                        $('#auditListModal').on('hidden.bs.modal', function () {
                            $("#auditListModal").remove();
                        });
                    });
                },
                List: function () {
                    var data = {
                        contractId: $("#Contract_ContractBasicInfo_ContractId").val()
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractAudit/ContractAudits", data, function (response) {
                        if (response.IsSuccess) {
                            $.openLoading();
                            $.each(response.Data, function (i, audit) {
                                $("tbody", "#tblContractAuditList").addRow(
                                    ++i,
                                    audit.AuditorName,
                                    audit.AuditStatusName,
                                    audit.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(audit.AuditDate)),
                                    audit.AuditContent
                                );
                            });

                            contract.ResetSize();
                            $.closeLoading();
                        }
                    }, true);
                },
                Audit: {
                    View: function (officialDocumentNo) {
                        var data =
                        {
                            officialDocumentNo: officialDocumentNo,
                        };
                        var url = AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocumentAudit/Audit";
                        $.openLoading();
                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(".slide-panel-container").empty();
                            $(".slide-panel-container").append(result);
                            $(".slide-panel-container").addClass("show-panel");
                        });
                    },
                    ToAudit: function (contractId, isDraft) {
                        var data = {};
                        data["ContractId"] = contractId;

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/Contract/ToAudit", data, function (response) {
                            if (response.IsSuccess) {
                                if (isDraft) {
                                    contract.Sponsor.DraftList();
                                } else {
                                    contract.Sponsor.RejectedList();
                                }

                                $.showModalMessageBox("提交成功.");

                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },
                    ViewAudit: function (contractId, contractNo) {

                        var data =
                        {
                            contractId: contractId,
                            contractNo: contractNo
                        };

                        var url = AP_ROOT + AP_PAGE_ID + "/FCM/ContractAudit/ContractAuditList";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#contractAuditListModal').modal({ backdrop: 'static', keyboard: false });
                            $('#contractAuditListModal').on('hidden.bs.modal', function () {
                                $("#contractAuditListModal").remove();
                            });
                        });

                    },
                    AuditClose: function () {
                        $('#contractAuditListModal').modal('hide');
                    },
                    Open: function (contractId, contractNo) {

                        var data =
                        {
                            contractId: contractId,
                            contractNo: contractNo
                        };

                        var url = AP_ROOT + AP_PAGE_ID + "/FCM/ContractAudit/ContractAudit";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#contractAuditModal').modal({ backdrop: 'static', keyboard: false });
                            $('#contractAuditModal').on('hidden.bs.modal', function () {
                                $("#contractAuditModal").remove();
                            });
                        });

                    },
                    Close: function () {
                        $('.slide-panel-container').empty(); $('.slide-panel-container').removeClass('show-panel');
                    },
                    Approved: function () {
                        var data = {
                            officialDocumentNo: $("#OfficialDocument_Basic_OfficialDocumentNo").val(),
                            auditRemark: $("#OfficialDocument_Audit_Remark").val(), 
                        };
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocumentAudit/Approved", data, function (response) {
                            if (response.IsSuccess) {
                                $.showTips("已审核",0,3);
                                officialDocument.OfficialDocuments.List();
                                officialDocument.OfficialDocuments.OfficialDocument.Audits.Audit.Close();
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },
                    Rejected: function () {
                        var data = {
                            officialDocumentNo: $("#OfficialDocument_Basic_OfficialDocumentNo").val(),
                            auditRemark: $("#OfficialDocument_Audit_Remark").val(),
                        };
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocumentAudit/Rejected", data, function (response) {
                            if (response.IsSuccess) {
                                $.showTips("已拒绝", 0, 3);
                                officialDocument.OfficialDocuments.List();
                                officialDocument.OfficialDocuments.OfficialDocument.Audits.Audit.Close();
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },
                    CreateUpdateCallBack: function () {
                        window.location = AP_ROOT + "REDACTED_ARCHIVE_ONLY";
                    },
                },
            },
            Files: {
                Preview: function (officialDocumentGuid) {
                    var data = { officialDocumentGuid: officialDocumentGuid };
                    var url = AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocumentFile/FileList";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#fileListModal').modal({ backdrop: 'static', keyboard: false });
                        $('#fileListModal').on('hidden.bs.modal', function () {
                            $("#fileListModal").remove();
                        });
                    });
                },
                List: function () {
                    var data = {
                        investigationClueGuid: $("#InvestigationClue_Basic_ClueGuid").val(),
                        pageNo: $("#PageNo").val(),
                        pageSize: $("#PageSize").val()
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueFile/InvestigationClueFiles", data, function (response) {
                        if (response.IsSuccess) {
                            $.openLoading();
                            $("tbody", "#tblInvestigationClueFileList").clearRow();
                            if (response.Data.TotalItemCount > 0) {
                                $.each(response.Data.InvestigationClueFiles, function (i, file) {

                                    $("tbody", "#tblInvestigationClueFileList").addRow(
                                       "<input type='checkbox' id='chkFileId' name='chkFileId' value=" + file.FileId + ">",
                                        file.UploadingUserName,
                                        file.FileName,
                                        file.UploadingTime == null ? '' : getDate(convertJsonDateToJSDate(file.UploadingTime)),
                                        "<a style='color: #039' href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Clues.Clue.Files.File.View(" + file.FileId + ",\"" + file.ClueGuid + "\",\"" + file.FileName + "\");'><span>查看</span></a>&nbsp;&nbsp;&nbsp;" +
                                        "<a style='color: #039' href='javascript:void(0);' onclick='javascript:investigation.Investigations.Investigation.Clues.Clue.Files.File.Download(\"" + file.FileId + "\");'><span>下载</span></a>"
                                    );
                                });

                                $("tfoot", "#tblInvestigationClueFileList").show();
                                $(".simple-grid-none-data-wrap.none-investigationcluefile").hide();

                                $(".pull-right.page-box.InvestigationClueFile").cPaging({
                                    totalCount: response.Data.TotalItemCount,
                                    pageNo: response.Data.PageNo,
                                    pageSize: response.Data.PageSize,
                                    callBack: investigation.Investigations.Investigation.Clues.Clue.Files.List,
                                    callBackArgs: null
                                });

                            } else {
                                $(".simple-grid-none-data-wrap.none-investigationcluefile").show();
                                $("tfoot", "#tblInvestigationClueFileList").hide();

                            }
                            investigation.ResetSize();
                            $.closeLoading();
                        }
                    }, true);
                },
                Selected: function (e) {
                    if ($(e).prop('checked') == true) {
                        $.checkbox.all("chkFileId");
                        $.checkbox.all("chkFileAll");

                    } else {
                        $.checkbox.not("chkFileId");
                        $.checkbox.not("chkFileAll");
                    }
                },
                File: {
                    Open: function (investigationClueNo) {
                        var data =
                        {
                            investigationClueNo: investigationClueNo,
                        };
                        var url = AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClueFile/FileUpload";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#investigationClueFileModal').modal({ backdrop: 'static', keyboard: false });
                            $('#investigationClueFileModal').on('hidden.bs.modal', function () {
                                $("#investigationClueFileModal").remove();
                            });
                        });
                    },
                    Close: function () {
                        $('#investigationClueFileModal').modal('hide');
                    },
                    Upload: function (e) {
                        if ($("#flOfficialDocumentFile").val() == '') {
                            $.showModalMessageBox("请选择上传文件.");
                            return false;
                        }
                        $('#officialDocument').ajaxSubmit({
                            success: function (response) {
                                $.showModalMessageBox("上传成功.");
                                if (response.IsSuccess) {
                                    $.each(response.Data, function (i, f) {
                                        officialDocument.OfficialDocuments.OfficialDocument.Files.File.AddIn(f);
                                    });
                                    $("#help-block").hide()
                                } else {
                                    $("#help-block").show();
                                }
                            }
                        });
                    },
                    AddIn: function (f) {
                        //debugger
                        $("#attachments").append("<div  class='margin-top'><span>" + f.FileName + "</span> "
                         + "<a name='attachmentfile' filename=" + f.FileName + " href='javascript:void(0);' onclick='javascript:officialDocument.OfficialDocuments.OfficialDocument.Files.File.DeleteFile(this," + f.FileId + ")'>删除</a></div>");
                    },


                    View: function (officialDocumentFileId, officialDocumentGuid, officialDocumentFileName) {
                        if (officialDocumentFileId == '' || officialDocumentFileId == '') {
                            $.showModalMessageBox("无文件.");
                            return false;
                        }
                        var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                        var picfiles = new Array('jpg','png','tif', 'pdf');
                        var extName = officialDocumentFileName.substring(officialDocumentFileName.lastIndexOf('.') + 1, officialDocumentFileName.length);
                        if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                            var path = GV_LS.OfficeOnlineUrl + GV_LS.OnlineUrl + "CaseFiles/OfficialDocumentFiles/" + officialDocumentGuid + "/" + officialDocumentFileName;
                            window.open(path);
                        }
                        else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                            var path = GV_LS.OnlineUrl + "CaseFiles/OfficialDocumentFiles/" + officialDocumentGuid + "/" + officialDocumentFileName;
                            window.open(path);
                        } else {
                            officialDocument.OfficialDocuments.OfficialDocument.Files.File.Download(officialDocumentFileId);
                        }
                        return true;
                    },
                    Download: function (officialDocumentFileId) {
                        window.open(AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocumentFile/OfficialDocumentFileDownload?officialDocumentFileId=" + officialDocumentFileId);
                        return true;
                    },
                    Delete: function (fileIds, functionCallback) {
                        var data = {
                            fileIds: fileIds,
                        };
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocumentFile/Delete", data, function (response) {
                            if (response.IsSuccess) {
                                $.showModalMessageBox("删除成功.");

                                if (functionCallback != null) {
                                    setTimeout(functionCallback(), 200);
                                }
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },
                    DeleteFile: function (e, fileId) {
                        var fileIds = new Array();
                        fileIds.push(fileId);
                        var data = {
                            fileIds: fileIds,
                        };
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocumentFile/Delete", data, function (response) {
                            if (response.IsSuccess) {
                                $(e).parent().remove();
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    }

                },
            },
            Rollback: function () {
                var officialDocumentNos = $.checkbox.vals("chkOfficialDocumentId");
                if (officialDocumentNos.length == 0) {
                    $.showTips("请选择需要撤回的用印申请.", 0, 3);
                    return false;
                }
                $.showModalConfirmDialog("确定撤回用印申请？", "officialDocument.OfficialDocuments.OfficialDocument.RollbackCallBack", officialDocumentNos);
                return true;
            },

            RollbackCallBack: function (officialDocumentNos) {

                var data = {
                    officialDocumentNos: officialDocumentNos,
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocument/Rollback", data, function (response) {
                    if (response.IsSuccess) {
                        $.showTips("用印申请已撤回.", 0, 3);
                        officialDocument.OfficialDocuments.List();
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },

            Stamp: {
               UploadFile : function (officialDocumentNos) {
                    //var data = {
                    //    officialDocumentNos: officialDocumentNos,
                    //};
                    //$.ajaxPost(AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocument/Print", data, function (response) {
                    //    if (response.IsSuccess) {
                    //        $.showTips("标记用印成功.", 0, 3);
                    //        officialDocument.OfficialDocuments.List();
                    //    } else {
                    //        $.showModalMessageBox(response.Message);
                    //    }
                    //});
                    var data = {
                        officialDocumentNos: officialDocumentNos
                    };
                    var url = AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocument/FileUpload";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#officialDocumentFileUpload').modal({ backdrop: 'static', keyboard: false });
                        $('#officialDocumentFileUpload').on('hidden.bs.modal', function () {
                            $("#officialDocumentFileUpload").remove();
                        });

                        $(document).ready(function () {
                            $("#officialDocumentNos").val(officialDocumentNos.join(","));
                        });
                    });
               },

               Close: function () {
                   $('#officialDocumentFileUpload').modal('hide');
               },
               Upload: function (e) {
                   //if ($("#flOfficialDocumentFile").val() == '') {
                   //    $.showModalMessageBox("请选择上传文件.");
                   //    return false;
                   //}
                   $('#fileUploadForm').ajaxSubmit({
                       success: function (response) {
                           $.showTips("标记用印成功.", 0, 3);
                           if (response.IsSuccess) {
                               $('#officialDocumentFileUpload').modal('hide');
                               officialDocument.OfficialDocuments.List();
                           }
                       }
                   });
               },



            },
        },
    },
};
 

$(document).ready(function () {

    $(window).resize(function () {
        officialDocument.ResetSize();
    });

    $(document).click(function () {
    });

    $(document).off('click', '#btnOfficialDocumentFileUpload').on('click', '#btnOfficialDocumentFileUpload', function () {
        $("#flOfficialDocumentFile").trigger("click");
    });

    $(document).off('change', '#flOfficialDocumentFile').on('change', '#flOfficialDocumentFile', function () {
        officialDocument.OfficialDocuments.OfficialDocument.Files.File.Upload();
    });

    $(document).off('click', '#btnOfficialDocumentCreateUpdate').on('click', '#btnOfficialDocumentCreateUpdate', function () {
        officialDocument.OfficialDocuments.OfficialDocument.Create();
    });

    $(document).off('click', '#btnOfficialDocumentEdit').on('click', '#btnOfficialDocumentEdit', function () {

        /*列表选中修改*/
        var officialDocumentIds = $.checkbox.vals("chkOfficialDocumentId");
        if (officialDocumentIds.length == 0) {
            $.showModalMessageBox("请选择用印申请.");
            return false;
        }
        if (officialDocumentIds.length > 1) {
            $.showModalMessageBox("只能选择一个用印申请进行修改.");
            return false;
        }
        var officialDocumentId = officialDocumentIds[0];
        officialDocument.OfficialDocuments.OfficialDocument.Edit(officialDocumentId);
    });

    $(document).off('click', '#btnOfficialDocumentToAudit').on('click', '#btnOfficialDocumentToAudit', function () {
        officialDocument.OfficialDocuments.OfficialDocument.CreateUpdate(true,null);
    });

    $(document).off('click', '#btnOfficialDocumentByContractToAudit').on('click', '#btnOfficialDocumentByContractToAudit', function () {
        officialDocument.OfficialDocuments.OfficialDocument.CreateUpdate(true, officialDocument.OfficialDocuments.OfficialDocument.CreateUpdateByContractCallBack);
    });

    $(document).off('click', '#btnOfficialDocumentByCaseToAudit').on('click', '#btnOfficialDocumentByCaseToAudit', function () {
        officialDocument.OfficialDocuments.OfficialDocument.CreateUpdate(true, officialDocument.OfficialDocuments.OfficialDocument.CreateUpdateByCaseCallBack);
    });

    $(document).off('click', '#btnOfficialDocumentAudit').on('click', '#btnOfficialDocumentAudit', function () {
        if ($('input:radio[name="OfficialDocument_Audit"]:checked').val() == 'true') {
            officialDocument.OfficialDocuments.OfficialDocument.Audits.Audit.Approved();
        }
        else {
            officialDocument.OfficialDocuments.OfficialDocument.Audits.Audit.Rejected();
        }
    });

    $(document).off('click', '#btnOfficialDocumentAuditApproved').on('click', '#btnOfficialDocumentAuditApproved', function () {
        officialDocument.OfficialDocuments.OfficialDocument.Audits.Audit.Approved();
    });

    $(document).off('click', '#btnOfficialDocumentAuditRejected').on('click', '#btnOfficialDocumentAuditRejected', function () {
        officialDocument.OfficialDocuments.OfficialDocument.Audits.Audit.Rejected();
         
    });

    $(document).off('click', '#btnOfficialDocumentPrint').on('click', '#btnOfficialDocumentPrint', function () {
        var officialDocumentNos = $.checkbox.vals("chkOfficialDocumentId");
        if (officialDocumentNos.length == 0) {
            $.showTips("请选择用印文件.",0,3);
            return false;
        }
        officialDocument.OfficialDocuments.OfficialDocument.Stamp.UploadFile(officialDocumentNos);
    });

    $(document).off('click', '#btnOfficialDocumentUpload').on('click', '#btnOfficialDocumentUpload', function () {
        officialDocument.OfficialDocuments.OfficialDocument.Stamp.Upload();
    });

    $(document).off('click', '#btnOfficialDocumentUploadClose,#btnOfficialDocumentUploadCancel').on('click', '#btnOfficialDocumentUploadClose,#btnOfficialDocumentUploadCancel', function () {
        officialDocument.OfficialDocuments.OfficialDocument.Stamp.Close();
    });

    $(document).off('click', '#btnOfficialDocumentDownload').on('click', '#btnOfficialDocumentDownload', function () {
        var officialDocumentNos = $.checkbox.vals("chkOfficialDocumentId");
        if (officialDocumentNos.length == 0) {
            $.showTips("请选择用印文件.", 0, 3);
            return false;
        }
        officialDocument.OfficialDocuments.Download(officialDocumentNos);
    });

    $(document).off('click', '#flOfficialDocumentFile').on('change', '#flOfficialDocumentFile', function () {
        $("#txtOfficialDocumentFilePath").val($("#flOfficialDocumentFile").val());
    });

    $(document).off('click', '.btn_contract_search').on('click', '.btn_contract_search', function () {
        contract.Contracts.List();
    });

    $(document).off('click', '.contractremove').on('click', '.contractremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        $("#OfficialDocument_Basic_CustomerNo").val('');
        $("#OfficialDocument_Basic_CustomerName").val('');

        $(this).parent().remove();
    });

    $(document).off('click', '.btn_case_search').on('click', '.btn_case_search', function () {
        c.Cases.SelectedList();
    });

    $(document).off('click', '.caseremove').on('click', '.caseremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        $("#OfficialDocument_Basic_ContractNo").val('');
        $("#OfficialDocument_Basic_CustomerNo").val('');
        $("#OfficialDocument_Basic_CustomerName").val('');

        $(this).parent().remove();
    });
    
    $(document).off('click', '#btnCaseListSearch').on('click', '#btnCaseListSearch', function () {
        c.Cases.List();
    });

    $(document).off('click', '#btnContractListSearch').on('click', '#btnContractListSearch', function () {
        contract.Contracts.List();
    });
    
    officialDocument.ResetSize();
});