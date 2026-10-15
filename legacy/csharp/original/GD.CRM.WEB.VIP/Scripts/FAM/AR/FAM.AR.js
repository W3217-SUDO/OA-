function AssociateCustomer(div, ctlid, ctlname, ctlcustomername) {
    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;

    this.Customer = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") { return false; }
        var curobj = new Object();
        curobj.keyword = name;
        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CRM/Customer/AllCustomerList", curobj, function (response) {
            $(div).find(".i_common_list").empty();
            if (response.IsSuccess) {
                if (response.Data) {
                    var html = "";
                    $.each(response.Data.Customers, function (i, c) {
                        html += '<a href="javascript:void(0)" customerno=' + c.CustomerBasic.CustomerNo + ' >' + c.CustomerBasic.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").click(function () {
                        $(ctlid).val($(this).attr("customerNo"));
                        $(ctlname).val($(this).text());
                        $(ctlcustomername).val($(this).text());

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
            "left": $(ctlname).parents().position().left,
            "top": $(ctlname).parents().position().top + 30
        }).toggle();
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
                //$(this).val("");
            }
        }
        //        if (event.data.obj.GlobalName != "") {
        //            $(this).val(event.data.obj.GlobalName);
        //            $(ctlid).val(event.data.obj.GlobalID);
        //        }
    });

    return this;
}
 
