var customer = {
    Init: function () {
       
    },

    ResetSize: function () {
        if ($("#divContextList").length > 0) {
            $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 18);
        }
    },

    Customer: {
        View: function (customerId) {
            var url = AP_ROOT + AP_PAGE_ID + "/CRM/Customer/View?customerId=" + customerId;
            //window.open(url);
            addtabs(url, "客户查看");
        },
        Edit: function (customerId) {
            var url = AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CreateUpdate?customerId=" + customerId;
            addtabs(url, "客户编辑");
            //window.open(url);
        },
        CreateUpdate: function () {

            if ($("#Customer_CustomerBasic_CustomerName").val() == '') {
                $.showModalMessageBox("请输入客户名称.");
                return false;
            }

            if ($("#province").val() != "- 请选择 -")
            {
                $("#Customer_CustomerBasic_Province").val($("#province").val());
            }

            if ($("#city").val() != "- 请选择 -") {
                $("#Customer_CustomerBasic_City").val($("#city").val());
            }

            var regd1 = /^.*[\\\'\"<>|]+.*$/;
            if (regd1.test($("#Customer_CustomerRegistration_RegistrationAddress").val())) {
                $.showModalMessageBox("注册地址禁止输入 <  >  \"   \'  \\ 半角字符，请检查");
                return false;
            }

            var regd = /^.*[-—\\\'\"<>|]+.*$/;
            //if (regd.test($("#Customer_CustomerRegistration_LicenseNo").val())) {
            //    $.showModalMessageBox("统一社会信用代码禁止输入 <  >  \"   \'  \\ 半角字符，请检查");
            //    return false;
            //}

            if (regd.test($("#Customer_CustomerBasic_Zip").val())) {
                $.showModalMessageBox("邮编禁止输入 <  >  \"   \'  \\ 半角字符，请检查");
                return false;
            }

            var coordinators = [];
            var coordinatornames = [];

            $("a[name='coordinatorname']").each(function () {
                coordinators.push($(this).attr("username"));
                coordinatornames.push($(this).attr("userchname"));
            });

            $("#Customer_CustomerBasic_Coordinator").val(coordinators);
            
            $("#customerForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CustomerCreateUpdate", function (response) {
                if (response.IsSuccess) {
                    $('#Customer_CustomerBasic_CustomerId').val(response.Data.CustomerBasic.CustomerId);
                    $('#Customer_CustomerBasic_CustomerNo').val(response.Data.CustomerBasic.CustomerNo);
                    $.showModalMessageBox("保存成功.");
                }
                else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },

        Delete: function (customerId) {
            $.showModalConfirmDialog("确定删除该客户?", 'customer.Customer.DeleteCallBack', customerId);
            return true;
        },

        DeleteCallBack: function (customerId) {
            var data = {
                customerId: customerId
            }

            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CustomerDelete", data, function (response) {
                if (response.IsSuccess) {
                    customer.Customer.List.CustomerList();
                 }
                else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },

        AddContract: function (customerId) {
            var url = AP_ROOT + AP_PAGE_ID + "/FCM/ContractDraft/Create?customerId=" + customerId;
            addtabs(url, "新建合同");
            return true;
        },

        Restore: function (customerId) {
            var data = {
                customerId: customerId
            }

            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CustomerRestore", data, function (response) {
                if (response.IsSuccess) {
                    customer.Customer.List.CustomerList();
                }
                else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },

        InOpen: function (customerId) {
            var data = {
                customerId: customerId
            }

            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CustomerOpen", data, function (response) {
                if (response.IsSuccess) {
                    customer.Customer.List.CustomerList();
                }
                else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },

        InClose: function (customerId) {
            var data = {
                customerId: customerId
            }

            $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CustomerClose", data, function (response) {
                if (response.IsSuccess) {
                    customer.Customer.List.CustomerList();
                }
                else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },
    
        Assignment: {
            Open: function (customerId) {

                var data = {
                    customerId: customerId
                };

                    var url =  AP_ROOT + AP_PAGE_ID + "/CRM/CustomerAssignment/Assigning";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#customerAssignmentModal').modal({ backdrop: 'static', keyboard: false });
                        $('#customerAssignmentModal').on('hidden.bs.modal', function () {
                            $("#customerAssignmentModal").remove();
                        });

                        var assigningCustomerOwner = new AssociateUser(
                            $("#divModelAssociateUserList"),
                            $("#AssigningCustomerOwner"),
                            $("#AssigningCustomerOwnerName"),
                            null
                        );
                    });
                },
            Close: function () {
                $('#customerAssignmentModal').modal('hide');
            },
            Create: function () {

                if ($("#AssigningCustomerOwner").val() == '') {
                    $.showModalMessageBox("请选择现客戶管理人.");
                    return false;
                }
                if ($("#AssigningCustomerOwnerName").val() == '') {
                    $.showModalMessageBox("请选择现客戶管理人.");
                    return false;
                }

                var data = {
                    customerId: $("#Customer_CustomerBasic_CustomerId").val(),
                    assigningCustomerOwner: $("#AssigningCustomerOwner").val(),
                }

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/CustomerAssignment/CustomerAssigning", data, function (response) {
                    if (response.IsSuccess) {
                        $('#customerAssignmentModal').modal('hide');
                        $.showModalMessageBox("分配成功.");
                        customer.Customer.List.CustomerList();

                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            }
        },

        Share: {
            Open: function (customerId) {

                var data = {
                    customerId: customerId
                };

                var url =  AP_ROOT + AP_PAGE_ID + "/CRM/CustomerShare/Sharing";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);
                    $('#customerShareModal').modal({ backdrop: 'static', keyboard: false });
                    $('#customerShareModal').on('hidden.bs.modal', function () {
                        $("#customerShareModal").remove();
                    });

                    customer.Customer.Share.List();
                });
            },
            Close: function () {
                $('#customerShareModal').modal('hide');
            },
            Create: function () {
 
                var data = {
                    customerId: $("#Customer_CustomerBasic_CustomerId").val()
                }

                var i = 0;
                $("input[id='item_CustomerSharedObject']").each(
                    function () {
                        if ($(this).val() != '')
                        {
                            data["sharedObjects[" + i + "]"] = $(this).val();
                            i++;
                        }
                    }
                );

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/CustomerShare/CustomerSharing", data, function (response) {
                    if (response.IsSuccess) {
                        $('#customerShareModal').modal('hide');
                        $.showModalMessageBox("共享成功.");

                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },
            List: function () {
                var data = {
                    customerId: $("#Customer_CustomerBasic_CustomerId").val()
                };

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/CustomerShare/CustomerSharedObjects", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $.each(response.Data, function (i, c) {

                            var tr = '';
                            if (c.StaffName != null) {
                                tr = "<tr>"
                                         + "<td><input id='item_CustomerSharedObject' type='hidden' value='" + c.StaffName + "'><input class='form-control' id='item_CustomerSharedObject_Name' name='item_CustomerSharedObject_Name' type='text' value='" + c.StaffChName + "'></td>"
                                         + "<td><a style='color:green;' href='javascript:void(0);'><span class='btn_ar_add glyphicon glyphicon-plus'></span></a>&nbsp;&nbsp;&nbsp;<a  style='color:red;' href='javascript:void(0);'><span class='btn_ar_remove glyphicon glyphicon-remove'></span></a></td>"
                                  + "</tr>";
                            } else {
                                tr = "<tr>"
                                         + "<td><input id='item_CustomerSharedObject' type='hidden'><input class='form-control' id='item_CustomerSharedObject_Name' name='item_CustomerSharedObject_Name' type='text' ></td>"
                                         + "<td><a style='color:green;' href='javascript:void(0);'><span class='btn_ar_add glyphicon glyphicon-plus'></span></a>&nbsp;&nbsp;&nbsp;<a  style='color:red;' href='javascript:void(0);'><span class='btn_ar_remove glyphicon glyphicon-remove'></span></a></td>"
                                  + "</tr>";
                            }
                            $('#tblCustomerShareList>tbody>tr:last').after(tr);
                        });

                        customer.Customer.Share.ObjectItem.BindEvent();

                        $.closeLoading();
                    }
                }, true);
            },
            ObjectItem: {
                BindEvent: function () {

                    $("input[id='item_CustomerSharedObject_Name']").each(
                        function () {
                            var assigningCustomerOwner = new AssociateUser(
                                $("#divModelAssociateUserList"),
                                $(this).parent().find("#item_CustomerSharedObject"),
                                $(this),
                                null
                            );
                        }
                    );

                    /*更新案件按钮*/
                    $(".btn_ar_add").unbind("click");
                    $(".btn_ar_add").click(function () {
                        customer.Customer.Share.ObjectItem.Add(this);
                        customer.Customer.Share.ObjectItem.BindEvent();
                    });

                    $(".btn_ar_remove").unbind("click");
                    $(".btn_ar_remove").click(function () {
                        customer.Customer.Share.ObjectItem.Remove(this);
                    });

                },
                Add: function (e) {
                    var tr = $(e).parents("tr").clone().show();
                    $(tr).find(":input[type='text']").val('');
                    $(tr).find(":input[type='hidden']").val('');
                    $(tr).find(":input[type='checkbox']").attr("checked", false);
 
                    $("#tblCustomerShareList").append(tr);
                    return tr;
                },
                Remove: function (e) {
                    $(e).parents("tr").remove();
                },
             },
        },

        Coordinator: {
            AddIn: function (username, userchname) {

                var existsUser = false;

                $("a[name='coordinatorname']").each(function () {
                    if ($(this).attr("username") == username) {
                        existsUser = true;
                        return true;
                    }
                });

                //重复

                if (existsUser) return true;

                var $tag = $("<span class='tag label label-info'>"
                                + "<a name='coordinatorname' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                + " username='" + username + "'"
                                + " userchname='" + userchname + "'"
                                + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);'   data-original-title=" + userchname + " '>" + userchname + "</a>"
                                + "<span class='userremove' data-role='remove'></span>"
                            + "</span>");

                $("#Customer_Coordinator_Input").before($tag);
                $tag.after(' ');

            },
            Remove: function (e) {
                $(e).parent().remove();
            },
        },

        List: {
            BindMenu: function () {

                $('#customergridSection').contextMenu('customerMenu', {
                    menuStyle: {
                        width: '152px'
                    },

                    itemStyle: {
                        width: '150px'
                    },

                    bindings: {
                        'view': function (t, e) {
                            var customerId = $(e).find("span").text();
                            if (customerId == '') {
                                $.showModalMessageBox("请选择查看的客户.");
                                return false;
                            }

                            customer.Customer.View(customerId);
                        },
                        'edit': function (t, e) {
                            var customerId = $(e).find("span").text();
                            if (customerId == '') {
                                $.showModalMessageBox("请选择编辑的客户.");
                                return false;
                            }

                            customer.Customer.Edit(customerId);
 
                            return true;
                        },
                        'createcontract': function (t, e) {
                            var customerId = $(e).find("span").text();
                            if (customerId == '') {
                                $.showModalMessageBox("请选择客户.");
                                return false;
                            }

                            window.open( AP_ROOT + AP_PAGE_ID + "/FCM/ContractDraft/Create?customerId=" + customerId);

                            return true;
                        },

                        'assigning': function (t, e) {
                            var customerId = $(e).find("span").text();
                            if (customerId == '') {
                                $.showModalMessageBox("请选择需要分配的客户.");
                                return false;
                            }

                            customer.Customer.Assignment.Open(customerId);

                            return true;
                        },

                        'sharing': function (t, e) {
                            var customerId = $(e).find("span").text();
                            if (customerId == '') {
                                $.showModalMessageBox("请选择需要分享的客户.");
                                return false;
                            }

                            customer.Customer.Share.Open(customerId);

                            return true;
                        },

                        'delete': function (t, e) {
                            var customerId = $(e).find("span").text();
                            if (customerId == '') {
                                $.showModalMessageBox("请选择需要删除的客户.");
                                return false;
                            }

                            customer.Customer.Delete(customerId);

                            return true;
                        },

                        'restore': function (t, e) {
                            var customerId = $(e).find("span").text();
                            if (customerId == '') {
                                $.showModalMessageBox("请选择需要恢复的客户.");
                                return false;
                            }

                            customer.Customer.Restore(customerId);

                            return true;
                        },

                        'inopen': function (t, e) {
                            var customerId = $(e).find("span").text();
                            if (customerId == '') {
                                $.showModalMessageBox("请选择需要进入公海的客户.");
                                return false;
                            }

                            customer.Customer.InOpen(customerId);

                            return true;
                        },

                        'inclose': function (t, e) {
                            var customerId = $(e).find("span").text();
                            if (customerId == '') {
                                $.showModalMessageBox("请选择需要进入拾回的客户.");
                                return false;
                            }

                            customer.Customer.InClose(customerId);

                            return true;
                        },

                    },
                    onContextMenu: function (e) {
                        return true;
                    },
                    onShowMenu: function (e, menu) {
                        if ($(e.target).parents("tr").find(".customerId").hasClass("customerId")) {
                            var customerId = $(e.target).parents("tr").find(".customerId").text();
                            $('#view', menu).append("<span style='display:none'>" + customerId + "</span>");
                            $('#edit', menu).append("<span style='display:none'>" + customerId + "</span>");
                            $('#createcontract', menu).append("<span style='display:none'>" + customerId + "</span>");
                            $('#assigning', menu).append("<span style='display:none'>" + customerId + "</span>");
                            $('#sharing', menu).append("<span style='display:none'>" + customerId + "</span>");
                            $('#delete', menu).append("<span style='display:none'>" + customerId + "</span>");
                            $('#restore', menu).append("<span style='display:none'>" + customerId + "</span>");
                            $('#inopen', menu).append("<span style='display:none'>" + customerId + "</span>");
                            $('#inclose', menu).append("<span style='display:none'>" + customerId + "</span>");

                         } else {
                            $('#view,#edit,#createcontract,#assigning,#sharing,#delete,#restore,#inopen,#inclose', menu).remove();
                        }
                        return menu;
                    }
                });
            },
            CustomerList: function()
            {
                $("#postForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/Customer/List", function (response) {
                    if (response.IsSuccess) {
                        $("tbody", "#tblCustomerList").clearRow();
                        if (response.Data.TotalItemCount > 0) {

                            $(".info_inall.layoutfix").show();
                            $.each(response.Data.Customers, function (i, c) {

                                $("tbody", "#tblCustomerList").addRow(
                                       "<input type='checkbox' id='chkCustomerId' name='chkCustomerId'  customerno=" + c.CustomerBasic.CustomerNo + "'   value=" + c.CustomerBasic.CustomerId + ">",
                                       "<span class='customerId' style='display:none'>" + c.CustomerBasic.CustomerId + "</span><a style='color: #039' href='javascript:void(0);' >" + c.CustomerBasic.CustomerNo + "</a>",
                                        c.CustomerBasic.CustomerName,
                                        c.CustomerExtend.BusinessOwnerName,
                                        c.CustomerBasic.CoordinatorName,
                                        c.CustomerControlling.InputDate == null ? '' : getDate(convertJsonDateToJSDate(c.CustomerControlling.InputDate)),
                                        c.CustomerControlling.LastContactTime == null ? '' : getDate(convertJsonDateToJSDate(c.CustomerControlling.LastContactTime)),
                                        c.CustomerControlling.LastUpdateTime == null ? '' : getDate(convertJsonDateToJSDate(c.CustomerControlling.LastUpdateTime)),
                                        c.CustomerBasic.ContactCounts,
                                        c.CustomerBasic.ContractCounts,
                                        c.CustomerBasic.CaseCounts,
                                        c.CustomerBasic.ARAmount,
                                        c.CustomerControlling.Status
                                   );
                            });

                            $("tfoot", "#tblCustomerList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.customer").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: customer.Customer.List.CustomerList,
                                callBackArgs: null
                            });

                            customer.Customer.List.BindMenu();


                        } else {

                            $("tfoot", "#tblCustomerList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                    }
                });
            },

            CustomerPublicList: function () {
                $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/CRM/Customer/List", function (response) {
                    if (response.IsSuccess) {
                        $("tbody", "#tblCustomerList").clearRow();
                        if (response.Data.TotalItemCount > 0) {

                            $(".info_inall.layoutfix").show();
                            $.each(response.Data.Customers, function (i, c) {

                                $("tbody", "#tblCustomerList").addRow(
                                       //"<span class='customerId' style='display:none'>" + c.CustomerBasic.CustomerId + "</span><a style='color: #039' href='javascript:void(0);' >" + c.CustomerBasic.CustomerNo + "</a>",
                                        c.CustomerBasic.CustomerNo,
                                        c.CustomerBasic.CustomerName,
                                        c.CustomerControlling.InputDate == null ? '' : getDate(convertJsonDateToJSDate(c.CustomerControlling.InputDate)),
                                        c.CustomerExtend.BusinessOwnerName,
                                        c.CustomerControlling.LastContactTime == null ? '' : getDate(convertJsonDateToJSDate(c.CustomerControlling.LastContactTime)),
                                        c.CustomerControlling.LastUpdateTime == null ? '' : getDate(convertJsonDateToJSDate(c.CustomerControlling.LastUpdateTime)),
                                        c.CustomerBasic.ContactCounts,
                                        c.CustomerBasic.ContractCounts,
                                        c.CustomerBasic.CaseCounts
                                   );
                            });

                            $("tfoot", "#tblCustomerList").show();
                            $(".simple-grid-none-data-wrap").hide();

                            $(".pull-right.page-box.customer").cPaging({
                                totalCount: response.Data.TotalItemCount,
                                pageNo: response.Data.PageNo,
                                pageSize: response.Data.PageSize,
                                callBack: customer.Customer.List.CustomerPublicList,
                                callBackArgs: null
                            });

                            customer.Customer.List.BindMenu();


                        } else {

                            $("tfoot", "#tblCustomerList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }
                    }
                });
            },
        },

        Files: {
            Layout: function () {
                var data = {
                    customerId: $("#Customer_CustomerBasic_CustomerGuid").val()
                };

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/CustomerFile/CustomerFileList", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_List").empty();
                        $("#dv_List").html(response.Data);
                        customer.Customer.Files.List();
                        //customer.ResetSize();
                        $.closeLoading();
                    }
                }, true);
            },
            List: function () {
                var data = {
                    customerGuid: $("#Customer_CustomerBasic_CustomerGuid").val(),
                };

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/CustomerFile/CustomerFiles", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();

                        if (response.Data.length > 0) {
                            $.each(response.Data, function (i, file) {
                                $("tbody", "#tblCustomerFileList").addRow(
                                    ++i,
                                    file.UploadUserName,
                                    file.FileName,
                                    file.UploadTime == null ? '' : getDate(convertJsonDateToJSDate(file.UploadTime)),
                                    "<a style='color: #039' href='javascript:void(0);' onclick='javascript:customer.Customer.Files.File.View(\"" + file.CustomerGuid + "\",\"" + file.FileGuid + "\",\"" + file.FileName + "\");'><span>查看</span></a>&nbsp;&nbsp;&nbsp;" +
                                    "<a style='color: #039' href='javascript:void(0);' onclick='javascript:customer.Customer.Files.File.Download(\"" + file.FileGuid + "\");'><span>下载</span></a>",
                                    "<a style='color:green;' href='javascript:void(0);'><span class='btn_customerfile_add glyphicon glyphicon-plus'></span></a>    " 
                                );
                            });
                            $(".simple-grid-none-data-wrap").hide();
                        } else {
                            $(".simple-grid-none-data-wrap").show();
                        }
                        customer.ResetSize();
                        $.closeLoading();
                    }
                }, true);
            },
            File: {
                Open: function () {
                    var data =
                    {
                        customerGuid: $("#Customer_CustomerBasic_CustomerGuid").val(),
                    };
                    var url =  AP_ROOT + AP_PAGE_ID + "/CRM/CustomerFile/CustomerFileUpload";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#customerFileUploadModal').modal({ backdrop: 'static', keyboard: false });
                        $('#customerFileUploadModal').on('hidden.bs.modal', function () {
                            $("#customerFileUploadModal").remove();
                        });
                    });
                },
                Close: function () {
                    $('#customerFileUploadModal').modal('hide');
                },
                Upload: function () {

                    if ($("#flCustomerFile").val() == '') {
                        $.showModalMessageBox("请选择上传文件.");
                        return false;
                    }

                    $('#uploadForm').ajaxSubmit({
                        success: function (response) {
                            $.showModalMessageBox("上传成功.");
                            customer.Customer.Files.File.Close();
                            customer.Customer.Files.Layout();
                        }
                    });
                },
                View: function (customerNo, customerFileId, customerFileName) {

                    if (customerFileId == '' || customerFileName == '') {
                        $.showModalMessageBox("无客户文件.");
                        return false;
                    }

                    var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                    var picfiles = new Array('jpg', 'tif', 'pdf');
                    var extName = customerFileName.substring(customerFileName.lastIndexOf('.') + 1, customerFileName.length);

                    if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                        var path = GV_IPR.OfficeOnlineUrl + GV_IPR.OnlineUrl + "CustomerFiles/CustomerFiles/" + customerNo + "/" + customerFileName;
                        window.open(path);
                    }
                    else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                        var path = GV_IPR.OnlineUrl + "CustomerFiles/CustomerFiles/" + customerNo + "/" + customerFileName;
                        window.open(path);
                    } else {
                        customer.Customer.Files.File.Download(customerFileId);
                    }

                    return true;
                },
                Download: function (customerFileId) {
                    window.open( AP_ROOT + AP_PAGE_ID + "/CRM/CustomerFile/CustomerFileDownloadByGuid?customerFileId=" + customerFileId);
                    return true;
                },
            }
        },

        Events: {
            Layout: function () {

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/CustomerEvent/CustomerEventList", null, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_List").empty();
                        $("#dv_List").html(response.Data);
                        customer.Customer.Events.List();
                        $.closeLoading();
                    }
                }, true);
            },
            List: function () {
                var data = {
                    customerGuid: $("#Customer_CustomerBasic_CustomerGuid").val()
                };

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/CustomerEvent/CustomerEvents", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        if (response.Data.length > 0) {
                            $.each(response.Data, function (i, event) {
                                $("tbody", "#tblCustomerEventList").addRow(
                                    ++i,
                                    "<textarea cols='20'  maxlength='1000' required='true' rows='4' style='width:100%' readonly>"  +event.Content+ "</textarea>",
                                    event.OperatorName,
                                    event.OperateTime == null ? '' : getDate(convertJsonDateToJSDate(event.OperateTime)),
                                    "<a style='color:green;' href='javascript:void(0);'><span class='btn_customerevent_add glyphicon glyphicon-plus'></span></a>    " 
                                );
                            });
                            $(".simple-grid-none-data-wrap").hide();
                        } else {
                            $(".simple-grid-none-data-wrap").show();
                        }
                        customer.ResetSize();
                        $.closeLoading();
                    }
                }, true);
            },
            Event: {
                Open: function () {

                    var url =  AP_ROOT + AP_PAGE_ID + "/CRM/CustomerEvent/CustomerEvent";
                    $.openLoading();

                    $("<div></div>").load(url, null, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#customerEventModal').modal({ backdrop: 'static', keyboard: false });
                        $('#customerEventModal').on('hidden.bs.modal', function () {
                            $("#customerEventModal").remove();
                        });
                    });
                },
                Close: function () {
                    $('#customerEventModal').modal('hide');
                },
                Create: function () {
                    if ($("#CustomerEvent_Content").val() == '') {
                        $.showModalMessageBox("请输入事项内容.");
                        return false;
                    }

                    var data = {
                        customerGuid: $("#Customer_CustomerBasic_CustomerGuid").val(),
                        content: $("#CustomerEvent_Content").val(),
                    }

                    $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/CustomerEvent/CustomerEventCreate", data, function (response) {
                        if (response.IsSuccess) {
                            $('#customerEventModal').modal('hide');
                            customer.Customer.Events.Layout();
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                }
            },
        },

        CustomerContacts: {

            BindMenu: function () {

                $('#customerContactsGridSection').contextMenu('contactsMenu', {
                    menuStyle: {
                        width: '152px'
                    },

                    itemStyle: {
                        width: '150px'
                    },

                    bindings: {
                        'create': function (t, e) {
                            customer.Customer.CustomerContacts.Open();
                            return true;
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

            List: function (isView) {
                var data = {
                    isView : isView,
                    customerId: $("#Customer_CustomerBasic_CustomerId").val(),
                    pageNo: $("#PageNo").val(),
                    pageSize: $("#PageSize").val()
                };

                $.ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/CustomerContacts/ContactsList", data, function (response) {
                    if (response.IsSuccess) {
                        $.openLoading();
                        $("#dv_List").empty();
                        $("#dv_List").html(response.Data);

                        $(".pull-right.page-box.contacts").cPaging({
                            totalCount: parseInt($("#SearchCondition_TotalCount").val()),
                            pageNo: parseInt($("#SearchCondition_PageNo").val()),
                            pageSize: parseInt($("#SearchCondition_PageSize").val()),
                            callBack: customer.Customer.CustomerContacts.List,
                            callBackArgs: null
                        });

                        var totalCount = parseInt($("#SearchCondition_TotalCount").val());

                        customer.ResetSize();

                        if (totalCount > 0) {
                            $("tfoot", "#tblContactsList").show();
                            $(".simple-grid-none-data-wrap").hide();
                        } else {
                            $("tfoot", "#tblContactsList").hide();
                            $(".simple-grid-none-data-wrap").show();
                        }

                        customer.Customer.CustomerContacts.BindMenu();

                        $.closeLoading();
                    }
                }, true);
            },

            /*创建客户*/
            Open: function (contactsId) {

                if ($("#Customer_CustomerBasic_CustomerId").val() == "") {
                    $.showModalMessageBox("请先保存客户基本资料.");
                    return false;
                }

                var data =
                {
                    customerId: $("#Customer_CustomerBasic_CustomerId").val(),
                    customerNo: $("#Customer_CustomerBasic_CustomerNo").val(),
                    contactsId: contactsId
                };

                var url =  AP_ROOT + AP_PAGE_ID + "/CRM/CustomerContacts/CreateUpdate";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);

                    $('#customerContactsModal').modal({ backdrop: 'static', keyboard: false });
                    $('#customerContactsModal').on('hidden.bs.modal', function () {
                        $("#customerContactsModal").remove();
                    });
                });
            },


            /*查看客户*/
            View: function (contactsId) {

                if ($("#Customer_CustomerBasic_CustomerId").val() == "") {
                    $.showModalMessageBox("请先保存客户基本资料.");
                    return false;
                }

                var data =
                {
                    customerId: $("#Customer_CustomerBasic_CustomerId").val(),
                    customerNo: $("#Customer_CustomerBasic_CustomerNo").val(),
                    contactsId: contactsId
                };

                var url =  AP_ROOT + AP_PAGE_ID + "/CRM/CustomerContacts/View";
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();
                    $(document.body).append(result);

                    $('#customerContactsModal').modal({ backdrop: 'static', keyboard: false });
                    $('#customerContactsModal').on('hidden.bs.modal', function () {
                        $("#customerContactsModal").remove();
                    });
                });
            },

            CreateUpdate: function () {

                if ($("#Contacts_Contacts").val() == '') {
                    $.showModalMessageBox("请输入联系人姓名.");
                    return false;
                }

                $("#customerContactsForm").ajaxPost( AP_ROOT + AP_PAGE_ID + "/CRM/CustomerContacts/ContactsCreateUpdate", function (response) {
                    if (response.IsSuccess) {
                        $('#Contacts_ContactsId').val(response.Data.ContactsId);
                        $('#customerContactsModal').modal('hide');
                        customer.Customer.CustomerContacts.List(false);
                        $.showModalMessageBox("保存成功.");
                    }
                    else {
                        $.showModalMessageBox(response.Message);
                    }
                });

                return true;
            },

            Close: function () {
                $('#customerContactsModal').modal('hide');
            },

            ContactsPhoto:
            {
                /*上传*/
                Open: function () {
                    var data =
                    {
                        contactsGuid: $('#Contacts_ContactsGuid').val(),
                        customerNo: $('#Contacts_CustomerNo').val()
                    };

                    var url =  AP_ROOT + AP_PAGE_ID + "/CRM/CustomerContacts/ContactsPhoto";

                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#contactsPhotoModal').modal({ backdrop: 'static', keyboard: false });
                        $('#contactsPhotoModal').on('hidden.bs.modal', function () {
                            $("#contactsPhotoModal").remove();
                        });
                    });
                },

                /*上传*/
                Upload: function () {
                    $('#uploadingForm').ajaxSubmit({
                        success: function (response) {
                            $("#imgContactsPhoto").attr("src", response.Data.PhotoFileFullPath);
                            $("#aimgContactsPhoto").attr("href", response.Data.PhotoFileFullPath);
                            $("#Contacts_PhotoFileName").val(response.Data.PhotoFileName);
                            $('#contactsPhotoModal').modal('hide');
                        }
                    });
                },

                /*关闭*/
                Close: function () {
                    $('#contactsPhotoModal').modal('hide');
                }
            },
        },

        CustomerSearching: function ()
        {
            var data = {
                customerName: $("#CustomerName").val()
            }

            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CustomerQuery", data, function (response) {
                if (response.IsSuccess) {
                    if (typeof (response.Data) == "undefined" || response.Data == null) {
                        $("#help-info-step1").text("未找到该企业基本信息.");
                        return false;
                    }
                    $("#Customer_CustomerBasic_CustomerName").val(response.Data.Customer.CustomerBasic.CustomerName);
                    $("#Customer_CustomerBasic_BusinessOwnerName").val(response.Data.Customer.CustomerBasic.BusinessOwnerName);

                    if (response.Data.Case == null) {
                        $("#Case_Basic_CaseNo").val("无");
                        $("#Case_Basic_CaseRegisterDate").val("无");
                        $("#Case_Basic_AppellantNames").val("无");
                        $("#Case_Basic_AppelleeNames").val("无");
                        $("#Case_Basic_TheThirdNames").val("无");
                        $("#Case_Basic_CustomerName").val("无");
                    }
                    else {
                        $("#Case_Basic_CaseNo").val(response.Data.Case.Basic.CaseNo);
                        $("#Case_Basic_CaseRegisterDate").val(getDate(convertJsonDateToJSDate(response.Data.Case.Basic.CaseRegisterDate)));
                        $("#Case_Basic_AppelleeNames").val(response.Data.Case.Basic.AppelleeNames);
                        $("#Case_Basic_AppellantNames").val(response.Data.Case.Basic.AppellantNames);
                      
                        $("#Case_Basic_TheThirdNames").val(response.Data.Case.Basic.TheThirdNames);
                        $("#Case_Basic_CustomerName").val(response.Data.Case.Basic.CustomerName);
                    }
                    
                    $(".step.col-md-6.step-first").removeClass("step-active");
                    $(".step.col-md-6.step-end").addClass("step-active");
                    $("#divCustomerSearchingStep1").hide();
                    $("#divCustomerSearchingStep2").show();
                }
                else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        }

    },
};

