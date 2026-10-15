var cashed = {
    List: function() {
        $("#postForm").ajaxPost(AP_ROOT + "FAM/Cashed/HistoryList", function(response) {
            if (response.IsSuccess) {
                $("tbody", "#tblCashedList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();
                    $.each(response.Data.CashedList, function(i, c) {
                        $("tbody", "#tblCashedList").addRow(
                            c.CustomerNo,
                            c.CustomerName,
                            c.CashedDate == null ? '' : getDate(convertJsonDateToJSDate(c.CashedDate)),
                            c.Amount,
                            c.Amount - c.AppliedAmount,
                            c.AppliedAmount,
                            c.PaymentModeName,
                            c.BillNo,
                            "<a href='javascript:void(0)' onclick='javascript:cashed.Applied.Open(" + c.CashedId + ")'>分配记录</a>");
                    });

                    $("tfoot", "#tblCashedList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.cashedlist").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: cashed.List,
                        callBackArgs: null
                    });
                } else {

                    $("tfoot", "#tblCashedList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    Applied : {
        Open: function (cashedId) {
            var data = {
                cashedId: cashedId
            };
            var url = AP_ROOT + "FAM/Cashed/AppliedList";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#appliedListModal').modal({ backdrop: 'static', keyboard: false });
                $('#appliedListModal').on('hidden.bs.modal', function () {
                    $("#appliedListModal").remove();
                });
                cashed.Applied.List();
            });
        },

        Close: function () {
            $('#appliedListModal').modal('hide');
        },

        Selected: function (e) {

            if ($(e).attr("checked") == "checked") {
                $.checkbox.all("chkAppliedId");
            }
            else {
                $.checkbox.not("chkAppliedId");
            }
        },

        List: function () {
            $("#appliedListForm").ajaxPost(AP_ROOT + "FAM/Cashed/GetAppliedList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblAppliedList").clearRow();
                    if (response.Data.TotalItemCount > 0) {

                        $.each(response.Data.AppliedList, function (i, e) {
                            $("tbody", "#tblAppliedList").addRow(
                               "<input type='checkbox' name='chkAppliedId' class='ng-pristine ng-valid' value='" + e.AppliedId + "'>",
                                e.ContractNo,
                                e.CaseNo,
                                e.CaseRequestNo,
                                e.CaseFeeTypeName,
                                e.Amount,
                                e.AppliedAmount,
                                e.Confirmor,
                                e.AppliedDate == null ? '' : getDate(convertJsonDateToJSDate(e.AppliedDate))
                                );
                        });

                        $("tfoot", "#tblAppliedList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $("#appliedlistpaging").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: cashed.Applied.List,
                            callBackArgs: null
                        });
                    }
                    else {
                        $("tfoot", "#tblAppliedList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },

        AppliedCancel: function () {

            var appliedIds = new Array();

            $("input[name='chkAppliedId']:checked").each(
                function () {
                    appliedIds.push($(this).val());
                }
            );

            if (appliedIds.length == 0) {
                $.showModalMessageBox("请选择到账分配记录.");
                return false;
            }

            $.showModalConfirmDialog("确定取消到账确认?", 'cashed.Applied.AppliedCancelCallBack', appliedIds, false);
        },

        AppliedCancelCallBack: function (appliedIds) {

            var data = { appliedIds: appliedIds };

            $.ajaxPost(AP_ROOT + "FAM/Cashed/AppliedCancel", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("取消到账分配成功.");
                    cashed.Applied.Close();

                } else {
                    $.showModalMessageBox(response.Message);
                }
            });

        },
    }

};
 

$(document).ready(function() {

    $(document).click(function() {

    });

    $("#btnSearch").die().live("click", function () {
        cashed.List();
    });

    $("#btnAppliedListCancel,#btnAppliedListClose").die().live("click", function () {
        cashed.Applied.Close();
    });

    $("#btnAppliedCancel").die().live("click", function () {
        cashed.Applied.AppliedCancel();
    });

    $("#chkAppliedIdAll").die().live("click", function () {
        cashed.Applied.Selected(this);
    });
});