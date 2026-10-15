/*案件导出*/

function AssociateCustomer(div, ctlid, ctlname) {
    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;

    this.Customer = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") { return false; }
        var curobj = new Object();
        curobj.keyword = name;
        $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CustomerList", curobj, function (response) {
            $(div).find(".i_common_list").empty();
            if (response.IsSuccess) {
                if (response.Data) {
                    var html = "";
                    $.each(response.Data.Customers, function (i, c) {
                        html += '<a href="javascript:void(0)" customerid=' + c.CustomerBasic.CustomerId + ' >' + c.CustomerBasic.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").click(function () {
                        $(ctlid).val($(this).attr("customerId"));
                        $(ctlname).val($(this).text());
                        $(div).hide();
                    });
                }
            }
            else {
                $.showModalMessageBox(response.Message);
            }
        }, false);

        $(div).css({
            "position": "absolute",
            "left": $(ctlname).position().left + 15,
            "top": $(ctlname).position().top + 70,
            "z-index": 9999
        }).show();
    }

    $(ctlname).bind('keyup', { obj: this }, function (event) {
        if (event.keyCode == 38) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).prev().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).prev().addClass("hover");
                        $(hover).prev().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 40) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).next().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).next().addClass("hover");
                        $(hover).next().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 13) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    $(hover).click();
                }
            }
        } else {
            clearTimeout(event.data.obj.Event);
            event.data.obj.Event = setTimeout(function () { event.data.obj.Customer(event.data.obj); }, 500);
        }
    });

    $(ctlname).bind('blur', { obj: this }, function (event) {
        if ($(this).val() == "" || ($(this).val() == $(this).attr("mod-notice-tip"))) {
            event.data.obj.GlobalName = "";
            $(ctlid).val("");
        }
        if ($(ctlid).val() == "") {
            if ($(this).attr("mod-notice-tip")) {
                $(this).val($(this).attr("mod-notice-tip"));
            } else {
                $(this).val("");
            }
        }
        //        if (event.data.obj.GlobalName != "") {
        //            $(this).val(event.data.obj.GlobalName);
        //            $(ctlid).val(event.data.obj.GlobalID);
        //        }
    });

    return this;
}