var payment = {
    ResetSize: function () {
        if ($("#divContextList").length > 0) {
            $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 22);
        }

        if ($("#divPaymentList").length > 0) {
            $("#divPaymentList").css("height", $(window).height() - $("#divPaymentList").offset().top - 12);
        }
    },
    Payment: {
        ViewContract: function (contractId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FCM/Contract/ContractView?contractId=" + contractId;
            addtabs(url, '合同查看');
            //window.open(url);
        },
        Create: function (contractId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/AR/PaymentCreate?contractId=" + contractId;
            addtabs(url, '新增回款');
            //window.open(url);
        },
        View: function (paymentId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/AR/PaymentView?paymentId=" + paymentId;
            addtabs(url, '查看回款');
            //window.open(url);
        },
        Edit: function (paymentId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/AR/PaymentEdit?paymentId=" + paymentId;
            addtabs(url, '编辑回款');
            //window.open(url);
        },
        Apply: function (paymentId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/AR/PaymentApply?paymentId=" + paymentId;
            addtabs(url, '分配回款');
            //window.open(url);
        },
        Applied: function (paymentId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/AR/PaymentApplied?paymentId=" + paymentId;
            addtabs(url, '查看已分配回款');
            //window.open(url);
        },
        AppliedObjects: function (e, paymentId) {
            if ($(e).parent().parent().next().find("#tblAppliedObjects").length > 0) {
                $(e).find("span").attr('class', 'fa fa-plus-circle');
                $(e).parent().parent().next().remove();
                return false;
            }
            $(e).find("span").attr('class', 'fa fa-minus-circle');
            var data = { paymentId: paymentId };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentObjectAppliedList", data, function (response) {
                if (response.IsSuccess) {
                    if (response.Data != null && response.Data.length > 0) {
                        var table = "<table id='tblAppliedObjects' class='table table-hover' style='padding:0px;margin:0px'>"
                            + "                 <colgroup>"
                            + "                     <col style='width:3%'>"
                            + "                     <col style='width:3%'>"
                            + "                     <col style='width:8%'>"
                            + "                     <col style='width:10%'>"
                            + "                     <col style='width:8%'>"
                            + "                     <col style='width:8%'>"
                            + "                     <col style='width:8%'>"
                            + "                     <col style='width:8%'>"
                            + "                     <col style='width:8%'>"
                            + "                     <col style='width:12%'>"
                            + "                     <col style='width:8%'>"
                            + "                     <col style='width:8%'>"
                            + "                     <col style='width:15%'>"
                            + "                     <col style='width:8%'>"
                            + "                     <col style='width:8%'>"
                            + "                     <col style='width:10%'>"
                            + "                </colgroup>"
                            + "              <thead> "
                            + "                  <tr> "
                            + "                    <th style='text-align: center;vertical-align: middle;'>序<br>号</th> "
                            + "                    <th style='text-align: center;vertical-align: middle;'>选<br>择</th> "
                            + "                    <th style='text-align: center;vertical-align: middle;'>操<br>作</th> "
                            + "                    <th style='text-align: center;vertical-align: middle;'>案号</th>"
                            + "                    <th style='text-align: center;vertical-align: middle;'>阶段</th> "
                            + "                    <th style='text-align: center;vertical-align: middle;'>费用<br>类型</th> "
                            + "                    <th style='text-align: center;vertical-align: middle;'>费用<br>总金额</th> "
                            + "                    <th style='text-align: center;vertical-align: middle;'>费用<br>分配金额</th> "
                            + "                    <th style='text-align: center;vertical-align: middle;'>本笔<br>分配金额</th> "
                            + "                    <th style='text-align: center;vertical-align: middle;'>本笔<br>分配日期</th> "
                            + "                    <th style='text-align: center;vertical-align: middle;'>本笔<br>结算金额</th> "
                            + "                    <th style='text-align: center;vertical-align: middle;'>本笔<br>归档费</th> "
                            + "                    <th style='text-align: center;vertical-align: middle;'>客户</th>"
                            + "                    <th style='text-align: center;vertical-align: middle;'>经办<br>律师</th>"
                            + "                    <th style='text-align: center;vertical-align: middle;'>律师<br>助理</th>"
                            + "                    <th style='text-align: center;vertical-align: middle;'>合同号</th> "
                            + "                  </tr> "
                            + "               </thead> "
                            + "      <tbody> ";

                       
                        $.each(response.Data, function (i, f) {
                            var tr = "    <tr style=''> "
                                + "            <td style='text-align:center'>" + (i + 1) + "</td>"
                                + "            <td style='text-align:center'><input type = 'checkbox' id = 'chkCaseId' name = 'chkCaseId' value = " + f.Case.Basic.CaseNo + "></td> "
                                + "            <td style='text-align:center'>"
                                + "                 <a style='color:#18bc9c' onclick=\"javascript:c.Cases.Case.CaseTasks.CaseTask.OpenTask('" + f.CaseNo + "');\"><span class='fa fa-envelope' title='新建任务'></span></a>"
                                + "                 <a style='color:#18bc9c' onclick=\"javascript:c.Cases.Case.CaseFiles.CaseFile.SettlementList.Create(new Array('" + f.CaseNo + "'));\"><span class='fa fa-book' title='导出结算清单'></span></a>"
                                + "                 <a style='color:#18bc9c' onclick=\"javascript:payment.Payment.Settlement.ExportSelectedToExcel(new Array('" + f.CaseNo + "'));\"><span class='fa fa-table' title='导出结算列表'></span></a>"
                                + "            </td>"
                                + "            <td style='text-align:center'><a onclick=\"javascript:c.Cases.Case.View('" + f.CaseNo + "');\">" + f.CaseNo + "</a></td>"
                                + "            <td style='text-align:center'>" + f.Case.Basic.CasePhaseName + "</td>"
                                + "            <td style='text-align:left'>" + f.CaseFee.CaseFeeTypeName + "</td>"
                                + "            <td style='text-align:left'>" + f.CaseFee.Amount + "</td>"
                                + "            <td style='text-align:left'>" + f.CaseFee.CashedAmount + "</td>"
                                + "            <td style='text-align:left'>" + f.CaseFeePayAmount + "</td>"
                                + "            <td style='text-align:center'>" + (f.CashedDate == null ? '' : getDateTime(convertJsonDateToJSDate(f.CashedDate))) + "</td>"
                                + "            <td style='text-align:left'>" + f.SettlementAmount + "</td>"
                                + "            <td style='text-align:left'>" + f.ArchiveAmount + "</td>"
                                + "            <td style='text-align:left'>" + f.Case.Basic.CustomerName + "</td>"
                                + "            <td style='text-align:left'>" + f.Case.Basic.CaseLawyerName + "</td>"
                                + "            <td style='text-align:left'>" + f.Case.Basic.CaseAssistantName + "</td>"
                                + "            <td style='text-align:center'><a onclick=\"javascript:contract.Contracts.Contract.View('" + f.CaseFee.ContractNo + "');\">" + f.CaseFee.ContractNo + "</a></td>"
                                + "       </tr>";

                            table += tr;
                        });

                        table += "   </tbody>";
                        table += " </table>";
                        $(e).parent().parent().after("<tr><td colspan='15' style='text-align:right;padding-left:0%;padding-top:0px;padding-bottom:0px;padding-right:0%;'>" + table + "</td></tr>");
                    }
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        Push: function (paymentId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FAM/AR/PaymentPush?paymentId=" + paymentId;
            addtabs(url, '领取回款');
            //window.open(url);
        },
        Delete: function (paymentId) {

            var data = { paymentId: paymentId };

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentDelete", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("删除成功.");
                    payment.List.PaymentList();
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        PaymentApply: function () {
            var dataIsNOk = false;

            var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
            if (caseFeeIds.length == 0) {
                $.showModalMessageBox("请选择未分配的费用信息.");
                return false;
            }

            var data = {};

            data["Payment.PaymentBasic.PaymentId"] = $("#Payment_PaymentBasic_PaymentId").val();

            var i = 0;

            $("#tblARObjectList>tbody>tr").each(function (j, e) {
                if ($(e).css("display") != 'none' && $(e).find("#chkCaseFeeId").length > 0) {

                    if ($(e).find("#chkCaseFeeId").prop("checked") == true && $(e).find("#item_CaseFeePayAmount").val() == '0') {
                        dataIsNOk = true;
                        $.showModalMessageBox("第" + (j + 1) + "行,请录入本次回款金额.");
                        return false;
                    }

                    if ($(e).find("#item_CaseFeePayAmount") == '' || !$(e).find("#item_CaseFeePayAmount").isMoney()) {
                        dataIsNOk = true;
                        $.showModalMessageBox("第" + (j + 1) + "行,输入的不是数字金额.");
                        return false;
                    }

                    if ($(e).find("#chkCaseFeeId").prop("checked") == true) {

                        data["Payment.PaymentObjects[" + i + "].CaseId"] = $(e).find("#chkCaseFeeId").attr("caseId");
                        data["Payment.PaymentObjects[" + i + "].CaseNo"] = $(e).find("#chkCaseFeeId").attr("caseNo");
                        data["Payment.PaymentObjects[" + i + "].CaseFeeId"] = $(e).find("#chkCaseFeeId").attr("caseFeeId");
                        data["Payment.PaymentObjects[" + i + "].CaseFeePayAmount"] = $(e).find("#item_CaseFeePayAmount").val();
                        data["Payment.PaymentObjects[" + i + "].IsRefund"] = $(e).find("#chkCaseFeeId").attr("isRefund");

                        i++;
                    }
                }
            });

            if (dataIsNOk) return false;
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentApply", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("回款分配成功.");
                    payment.Payment.Objects.List();
                    $("#Payment_PaymentBasic_AppliedAmount").text(response.Data.PaymentBasic.AppliedAmount);
                    $("#Payment_PaymentBasic_UnAppliedAmount").text(response.Data.PaymentBasic.UnAppliedAmount);

                } else {
                    $.showModalMessageBox(response.Message);
                }
            });

        },
        PaymentAppliedCancel: function () {
            var dataIsNOk = false;
            var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
            if (caseFeeIds.length == 0) {
                $.showModalMessageBox("请选择已分配的费用信息.");
                return false;
            }

            var data = {};
            data["Payment.PaymentBasic.PaymentId"] = $("#Payment_PaymentBasic_PaymentId").val();
            var i = 0;
            $("#tblARObjectList>tbody>tr").each(function (j, e) {
                if ($(e).css("display") != 'none' && $(e).find("#chkCaseFeeId").length > 0) {

                    if ($(e).find("#chkCaseFeeId").prop("checked") == true) {
                        data["Payment.PaymentObjects[" + i + "].SeqId"] = $(e).find("#chkCaseFeeId").attr("seqId");
                        data["Payment.PaymentObjects[" + i + "].CaseId"] = $(e).find("#chkCaseFeeId").attr("caseId");
                        data["Payment.PaymentObjects[" + i + "].CaseNo"] = $(e).find("#chkCaseFeeId").attr("caseNo");
                        data["Payment.PaymentObjects[" + i + "].CaseFeeId"] = $(e).find("#chkCaseFeeId").attr("caseFeeId");
                        i++;
                    }
                }
            });

            if (dataIsNOk) return false;
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentAppliedCancel", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("回款取消分配成功.");
                    payment.Payment.Objects.AppliedList();
                    $("#Payment_PaymentBasic_AppliedAmount").text(response.Data.PaymentBasic.AppliedAmount);
                    $("#Payment_PaymentBasic_UnAppliedAmount").text(response.Data.PaymentBasic.UnAppliedAmount);

                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },
        TotalAmountSet: function () {
            var totalAmount = 0;
            $("input[name='item_CaseOfficeFeeCashAmount']").each(
                function () {
                    if ($(this).val() == '') {
                        $(this).val(0);
                    }
                    totalAmount += parseFloat($(this).val());
                }
            );
            $("input[name='item_CaseNonOfficeFeeCashAmount']").each(
                function () {
                    if ($(this).val() == '') {
                        $(this).val(0);
                    }
                    totalAmount += parseFloat($(this).val());
                }
            );
            $("input[name='item_CaseCommissionFeeCashAmount']").each(
                function () {
                    if ($(this).val() == '') {
                        $(this).val(0);
                    }
                    totalAmount += parseFloat($(this).val());
                }
            );

            var totalAmount = totalAmount + ($("#Payment_PaymentBasic_PrePaidAmount").val() == '' ? 0 : parseFloat($("#Payment_PaymentBasic_PrePaidAmount").val()));
            // $("#Payment_PaymentBasic_CashedAmount").val(totalAmount);

            $("input[name='Payment.PaymentBasic.CashedAmount']").each(
                function () {
                    $(this).val(totalAmount);
                }
            );

            //$("#Payment_PaymentBasic_TotalAmount").val(totalAmount);
        },
        Registration: {
            CreateUpdate: function (isCreateNextOne) {
                try {

                    if (!$("#Payment_PaymentBasic_CashedAmount").isMoney()) {
                        $.showModalMessageBox("回款金额格式不正确.");
                        return false;
                    }

                    if ($("#Payment_PaymentBasic_PayerName").val() == '') {
                        $.showModalMessageBox("请输入回款单位.");
                        return false;
                    }

                    if (!$("#Payment_PaymentBasic_CashedAmount").isMoney()) {
                        $.showModalMessageBox("回款金额格式不正确.");
                        return false;
                    }

                    if ($("#Payment_PaymentBasic_CashedAmount").val() == '' || parseFloat($("#Payment_PaymentBasic_CashedAmount").val()) == 0) {
                        $.showModalMessageBox("回款金额不能为零.");
                        return false;
                    }

                    if ($("#Payment_PaymentBasic_PaymentModeName").val() == '') {
                        $.showModalMessageBox("请输入回款方式.");
                        return false;
                    }

                    if ($("#Payment_PaymentBasic_InvoiceNo").val() == '') {
                        $.showModalMessageBox("请输入银行单号.");
                        return false;
                    }

                    var data = {};

                    data["Payment.PaymentBasic.PaymentId"] = $("#Payment_PaymentBasic_PaymentId").val();
                    data["Payment.PaymentBasic.PayerName"] = $("#Payment_PaymentBasic_PayerName").val();
                    data["Payment.PaymentBasic.SequenceNo"] = $("#Payment_PaymentBasic_SequenceNo").val();
                    data["Payment.PaymentBasic.CustomerNo"] = $("#Payment_PaymentBasic_CustomerNo").val();
                    data["Payment.PaymentBasic.CustomerName"] = $("#Payment_PaymentBasic_CustomerName").val();
                    data["Payment.PaymentBasic.CashedDate"] = $("#Payment_PaymentBasic_CashedDate").val();
                    data["Payment.PaymentBasic.CashedAmount"] = $("#Payment_PaymentBasic_CashedAmount").val();
                    data["Payment.PaymentBasic.PaymentMode"] = $("#Payment_PaymentBasic_PaymentMode").val();
                    data["Payment.PaymentBasic.PaymentModeName"] = $("#Payment_PaymentBasic_PaymentModeName").val();
                    data["Payment.PaymentBasic.InvoiceNo"] = $("#Payment_PaymentBasic_InvoiceNo").val();
                    data["Payment.PaymentBasic.ContractNo"] = $("#Payment_PaymentBasic_ContractNo").val();

                    data["Payment.PaymentBasic.Remark"] = $("#Payment_PaymentBasic_Remark").val();

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentCreateUpdate", data, function (response) {
                        if (response.IsSuccess) {

                            $.showModalMessageBox("提交成功");

                            if (isCreateNextOne) {
                                window.location = AP_ROOT + AP_PAGE_ID + "/FAM/AR/PaymentCreate";
                            }
                            else {
                                window.location = AP_ROOT + "/5001001002/FAM/AR/PaymentList";
                            }

                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {

                }
            },
            Push: function () {
                try {

                    if ($("#Payment_PaymentBasic_CustomerName").val() == '') {
                        $.showModalMessageBox("请输入客户关键字,选取客户.");
                        return false;
                    }

                    if ($("#Payment_PaymentBasic_CustomerNo").val() == '') {
                        $.showModalMessageBox("请输入客户关键字,选取客户.");
                        return false;
                    }

                    var data = {};

                    data["Payment.PaymentBasic.PaymentId"] = $("#Payment_PaymentBasic_PaymentId").val();
                    data["Payment.PaymentBasic.CustomerNo"] = $("#Payment_PaymentBasic_CustomerNo").val();
                    data["Payment.PaymentBasic.ContractNo"] = $("#Payment_PaymentBasic_ContractNo").val();
                    data["Payment.PaymentBasic.CustomerName"] = $("#Payment_PaymentBasic_CustomerName").val();
                    data["Payment.PaymentBasic.ReceivedRemark"] = $("#Payment_PaymentBasic_ReceivedRemark").val();

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentPush", data, function (response) {
                        if (response.IsSuccess) {
                            $.showModalMessageBox("提交成功.");
                            window.location = AP_ROOT + AP_PAGE_ID + "/FAM/AR/PaymentApply?PaymentId=" + $("#Payment_PaymentBasic_PaymentId").val();
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {

                }
            },
            CreateUpdateCallBack: function (isSubmit) {
                window.location = AP_ROOT + AP_PAGE_ID + "/FAM/AR/PaymentList";
            },
        },
        Objects: {
            List: function () {
                $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/AR/PaymentObjectList", function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_List").empty();
                        $("#dv_List").html(response.Data);

                        $(".pull-right.page-box.paymentList").cPaging({
                            totalCount: parseInt($("#TotalCount").val()),
                            pageNo: parseInt($("#PageNo").val()),
                            pageSize: parseInt($("#PageSize").val()),
                            callBack: payment.Payment.Objects.List,
                            callBackArgs: null
                        });

                        var totalCount = parseInt($("#TotalCount").val());
                        if (totalCount > 0) {
                            $("tfoot", "#tblARObjectList").show();
                            $(".simple-grid-none-data-wrap").hide();
                        } else {
                            $("tfoot", "#tblARObjectList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }

                        $.closeLoading();
                    }
                }, true);
            },
            AppliedList: function () {
                $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/AR/PaymentObjectAppliedList", function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_List").empty();
                        $("#dv_List").html(response.Data);

                        $(".pull-right.page-box.paymentList").cPaging({
                            totalCount: parseInt($("#TotalCount").val()),
                            pageNo: parseInt($("#PageNo").val()),
                            pageSize: parseInt($("#PageSize").val()),
                            callBack: payment.Payment.Objects.AppliedList,
                            callBackArgs: null
                        });

                        var totalCount = parseInt($("#TotalCount").val());

                        if (totalCount > 0) {
                            $("tfoot", "#tblARObjectList").show();
                            $(".simple-grid-none-data-wrap").hide();
                        } else {
                            $("tfoot", "#tblARObjectList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }

                        $.closeLoading();
                    }
                }, true);
            },
            ObjectItem: {
                Selected: function (e) {
                    if ($(e).prop("checked") == true) {
                        $.checkbox.all("chkCaseFeeId");

                        $("input[name='chkCaseFeeId']").each(function (j, e) {

                            if ($(e).attr("disabled") == "disabled") {
                                $(e).prop("checked", '');
                            }
                        });

                    } else {
                        $.checkbox.not("chkCaseFeeId");
                    }
                },
                Apply: function (e) {
                    var caseFeePayAmount = $(e).parents("tr").find("#item_CaseFeePayAmount");
                    if ($(e).prop("checked") == true) {
                        $(caseFeePayAmount).val($(caseFeePayAmount).attr("casefeeuncashedamount") == undefined ? "0" : $(caseFeePayAmount).attr("casefeeuncashedamount"));
                        $(e).parents("tr").find("#chkCaseFeeId").prop("checked", "checked");
                    } else {
                        $(caseFeePayAmount).val(0);
                        $(e).parents("tr").find("#chkCaseFeeId").prop("checked", '');
                    }
                }
            }
        },
        //生成单据号
        GenerateInvoiceNo: function () {
            var date = new Date().Format("yyMMdd");
            var r = parseInt(Math.random() * (99999 - 10000 + 1) + 10000, 10);

            return date + "-" + r;
        },
        Settlement: {
            ToAudit: function (paymentIds) {
                if (paymentIds.length == 0)
                {
                    $.showTips("请选择回款.", 0, 3);
                    return false;
                }
                var data = {};
                var url = AP_ROOT + AP_PAGE_ID + "/FAM/Settlement/ToAuditCreate";
                $.openLoading();
                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#settlementToAuditModel').modal({ backdrop: 'static', keyboard: false });
                    $('#settlementToAuditModel').on('hidden.bs.modal', function () {
                        $("#settlementToAuditModel").remove();
                    });

                    $(document).off('click', '#btnSettlementToAuditCreate').on('click', '#btnSettlementToAuditCreate', function () {
                        var result = payment.Payment.Settlement.ToAuditCallBack(paymentIds, $("#Settlement_Remark").val());
                    });
                });
                return true;
            },
            ToAuditCallBack: function (paymentIds) {
                try {
                    var data = {
                        paymentIds: paymentIds.join(","),
                        settlementRemark: $("#Settlement_Remark").val()
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Settlement/ToAudit", data, function (response) {
                        if (response.IsSuccess) {
                            $.showTips("提交成功.", 0, 3);
                            $('#settlementToAuditModel').modal('hide');
                            try {
                                payment.Payment.Settlement.PendingList();
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
            PendingList: function () {
                $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentList", function (response) {
                    if (response.IsSuccess) {
                        
                        $("tbody", "#tblPaymentList").clearRow();
                        if (response.Data.TotalItemCount > 0) {
                            $(".info_inall.layoutfix").show();

                            $("tbody", "#tblPaymentList").addRow(
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                response.Data.TotalAmount,
                                response.Data.TotalAppliedAmount,
                                response.Data.TotalUnAppliedAmount,
                                response.Data.TotalCaseOfficeFeeAppliedAmount,
                                response.Data.TotalCaseNonOfficeFeeAppliedAmount,
                                response.Data.TotalCaseCommissionFeeAppliedAmount,
                                "",
                                "",
                                "",
                                ""
                            );
                            $.each(response.Data.PaymentList, function (i, c) {
                                $("tbody", "#tblPaymentList").addRow(
                                    "<input type='checkbox' id='chkPaymentId' name='chkPaymentId' value=" + c.PaymentBasic.PaymentId + ">",
                                    "<a style='color:#18bc9c' onclick=\"javascript:payment.Payment.AppliedObjects(this,'" + c.PaymentBasic.PaymentId + "');\"><span class='fa fa-plus-circle' title='查看分配记录'></span></a>"
                                    + " &nbsp;"
                                    + "<a  style='color:#18bc9c' onclick =\"javascript:payment.Payment.Settlement.ToAudit(new Array('" + c.PaymentBasic.PaymentId + "'));\"><span class='fa fa-arrow-up'  title='申请结算'></span></a>"
                                    + " &nbsp;"
                                    + "<a  style='color:#18bc9c' onclick =\"javascript:payment.Payment.Settlement.ExportSettlementManifest(new Array('" + c.PaymentBasic.PaymentId + "'));\"><span class='fa fa-book'  title='导出结算清单'></span></a>",
                                    c.PaymentBasic.CustomerName,
                                    c.PaymentBasic.CustomerOwnerName,
                                    c.PaymentBasic.PayerName,
                                    c.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.CashedDate)),
                                    c.PaymentBasic.CashedAmount,
                                    c.PaymentBasic.AppliedAmount,
                                    c.PaymentBasic.UnAppliedAmount,
                                    c.PaymentBasic.CaseOfficeFeeAppliedAmount,
                                    c.PaymentBasic.CaseNonOfficeFeeAppliedAmount,
                                    c.PaymentBasic.CaseCommissionFeeAppliedAmount,
                                    c.PaymentBasic.CaseNonOfficeFeeSettlementAmount,
                                    c.PaymentBasic.CaseFeeArchiveAmount,
                                    c.PaymentBasic.CaseFeeSettlementAmount
                                );
                                $("tbody", "#tblPaymentList").append("<tr><td></td>"
                                    + "<td>银行备注:</td><td colspan='13' style='text-align: left'>" + c.PaymentBasic.Remark + "</td>"
                                    + "</tr> ");

                            });

                            $("tfoot", "#tblPaymentList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.paymentList").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: payment.Payment.Settlement.PendingList,
                                callBackArgs: null
                            });
                        } else {
                            $("tfoot", "#tblPaymentList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                        payment.ResetSize();
                    }
                });
            },
            ProcessingList: function () {
                $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentList", function (response) {
                    if (response.IsSuccess) {
                        
                        $("tbody", "#tblPaymentList").clearRow();

                        if (response.Data.TotalItemCount > 0) {

                            $(".info_inall.layoutfix").show();

                            $("tbody", "#tblPaymentList").addRow(
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                response.Data.TotalAmount,
                                response.Data.TotalAppliedAmount,
                                response.Data.TotalUnAppliedAmount,
                                response.Data.TotalCaseOfficeFeeAppliedAmount,
                                response.Data.TotalCaseNonOfficeFeeAppliedAmount,
                                response.Data.TotalCaseCommissionFeeAppliedAmount,
                                "",
                                "",
                                "",
                                ""
                            );

                            $.each(response.Data.PaymentList, function (i, c) {
                                $("tbody", "#tblPaymentList").addRow(
                                    "<input type='checkbox' id='chkPaymentId' name='chkPaymentId' value=" + c.PaymentBasic.PaymentId + ">",
                                    "<a style='color:#18bc9c' onclick=\"javascript:payment.Payment.AppliedObjects(this,'" + c.PaymentBasic.PaymentId + "');\"><span class='fa fa-plus-circle' title='查看分配记录'></span></a>"
                                    + " &nbsp;"
                                    + "<a style='color:#18bc9c' onclick =\"javascript:payment.Payment.Settlement.Approved(new Array('" + c.PaymentBasic.PaymentId + "'));\"><span class='fa fa-check-circle'  title='同意结算'></span></a>"
                                    + " &nbsp;"
                                    + "<a  style='color:#18bc9c' onclick =\"javascript:payment.Payment.Settlement.ExportSettlementManifest(new Array('" + c.PaymentBasic.PaymentId + "'));\"><span class='fa fa-book'  title='导出结算清单'></span></a>",
                                    c.PaymentBasic.CustomerName,
                                    c.PaymentBasic.CustomerOwnerName,
                                    c.PaymentBasic.PayerName,
                                    c.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.CashedDate)),
                                    c.PaymentBasic.CashedAmount,
                                    c.PaymentBasic.AppliedAmount,
                                    c.PaymentBasic.UnAppliedAmount,
                                    c.PaymentBasic.CaseOfficeFeeAppliedAmount,
                                    c.PaymentBasic.CaseNonOfficeFeeAppliedAmount,
                                    c.PaymentBasic.CaseCommissionFeeAppliedAmount,
                                    c.PaymentBasic.CaseNonOfficeFeeSettlementAmount,
                                    c.PaymentBasic.CaseFeeArchiveAmount,
                                    c.PaymentBasic.CaseFeeSettlementAmount
                                );

                                $("tbody", "#tblPaymentList").append("<tr><td></td>"
                                    + "<td>提交人:</td><td style='text-align: left'>" + c.PaymentBasic.SettlementToAuditBusinessOwnerName + "</td>"
                                    + "<td>提交时间:</td><td style='text-align: left'>" + (c.PaymentBasic.SettlementToAuditDate == null ? "" : getDateTime(convertJsonDateToJSDate(c.PaymentBasic.SettlementToAuditDate))) + "</td>"
                                    + "<td>提交备注:</td><td style='text-align: left' colspan='9'>" + c.PaymentBasic.SettlementRemark + "</td>"
                                    + "</tr> ");
                            });

                            $("tfoot", "#tblPaymentList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.paymentList").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: payment.Payment.Settlement.ProcessingList,
                                callBackArgs: null
                            });
                        } else {
                            $("tfoot", "#tblPaymentList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                        payment.ResetSize();
                    }
                });
            },
            PendingPaymentList: function () {
                $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentList", function (response) {
                    if (response.IsSuccess) {
                        $("tbody", "#tblPaymentList").clearRow();
                        if (response.Data.TotalItemCount > 0) {
                            $(".info_inall.layoutfix").show();

                            $("tbody", "#tblPaymentList").addRow(
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                response.Data.TotalAmount,
                                response.Data.TotalAppliedAmount,
                                response.Data.TotalUnAppliedAmount,
                                response.Data.TotalCaseOfficeFeeAppliedAmount,
                                response.Data.TotalCaseNonOfficeFeeAppliedAmount,
                                response.Data.TotalCaseCommissionFeeAppliedAmount,
                                response.Data.TotalCaseNonOfficeFeeSettlementAmount,
                                response.Data.TotalCaseFeeArchiveAmount,
                                response.Data.TotalCaseFeeSettlementAmount
                            );
                            $.each(response.Data.PaymentList, function (i, c) {
                                $("tbody", "#tblPaymentList").addRow(
                                    "<input type='checkbox' id='chkPaymentId' name='chkPaymentId' value=" + c.PaymentBasic.PaymentId + ">",
                                    "<a style='color:#18bc9c' onclick=\"javascript:payment.Payment.AppliedObjects(this,'" + c.PaymentBasic.PaymentId + "');\"><span class='fa fa-plus-circle' title='查看分配记录'></span></a>"
                                    + " &nbsp;"
                                    + "<a  style='color:#18bc9c' onclick =\"javascript:payment.Payment.Settlement.ExportSettlementManifest(new Array('" + c.PaymentBasic.PaymentId + "'));\"><span class='fa fa-book'  title='导出结算清单'></span></a>"
                                    + " &nbsp;"
                                    + "<a  style='color:#18bc9c' onclick =\"javascript:payment.Payment.Settlement.Rollback(new Array('" + c.PaymentBasic.PaymentId + "'));\"><span class='fa fa-reply'  title='回退结算'></span></a>"
                                    + " &nbsp;"
                                    + "<a  style='color:#18bc9c' onclick =\"javascript:payment.Payment.Settlement.Paid(new Array('" + c.PaymentBasic.PaymentId + "'));\"><span class='fa fa-share'  title='标记已支付'></span></a>",
                                    c.PaymentBasic.CustomerName,
                                    c.PaymentBasic.CustomerOwnerName,
                                    c.PaymentBasic.PayerName,
                                    c.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.CashedDate)),
                                    c.PaymentBasic.CashedAmount,
                                    c.PaymentBasic.AppliedAmount,
                                    c.PaymentBasic.UnAppliedAmount,
                                    c.PaymentBasic.CaseOfficeFeeAppliedAmount,
                                    c.PaymentBasic.CaseNonOfficeFeeAppliedAmount,
                                    c.PaymentBasic.CaseCommissionFeeAppliedAmount,
                                    c.PaymentBasic.CaseNonOfficeFeeSettlementAmount,
                                    c.PaymentBasic.CaseFeeArchiveAmount,
                                    c.PaymentBasic.CaseFeeSettlementAmount
                                );

                                $("tbody", "#tblPaymentList").append("<tr style='background-color: #99CC66'><td></td>"
                                    + "<td>审核人:</td><td style='text-align: left'>" + c.PaymentBasic.SettlementAuditorName + "</td>"
                                    + "<td>审核时间:</td><td style='text-align: left'>" + (c.PaymentBasic.SettlementAuditDate == null ? "" : getDateTime(convertJsonDateToJSDate(c.PaymentBasic.SettlementAuditDate))) + "</td>"
                                    + "<td>审核备注:</td><td style='text-align: left' colspan='2'>" + c.PaymentBasic.SettlementAuditRemark + "</td>"
                                    + "<td>提交人:</td><td style='text-align: left'>" + c.PaymentBasic.SettlementToAuditBusinessOwnerName + "</td>"
                                    + "<td>提交时间:</td><td style='text-align: left'>" + (c.PaymentBasic.SettlementToAuditDate == null ? "" : getDateTime(convertJsonDateToJSDate(c.PaymentBasic.SettlementToAuditDate))) + "</td>"
                                    + "<td>提交备注:</td><td style='text-align: left' colspan='2'>" + c.PaymentBasic.SettlementRemark + "</td>"
                                    + "</tr> ");
                            });

                            $("tfoot", "#tblPaymentList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.paymentList").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: payment.Payment.Settlement.ProcessedList,
                                callBackArgs: null
                            });
                        } else {
                            $("tfoot", "#tblPaymentList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                        payment.ResetSize();
                    }
                });
            },
            ProcessedList: function () {
                $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentList", function (response) {
                    if (response.IsSuccess) {
                        $("tbody", "#tblPaymentList").clearRow();
                        if (response.Data.TotalItemCount > 0) {
                            $(".info_inall.layoutfix").show();

                            $("tbody", "#tblPaymentList").addRow(
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                response.Data.TotalAmount,
                                response.Data.TotalAppliedAmount,
                                response.Data.TotalUnAppliedAmount,
                                response.Data.TotalCaseOfficeFeeAppliedAmount,
                                response.Data.TotalCaseNonOfficeFeeAppliedAmount,
                                response.Data.TotalCaseCommissionFeeAppliedAmount,
                                response.Data.TotalCaseNonOfficeFeeSettlementAmount,
                                response.Data.TotalCaseFeeArchiveAmount,
                                response.Data.TotalCaseFeeSettlementAmount
                            );
                            $.each(response.Data.PaymentList, function (i, c) {
                                $("tbody", "#tblPaymentList").addRow(
                                    "<input type='checkbox' id='chkPaymentId' name='chkPaymentId' value=" + c.PaymentBasic.PaymentId + ">",
                                    "<a style='color:#18bc9c' onclick=\"javascript:payment.Payment.AppliedObjects(this,'" + c.PaymentBasic.PaymentId + "');\"><span class='fa fa-plus-circle' title='查看分配记录'></span></a>"
                                    + " &nbsp;"
                                    + "<a  style='color:#18bc9c' onclick =\"javascript:payment.Payment.Settlement.ExportSettlementManifest(new Array('" + c.PaymentBasic.PaymentId + "'));\"><span class='fa fa-book'  title='导出结算清单'></span></a>"
                                    + " &nbsp;"
                                    + "<a  style='color:#18bc9c' onclick =\"javascript:payment.Payment.Settlement.Rollback(new Array('" + c.PaymentBasic.PaymentId + "'));\"><span class='fa fa-reply'  title='回退结算'></span></a>",
                                    c.PaymentBasic.CustomerName,
                                    c.PaymentBasic.CustomerOwnerName,
                                    c.PaymentBasic.PayerName,
                                    c.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.CashedDate)),
                                    c.PaymentBasic.CashedAmount,
                                    c.PaymentBasic.AppliedAmount,
                                    c.PaymentBasic.UnAppliedAmount,
                                    c.PaymentBasic.CaseOfficeFeeAppliedAmount,
                                    c.PaymentBasic.CaseNonOfficeFeeAppliedAmount,
                                    c.PaymentBasic.CaseCommissionFeeAppliedAmount,
                                    c.PaymentBasic.CaseNonOfficeFeeSettlementAmount,
                                    c.PaymentBasic.CaseFeeArchiveAmount,
                                    c.PaymentBasic.CaseFeeSettlementAmount
                                );

                                $("tbody", "#tblPaymentList").append("<tr style='background-color: #99CC66'><td></td>"
                                    + "<td>审核人:</td><td style='text-align: left'>" + c.PaymentBasic.SettlementAuditorName + "</td>"
                                    + "<td>审核时间:</td><td style='text-align: left'>" + (c.PaymentBasic.SettlementAuditDate == null ? "" : getDateTime(convertJsonDateToJSDate(c.PaymentBasic.SettlementAuditDate))) + "</td>"
                                    + "<td>审核备注:</td><td style='text-align: left' colspan='2'>" + c.PaymentBasic.SettlementAuditRemark + "</td>"
                                    + "<td>提交人:</td><td style='text-align: left'>" + c.PaymentBasic.SettlementToAuditBusinessOwnerName + "</td>"
                                    + "<td>提交时间:</td><td style='text-align: left'>" + (c.PaymentBasic.SettlementToAuditDate == null ? "" : getDateTime(convertJsonDateToJSDate(c.PaymentBasic.SettlementToAuditDate))) + "</td>"
                                    + "<td>提交备注:</td><td style='text-align: left' colspan='2'>" + c.PaymentBasic.SettlementRemark + "</td>"
                                    + "</tr> ");
                            });

                            $("tfoot", "#tblPaymentList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.paymentList").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: payment.Payment.Settlement.ProcessedList,
                                callBackArgs: null
                            });
                        } else {
                            $("tfoot", "#tblPaymentList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                        payment.ResetSize();
                    }
                });
            },
            RejectedList: function () {
                $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentList", function (response) {
                    if (response.IsSuccess) {
                        
                        $("tbody", "#tblPaymentList").clearRow();

                        if (response.Data.TotalItemCount > 0) {
                            $(".info_inall.layoutfix").show();
                            $("tbody", "#tblPaymentList").addRow(
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                response.Data.TotalAmount,
                                response.Data.TotalAppliedAmount,
                                response.Data.TotalUnAppliedAmount,
                                response.Data.TotalCaseOfficeFeeAppliedAmount,
                                response.Data.TotalCaseNonOfficeFeeAppliedAmount,
                                response.Data.TotalCaseCommissionFeeAppliedAmount,
                                "",
                                "",
                                "",
                                ""
                            );

                            $.each(response.Data.PaymentList, function (i, c) {
                                $("tbody", "#tblPaymentList").addRow(
                                    "<input type='checkbox' id='chkPaymentId' name='chkPaymentId' value=" + c.PaymentBasic.PaymentId + ">",
                                    "<a style='color:#18bc9c' onclick=\"javascript:payment.Payment.AppliedObjects(this,'" + c.PaymentBasic.PaymentId + "');\"><span class='fa fa-plus-circle' title='查看分配记录'></span></a>"
                                    + " &nbsp;"
                                    + "<a  style='color:#18bc9c' onclick =\"javascript:payment.Payment.Settlement.ToAudit(new Array('" + c.PaymentBasic.PaymentId + "'));\"><span class='fa fa-arrow-up'  title='重新申请结算'></span></a>"
                                    + " &nbsp;"
                                    + "<a  style='color:#18bc9c' onclick =\"javascript:payment.Payment.Settlement.ExportSettlementManifest(new Array('" + c.PaymentBasic.PaymentId + "'));\"><span class='fa fa-book'  title='导出结算清单'></span></a>",
                                    c.PaymentBasic.CustomerName,
                                    c.PaymentBasic.CustomerOwnerName,
                                    c.PaymentBasic.PayerName,
                                    c.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.CashedDate)),
                                    c.PaymentBasic.CashedAmount,
                                    c.PaymentBasic.AppliedAmount,
                                    c.PaymentBasic.UnAppliedAmount,
                                    c.PaymentBasic.CaseOfficeFeeAppliedAmount,
                                    c.PaymentBasic.CaseNonOfficeFeeAppliedAmount,
                                    c.PaymentBasic.CaseCommissionFeeAppliedAmount,
                                    c.PaymentBasic.CaseNonOfficeFeeSettlementAmount,
                                    c.PaymentBasic.CaseFeeArchiveAmount,
                                    c.PaymentBasic.CaseFeeSettlementAmount
                                );

                                $("tbody", "#tblPaymentList").append("<tr style='background-color: #f39c12'><td></td>"
                                    + "<td>审核人:</td><td style='text-align: left'>" + c.PaymentBasic.SettlementAuditorName + "</td>"
                                    + "<td>审核时间:</td><td style='text-align: left'>" + (c.PaymentBasic.SettlementAuditDate == null ? "" : getDateTime(convertJsonDateToJSDate(c.PaymentBasic.SettlementAuditDate))) + "</td>"
                                    + "<td>审核备注:</td><td style='text-align: left' colspan='2'>" + c.PaymentBasic.SettlementAuditRemark + "</td>"
                                    + "<td>提交人:</td><td style='text-align: left'>" + c.PaymentBasic.SettlementToAuditBusinessOwnerName + "</td>"
                                    + "<td>提交时间:</td><td style='text-align: left'>" + (c.PaymentBasic.SettlementToAuditDate == null ? "" : getDateTime(convertJsonDateToJSDate(c.PaymentBasic.SettlementToAuditDate))) + "</td>"
                                    + "<td>提交备注:</td><td style='text-align: left' colspan='2'>" + c.PaymentBasic.SettlementRemark + "</td>"
                                    + "</tr> ");

                                //$("tbody", "#tblPaymentList").append("<tr><td></td><td>备注:</td><td colspan='13' style='text-align: left'>" + c.PaymentBasic.Remark + "</td></tr>");

                            });

                            $("tfoot", "#tblPaymentList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.paymentList").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: payment.Payment.Settlement.RejectedList,
                                callBackArgs: null
                            });
                        } else {
                            $("tfoot", "#tblPaymentList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                        payment.ResetSize();
                    }
                });
            },
            Approved: function (paymentIds) {
                if (paymentIds.length == 0)
                {
                    $.showTips("请选择回款.", 0, 3);
                    return false;
                }

                var data = {
               
                };

                var url = AP_ROOT + AP_PAGE_ID + "/FAM/Settlement/AuditApproved";
                $.openLoading();
                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#settlementAuditModel').modal({ backdrop: 'static', keyboard: false });
                    $('#settlementAuditModel').on('hidden.bs.modal', function () {
                        $("#settlementAuditModel").remove();
                    });

                    $(document).off('click', '#btnSettlementAuditApproved').on('click', '#btnSettlementAuditApproved', function () {
                        payment.Payment.Settlement.ToApprovedCallBack(paymentIds, $("#Settlement_Audit_Remark").val());
                    });
                });
                
                return true;
            },
            ToApprovedCallBack: function (paymentIds) {
                try {
                    var data = {
                        paymentIds: paymentIds.join(","),
                        settlementAuditRemark: $("#Settlement_Audit_Remark").val()
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Settlement/Approved", data, function (response) {
                        if (response.IsSuccess) {
                            $.showTips("提交成功.", 0, 3);
                            $('#settlementAuditModel').modal('hide');
                            try {
                                payment.Payment.Settlement.ProcessingList();
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

            Paid: function (paymentIds) {
                if (paymentIds.length == 0) {
                    $.showTips("请选择回款.", 0, 3);
                    return false;
                }

                var data = {

                };

                var url = AP_ROOT + AP_PAGE_ID + "/FAM/Settlement/AuditPaid";
                $.openLoading();
                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#settlementPaidModel').modal({ backdrop: 'static', keyboard: false });
                    $('#settlementPaidModel').on('hidden.bs.modal', function () {
                        $("#settlementPaidModel").remove();
                    });

                    $(document).off('click', '#btnSettlementPaid').on('click', '#btnSettlementPaid', function () {
                        payment.Payment.Settlement.ToPaidCallBack(paymentIds, $("#Settlement_Paid_Remark").val());
                    });
                });

                return true;
            },
            ToPaidCallBack: function (paymentIds) {
                try {
                    var data = {
                        paymentIds: paymentIds.join(","),
                        settlementAuditRemark: $("#Settlement_Paid_Remark").val()
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Settlement/Paid", data, function (response) {
                        if (response.IsSuccess) {
                            $.showTips("提交成功.", 0, 3);
                            $('#settlementPaidModel').modal('hide');
                            try {
                                payment.Payment.Settlement.PendingPaymentList();
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

            Rollback: function (paymentIds) {
                if (paymentIds.length == 0) {
                    $.showTips("请选择回款.", 0, 3);
                    return false;
                }
                var data = {

                };

                var url = AP_ROOT + AP_PAGE_ID + "/FAM/Settlement/AuditRollback";
                $.openLoading();
                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#settlementAuditModel').modal({ backdrop: 'static', keyboard: false });
                    $('#settlementAuditModel').on('hidden.bs.modal', function () {
                        $("#settlementAuditModel").remove();
                    });

                    $(document).off('click', '#btnSettlementAuditRollback').on('click', '#btnSettlementAuditRollback', function () {
                        payment.Payment.Settlement.ToRollbackCallBack(paymentIds, $("#Settlement_Rollback_Remark").val());
                    });
                });
                return true;
            },
            ToRollbackCallBack: function (paymentIds) {
                try {
                    var data = {
                        paymentIds: paymentIds.join(","),
                        settlementRollRemark: $("#Settlement_Rollback_Remark").val()
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Settlement/Rollback", data, function (response) {
                        if (response.IsSuccess) {
                            $.showTips("提交成功.", 0, 3);
                            $('#settlementAuditModel').modal('hide');
                            try {
                                payment.Payment.Settlement.ProcessedList();
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
            Rejected: function (paymentIds) {
                if (paymentIds.length == 0)
                {
                    $.showTips("请选择回款.", 0, 3);
                    return;
                }
                var data = {

                };

                var url = AP_ROOT + AP_PAGE_ID + "/FAM/Settlement/AuditRejected";
                $.openLoading();
                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#settlementAuditModel').modal({ backdrop: 'static', keyboard: false });
                    $('#settlementAuditModel').on('hidden.bs.modal', function () {
                        $("#settlementAuditModel").remove();
                    });

                    $(document).off('click', '#btnSettlementAuditRejected').on('click', '#btnSettlementAuditRejected', function () {
                        payment.Payment.Settlement.ToRejectedCallBack(paymentIds, $("#Settlement_Audit_Remark").val());
                    });
                });
                return true;
            },
            ToRejectedCallBack: function (paymentIds) {
                try {
                    var data = {
                        paymentIds: paymentIds.join(","),
                        settlementAuditRemark: $("#Settlement_Audit_Remark").val()
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Settlement/Rejected", data, function (response) {
                        if (response.IsSuccess) {
                            $.showTips("提交成功.", 0, 3);
                            $('#settlementAuditModel').modal('hide');
                            try {
                                payment.Payment.Settlement.ProcessingList();
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
            ExportSettlementManifest: function (paymentId) {
                var data = { paymentId: paymentId };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentObjectAppliedList", data, function (response) {
                    if (response.IsSuccess) {
                        if (response.Data != null && response.Data.length > 0) {
                            var caseNos = [];
                            $.each(response.Data, function (i, f) {
                                if (caseNos.indexOf(f.Case.Basic.CaseNo) == -1) {
                                    caseNos.push(f.Case.Basic.CaseNo);
                                }
                            });
                            c.Cases.Case.CaseFiles.CaseFile.SettlementList.Create(caseNos);
                        }
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });

            },
            ExportSelectedToExcel: function (caseNos) {
                if (caseNos.length == 0) {

                    $.showTips("请选择案件.", 0, 3);
                    return false;
                }

                var data = {
                    caseNos: caseNos,
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Settlement/SettlementListSelectedExportToExcel", data, function (response) {
                    if (response.IsSuccess) {
                        window.open(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListExportToExcelDownload?fileName=" + response.Data);
                        $.showModalMessageBox("导出成功.");
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },
            /**
             * 到账与明细清单
             */
            ExportSettlementManifestToExcel: function (paymentIds) {
                if (paymentIds.length == 0) {

                    $.showTips("请选择到账.", 0, 3);
                    return false;
                }

                var data = {
                    paymentIds: paymentIds,
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Settlement/ExportSettlementManifestToExcel", data, function (response) {
                    if (response.IsSuccess) {
                        window.open(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListExportToExcelDownload?fileName=" + response.Data);
                        $.showModalMessageBox("导出成功.");
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },
            /**
             * 到账清单
             */
            ExportSettlementHeaderManifestToExcel: function (paymentIds) {
                if (paymentIds.length == 0) {

                    $.showTips("请选择到账.", 0, 3);
                    return false;
                }

                var data = {
                    paymentIds: paymentIds,
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Settlement/ExportSettlementHeaderManifestToExcel", data, function (response) {
                    if (response.IsSuccess) {
                        window.open(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListExportToExcelDownload?fileName=" + response.Data);
                        $.showModalMessageBox("导出成功.");
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },
            /**
             * 明细清单 
             */
            ExportSettlementItemManifestToExcel: function (paymentIds) {
                if (paymentIds.length == 0) {

                    $.showTips("请选择到账.", 0, 3);
                    return false;
                }

                var data = {
                    paymentIds: paymentIds,
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Settlement/ExportSettlementItemManifestToExcel", data, function (response) {
                    if (response.IsSuccess) {
                        window.open(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListExportToExcelDownload?fileName=" + response.Data);
                        $.showModalMessageBox("导出成功.");
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },
           
        },
        ArchiveSettlement: {
            ToAudit: function (paymentObjectIds) {
                if (paymentObjectIds.length == 0) {

                    $.showTips("请选择归档费.", 0, 3);
                    return false;
                }
                var data = {};
                var url = AP_ROOT + AP_PAGE_ID + "/FAM/ArchiveSettlement/ToAuditCreate";
                $.openLoading();
                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#archiveSettlementToAuditModel').modal({ backdrop: 'static', keyboard: false });
                    $('#archiveSettlementToAuditModel').on('hidden.bs.modal', function () {
                        $("#archiveSettlementToAuditModel").remove();
                    });

                    $(document).off('click', '#btnSettlementToAuditCreate').on('click', '#btnSettlementToAuditCreate', function () {
                        payment.Payment.ArchiveSettlement.ToAuditCallBack(paymentObjectIds, $("#Settlement_Remark").val());
                    });
                });
                return true;
            },
            ToAuditCallBack: function (paymentObjectIds) {
                try {
                    var data = {
                        paymentObjectIds: paymentObjectIds.join(","),
                        settlementRemark: $("#Settlement_Remark").val()
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ArchiveSettlement/ToAudit", data, function (response) {
                        if (response.IsSuccess) {
                            $.showTips("提交成功.", 0, 3);
                            $('#archiveSettlementToAuditModel').modal('hide');
                            try {
                                payment.Payment.ArchiveSettlement.PendingList();
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
            PendingList: function () {
                $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentObjectList", function (response) {
                    if (response.IsSuccess) {
                        
                        $("tbody", "#tblPaymentObjectList").clearRow();
                        if (response.Data.TotalItemCount > 0) {
                            $(".info_inall.layoutfix").show();

                            $("tbody", "#tblPaymentObjectList").addRow(
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                response.Data.TotalAppliedAmount,
                                response.Data.TotalArchiveAmount,
                                "",
                                ""
                            );
      
                            $.each(response.Data.PaymentObjectList, function (i, p) {
                                $("tbody", "#tblPaymentObjectList").addRow(
                                    "<input type='checkbox' id='chkPaymentId' name='chkPaymentId' value=" + p.SeqId + ">",
                                    //"<a  style='color:#18bc9c' onclick =\"javascript:payment.Payment.ArchiveSettlement.ToAudit(new Array('" + p.SeqId + "'));\"><span class='fa fa-arrow-up'  title='申请支付'></span></a>"
                                    //+ " &nbsp;&nbsp;" +
                                    "<a style='color:#18bc9c' onclick=\"javascript:c.Cases.Case.CaseTasks.CaseTask.OpenTask('" + p.Case.Basic.CaseNo + "');\"><span class='fa fa-envelope' title='新建任务'></span></a>",
                                    "<a onclick=\"javascript:c.Cases.Case.View('" + p.Case.Basic.CaseNo + "');\">" + p.Case.Basic.CaseNo + "</a>",
                                    p.Case.Basic.CustomerName,
                                    p.Case.Basic.CasePhaseName,
                                    p.Case.Basic.CaseAssistantName,
                                    p.Case.Basic.CaseLawyerName,
                                    p.Payment.PaymentBasic.CustomerOwnerName,
                                    p.CaseFee.CaseFeeTypeName,
                                    p.CaseFee.Amount,
                                    p.Payment.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(p.Payment.PaymentBasic.CashedDate)),
                                    p.CaseFeePayAmount,
                                    p.ArchiveAmount,
                                    p.ArchiveAmountSettlementAuditDate == null ? '' : getDate(convertJsonDateToJSDate(p.ArchiveAmountSettlementAuditDate)),
                                    p.ArchiveAmountSettlementStatusName 
                                );
                            });

                            $("tfoot", "#tblPaymentObjectList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.paymentObjectList").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: payment.Payment.ArchiveSettlement.PendingList,
                                callBackArgs: null
                            });
                        } else {
                            $("tfoot", "#tblPaymentObjectList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                        payment.ResetSize();
                    }
                });
            },
            ProcessingList: function () {
                
                $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentObjectList", function (response) {
                    
                    if (response.IsSuccess) {
                        
                        $("tbody", "#tblPaymentObjectList").clearRow();
                        if (response.Data.TotalItemCount > 0) {
                            $(".info_inall.layoutfix").show();

                            $("tbody", "#tblPaymentObjectList").addRow(
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                response.Data.TotalAppliedAmount,
                                response.Data.TotalArchiveAmount,
                                "",
                                ""
                            );

                            $.each(response.Data.PaymentObjectList, function (i, p) {
                                $("tbody", "#tblPaymentObjectList").addRow(
                                    "<input type='checkbox' id='chkPaymentId' name='chkPaymentId' value=" + p.SeqId + ">",
                                    "<a style='color:#18bc9c' onclick =\"javascript:payment.Payment.ArchiveSettlement.Approved(new Array('" + p.SeqId + "'));\"><span class='fa fa-check-circle'  title='同意支付'></span></a>"
                                    + " &nbsp;"
                                    + "<a style='color:#f39c12' onclick =\"javascript:payment.Payment.ArchiveSettlement.Rejected(new Array('" + p.SeqId + "'));\"><span class='fa fa-times-circle'  title='拒绝支付'></span></a>"
                                    + " &nbsp;"
                                    + "<a style='color:#18bc9c' onclick=\"javascript:c.Cases.Case.CaseTasks.CaseTask.OpenTask('" + p.Case.Basic.CaseNo + "');\"><span class='fa fa-envelope' title='新建任务'></span></a>",
                                    "<a onclick=\"javascript:c.Cases.Case.View('" + p.Case.Basic.CaseNo + "');\">" + p.Case.Basic.CaseNo + "</a>",
                                    p.Case.Basic.CustomerName,
                                    p.Case.Basic.CasePhaseName,
                                    p.Case.Basic.CaseAssistantName,
                                    p.Case.Basic.CaseLawyerName,
                                    p.Payment.PaymentBasic.CustomerOwnerName,
                                    p.CaseFee.CaseFeeTypeName,
                                    p.CaseFee.Amount,
                                    p.Payment.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(p.Payment.PaymentBasic.CashedDate)),
                                    p.CaseFeePayAmount,
                                    p.ArchiveAmount,
                                    p.ArchiveAmountSettlementAuditDate == null ? '' : getDate(convertJsonDateToJSDate(p.ArchiveAmountSettlementAuditDate)),
                                    p.ArchiveAmountSettlementStatusName
                                );
                                $("tbody", "#tblPaymentObjectList").append("<tr style='background-color: #99CC66'><td></td>"
                                    + "<td style='text-align: left'>审核人:</td><td style='text-align: left'>" + p.ArchiveAmountSettlementAuditor + "</td>"
                                    + "<td style='text-align: left'>审核时间:" + (p.ArchiveAmountSettlementAuditDate == null ? "" : getDateTime(convertJsonDateToJSDate(p.ArchiveAmountSettlementAuditDate))) + "</td>"
                                    + "<td style='text-align: left'>审核备注:</td><td style='text-align: left' colspan='2'>" + p.ArchiveAmountSettlementAuditRemark + "</td>"
                                    + "<td style='text-align: left'>提交人:</td><td style='text-align: left'>" + p.ArchiveAmountSettlementToAuditBusinessOwnerName + "</td>"
                                    + "<td style='text-align: left' colspan='2' >提交时间:" + (p.ArchiveAmountSettlementToAuditDate == null ? "" : getDateTime(convertJsonDateToJSDate(p.ArchiveAmountSettlementToAuditDate))) + "</td>"
                                    + "<td style='text-align: left'>提交备注:</td><td style='text-align: left' colspan='3'>" + p.ArchiveAmountSettlementToAuditRemark + "</td>"
                                    + "</tr> ");
                            });

                            $("tfoot", "#tblPaymentObjectList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.paymentObjectList").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: payment.Payment.ArchiveSettlement.ProcessingList,
                                callBackArgs: null
                            });
                        } else {
                            $("tfoot", "#tblPaymentObjectList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                        payment.ResetSize();
                    }
                });
            },
            ProcessedList: function () {
                $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentObjectList", function (response) {
                    if (response.IsSuccess) {
                        
                        $("tbody", "#tblPaymentObjectList").clearRow();
                        if (response.Data.TotalItemCount > 0) {
                            $(".info_inall.layoutfix").show();

                            $("tbody", "#tblPaymentObjectList").addRow(
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                response.Data.TotalAppliedAmount,
                                response.Data.TotalArchiveAmount,
                                "",
                                ""
                            );

                            $.each(response.Data.PaymentObjectList, function (i, p) {
                                $("tbody", "#tblPaymentObjectList").addRow(
                                    "<input type='checkbox' id='chkPaymentId' name='chkPaymentId' value=" + p.SeqId + ">",
                                    "<a style='color:#18bc9c' onclick =\"javascript:payment.Payment.ArchiveSettlement.Rollback(new Array('" + p.SeqId + "'));\"><span class='fa fa-reply'  title='回滚归档费'></span></a>",
                                    "<a onclick=\"javascript:c.Cases.Case.View('" + p.Case.Basic.CaseNo + "');\">" + p.Case.Basic.CaseNo + "</a>",
                                    p.Case.Basic.CustomerName,
                                    p.Case.Basic.CasePhaseName,
                                    p.Case.Basic.CaseAssistantName,
                                    p.Case.Basic.CaseLawyerName,
                                    p.Payment.PaymentBasic.CustomerOwnerName,
                                    p.CaseFee.CaseFeeTypeName,
                                    p.CaseFee.Amount,
                                    p.Payment.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(p.Payment.PaymentBasic.CashedDate)),
                                    p.CaseFeePayAmount,
                                    p.ArchiveAmount,
                                    p.ArchiveAmountSettlementAuditDate == null ? '' : getDate(convertJsonDateToJSDate(p.ArchiveAmountSettlementAuditDate)),
                                    p.ArchiveAmountSettlementStatusName
                                );

                                $("tbody", "#tblPaymentObjectList").append("<tr style='background-color: #99CC66'><td></td>"
                                    + "<td style='text-align: left'>审核人:</td><td style='text-align: left'>" + p.ArchiveAmountSettlementAuditor + "</td>"
                                    + "<td style='text-align: left'>审核时间:" + (p.ArchiveAmountSettlementAuditDate == null ? "" : getDateTime(convertJsonDateToJSDate(p.ArchiveAmountSettlementAuditDate))) + "</td>"
                                    + "<td style='text-align: left'>审核备注:</td><td style='text-align: left' colspan='2'>" + p.ArchiveAmountSettlementAuditRemark + "</td>"
                                    + "<td style='text-align: left'>提交人:</td><td style='text-align: left'>" + p.ArchiveAmountSettlementToAuditBusinessOwnerName + "</td>"
                                    + "<td style='text-align: left' colspan='2' >提交时间:" + (p.ArchiveAmountSettlementToAuditDate == null ? "" : getDateTime(convertJsonDateToJSDate(p.ArchiveAmountSettlementToAuditDate))) + "</td>"
                                    + "<td style='text-align: left'>提交备注:</td><td style='text-align: left' colspan='3'>" + p.ArchiveAmountSettlementToAuditRemark + "</td>"
                                    + "</tr> ");

                            });

                            $("tfoot", "#tblPaymentObjectList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.paymentObjectList").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: payment.Payment.ArchiveSettlement.ProcessedList,
                                callBackArgs: null
                            });
                        } else {
                            $("tfoot", "#tblPaymentObjectList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                        payment.ResetSize();
                    }
                });
            },
            RejectedList: function () {
                $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentObjectList", function (response) {
                    if (response.IsSuccess) {
                        
                        $("tbody", "#tblPaymentObjectList").clearRow();
                        if (response.Data.TotalItemCount > 0) {
                            $(".info_inall.layoutfix").show();

                            $("tbody", "#tblPaymentObjectList").addRow(
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                response.Data.TotalAppliedAmount,
                                response.Data.TotalArchiveAmount,
                                "",
                                ""
                            );

                            $.each(response.Data.PaymentObjectList, function (i, p) {
                                $("tbody", "#tblPaymentObjectList").addRow(
                                    "<input type='checkbox' id='chkPaymentId' name='chkPaymentId' value=" + p.SeqId + ">",
                                    "<a  style='color:#18bc9c' onclick =\"javascript:payment.Payment.ArchiveSettlement.ToAudit(new Array('" + p.SeqId + "'));\"><span class='fa fa-arrow-up'  title='申请支付'></span></a>"
                                    + " &nbsp;&nbsp;"
                                    + "<a style='color:#18bc9c' onclick=\"javascript:c.Cases.Case.CaseTasks.CaseTask.OpenTask('" + p.Case.Basic.CaseNo + "');\"><span class='fa fa-envelope' title='新建任务'></span></a>",
                                    "<a onclick=\"javascript:c.Cases.Case.View('" + p.Case.Basic.CaseNo + "');\">" + p.Case.Basic.CaseNo + "</a>",
                                    p.Case.Basic.CustomerName,
                                    p.Case.Basic.CasePhaseName,
                                    p.Case.Basic.CaseAssistantName,
                                    p.Case.Basic.CaseLawyerName,
                                    p.Payment.PaymentBasic.CustomerOwnerName,
                                    p.CaseFee.CaseFeeTypeName,
                                    p.CaseFee.Amount,
                                    p.Payment.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(p.Payment.PaymentBasic.CashedDate)),
                                    p.CaseFeePayAmount,
                                    p.ArchiveAmount,
                                    p.ArchiveAmountSettlementAuditDate == null ? '' : getDate(convertJsonDateToJSDate(p.ArchiveAmountSettlementAuditDate)),
                                    p.ArchiveAmountSettlementStatusName
                                );
                                $("tbody", "#tblPaymentObjectList").append("<tr style='background-color: #f39c12'><td></td>"
                                  + "<td style='text-align: left'>审核人:</td><td style='text-align: left'>" + p.ArchiveAmountSettlementAuditor + "</td>"
                                  + "<td style='text-align: left'>审核时间:" + (p.ArchiveAmountSettlementAuditDate == null ? "" : getDateTime(convertJsonDateToJSDate(p.ArchiveAmountSettlementAuditDate))) + "</td>"
                                  + "<td style='text-align: left'>审核备注:</td><td style='text-align: left' colspan='2'>" + p.ArchiveAmountSettlementAuditRemark + "</td>"
                                  + "<td style='text-align: left'>提交人:</td><td style='text-align: left'>" + p.ArchiveAmountSettlementToAuditBusinessOwnerName + "</td>"
                                  + "<td style='text-align: left' colspan='2' >提交时间:" + (p.ArchiveAmountSettlementToAuditDate == null ? "" : getDateTime(convertJsonDateToJSDate(p.ArchiveAmountSettlementToAuditDate))) + "</td>"
                                  + "<td style='text-align: left'>提交备注:</td><td style='text-align: left' colspan='3'>" + p.ArchiveAmountSettlementToAuditRemark + "</td>"
                                  + "</tr> ");
                            });

                            $("tfoot", "#tblPaymentObjectList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.paymentObjectList").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: payment.Payment.ArchiveSettlement.RejectedList,
                                callBackArgs: null
                            });
                        } else {
                            $("tfoot", "#tblPaymentObjectList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                        payment.ResetSize();
                    }
                });
            },
            Approved: function (paymentObjectIds) {
                if (paymentObjectIds.length == 0) {
                    $.showTips("请选择归档费.", 0, 3);
                    return false;
                }
                var data = {};
                var url = AP_ROOT + AP_PAGE_ID + "/FAM/ArchiveSettlement/AuditApproved";
                $.openLoading();
                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#archiveSettlementAuditModel').modal({ backdrop: 'static', keyboard: false });
                    $('#archiveSettlementAuditModel').on('hidden.bs.modal', function () {
                        $("#archiveSettlementAuditModel").remove();
                    });

                    $(document).off('click', '#btnSettlementAuditApproved').on('click', '#btnSettlementAuditApproved', function () {
                        payment.Payment.ArchiveSettlement.ToApprovedCallBack(paymentObjectIds, $("#Settlement_Audit_Remark").val());
                    });
                });
                return true;
            },
            ToApprovedCallBack: function (paymentObjectIds, settlementAuditRemark) {
                try {
                    var data = {
                        paymentObjectIds: paymentObjectIds.join(","),
                        settlementAuditRemark: settlementAuditRemark
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ArchiveSettlement/Approved", data, function (response) {
                        if (response.IsSuccess) {
                            
                            $.showTips("提交成功.", 0, 3);
                        
                            $("#archiveSettlementAuditModel").modal('hide');
                            try {
                                payment.Payment.ArchiveSettlement.ProcessingList();
                                
                            }
                            catch (e) {
                                
                                alert(e);
                            }
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });

                } catch (e) {
                    
                    alert(e);

                }
            },
            Rejected: function (paymentObjectIds) {
                if (paymentObjectIds.length == 0) {
                    $.showTips("请选择归档费.", 0, 3);
                    return;
                }
                var data = {};
                var url = AP_ROOT + AP_PAGE_ID + "/FAM/ArchiveSettlement/AuditRejected";
                $.openLoading();
                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#archiveSettlementAuditModel').modal({ backdrop: 'static', keyboard: false });
                    $('#archiveSettlementAuditModel').on('hidden.bs.modal', function () {
                        $("#archiveSettlementAuditModel").remove();
                    });

                    $(document).off('click', '#btnSettlementAuditRejected').on('click', '#btnSettlementAuditRejected', function () {
                        payment.Payment.ArchiveSettlement.ToRejectedCallBack(paymentObjectIds, $("#Settlement_Audit_Remark").val());
                    });
                });
                return true;
            },
            ToRejectedCallBack: function (paymentObjectIds, settlementAuditRemark) {
                try {
                    var data = {
                        paymentObjectIds: paymentObjectIds.join(","),
                        settlementAuditRemark: settlementAuditRemark
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ArchiveSettlement/Rejected", data, function (response) {
                        if (response.IsSuccess) {
                            $.showTips("提交成功.", 0, 3);
                            $("#archiveSettlementAuditModel").hide();
                            try {
                                payment.Payment.ArchiveSettlement.ProcessingList();
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
            Rollback: function (paymentObjectIds) {
                if (paymentObjectIds.length == 0) {
                    $.showTips("请选择归档费.", 0, 3);
                    return false;
                }
                var data = {};
                var url = AP_ROOT + AP_PAGE_ID + "/FAM/ArchiveSettlement/AuditRollback";
                $.openLoading();
                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#archiveSettlementAuditModel').modal({ backdrop: 'static', keyboard: false });
                    $('#archiveSettlementAuditModel').on('hidden.bs.modal', function () {
                        $("#archiveSettlementAuditModel").remove();
                    });

                    $(document).off('click', '#btnSettlementAuditRollback').on('click', '#btnSettlementAuditRollback', function () {
                        payment.Payment.ArchiveSettlement.ToRollbackCallBack(paymentObjectIds, $("#Settlement_Rollback_Remark").val());
                    });
                });
                return true;
            },
            ToRollbackCallBack: function (paymentObjectIds, settlementRollbackRemark) {
                try {
                    var data = {
                        paymentObjectIds: paymentObjectIds.join(","),
                        settlementRollbackRemark: settlementRollbackRemark
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ArchiveSettlement/Rollback", data, function (response) {
                        if (response.IsSuccess) {
                            $.showTips("提交成功.", 0, 3);
                            $("#archiveSettlementAuditModel").hide();
                            try {
                                payment.Payment.ArchiveSettlement.ProcessedList();
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
            ExportSelectedToExcel: function (paymentObjectIds) {
                if (paymentObjectIds.length == 0) {

                    $.showTips("请选择案件.", 0, 3);
                    return false;
                }

                var data = {
                    paymentObjectIds: paymentObjectIds,
                };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Settlement/SettlementObjectListSelectedExportToExcel", data, function (response) {
                    if (response.IsSuccess) {
                        window.open(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/InvestigationClueListExportToExcelDownload?fileName=" + response.Data);
                        $.showModalMessageBox("导出成功.");
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },
        }

    },
    List: {
        //登记
        PaymentList: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();

                        $("tbody", "#tblPaymentList").addRow(
                            "",
                            "",
                            "",
                            "",
                            "",
                            response.Data.TotalAmount,
                            response.Data.TotalAppliedAmount,
                            response.Data.TotalUnAppliedAmount,
                            response.Data.TotalCaseOfficeFeeAppliedAmount,
                            response.Data.TotalCaseNonOfficeFeeAppliedAmount,
                            "",
                            ""
                        );

                        $.each(response.Data.PaymentList, function (i, c) {
                            $("tbody", "#tblPaymentList").addRow(
                                "<input type='checkbox' id='chkPaymentId' name='chkPaymentId' value=" + c.PaymentBasic.PaymentId + ">",
                                c.PaymentBasic.CustomerName,
                                c.PaymentBasic.CustomerOwnerName,
                                c.PaymentBasic.PayerName,
                                c.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.CashedDate)),
                                c.PaymentBasic.CashedAmount,
                                c.PaymentBasic.AppliedAmount,
                                c.PaymentBasic.UnAppliedAmount,
                                c.PaymentBasic.CaseOfficeFeeAppliedAmount,
                                c.PaymentBasic.CaseNonOfficeFeeAppliedAmount,
                                c.PaymentBasic.PaymentModeName,
                                c.PaymentBasic.Remark
                            );
                        });

                        $("tfoot", "#tblPaymentList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.paymentList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: payment.List.PaymentList,
                            callBackArgs: null
                        });
                    } else {
                        $("tfoot", "#tblPaymentList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }

                    payment.ResetSize();
                }
            });
        },
        //公海领取
        PaymentPublicList: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentPublicList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();

                        $("tbody", "#tblPaymentList").addRow(
                            "",
                            "",
                            "",
                            "",
                            "",
                            response.Data.TotalAmount,
                            response.Data.TotalAppliedAmount,
                            response.Data.TotalUnAppliedAmount,
                            response.Data.TotalCaseOfficeFeeAppliedAmount,
                            response.Data.TotalCaseNonOfficeFeeAppliedAmount,
                            "",
                            ""
                        );
                        $.each(response.Data.PaymentList, function (i, c) {
                            $("tbody", "#tblPaymentList").addRow(
                                "<input type='checkbox' id='chkPaymentId' name='chkPaymentId' value=" + c.PaymentBasic.PaymentId + ">",
                                c.PaymentBasic.CustomerName,
                                c.PaymentBasic.CustomerOwnerName,
                                c.PaymentBasic.PayerName,
                                c.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.CashedDate)),
                                c.PaymentBasic.CashedAmount,
                                c.PaymentBasic.AppliedAmount,
                                c.PaymentBasic.UnAppliedAmount,
                                c.PaymentBasic.CaseOfficeFeeAppliedAmount,
                                c.PaymentBasic.CaseNonOfficeFeeAppliedAmount,
                                c.PaymentBasic.PaymentModeName,
                                c.PaymentBasic.Remark
                            );
                        });

                        $("tfoot", "#tblPaymentList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.paymentList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: payment.List.PaymentList,
                            callBackArgs: null
                        });
                    } else {
                        $("tfoot", "#tblPaymentList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }

                    payment.ResetSize();
                }
            });
        },
        //待分配
        PaymentApplyList: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentApplyList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();

                        $("tbody", "#tblPaymentList").addRow(
                            "",
                            "",
                            "",
                            "",
                            "",
                            response.Data.TotalAmount,
                            response.Data.TotalAppliedAmount,
                            response.Data.TotalUnAppliedAmount,
                            response.Data.TotalCaseOfficeFeeAppliedAmount,
                            response.Data.TotalCaseNonOfficeFeeAppliedAmount,
                            "",
                            ""
                        );
                        $.each(response.Data.PaymentList, function (i, c) {
                            $("tbody", "#tblPaymentList").addRow(
                                "<input type='checkbox' id='chkPaymentId' name='chkPaymentId' value=" + c.PaymentBasic.PaymentId + ">",
                                c.PaymentBasic.CustomerName,
                                c.PaymentBasic.CustomerOwnerName,
                                c.PaymentBasic.PayerName,
                                c.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.CashedDate)),
                                c.PaymentBasic.CashedAmount,
                                c.PaymentBasic.AppliedAmount,
                                c.PaymentBasic.UnAppliedAmount,
                                c.PaymentBasic.CaseOfficeFeeAppliedAmount,
                                c.PaymentBasic.CaseNonOfficeFeeAppliedAmount,
                                c.PaymentBasic.PaymentModeName,
                                c.PaymentBasic.Remark
                            );
                        });

                        $("tfoot", "#tblPaymentList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.paymentList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: payment.List.PaymentApplyList,
                            callBackArgs: null
                        });
                    } else {
                        $("tfoot", "#tblPaymentList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                    payment.ResetSize();
                }
            });
        },
        //已分配
        PaymentAppliedList: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/ReceivedPayment/PaymentAppliedList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblPaymentList").clearRow();

                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $("tbody", "#tblPaymentList").addRow(
                            "",
                            "",
                            "",
                            "",
                            "",
                            response.Data.TotalAmount,
                            response.Data.TotalAppliedAmount,
                            response.Data.TotalUnAppliedAmount,
                            response.Data.TotalCaseOfficeFeeAppliedAmount,
                            response.Data.TotalCaseNonOfficeFeeAppliedAmount,
                            "",
                            ""
                        );
                        $.each(response.Data.PaymentList, function (i, c) {
                            $("tbody", "#tblPaymentList").addRow(
                                "<input type='checkbox' id='chkPaymentId' name='chkPaymentId' value=" + c.PaymentBasic.PaymentId + ">",
                                c.PaymentBasic.CustomerName,
                                c.PaymentBasic.CustomerOwnerName,
                                c.PaymentBasic.PayerName,
                                c.PaymentBasic.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.PaymentBasic.CashedDate)),
                                c.PaymentBasic.CashedAmount,
                                c.PaymentBasic.AppliedAmount,
                                c.PaymentBasic.UnAppliedAmount,
                                c.PaymentBasic.CaseOfficeFeeAppliedAmount,
                                c.PaymentBasic.CaseNonOfficeFeeAppliedAmount,
                                c.PaymentBasic.PaymentModeName,
                                c.PaymentBasic.Remark
                            );
                        });

                        $("tfoot", "#tblPaymentList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.paymentList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: payment.List.PaymentAppliedList,
                            callBackArgs: null
                        });
                    } else {
                        $("tfoot", "#tblPaymentList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }

                    payment.ResetSize();
                }
            });
        },
        //
        Selected: function (e) {
            if ($(e).prop('checked') == true) {
                $.checkbox.all("chkPaymentId");
                $.checkbox.all("chkPaymentAll");
                $.checkbox.all("chkCaseId");

            } else {
                $.checkbox.not("chkPaymentId");
                $.checkbox.not("chkPaymentAll");
                $.checkbox.not("chkCaseId");
            }
        },
    }
}

