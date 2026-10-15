/*案件批量处理*/

var caseInfo =
{
    View: function (caseId, caseNo) {

        var search = {};

        search.CaseId = caseId;
        search.PageId = "1001001010";
        search.PageNo = 1;
        search.PageSize = 100;
        search.PageName = "案件查看";
        search.Keyword = caseNo;

        var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CreateUpdate?typeId=1&caseId=" + caseId + "&k=" + escape(JSON.stringify(search));

        window.open(url);
    },

    Multiple: {

        AFM:{
            AddIn: function() {
                var caseIds = $.checkbox.vals("chkCaseId");
                if (caseIds.length == 0) {
                    $.showModalMessageBox("请勾选需要年费监控的案件.");
                    return;
                }

                var dataIsOk = true;
                $("input[name='chkCaseId']:checked").each(
                    function () {
                        if ($(this).attr("caserequestdate") == '') {
                            $.showModalMessageBox("案号:" + $(this).attr("caseno") + "无申请日,无法监控.");
                            dataIsOk = false;
                            return false;
                        }
                    }
                );

                if (!dataIsOk) return false;

                var data = { caseIds: caseIds };
                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseAddInAFM", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("所选案件已加入年费监控.");
                        //caseInfo.CaseFee.List();
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
                
            },

            Remove: function () {
                var caseIds = $.checkbox.vals("chkCaseId");
                if (caseIds.length == 0) {
                    $.showModalMessageBox("请勾选需要放弃年费监控的案件.");
                    return;
                }
                var data = { caseIds: caseIds };
                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseRemoveAFM", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("所选案件已放弃年费监控.");
                        caseQuery.List();
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });

            },
        },

        Edit: {
            /*批量案件基本信息*/
            Open: function () {
                var caseIds = $.checkbox.vals("chkCaseId");
                if (caseIds.length == 0) {
                    $.showModalMessageBox("请选择需要修改的案件.");
                    return false;
                }

                var data =
                {
                    caseIds: caseIds
                };

                var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseBatchEdit";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#caseBatchEditModal').modal({ backdrop: 'static', keyboard: false });
                    $('#caseBatchEditModal').on('hidden.bs.modal', function () {
                        $("#caseBatchEditModal").remove();
                    });
                });
            },

            /*批量修改*/
            Create: function () {

                if ($("#caseIdList").val().split(',').length > 1 && $("#CaseNo").val() != '') {
                    $.showModalMessageBox("不允许同时修改多个案件为同一案件编号.");
                    return false;
                }

                $.openLoading();
                $('#caseBatchEdit').ajaxSubmit({
                    success: function (response) {
                        $.closeLoading();
                        if (response.IsSuccess) {
                            $.showModalMessageBox("批量修改成功.");
                            $('#caseBatchEdit').modal('hide');
                            caseQuery.List();
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    }
                });
            },

            /*关闭*/
            Close: function () {
                $('#caseBatchEditModal').modal('hide');
            },
        },

        AnnualYearEdit: {
             
            Open: function () {
                var caseIds = $.checkbox.vals("chkCaseId");
                if (caseIds.length == 0) {
                    $.showModalMessageBox("请选择需要修改的案件.");
                    return false;
                }

                var data =
                {
                    caseIds: caseIds,
                };

                var url = AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseAnnualYearEdit";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#caseAnnualYearEditModal').modal({ backdrop: 'static', keyboard: false });
                    $('#caseAnnualYearEditModal').on('hidden.bs.modal', function () {
                        $("#caseAnnualYearEditModal").remove();
                    });
                });
            },

           
            Create: function () {

                var caseIds = $.checkbox.vals("chkCaseId");
                if (caseIds.length == 0) {
                    $.showModalMessageBox("请选择需要修改的案件.");
                    return false;
                }

                if ($("#CostSlowRate").val() == "" || $("#AnnualYear").val() == "") {
                    $.showModalMessageBox("请选择首年年度或减缓比例.");
                    return false;
                }
                
                var data =
                {
                    caseIds: caseIds,
                    firstAnnualYear: $("#FirstAnnualYear").val(),
                    costSlowRate: $("#CostSlowRate").val()
                };

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseAnnualYearEditCreate", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("设置成功.");
                        caseInfo.Multiple.AnnualYearEdit.Close();
                        //caseQuery.List();
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },

          
            Close: function () {
                $('#caseAnnualYearEditModal').modal('hide');
            },
        },

        Import: {

            /*批量导入open*/
            Open: function () {
                var caseIds = $.checkbox.vals("chkCaseId");
                if (caseIds.length == 0) {
                    $.showModalMessageBox("请选择需要导入文件的案件.");
                    return false;
                }

                var data =
                {
                    caseIds: caseIds
                };

                var url =  AP_ROOT + AP_PAGE_ID + "/IPR/CaseFile/CaseFileBatchImport";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#caseFileBatchImportModal').modal({ backdrop: 'static', keyboard: false });
                    $('#caseFileBatchImportModal').on('hidden.bs.modal', function () {
                        $("#caseFileBatchImportModal").remove();
                    });

                    var caseFileType = new AssociateCaseFileType(
                        $("#div_CaseFileTypeList"),
                        $("#CaseFileTypeId"),
                        $("#CaseFileTypeName"),
                        null,
                        false,
                        null
                    );
                });
            },

            /*批量导入关闭*/
            Close: function () {
                $('#caseFileBatchImportModal').modal('hide');
            },

            /*批量导入*/
            Create: function () {
                $.openLoading();
                $('#caseFileBatchImportProcess').ajaxSubmit({
                    success: function (response) {
                        $.closeLoading();
                        if (response.IsSuccess) {
                            $.showModalMessageBox("批量导入成功.");
                            $('#caseFileBatchImportModal').modal('hide');
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    }
                });
            },
        },

        Transfer: {

            Open: function () {

                var caseIds = $.checkbox.vals("chkCaseId");
                if (caseIds.length == 0) {
                    $.showModalMessageBox("请选择转文的案件.");
                    return;
                }

                var customerIds = new Array();

                $("input[name='chkCaseId']:checked").each(
                    function () {
                        if ($.inArray($(this).attr("customerid"), customerIds) > -1) {
                        } else {
                            customerIds.push($(this).attr("customerid"));
                        }
                    }
                );
                if (customerIds.length > 1) {
                    $.showModalMessageBox("客户不一致,不允许转文.");
                    return false;
                }

                var data = {
                    customerId: customerIds[0],
                    caseIds: caseIds,
                }

                var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseListExportToWord";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#caseToWordModal').modal({ backdrop: 'static', keyboard: false });
                    $('#caseToWordModal').on('hidden.bs.modal', function () {
                        $("#caseToWordModal").remove();
                    });

                    var caseFileType = new AssociateCaseFileType(
                     $("#div_CaseFileTypeList"),
                     $("#CaseFileTypeId"),
                     $("#CaseFileTypeName"),
                     null,
                     $("#IsTransformedFile").val() == 'true',
                     null
                    );
                });

                //$('.casetoword').load(url, data, function (result) {
                //    $.closeLoading();
                //    $('#caseToWordModal').modal('toggle');
                //});
            },

            /*关闭客户*/
            Close: function () {
                $('#caseToWordModal').modal('hide');
            },

            Export: function () {
                var caseIds = $.checkbox.vals("chkCaseId");
                if (caseIds.length == 0) {
                    $.showModalMessageBox("请选择导出的案件.");
                    return false;
                }
                if ($("#hidCaseFileTypeId").val() == '') {
                    $.showModalMessageBox("请选择转文文档.");
                    return false;
                }

                var data = {
                    customerId: $("#CustomerId").val(),
                    caseFileTypeId: $("#CaseFileTypeId").val(),
                    caseIds: caseIds,
                }

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/ExportCaseListToWord", data, function (response) {
                    if (response.IsSuccess) {
                        var customerId = response.Data.split('|')[0];
                        var fileName = response.Data.split('|')[1];
                        window.open( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseExportFileDownload?customerId=" + customerId + "&fileName=" + fileName);
                        $.showModalMessageBox("导出成功.");
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });

                return true;
            },

            Upload: function () {

                if ($("#CaseFileType").val() == '') {
                    $.showModalMessageBox("请选择文件类型.");
                    return false;
                }

                if ($("#flFile").val() == "") {
                    $.showModalMessageBox("请选择文档文件.");
                    return false;
                }

                $.openLoading();
                $('#uploadingForm').ajaxSubmit({
                    success: function (response) {
                        $.closeLoading();
                        if (response.IsSuccess) {
                            $.showModalMessageBox("上传成功.");
                            $('#caseToWordModal').modal('hide');
                            return false;
                        } else {
                            $.showModalMessageBox(response.Message);
                            return false;
                        }
                    }
                });
            },


            ProcessFileTypeSelectedCallBack: function (caseFileTypeId, caseFileTypeNameText, hedgingFileTypeId) {
                $(".spanreferencedate").text(caseFileTypeNameText + "日期");

                if (caseFileTypeId == '8'
                    || caseFileTypeId == '38'
                    || caseFileTypeId == '126'
                    || caseFileTypeId == '127'
                    || caseFileTypeId == '157') {
                    //$(".spanreferencedate").text("申请日期");
                    if (caseFileTypeId == '8') {
                        $(".caserequestno").css("display", 'block');
                    }
                } else if (caseFileTypeId == '253'
                    || caseFileTypeId == '239'
                    || caseFileTypeId == '249'
                    || caseFileTypeId == '42'
                   ) {
                    //$(".spanreferencedate").text("授权日期");
                } else {
                    // $(".spanreferencedate").text("参考日期");
                }

                $(".caseHedgingFile").css("display", 'none');
                $("#HedgingFileId").empty();

                if (hedgingFileTypeId != '') {

                    var data = {
                        caseId: parseInt($("#CaseId").val()),
                        caseFileTypeId: caseFileTypeId
                    };

                    $.ajaxSetup({
                        async: false
                    });

                    $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/GetHedgingFileList", data, function (response) {
                        if (response.IsSuccess) {
                            if (response.Data.length > 0) {
                                $(".caseHedgingFile").css("display", 'block');
                                $.each(response.Data, function (i, c) {
                                    if (i == 0) {
                                        $("#HedgingFileId").append("<option selected value='" + c.FileId + "'>" + c.FileTypeId + c.FileTypeName + "</option>");
                                    } else {
                                        $("#HedgingFileId").append("<option value='" + c.FileId + "'>" + c.FileTypeId + c.FileTypeName + "</option>");
                                    }
                                });
                            } else {
                                $("#HedgingFileId").append("<option selected value=''>" + "无" + "</option>");
                            }
                        } else {
                            $("#HedgingFileId").append("<option selected value=''>" + "无" + "</option>");
                        }
                    });
                    $.ajaxSetup({
                        async: true
                    });

                } else {
                    $("#HedgingFileId").append("<option selected value='" + -1 + "'>" + "无" + "</option>");
                }
            },
        },

        TransmitFile: {

            Open: function (caseFileTypeId) {

                var caseFileIds = $.checkbox.vals("chkCaseFileId");
                if (caseFileIds.length == 0) {
                    $.showModalMessageBox("请选择待转官文.");
                    return;
                }

                var caseIds = new Array();

                $("input[name='chkCaseFileId']:checked").each(
                      function () {
                          caseIds.push($(this).attr("caseid"));
                      }
                  );

                var customerIds = new Array();

                $("input[name='chkCaseFileId']:checked").each(
                    function () {
                        if ($.inArray($(this).attr("customerid"), customerIds) > -1) {
                        } else {
                            customerIds.push($(this).attr("customerid"));
                        }
                    }
                );
                if (customerIds.length > 1) {
                    $.showModalMessageBox("客户不一致,不允许转文.");
                    return false;
                }

                var data = {
                    customerId: customerIds[0],
                    caseFileIds: caseFileIds,
                    caseIds : caseIds,
                    caseFileTypeId: caseFileTypeId
                }

                var url =  AP_ROOT + AP_PAGE_ID + "/IPR/CaseFile/TransmitCaseFile";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#transmitCaseFileModal').modal({ backdrop: 'static', keyboard: false });
                    $('#transmitCaseFileModal').on('hidden.bs.modal', function () {
                        $("#transmitCaseFileModal").remove();
                    });
                });
            },

            Close: function () {
                $('#transmitCaseFileModal').modal('hide');
            },

            Transmit: function () {
                var caseFileIds = $.checkbox.vals("chkCaseFileId");
                if (caseFileIds.length == 0) {
                    $.showModalMessageBox("请选择待转官文.");
                    return false;
                }
                if ($("#hidCaseFileTypeId").val() == '') {
                    $.showModalMessageBox("请选择转文文档.");
                    return false;
                }

                var caseIds = new Array();

                $("input[name='chkCaseFileId']:checked").each(
                      function () {
                          caseIds.push($(this).attr("caseid"));
                      }
                  );
 
                var data = {
                    customerId: $("#CustomerId").val(),
                    caseFileTypeId: $("#CaseFileTypeId").val(),
                    caseIds: caseIds,
                    caseFileIds: caseFileIds

                }

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFile/Transmit", data, function (response) {
                    if (response.IsSuccess) {
                        var customerId = response.Data.split('|')[0];
                        var fileName = response.Data.split('|')[1];
                        window.open( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseExportFileDownload?customerId=" + customerId + "&fileName=" + fileName);
                        $.showModalMessageBox("导出成功.");
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });

                return true;
            },

            Upload: function () {

                if ($("#CaseFileType").val() == '') {
                    $.showModalMessageBox("请选择文件类型.");
                    return false;
                }

                if ($("#flFile").val() == "") {
                    $.showModalMessageBox("请选择文档文件.");
                    return false;
                }

                $.openLoading();
                $('#uploadingForm').ajaxSubmit({
                    success: function (response) {
                        $.closeLoading();
                        if (response.IsSuccess) {
                            $.showModalMessageBox("上传成功.");
                            $('#caseToWordModal').modal('hide');
                            caseFileSearch.List();
                            return false;
                        } else {
                            $.showModalMessageBox(response.Message);
                            return false;
                        }
                    }
                });
            },

            TagTransformed: function () {
                var data = {
                    caseFileIds: $.checkbox.vals("chkCaseFileId")
                };

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/TagTransformed", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("处理成功.");
                        caseFileSearch.List();
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },

            ProcessFileTypeSelectedCallBack: function (caseFileTypeId, caseFileTypeNameText, hedgingFileTypeId) {
                $(".spanreferencedate").text(caseFileTypeNameText + "日期");

                if (caseFileTypeId == '8'
                    || caseFileTypeId == '38'
                    || caseFileTypeId == '126'
                    || caseFileTypeId == '127'
                    || caseFileTypeId == '157') {
                    //$(".spanreferencedate").text("申请日期");
                    if (caseFileTypeId == '8') {
                        $(".caserequestno").css("display", 'block');
                    }
                } else if (caseFileTypeId == '253'
                    || caseFileTypeId == '239'
                    || caseFileTypeId == '249'
                    || caseFileTypeId == '42'
                   ) {
                    //$(".spanreferencedate").text("授权日期");
                } else {
                    // $(".spanreferencedate").text("参考日期");
                }

                $(".caseHedgingFile").css("display", 'none');
                $("#HedgingFileId").empty();

                if (hedgingFileTypeId != '') {

                    var data = {
                        caseId: parseInt($("#CaseId").val()),
                        caseFileTypeId: caseFileTypeId
                    };

                    $.ajaxSetup({
                        async: false
                    });

                    $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/GetHedgingFileList", data, function (response) {
                        if (response.IsSuccess) {
                            if (response.Data.length > 0) {
                                $(".caseHedgingFile").css("display", 'block');
                                $.each(response.Data, function (i, c) {
                                    if (i == 0) {
                                        $("#HedgingFileId").append("<option selected value='" + c.FileId + "'>" + c.FileTypeId + c.FileTypeName + "</option>");
                                    } else {
                                        $("#HedgingFileId").append("<option value='" + c.FileId + "'>" + c.FileTypeId + c.FileTypeName + "</option>");
                                    }
                                });
                            } else {
                                $("#HedgingFileId").append("<option selected value=''>" + "无" + "</option>");
                            }
                        } else {
                            $("#HedgingFileId").append("<option selected value=''>" + "无" + "</option>");
                        }
                    });
                    $.ajaxSetup({
                        async: true
                    });

                } else {
                    $("#HedgingFileId").append("<option selected value='" + -1 + "'>" + "无" + "</option>");
                }
            },
        },

        TransmitFeeFile: {

            Open: function (caseFileTypeId) {

                var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
                if (caseFeeIds.length == 0) {
                    $.showModalMessageBox("请选择通知的费用.");
                    return;
                }

                var customerIds = new Array();

                $("input[name='chkCaseFeeId']:checked").each(
                    function () {
                        if ($.inArray($(this).attr("customerid"), customerIds) > -1) {
                        } else {
                            customerIds.push($(this).attr("customerid"));
                        }
                    }
                );
                if (customerIds.length > 1) {
                    $.showModalMessageBox("客户不一致,不允许转票.");
                    return false;
                }

                var caseIds = new Array();

                $("input[name='chkCaseFeeId']:checked").each(
                      function () {
                          caseIds.push($(this).attr("caseid"));
                      }
                  );

                var data = {
                    customerId: customerIds[0],
                    caseFeeIds: caseFeeIds,
                    caseIds : caseIds,
                    caseFileTypeId: caseFileTypeId
                }

                var url =  AP_ROOT + AP_PAGE_ID + "/IPR/CaseFile/TransmitCaseFeeFile";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#transmitCaseFeeFileModal').modal({ backdrop: 'static', keyboard: false });
                    $('#transmitCaseFeeFileModal').on('hidden.bs.modal', function () {
                        $("#transmitCaseFeeFileModal").remove();
                    });
                });
            },

            Close: function () {
                $('#transmitCaseFeeFileModal').modal('hide');
            },

            Transmit: function () {
                var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
                if (caseFeeIds.length == 0) {
                    $.showModalMessageBox("请选择待转票.");
                    return false;
                }
                if ($("#hidCaseFileTypeId").val() == '') {
                    $.showModalMessageBox("请选择转文文档.");
                    return false;
                }

                var caseIds = new Array();

                $("input[name='chkCaseFeeId']:checked").each(
                      function () {
                          caseIds.push($(this).attr("caseid"));
                      }
                  );

                var data = {
                    customerId: $("#CustomerId").val(),
                    caseFileTypeId: $("#CaseFileTypeId").val(),
                    caseIds: caseIds,
                    caseFeeIds: caseFeeIds
                }

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFile/Inform", data, function (response) {
                    if (response.IsSuccess) {
                        var customerId = response.Data.split('|')[0];
                        var fileName = response.Data.split('|')[1];
                        window.open( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseExportFileDownload?customerId=" + customerId + "&fileName=" + fileName);
                        $.showModalMessageBox("导出成功.");
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });

                return true;
            },

            Upload: function () {

                if ($("#CaseFileType").val() == '') {
                    $.showModalMessageBox("请选择文件类型.");
                    return false;
                }

                if ($("#flFile").val() == "") {
                    $.showModalMessageBox("请选择文档文件.");
                    return false;
                }

                $.openLoading();
                $('#uploadingForm').ajaxSubmit({
                    success: function (response) {
                        $.closeLoading();
                        if (response.IsSuccess) {
                            $.showModalMessageBox("上传成功.");
                            $('#caseToWordModal').modal('hide');
                            
                            caseFeeSearch.List();

                            return false;
                        } else {
                            $.showModalMessageBox(response.Message);
                            return false;
                        }
                    }
                });
            },

            RemoveFeeHedgingFile: function () {

                var data = {
                    caseFeeIds: $.checkbox.vals("chkCaseFeeId")
                };

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/ARCaseFee/RemoveFeeHedgingFile", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("处理成功.");
                        caseFeeFileSearch.List();
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },
         },

        TransmitFeeInvoiceFile: {

            Open: function (caseFileTypeId) {

                var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
                if (caseFeeIds.length == 0) {
                    $.showModalMessageBox("请选择费用发票.");
                    return;
                }

                var customerIds = new Array();

                $("input[name='chkCaseFeeId']:checked").each(
                    function () {
                        if ($.inArray($(this).attr("customerid"), customerIds) > -1) {
                        } else {
                            customerIds.push($(this).attr("customerid"));
                        }
                    }
                );
                if (customerIds.length > 1) {
                    $.showModalMessageBox("客户不一致,不允许转票.");
                    return false;
                }

                var caseIds = new Array();

                $("input[name='chkCaseFeeId']:checked").each(
                      function () {
                          caseIds.push($(this).attr("caseid"));
                      }
                  );

                var data = {
                    customerId: customerIds[0],
                    caseFeeIds: caseFeeIds,
                    caseIds: caseIds,
                    caseFileTypeId: caseFileTypeId
                }

                var url = AP_ROOT + AP_PAGE_ID + "/IPR/CaseFile/TransmitCaseFeeInvoiceFile";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#transmitCaseFeeInvoiceFileModal').modal({ backdrop: 'static', keyboard: false });
                    $('#transmitCaseFeeInvoiceFileModal').on('hidden.bs.modal', function () {
                        $("#transmitCaseFeeInvoiceFileModal").remove();
                    });
                });
            },

            Close: function () {
                $('#transmitCaseFeeInvoiceFileModal').modal('hide');
            },

            Transmit: function () {
                var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
                if (caseFeeIds.length == 0) {
                    $.showModalMessageBox("请选择票据文件.");
                    return false;
                }
                if ($("#hidCaseFileTypeId").val() == '') {
                    $.showModalMessageBox("请选择转文文档.");
                    return false;
                }

                var caseIds = new Array();

                $("input[name='chkCaseFeeId']:checked").each(
                      function () {
                          caseIds.push($(this).attr("caseid"));
                      }
                  );

                var data = {
                    customerId: $("#CustomerId").val(),
                    caseFileTypeId: $("#CaseFileTypeId").val(),
                    caseIds: caseIds,
                    caseFeeIds: caseFeeIds
                }

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/CaseFile/TransmitInvoiceFile", data, function (response) {
                    if (response.IsSuccess) {
                        var customerId = response.Data.split('|')[0];
                        var fileName = response.Data.split('|')[1];
                        window.open(AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseExportFileDownload?customerId=" + customerId + "&fileName=" + fileName);
                        $.showModalMessageBox("导出成功.");
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });

                return true;
            },

            Upload: function () {

                if ($("#CaseFileType").val() == '') {
                    $.showModalMessageBox("请选择文件类型.");
                    return false;
                }

                if ($("#flFile").val() == "") {
                    $.showModalMessageBox("请选择文档文件.");
                    return false;
                }

                $.openLoading();
                $('#uploadingForm').ajaxSubmit({
                    success: function (response) {
                        $.closeLoading();
                        if (response.IsSuccess) {
                            $.showModalMessageBox("上传成功.");
                            $('#caseToWordModal').modal('hide');
                            caseFeeFileSearch.List();

                            return false;
                        } else {
                            $.showModalMessageBox(response.Message);
                            return false;
                        }
                    }
                });
            },

            RemoveFeeHedgingFile: function () {

                var data = {
                    caseFeeIds: $.checkbox.vals("chkCaseFeeId")
                };

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/ARCaseFee/RemoveFeeHedgingFile", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("处理成功.");
                        caseFeeFileSearch.List();
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },
        },

        Task: {
            Finished: function ()
            {
                var caseIds = $.checkbox.vals("chkCaseId");
                if (caseIds.length == 0) {
                    $.showModalMessageBox("请选择案件.");
                    return;
                }

                var data = { caseIds: caseIds };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/CaseTask/Finished", data, function (response) {
                    if (response.IsSuccess) {
                        caseQuery.List();
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            }
        },

        Event:
        {
            Open: function () {

                var caseIds = $.checkbox.vals("chkCaseId");
                if (caseIds.length == 0) {
                    $.showModalMessageBox("请选择案件.");
                    return;
                }

                var data = { caseIds: caseIds };

                var url = AP_ROOT + AP_PAGE_ID + "/IPR/CaseEvent/CaseEvent";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#caseEventModal').modal({ backdrop: 'static', keyboard: false });
                    $('#caseEventModal').on('hidden.bs.modal', function () {
                        $("#caseEventModal").remove();
                    });
                });
            },

            CreateUpdate: function () {

                var caseIds = $.checkbox.vals("chkCaseId");
                if (caseIds.length == 0) {
                    $.showModalMessageBox("请选择案件.");
                    return;
                }

                if ($("#EventTime").val() == '') {
                    $.showModalMessageBox("请输入提醒日期.");
                    return false;
                }

                if ($("#EventContent").val() == '') {
                    $.showModalMessageBox("请输入提醒内容.");
                    return false;
                }

                var data = {
                    caseIds: caseIds,
                    eventTime : $("#EventTime").val(),
                    eventContent: $("#EventContent").val()
                }

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/CaseEvent/CaseEventCreate", data,function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("新增成功.");
                        $('#caseEventModal').modal('hide');
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },

            Remove:function()
            {
                var caseIds = $.checkbox.vals("chkCaseId");
                if (caseIds.length == 0) {
                    $.showModalMessageBox("请选择案件.");
                    return;
                }

                $.showModalConfirmDialog("确定要删除选中案件自定义提醒?", 'caseInfo.Multiple.Event.RemoveCallBack', true, true);
            },

            RemoveCallBack: function () {

                var caseIds = $.checkbox.vals("chkCaseId");
                var data = {
                    caseIds: caseIds
                 }

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/CaseEvent/CaseEventRemove", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("删除成功.");
                        $('#caseEventModal').modal('hide');
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },

            Close: function () {
                $('#caseEventModal').modal('hide');
            },
        }
     }
};


