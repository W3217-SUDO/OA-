var caseInfo = {

    View: function (caseId) {
        window.open(AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/CreateUpdate?CaseId=" + caseId);
    },

    Open: function (e) {

        if ($("#Contract_ContractBasicInfo_CustomerId").val() == '') {
            $.showModalMessageBox("请选择客户.");
            return false;
        }

        $(e).parents("tr").attr("selected", "true");

        var data =
        {
            customerId: $("#Contract_ContractBasicInfo_CustomerId").val(),
        };

        var url = AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/CaseTreeView";
        $.openLoading();

        $("<div></div>").load(url, data, function (result) {
            $.closeLoading();
            $(document.body).append(result);
            $('#treeviewModal').modal({ backdrop: 'static', keyboard: false });
            $('#treeviewModal').on('hidden.bs.modal', function () {
                $("#treeviewModal").remove();
            });

            caseInfo.BulidCaseTreeView();
        });
    },
    Close: function () {
        $('#treeviewModal').modal('hide');
    },
    BulidCaseTreeView: function () {
        var data1 = {
            customerId: $("#Contract_ContractBasicInfo_CustomerId").val()
        };

        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/CaseListByCustomerId", data1, function (response) {
            if (response.IsSuccess) {
                $('#treeview').treeview({
                    data: response.Data, // 数据源
                    showCheckbox: false, //是否显示复选框
                    highlightSelected: true, //是否高亮选中
                    //nodeIcon: 'glyphicon glyphicon-user',    //节点上的图标
                    nodeIcon: '',
                    emptyIcon: 'icon expand-icon glyphicon glyphicon-minus', //没有子节点的节点图标
                    multiSelect: false, //多选
                    onNodeChecked: function (event, data) {
                        if (data.parentId != null) {
                            $('#treeview').treeview('checkNode', [data.parentId, { silent: true }]);
                        }
                        if (data.nodes != null) {
                            $.each(data.nodes, function (i, c) {
                                $('#treeview').treeview('checkNode', [c.nodeId, { silent: true }]);
                            });
                        }
                    },
                    onNodeUnchecked: function (event, data) {
                        if (data.nodes != null) {
                            $.each(data.nodes, function (i, c) {
                                $('#treeview').treeview('uncheckNode', [c.nodeId, { silent: true }]);
                            });
                        }
                    },
                    onNodeSelected: function (event, data) {

                        if (data.parentId != null) {
                            $('#treeview').treeview('checkNode', [data.parentId, { silent: true }]);
                        }
                        if (data.nodes != null) {
                            $.each(data.nodes, function (i, c) {
                                $('#treeview').treeview('checkNode', [c.nodeId, { silent: true }]);
                            });
                        }
                    }
                });
            } else {
                $.showModalMessageBox(response.Message);
            }
        });
    },
    Selected: function () {
        var nodes = $('#treeview').treeview('getSelected');
        var data = {};
        if (nodes != null && nodes.length > 0) {
            if (nodes[0].nodeType == 'A') {
                data["CaseId"] = nodes[0].nodeOriginalId;
                data["CaseNo"] = nodes[0].nodeCode;

            } else {
                $.showModalMessageBox("请选择案件.");
                return false;
            }
        }

        $("#tblContractObjectList tbody tr").each(function (i, e) {
            if (typeof ($(e).attr("selected")) != "undefined") {
                $(e).find("#item_CaseNo").val(data["CaseNo"]);
                $.lscase.getCaseBasicByCaseNo($(e).find("#item_CaseNo"), $(e).find("#item_CaseNo").val(), contract.Draft.Objects.ObjectItem.getCaseBasicCallBack);
                event.stopPropagation();
            }
            $(e).removeAttr("selected");
            caseInfo.Close();
        });
    },
    QuickCase: {
        Open: function (e) {

            if ($("#Contract_ContractBasicInfo_CustomerId").val() == '') {
                $.showModalMessageBox("请选择客户.");
                return false;
            }

            $("input[name='item_CaseNo']").each(
                function () {
                    $(this).removeAttr("selected");
                }
            );

            $(e).parents("tr").find("#item_CaseNo").attr("selected", "true");

            var data =
            {
                customerId: $("#Contract_ContractBasicInfo_CustomerId").val(),
            };

            var url = AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/QuickCreate";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#quickCreateModel').modal({ backdrop: 'static', keyboard: false });
                $('#quickCreateModel').on('hidden.bs.modal', function () {
                    $("#quickCreateModel").remove();
                });
            });
        },
        Close: function () {

            //$("#tblContractObjectList tbody tr").each(function (i, e) {
            //    $(e).removeAttr("selected");
            //});
            $("input[name='item_CaseNo']").each(
                function () {
                    $(this).removeAttr("selected");
                }
            );

            $('#quickCreateModel').modal('hide');
        },
        CreateUpdate: function () {
            try {
                var data = {};
                //第一申请人
                data["Case.CurrentCaseLevel"] = 1;//调查
                data["Case.CaseBasicInfo.CustomerId"] = $("#Contract_ContractBasicInfo_CustomerId").val();
                data["Case.CaseInvestigation.CaseProsecutor"] = $("#Contract_ContractBasicInfo_CustomerId").val();
                data["Case.CaseBasicInfo.CustomerNo"] = $("#Contract_ContractBasicInfo_CustomerNo").val();
                data["Case.CaseBasicInfo.CaseTypeId"] = $("#CaseInfo_CaseBasicInfo_CaseTypeId").val();
                data["Case.CaseInvestigation.CopyrightType"] = $("#CaseInfo_CaseBasicInfo_CaseTypeId").val();

                data["isSubmit"] = true;

                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Lawsuit/Case/CaseQuickCreateUpdate", data, function (response) {
                    if (response.IsSuccess) {
                        $("#tblContractObjectList tbody tr").each(function (i, e) {
                            if (typeof ($(e).find("#item_CaseNo").attr("selected")) != "undefined") {
                                contract.Draft.Objects.ObjectItem.getCaseBasicCallBack(response, $(e).find("#item_CaseNo"));
                                //event.stopPropagation();
                            }
                        });

                        caseInfo.QuickCase.Close();

                    } else if (response.IsRedirect) {
                        window.location = AP_ROOT + 'Home/Index';
                    } else {
                        $.showModalMessageBox(response.Message);

                    }
                });
            } catch (e) {
                alert(e);
            }
        },
    }
}