var contract = {
    Contracts: {
        Contract: {
            View: function (contractNo) {
                var url = AP_ROOT + AP_PAGE_ID + "/FCM/Contract/PreView?contractNo=" + contractNo;
                addtabs(url, contractNo);
                //window.open(url);
            },
        },
    },
    List: {
        ContractList: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/Contract/List", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblContractList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.ContractList, function (i, c) {
                            $("tbody", "#tblContractList").addRow(
                                "<a href='javascript:void(0);' onclick='javascript:payment.Payment.Create(" + c.ContractBasicInfo.ContractId + ")'>新增回款</a>&nbsp;&nbsp;",
                                c.ContractBasicInfo.ContractNo,
                                c.ContractBasicInfo.ContractName,
                                c.ContractBasicInfo.ContractStatusName,
                                c.ContractBasicInfo.TotalAmount,
                                c.ContractBasicInfo.CashedAmount,
                                c.ContractBasicInfo.ARAmount,
                                c.ContractBasicInfo.BusinessOwnerName,
                                c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                                c.ContractBasicInfo.CustomerNo,
                                c.ContractBasicInfo.CustomerName
                            );
                        });

                        $("tfoot", "#tblContractList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.contractList").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: contract.List.ContractList,
                            callBackArgs: null
                        });


                    } else {
                        $("tfoot", "#tblContractList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
    }
}

