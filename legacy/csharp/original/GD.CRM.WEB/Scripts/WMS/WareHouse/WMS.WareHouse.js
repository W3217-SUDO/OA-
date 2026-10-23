var wms = {

    ResetSize: function () {
        if ($("#storageLocationListTree").length > 0) {
            $("#storageLocationListTree").css("height", $(window).height() - $("#storageLocationListTree").offset().top - 12);
        }
        if ($("#divWarehouseList").length > 0) {
            $("#divWarehouseList").css("height", $(window).height() - $("#divWarehouseList").offset().top - 12);
        }
    },
 
    WareHouse: {
            /*货物*/
            Goods: {
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
                        $.checkbox.all("chkClueId");
                        $.checkbox.all("chkClueAll");

                    } else {
                        $.checkbox.not("chkClueId");
                        $.checkbox.not("chkClueAll");
                    }
                },
                List: function () {
                    $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/WMS/Warehouse/GoodsList", function (response) {
                        if (response.IsSuccess) {
                            $("tbody", "#tblGoodsList").clearRow();
                            if (response.Data.TotalItemCount > 0) {
                                $(".info_inall.layoutfix").show();
                                $.each(response.Data.GoodsList, function (i, goods) {
                                    $("tbody", "#tblGoodsList").addRow(
                                           "<input type='checkbox' id='chkClueId' name='chkGoodsId' value=" + goods.EvidenceNo + ">",
                                            goods.StorageLocation,
                                            "<a href='javascript:void(0);' onclick='javascript:investigation.InvestigationClue.View(\"" + goods.ClueNo + "\");'><span>" + goods.ClueNo + "</span></a>",
                                            goods.NotarialNo,
                                            goods.CaseNo == null ? "":"<a href='javascript:void(0);' onclick='javascript:$.case.View(\"" + goods.CaseNo + "\");'><span>" + goods.CaseNo + "</span></a>",
                                            goods.StoreName,
                                            goods.InvestigatorName,
                                            goods.NotaryOrganization,
                                            goods.IndicterName,
                                            goods.NotarialObtainDate == null ? '' : getDate(convertJsonDateToJSDate(goods.NotarialObtainDate)),
                                            goods.GoodsStatusName
                                        );
                                });
                                $("tfoot", "#tblGoodsList").show();
                                $(".simple-grid-none-data-wrap").hide();

                                $(".pull-right.page-box.warehousegoods").cPaging({
                                    totalCount: response.Data.TotalItemCount,
                                    pageNo: response.Data.PageNo,
                                    pageSize: response.Data.PageSize,
                                    callBack: wms.WareHouse.Goods.List,
                                    callBackArgs: null
                                });
                            } else {
                                $("tfoot", "#tblGoodsList").hide();
                                $(".simple-grid-none-data-wrap").show();
                            }
                        }
                    });
                },
            },
            StorageLocation: {
                Tree: {
                    type: {
                        warehouse: "warehouse",
                        location: "location",
                    },
                    setting : {
                        view: {
                            showLine: false,
                            addHoverDom: false,
                            removeHoverDom: false,
                            selectedMulti: false
                        },
                        edit: {
                            enable: true,
                            showRemoveBtn: false,
                            showRenameBtn: false,
                            showUploadBtn: false

                        },
                        data: {
                            simpleData: {
                                enable: true
                            }
                        },
                        callback: {
                            onClick: function (event, treeId, treeNode) {
                                if (treeNode.typeId == wms.WareHouse.StorageLocation.Tree.type.warehouse)
                                {
                                    $("#SearchCondition_WareHouseNo").val(treeNode.id);
                                    $("#SearchCondition_DepositAddress").val('');
                                }
                                else if (treeNode.typeId == wms.WareHouse.StorageLocation.Tree.type.location)
                                {
                                    $("#SearchCondition_WareHouseNo").val(treeNode.pId);
                                    $("#SearchCondition_DepositAddress").val(treeNode.no);
                                }

                                $("#SearchCondition_PageNo").val(1);
                                //$("#SearchCondition_PageSize").val(15);
                                wms.WareHouse.Goods.List();
                            },

                        }
                    },
                    
                },
                List: function () {
                    var data = {};
            
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/WMS/WarehouseStorageLocation/GetStorageLocationGoodsCountList", data, function (response) {
                        if (response.IsSuccess) {
                            if (response.Data.WarehouseLocationGoods.length > 0) {
                                var zNodes = [];
                                $.each(response.Data.WarehouseLocationGoods, function (i, warehouse) {
                                    var node = {};
                                    node.id = warehouse.WarehouseNo;
                                    node.pId = warehouse.WarehouseNo;
                                    node.name = warehouse.WarehouseName + "【" + warehouse.GoodsCounts + "】";
                                    node.open = false;
                                    node.typeId = wms.WareHouse.StorageLocation.Tree.type.warehouse;
                                    zNodes.push(node);

                                    if (warehouse.Locations.length > 0)
                                    {
                                        $.each(warehouse.Locations, function (i, location) {
                                            var node = {};
                                            node.id = location.StorageLocationId;
                                            node.pId = warehouse.WarehouseNo;
                                            node.name = location.StorageLocationName + "【" + location.GoodsCounts + "】";
                                            node.no = location.StorageLocationName;
                                            node.open = false;
                                            node.typeId = wms.WareHouse.StorageLocation.Tree.type.location;
                                            zNodes.push(node);
                                        });
                                    }

                                });
                                $.fn.zTree.init($("#storageLocationListTree"), wms.WareHouse.StorageLocation.Tree.setting, zNodes);
                                wms.ResetSize();
                            }
                        }
                    });
                }
            }
        },
 
};

$(document).ready(function () {

    $(window).resize(function () {
        wms.ResetSize();
    });

    $(document).click(function () {
        //$("#divCaseInfringementWayCheckBoxList").off().hide();
        //$("#divCaseDetermineThewayCheckBoxList").off().hide();
    });

    $(document).off('click', '#btnGoodsSearch').on('click', '#btnGoodsSearch', function () {
        wms.WareHouse.Goods.List();
    });

    wms.WareHouse.StorageLocation.List();
});