function AssociateAvailableUserForCustomer(div, ctlid, ctlname, func) {

    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;
    this.CallBackFunc = func;

    this.UserName = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") {
            return false;
        }
        var curobj = new Object();
        curobj.keyword = name;

        var data = { userName: name };
        $.ajaxPostMessage(AP_ROOT + AP_PAGE_ID + "/Account/UserCenter/AvailableUsers", data, function (response) {
            if (response.IsSuccess) {
                if (response.Data.length > 0) {
                    var html = '';
                    $.each(response.Data, function (i, c) {
                        html += '<a href="javascript:void(0)" userId=' + c.Item1 + '>' + c.Item2 + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);

                    $(div).find(".i_common_list a").css({
                        "height": $(ctlname).outerHeight(),
                        "line-height": ($(ctlname).outerHeight() - 4) + "px"
                    });

                    $(div).find(".i_common_list a").click(function () {

                        if (func != null) {
                            func($(this).attr("userId"), $(this).text());
                            $(ctlname).val('');
                            $(ctlname).focus();
                        }
                        else {

                            $(ctlid).val($(this).attr("userId"));
                            $(ctlname).val($(this).text());
                        }
                        $(div).hide();
                    });


                    $(div).css({
                        "position": "absolute",
                        "height": $(ctlname).outerHeight() - 32,
                        "line-height": ($(ctlname).outerHeight() - 4) + "px",
                        "width": "450px",
                        "top": $(ctlname).offset().top - 24 ,
                        "left": $(ctlname).position().left + 120,
                        "z-index": 9999
                    }).show();
                }
                else {
                    var html = "";
                    html += '<a href="javascript:void(0)" >没有查询到符合条件的记录.</a>';
                    $(div).find(".i_common_list").html(html);
                    $(div).find(".i_common_list a").css({
                        "height": $(ctlname).outerHeight(),
                        "line-height": ($(ctlname).outerHeight() - 4) + "px"
                    });
                }
            }
            else {

            }
        }, false);

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
            event.data.obj.Event = setTimeout(function () { event.data.obj.UserName(event.data.obj); }, 500);
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
    });

    return this;
}