var cases = {

    OpenCase: function (caseId) {
        if (caseId == undefined) {
            var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CreateUpdate?typeId=1";
            window.open(url);
        } else {
            var url =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CreateUpdate?CaseId=" + caseId;
            window.open(url);
        }
    },

    List: function() {

        if ($("#SearchCondition_CustomerId").val() == '') {
            $.showModalMessageBox("请输入客户查询条件.");
            return false;
        }
        $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseListToWord", function(response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCaseList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.CaseList, function (i, c) {
                        $("tbody", "#tblCaseList").addRow(
                            "<input type='checkbox' name='chkCaseId' class='ng-pristine ng-valid' value='" + c.CaseBasicInfo.CaseId + "'>",
                            "<a href='javascript:void(0)' onclick='javascript:cases.OpenCase(" + c.CaseBasicInfo.CaseId + ")'>" + c.CaseBasicInfo.CaseNo + "</a>",
                            $.caseType.getCaseTypeName(c.CaseBasicInfo.CaseTypeId),
                            $.casePhase.getcasePhaseName(c.CaseBasicInfo.CaseTypeId,c.CaseBasicInfo.CasePhaseId),
                            c.CaseBasicInfo.CaseRequestNo,
                            c.CaseBasicInfo.CaseRequestDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseRequestDate)),
                            c.CaseBasicInfo.CaseAcceptDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseAcceptDate)),
                            c.CaseBasicInfo.CaseOriginPeopleName,
                            c.CaseBasicInfo.CaseOriginDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseOriginDate)),
                            c.CaseBasicInfo.CaseRegisterDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseRegisterDate)),
                            c.CaseBasicInfo.CaseRegisterNo,
                            c.CaseBasicInfo.AuthorizationDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.AuthorizationDate)),
                            c.CaseBasicInfo.ProcuratorName,
                            c.CaseBasicInfo.CopywriterName,
                            //c.CaseBasicInfo.CaseSubmitter,
                            //c.CaseBasicInfo.CaseSubmitDate == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.CaseSubmitDate)),
                            c.CaseBasicInfo.CaseOfficerName,
                            c.CaseBasicInfo.Deadline == null ? '' : getDate(convertJsonDateToJSDate(c.CaseBasicInfo.Deadline)),
                            "<span class=\"judge\">" + (c.CaseBasicInfo.HasPriority ? "&radic;" : "&times;") + "</span>",
                            "<span class=\"judge\">" + (c.CaseBasicInfo.HasForeign ? "&radic;" : "&times;") + "</span>"
                        );
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

                    cases.BindMenu();

                } else {
                    $("tfoot", "#tblCaseList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
        return true;
    },

    BindMenu: function() {
        $('div.gridSection').contextMenu('exportingMenu', {
            menuStyle: {
                width: '152px'
            },

            itemStyle: {
                width: '150px'
            },

            //itemHoverStyle: {
            //    color: '#fff',
            //    backgroundColor: '#0f0',
            //    border: 'none'
            //},

            bindings: {
                'exportToWord': function (t, e) {
                    cases.Open();
                },
 
            },
            onContextMenu: function(e) {
                return true;
            },
            onShowMenu: function(e, menu) {
                if ($(e.target).parents("tr").find(".feeId").hasClass("feeId")) {
                    var feeId = $(e.target).parents("tr").find("#item_FeeId").val();
                    $('#feeConfirm,#billConfirm,#nolock', menu).append("<span style='display:none'>" + feeId + "</span>");
                } else {
                    $('#feeConfirm, #billConfirm,#nolock', menu).remove();
                }
                return menu;
            }
        });
    },

    Open: function () {

        var caseIds = $.checkbox.vals("chkCaseId");
        if (caseIds.length == 0) {
            $.showModalMessageBox("请选择导出的案件.");
            return;
        }

        var customerId = $("#SearchCondition_CustomerId").val();
        var data = {
            customerId: customerId,
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
             $("#CaseFileType"),
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
            $.showModalMessageBox("请选择专文文档.");
            return false;
        }


        var data = {
            customerId: $("#SearchCondition_CustomerId").val(),
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

    Selected: function (e) {
        if ($(e).prop("checked") == true) {
            $.checkbox.all("chkCaseId");
        }
        else {
            $.checkbox.not("chkCaseId");
        }
    },

    ProcessFileTypeSelectedCallBack: function (caseFileTypeId, caseFileTypeNameText,hedgingFileTypeId) {
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
}

$(document).ready(function () {

    var customter = new AssociateCustomer(
         $("#div_customer"),
         $("#SearchCondition_CustomerId"),
         $("#txtCustomerNo")
        );

    $("#chkCaseAll").off().on("click", function () {
        cases.Selected(this);
    });

    $("#btnCaseSearch").off().on("click", function () {
        cases.List();
    });

    $("#btnCreate").off().on("click", function () {
        cases.Open();
    });

    $("#btnCaseListExportToWordCancel,#btnCaseListExportToWordClose").off().on("click", function () {
        cases.Close();
    });

    $("#btnCaseListExportToWordCreate").off().on("click", function () {
        cases.Export();
    });

    $("#btnCaseListExportToWordUpload").off().on("click", function () {
        cases.Upload();
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
            "top": $(tirgger).position().top + 70
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

    //$("#CaseFileType").off().on("click", function () {
    //    var tirgger = this;
    //    $(".divCaseFileTypeList").empty();
    //    $(".divCaseFileTypeList").html($.caseFileType.getCaseTransformedFileTypeListHtml());
    //    $("#divCaseFileTypeList").css({
    //        "position": "absolute",
    //        "left": $(tirgger).position().left + 142,
    //        "top": $(tirgger).position().top + 60
    //    }).toggle();

    //    $("#hidCaseFileTypeName").val($(tirgger).attr("id")); //名称
    //    $("#hidCaseFileTypeId").val($("#CaseFileTypeId").attr("id"));//Id

    //    return false;
    //});

    $("#flCaseFile").off().on("change", function () {
        $("#txtCaseFilePath").val($("#flCaseFile").val());
    });

    $("#lnkCaseFileTypeId").off().on("click", function () {
        var tirgger = $("#CaseFileType");
        $(".divCaseFileTypeList").empty();
        $(".divCaseFileTypeList").html($.caseFileType.getCaseTransformedFileTypeListHtml());
        $("#divCaseFileTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left + 15,
            "top": $(tirgger).offsetParent().position().top + 32
        }).toggle();

        $("#hidCaseFileTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFileTypeId").val($("#CaseFileTypeId").attr("id"));//Id

        return false;
    });
    

    $("#divCaseFileTypeList").find("li").off().on("click", function () {
        var caseFeeTypeId = $(this).find("a").attr("id");
        var caseFeeTypeName = $(this).find("a").text();
        var currentSelectedControlId = $("#hidCaseFileTypeId").val();
        var currentSelectedControlName = $("#hidCaseFileTypeName").val();
        $("#" + currentSelectedControlId).val(caseFeeTypeId);
        $("#" + currentSelectedControlName).val(caseFeeTypeName);
        $("#divCaseFileTypeList").hide();
    });

    $(document).click(function () {
        $("#divCaseFileTypeList").hide();
    });
    
});


