var officialDocument = {
    ResetSize: function () {
        //if ($("#divContextList").length > 0) {
        //    $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 12);
        //}
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
                                    "<a href='javascript:void(0);' onclick='javascript:officialDocument.OfficialDocuments.OfficialDocument.Audits.Preview(\"" + officialDocument.Basic.OfficialDocumentNo + "\");'><span>查看</span></a>"
                                 );
                            }
                            else if (AP_PAGE_ID == "8101001001") {
                                $("tbody", "#tblOfficialDocumentList").addRow(
                                    "<input type='checkbox' id='chkOfficialDocumentId' name='chkOfficialDocumentId'  customerNo=" + officialDocument.Basic.CustomerNo + " officialDocumentGuid=" + officialDocument.Basic.OfficialDocumentGuid + " value=" + officialDocument.Basic.OfficialDocumentNo + ">",
                                    "<a href='javascript:void(0);' onclick='javascript:officialDocument.OfficialDocuments.OfficialDocument.Edit(\"" + officialDocument.Basic.OfficialDocumentNo + "\");'><span>" + officialDocument.Basic.OfficialDocumentNo + "</span></a>",
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
                                    "<a href='javascript:void(0);' onclick='javascript:officialDocument.OfficialDocuments.OfficialDocument.Audits.Preview(\"" + officialDocument.Basic.OfficialDocumentNo + "\");'><span>查看</span></a>"
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
                                    "<a href='javascript:void(0);' onclick='javascript:officialDocument.OfficialDocuments.OfficialDocument.Audits.Preview(\"" + officialDocument.Basic.OfficialDocumentNo + "\");'><span>查看</span></a>"
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
        ExportAllToExcel: function () {

            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListAllExportToExcel", function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListExportToExcelDownload?fileName=" + response.Data);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        ExportSelectedToExcel: function () {

            var clueGuids = [];
            $("input[name='chkClueId']:checked").each(
                function (i) { clueGuids[i] = $(this).attr("clueGuid"); }
            );


            if (clueGuids.length < 1) {
                $.showModalMessageBox("请选择需要导出的线索.");
                return false;
            }

            var data = {
                investigationClueGuids: clueGuids,
            };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListSelectedExportToExcel", data, function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListExportToExcelDownload?fileName=" + response.Data);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        ExportAllToExcelForManifest: function () {

            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListAllExportToExcelForManifest", function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListExportToExcelDownload?fileName=" + response.Data);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        ExportSelectedToExcelForManifest: function () {

            var clueGuids = [];
            $("input[name='chkClueId']:checked").each(
                function (i) { clueGuids[i] = $(this).attr("clueGuid"); }
            );


            if (clueGuids.length < 1) {
                $.showModalMessageBox("请选择需要导出的线索.");
                return false;
            }

            var data = {
                investigationClueGuids: clueGuids,
            };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListSelectedExportToExcelForManifest", data, function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListExportToExcelDownload?fileName=" + response.Data);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
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
        Print: function (officialDocumentNos) {
            var data = {
                officialDocumentNos: officialDocumentNos,
            };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocument/Print", data, function (response) {
                if (response.IsSuccess) {
                    $.showTips("标记用印成功.", 0, 3);
                    officialDocument.OfficialDocuments.List();
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
            CreateUpdate: function (needToAudit) {
                try {
                    if (!officialDocument.OfficialDocuments.OfficialDocument.checkIntput()) return false;
                    var data = officialDocument.OfficialDocuments.OfficialDocument.getIntput();
                    $.ajaxPostJson(AP_ROOT + AP_PAGE_ID + "/AWS/OfficialDocument/CreateUpdate", JSON.stringify({ request: data, needToAudit: needToAudit }), function (response) {
                        if (response.IsSuccess) {
                            $.showModalMessageBox((needToAudit ? "提交成功." : "保存成功"));

                            $('.slide-panel-container').empty();
                            $('.slide-panel-container').removeClass('show-panel');

                            officialDocument.OfficialDocuments.List();

                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                  } catch (e) {
                }
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
                            auditId: $("#OfficialDocumentAudit_AuditId").val(),
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
                            auditId: $("#OfficialDocumentAudit_AuditId").val(),
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
                        debugger
                        $("#attachments").append("<div  class='margin-top'><span>" + f.FileName + "</span> "
                         + "<a name='attachmentfile' filename=" + f.FileName + " href='javascript:void(0);' onclick='javascript:officialDocument.OfficialDocuments.OfficialDocument.Files.File.DeleteFile(this," + f.FileId + ")'>删除</a></div>");
                    },

                    //FileUpload: function (e) {
                    //    if ($("#flClueFile").val() == '') {
                    //        $.showModalMessageBox("请选择上传文件.");
                    //        return false;
                    //    }

                    //    $('#investigationClue').ajaxSubmit({
                    //        success: function (response) {
                    //            $.showModalMessageBox("上传成功.");
                    //            if (response.IsSuccess) {
                    //                investigation.Investigations.Investigation.Clues.Clue.Files.File.Close();
                    //                investigation.Investigations.Investigation.Files.List();
                    //            } else {
                    //                $.showModalMessageBox("上传失败.");
                    //            }
                    //        }
                    //    });
                    //},
                    View: function (officialDocumentFileId, investigationGuid, investigationFileName) {

                        if (investigationFileId == '' || investigationFileName == '') {
                            $.showModalMessageBox("无线索文件.");
                            return false;
                        }

                        var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                        var picfiles = new Array('jpg', 'tif', 'pdf');
                        var extName = investigationFileName.substring(investigationFileName.lastIndexOf('.') + 1, investigationFileName.length);

                        if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                            var path = GV_LS.OfficeOnlineUrl + GV_LS.OnlineUrl + "CaseFiles/CIT/InvestigationCule/" + investigationGuid + "/" + investigationFileName;

                            window.open(path);
                        }
                        else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                            var path = GV_LS.OnlineUrl + "CaseFiles/CIT/InvestigationClueFiles/" + investigationGuid + "/" + investigationFileName;
                            window.open(path);
                        } else {
                            investigation.Investigations.Investigation.Clues.Clue.Files.File.Download(investigationFileId);
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
        },
    },
};
var contract = {
    Contracts: {
        List: function () {
            var data = {};
            var url = AP_ROOT + AP_PAGE_ID + "/FCM/Contract/ContractSelectedList";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#contractListModal').modal({ backdrop: 'static', keyboard: false });
                $('#contractListModal').on('hidden.bs.modal', function () {
                    $("#contractListModal").remove();
                });
                $(document).ready(function () {
                    contract.Contracts.ContractSelectedList();
                });
            });
        },
        ContractSelectedList: function () {
            $("#contractListForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/Contract/List", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.ContractList, function (i, c) {
                            $("tbody", "#tblContractList").addRow(
                                "<span class='contractId' style='display:none'>" + c.ContractBasicInfo.ContractId + "</span>"
                                + "<span class='contractStatus' style='display:none'>" + c.ContractBasicInfo.ContractStatus + "</span>"
                                + "<a style='color: #039' href='javascript:void(0);' "
                                + " onclick = 'javascript:contract.Contracts.Contract.Selected(\"" + c.ContractBasicInfo.ContractNo + "\",\"" + c.ContractBasicInfo.CustomerNo + "\",\"" + c.ContractBasicInfo.CustomerName + "\")' > "
                                + c.ContractBasicInfo.ContractNo + "</a>",
                                c.ContractBasicInfo.ContractName,
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.CoordinatorName,
                                c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate))
                            );
                        });

                        $("tfoot", "#tblContractList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.contractlist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: contract.Contracts.ContractSelectedList,
                            callBackArgs: null
                        });

                    } else {

                        $("tfoot", "#tblContractList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        Contract: {
            Selected: function (contractNo,customerNo,customeName) {
                contract.Contracts.Contract.ContractNo.AddIn(contractNo);
                $("#OfficialDocument_Basic_CustomerNo").val(customerNo);
                $("#OfficialDocument_Basic_CustomerName").val(customeName);
                $('#contractListModal').modal('hide');
            },
            ContractNo: {
                AddIn: function (contractNo) {

                    var existsContractNo = false;

                    if ($("a[name='contractno']").length > 0) {
                        return false;
                    }

                    $("a[name='contractno']").each(function () {
                        if ($(this).attr("contractno") == contractno) {
                            existsContractNo = true;
                            return true;
                        }
                    });

                    if (existsContractNo) return true;

                    var $tag = $("<span class='tag label label-info'>"
                        + "<a name='contractno' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                        + " contractno='" + contractNo + "'"
                        + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);'   data-original-title=" + contractNo + " '>" + contractNo + "</a>"
                        + "<span class='contractremove' data-role='remove'></span>"
                        + "</span>");

                    $("#OfficialDocument_ContractNo_Input").before($tag);
                    $tag.after(' ');

                },
                Remove: function (e) {
                    $(e).parent().remove();
                },
                Clear: function () {
                    $("#OfficialDocument_ContractNo_Input").parent().find("span").remove();
                }
            },
        }
    }
};
var c = {
    Cases: {
        List: function () {
            var data = {};
            var url = AP_ROOT + AP_PAGE_ID + "/Legal/CaseList/SelectedList";
            $.openLoading();
            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#caseListModal').modal({ backdrop: 'static', keyboard: false });
                $('#caseListModal').on('hidden.bs.modal', function () {
                    $("#caseListModal").remove();
                });
                $(document).ready(function () {
                    c.Cases.CaseSelectedList();
                });
            });
        },
        CaseSelectedList: function () {
            $("#caseListForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseList/CaseSearchList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblCaseList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.CaseList, function (i, c) {
                            $("tbody", "#tblCaseList").addRow(
                                  "<span class='caseId' style='display:none'>" + c.Basic.CaseId + "</span>"
                                + "<a style='color: #039' href='javascript:void(0);' "
                                + " onclick = 'javascript:c.Cases.Case.Selected(\"" + c.Basic.CaseNo + "\",\"" + c.Basic.ContractNo  + "\",\"" + c.Basic.CustomerNo + "\",\"" + c.Basic.CustomerName + "\")' > "
                                + c.Basic.CaseNo + "</a>",
                                c.Basic.CasePhaseName,
                                c.Basic.AppellantNames,
                                c.Basic.AppelleeNames,
                                c.Basic.CourtLawyerName,
                                c.Basic.CaseLawyerName,
                                c.Basic.CaseAssistantName
                            );
                        });

                        $("tfoot", "#tblCaseList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.caselist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: c.Cases.CaseSelectedList,
                            callBackArgs: null
                        });

                    } else {

                        $("tfoot", "#tblCaseList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        Case: {
            Selected: function (caseNo, contractNo, customerNo, customeName) {
                c.Cases.Case.CaseNo.AddIn(caseNo);
                $("#OfficialDocument_Basic_ContractNo").val(contractNo);
                $("#OfficialDocument_Basic_CustomerNo").val(customerNo);
                $("#OfficialDocument_Basic_CustomerName").val(customeName);
                $('#caseListModal').modal('hide');
            },
            CaseNo: {
                AddIn: function (caseNo) {

                    var existscaseno = false;

                    if ($("a[name='caseno']").length > 0) {
                        return false;
                    }

                    $("a[name='caseno']").each(function () {
                        if ($(this).attr("caseno") == caseno) {
                            existscaseno = true;
                            return true;
                        }
                    });

                    if (existscaseno) return true;

                    var $tag = $("<span class='tag label label-info'>"
                        + "<a name='caseno' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                        + " caseno='" + caseNo + "'"
                        + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);'   data-original-title=" + caseNo + " '>" + caseNo + "</a>"
                        + "<span class='caseremove' data-role='remove'></span>"
                        + "</span>");

                    $("#OfficialDocument_CaseNo_Input").before($tag);
                    $tag.after(' ');

                },
                Remove: function (e) {
                    $(e).parent().remove();
                },
                Clear: function () {
                    $("#OfficialDocument_CaseNo_Input").parent().find("span").remove();
                }
            },
        }
    }
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
        //officialDocument.OfficialDocuments.OfficialDocument.Edit();
    });

    $(document).off('click', '#btnOfficialDocumentToAudit').on('click', '#btnOfficialDocumentToAudit', function () {
        officialDocument.OfficialDocuments.OfficialDocument.CreateUpdate(true);
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
        officialDocument.OfficialDocuments.Print(officialDocumentNos);
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
        c.Cases.List();
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
    
    
});