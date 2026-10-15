$(document).ready(function () {
    c.Cases.Case.CaseFiles.Layout();
    c.Cases.Case.CaseLogs.List();
    c.Cases.Case.CaseEvents.List();

    $(function () {
        $('[data-toggle="popover"]').each(function () {
            var element = $(this);
            var id = element.attr('id');
            var txt = element.html();
            element.popover({
                trigger: 'manual',
                placement: 'bottom', //top, bottom, left or right
                title: txt,
                html: 'true',
                content: getLitigantAgent(element),

            }).on("mouseenter", function () {
                var _this = this;
                $(this).popover("show");
                $(this).siblings(".popover").on("mouseleave", function () {
                    $(_this).popover('hide');
                });
            }).on("mouseleave", function () {
                var _this = this;
                setTimeout(function () {
                    if (!$(".popover:hover").length) {
                        $(_this).popover("hide")
                    }
                }, 100);
            });
        });
    });

    $(function () {
        $('[data-toggle="popover_lawyer"]').each(function () {
            var element = $(this);
            var id = element.attr('id');
            var txt = element.html();
            element.popover({
                trigger: 'manual',
                placement: 'bottom', //top, bottom, left or right
                title: txt,
                html: 'true',
                content: getStaff(element),

            }).on("mouseenter", function () {
                var _this = this;
                $(this).popover("show");
                $(this).siblings(".popover").on("mouseleave", function () {
                    $(_this).popover('hide');
                });
            }).on("mouseleave", function () {
                var _this = this;
                setTimeout(function () {
                    if (!$(".popover:hover").length) {
                        $(_this).popover("hide")
                    }
                }, 100);
            });
        });
    });

    $(function () {
        $('[data-toggle="popover_assistant"]').each(function () {
            var element = $(this);
            var id = element.attr('id');
            var txt = element.html();
            element.popover({
                trigger: 'manual',
                placement: 'bottom', //top, bottom, left or right
                title: txt,
                html: 'true',
                content: getStaff(element),

            }).on("mouseenter", function () {
                var _this = this;
                $(this).popover("show");
                $(this).siblings(".popover").on("mouseleave", function () {
                    $(_this).popover('hide');
                });
            }).on("mouseleave", function () {
                var _this = this;
                setTimeout(function () {
                    if (!$(".popover:hover").length) {
                        $(_this).popover("hide")
                    }
                }, 100);
            });
        });
    });

    $(function () {
        $('[data-toggle="popover_court"]').each(function () {
            var element = $(this);
            var id = element.attr('id');
            var txt = element.html();
            element.popover({
                trigger: 'manual',
                placement: 'right', //top, bottom, left or right
                title: txt,
                html: 'true',
                content: getCourt(element),

            }).on("mouseenter", function () {
                var _this = this;
                $(this).popover("show");
                $(this).siblings(".popover").on("mouseleave", function () {
                    $(_this).popover('hide');
                });
            }).on("mouseleave", function () {
                var _this = this;
                setTimeout(function () {
                    if (!$(".popover:hover").length) {
                        $(_this).popover("hide")
                    }
                }, 100);
            });
        });
    });

    function getLitigantAgent(e) {

        var name = $(e).attr("litigant_name");
        var position = $(e).attr("litigant_position");
        var authCode = $(e).attr("litigant_authCode");

        return '<table class="table table-bordered">' +
                    '<tr><td style="text-align:left;width:30%" >姓名</td><td style="text-align: left;width:70%">' + name + '</td></tr>' +
                    '<tr><td style="text-align:left;width:30%">身份</td><td style="text-align: left;width:70%">' + position + '</td></tr>' +
                    '<tr><td style="text-align:left;width:30%">代理权限</td><td style="text-align: left;width:70%">' + authCode + '</td></tr>' +
                '</table>';
    }

    function getStaff(e) {

        var name = $(e).attr("staff_chname");
        var mobilephone = $(e).attr("staff_mobilephone");
        var email = $(e).attr("staff_email");

        return '<table class="table table-bordered">' +
                    '<tr><td style="text-align:left;width:30%" >姓名</td><td style="text-align: left;width:70%">' + name + '</td></tr>' +
                    '<tr><td style="text-align:left;width:30%">手机</td><td style="text-align: left;width:70%">' + mobilephone + '</td></tr>' +
                    '<tr><td style="text-align:left;width:30%">Email</td><td style="text-align: left;width:70%">' + email + '</td></tr>' +
                '</table>';
    }

    function getCourt(e) {
        var court_name = $(e).attr("court_name");
        var judge_name = $(e).attr("court_judge_name") == undefined ? '' : $(e).attr("court_judge_name");
        var judge_phone = $(e).attr("court_judge_phone") == undefined ? '' : $(e).attr("court_judge_phone");
        var judge_email = $(e).attr("court_judge_email") == undefined ? '' : $(e).attr("court_judge_email");

        var clerk_name = $(e).attr("court_clerk_name") == undefined ? '' : $(e).attr("court_clerk_name");
        var clerk_phone = $(e).attr("court_clerk_phone") == undefined ? '' : $(e).attr("court_clerk_phone");
        var clerk_email = $(e).attr("court_clerk_email") == undefined ? '' : $(e).attr("court_clerk_email");

        return '<table class="table table-bordered">' +
                    '<tr><td style="text-align:left;width:20%" >法院</td><td  style="text-align: left;width:80%">' + (court_name == '' ? '无' : court_name) + '</td></tr>' +
                    '<tr><td style="text-align:left;width:20%">主审法官</td><td  style="text-align: left;width:80%">' + (judge_name == '' ? '无' : judge_name) + ', 电话:' + judge_phone + ' Email:' + judge_email + '</td></tr>' +
                    '<tr><td style="text-align:left;width:20%">书记员</td><td  style="text-align: left;width:80%">' + (clerk_name == '' ? '无' : clerk_name) + ', 电话:' + clerk_phone + ' Email:' + clerk_email + '</td>' +
                '</table>';
    }

    $(document).click(function () {
        $("#divCaseFileTypeList").off().hide();
        $("#divCaseTaskTypeList").off().hide();
        $("#divCaseFeeTypeList").off().hide();
        $("#divCaseFeeTypeList").off().hide();
        $("#divAssociatePaymentTypeList_CaseFee").off().hide();

        $(".popover").off().hide();
        
    });

    $(document).off('click', '#btnCaseFileCreate').on('click', '#btnCaseFileCreate', function () {
        c.Cases.Case.CaseFiles.CaseFile.Open();
    });

    $(document).off('click', '#btnCaseCreate').on('click', '#btnCaseCreate', function () {
        c.Cases.Case.CreateUpdate(c.Cases.Case.CreateUpdate_NextStep);
    });

    $(document).off('click', '#divCaseFileTypeList ul li').on('click', '#divCaseFileTypeList ul li', function (i, e) {
        var caseFileTypeId = $(this).find("a").attr("id");
        var caseFileTypeName = $(this).find("a").text();
        var caseFileTypeNameText = $(this).find("a").attr("text");
        var currentSelectedControl = $("#hidCaseFileTypeName").val();
        var currentSelectedIdControl = $("#hidCaseFileTypeId").val();
        $("#" + currentSelectedControl).val(caseFileTypeName);
        $("#" + currentSelectedIdControl).val(caseFileTypeId);

        var hedgingFileTypeId = $(this).find("a").attr("hedgingFileTypeId");
        var hedgingFeeTypeId = $(this).find("a").attr("hedgingFeeTypeId");

        //caseInfo.CaseFile.ProcessFileTypeSelectedCallBack(caseFileTypeId, caseFileTypeNameText, hedgingFileTypeId, hedgingFeeTypeId);

        $("#divCaseFileTypeList").hide();

        return true;
    });

    $(document).off('click', '#lnkCaseOfficeFileTypeId').on('click', '#lnkCaseOfficeFileTypeId', function (e) {
        var tirgger = $("#CaseFileTypeName");
        if ($("#IsTransformedFile").val() == 'true') {
            $(".divCaseFileTypeList").html($.lsCaseFileType.getCaseTransformedFileTypeListHtml($("#Case_Basic_CaseTypeId").val()));
        } else {
            $(".divCaseFileTypeList").html($.lsCaseFileType.getCaseOfficeFileTypeListHtml($("#Case_Basic_CaseTypeId").val()));
        }
        $("#divCaseFileTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left + 15,
            "top": $(tirgger).offsetParent().position().top + 32
        }).toggle();

        $("#hidCaseFileTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFileTypeId").val($("#CaseFileTypeId").attr("id")); //Id

        return false;
    });

    $(document).off('click', '#lnkCaseNonOfficeFileTypeId').on('click', '#lnkCaseNonOfficeFileTypeId', function (e) {
        var tirgger = $("#CaseFileTypeName");
        if ($("#IsTransformedFile").val() == 'true') {
            $(".divCaseFileTypeList").html($.lsCaseFileType.getCaseTransformedFileTypeListHtml($("#Case_Basic_CaseTypeId").val()));
        } else {
            $(".divCaseFileTypeList").html($.lsCaseFileType.getCaseNonOfficeFileTypeListHtml($("#Case_Basic_CaseTypeId").val()));
        }
        $("#divCaseFileTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left + 15,
            "top": $(tirgger).offsetParent().position().top + 32
        }).toggle();

        $("#hidCaseFileTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFileTypeId").val($("#CaseFileTypeId").attr("id")); //Id

        return false;
    });

    $(document).off('click', '#btnCaseFileUploading').on('click', '#btnCaseFileUploading', function (e) {
        c.Cases.Case.CaseFiles.CaseFile.CreateUpdate();
    });

    $(document).off('click', '#flCaseFile').on('change', '#flCaseFile', function (e) {
        $("#txtCaseFilePath").val($("#flCaseFile").val());
    });

    //$(document).off('click', '#btnCaseFileDelete').on('click', '#btnCaseFileDelete', function (e) {
    //    var caseFileIds = $.checkbox.vals("chkFileId");
    //    if (caseFileIds.length == 0) {
    //        $.showModalMessageBox("请选择文件.");
    //        return false;
    //    }
    //    c.Cases.Case.CaseFiles.CaseFile.Delete(caseFileIds);
    //});

    $(document).off('click', '#btnCaseFileTypeIdChange').on('click', '#btnCaseFileTypeIdChange', function (e) {
        var caseFileIds = $.checkbox.vals("chkFileId");
        if (caseFileIds.length == 0) {
            $.showModalMessageBox("请选择文件.");
            return false;
        }
        c.Cases.Case.CaseFiles.CaseFile.FileType.Open(caseFileIds);
    });

    $(document).off('click', '#btnCaseFileTypeChanged').on('click', '#btnCaseFileTypeChanged', function (e) {
        var caseFileIds = $.checkbox.vals("chkFileId");

        if (caseFileIds.length == 0) {
            $.showModalMessageBox("请选择文件.");
            return false;
        }
        c.Cases.Case.CaseFiles.CaseFile.FileType.Change(caseFileIds);
    });

    $(document).off('click', '#btnCasePhaseTypeChanged').on('click', '#btnCasePhaseTypeChanged', function (e) {
        var caseNos = new Array($('#Case_Basic_CaseNo').val());
        c.Cases.Case.CasePhases.CasePhase.Change(caseNos);
    });

    $(document).off('click', '#btnCaseFileList').on('click', '#btnCaseFileList', function (e) {
        $("li", '.nav.nav-tabs').each(function (i, e) {
            $(e).removeClass("active");
        });
        $(this).parent().addClass("active");
        if ($("#PageNo").length) {
            $("#PageNo").val(1);
            $("#PageSize").val(10);
        }
        c.Cases.Case.CaseFiles.Layout();
    });

    $(document).off('click', '#btnARCaseFeeList').on('click', '#btnARCaseFeeList', function (e) {
        $("li", '.nav.nav-tabs').each(function (i, e) {
            $(e).removeClass("active");
        });
        $(this).parent().addClass("active");
        if ($("#PageNo").length) {
            $("#PageNo").val(1);
            $("#PageSize").val(10);
        }
        c.Cases.Case.CaseFees.List();
    });

    $(document).off('click', '#btnInternalFeeList').on('click', '#btnInternalFeeList', function (e) {
        $("li", '.nav.nav-tabs').each(function (i, e) {
            $(e).removeClass("active");
        });
        $(this).parent().addClass("active");
        if ($("#PageNo").length) {
            $("#PageNo").val(1);
            $("#PageSize").val(10);
        }
        c.Cases.Case.InternalFees.List();
    });

    $(document).off('click', '#btnCaseLogList').on('click', '#btnCaseLogList', function (e) {
        $("li", '.nav.nav-tabs').each(function (i, e) {
            $(e).removeClass("active");
        });
        $(this).parent().addClass("active");
        if ($("#PageNo").length) {
            $("#PageNo").val(1);
            $("#PageSize").val(10);
        }
        c.Cases.Case.CaseLogs.OperatingLogList();
    });

    $(document).off('click', '#btnCaseTaskList').on('click', '#btnCaseTaskList', function (e) {
        $("li", '.nav.nav-tabs').each(function (i, e) {
            $(e).removeClass("active");
        });
        $(this).parent().addClass("active");
        if ($("#PageNo").length) {
            $("#PageNo").val(1);
            $("#PageSize").val(10);
        }
        c.Cases.Case.CaseTasks.List();
    });

    $(document).off('click', '#btnCaseClueList').on('click', '#btnCaseClueList', function (e) {
        $("li", '.nav.nav-tabs').each(function (i, e) {
            $(e).removeClass("active");
        });
        $(this).parent().addClass("active");
        if ($("#PageNo").length) {
            $("#PageNo").val(1);
            $("#PageSize").val(10);
        }
        c.Cases.Case.CaseClues.List();
    });

    $(document).off('click', '#btnVipCaseTaskList').on('click', '#btnVipCaseTaskList', function (e) {
        $("li", '.nav.nav-tabs').each(function (i, e) {
            $(e).removeClass("active");
        });
        $(this).parent().addClass("active");
        if ($("#PageNo").length) {
            $("#PageNo").val(1);
            $("#PageSize").val(10);
        }
        c.Cases.Case.VipCaseTasks.List();
    });


    $(document).off('click', '#btnCaseLogCreate').on('click', '#btnCaseLogCreate', function (e) {
        //新增日志
        c.Cases.Case.CaseLogs.CaseLog.Open(new Array($('#Case_Basic_CaseNo').val()));
    });

    $(document).off('click', '#btnCaseEventCreate').on('click', '#btnCaseEventCreate', function (e) {
        //新增提醒
        c.Cases.Case.CaseEvents.CaseEvent.Open();
    });

    //$(document).off('click', '#btnCaseTaskCreate').on('click', '#btnCaseTaskCreate', function (e) {
    //    //新增任务
    //    c.Cases.Case.CaseTasks.CaseTask.Open();
    //});

    $(document).off('click', '#btnCaseTask').on('click', '#btnCaseTask', function (e) {
        //新增任务
        c.Cases.Case.CaseTasks.CaseTask.CreateUpdate();
    });

    $(document).off('click', '#btnCaseTaskEdit').on('click', '#btnCaseTaskEdit', function () {
        /*列表选中修改*/
        var taskNos = $.checkbox.vals("chkTaskId");
        if (taskNos.length == 0) {
            $.showModalMessageBox("请选择案件任务.");
            return false;
        }
        var taskId = taskNos[0];
        c.Cases.Case.CaseTasks.CaseTask.Open(taskId);
    });

    $(document).off('click', '#spanCaseCourt').on('click', '#spanCaseCourt', function () {
        if ($(this).hasClass("icon-down")) {
            $("#divCourt").show();
            $(this).removeClass("icon-down")
            $(this).addClass("icon-up")
        }
        else if ($(this).hasClass("icon-up")) {
            $("#divCourt").hide();
            $(this).removeClass("icon-up")
            $(this).addClass("icon-down")
        }
        c.ResetSize();
    });

    $(document).off('click', '#spanProcuratorateUnit').on('click', '#spanProcuratorateUnit', function () {
        if ($(this).hasClass("icon-down")) {
            $("#divProcuratorateUnit").show();
            $(this).removeClass("icon-down")
            $(this).addClass("icon-up")
        }
        else if ($(this).hasClass("icon-up")) {
            $("#divProcuratorateUnit").hide();
            $(this).removeClass("icon-up")
            $(this).addClass("icon-down")
        }
        c.ResetSize();
    });

    $(document).off('click', '#spanCasePublicSecurityUnit').on('click', '#spanCasePublicSecurityUnit', function () {
        if ($(this).hasClass("icon-down")) {
            $("#divPublicSecurityUnit").show();
            $(this).removeClass("icon-down")
            $(this).addClass("icon-up")
        }
        else if ($(this).hasClass("icon-up")) {
            $("#divPublicSecurityUnit").hide();
            $(this).removeClass("icon-up")
            $(this).addClass("icon-down")
        }
        c.ResetSize();
    });

    $(document).off('click', '#lnkCaseFeeTypeIdForOffice').on('click', '#lnkCaseFeeTypeIdForOffice', function () {
        var tirgger = $("#CaseFee_CaseFeeTypeName");
        $(".divCaseFeeTypeList").html($.lsCaseFeeType.getCaseOfficeFeeTypeListHtml($("#Case_Basic_CaseTypeId").val()));
        $("#divCaseFeeTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left + 15,
            "top": $(tirgger).offsetParent().position().top + 32,
            "z-index": 1200
        }).toggle();

        $("#hidCaseFeeTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFeeTypeId").val($("#CaseFee_CaseFeeTypeId").attr("id")); //Id
        $("#hidCaseFeeTypeTypeId").val($("#CaseFee_FeeTypeId").attr("id")); //Id

        return false;
    });

    $(document).off('click', '#lnkCaseFeeTypeIdForNonOffice').on('click', '#lnkCaseFeeTypeIdForNonOffice', function () {
        var tirgger = $("#CaseFee_CaseFeeTypeName");
        $(".divCaseFeeTypeList").html($.lsCaseFeeType.getCaseNonOfficeFeeTypeListHtml($("#Case_Basic_CaseTypeId").val()));
        $("#divCaseFeeTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left + 15,
            "top": $(tirgger).offsetParent().position().top + 32,
            "z-index": 1200
        }).toggle();

        $("#hidCaseFeeTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFeeTypeId").val($("#CaseFee_CaseFeeTypeId").attr("id")); //Id
        $("#hidCaseFeeTypeTypeId").val($("#CaseFee_FeeTypeId").attr("id")); //Id

        return false;
    });

    $(document).off('click', '#lnkCaseFeeTypeIdForOther').on('click', '#lnkCaseFeeTypeIdForOther', function () {
        var tirgger = $("#CaseFee_CaseFeeTypeName");
        $(".divCaseFeeTypeList").html($.lsCaseFeeType.getCaseOtherFeeTypeListHtml($("#Case_Basic_CaseTypeId").val()));
        $("#divCaseFeeTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left + 15,
            "top": $(tirgger).offsetParent().position().top + 32,
            "z-index": 1200
        }).toggle();

        $("#hidCaseFeeTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFeeTypeId").val($("#CaseFee_CaseFeeTypeId").attr("id")); //Id
        $("#hidCaseFeeTypeTypeId").val($("#CaseFee_FeeTypeId").attr("id")); //Id

        return false;
    });

    $(document).off('click', '#lnkCaseFeeTypeIdForInternal').on('click', '#lnkCaseFeeTypeIdForInternal', function () {
        var tirgger = $("#InternalFee_FeeTypeName");
        $(".divCaseFeeTypeList").html($.lsCaseFeeType.getCaseInternalFeeTypeListHtml($("#Case_Basic_CaseTypeId").val()));
        $("#divCaseFeeTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left + 15,
            "top": $(tirgger).offsetParent().position().top + 32,
            "z-index": 1200
        }).toggle();

        $("#hidCaseFeeTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFeeTypeId").val($("#InternalFee_FeeTypeId").attr("id")); //Id
        $("#hidCaseFeeTypeTypeId").val("hidCaseFeeTypeTypeId"); //Id

        return false;
    });

    $(document).off('click', '#divCaseFeeTypeList ul li').on('click', '#divCaseFeeTypeList ul li', function (i, e) {
        var caseFeeTypeId = $(this).find("a").attr("id");
        var caseFeeTypeTypeId = $(this).find("a").attr("typeId");
        var caseFeeTypeName = $(this).find("a").text();
        var caseFeeTypeNameText = $(this).find("a").attr("text");
        var currentSelectedControl = $("#hidCaseFeeTypeName").val();
        var currentSelectedIdControl = $("#hidCaseFeeTypeId").val();
        var currentSelectedTypeIdControl = $("#hidCaseFeeTypeTypeId").val();

        $("#" + currentSelectedControl).val(caseFeeTypeName);
        $("#" + currentSelectedIdControl).val(caseFeeTypeId);
        $("#" + currentSelectedTypeIdControl).val(caseFeeTypeTypeId);

        $("#divCaseFeeTypeList").hide();
    });

    $(document).off('click', '#btnCaseFeeCreateUpdate').on('click', '#btnCaseFeeCreateUpdate', function (e) {
        c.Cases.Case.CaseFees.CaseFee.CreateUpdate();
    });

    $(document).off('click', '#btnCaseFeeCreate').on('click', '#btnCaseFeeCreate', function (e) {
        c.Cases.Case.CaseFees.CaseFee.Open();
    });

    $(document).off('click', '#btnCaseFeeEdit').on('click', '#btnCaseFeeEdit', function (e) {
        var chkCaseFeeIds = $.checkbox.vals("chkCaseFeeId");
        if (chkCaseFeeIds.length == 0) {
            $.showModalMessageBox("请选择费用.");
            return false;
        }
        c.Cases.Case.CaseFees.CaseFee.Edit(chkCaseFeeIds[0]);
    });

    $(document).off('click', '#btnCaseFeePayment').on('click', '#btnCaseFeePayment', function (e) {
        var chkCaseFeeIds = $.checkbox.vals("chkCaseFeeId");
        if (chkCaseFeeIds.length == 0) {
            $.showModalMessageBox("请选择费用.");
            return false;
        }
        c.Cases.Case.CaseFees.PaymentApply.Open();
    });

    $(document).off('click', '#btnCaseFeeInvoice').on('click', '#btnCaseFeeInvoice', function (e) {
        var chkCaseFeeIds = $.checkbox.vals("chkCaseFeeId");
        if (chkCaseFeeIds.length == 0) {
            $.showModalMessageBox("请选择费用.");
            return false;
        }
        c.Cases.Case.CaseFees.Invoice.Apply();
    });

    $(document).off('click', '#btnCaseFeeRefound').on('click', '#btnCaseFeeRefound', function (e) {
        var chkCaseFeeIds = $.checkbox.vals("chkCaseFeeId");
        if (chkCaseFeeIds.length == 0) {
            $.showModalMessageBox("请选择费用.");
            return false;
        }
        c.Cases.Case.CaseFees.Refound.Open(chkCaseFeeIds[0]);
    });

    /*内部费用*/
    $(document).off('click', '#btnInternalFeeMultiCreateUpdate').on('click', '#btnInternalFeeMultiCreateUpdate', function (e) {
        
        c.Cases.Case.InternalFees.InternalFee.MultiCreateUpdate();
    });

    /*内部费用*/
    $(document).off('click', '#btnInternalFeeCreate').on('click', '#btnInternalFeeCreate', function (e) {
        c.Cases.Case.InternalFees.InternalFee.MultiOpen(new Array($('#Case_Basic_CaseNo').val()));
    });

    $(document).off('click', '#btnInternalFeeCreateUpdate').on('click', '#btnInternalFeeCreateUpdate', function (e) {
        c.Cases.Case.InternalFees.InternalFee.CreateUpdate();
    });

    $(document).off('click', '#btnInternalFeeEdit').on('click', '#btnInternalFeeEdit', function (e) {
        var internalFeeIds = $.checkbox.vals("chkInternalFeeId");
        if (internalFeeIds.length == 0) {
            $.showModalMessageBox("请选择费用.");
            return false;
        }
        c.Cases.Case.InternalFees.InternalFee.Edit(internalFeeIds[0]);
    });

    $(document).off('click', '#btnInternalFeeDelete').on('click', '#btnInternalFeeDelete', function (e) {
        var internalFeeIds = $.checkbox.vals("chkInternalFeeId");
        if (internalFeeIds.length == 0) {
            $.showModalMessageBox("请选择费用.");
            return false;
        }
        c.Cases.Case.InternalFees.InternalFee.Delete(internalFeeIds);
    });

    $(document).off('click', '#btnInternalFeePayment').on('click', '#btnInternalFeePayment', function (e) {
        var chkCaseFeeIds = $.checkbox.vals("chkInternalFeeId");
        if (chkCaseFeeIds.length == 0) {
            $.showModalMessageBox("请选择费用.");
            return false;
        }
        c.Cases.Case.InternalFees.PaymentApply.Open();
    });

    $(document).off('change', '.internalFeeType').on('change', '.internalFeeType', function (e) {

        var target = $(this).parent().parent();

        $(target).find(".item_PaymentObjectName_Input").removeAttr("disabled");
        $(target).find(".item_PaymentObjectName_Input").css("width", "100%");

        $(target).find(".item_PaymentObjectName_Input").prevAll().remove();

        if ($(this).val() == '11040040') {
            if ($(this).attr("caselawyer") == '' || $(this).attr("caselawyer") == null) {
                $(target).find(".item_PaymentObjectName_Input").attr("disabled", "disabled");
                return false;
            }
            else {
                var caseLawyers = $(this).attr("caselawyer").split(",");
                var caseLawyerNames = $(this).attr("caselawyername").split(",");
                $.each(caseLawyers, function (i, lawyer) {
                    c.Cases.Case.InternalFees.InternalFee.Objects.PaymentObject.AddIn(target, lawyer, caseLawyerNames[i], false)
                });
            }
        }
        else if ($(this).val() == '11040030') {
            if ($(this).attr("caseassistant") == '' || $(this).attr("caseassistant") == null) {
                $(target).find(".item_PaymentObjectName_Input").attr("disabled", "disabled");
                return false;
            }
            else {
                var caseAssistants = $(this).attr("caseassistant").split(",");
                var caseAssistantNames = $(this).attr("caseassistantname").split(",");
                $.each(caseAssistants, function (i, assistant) {
                    c.Cases.Case.InternalFees.InternalFee.Objects.PaymentObject.AddIn(target, assistant, caseAssistantNames[i], false)
                });
            }
        }
        else if ($(this).val() == '11040070') {

            if ($(this).attr("caseinvestigator") == '' || $(this).attr("caseinvestigator") == null) {
                $(target).find(".item_PaymentObjectName_Input").attr("disabled", "disabled");
                return false;
            }
            else {
                var caseInvestigators = $(this).attr("caseinvestigator").split(",");
                var caseInvestigatorNames = $(this).attr("caseinvestigatorname").split(",");
                $.each(caseInvestigators, function (i, investigator) {
                    c.Cases.Case.InternalFees.InternalFee.Objects.PaymentObject.AddIn(target, investigator, caseInvestigatorNames[i], false)
                });
            }
        }
        else if ($(this).val() == '11040020') {
            if ($(this).attr("casebusinessowner") == '' || $(this).attr("casebusinessowner") == null) {
                $(target).find(".item_PaymentObjectName_Input").attr("disabled", "disabled");
                return false;
            }
            else {
                var caseBusinessOwners = $(this).attr("casebusinessowner").split(",");
                var caseBusinessOwnerNames = $(this).attr("casebusinessownername").split(",");
                $.each(caseBusinessOwners, function (i, businessOwner) {
                    
                    c.Cases.Case.InternalFees.InternalFee.Objects.PaymentObject.AddIn(target, businessOwner, caseBusinessOwnerNames[i], false)
                });
            }
        }
    });

    $(document).off('change', '.caseFeeType').on('change', '.caseFeeType', function (e) {
        var target = $(this).parent().parent();
        if ($(this).val() == '11010020' || $(this).val() == '11010030' || $(this).val() == '11010040' || $(this).val() == '11010090') {
            var remark = "法院号:" + ($(this).attr("officialNo") == '' ? "无" : $(this).attr("officialNo")) + ";费用类型: " + $(this).find("option:selected").text();
            $(target).find(".item_Remark").val(remark);
        }
        else if ($(this).val() == '11010050') {
            var remark = "公证号:" + ($(this).attr("notarialnos") == '' ? "无" : $(this).attr("notarialnos")) + ";费用类型: " + $(this).find("option:selected").text();
            $(target).find(".item_Remark").val(remark);
        }
        else {
            $(target).find(".item_Remark").val('');
        }
    });

    $(document).off('click', '.paymentobjectremove').on('click', '.paymentobjectremove', function () {
        //if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
        //    return false;
        //}
        c.Cases.Case.InternalFees.InternalFee.Objects.PaymentObject.Remove(this);
    });

    $(document).off('click', '.casefeepaymentobjectremove').on('click', '.casefeepaymentobjectremove', function () {
        //if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
        //    return false;
        //}
        
        c.Cases.Case.CaseFees.Payment.Objects.PaymentObject.Remove(this);
    });

    $(window).resize(function () {
        c.ResetSize();
    });

});