var caseFileSearch = {
    View: function (e) {

        var caseFileId = $(e).attr("fileId");
        if (caseFileId == '') {
            $.showModalMessageBox("请选择查看的文件.");
            return false;
        }

        var caseFileName = $(e).attr("fileName");
        if (caseFileName == '') {
            $.showModalMessageBox("无文件.");
            return false;
        }

        var caseno = $(e).attr("caseno");

        var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
        var picfiles = new Array('jpg', 'tif', 'pdf');
        var extName = caseFileName.substring(caseFileName.lastIndexOf('.') + 1, caseFileName.length);

        if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
            var path = GV_IPR.OfficeOnlineUrl + GV_IPR.IPROnlineUrl + "CaseFiles/" + caseno + "/" + caseFileName;
            window.open(path);
        }
        else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
            var path = GV_IPR.IPROnlineUrl + "CaseFiles/" + caseno + "/" + caseFileName;
            window.open(path);
        } else {
            caseFileSearch.Download(caseFileId);
        }

        return true;
    },

    Download: function (caseFileId) {
        window.open( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseFileDownload?caseFileId=" + caseFileId);
        return true;
    },

    List: function () {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/CasePatentOfficeFile/CaseFileSearchList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseFileList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.CaseFileList, function (i, c) {
                        var caseRequestDate = c.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseRequestDate));
                        var fileTypeName = $.caseFileType.getCaseFileTypeNameById(c.FileTypeId);
                        var filePath = c.CaseNo + "/" + c.FileName;

                        $("tbody", "#tblCaseFileList").addRow(
                            "<input type='checkbox' id='chkCaseFileId' name='chkCaseFileId' class='ng-pristine ng-valid' customerid=" + c.CustomerId + " caseno=" + c.CaseNo + " caseid=" + c.CaseId +  " value=" + c.FileId + " caserequestdate=" + caseRequestDate + ">",
                            c.IsTransmitted == true ? "已转" : "未转",
                            fileTypeName,
                            "<a  id='fileId' fileId=" + c.FileId + " caseno=" + c.CaseNo + " href='javascript:void(0)' fileName=" + c.FileName + " onclick=\"javascript:caseFileSearch.View(this)\"> " + c.FileName + "</a> ",
                            c.UploadingTime == null ? '' : getDate(convertJsonDateToJSDate(c.UploadingTime)),
                            "<a href='javascript:void(0)' onclick=\"javascript:caseInfo.View(" + c.CaseId + ",'" + c.CaseNo + "')\"> " + c.CaseNo + "</a>",
                            c.CaseRequestNo,
                            c.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseRequestDate)),
                            c.CustomerName,
                            c.CaseName
                            );
                    });

                    $("tfoot", "#tblCaseFileList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.caseFileList").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: caseFileSearch.List,
                        callBackArgs: null
                    });
                    caseFileSearch.BindMenu();
                } else {
                    $("tfoot", "#tblCaseFileList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    BindMenu: function () {
        $('div.gridSection').contextMenu('menu', {
            menuStyle: {
                width: '252px'
            },

            itemStyle: {
                width: '250px'
            },

            bindings: {

                /*转文*/
                'transmit': function (t, e) {
                    var caseFileTypeId = $(e).attr("fileTypeId");
                    caseInfo.Multiple.TransmitFile.Open(caseFileTypeId);
                },

                /*标记已转*/
                'transmitTag': function (t, e) {
                    caseInfo.Multiple.TransmitFile.TagTransformed();
                },
            },
            onContextMenu: function (e) {
                return true;
            },
            onShowMenu: function (e, menu) {
                return menu;
            }
        });
    },

    ExportToExcel: function () {

        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/CaseList/CaseListExportToExcel", function (response) {
            if (response.IsSuccess) {
                window.open( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseListExportToExcelDownload?fileName=" + response.Data);
                $.showModalMessageBox("导出成功.");
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    Reset: function () {
        $("#postForm :text").each(function () {
            $(this).val('');
        });
        $("#postForm :hidden").each(function () {
            $(this).val('');
        });

        $("#SearchCondition_SearchByMonthAndDay").attr("checked", false);
    },

    Selected: function (e) {

        if ($(e).prop("checked") == true) {
            $.checkbox.all("chkCaseFileId");
        } else {
            $.checkbox.not("chkCaseFileId");
        }
    },

}

var caseFeeFileSearch = {

    View: function (e) {

        var caseFeeId = $(e).attr("caseFeeId");
        if (caseFeeId == '') {
            $.showModalMessageBox("请选择查看的票据文件.");
            return false;
        }

        var caseFileName = $(e).attr("fileName");
        if (caseFileName == '') {
            $.showModalMessageBox("无票据文件.");
            return false;
        }

        var caseno = $(e).attr("caseno");

        var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
        var picfiles = new Array('jpg', 'tif', 'pdf');
        var extName = caseFileName.substring(caseFileName.lastIndexOf('.') + 1, caseFileName.length);

        if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
            var path = GV_IPR.OfficeOnlineUrl + GV_IPR.IPROnlineUrl + "CaseFeeFiles/" + caseno + "/" + caseFileName;
            window.open(path);
        }
        else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
            var path = GV_IPR.IPROnlineUrl + "CaseFeeFiles/" + caseno + "/" + caseFileName;
            window.open(path);
        } else {
            caseFeeFileSearch.Download(caseFeeId);
        }
    },

    Download: function (caseFeeId) {
        window.open( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseFeeFileDownload?caseFeeId=" + caseFeeId);
        return true;
    },

    List: function () {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/CasePatentOfficeInvoiceFile/CaseFeeFileSearchList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseFeeList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    
                    $.each(response.Data.CaseFeeList, function (i, c) {
                        var caseRequestDate = c.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseRequestDate));
                        var feeTypeName = $.caseFeeType.getCaseFeeTypeNameById(c.CaseFeeTypeId);
                        var filePath = c.CaseNo + "/" + c.InvoiceFile.InvoiceFileName;

                        $("tbody", "#tblCaseFeeList").addRow(
                            "<input type='checkbox' id='chkCaseFeeId' name='chkCaseFeeId' class='ng-pristine ng-valid' customerid=" + c.CustomerId + " caseno=" + c.CaseNo + " caseid=" + c.CaseId + " value=" + c.CaseFeeId + " caserequestdate=" + caseRequestDate  +">",
                            c.HasHedgingFile == true ? "已转" : "未转",
                            feeTypeName,
                            c.Amount,
                            c.InvoiceFile.InvoiceNo,
                            "<a  id='caseFeeId' caseFeeId=" + c.CaseFeeId + " caseno=" + c.CaseNo + " href='javascript:void(0)' fileName=" + c.InvoiceFile.InvoiceFileName + " onclick=\"javascript:caseFeeFileSearch.View(this)\"> " + c.InvoiceFile.InvoiceFileName + "</a> ",
                            c.InformDate == null ? '' : getDate(convertJsonDateToJSDate(c.InformDate)),
                            "<a href='javascript:void(0)' onclick=\"javascript:caseInfo.View(" + c.CaseId + ",'" + c.CaseNo + "')\"> " + c.CaseNo + "</a>",
                            c.CaseRequestNo,
                            c.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseRequestDate)),
                            c.CustomerName,
                            c.CaseName
                            );
                    });

                    $("tfoot", "#tblCaseFeeList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.caseFeeList").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: caseFeeFileSearch.List,
                        callBackArgs: null
                    });
                    caseFeeFileSearch.BindMenu();
                } else {
                    $("tfoot", "#tblCaseFeeList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    BindMenu: function () {
        $('div.gridSection').contextMenu('menu', {
            menuStyle: {
                width: '252px'
            },

            itemStyle: {
                width: '250px'
            },

            bindings: {

                /*转票*/
                'transmit': function (t, e) {
                    var caseFileTypeId = $(e).attr("fileTypeId");
                    caseInfo.Multiple.TransmitFeeInvoiceFile.Open(caseFileTypeId);
                },

                'transmitTag': function (t, e) {
                    caseInfo.Multiple.TransmitFeeInvoiceFile.RemoveFeeHedgingFile();
                },
            },
            onContextMenu: function (e) {
                return true;
            },
            onShowMenu: function (e, menu) {
                return menu;
            }
        });
    },

    ExportToExcel: function () {

        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/CaseList/CaseListExportToExcel", function (response) {
            if (response.IsSuccess) {
                window.open( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseListExportToExcelDownload?fileName=" + response.Data);
                $.showModalMessageBox("导出成功.");
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    Reset: function () {
        $("#postForm :text").each(function () {
            $(this).val('');
        });
        $("#postForm :hidden").each(function () {
            $(this).val('');
        });

        $("#SearchCondition_SearchByMonthAndDay").attr("checked", false);
    },

    Selected: function (e) {

        if ($(e).prop("checked") == true) {
            $.checkbox.all("chkCaseFeeId");
        } else {
            $.checkbox.not("chkCaseFeeId");
        }
    },

}

var caseFeeSearch = {

    View: function (e) {

        var caseFeeId = $(e).attr("caseFeeId");
        if (caseFeeId == '') {
            $.showModalMessageBox("请选择查看的票据文件.");
            return false;
        }

        var caseFileName = $(e).attr("fileName");
        if (caseFileName == '') {
            $.showModalMessageBox("无票据文件.");
            return false;
        }

        var caseno = $(e).attr("caseno");

        var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
        var picfiles = new Array('jpg', 'tif', 'pdf');
        var extName = caseFileName.substring(caseFileName.lastIndexOf('.') + 1, caseFileName.length);

        if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
            var path = GV_IPR.OfficeOnlineUrl + GV_IPR.IPROnlineUrl + "CaseFeeFiles/" + caseno + "/" + caseFileName;
            window.open(path);
        }
        else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
            var path = GV_IPR.IPROnlineUrl + "CaseFeeFiles/" + caseno + "/" + caseFileName;
            window.open(path);
        } else {
            caseFeeSearch.Download(caseFeeId);
        }
    },

    Download: function (caseFeeId) {
        window.open( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseFeeFileDownload?caseFeeId=" + caseFeeId);
        return true;
    },

    List: function () {
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/CasePatentOfficeFee/CaseFeeFileSearchList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseFeeList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.CaseFeeList, function (i, c) {
                        var caseRequestDate = c.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseRequestDate));
                        var feeTypeName = $.caseFeeType.getCaseFeeTypeNameById(c.CaseFeeTypeId);

                        $("tbody", "#tblCaseFeeList").addRow(
                            "<input type='checkbox' id='chkCaseFeeId' name='chkCaseFeeId' class='ng-pristine ng-valid' customerid=" + c.CustomerId + " caseno=" + c.CaseNo + " caseid=" + c.CaseId + " value=" + c.CaseFeeId + " caserequestdate=" + caseRequestDate + ">",
                            "未到账",
                            feeTypeName,
                            c.Amount,
                            c.CashedAmount == null ? 0 : c.CashedAmount,
                            c.PaidAmount == null ? 0 : c.PaidAmount,
                            c.InvoicedAmount == null ? 0 : c.InvoicedAmount,
                            c.InformDate == null ? '' : getDate(convertJsonDateToJSDate(c.InformDate)),
                            "<a href='javascript:void(0)' onclick=\"javascript:caseInfo.View(" + c.CaseId + ",'" + c.CaseNo + "')\"> " + c.CaseNo + "</a>",
                            c.CaseRequestNo,
                            c.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseRequestDate)),
                            c.CustomerName,
                            c.CaseName
                            );
                    });

                    $("tfoot", "#tblCaseFeeList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.caseFeeList").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: caseFeeSearch.List,
                        callBackArgs: null
                    });
                    caseFeeSearch.BindMenu();
                } else {
                    $("tfoot", "#tblCaseFeeList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    BindMenu: function () {
        $('div.gridSection').contextMenu('menu', {
            menuStyle: {
                width: '252px'
            },

            itemStyle: {
                width: '250px'
            },

            bindings: {

                /*转票*/
                'transmit': function (t, e) {
                    var caseFileTypeId = $(e).attr("fileTypeId");
                    caseInfo.Multiple.TransmitFeeFile.Open(caseFileTypeId);
                },

                'transmitTag': function (t, e) {
                    caseInfo.Multiple.TransmitFeeFile.RemoveFeeHedgingFile();
                },
            },
            onContextMenu: function (e) {
                return true;
            },
            onShowMenu: function (e, menu) {
                return menu;
            }
        });
    },

    ExportToExcel: function () {

        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/CaseList/CaseListExportToExcel", function (response) {
            if (response.IsSuccess) {
                window.open( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseListExportToExcelDownload?fileName=" + response.Data);
                $.showModalMessageBox("导出成功.");
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    Reset: function () {
        $("#postForm :text").each(function () {
            $(this).val('');
        });
        $("#postForm :hidden").each(function () {
            $(this).val('');
        });

        $("#SearchCondition_SearchByMonthAndDay").attr("checked", false);
    },

    Selected: function (e) {

        if ($(e).prop("checked") == true) {
            $.checkbox.all("chkCaseFeeId");
        } else {
            $.checkbox.not("chkCaseFeeId");
        }
    },

}

var caseQuery = {

    List: function () {

        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/CaseList/CaseSearchList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.CaseList, function (i, c) {
                        var customerNames = new Array();
                        if (c.CaseCustomers != null) {
                            $.each(c.CaseCustomers, function (j, cc) {
                                customerNames.push(cc.CustomerBasic.CustomerName);
                            });
                        }

                        var caseRequestDate = c.CaseBasicInfo.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseRequestDate));

                        var deadlinestyle = '';
                        if (c.CaseBasicInfo.DeadlineLeftDays < 5) {
                            deadlinestyle = 'color:red';
                        }
                        else if (c.CaseBasicInfo.DeadlineLeftDays < 10) {
                            deadlinestyle = 'color:red';
                        }
                        else if (c.CaseBasicInfo.DeadlineLeftDays >= 10) {
                            deadlinestyle = 'color:green';
                        }

                        $("tbody", "#tblCaseList").addRow(
                            "<input type='checkbox' id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' customerid=" + c.CaseBasicInfo.CustomerId + " caseno=" + c.CaseBasicInfo.CaseNo + " caserequestdate='" + caseRequestDate + "'   value=" + c.CaseBasicInfo.CaseId + ">",
                            "<a href='javascript:void(0)' onclick='javascript:caseQuery.Open(" + c.CaseBasicInfo.CaseId + ")'>" + c.CaseBasicInfo.CaseNo + "</a>",
                            c.CaseCustomers != null ? customerNames.join() : '',
                            $.caseType.getCaseTypeName(c.CaseBasicInfo.CaseTypeId),
                            $.casePhase.getcasePhaseName(c.CaseBasicInfo.CaseTypeId, c.CaseBasicInfo.CasePhaseId),
                            c.CaseBasicInfo.CaseRequestNo,
                            c.CaseBasicInfo.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseRequestDate)),
                            c.CaseBasicInfo.CaseOriginPeopleName,
                            //c.CaseBasicInfo.ProcuratorName,
                            //c.CaseBasicInfo.CopywriterName,
                            //c.CaseBasicInfo.CaseOfficerName,
                            //c.CaseBasicInfo.ReminderDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.ReminderDate)),
                            c.CaseBasicInfo.Deadline == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.Deadline)),
                            "<div><span style='" + deadlinestyle + "'>" + c.CaseBasicInfo.DeadlineLeftDays + "</span></div>"
                            );
                    });

                    $("tfoot", "#tblCaseList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.Caselist").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: caseQuery.List,
                        callBackArgs: null
                    });

                    caseQuery.BindMenu();

                } else {

                    $("tfoot", "#tblCaseList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    AnnualYearFeeList: function () {

        $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/CaseList/SearchAnnualYearFeeList", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.CaseList, function (i, c) {
                        var customerNames = new Array();
                        if (c.CaseCustomers != null) {
                            $.each(c.CaseCustomers, function (j, cc) {
                                customerNames.push(cc.CustomerBasic.CustomerName);
                            });
                        }

                        var caseRequestDate = c.CaseBasicInfo.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseRequestDate));

                        $("tbody", "#tblCaseList").addRow(
                            "<input type='checkbox' id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' customerid=" + c.CaseBasicInfo.CustomerId + " caseno=" + c.CaseBasicInfo.CaseNo + " caserequestdate='" + caseRequestDate + "'   value=" + c.CaseBasicInfo.CaseId + ">",
                            c.CaseCustomers != null ? customerNames.join() : '',
                            c.CaseBasicInfo.CaseName,
                            $.caseType.getCaseTypeName(c.CaseBasicInfo.CaseTypeId),
                            "<a href='javascript:void(0)' onclick=\"javascript:caseInfo.View(" + c.CaseBasicInfo.CaseId + ",'" + c.CaseBasicInfo.CaseNo + "')\"> " + c.CaseBasicInfo.CaseNo + "</a>",
                            c.CaseBasicInfo.CaseRequestNo,
                            c.CaseBasicInfo.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseRequestDate)),
                            c.CaseBasicInfo.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseRequestDate)),
                            "第" + c.AnnualYearFee.AnnualYear + "年度: " + getDate(convertJsonDateToJSDate(c.AnnualYearFee.AnnualFrom)) + "至" + getDate(convertJsonDateToJSDate(c.AnnualYearFee.AnnualEnd)),
                            c.AnnualYearFee.NormalAmout + "/" + c.AnnualYearFee.CostSlowRate85Amout + "/" + c.AnnualYearFee.CostSlowRate70Amout,
                            c.AnnualYearFee.CaseCostSlowRateAmout,
                            c.CaseBasicInfo.CostSlowRate == null ? "100%" : (c.CaseBasicInfo.CostSlowRate * 100) + "%",
                            c.AnnualYearFee.PaymentInfo
                            );
                    });

                    $("tfoot", "#tblCaseList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.Caselist").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: caseQuery.AnnualYearFeeList,
                        callBackArgs: null
                    });

                    //caseQuery.BindMenu();

                } else {

                    $("tfoot", "#tblCaseList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    BindMenu: function () {
        $('div.gridSection').contextMenu('menu', {
            menuStyle: {
                width: '152px'
            },

            itemStyle: {
                width: '150px'
            },

            bindings: {

                'inprocess': function (t, e) {
                    var caseId = $(e).find("span").html();
                    caseQuery.InProcess(caseId);
                },

                'taskFinished': function (t, e) {
                    caseInfo.Multiple.Task.Finished();
                },

                'addEvent': function (t, e) {
                    caseInfo.Multiple.Event.Open();
                },

                'removeEvent': function (t, e) {
                    caseInfo.Multiple.Event.Remove();
                },

                /**/
                'push': function (t, e) {
                    caseInfo.Multiple.Edit.Open();
                },

                /*文件导入*/
                'fileImport': function (t, e) {
                    caseInfo.Multiple.Import.Open();
                },

                /*转文*/
                'transfer': function (t, e) {
                    caseInfo.Multiple.Transfer.Open();
                },

                /*加入年费监控*/
                'addInAfm': function (t, e) {
                    caseInfo.Multiple.AFM.AddIn();
                },

                /*移除年费监控*/
                'removeAfm': function (t, e) {
                    caseInfo.Multiple.AFM.Remove();
                },


            },
            onContextMenu: function (e) {
                return true;
            },
            onShowMenu: function (e, menu) {
                var caseId = $(e.target).parents("tr").find("#chkCaseId").val();
                $('#inprocess', menu).append("<span style='display:none'>" + caseId + "</span>");
                return menu;
            }
        });
    },

    ExportToExcel: function () {

        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/CaseList/CaseListExportToExcel", function (response) {
            if (response.IsSuccess) {
                window.open( AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseListExportToExcelDownload?fileName=" + response.Data);
                $.showModalMessageBox("导出成功.");
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    AnnualYearExportToExcel: function () {

        $.showModalConfirmDialog("导出的年费清单只包含已授权专利案件.", 'caseQuery.AnnualYearExportToExcelCallBack', null);
        return true;
    },

    AnnualYearExportToExcelCallBack: function () {

        $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/CaseList/AnnualYearExportToExcel", function (response) {
            if (response.IsSuccess) {
                window.open(AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseListExportToExcelDownload?fileName=" + response.Data);
                $.showModalMessageBox("导出成功.");
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },

    InProcess: function (caseId) {

        var search = {};

        search.CaseId = caseId;
        search.PageId = $("#SearchCondition_PageId").val();
        search.PageNo = $("#SearchCondition_PageNo").val();
        search.PageSize = $("#SearchCondition_PageSize").val();
        search.PageName = $("#SearchCondition_PageName").val();

        search.CustomerName = $("#SearchCondition_CustomerName").val();
        search.CaseNos = $("#SearchCondition_CaseNos").val();
        search.CaseTypeId = $("#SearchCondition_CaseTypeId").val();
        search.CasePhaseId = $("#SearchCondition_CasePhaseId").val();
        search.CaseOriginPeopleName = $("#SearchCondition_CaseOriginPeopleName").val();
        search.CaseCopywriterName = $("#SearchCondition_CaseCopywriterName").val();
        search.CaseProcuratorName = $("#SearchCondition_CaseProcuratorName").val();
        search.CaseOfficerName = $("#SearchCondition_CaseOfficerName").val();
        search.CaseRequestDateFrom = $("#SearchCondition_CaseRequestDateFrom").val() == '' ? null : $("#SearchCondition_CaseRequestDateFrom").val();
        search.CaseRequestDateTo = $("#SearchCondition_CaseRequestDateTo").val() == '' ? null : $("#SearchCondition_CaseRequestDateTo").val();
        search.SearchByMonthAndDay = $("#SearchCondition_SearchByMonthAndDay").prop("checked") == true;

        search.CaseDeadlineFrom = $("#SearchCondition_CaseDeadlineFrom").val() == '' ? null : $("#SearchCondition_CaseDeadlineFrom").val();
        search.CaseDeadlineTo = $("#SearchCondition_CaseDeadlineTo").val() == '' ? null : $("#SearchCondition_CaseDeadlineTo").val();


        var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CreateUpdate?typeId=1&caseId=" + caseId + "&k=" + escape(JSON.stringify(search));
        window.open(url);

    },

    /*创建案件*/
    Open: function (caseId) {
        caseQuery.InProcess(caseId);
    },

    Reset: function () {
        $("#postForm :text").each(function () {
            $(this).val('');
        });
        //$("#postForm :hidden").each(function () {
        //    if ($(this).attr("id") == "SearchCondition_PageId" || $(this).attr("id") == "")
        //    {

        //    }
        //    $(this).val('');
        //});

        $("#SearchCondition_SearchByMonthAndDay").attr("checked", false);
    },

    Selected: function (e) {

        if ($(e).prop("checked") == true) {
            $.checkbox.all("chkCaseId");
        } else {
            $.checkbox.not("chkCaseId");
        }
    },

}

$(document).ready(function () {

    $(document).click(function (e) {
        $("#divCasePhaseCheckBoxList").off().hide();
        $("#divCaseFeeTypeCheckBoxList").off().hide();
        $("#divCaseTypeCheckBoxList").off().hide();
        $("#divCaseFileTypeList").off().hide();
        $("#div_CaseFileTypeList").off().hide();

        $("#divUserList").off().hide();
        $("#divUsers").off().hide();
    });

    //caseQuery.List();

    var caseOfficer = new AssociateUser(
        $("#divAssociateUserList"),
        $("#SearchCondition_CaseOfficerName"),
        $("#SearchCondition_CaseOfficerName"),
        null
    );

    var caseOriginPeople = new AssociateUser(
        $("#divAssociateUserList"),
        $("#SearchCondition_CaseOriginPeopleName"),
        $("#SearchCondition_CaseOriginPeopleName"),
        null
    );

    var caseProcurator = new AssociateUser(
        $("#divAssociateUserList"),
        $("#SearchCondition_CaseProcuratorName"),
        $("#SearchCondition_CaseProcuratorName"),
        null
    );

    var caseCopywriter = new AssociateUser(
        $("#divAssociateUserList"),
        $("#SearchCondition_CaseCopywriterName"),
        $("#SearchCondition_CaseCopywriterName"),
        null
    );

    $("#chkCaseAll").off().on("click", function () {
        caseQuery.Selected(this);
    });

    $("#chkCaseFileIdAll").off().on("click", function () {
        caseFileSearch.Selected(this);
    });

    $("#chkCaseFeeIdAll").off().on("click", function () {
        caseFeeFileSearch.Selected(this);
    });
    
    $("#btnCaseSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        caseQuery.List();
    });

    $("#btnCaseAnnualYearFeeSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        caseQuery.AnnualYearFeeList();
    });

    $("#btnCasePatentOfficeFileSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        caseFileSearch.List();
    });

    $("#btnCasePatentOfficeFeeSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        caseFeeSearch.List();
    });

    $("#btnCasePatentOfficeFeeFileSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        caseFeeSearch.List();
    });

    $("#btnCasePatentOfficeInvoiceFileSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        caseFeeFileSearch.List();
    });

    $("#btnCaseTrademarkOfficeInvoiceFileSearch").click(function () {

        $("#SearchCondition_PageNo").val(1);
        $("#SearchCondition_PageSize").val(20);

        caseFeeFileSearch.List();
    });

    $("#btnCaseExportToExcel").click(function () {
        caseQuery.ExportToExcel();
    });

    $("#btnCaseSearchReset").click(function () {
        caseQuery.Reset();
    });

    $("#SearchCondition_CasePhaseName").off().on("click", function () {
        var tirgger = this;
        var html = $.casePhase.getCasePhaseCheckBoxListHtml();
        $(".divcaseconditioncasephases").html(html);
        $("#hidCasePhaseId").val("SearchCondition_CasePhaseId");
        $("#hidCasePhaseName").val($(tirgger).attr("id"));
        $("#divCasePhaseCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 15,
            "top": $(tirgger).position().top + 110
        }).toggle();

        return false;
    });

    $("#SearchCondition_CaseTypeName").off().on("click", function () {
        var tirgger = this;
        var html = $.caseType.getCaseTypeCheckBoxListHtml();
        $(".divcaseconditioncasetypes").html(html);
        $("#hidCaseTypeId").val("SearchCondition_CaseTypeId");
        $("#hidCaseTypeName").val($(tirgger).attr("id"));
        $("#divCaseTypeCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 15,
            "top": $(tirgger).position().top + 110
        }).toggle();

        return false;
    });

    $("#btnCaseBatchEditCancel,#btnCaseBatchEditClose").off().on("click", function () {
        caseInfo.Multiple.Edit.Close();
    });

    $("#btnCaseBatchEdit").off().on("click", function () {
        caseInfo.Multiple.Edit.Create();
    });

    $("#btnCaseAnnualYearEditCreate").off().on("click", function () {
        caseInfo.Multiple.AnnualYearEdit.Create();
    });

    $("#btnCaseAnnualYearEdit").off().on("click", function () {
        caseInfo.Multiple.AnnualYearEdit.Open();
    });

    $("#btnCaseAnnualYearEditClose,#btnCaseAnnualYearEditCancel").off().on("click", function () {
        caseInfo.Multiple.AnnualYearEdit.Close();
    });

    
    $("#btnCaseFileBatchImportCancel,#btnCaseFileBatchImportClose").off().on("click", function () {
        caseInfo.Multiple.Import.Close();
    });

    $("#btnCaseFileBatchImport").off().on("click", function () {
        caseInfo.Multiple.Import.Create();
    });

    $("#CaseOfficerName").off().on("click", function () {
        $("#hidUserId").val("CaseOfficer");
        $("#hidUserName").val("CaseOfficerName");
        $("#divUsers").off().css({
            "position": "absolute",
            "left": $("#CaseOfficerName").offsetParent().position().left + 15,
            "top": $("#CaseOfficerName").offsetParent().position().top + 25,
            "z-index": 9999
        }).show();
        return false;
    });

    $("#divCaseTypeCheckBoxList").find("li").off().on("click", function (e) {

        if ($(e.target).is("lable")) {
            e.stopPropagation();
            return false;
        }

        var currentSelectedControl = $("#hidCaseTypeName").val();
        var currentSelectedIdControl = $("#hidCaseTypeId").val();

        if ($(this).attr("id") == 'btnAllUnSelected') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }
        else if ($(this).attr("id") == 'btnAllSelected') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }

        $("#" + currentSelectedControl).val('');
        $("#" + currentSelectedIdControl).val('');

        var caseTypeNames = '';
        var caseTypeIds = '';

        $("#divCaseTypeCheckBoxList").find("input:checkbox").each(function () {
            if ($(this).attr("checked") == 'checked') {
                caseTypeNames += $(this).attr("casetypename") + ",";
                caseTypeIds += $(this).attr("casetypeid") + ",";
            }
        });

        $("#" + currentSelectedControl).val(caseTypeNames.substring(0, caseTypeNames.length - 1));
        $("#" + currentSelectedIdControl).val(caseTypeIds.substring(0, caseTypeIds.length - 1));

        e.stopPropagation();

        return true;
    });

    $("#divCasePhaseCheckBoxList").find("li").off().on("click", function (e) {

        if ($(e.target).is("lable")) {
            e.stopPropagation();
            return false;
        }

        var currentSelectedControl = $("#hidCasePhaseName").val();
        var currentSelectedIdControl = $("#hidCasePhaseId").val();

        if ($(this).attr("id") == 'btnAllUnSelected') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }
        else if ($(this).attr("id") == 'btnAllSelected') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }

        $("#" + currentSelectedControl).val('');
        $("#" + currentSelectedIdControl).val('');

        var casePhaseNames = '';
        var casePhaseIds = '';

        $("#divCasePhaseCheckBoxList").find("input:checkbox").each(function () {
            if ($(this).attr("checked") == 'checked') {
                casePhaseNames += $(this).attr("casephasename") + ",";
                casePhaseIds += $(this).attr("casephaseid") + ",";
            }
        });

        $("#" + currentSelectedControl).val(casePhaseNames.substring(0, casePhaseNames.length - 1));
        $("#" + currentSelectedIdControl).val(casePhaseIds.substring(0, casePhaseIds.length - 1));

        e.stopPropagation();

        return true;
    });

    //$("#SearchCondition_CaseOriginPeopleName").off().on("click", function () {
    //    $("#hidUserId").val("SearchCondition_CaseOriginPeopleId");
    //    $("#hidUserName").val("SearchCondition_CaseOriginPeopleName");
    //    $("#divUserList").off().css({
    //        "position": "absolute",
    //        "left": $("#SearchCondition_CaseOriginPeopleName").position().left + 0,
    //        "top": $("#SearchCondition_CaseOriginPeopleName").position().top + 25,
    //        "z-index": 9999
    //    }).show();
    //    return false;
    //});

    //$("#SearchCondition_CaseOfficerName").off().on("click", function () {
    //    $("#hidUserId").val("SearchCondition_CaseOfficerId");
    //    $("#hidUserName").val("SearchCondition_CaseOfficerName");
    //    $("#divUserList").off().css({
    //        "position": "absolute",
    //        "left": $("#SearchCondition_CaseOfficerName").position().left + 0,
    //        "top": $("#SearchCondition_CaseOfficerName").position().top + 25,
    //        "z-index": 9999
    //    }).show();
    //    return false;
    //});

    //$("#SearchCondition_CaseCopywriterName").off().on("click", function () {
    //    $("#hidUserId").val("SearchCondition_CaseCopywriterId");
    //    $("#hidUserName").val("SearchCondition_CaseCopywriterName");
    //    $("#divUserList").off().css({
    //        "position": "absolute",
    //        "left": $("#SearchCondition_CaseCopywriterName").position().left + 0,
    //        "top": $("#SearchCondition_CaseCopywriterName").position().top + 25,
    //        "z-index": 9999
    //    }).show();
    //    return false;
    //});

    //$("#SearchCondition_CaseProcuratorName").off().on("click", function () {
    //    $("#hidUserId").val("SearchCondition_CaseProcuratorId");
    //    $("#hidUserName").val("SearchCondition_CaseProcuratorName");
    //    $("#divUserList").off().css({
    //        "position": "absolute",
    //        "left": $("#SearchCondition_CaseProcuratorName").position().left + 0,
    //        "top": $("#SearchCondition_CaseProcuratorName").position().top + 25,
    //        "z-index": 9999
    //    }).show();
    //    return false;
    //});

    $("#divUserList").find("li").off().on("click", function () {
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        var currentSelectedControl = $("#hidUserName").val();
        var currentSelectedIdControl = $("#hidUserId").val();
        $("#" + currentSelectedControl).val(userName);
        $("#" + currentSelectedIdControl).val(userId);
        $("#divUsers").hide();
    });

    $("#divUsers").find("li").off().on("click", function () {
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        var currentSelectedControl = $("#hidUserName").val();
        var currentSelectedIdControl = $("#hidUserId").val();
        $("#" + currentSelectedControl).val(userName);
        $("#" + currentSelectedIdControl).val(userId);
        $("#divUsers").hide();
    });

    $("#lnkCaseFileTypeId").off().on("click", function () {
        var tirgger = $("#CaseFileTypeName");

        $(".divCaseFileTypeList").html($.caseFileType.getAllCaseFileTypeListHtml());

        $("#divCaseFileTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left + 15,
            "top": $(tirgger).offsetParent().position().top + 32,
            "z-index": 9999
        }).toggle();

        $("#hidCaseFileTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFileTypeId").val($("#CaseFileTypeId").attr("id"));//Id

        return false;
    });

    $("#lnkCaseFileTransformedTypeId").off().on("click", function () {
        var tirgger = $("#CaseFileTypeName");

        $(".divCaseFileTypeList").html($.caseFileType.getCaseTransformedFileTypeListHtml());

        $("#divCaseFileTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left + 15,
            "top": $(tirgger).offsetParent().position().top + 32,
            "z-index": 9999
        }).toggle();

        $("#hidCaseFileTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFileTypeId").val($("#CaseFileTypeId").attr("id"));//Id

        return false;
    });

    $("#divCaseFileTypeList").find("li").off().on("click", function () {
        var caseFileTypeId = $(this).find("a").attr("id");
        var caseFileTypeName = $(this).find("a").text();
        var caseFileTypeNameText = $(this).find("a").attr("text");
        var currentSelectedControl = $("#hidCaseFileTypeName").val();
        var currentSelectedIdControl = $("#hidCaseFileTypeId").val();
        $("#" + currentSelectedControl).val(caseFileTypeName);
        $("#" + currentSelectedIdControl).val(caseFileTypeId);

        var hedgingFileTypeId = $(this).find("a").attr("hedgingFileTypeId");
        var hedgingFeeTypeId = $(this).find("a").attr("hedgingFeeTypeId");

        $("#divCaseFileTypeList").hide();
    });

    $("#flCaseFile").off().on("change", function () {
        $("#txtCaseFilePath").val($("#flCaseFile").val());
    });

    $("#SearchCondition_CasePhaseName").off().on("click", function () {
        var tirgger = this;
        var html = $.casePhase.getCasePhaseCheckBoxListHtml();
        $(".divcaseconditioncasephases").html(html);
        $("#hidCasePhaseId").val("SearchCondition_CasePhaseId");
        $("#hidCasePhaseName").val("SearchCondition_CasePhaseName");
        $("#divCasePhaseCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 0,
            "top": $(tirgger).position().top + 25,
            "z-index": 9999
        }).toggle();

        return false;
    });
    $("#divCasePhaseCheckBoxList").find("li").off().on("click", function (e) {

        if ($(e.target).is("lable")) {
            e.stopPropagation();
            return false;
        }

        var currentSelectedControl = $("#hidCasePhaseName").val();
        var currentSelectedIdControl = $("#hidCasePhaseId").val();

        if ($(this).attr("id") == 'btnAllUnSelected') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }
        else if ($(this).attr("id") == 'btnAllSelected') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }

        $("#" + currentSelectedControl).val('');
        $("#" + currentSelectedIdControl).val('');

        var casePhaseNames = '';
        var casePhaseIds = '';

        $("#divCasePhaseCheckBoxList").find("input:checkbox").each(function () {
            if ($(this).attr("checked") == 'checked') {
                casePhaseNames += $(this).attr("casephasename") + ",";
                casePhaseIds += $(this).attr("casephaseid") + ",";
            }
        });

        $("#" + currentSelectedControl).val(casePhaseNames.substring(0, casePhaseNames.length - 1));
        $("#" + currentSelectedIdControl).val(casePhaseIds.substring(0, casePhaseIds.length - 1));

        e.stopPropagation();

        return true;
    });
    $("#SearchCondition_CaseTypeName").off().on("click", function () {
        var tirgger = this;
        var html = $.caseType.getCaseTypeCheckBoxListHtml();
        $(".divcaseconditioncasetypes").html(html);
        $("#hidCaseTypeId").val("SearchCondition_CaseTypeId");
        $("#hidCaseTypeName").val($(tirgger).attr("id"));
        $("#divCaseTypeCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 0,
            "top": $(tirgger).position().top + 25,
            "z-index": 9999
        }).toggle();

        return false;
    });
    $("#divCaseTypeCheckBoxList").find("li").off().on("click", function (e) {

        if ($(e.target).is("lable")) {
            e.stopPropagation();
            return false;
        }

        var currentSelectedControl = $("#hidCaseTypeName").val();
        var currentSelectedIdControl = $("#hidCaseTypeId").val();

        if ($(this).attr("id") == 'btnAllUnSelected') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }
        else if ($(this).attr("id") == 'btnAllSelected') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }

        $("#" + currentSelectedControl).val('');
        $("#" + currentSelectedIdControl).val('');

        var caseTypeNames = '';
        var caseTypeIds = '';

        $("#divCaseTypeCheckBoxList").find("input:checkbox").each(function () {
            if ($(this).attr("checked") == 'checked') {
                caseTypeNames += $(this).attr("casetypename") + ",";
                caseTypeIds += $(this).attr("casetypeid") + ",";
            }
        });

        $("#" + currentSelectedControl).val(caseTypeNames.substring(0, caseTypeNames.length - 1));
        $("#" + currentSelectedIdControl).val(caseTypeIds.substring(0, caseTypeIds.length - 1));

        e.stopPropagation();

        return true;
    });
    $("#divCaseFeeTypeCheckBoxList").find("li").off().on("click", function (e) {

        if ($(e.target).is("lable")) {
            e.stopPropagation();
            return false;
        }

        var currentSelectedControl = $("#hidCaseFeeTypeName").val();
        var currentSelectedIdControl = $("#hidCaseFeeTypeId").val();

        if ($(this).attr("id") == 'btnAllUnSelected') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }
        else if ($(this).attr("id") == 'btnAllSelected') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }

        $("#" + currentSelectedControl).val('');
        $("#" + currentSelectedIdControl).val('');

        var caseFeeTypeNames = '';
        var caseFeeTypeIds = '';

        $("#divCaseFeeTypeCheckBoxList").find("input:checkbox").each(function () {
            if ($(this).attr("checked") == 'checked') {
                caseFeeTypeNames += $(this).attr("casefeetypename") + ",";
                caseFeeTypeIds += $(this).attr("casefeetypeid") + ",";
            }
        });

        $("#" + currentSelectedControl).val(caseFeeTypeNames.substring(0, caseFeeTypeNames.length - 1));
        $("#" + currentSelectedIdControl).val(caseFeeTypeIds.substring(0, caseFeeTypeIds.length - 1));

        e.stopPropagation();

        return true;
    });
    $("#SearchCondition_CaseFeeTypeName").off().on("click", function () {
        var tirgger = this;
        var caseClassTypeId = $("#SearchCondition_CaseClassTypeId").val();
        var html = $.caseFeeType.getCaseFeeTypeCheckBoxListHtmlForCaseTypeId(caseClassTypeId);
        $(".divcaseconditioncasefeetypes").html(html);
        $("#hidCaseFeeTypeId").val("SearchCondition_CaseFeeTypeId");
        $("#hidCaseFeeTypeName").val($(tirgger).attr("id"));
        $("#divCaseFeeTypeCheckBoxList").css({
            "position": "absolute",
            "left": $(tirgger).position().left + 0,
            "top": $(tirgger).position().top + 25,
            "z-index": 9999
        }).toggle();

        return false;
    });

    $("#btnCaseListExportToWordCancel,#btnCaseListExportToWordClose").off().on("click", function () {
        caseInfo.Multiple.Transfer.Close();
    });

    $("#btnCaseListExportToWordCreate").off().on("click", function () {
        caseInfo.Multiple.Transfer.Export();
    });

    $("#btnCaseListExportToWordUpload").off().on("click", function () {
        caseInfo.Multiple.Transfer.Upload();
    });

    $("#btnTransmitCaseFileClose,#btnTransmitCaseFileCancel").off().on("click", function () {
        caseInfo.Multiple.TransmitFile.Close();
    });

    $("#btnTransmitCaseFileCreate").off().on("click", function () {
        caseInfo.Multiple.TransmitFile.Transmit();
    });

    $("#btnTransmitCaseFileUpload").off().on("click", function () {
        caseInfo.Multiple.TransmitFile.Upload();
    });

    $("#btnTransmitCaseFeeFileClose,#btnTransmitCaseFeeFileCancel").off().on("click", function () {
        caseInfo.Multiple.TransmitFeeFile.Close();
    });

    $("#btnTransmitCaseFeeFileCreate").off().on("click", function () {
        caseInfo.Multiple.TransmitFeeFile.Transmit();
    });

    $("#btnTransmitCaseFeeFileUpload").off().on("click", function () {
        caseInfo.Multiple.TransmitFeeFile.Upload();
    });

    $("#btnTransmitCaseFeeInvoiceFileClose,#btnTransmitCaseFeeInvoiceFileCancel").off().on("click", function () {
        caseInfo.Multiple.TransmitFeeInvoiceFile.Close();
    });

    $("#btnTransmitCaseFeeInvoiceFileCreate").off().on("click", function () {
        caseInfo.Multiple.TransmitFeeInvoiceFile.Transmit();
    });

    $("#btnTransmitCaseFeeInvoiceFileUpload").off().on("click", function () {
        caseInfo.Multiple.TransmitFeeInvoiceFile.Upload();
    });

    $("#btnCaseEvent").off().on("click", function () {
        caseInfo.Multiple.Event.CreateUpdate();
    });

    $("#btnCaseEventClose,#btnCaseEventCancel").off().on("click", function () {
        caseInfo.Multiple.Event.Close();
    });

    $(".aps-icon-shangjiantou").off().on("click", function () {
        var sorting = $(this).parent().attr("data-field");
        if (sorting != null && sorting != '')
        {
            $(".aps-sort").each(function (i, e) {
                $(e).removeClass("aps-asc");
                $(e).removeClass("aps-desc");
            });

            $(this).parent().addClass("aps-asc");
            $("#SearchCondition_Sorting").val(sorting + " asc");
        }
        caseQuery.List();
    });

    $(".aps-icon-xiajiantou").off().on("click", function () {
        var sorting = $(this).parent().attr("data-field");
        if (sorting != null && sorting != '') {
            $(".aps-sort").each(function (i, e) {
                $(e).removeClass("aps-asc");
                $(e).removeClass("aps-desc");
            });
            $(this).parent().addClass("aps-desc");
            $("#SearchCondition_Sorting").val(sorting + " desc");
        }
        caseQuery.List();
    });

    $("#btnCaseAnnualYearExportToExcel").click(function () {
        caseQuery.AnnualYearExportToExcel();
    });
});