$(document).ready(function () {

    $(window).resize(function () {
        payment.ResetSize();
    });

    var businessOwner = new AssociateUser(
        $("#divAssociateUserList"),
        $("#SearchCondition_BusinessOwner"),
        $("#SearchCondition_BusinessOwnerName"),
        null
    );

    var customter = new AssociateCustomer(
        $("#div_customer"),
        $("#Payment_PaymentBasic_CustomerNo"),
        $("#Payment_PaymentBasic_PayerName"),
        $("#Payment_PaymentBasic_CustomerName")
    );

    var customter = new AssociateCustomer(
        $("#div_customer"),
        $("#Payment_PaymentBasic_CustomerNo"),
        $("#Payment_PaymentBasic_CustomerName"),
        $("#Payment_PaymentBasic_CustomerName")
    );


    $("#divPaymentTypeList").find("li").off().on("click", function () {
        var paymentTypeName = $(this).find("a").attr("name");
        var paymentTypeId = $(this).find("a").attr("paymenttypeid");
        var currentSelectedControl = $("#hidPaymentTypeName").val();
        var currentSelectedControlId = $("#hidPaymentTypeId").val();

        $("#" + currentSelectedControl).val(paymentTypeName);
        $("#" + currentSelectedControlId).val(paymentTypeId);

        $("#divPaymentTypeList").hide();
    });

    $("#Payment_PaymentBasic_PaymentModeName").off().on("click", function () {
        $("#hidPaymentTypeName").val("Payment_PaymentBasic_PaymentModeName");
        $("#hidPaymentTypeId").val("Payment_PaymentBasic_PaymentMode");
        
        $("#divPaymentTypeList").off().css({
            "position": "absolute",
            "left": $("#Payment_PaymentBasic_PaymentModeName").parents().position().left + 0,
            "top": $("#Payment_PaymentBasic_PaymentModeName").parents().position().top + 30,
            "z-index": 1200
        }).show();
        return false;
    });

    $("#SearchCondition_BusinessOwnerName").off().on("click", function () {
        $("#hidUserId").val("SearchCondition_BusinessOwner");
        $("#hidUserName").val("SearchCondition_BusinessOwnerName");
        $("#divUserList").css({
            "position": "absolute",
            "left": $("#SearchCondition_BusinessOwnerName").position().left + 16,
            "top": $("#SearchCondition_BusinessOwnerName").position().top + 70,
            "z-index": 1200
        }).toggle();
        return false;
    });

    $("#divUserList").find("li").off().on("click", function (e) {
        var currentSelectedControl = $("#hidUserName").val();
        var currentSelectedIdControl = $("#hidUserId").val();
        if ($(this).attr("id") == 'btnClear') {
            $("#" + currentSelectedControl).val('');
            $("#" + currentSelectedIdControl).val('');
            return false;
        }
        var userId = $(this).find("a").attr("name");
        var userName = $(this).find("a").text();
        $("#" + currentSelectedControl).val(userName);
        $("#" + currentSelectedIdControl).val(userId);
        $("#divUserList").hide();
        return false;
    });

    $("#lblPaymentType").off().on("click", function () {
        payment.Payment.PaymentType.Open();
    });

    $("#lblInvoiceNo").off().on("click", function () {

        if ($("#Payment_PaymentBasic_InvoiceNo").val() == '')
        {
            var invoiceNo = payment.Payment.GenerateInvoiceNo();
            $("#Payment_PaymentBasic_InvoiceNo").val(invoiceNo);
        }
    });

    $("#btnPaymentTypeCancel,#btnPaymentTypeClose").off().on("click", function () {
        payment.Payment.PaymentType.Close();
    });
    
    $("#btnPaymentTypeSelected").off().on("click", function () {
        payment.Payment.PaymentType.Selected();
    });

    $("input[name='chkPaymentTypeId']").off().on("click", function () {
        payment.Payment.PaymentType.Select(this);
    });

    $(document).off('click', '#item_PaymentApply').on('click', '#item_PaymentApply', function () {
        payment.Payment.Objects.ObjectItem.Apply(this);
    });

    $("#Payment_PaymentBasic_PrePaidAmount").off().on("change", function () {

        if ($(this).val() == '') {
            $(this).val(0);
        }

        var prePaidAmount = parseFloat($("#Customer_CustomerBasic_PrePaidAmount").attr("prepaidamount")) + parseFloat($("#Payment_PaymentBasic_PrePaidAmount").val());
        $("#Customer_CustomerBasic_PrePaidAmount").val(prePaidAmount);

        payment.Payment.TotalAmountSet();
    });
 
    $("#btnPaymentListSearch").off().on("click", function () {
        payment.List.PaymentList();
    });
    $("#btnPaymentPublicListSearch").off().on("click", function () {
        payment.List.PaymentPublicList();
    });
    $("#btnPaymentApplyListSearch").off().on("click", function () {
        payment.List.PaymentApplyList();
    });
    $("#btnPaymentAppliedListSearch").off().on("click", function () {
        payment.List.PaymentAppliedList();
    });

    $(document).off('click', '#btnPaymentPendingListSearch').on('click', '#btnPaymentPendingListSearch', function () {
        payment.Payment.Settlement.PendingList();
    });
    $(document).off('click', '#btnPaymentProcessingListSearch').on('click', '#btnPaymentProcessingListSearch', function () {
        payment.Payment.Settlement.ProcessingList();
    });

    $(document).off('click', '#btnPaymentPendingPaymentListSearch').on('click', '#btnPaymentPendingPaymentListSearch', function () {
        payment.Payment.Settlement.PendingPaymentList();
    });

    $(document).off('click', '#btnPaymentProcessedListSearch').on('click', '#btnPaymentProcessedListSearch', function () {
        payment.Payment.Settlement.ProcessedList();
    });
    $(document).off('click', '#btnPaymentRejectedListSearch').on('click', '#btnPaymentRejectedListSearch', function () {
        
        payment.Payment.Settlement.RejectedList();
    });

    $("#btnPaymentObjectSearch").off().on("click", function () {
        payment.Payment.Objects.List();
    });

    $("#btnPaymentObjectAppliedSearch").off().on("click", function () {
        payment.Payment.Objects.AppliedList();
    });

    $("#btnPaymentCreateUpdate").off().on("click", function () {
        payment.Payment.Registration.CreateUpdate(false);
    });

    $("#btnPaymentCreateAndNextOne").off().on("click", function () {
        payment.Payment.Registration.CreateUpdate(true);
    });

    $(document).off('click', '#chkCaseFeeAll').on('click', '#chkCaseFeeAll', function () {
        payment.Payment.Objects.ObjectItem.Selected(this);
    });
     
    $("#btnPaymentApply").off().on("click", function () {
        payment.Payment.PaymentApply();
    });

    $("#btnPaymentAppliedCancel").off().on("click", function () {
        payment.Payment.PaymentAppliedCancel();
    });

    $("#btnPaymentSearchClear").off().on("click", function () {
        $("#SearchCondition_CustomerName").val('');
        $("#SearchCondition_ContractNo").val('');
        $("#SearchCondition_CaseNo").val('');
        $("#SearchCondition_CaseTypeName").val('');
        $("#SearchCondition_CaseTypeId").val('');
        $("#SearchCondition_CasePhaseName").val('');
        $("#SearchCondition_CasePhaseId").val('');
        $("#SearchCondition_CaseFeeTypeName").val('');
        $("#SearchCondition_CaseFeeTypeId").val('');
    });

    $(document).off('click', '#btnPaymentEdit').on('click', '#btnPaymentEdit', function () {
        /*列表选中修改*/
        var paymentIds = $.checkbox.vals("chkPaymentId");
        if (paymentIds.length == 0) {
            $.showModalMessageBox("请选择回款.");
            return false;
        }
        var paymentId = paymentIds[0];
        payment.Payment.Edit(paymentId);
    });

    $(document).off('click', '#btnPaymentDelete').on('click', '#btnPaymentDelete', function () {
        /*列表选中修改*/
        var paymentIds = $.checkbox.vals("chkPaymentId");
        if (paymentIds.length == 0) {
            $.showModalMessageBox("请选择回款.");
            return false;
        }
        var paymentId = paymentIds[0];
        payment.Payment.Delete(paymentId);
    });

    $(document).off('click', '#btnPaymentListPush').on('click', '#btnPaymentListPush', function () {
        var paymentIds = $.checkbox.vals("chkPaymentId");
        if (paymentIds.length == 0) {
            $.showModalMessageBox("请选择回款.");
            return false;
        }
        var paymentId = paymentIds[0];
      
        payment.Payment.Push(paymentId);
    });

    $(document).off('click', '#btnPaymentListApply').on('click', '#btnPaymentListApply', function () {
        var paymentIds = $.checkbox.vals("chkPaymentId");
        if (paymentIds.length == 0) {
            $.showModalMessageBox("请选择回款.");
            return false;
        }
        var paymentId = paymentIds[0];

        payment.Payment.Apply(paymentId);
    });

    $(document).off('click', '#btnPaymentListApplied').on('click', '#btnPaymentListApplied', function () {
        var paymentIds = $.checkbox.vals("chkPaymentId");
        if (paymentIds.length == 0) {
            $.showModalMessageBox("请选择回款.");
            return false;
        }
        var paymentId = paymentIds[0];

        payment.Payment.Applied(paymentId);
    });

    $(document).off('click', '#btnPaymentPushed').on('click', '#btnPaymentPushed', function () {
        payment.Payment.Registration.Push();
    });

    $(document).off('click', '#chkPaymentAll').on('click', '#chkPaymentAll', function () {
        payment.List.Selected(this);
    });

    $(document).off('click', '#chkPaymentId').on('click', '#chkPaymentId', function () {
        if ($(this).prop('checked') == true) {
           
            $(this).parent().parent().next().find("#tblAppliedObjects").find(":checkbox").each(

                function () { $(this).prop("checked", 'checked'); }
            );
        } else {
            
            $(this).parent().parent().next().find("#tblAppliedObjects").find(":checkbox").each(
                function () { $(this).prop("checked", ''); }
            );
        }
    });

 
});