$(document).ready(function () {

    //键盘enter事件
    document.onkeypress = function () {
        if (event.keyCode == 13) {
            customer.Customer.List.CustomerList();
        }
    }

    var holder = new AssociateUser(
        $("#divAssociateUserList"),
        $("#Customer_CustomerControlling_Holder"),
        $("#Customer_CustomerControlling_HolderName"),
        null
    );

    var coordinator = new AssociateAvailableUserForCustomer(
          $("#div_coordinatorlist"),
          $("#Customer_Coordinator_Input"),
          $("#Customer_Coordinator_Input"),
           customer.Customer.Coordinator.AddIn
      );

    var businessOwner = new AssociateUser(
        $("#divAssociateUserList"),
        $("#Customer_CustomerExtend_BusinessOwner"),
        $("#Customer_CustomerExtend_BusinessOwnerName"),
        null
    );

    var searchBusinessOwner = new AssociateUser(
        $("#divAssociateUserList"),
        $("#SearchCondition_BusinessOwner"),
        $("#SearchCondition_BusinessOwnerName"),
        null
    );

    $("#AssigningCustomerOwnerName").off().on("click", function () {
        $("#hidUserId").val("AssigningCustomerOwner");
        $("#hidUserName").val("AssigningCustomerOwnerName");
        $("#divModelUserList").css({
            "position": "absolute",
            "left": $("#AssigningCustomerOwnerName").parent().position().left + 16,
            "top": $("#AssigningCustomerOwnerName").parent().position().top + 24,
            "z-index": 1200
        }).toggle();
        return false;
    });

    $("#divModelUserList").find("li").off().on("click", function (e) {
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
        $("#divModelUserList").hide();
        return false;
    });

    //$("#SearchCondition_BusinessOwnerName").off().on("click", function () {
    //    $("#hidUserId").val("SearchCondition_BusinessOwner");
    //    $("#hidUserName").val("SearchCondition_BusinessOwnerName");
    //    $("#divUserList").css({
    //        "position": "absolute",
    //        "left": $("#SearchCondition_BusinessOwnerName").position().left,
    //        "top": $("#SearchCondition_BusinessOwnerName").position().top + 24,
    //        "z-index": 1200
    //    }).toggle();
    //    return false;
    //});

    //$("#Customer_CustomerControlling_HolderName").off().on("click", function () {
    //    $("#hidUserId").val("Customer_CustomerControlling_Holder");
    //    $("#hidUserName").val("Customer_CustomerControlling_HolderName");
    //    $("#divUserList").css({
    //        "position": "absolute",
    //        "left": $("#Customer_CustomerControlling_HolderName").position().left,
    //        "top": $("#Customer_CustomerControlling_HolderName").position().top + 30,
    //        "z-index": 1200
    //    }).toggle();
    //    return false;
    //});

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

    $(document).click(function () {
        $("#divUserList").off().hide();
        $("#divAssociateUserList").off().hide();
        $("#divModelUserList").off().hide();
    });

    $(window).resize(function () {
        customer.ResetSize();
    });

    $(document).off('click', '.btn_serviceItem_add').on('click', '.btn_serviceItem_add', function () {
        customerId.Customer.Services.Item.Add(this);
    });

    $(document).off('click', '.btn_serviceItem_remove').on('click', '.btn_serviceItem_remove', function () {
        customerId.Customer.Services.Item.Remove(this);
    });

    $(document).off('click', '#btnCustomerCreateUpdate').on('click', '#btnCustomerCreateUpdate', function () {
        customer.Customer.CreateUpdate();
    });
    
    $(document).off('click', '#btnCustomerContactsCreate').on('click', '#btnCustomerContactsCreate', function () {
        customer.Customer.CustomerContacts.Open();
    });

    $(document).off('click', '#btnCustomerContactsCancel,#btnCustomerContactsClose').on('click', '#btnCustomerContactsCancel,#btnCustomerContactsClose', function () {
        customer.Customer.CustomerContacts.Close();
    });

    $(document).off('click', '#btnCustomerContactsCreateUpdate').on('click', '#btnCustomerContactsCreateUpdate', function () {
        customer.Customer.CustomerContacts.CreateUpdate();
    });

    $(document).off('click', '#btnCustomerContactsPhotoCreate').on('click', '#btnCustomerContactsPhotoCreate', function () {
        customer.Customer.CustomerContacts.ContactsPhoto.Open();
    });

    $(document).off('click', '#btnContactsPhotoUploadCancel,#btnContactsPhotoUploadClose').on('click', '#btnContactsPhotoUploadCancel,#btnContactsPhotoUploadClose', function () {
        customer.Customer.CustomerContacts.ContactsPhoto.Close();
    });

    $(document).off('change', '#flContactsPhotoFile').on('change', '#flContactsPhotoFile', function () {
        $("#txtContactsPhotoFilePath").val($("#flContactsPhotoFile").val());
    });

    $(document).off('click', '#btnContactsPhotoUpload').on('click', '#btnContactsPhotoUpload', function () {
        customer.Customer.CustomerContacts.ContactsPhoto.Upload();
    });

    $(document).off('click', '#btnCustomerSearch').on('click', '#btnCustomerSearch', function () {
        customer.Customer.List.CustomerList();
    });

    $(document).off('click', '#btnCustomerPublicSearch').on('click', '#btnCustomerPublicSearch', function () {
         customer.Customer.List.CustomerPublicList();
    });

    $(document).off('click', '#btnCustomerAssigningCancel,#btnCustomerAssigningClose').on('click', '#btnCustomerAssigningCancel,#btnCustomerAssigningClose', function () {
        customer.Customer.Assignment.Close();
    });

    $(document).off('click', '#btnCustomerAssigning').on('click', '#btnCustomerAssigning', function () {
        customer.Customer.Assignment.Create();
    });

    $(document).off('click', '#btnCustomerShareCancel,#btnCustomerShareClose').on('click', '#btnCustomerShareCancel,#btnCustomerShareClose', function () {
        customer.Customer.Share.Close();
    });

    $(document).off('click', '#btnCustomerShareCreate').on('click', '#btnCustomerShareCreate', function () {
        customer.Customer.Share.Create();
    });
    
    $(document).off('click', '#btnCustomerSearching').on('click', '#btnCustomerSearching', function () {
        customer.Customer.CustomerSearching();
    });
});