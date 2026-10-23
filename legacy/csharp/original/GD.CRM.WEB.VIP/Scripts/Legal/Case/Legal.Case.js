function AssociateCustomer(div, ctlid, ctlno, ctlname, func, func2) {
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
                if (response.Data.Customers.length > 0) {
                    var html = "";
                    $.each(response.Data.Customers, function (i, c) {

                        var defaultContactsContacts = c.DefaultContacts == null ? "" : c.DefaultContacts.Contacts;
                        var defaultContactsContactTelphone = c.DefaultContacts == null ? "" : c.DefaultContacts.OfficePhone;
                        var defaultContactsContactEmail = c.DefaultContacts == null ? "" : c.DefaultContacts.Email;
                        var defaultContactsContactAddress = c.DefaultContacts == null ? "" : c.DefaultContacts.ContactAddress;

                        html += '<a href="javascript:void(0)"  customerid=' + c.CustomerBasic.CustomerId
                            + ' customerno=' + c.CustomerBasic.CustomerNo
                            + ' defaultContactsContacts=' + defaultContactsContacts
                            + ' defaultContactsContactTelphone=' + defaultContactsContactTelphone
                            + ' defaultContactsContactEmail=' + defaultContactsContactEmail
                            + ' defaultContactsContactAddress=' + defaultContactsContactAddress
                            + ' >' + c.CustomerBasic.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);

                    $(div).find(".i_common_list a").css({
                        "height": $(ctlname).outerHeight(),
                        "line-height": ($(ctlname).outerHeight() - 4) + "px"
                    });

                    $(div).find(".i_common_list a").click(function () {
                        //$(ctlid).val($(this).attr("customerid"));
                        $(ctlno).val($(this).attr("customerno"));
                        $(ctlname).val($(this).text());

                        $(div).hide();

                        if (func != null) {
                            setTimeout(func, 500);
                        }

                        if (func2 != null) {
                            setTimeout(func2, 500);
                        }

                    });
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
                $.showModalMessageBox(response.Message);
            }
        }, false);
        $(div).css({
            "position": "absolute",
            "left": $(ctlname).position().left + 0,
            "top": $(ctlname).position().top + 32,
            "width": $(ctlname).outerWidth(),
            "height": $(ctlname).outerHeight(),
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
    });

    return this;
}
function AssociateLitigant(div, ctlid, ctlno, ctlname, func) {
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
                if (response.Data.Customers.length > 0) {
                    var html = "";
                    $.each(response.Data.Customers, function (i, c) {

                        var defaultContactsContacts = c.DefaultContacts == null ? "" : c.DefaultContacts.Contacts;
                        var defaultContactsContactTelphone = c.DefaultContacts == null ? "" : c.DefaultContacts.OfficePhone;
                        var defaultContactsContactEmail = c.DefaultContacts == null ? "" : c.DefaultContacts.Email;
                        var defaultContactsContactAddress = c.DefaultContacts == null ? "" : c.DefaultContacts.ContactAddress;

                        html += '<a href="javascript:void(0)"  customerid=' + c.CustomerBasic.CustomerId
                            + ' customerno=' + c.CustomerBasic.CustomerNo
                            + ' defaultContactsContacts=' + defaultContactsContacts
                            + ' defaultContactsContactTelphone=' + defaultContactsContactTelphone
                            + ' defaultContactsContactEmail=' + defaultContactsContactEmail
                            + ' defaultContactsContactAddress=' + defaultContactsContactAddress
                            + ' >' + c.CustomerBasic.CustomerName + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);

                    $(div).find(".i_common_list a").css({
                        "height": $(ctlname).outerHeight(),
                        "line-height": ($(ctlname).outerHeight() - 4) + "px"
                    });

                    $(div).find(".i_common_list a").click(function () {

                        if (func != null) {
                            func($(this).attr("customerid"), $(this).attr("customerno"), $(this).text());
                        }
                        $(ctlname).val('');
                        $(ctlname).focus();
                        $(div).hide();

                    });
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
                $.showModalMessageBox(response.Message);
            }
        }, false);
        $(div).css({
            "position": "absolute",
            "left": $(ctlname).position().left + 0,
            "top": $(ctlname).position().top + 32,
            "width": $(ctlname).outerWidth(),
            "height": $(ctlname).outerHeight(),
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
    });

    return this;
}
function AssociateAvailableUser_Laywer(div, ctlid, ctlname, func) {

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
                        "left": $(ctlname).position().left + 2,
                        "top": $(ctlname).position().top + 26,
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
function AssociateAvailableUser_PaymentObject(div, ctlid, ctlname, func) {

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
                            var target = $(ctlid).parent().parent().parent();
                            func(target, $(this).attr("userId"), $(this).text());
                            $(ctlname).val('');
                            $(ctlname).focus();
                        }
                        else {
                            $(ctlid).val($(this).attr("userId"));
                            $(ctlname).val($(this).text());
                        }
                        $(div).hide();
                    });
                    //$(div).css({
                    //    "position": "absolute",
                    //    "height": $(ctlname).outerHeight() - 32,
                    //    "line-height": ($(ctlname).outerHeight() - 4) + "px",
                    //    "left": $(ctlname).parent().position().left + 150,
                    //    //"top": $(ctlname).parent().position().top + $(ctlname).parent().parent().parent().parent().parent().height(),
                    //    "z-index": 9999
                    //}).show();

                    $(div).css({
                        "position": "absolute",
                        "height": $(ctlname).outerHeight() - 32,
                        "line-height": ($(ctlname).outerHeight() - 4) + "px",
                        "width": "450px",
                        "top": $(ctlname).offset().top - 65,
                        "left": $(ctlname).position().left + 55,
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
function AssociateAvailableUser_Task(div, ctlid, ctlname, func) {


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
                        "left": $(ctlname).position().left + 2,
                        "top": $(ctlname).position().top + 26,
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
function AssociateCause(div, ctlid, ctlname, func) {

    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;
    this.CallBackFunc = func;

    this.Cause = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") {
            return false;
        }
        var curobj = new Object();
        curobj.keyword = name;

        var data = { keyword: name };
        $.ajaxPostMessage(AP_ROOT + AP_PAGE_ID + "/BAS/Cause/Causes", data, function (response) {
            if (response.IsSuccess) {
                if (response.Data.length > 0) {
                    var html = '';
                    $.each(response.Data, function (i, c) {
                        html += '<a href="javascript:void(0)" causeId=' + c.Item1 + '>' + c.Item2 + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);

                    $(div).find(".i_common_list a").css({
                        "height": $(ctlname).outerHeight(),
                        "line-height": ($(ctlname).outerHeight() - 4) + "px"
                    });

                    $(div).find(".i_common_list a").click(function () {
                        if (func != null) {
                            func($(this).text(), $(this).text());
                            $(ctlname).val('');
                            $(ctlname).focus();
                        }
                        else {
                            $(ctlid).val($(this).attr("causeId"));
                            $(ctlname).val($(this).text());
                        }
                        $(div).hide();
                    });

                    //$(div).find(".i_common_list a").click(function () {
                    //    $(ctlid).val($(this).attr("causeId"));
                    //    $(ctlname).val($(this).text());
                    //    $("#Case_Basic_CaseName").val($(this).text());
                    //    $(div).hide();
                    //});

                    $(div).css({
                        "position": "absolute",
                        "left": $(ctlname).position().left + 2,
                        "top": $(ctlname).position().top + 26,
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
            event.data.obj.Event = setTimeout(function () { event.data.obj.Cause(event.data.obj); }, 500);
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
function AssociateCourt(div, ctlid, ctlname, func) {

    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;
    this.CallBackFunc = func;

    this.Court = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") {
            return false;
        }
        var curobj = new Object();
        curobj.keyword = name;

        var data = { keyword: name };

        $.ajaxPostMessage(AP_ROOT + AP_PAGE_ID + "/BAS/Court/Courts", data, function (response) {
            if (response.IsSuccess) {
                if (response.Data.length > 0) {
                    var html = '';
                    $.each(response.Data, function (i, c) {
                        html += '<a href="javascript:void(0)" courtNo=' + c.Item1 + '>' + c.Item2 + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);

                    $(div).find(".i_common_list a").css({
                        "height": $(ctlname).outerHeight(),
                        "line-height": ($(ctlname).outerHeight() - 4) + "px"
                    });

                    $(div).find(".i_common_list a").click(function () {
                        $(ctlid).val($(this).attr("courtNo"));
                        $(ctlname).val($(this).text());
                        $(div).hide();
                    });

                    $(div).css({
                        "position": "absolute",
                        "left": $(ctlname).position().left + 2,
                        "top": $(ctlname).position().top + 26,
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
            event.data.obj.Event = setTimeout(function () { event.data.obj.Court(event.data.obj); }, 500);
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
function AssociateCourtOfficer(div, ctlCourtNo, ctlid, ctlname, func) {

    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;
    this.CallBackFunc = func;

    this.CourtOfficer = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") {
            return false;
        }
        var curobj = new Object();
        curobj.keyword = name;

        var data = {
            courtNo: $(ctlCourtNo).val(),
            keyword: name
        };

        $.ajaxPostMessage(AP_ROOT + AP_PAGE_ID + "/BAS/CourtOfficer/CourtOfficers", data, function (response) {

            if (response.IsSuccess) {
                if (response.Data.length > 0) {
                    var html = '';
                    $.each(response.Data, function (i, c) {
                        html += '<a href="javascript:void(0)" officerId=' + c.Item1 + '>' + c.Item2 + '</a>';
                    });

                    $(div).find(".i_common_list").html(html);

                    $(div).find(".i_common_list a").css({
                        "height": $(ctlname).outerHeight(),
                        "line-height": ($(ctlname).outerHeight() - 4) + "px"
                    });

                    $(div).find(".i_common_list a").click(function () {

                        $(ctlid).val($(this).attr("officerId"));
                        $(ctlname).val($(this).text());
                        $(div).hide();
                    });

                    $(div).css({
                        "position": "absolute",
                        "left": $(ctlname).position().left + 2,
                        "top": $(ctlname).position().top + 26,
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
            event.data.obj.Event = setTimeout(function () { event.data.obj.CourtOfficer(event.data.obj); }, 500);
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

var investigationClue = {
    InvestigationClues: {
        List: function () {
            var data = {
                indicterNo: $("#Case_Basic_CustomerNo").val()
            };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/CIT/InvestigationClue/GetInvestigationClueListByIndicterNo", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();

                    $("#Case_Basic_InvestigationClueNo").empty();
                    if (response.Data.length > 0) {

                        $.each(response.Data, function (i, c) {
                            $("#Case_Basic_InvestigationClueNo").append('<option value=' + c.Basic.ClueNo + '>' + c.Basic.ClueNo + "_" + c.Basic.Indictee + '</option>');
                        });

                        $("#Case_Basic_InvestigationClueNo").trigger("chosen:updated");
                        $("#Case_Basic_InvestigationClueNo").chosen();
                    }

                    $.closeLoading();
                }
            }, true);
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
        List: function () {
            var data = {
                customerNo: $("#Case_Basic_CustomerNo").val()
            };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/Contract/GetContractListByCustomerNo", data, function (response) {
                if (response.IsSuccess) {
                    $.openLoading();
                    $("#Case_Basic_ContractNo").empty();

                    if (response.Data.length > 0) {
                        $.each(response.Data, function (i, c) {
                            $("#Case_Basic_ContractNo").append('<option value=' + c.ContractBasicInfo.ContractNo + '>' + c.ContractBasicInfo.ContractNo + "_" + c.ContractBasicInfo.ContractName + '</option>');
                        });
                    }
                    else {
                        $("#Case_Basic_ContractNo").append('<option value="">该客户下未存在合同,请新建合同</option>');

                    }

                    $.closeLoading();
                }
            }, true);
        },
    }
}

var c = {
    ResetSize: function () {
        if ($("#divContextList").length > 0) {
            $("#divContextList").css("height", $(window).height() - $("#divContextList").offset().top - 12);
            $("#caseFileTree").css("height", $(window).height() - $("#divContextList").offset().top - 12);
        }
        if ($("#divCaseEvents").length > 0) {
            $("#divCaseEvents").css("height", $('.case-section-product').height() - 2);
        }
        if ($("#divCaseLogs").length > 0) {
            $("#divCaseLogs").css("height", $(window).height() - $("#divCaseLogs").offset().top - 12 + 8);
        }

        if ($("#divCaseList").length > 0) {
            $("#divCaseList").css("height", $(window).height() - $("#divCaseList").offset().top - 12);
        }
        if ($("#caseListTree").length > 0) {
            $("#caseListTree").css("height", $(window).height() - $("#caseListTree").offset().top - 12);
        }
        
    },
    Cases: {
        Case: {
            CreateUpdate: function (callBackFunc) {
                try {
                    var data = {};

                    if ($("#Case_Basic_CustomerNo").val() == '') {
                        $.showModalMessageBox("请选择客户.");
                        return false;
                    }
                    
                    if ($("#Case_Basic_ContractNo").val() == null || $("#Case_Basic_ContractNo").val() == '') {
                        $.showModalMessageBox("请选择合同.");
                        return false;
                    }

                    if ($("#Case_Basic_CauseName").val() == '' && $("#Case_Basic_CaseTypeId").val() != "140") {
                        $.showModalMessageBox("请选择案由.");
                        return false;
                    }

                    if ($("#Case_Basic_CaseName").val() == '') {
                        $.showModalMessageBox("请输入案件名称.");
                        return false;
                    }

                    var causenames = [];
                    $("a[name='causename']").each(function () {
                        causenames.push($(this).attr("causename"));
                    });

                    if (causenames.length == 0 && $("#Case_Basic_CaseTypeId").val() != "140") {
                        $.showModalMessageBox("请输入案由.");
                        return false;
                    }

                    var lawyernames = [];
                    var lawyerchnames = [];

                    $("a[name='lawyername']").each(function () {
                        lawyernames.push($(this).attr("username"));
                        lawyerchnames.push($(this).attr("userchname"));
                    });

                    if (lawyernames.length == 0) {
                        $.showModalMessageBox("请按顺序录入经办律师.");
                        $("#Case_Basic_CaseLawyer_Input").focus();
                        return false;
                    }

                    data["Case.Basic.CaseNo"] = $("#Case_Basic_CaseNo").val();
                    data["Case.Basic.CustomerNo"] = $("#Case_Basic_CustomerNo").val();
                    data["Case.Basic.ContractNo"] = $("#Case_Basic_ContractNo").val();
                    data["Case.Basic.CauseName"] = causenames.join(",");
                    data["Case.Basic.CaseName"] = $("#Case_Basic_CaseName").val();
                    //data["Case.Basic.CasePhaseId"] = $("#Case_Basic_CasePhaseId").val();
                    data["Case.Basic.CaseTypeId"] = $("#Case_Basic_CaseTypeId").val();
                    data["Case.Basic.CaseRightTypeId"] = $("#Case_Basic_CaseRightTypeId").val();
                    data["Case.Basic.CustomerTypeId"] = $("#Case_Basic_CustomerTypeId").val();
                    data["Case.Basic.InvestigationClueNos"] = $("#Case_Basic_InvestigationClueNo").val().join();

                    data["Case.Basic.ConsultantTypeId"] = $("#Case_Basic_ConsultantTypeId").val();
                    data["Case.Basic.ConsultantBeginDate"] = $("#Case_Basic_ConsultantBeginDate").val();
                    data["Case.Basic.ConsultantEndDate"] = $("#Case_Basic_ConsultantEndDate").val();

                    var assistantnames = [];
                    var assistantchnames = [];

                    $("a[name='assistantname']").each(function () {
                        assistantnames.push($(this).attr("username"));
                        assistantchnames.push($(this).attr("userchname"));
                    });

                    var investigatornames = [];
                    var investigatorchnames = [];

                    $("a[name='investigatorname']").each(function () {
                        investigatornames.push($(this).attr("username"));
                        investigatorchnames.push($(this).attr("userchname"));
                    });

                    var businessownernames = [];
                    var businessownerchnames = [];

                    $("a[name='businessownername']").each(function () {
                        businessownernames.push($(this).attr("username"));
                        businessownerchnames.push($(this).attr("userchname"));
                    });

                    data["Case.Basic.CaseLawyer"] = lawyernames.join(",");
                    data["Case.Basic.CaseLawyerName"] = lawyerchnames.join(",");
                    data["Case.Basic.CaseAssistant"] = assistantnames.join(",");
                    data["Case.Basic.CaseAssistantName"] = assistantchnames.join(",");
                    data["Case.Basic.Investigator"] = investigatornames.join(",");
                    data["Case.Basic.InvestigatorName"] = investigatorchnames.join(",");

                    data["Case.Basic.BusinessOwner"] = businessownernames.join(",");
                    data["Case.Basic.BusinessOwnerName"] = businessownerchnames.join(",");

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseCreateUpdate", data, function (response) {
                        if (response.IsSuccess) {
                            if (callBackFunc != null) {
                                callBackFunc(response.Data.CaseNo);
                            }
                            else {
                                window.location = AP_ROOT + AP_PAGE_ID + "/Legal/Case/Litigant?caseNo=" + response.Data.CaseNo;
                            }
                        }
                        else if (response.IsRedirect) {
                            window.location = AP_ROOT + 'Home/Index';
                        } else {
                            $.showModalMessageBox(response.Message);

                        }
                    });
                } catch (e) {
                    alert(e);
                }
            },

            CourtLawerUpdate: function (callBackFunc) {
                try {
                    var data = {};
 
                    var lawyernames = [];
                    var lawyerchnames = [];

                    $("a[name='courtlawyername']").each(function () {
                        lawyernames.push($(this).attr("username"));
                        lawyerchnames.push($(this).attr("userchname"));
                    });

                    if (lawyernames.length == 0) {
                        $.showModalMessageBox("请按顺序录入经办律师.");
                        $("#Case_Basic_CourtLawyer_Input").focus();
                        return false;
                    }

                    data["Case.Basic.CourtLawyer"] = lawyernames.join(",");
                    data["Case.Basic.CourtLawyerName"] = lawyerchnames.join(",");

                    data["Case.Basic.CaseNo"] = $("#Case_Basic_CaseNo").val();

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/Case/CourtLawyerCreateUpdate", data, function (response) {
                        if (response.IsSuccess) {
                            if (callBackFunc != null) {
                                callBackFunc(response.Data.CaseNo);
                            }
                        }
                        else if (response.IsRedirect) {
                            window.location = AP_ROOT + 'Home/Index';
                        } else {
                            $.showModalMessageBox(response.Message);

                        }
                    });
                } catch (e) {
                    alert(e);
                }
            },

            CreateUpdate_NextStep: function (caseNo) {
                window.location = AP_ROOT + AP_PAGE_ID + "/Legal/Case/Litigant?caseNo=" + caseNo;
            },

            ClueToCase_CreateUpdate: function (callBackFunc) {
                try {

                    var data = {};

                    var clueNos = [];
                    $("a[name='clueNo']").each(function () {
                        clueNos.push($(this).attr("clueno"));
                    });

                    if (clueNos.length == 0) {
                        $.showModalMessageBox("无可生成案件的线索，请重新选择线索");
                        return false;
                    }

                    if ($("#Case_Basic_CustomerNo").val() == '') {
                        $.showModalMessageBox("请选择客户.");
                        return false;
                    }

                    if ($("#Case_Basic_ContractNo").val() == null || $("#Case_Basic_ContractNo").val() == '') {
                        $.showModalMessageBox("请选择合同.");
                        return false;
                    }

                    //if ($("#Case_Basic_CauseName").val() == '') {
                    //    $.showModalMessageBox("请选择案由.");
                    //    return false;
                    //}

                    var causenames = [];
                    $("a[name='causename']").each(function () {
                        causenames.push($(this).attr("causename"));
                    });

                    if (causenames.length == 0) {
                        $.showModalMessageBox("请输入案由.");
                        return false;
                    }
                    
                    var lawyernames = [];
                    var lawyerchnames = [];

                    $("a[name='lawyername']").each(function () {
                        lawyernames.push($(this).attr("username"));
                        lawyerchnames.push($(this).attr("userchname"));
                    });

                    if (lawyernames.length == 0) {
                        $.showModalMessageBox("请按顺序录入经办律师.");
                        $("#Case_Basic_CaseLawyer_Input").focus();
                        return false;
                    }

                    data["Case.Basic.CaseNo"] = $("#Case_Basic_CaseNo").val();
                    data["Case.Basic.CustomerNo"] = $("#Case_Basic_CustomerNo").val();
                    data["Case.Basic.ContractNo"] = $("#Case_Basic_ContractNo").val();
                    data["Case.Basic.CauseName"] = $("#Case_Basic_CauseName").val();
                    data["Case.Basic.CasePhaseId"] = $("#Case_Basic_CasePhaseId").val();
                    data["Case.Basic.CaseTypeId"] = $("#Case_Basic_CaseTypeId").val();
                    data["Case.Basic.CaseRightTypeId"] = $("#Case_Basic_CaseRightTypeId").val();
                    data["Case.Basic.CustomerTypeId"] = $("#Case_Basic_CustomerTypeId").val();
                    data["InvestigationClueNos"] = clueNos;

                    var assistantnames = [];
                    var assistantchnames = [];

                    $("a[name='assistantname']").each(function () {
                        assistantnames.push($(this).attr("username"));
                        assistantchnames.push($(this).attr("userchname"));
                    });

                    data["Case.Basic.CaseLawyer"] = lawyernames.join(",");
                    data["Case.Basic.CaseLawyerName"] = lawyerchnames.join(",");
                    data["Case.Basic.CaseAssistant"] = assistantnames.join(",");
                    data["Case.Basic.CaseAssistantName"] = assistantchnames.join(",");

                    $("#btnClueGenerateCaseCreate").attr("disabled", "disabled");

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/Case/ClueToCaseCreateUpdate", data, function (response) {
                        if (response.IsSuccess) {
                            if (callBackFunc != null) {
                                callBackFunc(response.Data.CaseList);
                            }
                        }
                        else if (response.IsRedirect) {
                            window.location = AP_ROOT + 'Home/Index';
                        } else {
                            $.showModalMessageBox(response.Message);

                        }
                    });
                } catch (e) {
                    alert(e);
                }
            },

            ClueToCase_CreateUpdate_NextStep: function (caseList) {

                var data = {};
                var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/ClueToCaseList";
 
                $.openLoading();

                $("<div></div>").load(url, data, function (result) {
                    $.closeLoading();

                    $(".slide-panel-container").empty();
                    $(".slide-panel-container").append(result);
                    $(".slide-panel-container").addClass("show-panel");

                    $("tbody", "#tblCaseList").clearRow();

                    var tr = '';
                    $.each(caseList, function (i, c) {
                        tr += "<tr>"
                                + "<td  style='text-align: center; padding:0px'> <a href='javascript:void(0)' onclick='javascript:c.Cases.Case.View(\"" + c.Basic.CaseNo + "\")'>" + c.Basic.CaseNo + "</a></td>"
                                + "<td  style='text-align: left; padding:0px; white-space: nowrap'> " + c.Basic.CaseName + "</td>"
                                + "<td  style='text-align: center; padding:0px'> " + (c.Basic.CaseLawyerName == null ? "" : c.Basic.CaseLawyerName) + "</td>"
                                + "<td  style='text-align: center; padding:0px'> " + (c.Basic.InvestigatorName == null ? "" : c.Basic.InvestigatorName) + "</td>"
                                + "<td  style='text-align: center; padding:0px'> " + (c.Basic.CaseRegisterDate == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.CaseRegisterDate))) + "</td>"
                             + "</tr>"
                    });

                    $('#tblCaseList>tbody').html(tr);
                     
                });
            },

            CreateUpdate_Refersh: function (caseNo) {
                window.location = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + caseNo;
            },

            View: function (caseNo) {
                var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + caseNo;
                addtabs(url, caseNo);
                //window.open(url);
            },

            Delete: function (caseNos) {
                $.showModalConfirmDialog("确定删除案件？", "c.Cases.Case.DeleteCallBack", caseNos);
                return true;
            },
            DeleteCallBack: function (caseNos) {
                var data = { caseNos: caseNos };
                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseDelete", data, function (response) {
                    if (response.IsSuccess) {
                        $.showModalMessageBox("删除成功.");
                        c.Cases.List();
                    } else {
                        $.showModalMessageBox(response.Message);
                    }
                });
            },
            Basic: {
                CaseLawyer: {
                    AddIn: function (username, userchname) {

                        var existsUser = false;

                        $("a[name='lawyername']").each(function () {
                            if ($(this).attr("username") == username) {
                                existsUser = true;
                                return true;
                            }
                        });

                        //重复

                        if (existsUser) return true;

                        var $tag = $("<span class='tag label label-info'>"
                                     + "<a name='lawyername' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                     + " username='" + username + "'"
                                     + " userchname='" + userchname + "'"
                                     + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);'   data-original-title=" + userchname + " '>" + userchname + "</a>"
                                     + "<span class='lawyerremove' data-role='remove'></span>"
                                   + "</span>");

                        $("#Case_Basic_CaseLawyer_Input").before($tag);
                        $tag.after(' ');

                    },
                    Remove: function (e) {
                        $(e).parent().remove();
                    },
                },
                CourtLawyer: {
                    AddIn: function (username, userchname) {

                        var existsUser = false;

                        $("a[name='courtlawyername']").each(function () {
                            if ($(this).attr("username") == username) {
                                existsUser = true;
                                return true;
                            }
                        });

                        //重复

                        if (existsUser) return true;

                        var $tag = $("<span class='tag label label-info'>"
                                     + "<a name='courtlawyername' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                     + " username='" + username + "'"
                                     + " userchname='" + userchname + "'"
                                     + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);'   data-original-title=" + userchname + " '>" + userchname + "</a>"
                                     + "<span class='lawyerremove' data-role='remove'></span>"
                                   + "</span>");

                        $("#Case_Basic_CourtLawyer_Input").before($tag);
                        $tag.after(' ');

                    },
                    Remove: function (e) {
                        $(e).parent().remove();
                    },
                    Open: function () {

                        var data =
                        {
                            caseId: $("#Case_Basic_CaseId").val(),
                            caseNo: $("#Case_Basic_CaseNo").val(),
                        };

                        var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CourtLawyerEdit";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#caseBasicModal').modal({ backdrop: 'static', keyboard: false });
                            $('#caseBasicModal').on('hidden.bs.modal', function () {
                                $("#caseBasicModal").remove();
                            });
                        });
                    },
                },
                CaseAssistant: {
                    AddIn: function (username, userchname) {

                        var existsUser = false;

                        $("a[name='assistantname']").each(function () {
                            if ($(this).attr("username") == username) {
                                existsUser = true;
                                return true;
                            }
                        });

                        //重复

                        if (existsUser) return true;

                        var $tag = $("<span class='tag label label-info'>"
                                     + "<a name='assistantname' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                     + " username='" + username + "'"
                                     + " userchname='" + userchname + "'"
                                     + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);'   data-original-title=" + userchname + " '>" + userchname + "</a>"
                                     + "<span class='assistantremove' data-role='remove'></span>"
                                   + "</span>");

                        $("#Case_Basic_CaseAssistant_Input").before($tag);
                        $tag.after(' ');

                    },
                    Remove: function (e) {
                        $(e).parent().remove();
                    },
                },
                BusinessOwner: {
                    AddIn: function (username, userchname) {

                        var existsUser = false;

                        $("a[name='businessownername']").each(function () {
                            if ($(this).attr("username") == username) {
                                existsUser = true;
                                return true;
                            }
                        });

                        //重复

                        if (existsUser) return true;

                        var $tag = $("<span class='tag label label-info'>"
                                     + "<a name='businessownername' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                     + " username='" + username + "'"
                                     + " userchname='" + userchname + "'"
                                     + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);'   data-original-title=" + userchname + " '>" + userchname + "</a>"
                                     + "<span class='businessownerremove' data-role='remove'></span>"
                                   + "</span>");

                        $("#Case_Basic_BusinessOwner_Input").before($tag);
                        $tag.after(' ');

                    },
                    Remove: function (e) {
                        $(e).parent().remove();
                    },
                },
                Investigator: {
                    AddIn: function (username, userchname) {

                        var existsUser = false;

                        $("a[name='investigatorname']").each(function () {
                            if ($(this).attr("username") == username) {
                                existsUser = true;
                                return true;
                            }
                        });

                        //重复

                        if (existsUser) return true;

                        var $tag = $("<span class='tag label label-info'>"
                                     + "<a name='investigatorname' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                     + " username='" + username + "'"
                                     + " userchname='" + userchname + "'"
                                     + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);'   data-original-title=" + userchname + " '>" + userchname + "</a>"
                                     + "<span class='investigatorremove' data-role='remove'></span>"
                                   + "</span>");

                        $("#Case_Basic_Investigator_Input").before($tag);
                        $tag.after(' ');

                    },
                    Remove: function (e) {
                        $(e).parent().remove();
                    },
                },
                Cause: {
                    AddIn: function (causename, causename) {

                        var existsCause = false;

                        $("a[name='causename']").each(function () {
                            if ($(this).attr("causename") == causename) {
                                existsCause = true;
                                return true;
                            }
                        });

                        //重复

                        if (existsCause) return true;

                        var $tag = $("<span class='tag label label-info'>"
                                     + "<a name='causename' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                     + " causename='" + causename + "'"
                                     + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);'   data-original-title=" + causename + " '>" + causename + "</a>"
                                     + "<span class='causeremove' data-role='remove'></span>"
                                   + "</span>");

                        $("#Case_Basic_CauseName_Input").before($tag);
                        $tag.after(' ');

                    },
                    Remove: function (e) {
                        $(e).parent().remove();
                    },
                },
                Open: function () {

                    var data =
                    {
                        caseId: $("#Case_Basic_CaseId").val(),
                        caseNo: $("#Case_Basic_CaseNo").val(),
                    };

                    var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseBasicEdit";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#caseBasicModal').modal({ backdrop: 'static', keyboard: false });
                        $('#caseBasicModal').on('hidden.bs.modal', function () {
                            $("#caseBasicModal").remove();
                        });
                    });
                },
            },
            PublicSecurityUnit: {
                Open: function () {

                    var data =
                    {
                        caseId: $("#Case_Basic_CaseId").val(),
                        caseNo: $("#Case_Basic_CaseNo").val(),
                    };

                    var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/PublicSecurityUnitEdit";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#casePublicSecurityUnitModal').modal({ backdrop: 'static', keyboard: false });
                        $('#casePublicSecurityUnitModal').on('hidden.bs.modal', function () {
                            $("#casePublicSecurityUnitModal").remove();
                        });
                    });
                },

                CreateUpdate: function () {
                    try {
                        var data = {};
                        data["Case.Basic.CaseNo"] = $("#Case_Basic_CaseNo").val();

                        data["Case.Basic.FirstIntanceCourt"] = $("#Case_Basic_FirstIntanceCourt").val();
                        data["Case.Basic.FirstIntanceCourtRoom"] = $("#Case_Basic_FirstIntanceCourtRoom").val();
                        data["Case.Basic.FirstIntanceJudge"] = $("#Case_Basic_FirstIntanceJudge").val();
                        data["Case.Basic.FirstIntanceClerk"] = $("#Case_Basic_FirstIntanceClerk").val();
                        data["Case.Basic.FirstIntanceCaseNo"] = $("#Case_Basic_FirstIntanceCaseNo").val();
                        data["Case.Basic.FirstIntanceRegisterDate"] = $("#Case_Basic_FirstIntanceRegisterDate").val();
                        data["Case.Basic.FirstIntanceLawfulDay"] = $("#Case_Basic_FirstIntanceLawfulDay").val();
                        data["Case.Basic.FirstIntanceJudgmentDate"] = $("#Case_Basic_FirstIntanceJudgmentDate").val();

                        data["Case.Basic.SecondIntanceCourt"] = $("#Case_Basic_SecondIntanceCourt").val();
                        data["Case.Basic.SecondIntanceCourtRoom"] = $("#Case_Basic_SecondIntanceCourtRoom").val();
                        data["Case.Basic.SecondIntanceJudge"] = $("#Case_Basic_SecondIntanceJudge").val();
                        data["Case.Basic.SecondIntanceClerk"] = $("#Case_Basic_SecondIntanceClerk").val();
                        data["Case.Basic.SecondIntanceCaseNo"] = $("#Case_Basic_SecondIntanceCaseNo").val();
                        data["Case.Basic.SecondIntanceRegisterDate"] = $("#Case_Basic_SecondIntanceRegisterDate").val();
                        data["Case.Basic.SecondIntanceLawfulDay"] = $("#Case_Basic_SecondIntanceLawfulDay").val();
                        data["Case.Basic.SecondIntanceJudgmentDate"] = $("#Case_Basic_SecondIntanceJudgmentDate").val();

                        data["Case.Basic.LastIntanceCourt"] = $("#Case_Basic_LastIntanceCourt").val();
                        data["Case.Basic.LastIntanceCourtRoom"] = $("#Case_Basic_LastIntanceCourtRoom").val();
                        data["Case.Basic.LastIntanceJudge"] = $("#Case_Basic_LastIntanceJudge").val();
                        data["Case.Basic.LastIntanceClerk"] = $("#Case_Basic_LastIntanceClerk").val();
                        data["Case.Basic.LastIntanceCaseNo"] = $("#Case_Basic_LastIntanceCaseNo").val();
                        data["Case.Basic.LastIntanceRegisterDate"] = $("#Case_Basic_LastIntanceRegisterDate").val();
                        data["Case.Basic.LastIntanceLawfulDay"] = $("#Case_Basic_LastIntanceLawfulDay").val();
                        data["Case.Basic.LastIntanceJudgmentDate"] = $("#Case_Basic_LastIntanceJudgmentDate").val();

                        //公安机关
                        data["Case.Basic.PublicSecurityUnitName"] = $("#Case_Basic_PublicSecurityUnitName").val();
                        data["Case.Basic.PublicSecurityUnitCaseNo"] = $("#Case_Basic_PublicSecurityUnitCaseNo").val();
                        data["Case.Basic.PublicSecurityUnitAddress"] = $("#Case_Basic_PublicSecurityUnitAddress").val();
                        data["Case.Basic.PublicSecurityUnitPhone"] = $("#Case_Basic_PublicSecurityUnitPhone").val();
                        data["Case.Basic.PublicSecurityUnitOperator"] = $("#Case_Basic_PublicSecurityUnitOperator").val();

                        //一审检查机关
                        data["Case.Basic.FirstIntanceProcuratorateUnitName"] = $("#Case_Basic_FirstIntanceProcuratorateUnitName").val();
                        data["Case.Basic.FirstIntanceProcuratorateUnitCaseNo"] = $("#Case_Basic_FirstIntanceProcuratorateUnitCaseNo").val();
                        data["Case.Basic.FirstIntanceProcuratorateUnitAddress"] = $("#Case_Basic_FirstIntanceProcuratorateUnitAddress").val();
                        data["Case.Basic.FirstIntanceProcuratorateUnitOperator"] = $("#Case_Basic_FirstIntanceProcuratorateUnitOperator").val();
                        data["Case.Basic.FirstIntanceProcuratorateUnitPhone"] = $("#Case_Basic_FirstIntanceProcuratorateUnitPhone").val();

                        //二审检查机关
                        data["Case.Basic.SecondIntanceProcuratorateUnitName"] = $("#Case_Basic_SecondIntanceProcuratorateUnitName").val();
                        data["Case.Basic.SecondIntanceProcuratorateUnitCaseNo"] = $("#Case_Basic_SecondIntanceProcuratorateUnitCaseNo").val();
                        data["Case.Basic.SecondIntanceProcuratorateUnitAddress"] = $("#Case_Basic_SecondIntanceProcuratorateUnitAddress").val();
                        data["Case.Basic.SecondIntanceProcuratorateUnitOperator"] = $("#Case_Basic_SecondIntanceProcuratorateUnitOperator").val();
                        data["Case.Basic.SecondIntanceProcuratorateUnitPhone"] = $("#Case_Basic_SecondIntanceProcuratorateUnitPhone").val();

                        //再审检查机关
                        data["Case.Basic.LastIntanceProcuratorateUnitName"] = $("#Case_Basic_LastIntanceProcuratorateUnitName").val();
                        data["Case.Basic.LastIntanceProcuratorateUnitCaseNo"] = $("#Case_Basic_LastIntanceProcuratorateUnitCaseNo").val();
                        data["Case.Basic.LastIntanceProcuratorateUnitAddress"] = $("#Case_Basic_LastIntanceProcuratorateUnitAddress").val();
                        data["Case.Basic.LastIntanceProcuratorateUnitOperator"] = $("#Case_Basic_LastIntanceProcuratorateUnitOperator").val();
                        data["Case.Basic.LastIntanceProcuratorateUnitPhone"] = $("#Case_Basic_LastIntanceProcuratorateUnitPhone").val();


                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/Case/PublicSecurityUnitCreateUpdate", data, function (response) {
                            if (response.IsSuccess) {
                                window.location = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + response.Data.CaseNo;
                            }
                            else if (response.IsRedirect) {
                                window.location = AP_ROOT + 'Home/Index';
                            } else {
                                $.showModalMessageBox(response.Message);

                            }
                        });
                    } catch (e) {
                        alert(e);
                    }
                },

            },
            Participant: {
                Open: function (caseNos) {

                    if (caseNos == null || caseNos.length == 0) {
                        $.showModalMessageBox("请选择案件.");
                        return false;
                    }

                    var data =
                    {
                        caseNos: caseNos.join(',')
                    };

                    var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/ParticipantEdit";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(".slide-panel-container").empty();
                        $(".slide-panel-container").append(result);
                        $(".slide-panel-container").addClass("show-panel");
                    });
                },
                CreateUpdate: function (callBackFunc) {
                    try {

                        var lawyernames = [];
                        var lawyerchnames = [];

                        $("a[name='lawyername']").each(function () {
                            lawyernames.push($(this).attr("username"));
                            lawyerchnames.push($(this).attr("userchname"));
                        });

                        var courtlawyernames = [];
                        var courtlawyerchnames = [];

                        $("a[name='courtlawyername']").each(function () {
                            courtlawyernames.push($(this).attr("username"));
                            courtlawyerchnames.push($(this).attr("userchname"));
                        });

                        var assistantnames = [];
                        var assistantchnames = [];

                        $("a[name='assistantname']").each(function () {
                            assistantnames.push($(this).attr("username"));
                            assistantchnames.push($(this).attr("userchname"));
                        });

                        var businessownernames = [];
                        var businessownerchnames = [];

                        $("a[name='businessownername']").each(function () {
                            businessownernames.push($(this).attr("username"));
                            businessownerchnames.push($(this).attr("userchname"));
                        });

                        //if (lawyernames.length == 0 && assistantnames.length == 0) {
                        //    $.showModalMessageBox("请输入经办律师或律师助理.");
                        //    return false;
                        //}

                        var casenos = [];
                        $("a[name='casename']").each(function () {
                            casenos.push($(this).attr("caseno"));
                        });

                        if ($("#LitigationAmount").val() != '' && !$("#LitigationAmount").isMoney())
                        {
                            $.showModalMessageBox("诉讼标的不是金额格式.");
                            return;
                        }

                        var data = {
                            CaseNos: casenos,
                            CourtLawyers: courtlawyernames,
                            CaseLawyers: lawyernames,
                            CaseAssistants: assistantnames,
                            BusinessOwners: businessownernames,
                            CasePhaseId: $("#CasePhaseId").val(),
                            LitigationAmount: $("#LitigationAmount").val()
                        };

                        
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/Case/ParticipantUpdate", data, function (response) {
                            if (response.IsSuccess) {
                                $.showModalMessageBox("修改成功.");
                                c.Cases.Case.Participant.Close();
                                if (callBackFunc != null) {
                                    callBackFunc();
                                }
                            }
                            else if (response.IsRedirect) {
                                window.location = AP_ROOT + 'Home/Index';
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    } catch (e) {
                        alert(e);
                    }
                },
                Close: function () {
                    $(".slide-panel-container").empty();
                    $(".slide-panel-container").removeClass("show-panel");
                    return false;
                },
            },
            SettlementAmount: {
                CreateUpdate: function () {
                    try {
                        var data = {};

                        if (!$("#Case_Basic_LitigationAmount").isMoney()) {
                            $.showModalMessageBox("诉讼标的格式不正确，请重新输入.");
                            return false;
                        }

                        if (!$("#Case_Basic_SettlementAmount").isMoney()) {
                            $.showModalMessageBox("判决金额格式不正确，请重新输入.");
                            return false;
                        }

                        data["Case.Basic.CaseNo"] = $("#Case_Basic_CaseNo").val();
                        data["Case.Basic.SettlementAmount"] = $("#Case_Basic_SettlementAmount").val();
                        data["Case.Basic.LitigationAmount"] = $("#Case_Basic_LitigationAmount").val();

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/Case/SettlementAmountCreateUpdate", data, function (response) {
                            if (response.IsSuccess) {
                                window.location = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + response.Data.CaseNo;
                            }
                            else if (response.IsRedirect) {
                                window.location = AP_ROOT + 'Home/Index';
                            } else {
                                $.showModalMessageBox(response.Message);

                            }
                        });
                    } catch (e) {
                        alert(e);
                    }
                },
                Open: function () {

                    var data =
                    {
                        caseId: $("#Case_Basic_CaseId").val(),
                        caseNo: $("#Case_Basic_CaseNo").val(),
                    };

                    var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/SettlementAmountEdit";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#caseSettlementAmountModal').modal({ backdrop: 'static', keyboard: false });
                        $('#caseSettlementAmountModal').on('hidden.bs.modal', function () {
                            $("#caseSettlementAmountModal").remove();
                        });
                    });
                },
            },
            NotarialNo: {
                CreateUpdate: function () {
                    try {
                        var data = {};

                        if ($("#Case_Basic_NotarialNos").val() == '') {
                            $.showModalMessageBox("请输入公证书号.");
                            return false;
                        }

                        //if ($("#Case_Basic_DepositAddress").val() == '') {
                        //    $.showModalMessageBox("请输入仓库位置.");
                        //    return false;
                        //}

                        data["Case.Basic.CaseNo"] = $("#Case_Basic_CaseNo").val();
                        data["Case.Basic.NotarialNos"] = $("#Case_Basic_NotarialNos").val();
                        data["Case.Basic.DepositAddress"] = $("#Case_Basic_DepositAddress").val();

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/Case/NotarialNoCreateUpdate", data, function (response) {
                            if (response.IsSuccess) {
                                window.location = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + response.Data.CaseNo;
                            }
                            else if (response.IsRedirect) {
                                window.location = AP_ROOT + 'Home/Index';
                            } else {
                                $.showModalMessageBox(response.Message);

                            }
                        });
                    } catch (e) {
                        alert(e);
                    }
                },
                Open: function () {

                    var data =
                    {
                        caseId: $("#Case_Basic_CaseId").val(),
                        caseNo: $("#Case_Basic_CaseNo").val(),
                    };

                    var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/NotarialNoEdit";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#caseNotarialNoModal').modal({ backdrop: 'static', keyboard: false });
                        $('#caseNotarialNoModal').on('hidden.bs.modal', function () {
                            $("#caseNotarialNoModal").remove();
                        });
                    });
                },
            },
            Litigant: {
                CreateUpdate: function (callBackFunc) {
                    try {

                        var data = {};
                        data["Case.Basic.CaseNo"] = $("#Case_Basic_CaseNo").val();

                        //原告
                        var appellantNos = [];
                        var appellantNames = [];

                        $("a[name='appellant']").each(function () {
                            appellantNos.push($(this).attr("customerno"));
                            appellantNames.push($(this).attr("customername"));
                        });

                        if (appellantNos.length == 0 && ($("#Case_Basic_CaseTypeId").val() == '110'
                                                      || $("#Case_Basic_CaseTypeId").val() == '130'
                                                      || $("#Case_Basic_CaseTypeId").val() == '150'))
                        {
                            $.showModalMessageBox("请录入原告.");
                            return false;
                        }

                        //被告
                        var appelleeNos = [];
                        var appelleeNames = [];

                        $("a[name='appellee']").each(function () {
                            appelleeNos.push($(this).attr("customerno"));
                            appelleeNames.push($(this).attr("customername"));
                        });

                        if (appelleeNos.length == 0 && ($("#Case_Basic_CaseTypeId").val() == '110'
                                                      || $("#Case_Basic_CaseTypeId").val() == '130'
                                                      || $("#Case_Basic_CaseTypeId").val() == '150')) {
                            $.showModalMessageBox("请录入被告.");
                            return false;
                        }

                        var thethirdNos = [];
                        var thethirdNames = [];

                        $("a[name='thethird']").each(function () {
                            thethirdNos.push($(this).attr("customerno"));
                            thethirdNames.push($(this).attr("customername"));
                        });

                        data["Case.Basic.AppellantNos"] = appellantNos.join(",");
                        data["Case.Basic.AppellantNames"] = appellantNames.join(",");
                        data["Case.Basic.AppelleeNos"] = appelleeNos.join(",");
                        data["Case.Basic.AppelleeNames"] = appelleeNames.join(",");
                        data["Case.Basic.TheThirdNos"] = thethirdNos.join(",");
                        data["Case.Basic.TheThirdNames"] = thethirdNames.join(",");


                        //原告代理人
                        $("a[name='appellantAgent']").each(function (i, e) {
                            data["Case.Basic.AppellantAgents[0].Name"] = $(e).attr("litigantname");
                            data["Case.Basic.AppellantAgents[0].Position"] = $(e).attr("litigantposition");
                            data["Case.Basic.AppellantAgents[0].AgentAuthCode"] = $(e).attr("agentauthcode");
                        });

                        //被告代理人
                        $("a[name='appelleeAgent']").each(function (i, e) {
                            data["Case.Basic.AppelleeAgents[0].Name"] = $(e).attr("litigantname");
                            data["Case.Basic.AppelleeAgents[0].Position"] = $(e).attr("litigantposition");
                            data["Case.Basic.AppelleeAgents[0].AgentAuthCode"] = $(e).attr("agentauthcode");
                        });

                        //第三人
                        $("a[name='theThirdAgent']").each(function (i, e) {
                            data["Case.Basic.TheThirdAgents[0].Name"] = $(e).attr("litigantname");
                            data["Case.Basic.TheThirdAgents[0].Position"] = $(e).attr("litigantposition");
                            data["Case.Basic.TheThirdAgents[0].AgentAuthCode"] = $(e).attr("agentauthcode");
                        });

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/Case/LitigantCreateUpdate", data, function (response) {
                            if (response.IsSuccess) {
                                if (callBackFunc != null) {
                                    callBackFunc(response.Data.CaseNo);
                                }
                                else {
                                    window.location = AP_ROOT + AP_PAGE_ID + "/Legal/Case/Litigant?caseNo=" + response.Data.CaseNo;
                                }
                            }
                            else if (response.IsRedirect) {
                                window.location = AP_ROOT + 'Home/Index';
                            } else {
                                $.showModalMessageBox(response.Message);

                            }
                        });
                    } catch (e) {
                        alert(e);
                    }
                },

                CreateUpdate_NextStep: function (caseNo) {
                    window.location = AP_ROOT + AP_PAGE_ID + "/Legal/Case/Court?caseNo=" + caseNo;
                },
                CreateUpdate_Refersh: function (caseNo) {
                    window.location = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + caseNo;
                },

                Open: function () {
                    var data =
                    {
                        caseId: $("#Case_Basic_CaseId").val(),
                        caseNo: $("#Case_Basic_CaseNo").val(),
                    };

                    var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/LitigantEdit";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#caseLitigantModal').modal({ backdrop: 'static', keyboard: false });
                        $('#caseLitigantModal').on('hidden.bs.modal', function () {
                            $("#caseLitigantModal").remove();
                        });
                    });
                },
                //原告
                Appellant: {
                    AddIn: function (customerId, customerNo, customerName) {

                        var existsLitigant = false;

                        $("a[name='appellant']").each(function () {
                            if ($(this).attr("customerid") == customerId) {
                                existsLitigant = true;
                                return true;
                            }
                        });

                        //重复

                        if (existsLitigant) return true;

                        var $tag = $("<span class='tag label label-info'>"
                                     + "<a name='appellant' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                     + " customerid='" + customerId + "'"
                                     + " customerno='" + customerNo + "'"
                                     + " customername='" + customerName + "'"
                                     + " title='' data-toggle='tooltip' data-container='body' href='javascript:caseInfo.CaseCustomer.ViewCustomer(" + customerId + ");' target='_blank' data-original-title=" + customerName + " '>" + customerName + "</a>"
                                     + "<span class='appellantremove' data-role='remove'></span>"
                                   + "</span>");

                        $("#Case_Basic_Appellant_Input").before($tag);
                        $tag.after(' ');

                    },
                    Remove: function (e) {
                        $(e).parent().remove();
                    },
                    LitigantAgent: {
                        AddIn: function (litigantNo, litigantName, litigantPosition, litigantAuthCode, ctlInput) {

                            var existsLitigant = false;
                            $("a[name='appellantAgent']").each(function () {
                                if ($(this).attr("litigantNo") == litigantNo) {
                                    existsLitigant = true;
                                    return true;
                                }
                            });

                            //重复
                            if (existsLitigant) return true;

                            var $tag = $("<span class='tag label label-info'>"
                                         + "<a name='appellantAgent' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                         + " litigantNo='" + litigantNo + "'"
                                         + " litigantName='" + litigantName + "'"
                                         + " litigantPosition='" + litigantPosition + "'"
                                         + " litigantAuthCode='" + litigantAuthCode + "'"
                                         + " title='' data-toggle='tooltip' data-container='body' href='javascript:caseInfo.CaseCustomer.ViewCustomer(" + litigantNo + ");' target='_blank' data-original-title=" + litigantName + " '>" + litigantName + "</a>"
                                         + "<span class='appellantagentremove' data-role='remove'></span>"
                                       + "</span>");

                            $(ctlInput).before($tag);
                            $tag.after(' ');

                        },
                        Remove: function (e) {
                            $(e).parent().remove();
                        },
                        Open: function (e) {
                            var data = {};
                            var url = AP_ROOT + AP_PAGE_ID + "/Legal/Litigant/LitigantAgent";
                            $.openLoading();
                            $("<div></div>").load(url, data, function (result) {
                                $.closeLoading();
                                $(document.body).append(result);

                                $("#LitigantAgentInput").val($(e).attr("id"));

                                $('#litigantAgentModal').modal({ backdrop: 'static', keyboard: false });
                                $('#litigantAgentModal').on('hidden.bs.modal', function () {
                                    $("#litigantAgentModal").remove();
                                });
                            });
                        },
                        CreateUpdate: function (func, ctlInput) {
                            try {
                                var data = {};
                                data["LitigantAgent.Name"] = $("#LitigantAgent_Name").val();
                                data["LitigantAgent.Position"] = $("#LitigantAgent_Position").val();
                                data["LitigantAgent.AgentAuthCode"] = $("#LitigantAgent_AgentAuthCode").val();

                                func($("#LitigantAgent_Name").val(), $("#LitigantAgent_Name").val(), $("#LitigantAgent_Position").val(), $("#LitigantAgent_AgentAuthCode").val(), ctlInput);

                                $('#litigantAgentModal').modal('hide');
                            } catch (e) {
                                alert(e);
                            }
                        },
                    }
                },

                //被告
                Appellee: {
                    AddIn: function (customerId, customerNo, customerName) {

                        var existsLitigant = false;

                        $("a[name='appellee']").each(function () {
                            if ($(this).attr("customerid") == customerId) {
                                existsLitigant = true;
                                return true;
                            }
                        });
                        //重复
                        if (existsLitigant) return true;

                        var $tag = $("<span class='tag label label-info'>"
                                     + "<a name='appellee' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                     + " customerid='" + customerId + "'"
                                     + " customerno='" + customerNo + "'"
                                     + " customername='" + customerName + "'"
                                     + " title='' data-toggle='tooltip' data-container='body' href='javascript:caseInfo.CaseCustomer.ViewCustomer(" + customerId + ");' target='_blank' data-original-title=" + customerName + " '>" + customerName + "</a>"
                                     + "<span class='appelleeremove' data-role='remove'></span>"
                                   + "</span>");

                        $("#Case_Basic_Appellee_Input").before($tag);
                        $tag.after(' ');

                    },
                    Remove: function (e) {
                        $(e).parent().remove();
                    },
                    LitigantAgent: {
                        AddIn: function (litigantNo, litigantName, litigantPosition, litigantAuthCode, ctlInput) {
                            var existsLitigant = false;
                            $("a[name='appelleeAgent']").each(function () {
                                if ($(this).attr("litigantNo") == litigantNo) {
                                    existsLitigant = true;
                                    return true;
                                }
                            });

                            //重复
                            if (existsLitigant) return true;

                            var $tag = $("<span class='tag label label-info'>"
                                         + "<a name='appelleeAgent' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                         + " litigantNo='" + litigantNo + "'"
                                         + " litigantName='" + litigantName + "'"
                                         + " litigantPosition='" + litigantPosition + "'"
                                         + " litigantAuthCode='" + litigantAuthCode + "'"
                                         + " title='' data-toggle='tooltip' data-container='body' href='javascript:caseInfo.CaseCustomer.ViewCustomer(" + litigantNo + ");' target='_blank' data-original-title=" + litigantName + " '>" + litigantName + "</a>"
                                         + "<span class='appelleeagentremove' data-role='remove'></span>"
                                       + "</span>");

                            $(ctlInput).before($tag);
                            $tag.after(' ');

                        },
                        Remove: function (e) {
                            $(e).parent().remove();
                        },
                        Open: function (e) {
                            var data = {};
                            var url = AP_ROOT + AP_PAGE_ID + "/Legal/Litigant/LitigantAgent";
                            $.openLoading();
                            $("<div></div>").load(url, data, function (result) {
                                $.closeLoading();
                                $(document.body).append(result);

                                $("#LitigantAgentInput").val($(e).attr("id"));

                                $('#litigantAgentModal').modal({ backdrop: 'static', keyboard: false });
                                $('#litigantAgentModal').on('hidden.bs.modal', function () {
                                    $("#litigantAgentModal").remove();
                                });
                            });
                        },
                        CreateUpdate: function (func, ctlInput) {
                            try {
                                var data = {};
                                data["LitigantAgent.Name"] = $("#LitigantAgent_Name").val();
                                data["LitigantAgent.Position"] = $("#LitigantAgent_Position").val();
                                data["LitigantAgent.AgentAuthCode"] = $("#LitigantAgent_AgentAuthCode").val();

                                func($("#LitigantAgent_Name").val(), $("#LitigantAgent_Name").val(), $("#LitigantAgent_Position").val(), $("#LitigantAgent_AgentAuthCode").val(), ctlInput);

                                $('#litigantAgentModal').modal('hide');

                            } catch (e) {
                                alert(e);
                            }
                        },
                    }
                },

                //第三人
                TheThird: {
                    AddIn: function (customerId, customerNo, customerName) {

                        var existsLitigant = false;

                        $("a[name='thethird']").each(function () {
                            if ($(this).attr("customerid") == customerId) {
                                existsLitigant = true;
                                return true;
                            }
                        });

                        //重复

                        if (existsLitigant) return true;

                        var $tag = $("<span class='tag label label-info'>"
                                     + "<a name='thethird' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                     + " customerid='" + customerId + "'"
                                     + " customerno='" + customerNo + "'"
                                     + " customername='" + customerName + "'"
                                     + " title='' data-toggle='tooltip' data-container='body' href='javascript:caseInfo.CaseCustomer.ViewCustomer(" + customerId + ");' target='_blank' data-original-title=" + customerName + " '>" + customerName + "</a>"
                                     + "<span class='thethirdremove' data-role='remove'></span>"
                                   + "</span>");

                        $("#Case_Basic_TheThird_Input").before($tag);
                        $tag.after(' ');

                    },
                    Remove: function (e) {
                        $(e).parent().remove();
                    },
                    LitigantAgent: {
                        AddIn: function (litigantNo, litigantName, litigantPosition, litigantAuthCode, ctlInput) {
                            var existsLitigant = false;
                            $("a[name='theThirdAgent']").each(function () {
                                if ($(this).attr("litigantNo") == litigantNo) {
                                    existsLitigant = true;
                                    return true;
                                }
                            });

                            //重复
                            if (existsLitigant) return true;

                            var $tag = $("<span class='tag label label-info'>"
                                         + "<a name='theThirdAgent' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                         + " litigantNo='" + litigantNo + "'"
                                         + " litigantName='" + litigantName + "'"
                                         + " litigantPosition='" + litigantPosition + "'"
                                         + " litigantAuthCode='" + litigantAuthCode + "'"
                                         + " title='' data-toggle='tooltip' data-container='body' href='javascript:caseInfo.CaseCustomer.ViewCustomer(" + litigantNo + ");' target='_blank' data-original-title=" + litigantName + " '>" + litigantName + "</a>"
                                         + "<span class='thethirdagentremove' data-role='remove'></span>"
                                       + "</span>");

                            $(ctlInput).before($tag);
                            $tag.after(' ');

                        },
                        Remove: function (e) {
                            $(e).parent().remove();
                        },
                        Open: function (e) {
                            var data = {};
                            var url = AP_ROOT + AP_PAGE_ID + "/Legal/Litigant/LitigantAgent";
                            $.openLoading();
                            $("<div></div>").load(url, data, function (result) {
                                $.closeLoading();
                                $(document.body).append(result);

                                $("#LitigantAgentInput").val($(e).attr("id"));

                                $('#litigantAgentModal').modal({ backdrop: 'static', keyboard: false });
                                $('#litigantAgentModal').on('hidden.bs.modal', function () {
                                    $("#litigantAgentModal").remove();
                                });
                            });
                        },
                        CreateUpdate: function (func, ctlInput) {
                            try {
                                var data = {};

                                data["LitigantAgent.Name"] = $("#LitigantAgent_Name").val();
                                data["LitigantAgent.Position"] = $("#LitigantAgent_Position").val();
                                data["LitigantAgent.AgentAuthCode"] = $("#LitigantAgent_AgentAuthCode").val();

                                func($("#LitigantAgent_Name").val(), $("#LitigantAgent_Name").val(), $("#LitigantAgent_Position").val(), $("#LitigantAgent_AgentAuthCode").val(), ctlInput);

                                $('#litigantAgentModal').modal('hide');
                            } catch (e) {
                                alert(e);
                            }
                        },
                    }
                },
            },
            Court: {
                CreateUpdate: function () {
                    try {
                        var data = {};
                        data["Case.Basic.CaseNo"] = $("#Case_Basic_CaseNo").val();

                        var firstIntanceJudges = [];
                        var firstIntanceJudgeNames = [];
                        $("a[name='firstCourtOfficer']").each(function () {
                            firstIntanceJudges.push($(this).attr("courtofficerno"));
                            firstIntanceJudgeNames.push($(this).attr("courtofficername"));
                        });

                        var firstIntanceClerks = [];
                        var firstIntanceClerkNames = [];
                        $("a[name='firstCourtClerk']").each(function () {
                            firstIntanceClerks.push($(this).attr("courtofficerno"));
                            firstIntanceClerkNames.push($(this).attr("courtofficername"));
                        });

                        var secondIntanceJudges = [];
                        var secondIntanceJudgeNames = [];
                        $("a[name='secondCourtOfficer']").each(function () {
                            secondIntanceJudges.push($(this).attr("courtofficerno"));
                            secondIntanceJudgeNames.push($(this).attr("courtofficername"));
                        });

                        var secondIntanceClerks = [];
                        var secondIntanceClerkNames = [];
                        $("a[name='secondCourtClerk']").each(function () {
                            secondIntanceClerks.push($(this).attr("courtofficerno"));
                            secondIntanceClerkNames.push($(this).attr("courtofficername"));
                        });

                        var executionIntanceJudges = [];
                        var executionIntanceJudgeNames = [];
                        $("a[name='executionCourtOfficer']").each(function () {
                            executionIntanceJudges.push($(this).attr("courtofficerno"));
                            executionIntanceJudgeNames.push($(this).attr("courtofficername"));
                        });

                        var executionIntanceClerks = [];
                        var executionIntanceClerkNames = [];
                        $("a[name='executionCourtClerk']").each(function () {
                            executionIntanceClerks.push($(this).attr("courtofficerno"));
                            executionIntanceClerkNames.push($(this).attr("courtofficername"));
                        });

                        var lastIntanceJudges = [];
                        var lastIntanceJudgeNames = [];
                        $("a[name='lastCourtOfficer']").each(function () {
                            lastIntanceJudges.push($(this).attr("courtofficerno"));
                            lastIntanceJudgeNames.push($(this).attr("courtofficername"));
                        });

                        var lastIntanceClerks = [];
                        var lastIntanceClerkNames = [];
                        $("a[name='lastCourtClerk']").each(function () {
                            lastIntanceClerks.push($(this).attr("courtofficerno"));
                            lastIntanceClerkNames.push($(this).attr("courtofficername"));
                        });


                        data["Case.Basic.FirstIntanceCourt"] = $("#Case_Basic_FirstIntanceCourt").val();
                        data["Case.Basic.FirstIntanceCourtRoom"] = $("#Case_Basic_FirstIntanceCourtRoom").val();
                        data["Case.Basic.FirstIntanceJudge"] = firstIntanceJudges.join(",");
                        data["Case.Basic.FirstIntanceClerk"] = firstIntanceClerks.join(",");
                        data["Case.Basic.FirstIntanceCaseNo"] = $("#Case_Basic_FirstIntanceCaseNo").val();
                        data["Case.Basic.FirstIntanceRegisterDate"] = $("#Case_Basic_FirstIntanceRegisterDate").val();
                        data["Case.Basic.FirstIntanceLawfulDay"] = $("#Case_Basic_FirstIntanceLawfulDay").val();
                        data["Case.Basic.FirstIntanceJudgmentDate"] = $("#Case_Basic_FirstIntanceJudgmentDate").val();

                        data["Case.Basic.SecondIntanceCourt"] = $("#Case_Basic_SecondIntanceCourt").val();
                        data["Case.Basic.SecondIntanceCourtRoom"] = $("#Case_Basic_SecondIntanceCourtRoom").val();
                        data["Case.Basic.SecondIntanceJudge"] = secondIntanceJudges.join(",");
                        data["Case.Basic.SecondIntanceClerk"] = secondIntanceClerks.join(",");
                        data["Case.Basic.SecondIntanceCaseNo"] = $("#Case_Basic_SecondIntanceCaseNo").val();
                        data["Case.Basic.SecondIntanceRegisterDate"] = $("#Case_Basic_SecondIntanceRegisterDate").val();
                        data["Case.Basic.SecondIntanceLawfulDay"] = $("#Case_Basic_SecondIntanceLawfulDay").val();
                        data["Case.Basic.SecondIntanceJudgmentDate"] = $("#Case_Basic_SecondIntanceJudgmentDate").val();

                        data["Case.Basic.ExecutionIntanceCourt"] = $("#Case_Basic_ExecutionIntanceCourt").val();
                        data["Case.Basic.ExecutionIntanceCourtRoom"] = $("#Case_Basic_ExecutionIntanceCourtRoom").val();
                        data["Case.Basic.ExecutionIntanceJudge"] = executionIntanceJudges.join(",");
                        data["Case.Basic.ExecutionIntanceClerk"] = executionIntanceClerks.join(",");
                        data["Case.Basic.ExecutionIntanceCaseNo"] = $("#Case_Basic_ExecutionIntanceCaseNo").val();
                        data["Case.Basic.ExecutionIntanceRegisterDate"] = $("#Case_Basic_ExecutionIntanceRegisterDate").val();
                        data["Case.Basic.ExecutionIntanceLawfulDay"] = $("#Case_Basic_ExecutionIntanceLawfulDay").val();
                        data["Case.Basic.ExecutionIntanceJudgmentDate"] = $("#Case_Basic_ExecutionIntanceJudgmentDate").val();

                        data["Case.Basic.LastIntanceCourt"] = $("#Case_Basic_LastIntanceCourt").val();
                        data["Case.Basic.LastIntanceCourtRoom"] = $("#Case_Basic_LastIntanceCourtRoom").val();
                        data["Case.Basic.LastIntanceJudge"] = lastIntanceJudges.join(",");
                        data["Case.Basic.LastIntanceClerk"] = lastIntanceClerks.join(",");
                        data["Case.Basic.LastIntanceCaseNo"] = $("#Case_Basic_LastIntanceCaseNo").val();
                        data["Case.Basic.LastIntanceRegisterDate"] = $("#Case_Basic_LastIntanceRegisterDate").val();
                        data["Case.Basic.LastIntanceLawfulDay"] = $("#Case_Basic_LastIntanceLawfulDay").val();
                        data["Case.Basic.LastIntanceJudgmentDate"] = $("#Case_Basic_LastIntanceJudgmentDate").val();


                        //公安机关
                        data["Case.Basic.PublicSecurityUnitName"] = $("#Case_Basic_PublicSecurityUnitName").val();
                        data["Case.Basic.PublicSecurityUnitCaseNo"] = $("#Case_Basic_PublicSecurityUnitCaseNo").val();
                        data["Case.Basic.PublicSecurityUnitAddress"] = $("#Case_Basic_PublicSecurityUnitAddress").val();
                        data["Case.Basic.PublicSecurityUnitPhone"] = $("#Case_Basic_PublicSecurityUnitPhone").val();
                        data["Case.Basic.PublicSecurityUnitOperator"] = $("#Case_Basic_PublicSecurityUnitOperator").val();
 
                        //一审检查机关
                        data["Case.Basic.FirstIntanceProcuratorateUnitName"] = $("#Case_Basic_FirstIntanceProcuratorateUnitName").val();
                        data["Case.Basic.FirstIntanceProcuratorateUnitCaseNo"] = $("#Case_Basic_FirstIntanceProcuratorateUnitCaseNo").val();
                        data["Case.Basic.FirstIntanceProcuratorateUnitAddress"] = $("#Case_Basic_FirstIntanceProcuratorateUnitAddress").val();
                        data["Case.Basic.FirstIntanceProcuratorateUnitOperator"] = $("#Case_Basic_FirstIntanceProcuratorateUnitOperator").val();
                        data["Case.Basic.FirstIntanceProcuratorateUnitPhone"] = $("#Case_Basic_FirstIntanceProcuratorateUnitPhone").val();

                        //二审检查机关
                        data["Case.Basic.SecondIntanceProcuratorateUnitName"] = $("#Case_Basic_SecondIntanceProcuratorateUnitName").val();
                        data["Case.Basic.SecondIntanceProcuratorateUnitCaseNo"] = $("#Case_Basic_SecondIntanceProcuratorateUnitCaseNo").val();
                        data["Case.Basic.SecondIntanceProcuratorateUnitAddress"] = $("#Case_Basic_SecondIntanceProcuratorateUnitAddress").val();
                        data["Case.Basic.SecondIntanceProcuratorateUnitOperator"] = $("#Case_Basic_SecondIntanceProcuratorateUnitOperator").val();
                        data["Case.Basic.SecondIntanceProcuratorateUnitPhone"] = $("#Case_Basic_SecondIntanceProcuratorateUnitPhone").val();

                        //再审检查机关
                        data["Case.Basic.LastIntanceProcuratorateUnitName"] = $("#Case_Basic_LastIntanceProcuratorateUnitName").val();
                        data["Case.Basic.LastIntanceProcuratorateUnitCaseNo"] = $("#Case_Basic_LastIntanceProcuratorateUnitCaseNo").val();
                        data["Case.Basic.LastIntanceProcuratorateUnitAddress"] = $("#Case_Basic_LastIntanceProcuratorateUnitAddress").val();
                        data["Case.Basic.LastIntanceProcuratorateUnitOperator"] = $("#Case_Basic_LastIntanceProcuratorateUnitOperator").val();
                        data["Case.Basic.LastIntanceProcuratorateUnitPhone"] = $("#Case_Basic_LastIntanceProcuratorateUnitPhone").val();

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/Case/CourtCreateUpdate", data, function (response) {
                            if (response.IsSuccess) {
                                if (window.location.href.indexOf("Legal/CaseList/List") > 0) {
                                    c.Cases.List();
                                    $('#caseCourtModal').modal('hide');
                                }
                                else {
                                    window.location = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + response.Data.CaseNo;
                                }
                            }
                            else if (response.IsRedirect) {
                                window.location = AP_ROOT + 'Home/Index';
                            } else {
                                $.showModalMessageBox(response.Message);

                            }
                        });
                    } catch (e) {
                        alert(e);
                    }
                },
                CreateUpdate_NextStep: function (caseNo) {
                    window.location = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + caseNo;

                },
                CreateUpdate_Refersh: function (caseNo) {
                    window.location = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + caseNo;
                },
                FirstCourt: function (caseId,caseNo) {
                    var data =
                    {
                        caseId: caseId,
                        caseNo: caseNo,
                    };

                    var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/FirstCourtEdit";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#caseCourtModal').modal({ backdrop: 'static', keyboard: false });
                        $('#caseCourtModal').on('hidden.bs.modal', function () {
                            $("#caseCourtModal").remove();
                        });
                    });

                },
                SecondCourt: function (caseId, caseNo) {
                    var data =
                    {
                        caseId: caseId,
                        caseNo: caseNo,
                    };

                    var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/SecondCourtEdit";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#caseCourtModal').modal({ backdrop: 'static', keyboard: false });
                        $('#caseCourtModal').on('hidden.bs.modal', function () {
                            $("#caseCourtModal").remove();
                        });
                    });
                },
                ExecutionCourt: function (caseId, caseNo) {
                    var data =
                    {
                        caseId: caseId,
                        caseNo: caseNo,
                    };

                    var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/ExecutionCourtEdit";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#caseCourtModal').modal({ backdrop: 'static', keyboard: false });
                        $('#caseCourtModal').on('hidden.bs.modal', function () {
                            $("#caseCourtModal").remove();
                        });
                    });

                },
                LastCourt: function (caseId, caseNo) {
                    var data =
                    {
                        caseId: caseId,
                        caseNo: caseNo,
                    };

                    var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/LastCourtEdit";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#caseCourtModal').modal({ backdrop: 'static', keyboard: false });
                        $('#caseCourtModal').on('hidden.bs.modal', function () {
                            $("#caseCourtModal").remove();
                        });
                    });
                },
                CourtEdit: function (intance,caseId, caseNo)
                {
                    if (intance == "FirstIntance") {
                        c.Cases.Case.Court.FirstCourt(caseId, caseNo);
                    }
                    else if (intance == "SecondIntance") {
                        c.Cases.Case.Court.SecondCourt(caseId, caseNo);
                    }
                    else if (intance == "ExecutionIntance") {
                        c.Cases.Case.Court.ExecutionCourt(caseId, caseNo);
                    }
                    else if (intance == "LastIntance") {
                        c.Cases.Case.Court.LastCourt(caseId, caseNo);
                    }
                }
            },

            ProcuratorateUnit: {
                CreateUpdate: function () {
                    try {
                        var data = {};
                        data["Case.Basic.CaseNo"] = $("#Case_Basic_CaseNo").val();

                        data["Case.Basic.FirstIntanceCourt"] = $("#Case_Basic_FirstIntanceCourt").val();
                        data["Case.Basic.FirstIntanceCourtRoom"] = $("#Case_Basic_FirstIntanceCourtRoom").val();
                        data["Case.Basic.FirstIntanceJudge"] = $("#Case_Basic_FirstIntanceJudge").val();
                        data["Case.Basic.FirstIntanceClerk"] = $("#Case_Basic_FirstIntanceClerk").val();
                        data["Case.Basic.FirstIntanceCaseNo"] = $("#Case_Basic_FirstIntanceCaseNo").val();
                        data["Case.Basic.FirstIntanceRegisterDate"] = $("#Case_Basic_FirstIntanceRegisterDate").val();
                        data["Case.Basic.FirstIntanceLawfulDay"] = $("#Case_Basic_FirstIntanceLawfulDay").val();
                        data["Case.Basic.FirstIntanceJudgmentDate"] = $("#Case_Basic_FirstIntanceJudgmentDate").val();

                        data["Case.Basic.SecondIntanceCourt"] = $("#Case_Basic_SecondIntanceCourt").val();
                        data["Case.Basic.SecondIntanceCourtRoom"] = $("#Case_Basic_SecondIntanceCourtRoom").val();
                        data["Case.Basic.SecondIntanceJudge"] = $("#Case_Basic_SecondIntanceJudge").val();
                        data["Case.Basic.SecondIntanceClerk"] = $("#Case_Basic_SecondIntanceClerk").val();
                        data["Case.Basic.SecondIntanceCaseNo"] = $("#Case_Basic_SecondIntanceCaseNo").val();
                        data["Case.Basic.SecondIntanceRegisterDate"] = $("#Case_Basic_SecondIntanceRegisterDate").val();
                        data["Case.Basic.SecondIntanceLawfulDay"] = $("#Case_Basic_SecondIntanceLawfulDay").val();
                        data["Case.Basic.SecondIntanceJudgmentDate"] = $("#Case_Basic_SecondIntanceJudgmentDate").val();

                        data["Case.Basic.LastIntanceCourt"] = $("#Case_Basic_LastIntanceCourt").val();
                        data["Case.Basic.LastIntanceCourtRoom"] = $("#Case_Basic_LastIntanceCourtRoom").val();
                        data["Case.Basic.LastIntanceJudge"] = $("#Case_Basic_LastIntanceJudge").val();
                        data["Case.Basic.LastIntanceClerk"] = $("#Case_Basic_LastIntanceClerk").val();
                        data["Case.Basic.LastIntanceCaseNo"] = $("#Case_Basic_LastIntanceCaseNo").val();
                        data["Case.Basic.LastIntanceRegisterDate"] = $("#Case_Basic_LastIntanceRegisterDate").val();
                        data["Case.Basic.LastIntanceLawfulDay"] = $("#Case_Basic_LastIntanceLawfulDay").val();
                        data["Case.Basic.LastIntanceJudgmentDate"] = $("#Case_Basic_LastIntanceJudgmentDate").val();

                        //公安机关
                        data["Case.Basic.PublicSecurityUnitName"] = $("#Case_Basic_PublicSecurityUnitName").val();
                        data["Case.Basic.PublicSecurityUnitCaseNo"] = $("#Case_Basic_PublicSecurityUnitCaseNo").val();
                        data["Case.Basic.PublicSecurityUnitAddress"] = $("#Case_Basic_PublicSecurityUnitAddress").val();
                        data["Case.Basic.PublicSecurityUnitPhone"] = $("#Case_Basic_PublicSecurityUnitPhone").val();
                        data["Case.Basic.PublicSecurityUnitOperator"] = $("#Case_Basic_PublicSecurityUnitOperator").val();

                        //一审检查机关
                        data["Case.Basic.FirstIntanceProcuratorateUnitName"] = $("#Case_Basic_FirstIntanceProcuratorateUnitName").val();
                        data["Case.Basic.FirstIntanceProcuratorateUnitCaseNo"] = $("#Case_Basic_FirstIntanceProcuratorateUnitCaseNo").val();
                        data["Case.Basic.FirstIntanceProcuratorateUnitAddress"] = $("#Case_Basic_FirstIntanceProcuratorateUnitAddress").val();
                        data["Case.Basic.FirstIntanceProcuratorateUnitOperator"] = $("#Case_Basic_FirstIntanceProcuratorateUnitOperator").val();
                        data["Case.Basic.FirstIntanceProcuratorateUnitPhone"] = $("#Case_Basic_FirstIntanceProcuratorateUnitPhone").val();

                        //二审检查机关
                        data["Case.Basic.SecondIntanceProcuratorateUnitName"] = $("#Case_Basic_SecondIntanceProcuratorateUnitName").val();
                        data["Case.Basic.SecondIntanceProcuratorateUnitCaseNo"] = $("#Case_Basic_SecondIntanceProcuratorateUnitCaseNo").val();
                        data["Case.Basic.SecondIntanceProcuratorateUnitAddress"] = $("#Case_Basic_SecondIntanceProcuratorateUnitAddress").val();
                        data["Case.Basic.SecondIntanceProcuratorateUnitOperator"] = $("#Case_Basic_SecondIntanceProcuratorateUnitOperator").val();
                        data["Case.Basic.SecondIntanceProcuratorateUnitPhone"] = $("#Case_Basic_SecondIntanceProcuratorateUnitPhone").val();

                        //再审检查机关
                        data["Case.Basic.LastIntanceProcuratorateUnitName"] = $("#Case_Basic_LastIntanceProcuratorateUnitName").val();
                        data["Case.Basic.LastIntanceProcuratorateUnitCaseNo"] = $("#Case_Basic_LastIntanceProcuratorateUnitCaseNo").val();
                        data["Case.Basic.LastIntanceProcuratorateUnitAddress"] = $("#Case_Basic_LastIntanceProcuratorateUnitAddress").val();
                        data["Case.Basic.LastIntanceProcuratorateUnitOperator"] = $("#Case_Basic_LastIntanceProcuratorateUnitOperator").val();
                        data["Case.Basic.LastIntanceProcuratorateUnitPhone"] = $("#Case_Basic_LastIntanceProcuratorateUnitPhone").val();


                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/Case/ProcuratorateUnitCreateUpdate", data, function (response) {
                            if (response.IsSuccess) {
                                window.location = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + response.Data.CaseNo;
                            }
                            else if (response.IsRedirect) {
                                window.location = AP_ROOT + 'Home/Index';
                            } else {
                                $.showModalMessageBox(response.Message);

                            }
                        });
                    } catch (e) {
                        alert(e);
                    }
                },
                CreateUpdate_NextStep: function (caseNo) {
                    window.location = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + caseNo;

                },
                CreateUpdate_Refersh: function (caseNo) {
                    window.location = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + caseNo;
                },
                FirstProcuratorateUnit: function () {
                    var data =
                    {
                        caseId: $("#Case_Basic_CaseId").val(),
                        caseNo: $("#Case_Basic_CaseNo").val(),
                    };

                    var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/FirstProcuratorateUnitEdit";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {

                        
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#caseProcuratorateUnitModal').modal({ backdrop: 'static', keyboard: false });
                        $('#caseProcuratorateUnitModal').on('hidden.bs.modal', function () {
                            $("#caseProcuratorateUnitModal").remove();
                        });
                    });

                },
                SecondProcuratorateUnit: function () {
                    var data =
                    {
                        caseId: $("#Case_Basic_CaseId").val(),
                        caseNo: $("#Case_Basic_CaseNo").val(),
                    };

                    var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/SecondProcuratorateUnitEdit";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#caseProcuratorateUnitModal').modal({ backdrop: 'static', keyboard: false });
                        $('#caseProcuratorateUnitModal').on('hidden.bs.modal', function () {
                            $("#caseProcuratorateUnitModal").remove();
                        });
                    });
                },
                LastProcuratorateUnit: function () {
                    var data =
                    {
                        caseId: $("#Case_Basic_CaseId").val(),
                        caseNo: $("#Case_Basic_CaseNo").val(),
                    };

                    var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/LastProcuratorateUnitEdit";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(document.body).append(result);
                        $('#caseProcuratorateUnitModal').modal({ backdrop: 'static', keyboard: false });
                        $('#caseProcuratorateUnitModal').on('hidden.bs.modal', function () {
                            $("#caseProcuratorateUnitModal").remove();
                        });
                    });
                },
            },

            CasePhases: {
                CasePhase: {
                    Create: function (treeNode, parentFileTypeId, fileTypeName) {
                        var data = {
                            parentFileTypeId: parentFileTypeId,
                            caseNo: $("#Case_Basic_CaseNo").val(),
                            fileTypeName: fileTypeName
                        };

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CasePhaseType/CasePhaseTypeCreate", data, function (response) {
                            if (response.IsSuccess) {
                                var zTree = $.fn.zTree.getZTreeObj("casePhaseTree");
                                zTree.addNodes(treeNode, { id: response.Data.CasePhaseType.FileTypeId, pId: treeNode.id, name: response.Data.CasePhaseType.FileTypeName, typeId: response.Data.CasePhaseType.TypeId });
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },
                    Rename: function (fileTypeId, fileTypeName) {
                        var data = {
                            fileTypeId: fileTypeId,
                            fileTypeName: fileTypeName
                        };

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CasePhaseType/CasePhaseTypeRename", data, function (response) {
                            if (response.IsSuccess) {
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },
                    Remove: function (fileTypeId) {
                        var data = {
                            fileTypeId: fileTypeId,
                        };

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CasePhaseType/CasePhaseTypeRemove", data, function (response) {
                            if (response.IsSuccess) {
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },
                    RemoveCheck: function (fileTypeId) {
                        var data = {
                            fileTypeId: fileTypeId,
                        };

                        $.ajaxSetup({
                            async: false
                        });

                        var canRemove = false;
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CasePhaseType/CasePhaseTypeRemoveCheck", data, function (response) {
                            $.ajaxSetup({
                                async: true
                            });
                            if (response.IsSuccess) {
                                if (!response.Data.CanRemove) {
                                    $.showModalMessageBox("目录存在子目录或文件,不允许删除.");
                                }
                                canRemove = response.Data.CanRemove
                            } else {
                                $.showModalMessageBox(response.Message);
                                return false;
                            }
                        });
                        return canRemove;
                    },
                    Open: function (caseNos) {
                        var data = {};
                        var url = AP_ROOT + AP_PAGE_ID + "/Legal/CasePhase/CasePhaseEdit";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $("#hidCaseNos").val(caseNos);
                            $('#casePhaseTypeModal').modal({ backdrop: 'static', keyboard: false });
                            $('#casePhaseTypeModal').on('hidden.bs.modal', function () {
                                $("#casePhaseTypeModal").remove();
                            });
                        });
                    },
                    Change: function (caseNos) {
                        var treeObj = $.fn.zTree.getZTreeObj("casePhaseTypeTree");
                        var nodes = treeObj.getCheckedNodes(true);
                        if (nodes[0].isParent)
                        {
                            $.showTips("不允许选择父阶段", 0, 3);
                            return false;
                        }
                        if (nodes.length > 0) {
                            var data = {
                                caseNos: caseNos,
                                casePhaseId: nodes[0].id
                            };
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/Case/CasePhaseTypeChange", data, function (response) {
                                if (response.IsSuccess) {
                                    $.showTips("变更成功", 0, 3);
                                    $('#casePhaseTypeModal').modal('hide');
                                    if ($("#Case_Basic_CaseNo").length > 0)
                                    {
                                        window.location = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + $("#Case_Basic_CaseNo").val();
                                    }
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });
                        }
                        else {
                            $.showTips("请选择阶段", 0, 3);
                        }
                    },
                },
            },
            
            CaseFiles: {
                Init: function () {
                    c.Cases.Case.CaseFiles.List();
                },
                /*文档类表*/
                Layout: function () {
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFile/CaseFileList", {}, function (response) {
                        if (response.IsSuccess) {
                            $.openLoading();
                            $("#dv_List").empty();
                            $("#dv_List").html(response.Data);
                            $(document).ready(function () {
                                c.Cases.Case.CaseFiles.CaseFile.WebUploader.Setting();
                                c.Cases.Case.CaseFiles.List();
                                c.Cases.Case.CaseFiles.CaseFileType.List();
                                c.ResetSize();
                            });
                        }
                    });
                },

                /*文档类表*/
                List: function (fileType) {
                    var fileTypeId = fileType == null ? 7 : fileType.typeId;
                    var data = {
                        fileTypeId: fileType == null ? null : fileType.fileTypeId,
                        caseNo: $("#Case_Basic_CaseNo").val(),
                        pageNo: $("#PageNo").val(),
                        pageSize: $("#PageSize").val()
                    };
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFile/GetCaseFileList", data, function (response) {
                        if (response.IsSuccess) {
                            $("tbody", "#tblCaseFile").clearRow();
                            if (response.Data.TotalItemCount > 0) {
                                $(".info_inall.layoutfix").show();
                                var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                                var picfiles = new Array('jpg', 'tif', 'pdf', "png");
                                $.each(response.Data.CaseFiles, function (i, f) {

                                    var extName = f.FileName.substring(f.FileName.lastIndexOf('.') + 1, f.FileName.length);
                                    var html = '';
                                    if (fileTypeId >= 7 &&
                                        ($("#Case_Basic_CasePhaseId").val() != "106012"
                                        && $("#Case_Basic_CasePhaseId").val() != "301042"
                                        && $("#Case_Basic_CasePhaseId").val() != "401042"
                                        && $("#Case_Basic_CasePhaseId").val() != "501042")
                                        && $.inArray(extName.toLowerCase(), officefiles) > -1) {
                                        html += 
                                        "<a style='color: #039' href='javascript:void(0);' onclick='javascript:c.Cases.Case.CaseFiles.CaseFile.View(" + f.FileId + ",\"" + fileTypeId + "\",\"" + f.FileName + "\",\"" + f.OnlineUrl + "\"); '><span>查看</span></a>&nbsp;" +
                                        "<a style='color: #039' href='javascript:void(0);' onclick='javascript:c.Cases.Case.CaseFiles.CaseFile.Download(" + f.FileId + ",\"" + fileTypeId + "\"); '><span>下载</span></a>&nbsp; " +
                                        "<a style='color: #039' href='javascript:void(0);' onclick='javascript:c.Cases.Case.CaseFiles.CaseFile.Edit(" + f.FileId + ",\"" + fileTypeId + "\",\"" + f.FileName + "\",\"" + f.OnlineUrl + "\"); '><span>编辑</span></a>" 
                                    }
                                    else {
                                        html += "<a style='color: #039' href='javascript:void(0);' onclick='javascript:c.Cases.Case.CaseFiles.CaseFile.View(" + f.FileId + ",\"" + fileTypeId + "\",\"" + f.FileName + "\",\"" + f.OnlineUrl + "\"); '><span>查看</span></a>&nbsp;" +
                                        "<a style='color: #039' href='javascript:void(0);' onclick='javascript:c.Cases.Case.CaseFiles.CaseFile.Download(" + f.FileId + ",\"" + fileTypeId + "\"); '><span>下载</span></a>" 
                                    }

                                    $("tbody", "#tblCaseFile").addRow(
                                        "<input type='checkbox' id='chkFileId' name='chkFileId' class='ng-pristine ng-valid'   name=" + f.FileId + "'   value=" + f.FileId + ">",
                                        "<span  class='fileId'    style='display:none' >" + f.FileId + "</span>" +
                                        "<span  class='fileName'  style='display:none' >" + f.FileName + "</span>" +
                                        "<span  class='caseNo'    style='display:none' >" + f.CaseNo + "</span>" +
                                        "<span>" + (i+1) + "</span>",
                                        f.UploadingUserName,
                                        f.FileName,
                                         getDate(convertJsonDateToJSDate(f.UploadingTime)), 
                                        html 
                                     );
                                });

                                $("tfoot", "#tblCaseFile").show();
                                $(".simple-grid-none-data-wrap").hide();
 
                                $(".pull-right.page-box.casefile").cPaging({
                                    totalCount: response.Data.TotalItemCount,
                                    pageNo: response.Data.PageNo,
                                    pageSize: response.Data.PageSize,
                                    callBack: c.Cases.Case.CaseFiles.List,
                                    callBackArgs: fileType
                                });
                                if (response.Data.CaseFiles.length > 5) {
                                    $("#table_dropdown").removeClass("dropdown");
                                    $("#table_dropdown").addClass("dropup");
                                }
                                else {
                                    $("#table_dropdown").removeClass("dropup");
                                    $("#table_dropdown").addClass("dropdown");
                                }

                                if (fileType != null && (fileType.typeId == 7 || fileType.typeId == 8 || fileType.typeId == 9 || fileType.typeId == 10
                                                     || fileType.typeId == 11 || fileType.typeId == 12 || fileType.typeId == 13 || fileType.typeId == 14
                                                     || fileType.typeId == 15 || fileType.typeId == 70)) {
                                    $("#btnCaseFileDelete").show();
                                    $("#btnCaseFileTypeIdChange").show();
                                }
                                else {
                                    $("#btnCaseFileDelete").hide();
                                    $("#btnCaseFileTypeIdChange").hide();
                                }
                            } else {
                                var top = (parseInt($("#btnCaseFileUpload_none_data").height()) - 27) / 2; // 44：按钮的高度
                                var left = (parseInt($("#btnCaseFileUpload_none_data").width()) - 68) / 2; // 168：按钮的宽度
                                $('#btnCaseFileUpload_none_data div:eq(1)').attr('style', 'position: absolute; top: ' + top + 'px; left: ' + left + 'px; width: 68px; height: 27px; overflow: hidden; bottom: auto; right: auto;');
                                $("tfoot", "#tblCaseFile").hide();
                                $(".simple-grid-none-data-wrap").show();
                            }
                            c.ResetSize();
                        }
                    });
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
                BindMenu: function () {
                    $('#casegridSection').contextMenu('fileMenu', {
                        menuStyle: {
                            width: '152px'
                        },

                        itemStyle: {
                            width: '150px'
                        },

                        bindings: {
                            'create': function (t, e) {
                                c.Cases.Case.CaseFiles.CaseFile.Open(false);
                            },
                            'view': function (t, e) {
                                var caseFileId = $(e).find("span").text();
                                if (caseFileId == '') {
                                    $.showModalMessageBox("请选择查看的文件.");
                                    return false;
                                }

                                var caseFileName = $(e).find("lable").text();
                                if (caseFileName == '') {
                                    $.showModalMessageBox("无文件.");
                                    return false;
                                }

                                var caseno = $(e).find("div").text();

                                var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                                var picfiles = new Array('jpg', 'tif', 'pdf');
                                var extName = caseFileName.substring(caseFileName.lastIndexOf('.') + 1, caseFileName.length);

                                if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                                    var path = GV_LS.OfficeOnlineUrl + GV_LS.IPROnlineUrl + "CaseFiles/" + caseno + "/" + caseFileName;
                                    window.open(path);
                                }
                                else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                                    var path = GV_LS.IPROnlineUrl + "CaseFiles/" + caseno + "/" + caseFileName;
                                    window.open(path);
                                } else {
                                    c.Cases.Case.CaseFiles.CaseFile.Download(caseFileId);
                                }

                                return true;
                            },
                            'download': function (t, e) {
                                var caseFileId = $(e).find("span").text();
                                if (caseFileId == '') {
                                    $.showModalMessageBox("请选择查看的文件.");
                                    return false;
                                }
                                c.Cases.Case.CaseFiles.CaseFile.Download(caseFileId);
                                return true;
                            },
                            'unlock': function (t, e) {
                                var caseFileId = $(e).find("span").text();
                                if (caseFileId == '') {
                                    $.showModalMessageBox("请选择解锁的文件.");
                                    return false;
                                }
                                c.Cases.Case.CaseFiles.CaseFile.UnLock(caseFileId);
                                return true;
                            },
                            'tagTransformed': function (t, e) {
                                var caseFileId = $(e).find("span").text();
                                if (caseFileId == '') {
                                    $.showModalMessageBox("请选择待转文文件.");
                                    return false;
                                }
                                c.Cases.Case.CaseFiles.CaseFile.TagTransformed(caseFileId);
                                return true;
                            },
                            'delete': function (t, e) {
                                var caseFileId = $(e).find("span").text();
                                if (caseFileId == '') {
                                    $.showModalMessageBox("请选择解锁的文件.");
                                    return false;
                                }
                                c.Cases.Case.CaseFiles.CaseFile.Delete(caseFileId);
                                return true;
                            },
                            'toword': function (t, e) {
                                //var caseFileId = $(e).find("span").text();
                                //if (caseFileId == '') {
                                //    $.showModalMessageBox("请选择导出的文件.");
                                //    return false;
                                //}
                                //c.Cases.Case.CaseFiles.CaseFile.ToWord(caseFileId);
                                c.Cases.Case.CaseFiles.CaseFile.Open(true);
                                return true;
                            },
                            'cpc': function (t, e) {
                                c.Cases.Case.CaseFiles.CaseFile.CPC.Create();
                                return true;
                            },
                            'refresh': function (t, e) {
                                c.Cases.Case.CaseFiles.CaseFile.List();
                            },

                        },
                        onContextMenu: function (e) {
                            return true;
                        },
                        onShowMenu: function (e, menu) {

                            if ($("#Case_Basic_CaseTypeId").val() == "1" || $("#Case_Basic_CaseTypeId").val() == "2" || $("#Case_Basic_CaseTypeId").val() == "3") {
                                $('#cpc', menu).append("<span style='display:none'></span>");
                            }
                            else {
                                $('#cpc', menu).remove();
                            }
                            if ($(e.target).parents("tr").find(".fileId").hasClass("fileId")) {
                                var fileId = $(e.target).parents("tr").find(".fileId").text();
                                var caseNo = $(e.target).parents("tr").find(".caseNo").text();
                                var fileName = $(e.target).parents("tr").find(".fileName").text();
                                $('#view', menu).append("<span style='display:none'>" + fileId + "</span><lable style='display:none'>" + fileName + "</lable><div style='display:none'>" + caseNo + "</div>");
                                $('#download', menu).append("<span style='display:none'>" + fileId + "</span>");
                                $('#unlock', menu).append("<span style='display:none'>" + fileId + "</span>");
                                $('#tagTransformed', menu).append("<span style='display:none'>" + fileId + "</span>");
                                $('#toword', menu).append("<span style='display:none'>" + fileId + "</span>");
                                $('#delete', menu).append("<span style='display:none'>" + fileId + "</span>");
                            } else {
                                $('#view,#download', menu).remove();
                                $('#unlock', menu).remove();
                                $('#tagTransformed', menu).remove();
                                $('#delete', menu).remove();
                            }
                            return menu;
                        }
                    });
                },
                CaseFile: {
                    onRenName: function (e)
                    {
                        if ($(e).val().trim().length == 0) {
                            $(e).remove();
                            return;
                        }
                        else {
                            var data = {
                                caseFileId: $(e).parent().parent().find("#chkFileId").val(),
                                caseFileName: $(e).val(),
                            };
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFile/CaseFileRename", data, function (response) {
                                if (response.IsSuccess) {
                                    $(e).parent().html($(e).val());
                                    $(e).remove();
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });
                        }
                    },

                    onEditName: function (e)
                    {
                        if (!$(e).find("input").length) {
                            $(e).html("<input onblur='javascript:c.Cases.Case.CaseFiles.CaseFile.onRenName(this);' class='item_CaseFileName form-control' style=' background-color:yellow;border:0px'  type='text' value='" + $(e).html() + "'></input>");
                            $(e).find("input").focus();
                        }
                    },

                    /*上传文件*/
                    Open: function (caseFileTypeId) {

                        if (parseInt($("#Case_Basic_CaseId").val()) == 0) {
                            $.showModalMessageBox("请先保存案件基本资料.");
                            return false;
                        }
                        var data =
                        {
                            caseId: $("#Case_Basic_CaseId").val(),
                            caseNo: $("#Case_Basic_CaseNo").val(),
                            caseTypeId: $("#Case_Basic_CaseTypeId").val(),
                            caseFileTypeId: caseFileTypeId,
                        };

                        var url = AP_ROOT + AP_PAGE_ID + "/Legal/CaseFile/CaseFileUpload";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#caseFileUploadingModal').modal({ backdrop: 'static', keyboard: false });
                            $('#caseFileUploadingModal').on('hidden.bs.modal', function () {
                                $("#caseFileUploadingModal").remove();
                            });

                            var caseFileType = new AssociateCaseFileType(
                                $("#div_CaseFileTypeList"),
                                $("#CaseFileTypeId"),
                                $("#CaseFileTypeName"),
                                $("#Case_Basic_CaseTypeId").val(),
                                $("#IsTransformedFile").val() == 'true',
                               null
                            );
                        });
                    },
                    MultiOpen: function (caseNos, caseFileTypeId) {
                        if (caseNos == null || caseNos.length == 0) {
                            $.showModalMessageBox("请选择案件.");
                            return false;
                        }
                        var data = {
                            caseNos: caseNos.join(','),
                            caseFileTypeId: caseFileTypeId
                        };
                        var url = AP_ROOT + AP_PAGE_ID + "/Legal/CaseFile/MultiCaseFileUpload";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(".slide-panel-container").empty();
                            $(".slide-panel-container").append(result);
                            $(".slide-panel-container").addClass("show-panel");
                        });
                    },
                    Close: function () {
                        $('#caseFileUploadingModal').modal('hide');
                    },
                    CreateUpdate: function () {

                        if ($("#flCaseFile").val() == "") {
                            $.showModalMessageBox("请选择文档文件.");
                            return false;
                        }

                        if ($("#UploadingTime").val() == "") {
                            $.showModalMessageBox("请输入" + $(".spanreferencedate").text());
                            return false;
                        }

                        $.openLoading();
                        $('#uploadingForm').ajaxSubmit({
                            success: function (response) {
                                $.closeLoading();
                                if (response.IsSuccess) {
                                    $('#caseFileUploadingModal').modal('hide');
                                    c.Cases.Case.CaseFiles.List();
                                    return true;
                                } else {
                                    $.showModalMessageBox(response.Message);
                                    return false;
                                }
                            }
                        });
                    },
                    View: function (fileId, fileTypeId, fileName,fileOnlinePath) {
                        var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                        var picfiles = new Array('jpg', 'tif', 'pdf',"png");
                        var extName = fileName.substring(fileName.lastIndexOf('.') + 1, fileName.length);

                        
                        if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                            
                            var path = GV_LS.OfficeOnlineUrl + fileOnlinePath;
                            window.open(path);
                        }
                        else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                            var path = fileOnlinePath;
                            window.open(path);
                        } else {
                            c.Cases.Case.CaseFiles.CaseFile.Download(fileId, fileTypeId);
                        }

                        return true;
                    },
                    Edit: function (fileId, fileTypeId, fileName, fileOnlinePath) {

                        var url = AP_ROOT + AP_PAGE_ID + "/Legal/CaseFile/CaseFileWordEdit?caseFileId=" + fileId;
                        POBrowser.openWindowModeless(url, 'fullscreen=yes;');

                        //var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
                        //var picfiles = new Array('jpg', 'tif', 'pdf', "png");
                        //var extName = fileName.substring(fileName.lastIndexOf('.') + 1, fileName.length);

                        //if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                        //    var path = GV_LS.OfficeOnlineUrl + fileOnlinePath;
                        //    window.open(path);
                        //}
                        //else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                        //    var path = fileOnlinePath;
                        //    window.open(path);
                        //} else {
                        //    c.Cases.Case.CaseFiles.CaseFile.Download(fileId, fileTypeId);
                        //}

                        return true;
                    },
                    Download: function (caseFileId, caseFileTypeId) {
                        window.open(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFileCenter/CaseFileDownloadByFileTypeId?caseFileId=" + caseFileId + "&caseFileTypeId=" + caseFileTypeId);
                        return true;
                    },
                    Delete: function (caseFileIds) {

                        if (caseFileIds.length == 0)
                        {
                            $.showModalMessageBox("请选择文件.");
                            return false;
                        }

                        $.showModalConfirmDialog("确定删除文件？", "c.Cases.Case.CaseFiles.CaseFile.DeleteCallBack", caseFileIds);
                        return true;
                    },
                    DeleteCallBack: function (caseFileIds) {
                        var data = { caseFileIds: caseFileIds };
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFile/CaseFileDelete", data, function (response) {
                            if (response.IsSuccess) {
                                $.showModalMessageBox("删除成功.");
                                // caseInfo.LoadCase($("#Case_Basic_CaseId").val())
                                var treeObj = $.fn.zTree.getZTreeObj("caseFileTree");
                                var nodes = treeObj.getSelectedNodes();
                                if (nodes.length > 0) {
                                    c.Cases.Case.CaseFiles.List({ fileTypeId: nodes[0].id, typeId: nodes[0].typeId });
                                }
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },

                    FileType: {
                        Create: function (treeNode, parentFileTypeId, fileTypeName)
                        {
                            var data = {
                                parentFileTypeId: parentFileTypeId,
                                caseNo: $("#Case_Basic_CaseNo").val(),
                                fileTypeName: fileTypeName
                            };
                            
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFileType/CaseFileTypeCreate", data, function (response) {
                                if (response.IsSuccess) {
                                    var zTree = $.fn.zTree.getZTreeObj("caseFileTree");
                                    zTree.addNodes(treeNode, { id: response.Data.CaseFileType.FileTypeId, pId: treeNode.id, name: response.Data.CaseFileType.FileTypeName,typeId:response.Data.CaseFileType.TypeId });
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });
                        },
                        Rename: function (fileTypeId, fileTypeName) {
                            var data = {
                                fileTypeId: fileTypeId,
                                fileTypeName: fileTypeName
                            };

                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFileType/CaseFileTypeRename", data, function (response) {
                                if (response.IsSuccess) {
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });
                        },
                        Remove: function (fileTypeId) {
                            var data = {
                                fileTypeId: fileTypeId,
                            };

                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFileType/CaseFileTypeRemove", data, function (response) {
                                if (response.IsSuccess) {
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });
                        },
                        RemoveCheck: function (fileTypeId) {
                            var data = {
                                fileTypeId: fileTypeId,
                            };

                            $.ajaxSetup({
                                async: false
                            });

                            var canRemove = false;
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFileType/CaseFileTypeRemoveCheck", data, function (response) {
                                $.ajaxSetup({
                                    async: true
                                });
                                if (response.IsSuccess) {
                                    if (!response.Data.CanRemove) {
                                        $.showModalMessageBox("目录存在子目录或文件,不允许删除.");
                                    }
                                    canRemove = response.Data.CanRemove
                                } else {
                                    $.showModalMessageBox(response.Message);
                                    return false;
                                }
                            });
                            return canRemove;
                        },
                        Open: function () {
                            var data = {};
                            var url = AP_ROOT + AP_PAGE_ID + "/Legal/CaseFile/FileType";
                            $.openLoading();

                            $("<div></div>").load(url, data, function (result) {
                                $.closeLoading();
                                $(document.body).append(result);
                                $('#caseFileTypeModal').modal({ backdrop: 'static', keyboard: false });
                                $('#caseFileTypeModal').on('hidden.bs.modal', function () {
                                    $("#caseFileTypeModal").remove();
                                });

                                var caseFileType = new AssociateCaseFileType(
                                   $("#div_CaseFileTypeList"),
                                   $("#CaseFileTypeId"),
                                   $("#CaseFileTypeName"),
                                   $("#Case_Basic_CaseTypeId").val(),
                                   $("#IsTransformedFile").val() == 'true',
                                  null
                               );
                            });
                        },
                        Change: function (caseFileIds) {

                            var treeObj = $.fn.zTree.getZTreeObj("caseFileTypeTree");
                            var nodes = treeObj.getCheckedNodes(true);
                            if (nodes.length > 0) {
                                var data = {
                                    caseFileIds: caseFileIds,
                                    fileTypeId: nodes[0].id
                                };
                                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFile/CaseFileTypeChange", data, function (response) {
                                    if (response.IsSuccess) {
                                        $.showModalMessageBox("变更成功.");
                                        var treeObj = $.fn.zTree.getZTreeObj("caseFileTree");
                                        var nodes = treeObj.getSelectedNodes();
                                        if (nodes.length > 0){
                                            c.Cases.Case.CaseFiles.List({ fileTypeId: nodes[0].id, typeId: nodes[0].typeId });
                                        }
                                        $('#caseFileTypeModal').modal('hide');
                                    } else {
                                        $.showModalMessageBox(response.Message);
                                    }
                                });
                            }
                            else {
                                $.showModalMessageBox("请选择文档目录.");
                            }
                        },
                    },
                    AuthorizationLetter: {
                        Create: function (caseNos) {

                            if (caseNos == null || caseNos.length == 0) {
                                $.showModalMessageBox("请选择案件.");
                                return false;
                            }
                            var data = { caseNos: caseNos };
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFile/AuthorizationLetterCreate", data, function (response) {
                                if (response.IsSuccess) {
                                    $.showModalMessageBox("生成成功.");
                                    window.open(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFileCenter/ExportTempFileDownload?fileName=" + response.Data.FileName);
                                    return true;
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });
                        },
                    },
                    LawyersLetter: {
                        Create: function (caseNos) {
                            if (caseNos == null || caseNos.length == 0) {
                                $.showModalMessageBox("请选择案件.");
                                return false;
                            }
                            var data = { caseNos: caseNos };
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFile/LawyersLetterCreate", data, function (response) {
                                if (response.IsSuccess) {
                                    $.showModalMessageBox("生成成功.");
                                    window.open(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFileCenter/ExportTempFileDownload?fileName=" + response.Data.FileName);
                                    return true;
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });
                        },
                    },
                    IdentificationLetter: {
                        Create: function (caseNos) {
                            if (caseNos == null || caseNos.length == 0) {
                                $.showModalMessageBox("请选择案件.");
                                return false;
                            }
                            var data = { caseNos: caseNos };
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFile/IdentificationLetterCreate", data, function (response) {
                                if (response.IsSuccess) {
                                    $.showModalMessageBox("生成成功.");
                                    window.open(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFileCenter/ExportTempFileDownload?fileName=" + response.Data.FileName);
                                    return true;
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });
                        },
                    },
                    SettlementList: {
                        Create: function (caseNos) {
                            if (caseNos == null || caseNos.length == 0) {
                                $.showModalMessageBox("请选择案件.");
                                return false;
                            }
                            var data = { caseNos: caseNos };
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFile/SettlementListCreate", data, function (response) {
                                if (response.IsSuccess) {
                                    $.showModalMessageBox("生成成功.");
                                    window.open(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFileCenter/ExportTempFileDownload?fileName=" + response.Data.FileName);
                                    return true;
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });
                        },
                    },

                    WebUploader: {
                        Setting: function ()
                        {
                            var _queue = [];
                            var _sucess_queue = [];
                            var uploader = WebUploader.create({

                                pick: {
                                    id: '.filePicker',
                                },
                                // 选完文件后，是否自动上传。
                                webkitdirectory: "webkitdirectory",
                                auto: true,
                                // swf文件路径
                                swf: '~/Resource/webuploader/Uploader.swf',
                                // 文件接收服务端。
                                server: AP_ROOT + AP_PAGE_ID + "/Legal/CaseFile/MultiCaseFileWebUpload",
                                // 选择文件的按钮。可选。
                                // 内部根据当前运行是创建，可能是input元素，也可能是flash.
                                //pick: '#picker',
                                disableGlobalDnd: true,
                                dnd: '#dropbox',
                                paste: '#dropbox',

                                // 不压缩image, 默认如果是jpeg，文件上传前会压缩一把再上传！
                                resize: false
                            });

                            // 拖拽时不接受 js, txt 文件。
                            uploader.on('dndAccept', function (items) {
                                var denied = false,
                                 len = items.length,
                                 i = 0,
                                 // 修改js类型
                                unAllowed = 'text/plain;application/javascript ';
                                for (; i < len; i++) {
                                    // 如果在列表里面
                                    if (~unAllowed.indexOf(items[i].type)) {
                                        denied = true;
                                        break;
                                    }
                                }
                                if (denied) return;
                                $("tbody", "#tblWebUploadList").empty();
                                $("#webuploaderlist").addClass("show-panel");
                            });
                            uploader.on('ready', function () {
                                window.uploader = uploader;
                            });
                            // 当有文件被添加进队列的时候
                            uploader.on('fileQueued', function (file) {
                                var itemTemplate = "";
                                var fileSize = parseInt(file.size / 1024);
                                if (fileSize >= 1024)
                                    fileSize = parseInt(fileSize / 1024) + "MB"
                                else
                                    fileSize = parseInt(fileSize) + "KB"

                                _queue.push(file);

                                itemTemplate = '<tr class="file-list" >'
                                             + '    <td style="text-align: left; ">' + file.name + '</td>'
                                             + '    <td style="text-align: left;  white-space: nowrap">' + fileSize + '</td>'
                                             + '    <td style="text-align: left; ">案件文档</td>'
                                             + '    <td id=' + file.id + ' style="text-align: left; ">'
                                             + '        <span  class="state">等待上传... </span>'
                                            + '      </td>'
                                            + '</tr>' + itemTemplate;
                                $("tbody", "#tblWebUploadList").append(itemTemplate);

                            });

                            uploader.on('beforeFileQueued', function (file) {
                                //_queue = [];
                                //_sucess_queue = [];
                            });

                            uploader.on('uploadBeforeSend', function (object, data, headers) {
                                data.relativepath = object.file.relativepath;
                                data.caseNos = $("#Case_Basic_CaseNo").val();
                                data.caseFileTypeId = $("#currentCaseFileTypeId").val(); //当前选中的Id

                            });

                            // 文件上传过程中创建进度条实时显示。
                            uploader.on('uploadProgress', function (file, percentage) {
                                var $li = $('#' + file.id),
                                    $percent = $li.find('.progress .progress-bar');
                                // 避免重复创建
                                if (!$percent.length) {
                                    $percent = $('<div class="progress progress-striped active" style="margin-bottom: 0px;">' +
                                      '<div class="progress-bar"  role="progressbar" style="width: 0%;">' +
                                      '</div>' +
                                    '</div>').appendTo($li).find('.progress-bar');
                                }
                                $li.find('span.state').text('上传中');
                                $percent.css('width', percentage * 100 + '%');
                            });

                            //文件成功、失败处理
                            uploader.on('uploadSuccess', function (file) {
                                $('#' + file.id).find('span.state').text('已上传');
                            });

                            //文件成功、失败处理
                            uploader.on('uploadFinished', function () {
                                c.Cases.Case.CaseFiles.CaseFileType .List();
                                c.Cases.Case.CaseFiles.List();

                                $.showTips("成功上传 " + _queue.length + " 个文件.", 0, 3);

                            });

                            uploader.on('uploadError', function (file) {
                                $('#' + file.id).find('span.state').text('上传出错');
                            });

                            uploader.on('uploadComplete', function (file) {
                                $('#' + file.id).find('.progress').fadeOut();
                            });
                        }
                    }
                },
                CaseFileType: {
                    Tree: {
                        zTreeOnClick: function (event, treeId, treeNode) {
                            $("#currentCaseFileTypeId").val(treeNode.id);
                            c.Cases.Case.CaseFiles.List({ fileTypeId: treeNode.id, typeId: treeNode.typeId });
                        },
                        beforeDrag: function (treeId, treeNodes) {
                            return false;
                        },
                        beforeEditName: function (treeId, treeNode) {
                            className = (className === "dark" ? "" : "dark");
                            var zTree = $.fn.zTree.getZTreeObj("caseFileTree");
                            zTree.selectNode(treeNode);
                            setTimeout(function () {
                                zTree.editName(treeNode);
                            }, 0);
                            return false;
                        },
                        beforeRemove: function (treeId, treeNode) {
                            className = (className === "dark" ? "" : "dark");
                            var zTree = $.fn.zTree.getZTreeObj("caseFileTree");
                            zTree.selectNode(treeNode);
                            var caseRemove = c.Cases.Case.CaseFiles.CaseFile.FileType.RemoveCheck(treeNode.id);
                            if (caseRemove) {
                                return confirm("确认删除目录 " + treeNode.name + " 吗？");
                            }
                            else {
                                return false;
                            }
                        },
                        onRemove: function (e, treeId, treeNode) {
                            c.Cases.Case.CaseFiles.CaseFile.FileType.Remove(treeNode.id);
                        },
                        beforeRename: function (treeId, treeNode, newName, isCancel) {
                            className = (className === "dark" ? "" : "dark");
                            if (newName.length == 0) {
                                setTimeout(function () {
                                    var zTree = $.fn.zTree.getZTreeObj("caseFileTree");
                                    zTree.cancelEditName();
                                    alert("节点名称不能为空.");
                                }, 0);
                                return false;
                            }
                            return true;
                        },
                        onRename: function (e, treeId, treeNode, isCancel) {
                            c.Cases.Case.CaseFiles.CaseFile.FileType.Rename(treeNode.id, treeNode.name);
                        },
                        showUploadBtn: function (treeId, treeNode) {

                            return false;
                            //return treeNode.typeId == 8 || treeNode.typeId == 9 || treeNode.typeId == 10
                            //   || treeNode.typeId == 11 || treeNode.typeId == 12 || treeNode.typeId == 13
                            //   || treeNode.typeId == 14 || treeNode.typeId == 15 || treeNode.typeId == 70;
                        },
                        showRemoveBtn: function (treeId, treeNode) {
                            return treeNode.typeId == 8 || treeNode.typeId == 9 || treeNode.typeId == 10
                               || treeNode.typeId == 11 || treeNode.typeId == 12 || treeNode.typeId == 13
                               || treeNode.typeId == 70;
                        },
                        showRenameBtn: function (treeId, treeNode) {
                            return treeNode.typeId == 8 || treeNode.typeId == 9 || treeNode.typeId == 10
                               || treeNode.typeId == 11 || treeNode.typeId == 12 || treeNode.typeId == 13
                               || treeNode.typeId == 70;
                        },
                        showLog: function (str) {
                            if (!log) log = $("#log");
                            log.append("<li class='" + className + "'>" + str + "</li>");
                            if (log.children("li").length > 8) {
                                log.get(0).removeChild(log.children("li")[0]);
                            }
                        },
                        getTime: function () {
                            var now = new Date(),
                            h = now.getHours(),
                            m = now.getMinutes(),
                            s = now.getSeconds(),
                            ms = now.getMilliseconds();
                            return (h + ":" + m + ":" + s + " " + ms);
                        },
                        addHoverDom: function (treeId, treeNode) {
                            if (treeNode.typeId == 7 || treeNode.typeId == 8 || treeNode.typeId == 9 || treeNode.typeId == 10
                               || treeNode.typeId == 11 || treeNode.typeId == 12 || treeNode.typeId == 13
                               || treeNode.typeId == 14 || treeNode.typeId == 15 || treeNode.typeId == 70) {
                                var sObj = $("#" + treeNode.tId + "_span");
                                if (treeNode.editNameFlag || $("#addBtn_" + treeNode.tId).length > 0) return;
                                var addStr = "<span class='button add' id='addBtn_" + treeNode.tId
                                    + "' title='新建文件夹' onfocus='this.blur();'></span>";

                                //var uploadStr = "<span class='button upload' id='uploadBtn_" + treeNode.tId
                                //    + "' title='上传文件' onfocus='this.blur();'></span>";

                                sObj.after(addStr);
                                var btn = $("#addBtn_" + treeNode.tId);

                                if (btn) btn.bind("click", function () {
                                    var fileTypeName = "新建文件夹" + (newCount++);
                                    c.Cases.Case.CaseFiles.CaseFile.FileType.Create(treeNode, treeNode.id, fileTypeName);
                                    return false;
                                });

                                //if (treeNode.editNameFlag || $("#uploadBtn_" + treeNode.tId).length > 0) return;

                                //var uploadStr = "<span class='button upload' id='uploadBtn_" + treeNode.tId
                                //    + "' title='上传文件' onfocus='this.blur();'></span>";

                                //sObj.after(uploadStr);

                                //var uploadBtn = $("#uploadBtn_" + treeNode.tId);
                                //if (uploadBtn) uploadBtn.bind("click", function () {
                                //    c.Cases.Case.CaseFiles.CaseFile.MultiOpen(new Array($('#Case_Basic_CaseNo').val()), treeNode.id);
                                //    return false;
                                //});
                            }
                            return false;
                        },
                        removeHoverDom: function (treeId, treeNode) {
                            $("#addBtn_" + treeNode.tId).unbind().remove();
                            $("#uploadBtn_" + treeNode.tId).unbind().remove();
                        },
                        selectAll: function () {
                            var zTree = $.fn.zTree.getZTreeObj("caseFileTree");
                            zTree.setting.edit.editNameSelectAll = $("#selectAll").attr("checked");
                        }
                    },
                    List: function () {
                        var data = {
                            caseNo: $("#Case_Basic_CaseNo").val()
                        };
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFileType/GetCaseFileTypeList", data, function (response) {
                            if (response.IsSuccess) {
                                if (response.Data.CaseFileTypes.length > 0) {
                                    var zNodes = [];
                                    $.each(response.Data.CaseFileTypes, function (i, fileType) {
                                        var node = {};
                                        node.id = fileType.FileTypeId;
                                        node.pId = fileType.ParentFileTypeId;
                                        node.name = fileType.FileTypeName;
                                        node.open = true;
                                        node.typeId = fileType.TypeId;
                                        if (node.name == "案件文档") {
                                            $("#currentCaseFileTypeId").val(fileType.FileTypeId);
                                        }
                                        zNodes.push(node);
                                    });
                                    $.fn.zTree.init($("#caseFileTree"), setting, zNodes);
                                }
                            }
                        });
                    }
                }
            },
            /*应收账款*/
            CaseFees: {
                /*案件费用列表*/
                List: function () {
                    var data = {
                        caseId: $("#Case_Basic_CaseId").val(),
                        pageNo: $("#PageNo").val(),
                        pageSize: $("#PageSize").val()
                    };
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFee/CaseFeeList", data, function (response) {

                        if (response.IsSuccess) {
                            $.openLoading();
                            $("#dv_List").empty();
                            $("#dv_List").html(response.Data);

                            $("tfoot", "#tblCaseFee").show();

                            $(".pull-right.page-box.casefee").cPaging({
                                totalCount: parseInt($("#TotalCount").val()),
                                pageNo: parseInt($("#PageNo").val()),
                                pageSize: parseInt($("#PageSize").val()),
                                callBack: c.Cases.Case.CaseFees.List,
                                callBackArgs: null
                            });

                            var totalCount = parseInt($("#TotalCount").val());

                            c.ResetSize();

                            if (totalCount > 0) {
                                $("tfoot", "#tblCaseFee").show();
                                $(".simple-grid-none-data-wrap").hide();
                            } else {
                                $("tfoot", "#tblCaseFee").hide();
                                $(".simple-grid-none-data-wrap").show();
                            }

                            //caseInfo.ARCaseFee.BindMenu();

                            $.closeLoading();
                        }
                    }, true);
                },
                CaseFee: {
                    Layout: function () {

                        var data = {
                            customerNo: $("#Case_Basic_CustomerNo").val()
                        };

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/Contract/GetContractListByCustomerNo", data, function (response) {
                            if (response.IsSuccess) {
                                $.openLoading();

                                tr = "<tr>"
                                         + "<td><select class='form-control' disable id='item_ContractId' ><option value='-1'>请选择</option></select></td>"
                                         + "<td><select class='form-control' disable id='item_CaseOfficeFeeTypeId' ><option value='-100'>请选择</option></select></td>"
                                         + "<td><input class='item_CaseOfficeFeeAmount form-control'  id='item_CaseOfficeFeeAmount' name='item_CaseOfficeFeeAmount' onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\" onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" type='text' value='0'></td>"
                                         + "<td><select class='form-control'  id='item_CaseNonOfficeFeeTypeId'><option value='-200'>请选择</option></select></td>"
                                         + "<td><input class='item_CaseNonOfficeFeeAmount form-control'  id='item_CaseNonOfficeFeeAmount' name='item_CaseNonOfficeFeeAmount'  onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\" onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" type='text' value='0'>"
                                         + "<td><select class='form-control'  id='item_CaseCommissionFeeTypeId'><option value='-300'>请选择</option></select></td>"
                                         + "<td><input class='item_CaseCommissionFeeAmount form-control'  id='item_CaseCommissionFeeAmount' name='item_CaseCommissionFeeAmount'  onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\" onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" type='text' value='0'>"
                                         + "<td><input class='item_Remark form-control' id='item_Remark'  type='text' value=''></td>"
                                         + "<td><a style='color:green;' href='javascript:void(0);'><span class='btn_ar_add glyphicon glyphicon-plus'></span></a>&nbsp;&nbsp;&nbsp;<a  style='color:red;' href='javascript:void(0);'><span class='btn_ar_remove glyphicon glyphicon-remove'></span></a></td>"
                                  + "</tr>";

                                $('#tblContractObjectList>tbody>tr:last').after(tr);

                                $("#tblContractObjectList tbody tr").each(function (i, e) {

                                    if ($(e).find("#item_ContractId option").length == 1) {
                                        $.each(response.Data, function (i, c) {
                                            $(e).find("#item_ContractId").append('<option value=' + c.ContractBasicInfo.ContractId + '>' + c.ContractBasicInfo.ContractNo + '</option>');
                                        });
                                    }

                                    if ($(e).find("#item_CaseOfficeFeeTypeId option").length == 1) {
                                        $.each(GV_LS.CaseFeeTypes, function (j, f) {
                                            if (f.TypeId == '1' && f.FeeTypeId != -100) {
                                                $(e).find("#item_CaseOfficeFeeTypeId").append('<option value=' + f.FeeTypeId + '>' + f.FeeTypeName + '</option>');
                                            }
                                        });

                                        $(e).find("#item_CaseOfficeFeeTypeId").val($(e).find("#item_CaseOfficeFeeTypeId").attr("caseOfficeFeeTypeId"));
                                    }

                                    if ($(e).find("#item_CaseNonOfficeFeeTypeId option").length == 1) {
                                        $.each(GV_LS.CaseFeeTypes, function (j, f) {
                                            if (f.TypeId == '2' && f.FeeTypeId != -200) {
                                                $(e).find("#item_CaseNonOfficeFeeTypeId").append('<option value=' + f.FeeTypeId + '>' + f.FeeTypeName + '</option>');
                                            }
                                        });

                                        $(e).find("#item_CaseNonOfficeFeeTypeId").val($(e).find("#item_CaseNonOfficeFeeTypeId").attr("caseNonOfficeFeeTypeId"));
                                    }

                                    if ($(e).find("#item_CaseCommissionFeeTypeId option").length == 1) {
                                        $.each(GV_LS.CaseFeeTypes, function (j, f) {
                                            if (f.TypeId == '3' && f.FeeTypeId != -300) {
                                                $(e).find("#item_CaseCommissionFeeTypeId").append('<option value=' + f.FeeTypeId + '>' + f.FeeTypeName + '</option>');
                                            }
                                        });

                                        $(e).find("#item_CaseCommissionFeeTypeId").val($(e).find("#item_CaseCommissionFeeTypeId").attr("caseCommissionFeeTypeId"));
                                    }
                                });

                                //caseInfo.ARCaseFee.Objects.ObjectItem.BindEvent();

                                $.closeLoading();
                            }
                        }, true);
                    },
                    Open: function () {
                        if (parseInt($("#Case_Basic_CaseId").val()) == 0) {
                            $.showModalMessageBox("请先保存案件基本资料.");
                            return false;
                        }

                        var data = {
                            customerNo: $("#Case_Basic_CustomerNo").val(),
                            contractNo: $("#Case_Basic_ContractNo").val()
                        };

                        var url = AP_ROOT + AP_PAGE_ID + "/Legal/CaseFee/Create";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#caseFeeModal').modal({ backdrop: 'static', keyboard: false });
                            $('#caseFeeModal').on('hidden.bs.modal', function () {
                                $("#caseFeeModal").remove();
                            });

                            //c.Cases.Case.CaseFees.CaseFee.Layout();
                        });

                    },
                    Edit: function (caseFeeId) {
                        if (parseInt($("#Case_Basic_CaseId").val()) == 0) {
                            $.showModalMessageBox("请先保存案件基本资料.");
                            return false;
                        }

                        var data = {
                            caseFeeId: caseFeeId
                        };

                        var url = AP_ROOT + AP_PAGE_ID + "/Legal/CaseFee/Edit";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#caseFeeModal').modal({ backdrop: 'static', keyboard: false });
                            $('#caseFeeModal').on('hidden.bs.modal', function () {
                                $("#caseFeeModal").remove();
                            });
                        });
                    },
                    Delete: function (caseFeeId) {
     
                        var data = {
                            caseFeeId: caseFeeId
                        };

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFee/Delete", data, function (response) {
                            if (response.IsSuccess) {

                                if (callback_func) {
                                    callback_func(response.Data.CaseFeeIds);
                                }
                                else {
                                    $.showModalMessageBox("保存成功.");
                                }

                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                        
                    },
                    Delete: function (caseFeeId) {
                        $.showModalConfirmDialog("确定删除？", "c.Cases.Case.CaseFees.CaseFee.DeleteCallBack", caseFeeId);
                        return true;
                    },
                    DeleteCallBack: function (caseFeeId) {
                        var data = { caseFeeId: caseFeeId };
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFee/CaseFeeDelete", data, function (response) {
                            if (response.IsSuccess) {
                                $.showModalMessageBox("删除成功.");
                                c.Cases.Case.CaseFees.List();
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },
                    Close: function () {
                        if ($('.slide-panel-container').length) {
                            $('.slide-panel-container').empty();
                            $('.slide-panel-container').removeClass('show-panel');
                        }
                        if ($('#caseFeeModal').length) {
                            $('#caseFeeModal').modal('hide');
                        }
                    },
                    CreateUpdate: function () {
                        try {

                            var data = {};
                            var dataIsNOk = false;

                            if ($("#CaseFee_ContractNo").val() == null) {
                                dataIsNOk = true;
                                $.showModalMessageBox("请选择合同,如无合同请联系客户管理人创建新合同.");
                                return false;
                            }

                            if ($("#CaseFee_CaseFeeTypeId").val() == '') {
                                dataIsNOk = true;
                                $.showModalMessageBox("请选择费用类型.");
                                return false;
                            }

                            if ($("#CaseFee_Amount").val() == '') {
                                $.showModalMessageBox("请输入金额.");
                                return false;
                            }

                            if (!$("#CaseFee_Amount").isMoney()) {
                                $.showModalMessageBox("金额格式不正确，请重新输入.");
                                return false;
                            }


                            var paidAmount = parseFloat($("#CaseFee_PaidAmount").val());
                            var invoicedAmount = parseFloat($("#CaseFee_InvoicedAmount").val());
                            var cashedAmount = parseFloat($("#CaseFee_CashedAmount").val());
                            var caseFeeAmount = parseFloat($("#CaseFee_Amount").val());

                            if (caseFeeAmount < paidAmount)
                            {
                                $.showModalMessageBox("已付款金额大于费用金额，不允许修改.");
                                return false;
                            }

                            //if (caseFeeAmount < invoicedAmount) {
                            //    $.showModalMessageBox("已开票金额大于费用金额，不允许修改.");
                            //    return false;
                            //}

                            if (caseFeeAmount < cashedAmount) {
                                $.showModalMessageBox("已回款金额大于费用金额，不允许修改.");
                                return false;
                            }

                            data["ContractObjects[0].ContractNo"] = $("#CaseFee_ContractNo").val();
                            //data["ContractObjects[0].ContractNo"] = $("#CaseFee_ContractNo").find('option:selected').text();

                            data["ContractObjects[0].CaseId"] = $("#Case_Basic_CaseId").val();
                            data["ContractObjects[0].CaseNo"] = $("#Case_Basic_CaseNo").val();

                            data["ContractObjects[0].CustomerNo"] = $("#Case_Basic_CustomerNo").val();

                            if ($("#CaseFee_FeeTypeId").val() == "1") {
                                data["ContractObjects[0].CaseOfficeFeeId"] = $("#CaseFee_CaseFeeId").val();
                                data["ContractObjects[0].CaseOfficeFeeTypeId"] = $("#CaseFee_CaseFeeTypeId").val();
                                data["ContractObjects[0].CaseOfficeFeeAmount"] = $("#CaseFee_Amount").val();
                            }
                            else if ($("#CaseFee_FeeTypeId").val() == "2") {
                                data["ContractObjects[0].CaseNonOfficeFeeId"] = $("#CaseFee_CaseFeeId").val();
                                data["ContractObjects[0].CaseNonOfficeFeeTypeId"] = $("#CaseFee_CaseFeeTypeId").val();
                                data["ContractObjects[0].CaseNonOfficeFeeAmount"] = $("#CaseFee_Amount").val();
                            }
                            else {
                                data["ContractObjects[0].CaseCommissionFeeId"] = $("#CaseFee_CaseFeeId").val();
                                data["ContractObjects[0].CaseCommissionFeeTypeId"] = $("#CaseFee_CaseFeeTypeId").val();
                                data["ContractObjects[0].CaseCommissionFeeAmount"] = $("#CaseFee_Amount").val();
                            }

                            data["ContractObjects[0].Remark"] = $("#CaseFee_Remark").val();
                            data["ContractObjects[0].IsChanged"] = true;

                            if (dataIsNOk) return false;

                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractDraft/ContractObjectsCreate", data, function (response) {
                                if (response.IsSuccess) {
                                    $.showModalMessageBox("保存成功.");
                                    c.Cases.Case.CaseFees.CaseFee.Close();
                                    c.Cases.Case.CaseFees.List();
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });

                        } catch (e) {
                            alert(e);
                        }
                    },
                    ObjectItem: {
                        BindEvent: function () {

                            $(".btn_ar_add").unbind("click");
                            $(".btn_ar_add").click(function () {
                                caseInfo.ARCaseFee.Objects.ObjectItem.Add(this);
                            });

                            $(".btn_ar_remove").unbind("click");
                            $(".btn_ar_remove").click(function () {
                                caseInfo.ARCaseFee.Objects.ObjectItem.Remove(this);
                            });

                            $(".btn_ar_edit").unbind("click");
                            $(".btn_ar_edit").click(function () {
                                caseInfo.ARCaseFee.Objects.ObjectItem.Edit(this);
                            });
                        },
                        Add: function (e) {
                            var tr = $(e).parents("tr").clone().show();

                            //$(tr).find(":input[type='text']").val('');
                            $(tr).find(":input[type='hidden']").val('');
                            $(tr).find(":input[type='checkbox']").attr("checked", false);

                            $(tr).find("#item_CaseOfficeFeeAmount").val('0');
                            $(tr).find("#item_CaseOfficeFeeTypeId").removeAttr("caseofficefeetypeid");
                            $(tr).find("#item_CaseOfficeFeeTypeId").removeAttr("caseofficefeeid");
                            $(tr).find("#item_CaseNonOfficeFeeTypeId").removeAttr("casenonofficefeetypeid");
                            $(tr).find("#item_CaseNonOfficeFeeTypeId").removeAttr("casenonofficetypeid");
                            $(tr).find("#item_CaseNonOfficeFeeAmount").val('0');
                            $(tr).find("#item_CaseCommissionFeeAmount").val('0');

                            $("#tblContractObjectList").append(tr);

                            caseInfo.ARCaseFee.Objects.ObjectItem.BindEvent();

                            return tr;
                        },
                        Clear: function (e) {
                            $(e).parents("tr").find(":input[type='text']").val('');
                            $(e).parents("tr").find(":input[type='hidden']").val('');
                            $(e).parents("tr").find(":input[type='checkbox']").attr("checked", false);
                        },
                        Remove: function (e) {
                            $(e).parents("tr").remove();
                        },

                        InitCaseOfficeFeeAnnualYear: function (e) {

                            if (($(e).val() == "11020" || $(e).val() == "21020" || $(e).val() == "31020") && $(e).parents("tr").find("#item_CaseRequestDate").val() == '') {
                                return false;
                            }

                            var selected = $(e).parents("tr").find("#item_CaseFeeAnnualYear");
                            var caseRequestDateStr = $(e).parents("tr").find("#item_CaseRequestDate").val();

                            $(selected).empty();
                            $(selected).removeAttr("disabled");
                            $($(e).parents("tr").find("#item_IsFirstYear")).removeAttr("disabled");


                            if ($(e).val() == "11020" || $(e).val() == "21020" || $(e).val() == "31020") {
                                if (caseRequestDateStr != '') {
                                    $(selected).removeAttr("disabled");
                                    var caseRequestDate = new Date(caseRequestDateStr);
                                    if ($(e).val() == "11020") {
                                        for (var i = 1; i <= 20; i++) {
                                            $(selected).append('<option value=' + i + ' annualfrom=' + caseRequestDate.addYears(i - 1).Format("yyyy-MM-dd") + ' annualend=' + caseRequestDate.addYears(i).addDays(-1).Format("yyyy-MM-dd") + '>第' + i + '年度 ' + caseRequestDate.addYears(i - 1).Format("yyyy-MM-dd") + '~' + caseRequestDate.addYears(i).addDays(-1).Format("yyyy-MM-dd") + '</option>');
                                        }
                                    }
                                    else {
                                        for (var i = 1; i <= 10; i++) {
                                            $(selected).append('<option value=' + i + ' annualfrom=' + caseRequestDate.addYears(i - 1).Format("yyyy-MM-dd") + ' annualend=' + caseRequestDate.addYears(i).addDays(-1).Format("yyyy-MM-dd") + '>第' + i + '年度 ' + caseRequestDate.addYears(i - 1).Format("yyyy-MM-dd") + '~' + caseRequestDate.addYears(i).addDays(-1).Format("yyyy-MM-dd") + '</option>');
                                        }
                                    }

                                }
                            } else {
                                $($(e).parents("tr").find("#item_IsFirstYear")).attr("disabled", "disabled");
                                $(selected).attr("disabled", "disabled");
                                $(selected).append('<option value=-1>无</option>');
                            }
                        },
                    },

                    MultiCreate: function (caseNos, feeTypeId) {
                        if (caseNos == null || caseNos.length == 0) {
                            $.showModalMessageBox("请选择案件.");
                            return false;
                        }

                        var data =
                        {
                            feeTypeId:feeTypeId,
                            caseNos: caseNos.join(',')
                        };

                        //var url = AP_ROOT + AP_PAGE_ID + "/FAM/AP/MultiCreate";
                        var url = AP_ROOT + AP_PAGE_ID + "/Legal/CaseFee/MultiCreate";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(".slide-panel-container").empty();
                            $(".slide-panel-container").append(result);
                            $(".slide-panel-container").addClass("show-panel");
                            c.Cases.Case.CaseFees.CaseFee.Objects.List(caseNos, feeTypeId);
                        });
                    },
                    MultiCreateUpdate: function (callback_func) {
                        try {
                            var data = {};
                            var dataIsNOk = false;
                            var i = 0;
                            $("#tblCaseFeeObjects>tbody>tr").each(function (j, e) {

                                if ($(e).css("display") != 'none') {

                                    if ($(e).find("#item_CaseFeeTypeId").val() == '-100') {
                                        dataIsNOk = true;
                                        $.showModalMessageBox("第" + (j) + "行,请选择费用类型.");
                                        return false;
                                    }

                                    if ($(e).find("#item_CaseFeeAmount").val() == '0') {
                                        dataIsNOk = true;
                                        $.showModalMessageBox("第" + (j) + "行,请输入费用金额.");
                                        return false;
                                    }

                                    if (!$(e).find("#item_CaseFeeAmount").isMoney()) {
                                        dataIsNOk = true;
                                        $.showModalMessageBox("第" + (j) + "行,金额格式不正确，请重新输入.");
                                        return false;
                                    }

                                    data["ContractObjects[" + i + "].CaseId"] = $(e).find("#item_CaseFeeTypeId").attr("caseid");
                                    data["ContractObjects[" + i + "].CaseNo"] = $(e).find("#item_CaseFeeTypeId").attr("caseno");

                                    data["ContractObjects[" + i + "].CustomerNo"] = $(e).find("#item_CaseFeeTypeId").attr("customerno");
                                    data["ContractObjects[" + i + "].ContractNo"] = $(e).find("#item_CaseFeeTypeId").attr("contractNo");

                                    //if ($("#CaseFee_CaseFeeTypeId").attr("typeid") == $.lsCaseFeeType.TypeId.OfficeFee) {
                                    //    data["ContractObjects[" + i + "].CaseOfficeFeeTypeId"] = $("#CaseFee_CaseFeeTypeId").val();
                                    //    data["ContractObjects[" + i + "].CaseOfficeFeeAmount"] = $("#CaseFee_Amount").val();
                                    //}
                                    //else if ($("#CaseFee_CaseFeeTypeId").attr("typeid") == $.lsCaseFeeType.TypeId.NonOfficeFee) {
                                    //    data["ContractObjects[" + i + "].CaseNonOfficeFeeTypeId"] = $("#CaseFee_CaseFeeTypeId").val();
                                    //    data["ContractObjects[" + i + "].CaseNonOfficeFeeAmount"] = $("#CaseFee_Amount").val();
                                    //}
                                    //else{
                                    //    data["ContractObjects[" + i + "].CaseCommissionFeeTypeId"] = $("#CaseFee_CaseFeeTypeId").val();
                                    //    data["ContractObjects[" + i + "].CaseCommissionFeeAmount"] = $("#CaseFee_Amount").val();
                                    //}

                                    data["ContractObjects[" + i + "].CaseOfficeFeeTypeId"] = $(e).find("#item_CaseFeeTypeId").val();
                                    data["ContractObjects[" + i + "].CaseOfficeFeeAmount"] = $(e).find("#item_CaseFeeAmount").val();

                                    data["ContractObjects[" + i + "].Remark"] = $(e).find("#item_Remark").val();

                                    i++;
                                }
                            });
                            
                            if (dataIsNOk) return false;
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FCM/ContractDraft/ContractObjectsCreate", data, function (response) {
                                if (response.IsSuccess) {
                                    c.Cases.Case.CaseFees.CaseFee.Close();
                                 
                                    if (callback_func) {
                                        callback_func(response.Data.CaseFeeIds);
                                    }
                                    else {
                                        $.showModalMessageBox("保存成功.");
                                    }

                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });

                        } catch (e) {
                            alert(e);
                        }
                    },

                    Objects: {
                        List: function (caseNos, feeTypeId) {
                            var data = {
                                caseNos: caseNos
                            };
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseList/GetCaseListByCaseNos", data, function (response) {
                                $("tbody", "#tblCaseFeeObjects").clearRow();
                                if (response.IsSuccess) {
                                    var tr = '';
                                    $.each(response.Data.CaseList, function (i, c) {
                                        tr += "<tr>"
                                              + "<td  style='text-align: center; padding:0px'> " + c.Basic.CaseNo + "</td>"
                                              + "<td  style='text-align: center; padding:0px'> "
                                              + "<select class='caseFeeType form-control' style='background-color:;border:0px' id='item_CaseFeeTypeId' caseFeeTypeId='-100' "
                                              + " caseid=" + c.Basic.CaseId + " caseno=" + c.Basic.CaseNo + " officialNo='" + c.Basic.OfficialNo + "' customerno=" + c.Basic.CustomerNo + " contractno=" + c.Basic.ContractNo
                                              + " caselawyer='" + c.Basic.CaseLawyer + "'  caseassistant='" + c.Basic.CaseAssistant + "'     caseinvestigator='" + c.Basic.Investigator + "' casebusinessowner='" + c.Basic.BusinessOwner + "' notarialnos='" + c.Basic.NotarialNos
                                              + "' caselawyername='" + c.Basic.CaseLawyerName + "' caseassistantname='" + c.Basic.CaseAssistantName + "' caseinvestigatorname='" + c.Basic.InvestigatorName + "' casebusinessownername='" + c.Basic.BusinessOwnerName + "'>"
                                              + "<option value='-100' >请选择</option></select></td>"
                                              + "<td  style='text-align: center; padding:0px'><input class='item_CaseFeeAmount form-control' autocomplete = off' style='background-color:yellow;border:0px'  id='item_CaseFeeAmount' name='item_CaseFeeAmount'  type='text' value='0'></td>"
                                              + "<td  style='text-align: center; padding:0px'><input class='item_Remark form-control' style='background-color:;border:0px' id='item_Remark'  type='text' value=''></td>"
                                              + "<td ><a style='color:green;' href='javascript:void(0);'><span class='btn_ar_add glyphicon glyphicon-plus'></span></a>&nbsp;&nbsp;&nbsp;<a  style='color:red;' href='javascript:void(0);'><span class='btn_ar_remove glyphicon glyphicon-remove'></span></a></td>"
                                              + "</tr>";
                                    });

                                    $('#tblCaseFeeObjects>tbody').html(tr);
                                    $("#tblCaseFeeObjects tbody tr").each(function (i, e) {
                                        if ($(e).find("#item_CaseFeeTypeId option").length == 1) {
                                            $.each(GV_LS.CaseFeeTypes, function (j, f) {
                                                if (f.TypeId == feeTypeId && f.FeeTypeId != -100) {
                                                    $(e).find("#item_CaseFeeTypeId").append('<option value=' + f.FeeTypeId + '>' + f.FeeTypeName + '</option>');
                                                }
                                            });

                                            $(e).find("#item_CaseFeeTypeId").val($(e).find("#item_CaseFeeTypeId").attr("caseFeeTypeId"));
                                        }

                                    });

                                    c.Cases.Case.CaseFees.CaseFee.Objects.ObjectItem.BindEvent();
                                }
                            });

                        },
                        ObjectItem: {
                            BindEvent: function () {

                                $(".btn_ar_add").unbind("click");
                                $(".btn_ar_add").click(function () {
                                    c.Cases.Case.CaseFees.CaseFee.Objects.ObjectItem.Add(this);
                                });

                                $(".btn_ar_remove").unbind("click");
                                $(".btn_ar_remove").click(function () {
                                    c.Cases.Case.CaseFees.CaseFee.Objects.ObjectItem.Remove(this);
                                });

                                $(".btn_ar_edit").unbind("click");
                                $(".btn_ar_edit").click(function () {
                                    c.Cases.Case.CaseFees.CaseFee.Objects.ObjectItem.Edit(this);
                                });


                            },
                            Add: function (e) {

                                //var tr = "<tr>"
                                //         + "<td  style='text-align: center; padding:0px'><select class='caseFeeType form-control' style='background-color:;border:0px' id='item_CaseFeeTypeId' caseFeeTypeId='-100'><option value='-100'   selected='selected' >请选择</option></select></td>"
                                //         + "<td  style='text-align: center; padding:0px'>"
                                //         + "<div class='bootstrap-tagsinput'>"
                                //         + "    <input type='text' placeholder='收款人' class='form-control inline-block' style='height:22px;width: 100px;margin-left: 6px;' id='item_PaymentObjectName_Input' autocomplete='off' size='1'>"
                                //         + "</div>"
                                //         + "</td>"
                                //         + "<td  style='text-align: center; padding:0px'><input class='item_CaseFeeAmount form-control' autocomplete = off' style='background-color:yellow;border:0px'  id='item_CaseFeeAmount' name='item_CaseFeeAmount' onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\" onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" type='text' value='0'></td>"
                                //         + "<td  style='text-align: center; padding:0px'><input class='item_Remark form-control' style='background-color:;border:0px' id='item_Remark'  type='text' value=''></td>"
                                //         + "<td ><a style='color:green;' href='javascript:void(0);'><span class='btn_ar_add glyphicon glyphicon-plus'></span></a>&nbsp;&nbsp;&nbsp;<a  style='color:red;' href='javascript:void(0);'><span class='btn_ar_remove glyphicon glyphicon-remove'></span></a></td>"
                                //   + "</tr>";

                                var tr = $(e).parents("tr").clone().show();

                                $(tr).find(":input[type='text']").val('');
                                $(tr).find(":input[type='hidden']").val('');
                                $(tr).find(":input[type='checkbox']").attr("checked", false);
                                $(tr).find("#item_PaymentObjectName_Input").prev().remove();
                                $(tr).find("#item_PaymentObjectName_Input").removeAttr("disabled");
                                $(tr).find("#item_CaseFeeAmount").val('0');

                                $(e).parents("tr").after(tr);

                                c.Cases.Case.CaseFees.CaseFee.Objects.ObjectItem.BindEvent();

                                var businessOwner = new AssociateAvailableUser_PaymentObject(
                                   $("#divAssociateUserList_CaseFee"),
                                   $(tr).find("#item_PaymentObjectName_Input"),
                                   $(tr).find("#item_PaymentObjectName_Input"),
                                   c.Cases.Case.CaseFees.CaseFee.Objects.PaymentObject.AddIn
                               );

                                return tr;
                            },
                            Clear: function (e) {
                                $(e).parents("tr").find(":input[type='text']").val('');
                                $(e).parents("tr").find(":input[type='hidden']").val('');
                                $(e).parents("tr").find(":input[type='checkbox']").attr("checked", false);
                            },
                            Remove: function (e) {
                                $(e).parents("tr").remove();
                            },
                            SyncPaymentType: function () {
                                var caseFeeTypeId = $($("#tblCaseFeeObjects tbody tr")[0]).find("#item_CaseFeeTypeId").val();
                                $("#tblCaseFeeObjects tbody tr").each(function (i, e) {
                                    $(e).find("#item_CaseFeeTypeId").val(caseFeeTypeId);
                                    $(e).find("#item_CaseFeeTypeId").change();
                                })
                            },
                            SyncPaymentObject: function () {
                                //var item_CaseFeeTypeId = $($("#tblCaseFeeObjects tbody tr")[1]).find("#item_CaseFeeAmount");
                                var item_CaseFeeTypeId = $("#tblCaseFeeObjects>tbody>tr:first").find("#item_CaseFeeAmount");
                                $("#tblCaseFeeObjects tbody tr").each(function (i, e) {
                                    $(e).find("#item_CaseFeeTypeId").val($(item_CaseFeeAmount).val());
                                })
                            },
                            SyncPaymentAmount: function () {
                                var amount = $($("#tblCaseFeeObjects tbody tr")[0]).find("#item_CaseFeeAmount").val();
                                $("#tblCaseFeeObjects tbody tr").each(function (i, e) {
                                    $(e).find("#item_CaseFeeAmount").val(amount);
                                })
                            },
                            SyncPaymentRemark: function () {
                                var item_Remark = $($("#tblCaseFeeObjects tbody tr")[0]).find("#item_Remark");
                                $("#tblCaseFeeObjects tbody tr").each(function (i, e) {
                                    $(e).find("#item_Remark").val($(item_Remark).val());
                                })
                            },
                        },
                        PaymentObject: {
                            AddIn: function (target, username, userchname, permitinput) {
                                var existsUser = false;

                                $("a[name='paymentobjectname']", target).each(function () {
                                    if ($(this).attr("username") == username) {
                                        existsUser = true;
                                        return true;
                                    }
                                });

                                //重复
                                if (existsUser) return true;

                                var $tag = $("<span class='tag label label-info'>"
                                             + "<a name='paymentobjectname' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                             + " username='" + username + "'"
                                             + " userchname='" + userchname + "'"
                                             + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);'   data-original-title=" + userchname + " '>" + userchname + "</a>"
                                             + "<span class='paymentobjectremove' data-role='remove'></span>"
                                           + "</span>");

                                if (!permitinput) {
                                    $(target).find("#item_PaymentObjectName_Input").attr("disabled", "disabled");
                                }
                                $(target).find("#item_PaymentObjectName_Input").before($tag);
                                $tag.after(' ');

                            },
                            Remove: function (e) {
                                
                                $(e).parent().remove();
                            },
                        },
                    },
                },
                Payment: {
                    View: function (paymentId) {
                        var url = AP_ROOT + "5001003001/FAM/AP/PaymentView?paymentId=" + paymentId;
                        window.open(url);
                    },
                    Open: function (caseFeeIds) {
                       var data =
                       {
                           caseFeeIds: caseFeeIds.join(',')
                       };
                        var url = AP_ROOT + AP_PAGE_ID + "/FAM/AP/MultiCreate";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(".slide-panel-container").empty();
                            $(".slide-panel-container").append(result);
                            $(".slide-panel-container").addClass("show-panel");
                            c.Cases.Case.CaseFees.Payment.Objects.List(caseFeeIds);
                        });
                    },
                    Objects: {
                        List: function (caseFeeIds) {
                            var data = {
                                caseFeeIds: caseFeeIds
                            };
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFee/GetCaseFeeListByCaseFeeIds", data, function (response) {
                                $("tbody", "#tblCaseFeeObjects").clearRow();
                                if (response.IsSuccess) {
                                    var tr = '';
                                    $.each(response.Data.CaseFeeList, function (i, f) {
                                        tr += "<tr>"
                                             + "<td  style='text-align: center; padding:0px'> " + f.ContractNo + "</td>"
                                             + "<td  style='text-align: center; padding:0px'> " + f.CaseNo + "</td>"
                                             + "<td  style='text-align: center; padding:0px'> " + f.CaseFeeTypeName + "</td>"
                                             + "<td  style='text-align: center; padding:0px'><input class='item_CaseFeePayAmount form-control' readonly=true autocomplete = off' style='background-color:;border:0px'  id='item_CaseFeePayAmount' name='item_CaseFeePayAmount'  type='text'"
                                             + " caseid=" + f.CaseId + " caseno=" + f.CaseNo + " customerno=" + f.CustomerNo + " contractno=" + f.ContractNo + " casefeeid=" + f.CaseFeeId
                                             + " value='" + f.Amount + "'>"
                                             + "</td>"
                                             + "<td  style='text-align: center; padding:0px'>"
                                             + "<div class='bootstrap-tagsinput'  style='text-align: center;border:0px; padding:0px'>"
                                             + "    <input type='text' placeholder='收款单位' class='item_PaymentObjectName_Input form-control inline-block' style='background-color:; height:22px;border:0px;padding:0px;width: 100%;margin-left: 4px;' id='item_PaymentObjectName_Input_" + i + "' autocomplete='off' size='1'>"
                                             + "</div>"
                                             + "</td>"
                                             + "<td ><a  style='color:red;' href='javascript:void(0);'><span class='btn_ar_remove glyphicon glyphicon-remove'></span></a></td>"
                                             + "</tr>";
                                    });

                                    $('#tblCaseFeeObjects>tbody').html(tr);

                                    $("#tblCaseFeeObjects tbody tr").each(function (i, e) {
                                        var paymentType = new AssociatePaymentType(
                                                $("#divAssociatePaymentTypeList_CaseFee"),
                                                $(e).find("#item_PaymentObjectName_Input_" + i),
                                                $(e).find("#item_PaymentObjectName_Input_" + i),
                                                c.Cases.Case.CaseFees.Payment.Objects.PaymentObject.AddIn,
                                                'c.Cases.Case.CaseFees.Payment.Objects.PaymentObject.AddIn'
                                            );
                                    });

                                    c.Cases.Case.CaseFees.Payment.Objects.ObjectItem.BindEvent();
                                }
                            });
                        },
                        ObjectItem: {
                            BindEvent: function () {

                                $(".btn_ar_add").unbind("click");
                                $(".btn_ar_add").click(function () {
                                    c.Cases.Case.CaseFees.CaseFee.Objects.ObjectItem.Add(this);
                                });

                                $(".btn_ar_remove").unbind("click");
                                $(".btn_ar_remove").click(function () {
                                    c.Cases.Case.CaseFees.CaseFee.Objects.ObjectItem.Remove(this);
                                });

                                $(".btn_ar_edit").unbind("click");
                                $(".btn_ar_edit").click(function () {
                                    c.Cases.Case.CaseFees.CaseFee.Objects.ObjectItem.Edit(this);
                                });

                                //var payment = new AssociatePaymentType(
                                //    $("#divAssociatePaymentTypeList_CaseFee"),
                                //    $("#item_PaymentObjectName_Input"),
                                //    $("#item_PaymentObjectName_Input"),
                                //    c.Cases.Case.CaseFees.Payment.Objects.PaymentObject.AddIn
                                //);

                            },
                            Add: function (e) {

                                //var tr = "<tr>"
                                //         + "<td  style='text-align: center; padding:0px'><select class='caseFeeType form-control' style='background-color:;border:0px' id='item_CaseFeeTypeId' caseFeeTypeId='-100'><option value='-100'   selected='selected' >请选择</option></select></td>"
                                //         + "<td  style='text-align: center; padding:0px'>"
                                //         + "<div class='bootstrap-tagsinput'>"
                                //         + "    <input type='text' placeholder='收款人' class='form-control inline-block' style='height:22px;width: 100px;margin-left: 6px;' id='item_PaymentObjectName_Input' autocomplete='off' size='1'>"
                                //         + "</div>"
                                //         + "</td>"
                                //         + "<td  style='text-align: center; padding:0px'><input class='item_CaseFeeAmount form-control' autocomplete = off' style='background-color:yellow;border:0px'  id='item_CaseFeeAmount' name='item_CaseFeeAmount' onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\" onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" type='text' value='0'></td>"
                                //         + "<td  style='text-align: center; padding:0px'><input class='item_Remark form-control' style='background-color:;border:0px' id='item_Remark'  type='text' value=''></td>"
                                //         + "<td ><a style='color:green;' href='javascript:void(0);'><span class='btn_ar_add glyphicon glyphicon-plus'></span></a>&nbsp;&nbsp;&nbsp;<a  style='color:red;' href='javascript:void(0);'><span class='btn_ar_remove glyphicon glyphicon-remove'></span></a></td>"
                                //   + "</tr>";

                                var item_PaymentObjectName_Input_Id = "item_PaymentObjectName_Input_" + $("#tblCaseFeeObjects>tbody>tr").length;

                                var tr = $(e).parents("tr").clone().show();

                                $(tr).find(":input[type='text']").val('');
                                $(tr).find(":input[type='hidden']").val('');
                                $(tr).find(":input[type='checkbox']").attr("checked", false);
                                $(tr).find(".item_PaymentObjectName_Input").attr("id", item_PaymentObjectName_Input_Id)
                                $(tr).find(".item_PaymentObjectName_Input").prev().remove();
                                $(tr).find(".item_PaymentObjectName_Input").removeAttr("disabled");
                                $(tr).find(".item_PaymentObjectName_Input").css("width", "100%");

                                $(tr).find("#item_CaseFeeAmount").val('0');

                                $(e).parents("tr").after(tr);

                                c.Cases.Case.CaseFees.CaseFee.Objects.ObjectItem.BindEvent();

                                var businessOwner = new AssociateAvailableUser_PaymentObject(
                                   $("#divAssociateUserList_CaseFee"),
                                   $(tr).find("#" + item_PaymentObjectName_Input_Id),
                                   $(tr).find("#" + item_PaymentObjectName_Input_Id),
                                   c.Cases.Case.CaseFees.CaseFee.Objects.PaymentObject.AddIn
                               );

                                return tr;
                            },
                            Clear: function (e) {
                                $(e).parents("tr").find(":input[type='text']").val('');
                                $(e).parents("tr").find(":input[type='hidden']").val('');
                                $(e).parents("tr").find(":input[type='checkbox']").attr("checked", false);
                            },
                            Remove: function (e) {
                                $(e).parents("tr").remove();
                            },

                            SyncPaymentObject: function () {
                                 
                                var paymentObject = $("#tblCaseFeeObjects>tbody>tr:first").find(".bootstrap-tagsinput").html();
                                $("#tblCaseFeeObjects tbody tr").each(function (i, e) {
                                    $(e).find(".bootstrap-tagsinput").html(paymentObject);
                                })
                            },

                        },
                        PaymentObject: {
                            AddIn: function (target, paymentType, permitinput) {

                                var exists = false;

                                $("a[name='paymentobjectname']", target).each(function () {
                                    if ($(this).attr("paymentTypeId") == paymentType.PaymentTypeId) {
                                        exists = true;
                                        return true;
                                    }
                                });

                                //重复
                                if (exists) return true;

                                var $tag = $("<span class='tag label label-info'>"
                                             + "<a name='paymentobjectname' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                             + " paymentTypeId='" + paymentType.PaymentTypeId + "'"
                                             + " organizationName='" + paymentType.OrganizationName + "'"
                                             + " account='" + paymentType.Account + "'"
                                             + " accountBank='" + paymentType.AccountBank + "'"
                                             + " remark='" + paymentType.Remark + "'"
                                             + " title='' data-toggle='popover_paymentobject' data-container='body' href='javascript:void(0);'   data-original-title=" + paymentType.OrganizationName + " '>" + paymentType.OrganizationName + "</a>"
                                             + "<span class='casefeepaymentobjectremove' data-role='remove'></span>"
                                           + "</span>");

                                if (!permitinput) {
                                    $(target).find(".item_PaymentObjectName_Input").css("width", "0px");
                                }
                                $(target).find(".item_PaymentObjectName_Input").before($tag);
                                $tag.after(' ');

                                $(function () {
                                    $('[data-toggle="popover_paymentobject"]').each(function () {
                                        
                                        var element = $(this);
                                        var id = element.attr('id');
                                        var txt = element.html();
                                        element.popover({
                                            trigger: 'manual',
                                            placement: 'bottom', //top, bottom, left or right
                                            title: txt,
                                            html: 'true',
                                            content: $.paymentType.View(element),

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

                            },
                            Remove: function (e) {
                                $(e).parents("tr").find(".item_PaymentObjectName_Input").css("width", "100%");

                                var paymentType = new AssociatePaymentType(
                                    $("#divAssociatePaymentTypeList_CaseFee"),
                                    $(e).parents("tr").find(".item_PaymentObjectName_Input"),
                                    $(e).parents("tr").find(".item_PaymentObjectName_Input"),
                                    c.Cases.Case.CaseFees.Payment.Objects.PaymentObject.AddIn,
                                    'c.Cases.Case.CaseFees.Payment.Objects.PaymentObject.AddIn'
                                    );

                                $(e).parent().remove();
                            },
                        },
                    },

                    Application: {
                        CreateUpdate: function (callback_func) {
                            try {

                                var data = {};
                                var dataIsNOk = false;
                                var i = 0;
                                $("#tblCaseFeeObjects>tbody>tr").each(function (j, e) {
                                    if ($(e).css("display") != 'none') {

                                        var paymentobjects = new Array();
                                        var paymentobjectnames = new Array();

                                        $("a[name='paymentobjectname']", $(e)).each(function () {
                                            paymentobjects.push($(this).attr("paymenttypeid"));
                                            paymentobjectnames.push($(this).attr("paymenttypename"));
                                        });

                                        if (paymentobjects.length == 0) {
                                            dataIsNOk = true;
                                            $.showModalMessageBox("第" + (j) + "行,请输入收款单位.");
                                            return false;
                                        }

                                        if (paymentobjects.length > 1) {
                                            dataIsNOk = true;
                                            $.showModalMessageBox("第" + (j) + "行,只能选择一个收款单位.");
                                            return false;
                                        }

                                        if ($(e).find("#item_CaseFeePayAmount").val() == '') {
                                            $.showModalMessageBox("请选择付款单位.");
                                            return false;
                                        }

                                        if ($(e).find("#item_CaseFeePayAmount").val() == '0') {
                                            dataIsNOk = true;
                                            $.showModalMessageBox("第" + (j) + "行,请输入付款金额.");
                                            return false;
                                        }

                                        if (!$(e).find("#item_CaseFeePayAmount").isMoney()) {
                                            dataIsNOk = true;
                                            $.showModalMessageBox("第" + (j) + "行,金额格式不正确，请重新输入.");
                                            return false;
                                        }

                                        data["PaymentObjects[" + i + "].PaymentTypeId"] = paymentobjects[0];
                                        data["PaymentObjects[" + i + "].CaseFeeId"] = $(e).find("#item_CaseFeePayAmount").attr("CaseFeeId");
                                        data["PaymentObjects[" + i + "].CaseId"] = $(e).find("#item_CaseFeePayAmount").attr("CaseId");
                                        data["PaymentObjects[" + i + "].CaseNo"] = $(e).find("#item_CaseFeePayAmount").attr("CaseNo");
                                        data["PaymentObjects[" + i + "].ContractNo"] = $(e).find("#item_CaseFeePayAmount").attr("ContractNo");
                                        data["PaymentObjects[" + i + "].CaseFeePaidAmount"] = $(e).find("#item_CaseFeePayAmount").val();
                                        data["PaymentObjects[" + i + "].CaseFeePrePaidAmount"] = $(e).find("#item_CaseFeePayAmount").val();
                                        data["PaymentObjects[" + i + "].IsChanged"] = false;

                                        i++;
                                    }
                                });

                                if (i == 0) {
                                    $.showModalMessageBox("无费用,不能申请付款.");
                                    return false;
                                }

                                if (dataIsNOk) return false;

                                $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/Payment/PaymentObjectsCreateUpdate", data, function (response) {
                                    if (response.IsSuccess) {
                                        if (callback_func != null)
                                        {
                                            callback_func(response.Data.PaymentList);
                                        }
                                    } else {
                                        $.showModalMessageBox(response.Message);
                                    }
                                });

                            } catch (e) {

                            }
                        },
                        CreateUpdateCallBack: function (paymentList) {

                            var data = {};
                            var url = AP_ROOT + AP_PAGE_ID + "/FAM/AP/MultiCreatePaymentList";
                            $.openLoading();

                            $("<div></div>").load(url, data, function (result) {
                                $.closeLoading();
                                $(".slide-panel-container").empty();
                                $(".slide-panel-container").append(result);
                                $(".slide-panel-container").addClass("show-panel");

                                $("tbody", "#tblPaymentObjects").clearRow();

                                var tr = '';
                                $.each(paymentList, function (i, p) {
                                    tr += "<tr>"
                                   
                                            + "<td  style='text-align: center; padding:0px'> <a href='javascript:void(0)' onclick='javascript:c.Cases.Case.CaseFees.Payment.View(\"" + p.PaymentBasic.PaymentId + "\")'>" + p.PaymentBasic.ApplicationNo + "</a></td>"
                                            + "<td  style='text-align: center; padding:0px'> " + p.PaymentBasic.PaidAmount + "</td>"
                                            + "<td  style='text-align: center; padding:0px'> " + p.PaymentBasic.PayerName + "</td>"
                                            + "<td  style='text-align: center; padding:0px'> " + p.PaymentType.OrganizationName + "</td>"
                                            + "<td  style='text-align: center; padding:0px'> " + p.PaymentType.Account + "</td>"
                                            + "<td  style='text-align: center; padding:0px'> " + p.PaymentType.AccountBank + "</td>"
                                         + "</tr>"
                                });

                                $('#tblPaymentObjects>tbody').html(tr);
                            });
                        },
                    },

                    ViewReceviedPayment: function (caseFeeId) {

                        var data = {
                            caseFeeId: caseFeeId
                        };

                        var url = AP_ROOT + AP_PAGE_ID + "/FAM/AR/PaymentList";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);

                            $('#paymentListModal').modal({ backdrop: 'static', keyboard: false });
                            $('#paymentListModal').on('hidden.bs.modal', function () {
                                $("#paymentListModal").remove();
                            });

                        });
                    },
                },
                PaymentApply: {
                    /*垫付款申请*/
                    Open: function () {
                        if (parseInt($("#Case_Basic_CaseId").val()) == 0) {
                            $.showModalMessageBox("请先保存案件基本资料.");
                            return false;
                        }
                        var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
                        if (caseFeeIds.length == 0) {
                            $.showModalMessageBox("请选择费用进行付款申请.");
                            return false;
                        }
                        var contractIds = new Array();
                        var batchNos = new Array();
                        var exitsNonOfficeType = false;

                        $("input[name='chkCaseFeeId']:checked").each(
                            function () {

                                if ($(this).attr("feetypeid") == payment.PaymentTypeId.NonOfficeFee) {
                                    exitsNonOfficeType = true;
                                }

                                if ($.inArray($(this).attr("contractid"), contractIds) > -1) {
                                } else {
                                    contractIds.push($(this).attr("contractid"));
                                }
                                batchNos.push($(this).attr("batchNo"));
                            }
                        );

                        if (exitsNonOfficeType) {
                            $.showModalMessageBox("不允许选择代理费进行付款.");
                            return false;
                        }

                        if (contractIds.length > 1) {
                            $.showModalMessageBox("请选择同一合同下的费用进行付款申请.");
                            return false;
                        }
                        var url = AP_ROOT + AP_PAGE_ID + '/FAM/AP/PaymentCreate?contractId=' + contractIds[0] + '&batchNos=' + batchNos.join(",");

                        addtabs(url, "申请付款");

                        //window.open(url);
                    },

                },
                Invoice: {

                    /*垫付款申请*/
                    Apply: function () {
                        if (parseInt($("#Case_Basic_CaseId").val()) == 0) {
                            $.showModalMessageBox("请先保存案件基本资料.");
                            return false;
                        }
                        var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
                        if (caseFeeIds.length == 0) {
                            $.showModalMessageBox("请选择费用进行付款申请.");
                            return false;
                        }
                        debugger
                        var url = AP_ROOT + AP_PAGE_ID + '/FAM/Invoice/InvoiceDetailCreate?customerNo=' + $("#Case_Basic_CustomerNo").val() + '&caseFeeIds=' + caseFeeIds.join(",");
                        addtabs(url, "申请开票");
                    },


                    /*案件票据确认*/
                    Open: function () {

                        if (parseInt($("#Case_Basic_CaseId").val()) == 0) {
                            $.showModalMessageBox("请先保存案件基本资料.");
                            return false;
                        }
                        var caseFeeIds = $.checkbox.vals("chkCaseFeeId");
                        if (caseFeeIds.length == 0) {
                            $.showModalMessageBox("请选择需要确认的应收款.");
                            return false;
                        }

                        var caseTypeIds = new Array('4', '5');

                        var caseClassType = '';

                        //商标以外的案件，除代理费发票允许上传外，其他类型发票不允许上传
                        if ($.inArray($("#Case_Basic_CaseTypeId").val(), caseTypeIds) <= -1) {
                            caseClassType = 'Patent';
                            var caseFeeTypeIds = new Array('0');
                            var caseTypeName = $("#Case_Basic_CaseTypeId").find("option:selected").text();

                            var result = true;
                            $("input[name='chkCaseFeeId']:checked").each(
                                function (i) {
                                    if ($.inArray($(this).attr("casefeetypeid"), caseFeeTypeIds) <= -1) {
                                        $.showModalMessageBox(caseTypeName + "案件不允上传" + $(this).attr("casefeetypename") + "的发票文件.");
                                        result = false;
                                        return false;
                                    }
                                }
                            );

                            if (!result) return false;
                        } else {
                            caseClassType = 'TradeCopyright';
                        }

                        var data =
                        {
                            caseFeeIds: caseFeeIds,
                            caseClassType: caseClassType,
                            invoiceType: 'Invoice'
                        };

                        var url = AP_ROOT + AP_PAGE_ID + "/IPR/CaseFeeInvoice/CaseFeeInvoiceConfirm";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#caseFeeInvoiceConfirmModal').modal({ backdrop: 'static', keyboard: false });
                            $('#caseFeeInvoiceConfirmModal').on('hidden.bs.modal', function () {
                                $("#caseFeeInvoiceConfirmModal").remove();
                            });
                        });

                    },

                    Download: function (caseFeeId) {
                        window.open(AP_ROOT + AP_PAGE_ID + "/IPR/CaseFileCenter/CaseFeeFileDownload?caseFeeId=" + caseFeeId);
                        return true;
                    },

                    Close: function () {
                        $('#caseFeeInvoiceConfirmModal').modal('hide');
                    },

                    Confirm: function () {

                        if ($("#Invoice_InvoiceNo").val() == '') {
                            $.showModalMessageBox("请输入票据编号.");
                            return false;
                        }

                        if ($("#Invoice_InvoiceDate").val() == '') {
                            $.showModalMessageBox("请输入票据日期.");
                            return false;
                        }

                        if ($("#flInvoiceFile").val() == '') {
                            $.showModalMessageBox("请选择上传文件.");
                            return false;
                        }

                        //专利发票不需要付款方式,付款人
                        if ($("#CaseClassType").val() == 'Patent' && $("#InvoiceType").val() == 'Invoice') {

                        } else {
                            if ($("#PaymentMode").val() == '') {
                                $.showModalMessageBox("付款方式.");
                                return false;
                            }

                            if ($("#PayerName").val() == '') {
                                $.showModalMessageBox("付款人.");
                                return false;
                            }
                        }

                        $.openLoading();
                        $('#caseFeeInvoiceConfirm').ajaxSubmit({
                            success: function (response) {
                                $.closeLoading();
                                if (response.IsSuccess) {
                                    $.showModalMessageBox("保存成功.");
                                    $('#caseFeeInvoiceConfirmModal').modal('hide');

                                    caseInfo.ARCaseFee.List();
                                    caseInfo.CaseEvent.List();

                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            }
                        });
                    },

                    /*票据文件*/
                    File: {
                        Open: function (caseFeeGuid) {
                            var data = {
                                caseFeeGuid: caseFeeGuid,
                            };

                            var url = AP_ROOT + AP_PAGE_ID + "/FAM/InvoiceFile/List";
                            $.openLoading();

                            $("<div></div>").load(url, data, function (result) {
                                $.closeLoading();
                                $(document.body).append(result);
                                $('#invoiceFileListModal').modal({ backdrop: 'static', keyboard: false });
                                $('#invoiceFileListModal').on('hidden.bs.modal', function () {
                                    $("#invoiceFileListModal").remove();
                                });
                            });
                        },


                    },
                },
                Refound: {
                    Open: function (caseFeeId) {
                        var data =
                        {
                            caseFeeId: caseFeeId
                        };

                        var url = AP_ROOT + AP_PAGE_ID + "/Legal/CaseFee/RefundAmount";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#caseRefundAmountModal').modal({ backdrop: 'static', keyboard: false });
                            $('#caseRefundAmountModal').on('hidden.bs.modal', function () {
                                $("#caseRefundAmountModal").remove();
                            });
                        });
                    },

                    CreateUpdate: function () {
                        try {

                            var chkCaseFeeIds = $.checkbox.vals("chkCaseFeeId");
                            if (chkCaseFeeIds.length == 0) {
                                $.showModalMessageBox("请选择费用.");
                                return false;
                            }

                            if (!$("#CaseFee_RefundAmount").isMoney()) {
                                $.showModalMessageBox("金额格式不正确，请重新输入.");
                                return false;
                            }

                            var data =
                            {
                                caseFeeId: chkCaseFeeIds[0],
                                refundAmount: $("#CaseFee_RefundAmount").val()
                            };

                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseFee/RefoundAmountCreateUpdate", data, function (response) {
                                if (response.IsSuccess) {
                                    $('#caseRefundAmountModal').modal('hide');
                                    c.Cases.Case.CaseFees.List();
                                }
                                else if (response.IsRedirect) {
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
            },
            /*案件内部费用*/
            InternalFees: {
                InternalFee: {
                    MultiOpen: function (caseNos) {
                        if (caseNos == null || caseNos.length == 0) {
                            $.showModalMessageBox("请选择案件.");
                            return false;
                        }

                        var data =
                        {
                            caseNos: caseNos.join(',')
                        };

                        var url = AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/MultiCreate";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(".slide-panel-container").empty();
                            $(".slide-panel-container").append(result);
                            $(".slide-panel-container").addClass("show-panel");
                            c.Cases.Case.InternalFees.InternalFee.Objects.List(caseNos);
                        });
                    },
                    Open: function () {
                        if (parseInt($("#Case_Basic_CaseId").val()) == 0) {
                            $.showModalMessageBox("请先保存案件基本资料.");
                            return false;
                        }

                        var data = {};

                        var url = AP_ROOT + AP_PAGE_ID + "/Legal/InternalFee/Create";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#internalFeeModal').modal({ backdrop: 'static', keyboard: false });
                            $('#internalFeeModal').on('hidden.bs.modal', function () {
                                $("#internalFeeModal").remove();
                            });

                            var businessOwner = new AssociateUser(
                            $("#divAssociateUserList_InternalFee"),
                                 $("#InternalFee_PaymentObject"),
                                 $("#InternalFee_PaymentObjectName"),
                                 null
                            );
                        });
                    },
                    Objects: {
                        List: function (caseNos) {
                            var data = {
                                caseNos: caseNos
                            };
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseList/GetCaseListByCaseNos", data, function (response) {
                                $("tbody", "#tblInternalFeeObjects").clearRow();
                                if (response.IsSuccess) {
                                    var tr = '';

                                    $.each(response.Data.CaseList, function (i, c) {
                                        tr += "<tr>"
                                              + "<td  style='text-align: center; padding:0px'> " + c.Basic.CaseNo + "</td>"
                                              + "<td  style='text-align: center; padding:0px'> "
                                                + "<select class='internalFeeType form-control' style='background-color:;border:0px' id='item_InternalFeeTypeId' internalFeeTypeId='-100' "
                                                + " caseid=" + c.Basic.CaseId + " caseno=" + c.Basic.CaseNo
                                                + " caselawyer='" + c.Basic.CaseLawyer
                                                + "' caseassistant='" + c.Basic.CaseAssistant
                                                + "' caseinvestigator='" + c.Basic.Investigator
                                                + "' casebusinessowner='" + c.Basic.BusinessOwner
                                                + "' caselawyername='" + c.Basic.CaseLawyerName
                                                + "' caseassistantname='" + c.Basic.CaseAssistantName
                                                + "' caseinvestigatorname='" + c.Basic.InvestigatorName
                                                + "' casebusinessownername='" + c.Basic.BusinessOwnerName + "'>"
                                                + "<option value='-100' >请选择</option></select></td>"
                                                + "<td  style='text-align: center; padding:0px'>"
                                              + "<div class='bootstrap-tagsinput' style='text-align: center; padding:0px;border:0px;'>"
                                              + "    <input type='text' placeholder='收款人' class='item_PaymentObjectName_Input form-control inline-block' style='background-color:;height:22px;border:0px;padding:0px;width:100%;margin-left: 4px;' id='item_PaymentObjectName_Input_" + i + "' autocomplete='off' size='1'>"
                                              + "</div>"
                                              + "</td>"
                                              + "<td  style='text-align: center; padding:0px'><input class='item_InternalFeeAmount form-control' autocomplete = off' style='background-color:yellow;border:0px'  id='item_InternalFeeAmount' name='item_InternalFeeAmount'  type='text' value='0'></td>"
                                              + "<td  style='text-align: center; padding:0px'><input class='item_Remark form-control' style='background-color:;border:0px' id='item_Remark'  type='text' value=''></td>"
                                              + "<td ><a style='color:green;' href='javascript:void(0);'><span class='btn_ar_add glyphicon glyphicon-plus'></span></a>&nbsp;&nbsp;&nbsp;<a  style='color:red;' href='javascript:void(0);'><span class='btn_ar_remove glyphicon glyphicon-remove'></span></a></td>"
                                               + "</tr>";
                                    });

                                    $('#tblInternalFeeObjects>tbody').html(tr);
                                    $("#tblInternalFeeObjects tbody tr").each(function (i, e) {

                                        if ($(e).find("#item_InternalFeeTypeId option").length == 1) {
                                            $.each(GV_LS.CaseFeeTypes, function (j, f) {
                                                if (f.TypeId == '4' && f.FeeTypeId != -100) {
                                                    $(e).find("#item_InternalFeeTypeId").append('<option value=' + f.FeeTypeId + '>' + f.FeeTypeName + '</option>');
                                                }
                                            });

                                            $(e).find("#item_InternalFeeTypeId").val($(e).find("#item_InternalFeeTypeId").attr("internalFeeTypeId"));
                                        }

                                        var paymentObject = new AssociateAvailableUser_PaymentObject(
                                             $("#divAssociateUserList_InternalFee"),
                                             $("#item_PaymentObjectName_Input_" + i),
                                             $("#item_PaymentObjectName_Input_" + i),
                                             c.Cases.Case.InternalFees.InternalFee.Objects.PaymentObject.AddIn
                                         );
                                    });

                                    c.Cases.Case.InternalFees.InternalFee.Objects.ObjectItem.BindEvent();
                                }
                            });

                        },
                        ObjectItem: {
                            BindEvent: function () {

                                $(".btn_ar_add").unbind("click");
                                $(".btn_ar_add").click(function () {
                                    c.Cases.Case.InternalFees.InternalFee.Objects.ObjectItem.Add(this);
                                });

                                $(".btn_ar_remove").unbind("click");
                                $(".btn_ar_remove").click(function () {
                                    c.Cases.Case.InternalFees.InternalFee.Objects.ObjectItem.Remove(this);
                                });

                                $(".btn_ar_edit").unbind("click");
                                $(".btn_ar_edit").click(function () {
                                    c.Cases.Case.InternalFees.InternalFee.Objects.ObjectItem.Edit(this);
                                });

                            },
                            Add: function (e) {

                                //var tr = "<tr>"
                                //         + "<td  style='text-align: center; padding:0px'><select class='internalFeeType form-control' style='background-color:;border:0px' id='item_InternalFeeTypeId' internalFeeTypeId='-100'><option value='-100'   selected='selected' >请选择</option></select></td>"
                                //         + "<td  style='text-align: center; padding:0px'>"
                                //         + "<div class='bootstrap-tagsinput'>"
                                //         + "    <input type='text' placeholder='收款人' class='form-control inline-block' style='height:22px;width: 100px;margin-left: 6px;' id='item_PaymentObjectName_Input' autocomplete='off' size='1'>"
                                //         + "</div>"
                                //         + "</td>"
                                //         + "<td  style='text-align: center; padding:0px'><input class='item_InternalFeeAmount form-control' autocomplete = off' style='background-color:yellow;border:0px'  id='item_InternalFeeAmount' name='item_InternalFeeAmount' onafterpaste=\"this.value=this.value.replace(/\\D/g,'')\" onkeyup=\"javascript:this.value=this.value.replace(/\\D/g,'')\" type='text' value='0'></td>"
                                //         + "<td  style='text-align: center; padding:0px'><input class='item_Remark form-control' style='background-color:;border:0px' id='item_Remark'  type='text' value=''></td>"
                                //         + "<td ><a style='color:green;' href='javascript:void(0);'><span class='btn_ar_add glyphicon glyphicon-plus'></span></a>&nbsp;&nbsp;&nbsp;<a  style='color:red;' href='javascript:void(0);'><span class='btn_ar_remove glyphicon glyphicon-remove'></span></a></td>"
                                //   + "</tr>";

                                var tr = $(e).parents("tr").clone().show();

                                var item_PaymentObjectName_Input_Id = "item_PaymentObjectName_Input_" + $("#tblInternalFeeObjects>tbody>tr").length;

                                $(tr).find(":input[type='text']").val('');
                                $(tr).find(":input[type='hidden']").val('');
                                $(tr).find(":input[type='checkbox']").attr("checked", false);
                                $(tr).find(".item_PaymentObjectName_Input").attr("id", item_PaymentObjectName_Input_Id)
                                $(tr).find(".item_PaymentObjectName_Input").prev().remove();
                                $(tr).find(".item_PaymentObjectName_Input").removeAttr("disabled");
                                $(tr).find(".item_PaymentObjectName_Input").css("width","100%");
                                $(tr).find("#item_InternalFeeAmount").val('0');

                                $(e).parents("tr").after(tr);

                                c.Cases.Case.InternalFees.InternalFee.Objects.ObjectItem.BindEvent();

                                var businessOwner = new AssociateAvailableUser_PaymentObject(
                                   $("#divAssociateUserList_InternalFee"),
                                   $(tr).find("#" + item_PaymentObjectName_Input_Id),
                                   $(tr).find("#" + item_PaymentObjectName_Input_Id),
                                   c.Cases.Case.InternalFees.InternalFee.Objects.PaymentObject.AddIn
                               );

                                return tr;
                            },
                            Clear: function (e) {
                                $(e).parents("tr").find(":input[type='text']").val('');
                                $(e).parents("tr").find(":input[type='hidden']").val('');
                                $(e).parents("tr").find(":input[type='checkbox']").attr("checked", false);
                            },
                            Remove: function (e) {
                                $(e).parents("tr").remove();
                            },

                            SyncPaymentType: function () {
                                var internalFeeTypeId = $($("#tblInternalFeeObjects tbody tr")[0]).find("#item_InternalFeeTypeId").val();
                                $("#tblInternalFeeObjects tbody tr").each(function (i, e) {
                                    $(e).find("#item_InternalFeeTypeId").val(internalFeeTypeId);
                                    $(e).find("#item_InternalFeeTypeId").change();
                                })
                            },
                            SyncPaymentObject: function () {
                                //var item_InternalFeeTypeId = $($("#tblInternalFeeObjects tbody tr")[1]).find("#item_InternalFeeAmount");
                                var item_InternalFeeTypeId = $("#tblInternalFeeObjects>tbody>tr:first").find("#item_InternalFeeAmount");
                                $("#tblInternalFeeObjects tbody tr").each(function (i, e) {
                                    $(e).find("#item_InternalFeeTypeId").val($(item_InternalFeeAmount).val());
                                })
                            },
                            SyncPaymentAmount: function () {
                                var amount = $($("#tblInternalFeeObjects tbody tr")[0]).find("#item_InternalFeeAmount").val();
                                $("#tblInternalFeeObjects tbody tr").each(function (i, e) {
                                    $(e).find("#item_InternalFeeAmount").val(amount);
                                })
                            },
                            SyncPaymentRemark: function () {
                                var item_Remark = $($("#tblInternalFeeObjects tbody tr")[0]).find("#item_Remark");
                                $("#tblInternalFeeObjects tbody tr").each(function (i, e) {
                                    $(e).find("#item_Remark").val($(item_Remark).val());
                                })
                            },
                        },
                        PaymentObject: {
                            AddIn: function (target, username, userchname, permitinput) {
                                var existsUser = false;

                                $("a[name='paymentobjectname']", target).each(function () {
                                    if ($(this).attr("username") == username) {
                                        existsUser = true;
                                        return true;
                                    }
                                });

                                //重复
                                if (existsUser) return true;

                                var $tag = $("<span class='tag label label-info'>"
                                             + "<a name='paymentobjectname' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                             + " username='" + username + "'"
                                             + " userchname='" + userchname + "'"
                                             + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);'   data-original-title=" + userchname + " '>" + userchname + "</a>"
                                             + "<span class='paymentobjectremove' data-role='remove'></span>"
                                           + "</span>");

                                if (!permitinput) {
                                    $(target).find(".item_PaymentObjectName_Input").css("width", "0px");
                                }
                                $(target).find(".item_PaymentObjectName_Input").before($tag);
                                $tag.after(' ');

                            },
                            Remove: function (e) {
                                $(e).parents("tr").find(".item_PaymentObjectName_Input").css("width", "100%");
                                $(e).parent().remove();
                            },
                        },
                    },
                    MultiCreate: function (caseNos) {
                        var data = {};
                        var url = AP_ROOT + AP_PAGE_ID + "/Legal/InternalFee/MultiCreate";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#internalFeeModal').modal({ backdrop: 'static', keyboard: false });
                            $('#internalFeeModal').on('hidden.bs.modal', function () {
                                $("#internalFeeModal").remove();
                            });

                            c.Cases.Case.InternalFees.InternalFee.Objects.List(caseNos);
                        });
                    },
                    Edit: function (internalFeeId) {
                        if (parseInt($("#Case_Basic_CaseId").val()) == 0) {
                            $.showModalMessageBox("请先保存案件基本资料.");
                            return false;
                        }

                        var data = {
                            internalFeeId: internalFeeId
                        };

                        var url = AP_ROOT + AP_PAGE_ID + "/Legal/InternalFee/Edit";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#internalFeeModal').modal({ backdrop: 'static', keyboard: false });
                            $('#internalFeeModal').on('hidden.bs.modal', function () {
                                $("#internalFeeModal").remove();
                            });
                        });
                    },
                    Delete: function (internalFeeIds) {
                        var data = {
                            internalFeeIds: internalFeeIds
                        };

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/InternalFee/Delete", data, function (response) {
                            if (response.IsSuccess) {
                                c.Cases.Case.InternalFees.List();
                                $.showModalMessageBox("删除成功.");
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });

                    },
                    Close: function () {

                        if ($('.slide-panel-container').length) {
                            $('.slide-panel-container').empty();
                            $('.slide-panel-container').removeClass('show-panel');
                        }

                        if ($('#internalFeeModal').length) {
                            $('#internalFeeModal').modal('hide');
                        }

                    },
                    CreateUpdate: function () {
                        try {

                            var data = {};

                            if ($("#InternalFee_PaymentObject").val() == '') {
                                $.showModalMessageBox("请输入支付对象.");
                                return false;
                            }
                            if ($("#InternalFee_FeeTypeId").val() == '') {
                                $.showModalMessageBox("请选择费用类型.");
                                return false;
                            }

                            if ($("#InternalFee_PaymentDate").val() == '') {
                                $.showModalMessageBox("请输入支付时间.");
                                return false;
                            }

                            if ($("#InternalFee_Amount").val() == '') {
                                dataIsNOk = true;
                                $.showModalMessageBox("请输入费用金额.");
                                return false;
                            }

                            if (!$("#InternalFee_Amount").isMoney()) {
                                $.showModalMessageBox("金额格式不正确，请重新输入.");
                                return false;
                            }

                            var paidAmount = parseFloat($("#InternalFee_PaidAmount").val());
                            var internalFeeAmount = parseFloat($("#InternalFee_Amount").val());
                            
                            if (internalFeeAmount < paidAmount) {
                                $.showModalMessageBox("已付款金额大于费用金额，不允许修改.");
                                return false;
                            }

                            data["InternalFeeObjects[0].CaseId"] = $("#Case_Basic_CaseId").val();
                            data["InternalFeeObjects[0].CaseNo"] = $("#Case_Basic_CaseNo").val();
                            data["InternalFeeObjects[0].InternalFeeId"] = $("#InternalFee_InternalFeeId").val();
                            data["InternalFeeObjects[0].PaymentObject"] = $("#InternalFee_PaymentObject").val();
                            data["InternalFeeObjects[0].PaymentDate"] = $("#InternalFee_PaymentDate").val();
                            data["InternalFeeObjects[0].FeeTypeId"] = $("#InternalFee_FeeTypeId").val();
                            data["InternalFeeObjects[0].Amount"] = $("#InternalFee_Amount").val();
                            data["InternalFeeObjects[0].Remark"] = $("#InternalFee_Remark").val();

                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/InternalFee/InternalFeeObjectsCreate", data, function (response) {
                                if (response.IsSuccess) {
                                    c.Cases.Case.InternalFees.List();
                                    c.Cases.Case.InternalFees.InternalFee.Close();
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });

                        } catch (e) {
                            alert(e);
                        }
                    },
                    MultiCreateUpdate: function (callback_func) {
                        try {
                            var data = {};
                            var dataIsNOk = false;
                            var i = 0;
                            $("#tblInternalFeeObjects>tbody>tr").each(function (j, e) {

                                if ($(e).css("display") != 'none') {

                                    if ($(e).find("#item_InternalFeeTypeId").val() == '-100') {
                                        dataIsNOk = true;
                                        $.showModalMessageBox("第" + (j+1) + "行,请选择费用类型.");
                                        return false;
                                    }

                                    if ($(e).find("#item_InternalFeeAmount").val() == '0') {
                                        dataIsNOk = true;
                                        $.showModalMessageBox("第" + (j) + "行,请输入费用金额.");
                                        return false;
                                    }

                                    if (!$(e).find("#item_InternalFeeAmount").isMoney()) {
                                        dataIsNOk = true;
                                        $.showModalMessageBox("第" + (j+1) + "行,金额格式不正确，请重新输入.");
                                        return false;
                                    }

                                    if ($(e).find("#item_PaymentDate").val() == '') {
                                        dataIsNOk = true;
                                        $.showModalMessageBox("第" + (j+1) + "行,请输入支付时间.");
                                        return false;
                                    }

                                    var paymentobjects = new Array();
                                    var paymentobjectnames = new Array();

                                    $("a[name='paymentobjectname']", $(e)).each(function () {
                                        paymentobjects.push($(this).attr("username"));
                                        paymentobjectnames.push($(this).attr("userchname"));
                                    });

                                    if (paymentobjects.length == 0) {
                                        dataIsNOk = true;
                                        $.showModalMessageBox("第" + (j+1) + "行,请选择收款人.");
                                        return false;
                                    }

                                    if (paymentobjects.length > 1) {
                                        dataIsNOk = true;
                                        $.showModalMessageBox("第" + (j+1) + "行,只能选择一个收款人.");
                                        return false;
                                    }

                                    data["InternalFeeObjects[" + i + "].CaseId"] = $(e).find("#item_InternalFeeTypeId").attr("caseid");
                                    data["InternalFeeObjects[" + i + "].CaseNo"] = $(e).find("#item_InternalFeeTypeId").attr("caseno");
                                    data["InternalFeeObjects[" + i + "].PaymentObject"] = paymentobjects[0];
                                    data["InternalFeeObjects[" + i + "].PaymentObjectName"] = paymentobjectnames[0];
                                    //data["InternalFeeObjects[" + i + "].PaymentDate"] = $(e).find("#item_PaymentDate").val();
                                    data["InternalFeeObjects[" + i + "].FeeTypeId"] = $(e).find("#item_InternalFeeTypeId").val();
                                    data["InternalFeeObjects[" + i + "].Amount"] = $(e).find("#item_InternalFeeAmount").val();
                                    data["InternalFeeObjects[" + i + "].Remark"] = $(e).find("#item_Remark").val();

                                    i++;
                                }
                            });

                            if (dataIsNOk) return false;
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/InternalFeeObjectsCreate", data, function (response) {
                                if (response.IsSuccess) {

                                    c.Cases.Case.InternalFees.InternalFee.Close();

                                    if (callback_func) {
                                        callback_func(response.Data.PaymentList);
                                        //c.Cases.Case.InternalFees.List();
                                    }
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });

                        } catch (e) {
                            alert(e);
                        }
                    },
                },

                Payment: {
                    View: function (paymentId) {
                        var url = AP_ROOT + "5001004001/FAM/InternalFee/PaymentView?paymentId=" + paymentId;
                        window.open(url);
                    },
                    Application: {
                        CreateUpdateCallBack: function (paymentList) {
                            
                            var data = {};
                            var url = AP_ROOT + AP_PAGE_ID + "/FAM/InternalFee/MultiCreatePaymentList";
                            $.openLoading();

                            $("<div></div>").load(url, data, function (result) {
                                $.closeLoading();
                                $(".slide-panel-container").empty();
                                $(".slide-panel-container").append(result);
                                $(".slide-panel-container").addClass("show-panel");

                                $("tbody", "#tblPaymentObjects").clearRow();
                                var tr = '';
                                $.each(paymentList, function (i, p) {
                                    $.each(p.PaymentObjects, function (i, po) {

                                        var feeTypeName = $.lsCaseFeeType.getCaseFeeTypeName(po.InternalFeeTypeId);
                                        tr += "<tr>"
                                                + "<td  style='text-align: center; padding:0px'> <a href='javascript:void(0)' onclick='javascript:c.Cases.Case.InternalFees.Payment.View(\"" + p.PaymentBasic.PaymentId + "\")'>" + p.PaymentBasic.ApplicationNo + "</a></td>"
                                                + "<td  style='text-align: center; padding:0px'> " + (po.PaymentObjectName == null ? "" : po.PaymentObjectName) + "</td>"
                                                + "<td  style='text-align: center; padding:0px'> " + feeTypeName + "</td>"
                                                + "<td  style='text-align: center; padding:0px'> " + po.InternalFeePayAmount + "</td>"
                                                + "<td  style='text-align: center; padding:0px'> " + p.PaymentBasic.CaseNo + "</td>"
                                                + "<td  style='text-align: center; padding:0px'> " + (p.PaymentBasic.ApplicationDate == null ? '' : getDate(convertJsonDateToJSDate(p.PaymentBasic.ApplicationDate))) + "</td>"
                                             + "</tr>"

                                        
                                    });
                                });

                                $('#tblPaymentObjects>tbody').html(tr);
                            });
                        },
                    },
                },

                PaymentApply: {
                    /*垫付款申请*/
                    Open: function () {
                        if (parseInt($("#Case_Basic_CaseId").val()) == 0) {
                            $.showModalMessageBox("请先保存案件基本资料.");
                            return false;
                        }
                        var caseFeeIds = $.checkbox.vals("chkInternalFeeId");
                        if (caseFeeIds.length == 0) {
                            $.showModalMessageBox("请选择费用进行付款申请.");
                            return false;
                        }
                        var caseNo = $("#Case_Basic_CaseNo").val()
                        var url = AP_ROOT + AP_PAGE_ID + '/FAM/InternalFee/PaymentCreate?caseNo=' + caseNo + '&caseFeeIds=' + caseFeeIds.join(",");
                        addtabs(url, "申请付款");
                        //window.open(url);
                    },
                },

                /*案件费用列表*/
                List: function () {
                    var data = {
                        caseId: $("#Case_Basic_CaseId").val(),
                        pageNo: $("#PageNo").val(),
                        pageSize: $("#PageSize").val()
                    };
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/InternalFee/List", data, function (response) {
                        if (response.IsSuccess) {
                            $.openLoading();
                            $("#dv_List").empty();
                            $("#dv_List").html(response.Data);

                            $("tfoot", "#tblCaseFee").show();

                            $(".pull-right.page-box.casefee").cPaging({
                                totalCount: parseInt($("#TotalCount").val()),
                                pageNo: parseInt($("#PageNo").val()),
                                pageSize: parseInt($("#PageSize").val()),
                                callBack: c.Cases.Case.InternalFees.List,
                                callBackArgs: null
                            });

                            var totalCount = parseInt($("#TotalCount").val());

                            c.ResetSize();

                            if (totalCount > 0) {
                                $("tfoot", "#tblCaseFee").show();
                                $(".simple-grid-none-data-wrap").hide();
                            } else {
                                $("tfoot", "#tblCaseFee").hide();
                                $(".simple-grid-none-data-wrap").show();
                            }

                            $.closeLoading();
                        }
                    }, true);
                },
                Selected: function (e) {
                    if ($(e).prop('checked') == true) {
                        $.checkbox.all("chkInternalFeeId");
                        $.checkbox.all("chkInternalFeeAll");

                    } else {
                        $.checkbox.not("chkInternalFeeId");
                        $.checkbox.not("chkInternalFeeAll");
                    }
                },

            },
            /*日志*/
            CaseLogs: {
                List: function () {
                    var data = { caseNo: $("#Case_Basic_CaseNo").val() };
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseLog/CaseLogList", data, function (response) {
                        if (response.IsSuccess) {
                            $.openLoading();
                            $(".caselogs").empty();
                            $(".caselogs").html(response.Data);
                            $.closeLoading();
                        }
                    }, true);
                },
                OperatingLogList: function () {
                    var data = {
                        caseNo: $("#Case_Basic_CaseNo").val(),
                        pageNo: $("#PageNo").val(),
                        pageSize: $("#PageSize").val()
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseLog/CaseOperatingLogList", data, function (response) {
                        if (response.IsSuccess) {
                            $.openLoading();
                            $("#dv_List").empty();
                            $("#dv_List").html(response.Data);

                            $(".pull-right.page-box.caselog").cPaging({
                                totalCount: parseInt($("#TotalCount").val()),
                                pageNo: parseInt($("#PageNo").val()),
                                pageSize: parseInt($("#PageSize").val()),
                                callBack: c.Cases.Case.CaseLogs.OperatingLogList,
                                callBackArgs: null
                            });

                            var totalCount = parseInt($("#TotalCount").val());

                            c.ResetSize();

                            if (totalCount > 0) {
                                $("tfoot", "#tblCaseLog").show();
                                $(".simple-grid-none-data-wrap").hide();
                            } else {
                                $("tfoot", "#tblCaseLog").hide();
                                $(".simple-grid-none-data-wrap").show();
                            }

                            $.closeLoading();
                        }
                    }, true);
                },
                CaseLog: {

                    /*打开案件日志*/
                    View: function (logId) {

                        if (parseInt($("#Case_Basic_CaseId").val()) == 0) {
                            $.showModalMessageBox("请先保存案件基本资料.");
                            return false;
                        }

                        var data =
                        {
                            caseId: $("#Case_Basic_CaseId").val(),
                            caseNo: $("#Case_Basic_CaseNo").val(),
                            logId: logId
                        };

                        var url = AP_ROOT + AP_PAGE_ID + "/Legal/CaseLog/CaseLog";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#caseLogModal').modal({ backdrop: 'static', keyboard: false });
                            $('#caseLogModal').on('hidden.bs.modal', function () {
                                $("#caseLogModal").remove();
                            });
                        });

                    },

                    Open: function (caseNos) {
                        if (caseNos == '')
                        {
                            $.showModalMessageBox("请选择案件.");
                            return false;
                        }
                        var data = { caseNos: caseNos.join(',') };                     
                        var url = AP_ROOT + AP_PAGE_ID + "/Legal/CaseLog/CaseLog";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#caseLogModal').modal({ backdrop: 'static', keyboard: false });
                            $('#caseLogModal').on('hidden.bs.modal', function () {
                                $("#caseLogModal").remove();
                            });
                        });
                    },

                    /*关闭案件日志*/
                    Close: function () {
                        $('#caseLogModal').modal('hide');
                    },
                    CreateUpdate: function () {
                        if ($("#CaseLog_Content").val() == '') {
                            $.showModalMessageBox("请输入日志内容");
                            return false;
                        }

                        $("#caseLog").ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseLog/CaseLogCreate", function (response) {
                            if (response.IsSuccess) {
                                $.showModalMessageBox("保存成功.");
                                $('#caseLogModal').modal('hide');

                                if ($(".caselogs").length > 0)
                                {
                                    c.Cases.Case.CaseLogs.List();
                                }
                                
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },
                    Delete: function () {
                        var data = { caseLogId: $("#CaseLog_LogId").val() };
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseLog/CaseLogDelete", data, function (response) {
                            if (response.IsSuccess) {
                                $.showModalMessageBox("删除成功.");
                                c.Cases.Case.CaseLogs.List();
                                c.Cases.Case.CaseLogs.CaseLog.Close();
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },
                },
            },
            /*案件事件提醒*/
            CaseEvents: {
                List: function () {
                    var data = { caseId: $("#Case_Basic_CaseId").val() };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseEvent/CaseEventList", data, function (response) {

                        if (response.IsSuccess) {
                            $.openLoading();
                            $(".caseevents").empty();
                            $(".caseevents").html(response.Data);
                            $.closeLoading();
                        }
                    }, true);
                },

                CaseEvent: {
                    Open: function (eventId, eventTypeId, eventOperator, eventTime, deadline, eventContent) {
                        if (parseInt($("#Case_Basic_CaseId").val()) == 0) {
                            $.showModalMessageBox("请先保存案件基本资料.");
                            return false;
                        }
                        var data =
                        {
                            caseNo: $("#Case_Basic_CaseNo").val(),
                            eventId: eventId
                        };

                        data["CaseEvent.EventId"] = eventId;
                        data["CaseEvent.EventTypeId"] = eventTypeId;
                        data["CaseEvent.Operator"] = eventOperator;
                        data["CaseEvent.EventTime"] = eventTime;
                        data["CaseEvent.Deadline"] = deadline;
                        data["CaseEvent.EventContent"] = eventContent;

                        var url = AP_ROOT + AP_PAGE_ID + "/Legal/CaseEvent/CaseEvent";
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

                    /*关闭案件提醒*/
                    Close: function () {
                        $('#caseEventModal').modal('hide');
                    },
                    CreateUpdate: function () {

                        if ($("#CaseEvent_Deadline").val() == '') {
                            $.showModalMessageBox("请输入截止日期.");
                            return false;
                        }

                        if ($("#CaseEvent_EventContent").val() == '') {
                            $.showModalMessageBox("请输入提醒内容.");
                            return false;
                        }


                        $("#caseEvent").ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseEvent/CaseEventCreate", function (response) {
                            if (response.IsSuccess) {
                                $.showModalMessageBox("保存成功.");
                                $('#caseEventModal').modal('hide');
                                c.Cases.Case.CaseEvents.List();

                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },

                    Delete: function () {
                        var data = { caseEventId: $("#EventId").val() };
                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseEvent/CaseEventDelete", data, function (response) {
                            if (response.IsSuccess) {
                                $.showModalMessageBox("删除成功.");
                                c.Cases.Case.CaseEvents.List();
                                c.Cases.Case.CaseEvents.CaseEvent.Close();
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },
                },

                /*打开案件提醒*/

            },

            CaseTasks: {
                BindEvent: function () {
                    /*案件任务*/
                    //$("#btnCaseTaskCreate").off().on("click", function () {
                    //    caseInfo.CaseTask.Open();
                    //});

                    $("#btnCaseTaskCreate").off().on("click", function () {
                        var caseNos = new Array();
                        caseNos.push($("#Case_Basic_CaseNo").val());
                        //task.Tasks.Task.Open(caseNos);
                        c.Cases.Case.CaseTasks.CaseTask.Open(caseNos);
                    });

                    $("#btnCaseTaskClose,#btnCaseTaskCancel").off().on("click", function () {
                        caseInfo.CaseTask.Close();
                    });

                    $("#btnCaseTask").off().on("click", function () {
                        caseInfo.CaseTask.CreateUpdate();
                    });
                },
                List: function () {
                    var data = {
                        caseId: $("#Case_Basic_CaseId").val(),
                        pageNo: $("#PageNo").val(),
                        pageSize: $("#PageSize").val()
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseTask/CaseTaskList", data, function (response) {
                        if (response.IsSuccess) {
                            $.openLoading();
                            $("#dv_List").empty();
                            $("#dv_List").html(response.Data);

                            $(".pull-right.page-box.casetask").cPaging({
                                totalCount: parseInt($("#TotalCount").val()),
                                pageNo: parseInt($("#PageNo").val()),
                                pageSize: parseInt($("#PageSize").val()),
                                callBack: c.Cases.Case.CaseTasks.List,
                                callBackArgs: null
                            });

                            var totalCount = parseInt($("#TotalCount").val());

                            c.ResetSize();

                            if (totalCount > 0) {
                                $("tfoot", "#tblCaseTask").show();
                                $(".simple-grid-none-data-wrap").hide();
                            } else {
                                $("tfoot", "#tblCaseTask").hide();
                                $(".simple-grid-none-data-wrap").show();
                            }

                            c.Cases.Case.CaseTasks.BindEvent();
                            //caseInfo.CaseTask.BindMenu();

                            $.closeLoading();
                        }
                    }, true);
                },
                Selected: function (e) {
                    if ($(e).prop('checked') == true) {
                        $.checkbox.all("chkTaskId");
                        $.checkbox.all("chkTaskAll");

                    } else {
                        $.checkbox.not("chkTaskId");
                        $.checkbox.not("chkTaskAll");
                    }
                },
                CaseTask: {
                    View: function (taskId) {
                        var url = AP_ROOT + AP_PAGE_ID + "/TP/Task/TaskDetail?taskId=" + taskId;
                        window.open(url);
                    },

                    Open: function (caseNos) {
                        var data = { caseNos: caseNos.join(',') };
                        var url = AP_ROOT + AP_PAGE_ID + "/TP/Task/TaskCreate";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(".slide-panel-container").empty();
                            $(".slide-panel-container").append(result);
                            $(".slide-panel-container").addClass("show-panel");

                            /*任务类型*/
                            $("#Task_TaskTitle").unbind("click");
                            $("#Task_TaskTitle").click(function () {
                                var tirgger = this;
                                
                                if ($("#Case_Basic_CaseTypeId").length>0) {
                                    var html = $.caseTaskType.getCaseTaskTypeListHtml($("#Case_Basic_CaseTypeId").val());
                                    $(".divCaseTaskType").html(html);
                                    $("#hidCaseTaskTypeName").val($(tirgger).attr("id"));
                                    $("#hidCaseTaskTypeId").val("Task_TaskTypeId");
                                    $("#divCaseTaskTypeList").css({
                                        "position": "absolute",
                                        "left": $(this).position().left,
                                        "top": $(this).position().top + 25,
                                        "z-index": 1200
                                    }).show();
                                }
                                return false;
                            });
                            $(document).off('click', '#divCaseTaskTypeList ul li').on('click', '#divCaseTaskTypeList ul li', function (e) {
                                var taskTypeId = $(this).find("a").attr("caseTaskTypeId");
                                var taskTypeName = $(this).find("a").text();
                                var taskTypeNameText = $(this).find("a").attr("text");
                                var currentSelectedControl = $("#hidCaseTaskTypeName").val();
                                var currentSelectedIdControl = $("#hidCaseTaskTypeId").val();
                                $("#" + currentSelectedControl).val(taskTypeName);
                                $("#Task_TaskTypeId").val(taskTypeId);

                                if (taskTypeId == '100002' && $("#Case_Basic_CaseAssistant").val() != '' && $("#Case_Basic_CaseAssistantName").val() != '') {
                                    //文书准备
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn($("#Case_Basic_CaseAssistant").val().split(',')[0], $("#Case_Basic_CaseAssistantName").val().split(',')[0]);
                                    var taskEndTime = new Date().addDays(15).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }
                                if (taskTypeId == '100004' && $("#Case_Basic_CaseAssistant").val() != '' && $("#Case_Basic_CaseAssistantName").val() != '') {
                                    //案件跟进
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn($("#Case_Basic_CaseAssistant").val().split(',')[0], $("#Case_Basic_CaseAssistantName").val().split(',')[0]);
                                    var taskEndTime = new Date().addDays(20).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }
                                else if (taskTypeId == '100003' && $("#Case_Basic_CaseLawyer").val() != '' && $("#Case_Basic_CaseLawyerName").val() != '') {
                                    //案件审核
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn($("#Case_Basic_CaseLawyer").val().split(',')[0], $("#Case_Basic_CaseLawyerName").val().split(',')[0]);
                                    var taskEndTime = new Date().addDays(7).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }
                                else if (taskTypeId == '100015' ) {
                                    //取证物任务
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn(GV_LS.TaskOfficer, GV_LS.TaskOfficerName);
                                    var taskEndTime = new Date().addDays(7).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }
                                else if (taskTypeId == '100020' && $("#Case_Basic_CaseAssistant").val() != '' && $("#Case_Basic_CaseAssistantName").val() != '') {
                                    //诉讼费退费
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn($("#Case_Basic_CaseAssistant").val().split(',')[0], $("#Case_Basic_CaseAssistantName").val().split(',')[0]);
                                    var taskEndTime = new Date().addDays(7).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }

                                $("#divCaseTaskTypeList").hide();
                            });
                        });
                    },

                    OpenTask: function (caseNo) {
                        c.Cases.Case.CaseTasks.CaseTask.OpenTasks(new Array(caseNo));
                    },

                    OpenTasks: function (caseNos) {
                        var data = { caseNos: caseNos.join(',') };
                        var url = AP_ROOT + AP_PAGE_ID + "/TP/Task/TaskCreate";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(".slide-panel-container").empty();
                            $(".slide-panel-container").append(result);
                            $(".slide-panel-container").addClass("show-panel");

                            /*任务类型*/
                            $("#Task_TaskTitle").unbind("click");
                            $("#Task_TaskTitle").click(function () {
                                var tirgger = this;
                                if ($("#SearchCondition_CaseTypeId").length > 0) {
                                    var html = $.caseTaskType.getCaseTaskTypeListHtml($("#SearchCondition_CaseTypeId").val());
                                    $(".divCaseTaskType").html(html);
                                    $("#hidCaseTaskTypeName").val($(tirgger).attr("id"));
                                    $("#divCaseTaskTypeList").css({
                                        "position": "absolute",
                                        "left": $(this).position().left,
                                        "top": $(this).position().top + 25,
                                        "z-index": 1200
                                    }).show();
                                }
                                return false;
          
                            });
                            $(document).off('click', '#divCaseTaskTypeList ul li').on('click', '#divCaseTaskTypeList ul li', function (e) {
                                var taskTypeId = $(this).find("a").attr("caseTaskTypeId");
                                var taskTypeName = $(this).find("a").text();
                                var taskTypeNameText = $(this).find("a").attr("text");
                                var currentSelectedControl = $("#hidCaseTaskTypeName").val();
                                //var currentSelectedIdControl = $("#hidCaseTaskTypeId").val();
                                $("#" + currentSelectedControl).val(taskTypeName);
                                $("#Task_TaskTypeId").val(taskTypeId);
                                
                                if (taskTypeId == '100002') {
                                    //文书准备
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn("caseAssistant", "默认文书");
                                    var taskEndTime = new Date().addDays(15).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }
                                if (taskTypeId == '100004') {
                                    //案件跟进
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn("caseAssistant", "默认文书");
 
                                    var taskEndTime = new Date().addDays(20).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }
                                else if (taskTypeId == '100003') {
                                    //案件审核
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn("caseLawyer", "默认经办律师");
                                    //task.Tasks.Task.Officer.AddIn($("#Case_Basic_CaseLawyer").val().split(',')[0], $("#Case_Basic_CaseLawyerName").val().split(',')[0]);
                                    var taskEndTime = new Date().addDays(7).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }
                                else if (taskTypeId == '100015') {
                                    //取证物任务
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn(GV_LS.TaskOfficer, GV_LS.TaskOfficerName);
                                    var taskEndTime = new Date().addDays(7).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }
                                else if (taskTypeId == '100020' && $("#Case_Basic_CaseAssistant").val() != '' && $("#Case_Basic_CaseAssistantName").val() != '') {
                                    //诉讼费退费
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn("caseAssistant", "默认文书");
                                    var taskEndTime = new Date().addDays(7).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }

                                $("#divCaseTaskTypeList").hide();
                            });
                        });
                    },

                    Close: function () {
                        $('#caseTaskModal').modal('hide');
                    },
                    CreateUpdate: function () {

                        if ($("#CaseTask_TaskTitle").val().trim() == '') {
                            $.showModalMessageBox("请输入任务标题");
                            return false;
                        }
                        if ($("#CaseTask_Officer").val().trim() == '') {
                            $.showModalMessageBox("请输入负责人");
                            return false;
                        }
                        //if ($("#CaseTask_TaskBeginTime").val() == '') {
                        //    $.showModalMessageBox("请输入任务开始时间");
                        //    return false;
                        //}
                        if ($("#CaseTask_TaskEndTime").val() == '') {
                            $.showModalMessageBox("请输入任务结束时间");
                            return false;
                        }

                        if ($("#CaseTask_TaskEndTime").val() == '') {
                            $.showModalMessageBox("请输入任务结束时间");
                            return false;
                        }

                        var data = {};

                        data["CaseTask.TaskId"] = $("#CaseTask_TaskId").val();
                        data["CaseTask.CaseId"] = $("#Case_Basic_CaseId").val();
                        data["CaseTask.CaseNo"] = $("#Case_Basic_CaseNo").val();
                        data["CaseTask.CustomerNo"] = $("#Case_Basic_CustomerNo").val();
                        data["CaseTask.TaskPriority"] = $("#CaseTask_TaskPriorityId").val();
                        data["CaseTask.TaskTitle"] = $("#CaseTask_TaskTitle").val();
                        data["CaseTask.Officer"] = $("#CaseTask_Officer").val();
                        //data["CaseTask.TaskBeginTime"] = $("#CaseTask_TaskBeginTime").val();
                        data["CaseTask.TaskEndTime"] = $("#CaseTask_TaskEndTime").val();
                        data["CaseTask.TaskContent"] = $("#CaseTask_TaskContent").val();

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseTask/CaseTaskCreate", data, function (response) {
                            if (response.IsSuccess) {
                                $('#caseTaskModal').modal('hide');
                                c.Cases.Case.CaseTasks.List();
                                //caseInfo.LoadCase($("#Case_Basic_CaseId").val())
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },
                },
                
                BindMenu: function () {
                    $('#taskgridSection').contextMenu('taskMenu', {
                        menuStyle: {
                            width: '152px'
                        },

                        itemStyle: {
                            width: '150px'
                        },

                        bindings: {
                            'create': function (t, e) {
                                caseInfo.CaseTask.Open();
                            },

                            'edit': function (t, e) {
                                var caseTaskId = $(e).find("span").text();
                                if (caseTaskId == '') {
                                    $.showModalMessageBox("请选择任务.");
                                    return false;
                                }
                                caseInfo.CaseTask.Open(caseTaskId);

                                return true;
                            },

                            'refresh': function (t, e) {
                                caseInfo.CaseTask.List();
                            },

                        },
                        onContextMenu: function (e) {
                            return true;
                        },
                        onShowMenu: function (e, menu) {
                            if ($(e.target).parents("tr").find("#taskId")) {
                                var caseTaskId = $(e.target).parents("tr").find("#taskId").text();
                                var canModify = $(e.target).parents("tr").find("#canModify").text();

                                if (canModify == 'True') {
                                    $('#edit', menu).append("<span style='display:none'>" + caseTaskId + "</span>");
                                } else {
                                    $('#edit', menu).remove();
                                }

                            } else {
                                $('#view', menu).remove();
                            }
                            return menu;
                        }
                    });
                },
            },

            CaseClues: {
                BindEvent: function () {
                    /*案件任务*/
                    //$("#btnCaseTaskCreate").off().on("click", function () {
                    //    caseInfo.CaseTask.Open();
                    //});

                    $("#btnCaseTaskCreate").off().on("click", function () {
                        var caseNos = new Array();
                        caseNos.push($("#Case_Basic_CaseNo").val());
                        //task.Tasks.Task.Open(caseNos);
                        c.Cases.Case.CaseTasks.CaseTask.Open(caseNos);
                    });

                    $("#btnCaseTaskClose,#btnCaseTaskCancel").off().on("click", function () {
                        caseInfo.CaseTask.Close();
                    });

                    $("#btnCaseTask").off().on("click", function () {
                        caseInfo.CaseTask.CreateUpdate();
                    });
                },
                List: function () {
                    var data = {
                        caseNo: $("#Case_Basic_CaseNo").val(),
                        pageNo: $("#PageNo").val(),
                        pageSize: $("#PageSize").val()
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseClue/CaseClueList", data, function (response) {
                        if (response.IsSuccess) {
                            $.openLoading();
                            $("#dv_List").empty();
                            $("#dv_List").html(response.Data);

                            $(".pull-right.page-box.caseclue").cPaging({
                                totalCount: parseInt($("#TotalCount").val()),
                                pageNo: parseInt($("#PageNo").val()),
                                pageSize: parseInt($("#PageSize").val()),
                                callBack: c.Cases.Case.CaseClues.List,
                                callBackArgs: null
                            });

                            var totalCount = parseInt($("#TotalCount").val());

                            c.ResetSize();

                            if (totalCount > 0) {
                                $("tfoot", "#tblCaseClueList").show();
                                $(".simple-grid-none-data-wrap").hide();
                            } else {
                                $("tfoot", "#tblCaseClueList").hide();
                                $(".simple-grid-none-data-wrap").show();
                            }

                            //c.Cases.Case.CaseTasks.BindEvent();
                       

                            $.closeLoading();
                        }
                    }, true);
                },
                Selected: function (e) {
                    if ($(e).prop('checked') == true) {
                        $.checkbox.all("chkTaskId");
                        $.checkbox.all("chkTaskAll");

                    } else {
                        $.checkbox.not("chkTaskId");
                        $.checkbox.not("chkTaskAll");
                    }
                },
                CaseTask: {
                    View: function (taskId) {
                        var url = AP_ROOT + AP_PAGE_ID + "/TP/Task/TaskDetail?taskId=" + taskId;
                        window.open(url);
                    },

                    Open: function (caseNos) {
                        var data = { caseNos: caseNos.join(',') };
                        var url = AP_ROOT + AP_PAGE_ID + "/TP/Task/TaskCreate";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(".slide-panel-container").empty();
                            $(".slide-panel-container").append(result);
                            $(".slide-panel-container").addClass("show-panel");

                            /*任务类型*/
                            $("#Task_TaskTitle").unbind("click");
                            $("#Task_TaskTitle").click(function () {
                                var tirgger = this;

                                if ($("#Case_Basic_CaseTypeId").length > 0) {
                                    var html = $.caseTaskType.getCaseTaskTypeListHtml($("#Case_Basic_CaseTypeId").val());
                                    $(".divCaseTaskType").html(html);
                                    $("#hidCaseTaskTypeName").val($(tirgger).attr("id"));
                                    $("#hidCaseTaskTypeId").val("Task_TaskTypeId");
                                    $("#divCaseTaskTypeList").css({
                                        "position": "absolute",
                                        "left": $(this).position().left,
                                        "top": $(this).position().top + 25,
                                        "z-index": 1200
                                    }).show();
                                }
                                return false;
                            });
                            $(document).off('click', '#divCaseTaskTypeList ul li').on('click', '#divCaseTaskTypeList ul li', function (e) {
                                var taskTypeId = $(this).find("a").attr("caseTaskTypeId");
                                var taskTypeName = $(this).find("a").text();
                                var taskTypeNameText = $(this).find("a").attr("text");
                                var currentSelectedControl = $("#hidCaseTaskTypeName").val();
                                var currentSelectedIdControl = $("#hidCaseTaskTypeId").val();
                                $("#" + currentSelectedControl).val(taskTypeName);
                                $("#Task_TaskTypeId").val(taskTypeId);

                                if (taskTypeId == '100002' && $("#Case_Basic_CaseAssistant").val() != '' && $("#Case_Basic_CaseAssistantName").val() != '') {
                                    //文书准备
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn($("#Case_Basic_CaseAssistant").val().split(',')[0], $("#Case_Basic_CaseAssistantName").val().split(',')[0]);
                                    var taskEndTime = new Date().addDays(15).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }
                                if (taskTypeId == '100004' && $("#Case_Basic_CaseAssistant").val() != '' && $("#Case_Basic_CaseAssistantName").val() != '') {
                                    //案件跟进
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn($("#Case_Basic_CaseAssistant").val().split(',')[0], $("#Case_Basic_CaseAssistantName").val().split(',')[0]);
                                    var taskEndTime = new Date().addDays(20).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }
                                else if (taskTypeId == '100003' && $("#Case_Basic_CaseLawyer").val() != '' && $("#Case_Basic_CaseLawyerName").val() != '') {
                                    //案件审核
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn($("#Case_Basic_CaseLawyer").val().split(',')[0], $("#Case_Basic_CaseLawyerName").val().split(',')[0]);
                                    var taskEndTime = new Date().addDays(7).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }
                                else if (taskTypeId == '100015') {
                                    //取证物任务
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn(GV_LS.TaskOfficer, GV_LS.TaskOfficerName);
                                    var taskEndTime = new Date().addDays(7).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }
                                else if (taskTypeId == '100020' && $("#Case_Basic_CaseAssistant").val() != '' && $("#Case_Basic_CaseAssistantName").val() != '') {
                                    //诉讼费退费
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn($("#Case_Basic_CaseAssistant").val().split(',')[0], $("#Case_Basic_CaseAssistantName").val().split(',')[0]);
                                    var taskEndTime = new Date().addDays(7).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }

                                $("#divCaseTaskTypeList").hide();
                            });
                        });
                    },

                    OpenTask: function (caseNo) {
                        c.Cases.Case.CaseTasks.CaseTask.OpenTasks(new Array(caseNo));
                    },

                    OpenTasks: function (caseNos) {
                        var data = { caseNos: caseNos.join(',') };
                        var url = AP_ROOT + AP_PAGE_ID + "/TP/Task/TaskCreate";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(".slide-panel-container").empty();
                            $(".slide-panel-container").append(result);
                            $(".slide-panel-container").addClass("show-panel");

                            /*任务类型*/
                            $("#Task_TaskTitle").unbind("click");
                            $("#Task_TaskTitle").click(function () {
                                var tirgger = this;
                                if ($("#SearchCondition_CaseTypeId").length > 0) {
                                    var html = $.caseTaskType.getCaseTaskTypeListHtml($("#SearchCondition_CaseTypeId").val());
                                    $(".divCaseTaskType").html(html);
                                    $("#hidCaseTaskTypeName").val($(tirgger).attr("id"));
                                    $("#divCaseTaskTypeList").css({
                                        "position": "absolute",
                                        "left": $(this).position().left,
                                        "top": $(this).position().top + 25,
                                        "z-index": 1200
                                    }).show();
                                }
                                return false;

                            });
                            $(document).off('click', '#divCaseTaskTypeList ul li').on('click', '#divCaseTaskTypeList ul li', function (e) {
                                var taskTypeId = $(this).find("a").attr("caseTaskTypeId");
                                var taskTypeName = $(this).find("a").text();
                                var taskTypeNameText = $(this).find("a").attr("text");
                                var currentSelectedControl = $("#hidCaseTaskTypeName").val();
                                //var currentSelectedIdControl = $("#hidCaseTaskTypeId").val();
                                $("#" + currentSelectedControl).val(taskTypeName);
                                $("#Task_TaskTypeId").val(taskTypeId);

                                if (taskTypeId == '100002') {
                                    //文书准备
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn("caseAssistant", "默认文书");
                                    var taskEndTime = new Date().addDays(15).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }
                                if (taskTypeId == '100004') {
                                    //案件跟进
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn("caseAssistant", "默认文书");

                                    var taskEndTime = new Date().addDays(20).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }
                                else if (taskTypeId == '100003') {
                                    //案件审核
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn("caseLawyer", "默认经办律师");
                                    //task.Tasks.Task.Officer.AddIn($("#Case_Basic_CaseLawyer").val().split(',')[0], $("#Case_Basic_CaseLawyerName").val().split(',')[0]);
                                    var taskEndTime = new Date().addDays(7).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }
                                else if (taskTypeId == '100015') {
                                    //取证物任务
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn(GV_LS.TaskOfficer, GV_LS.TaskOfficerName);
                                    var taskEndTime = new Date().addDays(7).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }
                                else if (taskTypeId == '100020' && $("#Case_Basic_CaseAssistant").val() != '' && $("#Case_Basic_CaseAssistantName").val() != '') {
                                    //诉讼费退费
                                    task.Tasks.Task.Officer.Clear();
                                    task.Tasks.Task.Officer.AddIn("caseAssistant", "默认文书");
                                    var taskEndTime = new Date().addDays(7).Format("yyyy-MM-dd hh:mm:ss")
                                    $("#Task_TaskEndTime").val(taskEndTime);
                                }

                                $("#divCaseTaskTypeList").hide();
                            });
                        });
                    },

                    Close: function () {
                        $('#caseTaskModal').modal('hide');
                    },
                    CreateUpdate: function () {

                        if ($("#CaseTask_TaskTitle").val().trim() == '') {
                            $.showModalMessageBox("请输入任务标题");
                            return false;
                        }
                        if ($("#CaseTask_Officer").val().trim() == '') {
                            $.showModalMessageBox("请输入负责人");
                            return false;
                        }
                        //if ($("#CaseTask_TaskBeginTime").val() == '') {
                        //    $.showModalMessageBox("请输入任务开始时间");
                        //    return false;
                        //}
                        if ($("#CaseTask_TaskEndTime").val() == '') {
                            $.showModalMessageBox("请输入任务结束时间");
                            return false;
                        }

                        if ($("#CaseTask_TaskEndTime").val() == '') {
                            $.showModalMessageBox("请输入任务结束时间");
                            return false;
                        }

                        var data = {};

                        data["CaseTask.TaskId"] = $("#CaseTask_TaskId").val();
                        data["CaseTask.CaseId"] = $("#Case_Basic_CaseId").val();
                        data["CaseTask.CaseNo"] = $("#Case_Basic_CaseNo").val();
                        data["CaseTask.CustomerNo"] = $("#Case_Basic_CustomerNo").val();
                        data["CaseTask.TaskPriority"] = $("#CaseTask_TaskPriorityId").val();
                        data["CaseTask.TaskTitle"] = $("#CaseTask_TaskTitle").val();
                        data["CaseTask.Officer"] = $("#CaseTask_Officer").val();
                        //data["CaseTask.TaskBeginTime"] = $("#CaseTask_TaskBeginTime").val();
                        data["CaseTask.TaskEndTime"] = $("#CaseTask_TaskEndTime").val();
                        data["CaseTask.TaskContent"] = $("#CaseTask_TaskContent").val();

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseTask/CaseTaskCreate", data, function (response) {
                            if (response.IsSuccess) {
                                $('#caseTaskModal').modal('hide');
                                c.Cases.Case.CaseTasks.List();
                                //caseInfo.LoadCase($("#Case_Basic_CaseId").val())
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },
                },

                BindMenu: function () {
                    $('#taskgridSection').contextMenu('taskMenu', {
                        menuStyle: {
                            width: '152px'
                        },

                        itemStyle: {
                            width: '150px'
                        },

                        bindings: {
                            'create': function (t, e) {
                                caseInfo.CaseTask.Open();
                            },

                            'edit': function (t, e) {
                                var caseTaskId = $(e).find("span").text();
                                if (caseTaskId == '') {
                                    $.showModalMessageBox("请选择任务.");
                                    return false;
                                }
                                caseInfo.CaseTask.Open(caseTaskId);

                                return true;
                            },

                            'refresh': function (t, e) {
                                caseInfo.CaseTask.List();
                            },

                        },
                        onContextMenu: function (e) {
                            return true;
                        },
                        onShowMenu: function (e, menu) {
                            if ($(e.target).parents("tr").find("#taskId")) {
                                var caseTaskId = $(e.target).parents("tr").find("#taskId").text();
                                var canModify = $(e.target).parents("tr").find("#canModify").text();

                                if (canModify == 'True') {
                                    $('#edit', menu).append("<span style='display:none'>" + caseTaskId + "</span>");
                                } else {
                                    $('#edit', menu).remove();
                                }

                            } else {
                                $('#view', menu).remove();
                            }
                            return menu;
                        }
                    });
                },
            },

            VipCaseTasks: {
                BindEvent: function () {
                    /*案件任务*/
                    //$("#btnCaseTaskCreate").off().on("click", function () {
                    //    caseInfo.CaseTask.Open();
                    //});

                    $("#btnCaseTaskCreate").off().on("click", function () {
                        var caseNos = new Array();
                        caseNos.push($("#Case_Basic_CaseNo").val());
                        task.Tasks.Task.Open(caseNos);
                    });

                    $("#btnCaseTaskClose,#btnCaseTaskCancel").off().on("click", function () {
                        caseInfo.CaseTask.Close();
                    });

                    $("#btnCaseTask").off().on("click", function () {
                        caseInfo.CaseTask.CreateUpdate();
                    });
                },
                List: function () {
                    var data = {
                        caseId: $("#Case_Basic_CaseId").val(),
                        pageNo: $("#PageNo").val(),
                        pageSize: $("#PageSize").val()
                    };

                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/VipCaseTask/CaseTaskList", data, function (response) {
                        if (response.IsSuccess) {
                            $.openLoading();
                            $("#dv_List").empty();
                            $("#dv_List").html(response.Data);

                            $(".pull-right.page-box.casetask").cPaging({
                                totalCount: parseInt($("#TotalCount").val()),
                                pageNo: parseInt($("#PageNo").val()),
                                pageSize: parseInt($("#PageSize").val()),
                                callBack: c.Cases.Case.VipCaseTasks.List,
                                callBackArgs: null
                            });

                            var totalCount = parseInt($("#TotalCount").val());

                            c.ResetSize();

                            if (totalCount > 0) {
                                $("tfoot", "#tblCaseTask").show();
                                $(".simple-grid-none-data-wrap").hide();
                            } else {
                                $("tfoot", "#tblCaseTask").hide();
                                $(".simple-grid-none-data-wrap").show();
                            }

                            c.Cases.Case.VipCaseTasks.BindEvent();
                            //caseInfo.CaseTask.BindMenu();

                            $.closeLoading();
                        }
                    }, true);
                },
                Selected: function (e) {
                    if ($(e).prop('checked') == true) {
                        $.checkbox.all("chkTaskId");
                        $.checkbox.all("chkTaskAll");

                    } else {
                        $.checkbox.not("chkTaskId");
                        $.checkbox.not("chkTaskAll");
                    }
                },
                CaseTask: {
                    View: function (taskId) {
                        var url = AP_ROOT + AP_PAGE_ID + "/TP/Task/TaskDetail?taskId=" + taskId;
                        window.open(url);
                    },
                    Open: function (caseNos) {

                        var data = { caseNos: caseNos.join(',') };
                        var url = AP_ROOT + AP_PAGE_ID + "/TP/Task/TaskCreate";
                        $.openLoading();

                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(".slide-panel-container").empty();
                            $(".slide-panel-container").append(result);
                            $(".slide-panel-container").addClass("show-panel");
                        });
                    },
                    Close: function () {
                        $('#caseTaskModal').modal('hide');
                    },
                    CreateUpdate: function () {

                        if ($("#CaseTask_TaskTitle").val().trim() == '') {
                            $.showModalMessageBox("请输入任务标题");
                            return false;
                        }
                        if ($("#CaseTask_Officer").val().trim() == '') {
                            $.showModalMessageBox("请输入负责人");
                            return false;
                        }
                        //if ($("#CaseTask_TaskBeginTime").val() == '') {
                        //    $.showModalMessageBox("请输入任务开始时间");
                        //    return false;
                        //}
                        if ($("#CaseTask_TaskEndTime").val() == '') {
                            $.showModalMessageBox("请输入任务结束时间");
                            return false;
                        }

                        if ($("#CaseTask_TaskEndTime").val() == '') {
                            $.showModalMessageBox("请输入任务结束时间");
                            return false;
                        }

                        var data = {};

                        data["CaseTask.TaskId"] = $("#CaseTask_TaskId").val();
                        data["CaseTask.CaseId"] = $("#Case_Basic_CaseId").val();
                        data["CaseTask.CaseNo"] = $("#Case_Basic_CaseNo").val();
                        data["CaseTask.CustomerNo"] = $("#Case_Basic_CustomerNo").val();
                        data["CaseTask.TaskPriority"] = $("#CaseTask_TaskPriorityId").val();
                        data["CaseTask.TaskTitle"] = $("#CaseTask_TaskTitle").val();
                        data["CaseTask.Officer"] = $("#CaseTask_Officer").val();
                        //data["CaseTask.TaskBeginTime"] = $("#CaseTask_TaskBeginTime").val();
                        data["CaseTask.TaskEndTime"] = $("#CaseTask_TaskEndTime").val();
                        data["CaseTask.TaskContent"] = $("#CaseTask_TaskContent").val();

                        $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseTask/CaseTaskCreate", data, function (response) {
                            if (response.IsSuccess) {
                                $('#caseTaskModal').modal('hide');
                                c.Cases.Case.CaseTasks.List();
                                //caseInfo.LoadCase($("#Case_Basic_CaseId").val())
                            } else {
                                $.showModalMessageBox(response.Message);
                            }
                        });
                    },
                },
                BindMenu: function () {
                    $('#taskgridSection').contextMenu('taskMenu', {
                        menuStyle: {
                            width: '152px'
                        },

                        itemStyle: {
                            width: '150px'
                        },

                        bindings: {
                            'create': function (t, e) {
                                caseInfo.CaseTask.Open();
                            },

                            'edit': function (t, e) {
                                var caseTaskId = $(e).find("span").text();
                                if (caseTaskId == '') {
                                    $.showModalMessageBox("请选择任务.");
                                    return false;
                                }
                                caseInfo.CaseTask.Open(caseTaskId);

                                return true;
                            },

                            'refresh': function (t, e) {
                                caseInfo.CaseTask.List();
                            },

                        },
                        onContextMenu: function (e) {
                            return true;
                        },
                        onShowMenu: function (e, menu) {
                            if ($(e.target).parents("tr").find("#taskId")) {
                                var caseTaskId = $(e.target).parents("tr").find("#taskId").text();
                                var canModify = $(e.target).parents("tr").find("#canModify").text();

                                if (canModify == 'True') {
                                    $('#edit', menu).append("<span style='display:none'>" + caseTaskId + "</span>");
                                } else {
                                    $('#edit', menu).remove();
                                }

                            } else {
                                $('#view', menu).remove();
                            }
                            return menu;
                        }
                    });
                },
            },

            MergeCase: {
                Open: function () {
                    var data = {};
                    var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/Merge";
                    $.openLoading();

                    $("<div></div>").load(url, data, function (result) {
                        $.closeLoading();
                        $(".slide-panel-container").empty();
                        $(".slide-panel-container").append(result);
                        $(".slide-panel-container").addClass("show-panel");
                    });
                },
                Merge: function () {

                    if ($("#Dest_CaseNo").val().trim() == '') {
                        $.showModalMessageBox("请输入待合并案件编号");
                        return false;
                    }

                    if ($("#Dest_CaseNo").val() == $("#Case_Basic_CaseNo").val())
                    {
                        $.showModalMessageBox("待合并的案号与本案件案号一致，请确认.");
                        return false;
                    }

                    var data = {};
                   
                    data["DestCaseNo"] = $("#Dest_CaseNo").val();
                    data["OrgCaseNo"] =  $("#Case_Basic_CaseNo").val(),
                     $.openLoading();
                    $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/Case/Merged", data, function (response) {
                        if (response.IsSuccess) {
                            $.closeLoading();
                            $.showModalMessageBox("合并成功.");
                            $(".slide-panel-container").empty();
                        } else {
                            $.showModalMessageBox(response.Message);
                        }
                    });
                },
            },

            Archive: {
                TypeId: {
                    Normal : 1,
                    Deficit : 2
                },
                
                Application: {
                    Create: function (caseNos, archiveTypeId) {
                        var data = { archiveTypeId: archiveTypeId};
                        var url = AP_ROOT + AP_PAGE_ID + "/Legal/CaseArchive/ApplicationCreate";
                        $.openLoading();
                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(".slide-panel-container").empty();
                            $(".slide-panel-container").append(result);
                            $(".slide-panel-container").addClass("show-panel");
                            c.Cases.Case.Archive.Application.Objects.List(caseNos);
                        });
                    },
                    ToAudit: function (archiveTypeId,callback_func) {
                        try {
                            
                            var data = {};
                            var dataIsNOk = false;
                            var i = 0;
                            $("#tblObjects>tbody>tr").each(function (j, e) {

                                if ($(e).css("display") != 'none') {

                                    data["Cases[" + i + "].Basic.CaseId"] = $(e).find("#item_Remark").attr("caseid");
                                    data["Cases[" + i + "].Basic.CaseNo"] = $(e).find("#item_Remark").attr("caseno");
                                    data["Cases[" + i + "].Basic.ToAuditRemark"] = $(e).find("#item_Remark").val();

                                    if (archiveTypeId == c.Cases.Case.Archive.TypeId.Deficit && $(e).find("#item_Remark").val() == '')
                                    {
                                        $.showTips("请填写亏损原因.", 0, 3);
                                        dataIsNOk = true;
                                    }

                                    i++;
                                }
                            });

                            data.CaseArchiveTypeId = archiveTypeId;

                            if (dataIsNOk) return false;
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseArchive/ToAudit", data, function (response) {
                                if (response.IsSuccess) {
                                    $.showTips(response.Message, 0, 3);
                                    c.Cases.Case.Archive.Application.Close();
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });

                        } catch (e) {
                            alert(e);
                        }
                    },
                    Objects: {
                        List: function (caseNos) {
                            var data = {
                                caseNos: caseNos
                            };
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseList/GetCaseListByCaseNos", data, function (response) {
                                $("tbody", "#tblObjects").clearRow();
                                if (response.IsSuccess) {
                                    var tr = '';
                                    $.each(response.Data.CaseList, function (i, c) {
                                        tr += "<tr>"
                                              + "<td  style='text-align: center; padding:0px'> " + c.Basic.CaseNo + "</td>"
                                              + "<td  style='text-align: center; padding:0px'> " + c.Basic.CasePhaseName + "</td>"
                                              + "<td  style='text-align: center; padding:0px'><input class='item_Remark form-control' style='background-color:;border:0px' id='item_Remark' "
                                                + " caseid=" + c.Basic.CaseId
                                                + " caseno='" + c.Basic.CaseNo
                                                + "' type='text' value=''></td>"
                                              + "<td ><a  style='color:red;' href='javascript:void(0);'><span class='btn_ar_remove glyphicon glyphicon-remove'></span></a></td>"
                                              + "</tr>";
                                    });
                                    $('#tblObjects>tbody').html(tr);
                                    c.Cases.Case.Archive.Application.Objects.ObjectItem.BindEvent();
                                }
                            });

                        },
                        ObjectItem: {
                            BindEvent: function () {

                                $(".btn_ar_remove").unbind("click");
                                $(".btn_ar_remove").click(function () {
                                    c.Cases.Case.Archive.Application.Objects.ObjectItem.Remove(this);
                                });
                            },
                        
                            Clear: function (e) {
                                $(e).parents("tr").find(":input[type='text']").val('');
                                $(e).parents("tr").find(":input[type='hidden']").val('');
                                $(e).parents("tr").find(":input[type='checkbox']").attr("checked", false);
                            },
                            Remove: function (e) {
                                $(e).parents("tr").remove();
                            },

                            SyncRemark: function () {
                                var item_Remark = $($("#tblObjects tbody tr")[0]).find("#item_Remark");
                                $("#tblObjects tbody tr").each(function (i, e) {
                                    $(e).find("#item_Remark").val($(item_Remark).val());
                                })
                            },

                        },
                       
                    },
                    Close: function () {
                        if ($('.slide-panel-container').length) {
                            $('.slide-panel-container').empty();
                            $('.slide-panel-container').removeClass('show-panel');
                        }
                    },
                },
                Audit: {
                    Open: function (caseNos, archiveTypeId) {
                        var data = {};
                        var url = AP_ROOT + AP_PAGE_ID + "/Legal/CaseArchive/Audit";
                        $.openLoading();
                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(".slide-panel-container").empty();
                            $(".slide-panel-container").append(result);
                            $(".slide-panel-container").addClass("show-panel");
                            $("#archiveTypeId").val(archiveTypeId);
                            c.Cases.Case.Archive.Audit.Objects.List(caseNos, archiveTypeId);
                        });
                    },
                    Approved: function (callback_func) {
                        try {
                            var data = {};
                            var dataIsNOk = false;
                            var i = 0;
                            $("#tblObjects>tbody>tr").each(function (j, e) {
                                if ($(e).css("display") != 'none') {

                                    data["Cases[" + i + "].Basic.CaseId"] = $(e).find("#item_Remark").attr("caseid");
                                    data["Cases[" + i + "].Basic.CaseNo"] = $(e).find("#item_Remark").attr("caseno");
                                    data["Cases[" + i + "].Basic.AuditedRemark"] = $(e).find("#item_Remark").val();

                                    if ($("#archiveTypeId").val() == c.Cases.Case.Archive.TypeId.Deficit && $(e).find("#item_Remark").val() == '') {
                                        $.showTips("请填写审核意见.", 0, 3);
                                        dataIsNOk = true;
                                    }
                                    i++;
                                }
                            });

                            if (dataIsNOk) return false;
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseArchive/Approved", data, function (response) {
                                if (response.IsSuccess) {
                                    $.showTips("已同意.", 0, 3);
                                    c.Cases.Case.Archive.Audit.Close();
                                    c.Cases.PendingList();
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });

                        } catch (e) {
                            alert(e);
                        }
                    },
                    Rejected: function (callback_func) {
                        
                        try {
                            var data = {};
                            var dataIsNOk = false;
                            var i = 0;
                            $("#tblObjects>tbody>tr").each(function (j, e) {
                                if ($(e).css("display") != 'none') {
                                    data["Cases[" + i + "].Basic.CaseId"] = $(e).find("#item_Remark").attr("caseid");
                                    data["Cases[" + i + "].Basic.CaseNo"] = $(e).find("#item_Remark").attr("caseno");
                                    data["Cases[" + i + "].Basic.AuditedRemark"] = $(e).find("#item_Remark").val();

                                    if ($(e).find("#item_Remark").val() == '') {
                                        $.showTips("请填写拒绝理由.", 0, 3);
                                        dataIsNOk = true;
                                    }

                                    i++;
                                }
                            });

                            if (dataIsNOk) return false;
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseArchive/Rejected", data, function (response) {
                                if (response.IsSuccess) {
                                    $.showTips("已拒绝.", 0, 3);
                                    c.Cases.Case.Archive.Audit.Close();
                                    c.Cases.PendingList();
                                } else {
                                    $.showModalMessageBox(response.Message);
                                }
                            });

                        } catch (e) {
                            alert(e);
                        }
                    },
                    Objects: {
                        List: function (caseNos, archiveTypeId) {
                            var data = {
                                caseNos: caseNos
                            };
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseList/GetCaseListByCaseNos", data, function (response) {
                                $("tbody", "#tblObjects").clearRow();
                                if (response.IsSuccess) {
                                    var tr = '';
                                    var auditedRemark = archiveTypeId == c.Cases.Case.Archive.TypeId.Deficit ? '无负责人;有负责人:调查员,责任比例%,责任金额.文书,责任比例%,责任金额.开庭律师,责任比例%,责任金额.' : '';
                                    $.each(response.Data.CaseList, function (i, c) {
                                        tr += "<tr>"
                                            + "<td  style='text-align: center; padding:0px'> " + c.Basic.CaseNo + "</td>"
                                            + "<td  style='text-align: center; padding:0px'> " + c.Basic.CasePhaseName + "</td>"
                                            + "<td  style='text-align: center; padding:0px'><input class='item_Remark form-control' style='background-color:;border:0px' id='item_Remark' "
                                            + " caseid=" + c.Basic.CaseId
                                            + " caseno='" + c.Basic.CaseNo
                                            + "' type='text' value='" + auditedRemark + "'></td>"
                                            + "<td ><a  style='color:red;' href='javascript:void(0);'><span class='btn_ar_remove glyphicon glyphicon-remove'></span></a></td>"
                                            + "</tr>";
                                    });
                                    $('#tblObjects>tbody').html(tr);
                                    c.Cases.Case.Archive.Audit.Objects.ObjectItem.BindEvent();
                                }
                            });
                        },
                        ObjectItem: {
                            BindEvent: function () {

                                $(".btn_ar_remove").unbind("click");
                                $(".btn_ar_remove").click(function () {
                                    c.Cases.Case.Archive.Audit.Objects.ObjectItem.Remove(this);
                                });
                            },
                            Clear: function (e) {
                                $(e).parents("tr").find(":input[type='text']").val('');
                                $(e).parents("tr").find(":input[type='hidden']").val('');
                                $(e).parents("tr").find(":input[type='checkbox']").attr("checked", false);
                            },
                            Remove: function (e) {
                                $(e).parents("tr").remove();
                            },
                            SyncRemark: function () {
                                var item_Remark = $($("#tblObjects tbody tr")[0]).find("#item_Remark");
                                $("#tblObjects tbody tr").each(function (i, e) {
                                    $(e).find("#item_Remark").val($(item_Remark).val());
                                })
                            },
                        },
                    },
                    Close: function () {
                        if ($('.slide-panel-container').length) {
                            $('.slide-panel-container').empty();
                            $('.slide-panel-container').removeClass('show-panel');
                        }
                    },
                }
            }
        },

        List: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseList/CaseSearchList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblCaseList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.CaseList, function (i, c) {

                            var deadlinestyle = '';
                            if (c.Basic.DeadlineLeftDays < 5) {
                                deadlinestyle = 'color:red';
                            }
                            else if (c.Basic.DeadlineLeftDays < 10) {
                                deadlinestyle = 'color:red';
                            }
                            else if (c.Basic.DeadlineLeftDays >= 10) {
                                deadlinestyle = 'color:green';
                            }

                            var courtName = '';
                            var judgeName = '';
                            var judgePhone = '';
                            var judgeEmail = '';
                            var judgeRemark = '';
                             
                            var courtRoomName  = '';
                            var lawfulDay = '';
                            var intance = ''

                            if (c.Basic.LastIntanceCourtName != null && c.Basic.LastIntanceCourtName != '') {
                                courtName = c.Basic.LastIntanceCourtName;
                                judgeName = c.Basic.LastIntanceJudgeName == null ? "无" : c.Basic.LastIntanceJudgeName;
                                judgePhone = c.Basic.LastIntanceJudgePhone == null ? "无" : c.Basic.LastIntanceJudgePhone;
                                judgeEmail = c.Basic.LastIntanceJudgeEmail == null ? "无" : c.Basic.LastIntanceJudgeEmail;
                                judgeRemark = c.Basic.LastIntanceJudgeRemark == null ? "无" : c.Basic.LastIntanceJudgeRemark;
                                courtRoomName =c.Basic.LastIntanceCourtRoom;
                                lawfulDay = c.Basic.LastIntanceLawfulDay == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.LastIntanceLawfulDay));
                                intance = "LastIntance";
                            }
                            else if (c.Basic.ExecutionIntanceCourtName != null && c.Basic.ExecutionIntanceCourtName != '') {
                                courtName = c.Basic.ExecutionIntanceCourtName;
                                judgeName = c.Basic.ExecutionIntanceJudgeName == null ? "无" : c.Basic.ExecutionIntanceJudgeName;
                                judgePhone = c.Basic.ExecutionIntanceJudgePhone == null ? "无" : c.Basic.ExecutionIntanceJudgePhone;
                                judgeEmail = c.Basic.ExecutionIntanceJudgeEmail == null ? "无" : c.Basic.ExecutionIntanceJudgeEmail;
                                judgeRemark = c.Basic.ExecutionIntanceJudgeRemark == null ? "无" : c.Basic.ExecutionIntanceJudgeRemark;
                                courtRoomName = c.Basic.ExecutionIntanceCourtRoom;
                                lawfulDay = c.Basic.ExecutionIntanceLawfulDay == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.ExecutionIntanceLawfulDay));
                                intance = "ExecutionIntance";
                            }
                            else if (c.Basic.SecondIntanceCourtName != null && c.Basic.SecondIntanceCourtName != '') {
                                courtName = c.Basic.SecondIntanceCourtName;
                                judgeName = c.Basic.SecondIntanceJudgeName == null ? "无" : c.Basic.SecondIntanceJudgeName;
                                judgePhone = c.Basic.SecondIntanceJudgePhone == null ? "无" : c.Basic.SecondIntanceJudgePhone;
                                judgeEmail = c.Basic.SecondIntanceJudgeEmail == null ? "无" : c.Basic.SecondIntanceJudgeEmail;
                                judgeRemark = c.Basic.SecondIntanceJudgeRemark == null ? "无" : c.Basic.SecondIntanceJudgeRemark;
                                courtRoomName =c.Basic.SecondIntanceCourtRoom;
                                lawfulDay = c.Basic.SecondIntanceLawfulDay == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.SecondIntanceLawfulDay));
                                intance = "SecondIntance";
                            }
                            else if (c.Basic.FirstIntanceCourtName != null && c.Basic.FirstIntanceCourtName != '') {
                                courtName = c.Basic.FirstIntanceCourtName;
                                judgeName = c.Basic.FirstIntanceJudgeName == null ? "无" : c.Basic.FirstIntanceJudgeName;
                                judgePhone = c.Basic.FirstIntanceJudgePhone == null ? "无" : c.Basic.FirstIntanceJudgePhone;
                                judgeEmail = c.Basic.FirstIntanceJudgeEmail == null ? "无" : c.Basic.FirstIntanceJudgeEmail;
                                judgeRemark = c.Basic.FirstIntanceJudgeRemark == null ? "无" : c.Basic.FirstIntanceJudgeRemark;
                                courtRoomName =c.Basic.FirstIntanceCourtRoom;
                                lawfulDay = c.Basic.FirstIntanceLawfulDay == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.FirstIntanceLawfulDay));
                                intance = "FirstIntance";
                            }

                            if (AP_PAGE_ID == "1001103040" || AP_PAGE_ID == "1001102040" || AP_PAGE_ID == "100110140") {
                                $("tbody", "#tblCaseList").addRow(
                                        "<input type='checkbox' id='chkCaseId' name='chkCaseId' class='' customerid=" + c.Basic.CustomerNo + " caseno='" + c.Basic.CaseNo + "'   value=" + c.Basic.CaseNo + ">",
                                        "<a href='javascript:void(0)' onclick='javascript:c.Cases.Case.View(\"" + c.Basic.CaseNo + "\")'>"+ c.Basic.CaseNo + "</a>",
                                        c.Basic.ConsultantTypeName,
                                        c.Basic.CustomerName,
                                        (c.Basic.ConsultantBeginDate == null ? "" : getDate(convertJsonDateToJSDate(c.Basic.ConsultantBeginDate))) + "  至  " + (c.Basic.ConsultantEndDate == null ? "" : getDate(convertJsonDateToJSDate(c.Basic.ConsultantEndDate))),
                                        c.Basic.CaseLawyerName,
                                        c.Basic.CaseAssistantName,
                                        c.Basic.BusinessOwnerName,
                                        "<div><span style='" + deadlinestyle + "'>" + c.Basic.DeadlineLeftDays + "</span></div>"
                                        );
                            }
                            else if (AP_PAGE_ID == "1001103020" || AP_PAGE_ID == "1001102020" || AP_PAGE_ID == "100110120"
                                  || AP_PAGE_ID == "1001103030" || AP_PAGE_ID == "1001102030" || AP_PAGE_ID == "1001101030" ) {
                                     $("tbody", "#tblCaseList").addRow(
                                        "<input type='checkbox' id='chkCaseId' name='chkCaseId' class='' customerid=" + c.Basic.CustomerNo + " caseno=" + c.Basic.CaseNo + "'   value=" + c.Basic.CaseNo + ">",
                                        "<a href='javascript:void(0)' onclick='javascript:c.Cases.Case.View(\"" + c.Basic.CaseNo + "\")'>" + c.Basic.CaseNo + "</a>",
                                        c.Basic.CauseName,
                                        c.Basic.AppellantNames,
                                        c.Basic.AppelleeNames,
                                        c.Basic.CasePhaseName,
                                        courtName,
                                        lawfulDay,
                                        c.Basic.CaseLawyerName,
                                        c.Basic.CaseAssistantName,
                                        c.Basic.BusinessOwnerName,
                                        "<div><span style='" + deadlinestyle + "'>" + c.Basic.DeadlineLeftDays + "</span></div>"
                                        );
                            }
                            else {
                                var investigationClueNo = '';
                                if (c.Basic.InvestigationClueNos != null && c.Basic.InvestigationClueNos != '')
                                {
                                    investigationClueNo = c.Basic.InvestigationClueNos.split(',')[0];
                                }
 
                                if ($("#SearchCondition_CasePhaseId").val() == "106011" || $("#SearchCondition_CasePhaseId").val() == "106017") {
                                    
                                    $("#divTaskHeader").hide();
                                    $("#divAppelleeHeader").hide();
                                    $("#divArchiveHeader").show();
 
                                    $("tbody", "#tblCaseList").addRow(
                                        "<input type='checkbox' id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' customerid=" + c.Basic.CustomerNo + " caseno='" + c.Basic.CaseNo + "'   value=" + c.Basic.CaseNo + ">",
                                        "<div><p><a href='javascript:void(0)' onclick='javascript:c.Cases.Case.View(\"" + c.Basic.CaseNo + "\")'>" + "案号:" + c.Basic.CaseNo + "</a></p><p><span>" + "阶段:" + c.Basic.CasePhaseName + "</span></p></div>",
                                        "<div><p>" + "原告:" + c.Basic.AppellantNames + "</a></p><p><span style='white-space: nowrap;'>" + "被告:" + c.Basic.AppelleeNames + "</span></p></div>",
                                        "<div><p>" + "法院:" + "<a data-toggle='tooltip'  onclick='javascript:c.Cases.Case.Court.CourtEdit(\"" + intance + "\"," + c.Basic.CaseId + ",\"" + c.Basic.CaseNo + "\");'  data-container='body' data-placement='bottom'  data-original-title='法官:" + judgeName + "(手机:" + judgePhone + ",Email:" + judgeEmail + ",备注:" + judgeRemark + ")" + "'>" + courtName + "</a></p><p>" + " 案号:" + c.Basic.OfficialNo + "</p></div>",
                                        "<div><p>" + "律师:" + c.Basic.CaseLawyerName + "</a></p><p><span>" + "助理:" + c.Basic.CaseAssistantName + "</span></p></div>",
                                        "<div><p><a onclick=\"javascript:investigation.InvestigationClue.View('" + investigationClueNo + "');\"><span>" + "调查员:" + c.Basic.InvestigatorName + "</span></a></p>" +
                                        "<p><span>" + "公证书:" + c.Basic.NotarialNos + "</span></p></div>",
                                        "<div><p>提交人:" + c.Basic.ToAuditApplicantName + "</a></p>" +
                                        "<p><span>" + "备注:" + c.Basic.ToAuditRemark + "</span></p></div>",
                                        "<div><p><span>" + "状态:" + c.Basic.ArchiveStatusName + "</span></p><p>" + "时间:" + (c.Basic.ToAuditTime == null ? "" : getDate(convertJsonDateToJSDate(c.Basic.ToAuditTime))) + "</a></p></div>"
                                        );
                                }
                                else if ($("#SearchCondition_CasePhaseId").val() == "106012" || $("#SearchCondition_CasePhaseId").val() == "106018") {

                                    $("#divTaskHeader").hide();
                                    $("#divAppelleeHeader").hide();
                                    $("#divArchiveHeader").show();

                                    $("tbody", "#tblCaseList").addRow(
                                        "<input type='checkbox' id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' customerid=" + c.Basic.CustomerNo + " caseno='" + c.Basic.CaseNo + "'   value=" + c.Basic.CaseNo + ">",
                                        "<div><p><a href='javascript:void(0)' onclick='javascript:c.Cases.Case.View(\"" + c.Basic.CaseNo + "\")'>" + "案号:" + c.Basic.CaseNo + "</a></p><p><span>" + "阶段:" + c.Basic.CasePhaseName + "</span></p></div>",
                                        "<div><p>" + "原告:" + c.Basic.AppellantNames + "</a></p><p><span style='white-space: nowrap;'>" + "被告:" + c.Basic.AppelleeNames + "</span></p></div>",
                                        "<div><p>" + "法院:" + "<a data-toggle='tooltip'  onclick='javascript:c.Cases.Case.Court.CourtEdit(\"" + intance + "\"," + c.Basic.CaseId + ",\"" + c.Basic.CaseNo + "\");'  data-container='body' data-placement='bottom'  data-original-title='法官:" + judgeName + "(手机:" + judgePhone + ",Email:" + judgeEmail + ",备注:" + judgeRemark + ")" + "'>" + courtName + "</a></p><p>" + " 案号:" + c.Basic.OfficialNo + "</p></div>",
                                        "<div><p>" + "律师:" + c.Basic.CaseLawyerName + "</a></p><p><span>" + "助理:" + c.Basic.CaseAssistantName + "</span></p></div>",
                                        "<div><p><a onclick=\"javascript:investigation.InvestigationClue.View('" + investigationClueNo + "');\"><span>" + "调查员:" + c.Basic.InvestigatorName + "</span></a></p>" +
                                        "<p><span>" + "公证书:" + c.Basic.NotarialNos + "</span></p></div>",
                                        "<div><p>审核人:" + c.Basic.AuditorName + "</a></p>" +
                                        "<p><span>" + "审核备注:" + c.Basic.AuditedRemark + "</span></p></div>",
                                        "<div><p><span>" + "状态:" + c.Basic.ArchiveStatusName + "</span></p><p>" + "时间:" + (c.Basic.AuditedTime == null ? "" : getDate(convertJsonDateToJSDate(c.Basic.AuditedTime))) + "</a></p></div>"
                                        );
                                }
                                else if ($("#SearchCondition_CasePhaseId").val() == "106014" || $("#SearchCondition_CasePhaseId").val() == "106019") {

                                    $("#divTaskHeader").hide();
                                    $("#divAppelleeHeader").hide();
                                    $("#divArchiveHeader").show();

                                    $("tbody", "#tblCaseList").addRow(
                                        "<input type='checkbox' id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' customerid=" + c.Basic.CustomerNo + " caseno='" + c.Basic.CaseNo + "'   value=" + c.Basic.CaseNo + ">",
                                        "<div><p><a href='javascript:void(0)' onclick='javascript:c.Cases.Case.View(\"" + c.Basic.CaseNo + "\")'>" + "案号:" + c.Basic.CaseNo + "</a></p><p><span>" + "阶段:" + c.Basic.CasePhaseName + "</span></p></div>",
                                        "<div><p>" + "原告:" + c.Basic.AppellantNames + "</a></p><p><span style='white-space: nowrap;'>" + "被告:" + c.Basic.AppelleeNames + "</span></p></div>",
                                        "<div><p>" + "法院:" + "<a data-toggle='tooltip'  onclick='javascript:c.Cases.Case.Court.CourtEdit(\"" + intance + "\"," + c.Basic.CaseId + ",\"" + c.Basic.CaseNo + "\");'  data-container='body' data-placement='bottom'  data-original-title='法官:" + judgeName + "(手机:" + judgePhone + ",Email:" + judgeEmail + ",备注:" + judgeRemark + ")" + "'>" + courtName + "</a></p><p>" + " 案号:" + c.Basic.OfficialNo + "</p></div>",
                                        "<div><p>" + "律师:" + c.Basic.CaseLawyerName + "</a></p><p><span>" + "助理:" + c.Basic.CaseAssistantName + "</span></p></div>",
                                        "<div><p><a onclick=\"javascript:investigation.InvestigationClue.View('" + investigationClueNo + "');\"><span>" + "调查员:" + c.Basic.InvestigatorName + "</span></a></p>" +
                                        "<p><span>" + "公证书:" + c.Basic.NotarialNos + "</span></p></div>",
                                        "<div><p>审核人:" + c.Basic.AuditorName + "</a></p>" +
                                        "<p><span>" + "审核备注:" + c.Basic.AuditedRemark + "</span></p></div>",
                                        "<div><p><span>" + "状态:" + c.Basic.ArchiveStatusName + "</span></p><p>" + "时间:" + (c.Basic.AuditedTime == null ? "" : getDate(convertJsonDateToJSDate(c.Basic.AuditedTime))) + "</a></p></div>"
                                        );
                                }
                                else if ($("#SearchCondition_CasePhaseId").val() == "101001" || $("#SearchCondition_CasePhaseId").val() == "101010") {

                                    $("#divTaskHeader").hide();
                                    $("#divAppelleeHeader").show();
                                    $("#divArchiveHeader").hide();

                                    if (c.FirtstInvestigationClue != null) {

                                        if (c.FirtstInvestigationClue.Basic.BusinessType == "E_EC" || c.FirtstInvestigationClue.Basic.BusinessType == "E_WL") {
                                            $("tbody", "#tblCaseList").addRow(
                                                "<input type='checkbox' id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' customerid=" + c.Basic.CustomerNo + " caseno='" + c.Basic.CaseNo + "'   value=" + c.Basic.CaseNo + ">",
                                                "<div><p><a href='javascript:void(0)' onclick='javascript:c.Cases.Case.View(\"" + c.Basic.CaseNo + "\")'>" + "案号:" + c.Basic.CaseNo + "</a></p><p><span>" + "阶段:" + c.Basic.CasePhaseName + "</span></p></div>",
                                                "<div><p>" + "原告:" + c.Basic.AppellantNames + "</a></p><p><span style='white-space: nowrap;'>" + "被告:" + c.Basic.AppelleeNames + "</span></p></div>",
                                                "<div><p>" + "法院:" + "<a data-toggle='tooltip' data-container='body' data-placement='bottom'  data-original-title='法官:" + judgeName + "(手机:" + judgePhone + ",Email:" + judgeEmail + ",备注:" + judgeRemark + ")" + "'>" + courtName + "</a></p><p>" + " 案号:" + c.Basic.OfficialNo + "</p></div>",
                                                "<div><p>" + "律师:" + c.Basic.CaseLawyerName + "</a></p><p><span>" + "助理:" + c.Basic.CaseAssistantName + "</span></p></div>",
                                                "<div><p><a onclick=\"javascript:investigation.InvestigationClue.View('" + investigationClueNo + "');\"><span>" + "调查员:" + c.Basic.InvestigatorName + "</span></a></p>" +
                                                "<p><span>" + "公证书:" + c.Basic.NotarialNos + "</span></p></div>",
                                                "<div><p><span>店铺名称:" + c.FirtstInvestigationClue.Basic.StoreName + "</span></p><p>" + "店铺地址:" + c.FirtstInvestigationClue.Basic.StoreUrl + "</a></p></div>",
                                                "<div><p><span>侵权方式:" + c.FirtstInvestigationClue.Basic.BusinessTypeZh + "</span></p><p><span>销售渠道:" + c.FirtstInvestigationClue.Basic.ChannelTypeZh + "</span></p></div>"
                                            );
                                        }
                                        else {
                                                $("tbody", "#tblCaseList").addRow(
                                                    "<input type='checkbox' id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' customerid=" + c.Basic.CustomerNo + " caseno='" + c.Basic.CaseNo + "'   value=" + c.Basic.CaseNo + ">",
                                                    "<div><p><a href='javascript:void(0)' onclick='javascript:c.Cases.Case.View(\"" + c.Basic.CaseNo + "\")'>" + "案号:" + c.Basic.CaseNo + "</a></p><p><span>" + "阶段:" + c.Basic.CasePhaseName + "</span></p></div>",
                                                    "<div><p>" + "原告:" + c.Basic.AppellantNames + "</a></p><p><span style='white-space: nowrap;'>" + "被告:" + c.Basic.AppelleeNames + "</span></p></div>",
                                                    "<div><p>" + "法院:" + "<a data-toggle='tooltip' onclick='javascript:c.Cases.Case.Court.CourtEdit(\"" + intance + "\"," + c.Basic.CaseId + ",\"" + c.Basic.CaseNo + "\");' data-container='body' data-placement='bottom'  data-original-title='法官:" + judgeName + "(手机:" + judgePhone + ",Email:" + judgeEmail + ",备注:" + judgeRemark + ")" + "'>" + courtName + "</a></p><p>" + " 案号:" + c.Basic.OfficialNo + "</p></div>",
                                                    "<div><p>" + "律师:" + c.Basic.CaseLawyerName + "</a></p><p><span>" + "助理:" + c.Basic.CaseAssistantName + "</span></p></div>",
                                                    "<div><p><a onclick=\"javascript:investigation.InvestigationClue.View('" + investigationClueNo + "');\"><span>" + "调查员:" + c.Basic.InvestigatorName + "</span></a></p>" +
                                                    "<p><span>" + "公证书:" + c.Basic.NotarialNos + "</span></p></div>",
                                                    "<div><p><span>店铺名称:" + c.FirtstInvestigationClue.Basic.StoreName + "</span></p><p>" + "店铺地址:" + c.FirtstInvestigationClue.Basic.Address + "</a></p></div>",
                                                    "<div><p><span>侵权方式:" + c.FirtstInvestigationClue.Basic.BusinessTypeZh + "</span></p><p><span>侵权区域:" + c.FirtstInvestigationClue.Basic.ProvinceZh + c.FirtstInvestigationClue.Basic.CityZh + c.FirtstInvestigationClue.Basic.CityZh + c.FirtstInvestigationClue.Basic.DistrictZh + "</span></p></div>"
                                                );
                                        }
          
                                    }
                                    else {
                                        $("tbody", "#tblCaseList").addRow(
                                           "<input type='checkbox' id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' customerid=" + c.Basic.CustomerNo + " caseno=" + c.Basic.CaseNo + "'   value=" + c.Basic.CaseNo + ">",
                                           "<div><p><a href='javascript:void(0)' onclick='javascript:c.Cases.Case.View(\"" + c.Basic.CaseNo + "\")'>" + "案号:" + c.Basic.CaseNo + "</a></p><p><span>" + "阶段:" + c.Basic.CasePhaseName + "</span></p></div>",
                                           "<div><p>" + "原告:" + c.Basic.AppellantNames + "</a></p><p><span style='white-space: nowrap;'>" + "被告:" + c.Basic.AppelleeNames + "</span></p></div>",
                                               "<div><p>" + "法院:" + "<a data-toggle='tooltip'  onclick='javascript:c.Cases.Case.Court.CourtEdit(\"" + intance + "\"," + c.Basic.CaseId + ",\"" + c.Basic.CaseNo + "\");'  data-container='body' data-placement='bottom'  data-original-title='法官:" + judgeName + "(手机:" + judgePhone + ",Email:" + judgeEmail + ",备注:" + judgeRemark + ")" + "'>" + courtName + "</a></p><p>" + "案号:" + c.Basic.OfficialNo + "</p></div>",
                                           "<div><p>" + "律师:" + c.Basic.CaseLawyerName + "</a></p><p><span>" + "助理:" + c.Basic.CaseAssistantName + "</span></p></div>",
                                          "<div><p><a onclick=\"javascript:investigation.InvestigationClue.View('" + investigationClueNo + "');\"><span>" + "调查员:" + c.Basic.InvestigatorName + "</span></a></p>" +
                                                    "<p><span>" + "公证书:" + c.Basic.NotarialNos + "</span></p></div>",
                                           "<div><p>无</p></div>",
                                           "<div></div>"
                                           );
                                    }

                                }
                                else
                                {
                                    $("#divTaskHeader").show();
                                    $("#divAppelleeHeader").hide();
                                    $("#divArchiveHeader").hide();

                                    if (c.NewestTask != null) {
                                        $("tbody", "#tblCaseList").addRow(
                                            "<input type='checkbox' id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' customerid=" + c.Basic.CustomerNo + " caseno='" + c.Basic.CaseNo + "'   value=" + c.Basic.CaseNo + ">",
                                            "<div><p><a href='javascript:void(0)' onclick='javascript:c.Cases.Case.View(\"" + c.Basic.CaseNo + "\")'>" + "案号:" + c.Basic.CaseNo + "</a></p><p><span>" + "阶段:" + c.Basic.CasePhaseName + "</span></p></div>",
                                            "<div><p>" + "原告:" + c.Basic.AppellantNames + "</a></p><p><span style='white-space: nowrap;'>" + "被告:" + c.Basic.AppelleeNames + "</span></p></div>",
                                            "<div><p>" + "法院:" + "<a data-toggle='tooltip'  onclick='javascript:c.Cases.Case.Court.CourtEdit(\"" + intance + "\"," + c.Basic.CaseId + ",\"" + c.Basic.CaseNo + "\");'  data-container='body' data-placement='bottom'  data-original-title='法官:" + judgeName + "(手机:" + judgePhone + ",Email:" + judgeEmail + ",备注:" + judgeRemark + ")" + "'>" + courtName + "</a></p><p>" + " 案号:" + c.Basic.OfficialNo + "</p></div>",
                                            "<div><p>" + "律师:" + c.Basic.CaseLawyerName + "</a></p><p><span>" + "助理:" + c.Basic.CaseAssistantName + "</span></p></div>",
                                            "<div><p><a onclick=\"javascript:investigation.InvestigationClue.View('" + investigationClueNo + "');\"><span>" + "调查员:" + c.Basic.InvestigatorName + "</span></a></p>" +
                                            "<p><span>" + "公证书:" + c.Basic.NotarialNos + "</span></p></div>",
                                            "<div><p><a onclick='javascript:task.Tasks.Task.ViewTask(this," + c.NewestTask.TaskId + ");'>" + "名称:" + (c.NewestTask == null ? "" : c.NewestTask.TaskTitle) + "</a></p>" +
                                            "<p><span>" + "内容:" + (c.NewestTask == null ? "" : c.NewestTask.TaskContent) + "</span></p></div>",
                                            "<div><p><span>" + "处理人:" + (c.NewestTask == null ? "" : c.NewestTask.OfficerName) + "</span></p><p>" + "时间:" + (c.NewestTask == null ? "" : getDate(convertJsonDateToJSDate(c.NewestTask.TaskEndTime))) + "</a></p></div>"
                                            );
                                    }
                                    else {
                                        $("tbody", "#tblCaseList").addRow(
                                            "<input type='checkbox' id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' customerid=" + c.Basic.CustomerNo + " caseno=" + c.Basic.CaseNo + "'   value=" + c.Basic.CaseNo + ">",
                                            "<div><p><a href='javascript:void(0)' onclick='javascript:c.Cases.Case.View(\"" + c.Basic.CaseNo + "\")'>" + "案号:" + c.Basic.CaseNo + "</a></p><p><span>" + "阶段:" + c.Basic.CasePhaseName + "</span></p></div>",
                                            "<div><p>" + "原告:" + c.Basic.AppellantNames + "</a></p><p><span style='white-space: nowrap;'>" + "被告:" + c.Basic.AppelleeNames + "</span></p></div>",
                                                "<div><p>" + "法院:" + "<a data-toggle='tooltip'  onclick='javascript:c.Cases.Case.Court.CourtEdit(\"" + intance + "\"," + c.Basic.CaseId + ",\"" + c.Basic.CaseNo + "\");'  data-container='body' data-placement='bottom'  data-original-title='法官:" + judgeName + "(手机:" + judgePhone + ",Email:" + judgeEmail + ",备注:" + judgeRemark + ")" + "'>" + courtName + "</a></p><p>" + "案号:" + c.Basic.OfficialNo + "</p></div>",
                                            "<div><p>" + "律师:" + c.Basic.CaseLawyerName + "</a></p><p><span>" + "助理:" + c.Basic.CaseAssistantName + "</span></p></div>",
                                           "<div><p><a onclick=\"javascript:investigation.InvestigationClue.View('" + investigationClueNo + "');\"><span>" + "调查员:" + c.Basic.InvestigatorName + "</span></a></p>" +
                                            "<p><span>" + "公证书:" + c.Basic.NotarialNos + "</span></p></div>",
                                            "<div><p>无</p></div>",
                                            "<div></div>"
                                            );
                                    }
                                }

                            }
                        });

                        if (response.Data.CaseList.length > 5) {
                            $(".divdropdown").removeClass("dropdown");
                            $(".divdropdown").addClass("dropup");
                        }
                        else {
                            $(".divdropdown").removeClass("dropup");
                            $(".divdropdown").addClass("dropdown");
                        }
                       
                        $("#divCaseList").show();
                        $("tfoot", "#tblCaseList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.Caselist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: c.Cases.List,
                            callBackArgs: null
                        });

                        $("[data-toggle='tooltip']").tooltip();
                        //caseQuery.BindMenu();

                    } else {
                        $("#divCaseList").hide();
                        $("tfoot", "#tblCaseList").hide();
                        $(".simple-grid-none-data-wrap").show();
                    }
                }
            });
        },
        
        ListWebUploader: {
            Setting: function ()
            {
                var _queue = [];
                var _sucess_queue = [];
                var uploader = WebUploader.create({

                    pick: {
                        id: '.filePicker',
                    },
                    // 选完文件后，是否自动上传。
                    webkitdirectory: "webkitdirectory",
                    auto: true,
                    // swf文件路径
                    swf: '~/Resource/webuploader/Uploader.swf',
                    // 文件接收服务端。
                    server: AP_ROOT + AP_PAGE_ID + "/Legal/CaseFile/MultiCaseFileWebUpload",
                    // 选择文件的按钮。可选。
                    // 内部根据当前运行是创建，可能是input元素，也可能是flash.
                    //pick: '#picker',
                    disableGlobalDnd: true,
                    dnd: '#dropbox',
                    //paste: '#dropbox',

                    // 不压缩image, 默认如果是jpeg，文件上传前会压缩一把再上传！
                    resize: false,
                    duplicate: true
                });

                // 拖拽时不接受 js, txt 文件。
                uploader.on('dndAccept', function (items) {
                    
                    var denied = false,
                     len = items.length,
                     i = 0,
                     // 修改js类型
                    unAllowed = 'text/plain;application/javascript ';
                    for (; i < len; i++) {
                        // 如果在列表里面
                        if (~unAllowed.indexOf(items[i].type)) {
                            denied = true;
                            break;
                        }
                    }

                    
                    if (denied) return;

                    $("tbody", "#tblWebUploadList").empty();
                    $("#webuploaderlist").addClass("show-panel");
                });
                uploader.on('ready', function () {
                    window.uploader = uploader;
                });
                // 当有文件被添加进队列的时候
                uploader.on('fileQueued', function (file) {
                    var itemTemplate = "";
                    var fileSize = parseInt(file.size / 1024);
                    if (fileSize >= 1024)
                        fileSize = parseInt(fileSize / 1024) + "MB"
                    else
                        fileSize = parseInt(fileSize) + "KB"

                 
                    _queue.push(file);

                    itemTemplate = '<tr class="file-list" >'
                                 + '    <td style="text-align: left; ">' + file.name + '</td>'
                                 + '    <td style="text-align: left;  white-space: nowrap">' + fileSize + '</td>'
                                 + '    <td style="text-align: left; ">案件文档</td>'
                                 + '    <td id=' + file.id + ' style="text-align: left; ">'
                                 + '        <span  class="state">等待上传... </span>'
                                + '      </td>'
                                + '</tr>' + itemTemplate;
                    $("tbody", "#tblWebUploadList").append(itemTemplate);

                });

                uploader.on('beforeFileQueued', function (file) {
                    //_queue = [];
                    //_sucess_queue = [];
                    var chkCaseNos = $.checkbox.vals("chkCaseId");
                    if (chkCaseNos.length == 0) {
                        $.showTips("请选择案件再上传文件.", 0, 3);
                        return false;
                    }
                });
                //上传之前获取 文件夹相对路径，

                uploader.on('uploadBeforeSend', function (object, data, headers) {
                    var chkCaseNos = $.checkbox.vals("chkCaseId");
                    data.relativepath = object.file.relativepath;
                    data.caseNos = chkCaseNos;
                    data.caseFileTypeId = 7; //当前选中的Id

                });

                // 文件上传过程中创建进度条实时显示。
                uploader.on('uploadProgress', function (file, percentage) {
                    var $li = $('#' + file.id),
                        $percent = $li.find('.progress .progress-bar');
                    // 避免重复创建
                    if (!$percent.length) {
                        $percent = $('<div class="progress progress-striped active" style="margin-bottom: 0px;">' +
                          '<div class="progress-bar"  role="progressbar" style="width: 0%;">' +
                          '</div>' +
                        '</div>').appendTo($li).find('.progress-bar');
                    }
                    $li.find('span.state').text('上传中');
                    $percent.css('width', percentage * 100 + '%');
                });

                //文件成功、失败处理
                uploader.on('uploadSuccess', function (file) {
                    
                    $('#' + file.id).find('span.state').text('已上传');
                });

                //文件成功、失败处理
                uploader.on('uploadFinished', function () {
                    $.showTips("成功上传 " + _queue.length + " 个文件.", 0, 3);
                });

                uploader.on('uploadError', function (file) {
                    $('#' + file.id).find('span.state').text('上传出错');
                });

                uploader.on('uploadComplete', function (file) {
                    $('#' + file.id).find('.progress').fadeOut();
                });
            }
        },

        ScheduleList: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseList/CaseSearchList", function (response) {
                if (response.IsSuccess) {
                    $("tbody", "#tblCaseList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.CaseList, function (i, c) {

                            var deadlinestyle = '';
                            if (c.Basic.DeadlineLeftDays < 5) {
                                deadlinestyle = 'color:red';
                            }
                            else if (c.Basic.DeadlineLeftDays < 10) {
                                deadlinestyle = 'color:red';
                            }
                            else if (c.Basic.DeadlineLeftDays >= 10) {
                                deadlinestyle = 'color:green';
                            }

                            var courtName = '';
                            var courtRoom = '';
                            var lawfulDay = '';

                            if (c.Basic.LastIntanceCourtName != null && c.Basic.LastIntanceCourtName != '') {
                                courtName = c.Basic.LastIntanceCourtName;
                                courtRoom = c.Basic.LastIntanceCourtRoom;
                                lawfulDay = c.Basic.LastIntanceLawfulDay == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.LastIntanceLawfulDay));
                            }
                            else if (c.Basic.SecondIntanceCourtName != null && c.Basic.SecondIntanceCourtName != '') {
                                courtName = c.Basic.SecondIntanceCourtName;
                                courtRoom = c.Basic.SecondIntanceCourtRoom;
                                lawfulDay = c.Basic.SecondIntanceLawfulDay == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.SecondIntanceLawfulDay));
                            }
                            else if (c.Basic.FirstIntanceCourtName != null && c.Basic.FirstIntanceCourtName != '') {
                                courtName = c.Basic.FirstIntanceCourtName;
                                courtRoom = c.Basic.FirstIntanceCourtRoom;
                                lawfulDay = c.Basic.FirstIntanceLawfulDay == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.FirstIntanceLawfulDay));
                            }

                            $("tbody", "#tblCaseList").addRow(
                                "<input type='checkbox' id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' customerid=" + c.Basic.CustomerNo + " caseno='" + c.Basic.CaseNo + "'   value=" + c.Basic.CaseNo + ">",
                                c.Basic.LawfulDayOfWeek,
                                c.Basic.LawfulDay == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.LawfulDay)),
                                c.Basic.LawfulDayTime,
                               "<a href='javascript:void(0)' onclick='javascript:c.Cases.Case.View(\"" + c.Basic.CaseNo + "\")'>" + c.Basic.CaseNo + "</a>",
                                c.Basic.CasePhaseName,
                                courtName,
                                courtRoom,
                                 c.Basic.AppellantNames,
                                c.Basic.AppelleeNames,
                                c.Basic.CourtLawyerName,
                                c.Basic.CaseLawyerName,
                                c.Basic.CaseAssistantName
                                );
                        });


                        if (response.Data.CaseList.length > 10) {
                            $(".divdropdown").removeClass("dropdown");
                            $(".divdropdown").addClass("dropup");
                        }
                        else {
                            $(".divdropdown").removeClass("dropup");
                            $(".divdropdown").addClass("dropdown");
                        }

                        $("tfoot", "#tblCaseList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.Caselist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: c.Cases.ScheduleList,
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

        PendingList: function () {
            
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseList/CaseSearchList", function (response) {

                if (response.IsSuccess) {
                    $("tbody", "#tblCaseList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.CaseList, function (i, c) {

                            var deadlinestyle = '';
                            if (c.Basic.DeadlineLeftDays < 5) {
                                deadlinestyle = 'color:red';
                            }
                            else if (c.Basic.DeadlineLeftDays < 10) {
                                deadlinestyle = 'color:red';
                            }
                            else if (c.Basic.DeadlineLeftDays >= 10) {
                                deadlinestyle = 'color:green';
                            }

                            var courtName = '';
                            var courtRoom = '';
                            var lawfulDay = '';

                            if (c.Basic.LastIntanceCourtName != null && c.Basic.LastIntanceCourtName != '') {
                                courtName = c.Basic.LastIntanceCourtName;
                                courtRoom = c.Basic.LastIntanceCourtRoom;
                                lawfulDay = c.Basic.LastIntanceLawfulDay == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.LastIntanceLawfulDay));
                            }
                            else if (c.Basic.SecondIntanceCourtName != null && c.Basic.SecondIntanceCourtName != '') {
                                courtName = c.Basic.SecondIntanceCourtName;
                                courtRoom = c.Basic.SecondIntanceCourtRoom;
                                lawfulDay = c.Basic.SecondIntanceLawfulDay == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.SecondIntanceLawfulDay));
                            }
                            else if (c.Basic.FirstIntanceCourtName != null && c.Basic.FirstIntanceCourtName != '') {
                                courtName = c.Basic.FirstIntanceCourtName;
                                courtRoom = c.Basic.FirstIntanceCourtRoom;
                                lawfulDay = c.Basic.FirstIntanceLawfulDay == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.FirstIntanceLawfulDay));
                            }

                            $("tbody", "#tblCaseList").addRow(
                                "<input type='checkbox' id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' customerid=" + c.Basic.CustomerNo + " caseno='" + c.Basic.CaseNo + "'   value=" + c.Basic.CaseNo + ">",
                                c.Basic.ToAuditApplicantName,
                                c.Basic.ToAuditTime == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.ToAuditTime)),
                                c.Basic.ToAuditRemark,
                               "<a href='javascript:void(0)' onclick='javascript:c.Cases.Case.View(\"" + c.Basic.CaseNo + "\")'>" + c.Basic.CaseNo + "</a>",
                                c.Basic.CasePhaseName,
                                courtName,
                                c.Basic.AppellantNames,
                                c.Basic.AppelleeNames,
                                c.Basic.CourtLawyerName,
                                c.Basic.CaseLawyerName,
                                c.Basic.CaseAssistantName
                                );
                        });


                        if (response.Data.CaseList.length > 10) {
                            $(".divdropdown").removeClass("dropdown");
                            $(".divdropdown").addClass("dropup");
                        }
                        else {
                            $(".divdropdown").removeClass("dropup");
                            $(".divdropdown").addClass("dropdown");
                        }

                        $("tfoot", "#tblCaseList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.Caselist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: c.Cases.PendingList,
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

        ApprovedList: function () {
            
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseList/CaseSearchList", function (response) {

                if (response.IsSuccess) {
                    $("tbody", "#tblCaseList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.CaseList, function (i, c) {

                            var deadlinestyle = '';
                            if (c.Basic.DeadlineLeftDays < 5) {
                                deadlinestyle = 'color:red';
                            }
                            else if (c.Basic.DeadlineLeftDays < 10) {
                                deadlinestyle = 'color:red';
                            }
                            else if (c.Basic.DeadlineLeftDays >= 10) {
                                deadlinestyle = 'color:green';
                            }

                            var courtName = '';
                            var courtRoom = '';
                            var lawfulDay = '';

                            if (c.Basic.LastIntanceCourtName != null && c.Basic.LastIntanceCourtName != '') {
                                courtName = c.Basic.LastIntanceCourtName;
                                courtRoom = c.Basic.LastIntanceCourtRoom;
                                lawfulDay = c.Basic.LastIntanceLawfulDay == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.LastIntanceLawfulDay));
                            }
                            else if (c.Basic.SecondIntanceCourtName != null && c.Basic.SecondIntanceCourtName != '') {
                                courtName = c.Basic.SecondIntanceCourtName;
                                courtRoom = c.Basic.SecondIntanceCourtRoom;
                                lawfulDay = c.Basic.SecondIntanceLawfulDay == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.SecondIntanceLawfulDay));
                            }
                            else if (c.Basic.FirstIntanceCourtName != null && c.Basic.FirstIntanceCourtName != '') {
                                courtName = c.Basic.FirstIntanceCourtName;
                                courtRoom = c.Basic.FirstIntanceCourtRoom;
                                lawfulDay = c.Basic.FirstIntanceLawfulDay == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.FirstIntanceLawfulDay));
                            }

                            $("tbody", "#tblCaseList").addRow(
                                "<input type='checkbox' id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' customerid=" + c.Basic.CustomerNo + " caseno='" + c.Basic.CaseNo + "'   value=" + c.Basic.CaseNo + ">",
                                c.Basic.ToAuditApplicantName,
                                c.Basic.ToAuditTime == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.ToAuditTime)),
                                c.Basic.AuditorName,
                                c.Basic.AuditedTime == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.AuditedTime)),
                                "<a href='javascript:void(0)' onclick='javascript:c.Cases.Case.View(\"" + c.Basic.CaseNo + "\")'>" + c.Basic.CaseNo + "</a>",

                                c.Basic.CasePhaseName,
                                courtName,
                                c.Basic.AppellantNames,
                                c.Basic.AppelleeNames,
                                c.Basic.CourtLawyerName,
                                c.Basic.CaseLawyerName,
                                c.Basic.CaseAssistantName
                                );

                            $("tbody", "#tblCaseList").append("<tr style='background-color: #99CC66'><td></td>"
                            + "<td>审核备注:</td><td style='text-align: left' colspan='3'>" + c.Basic.AuditedRemark + "</td>"
                            + "<td>提交备注:</td><td style='text-align: left' colspan='7'>" + c.Basic.ToAuditRemark + "</td>"
                            + "</tr> ");
                        });




                        if (response.Data.CaseList.length > 10) {
                            $(".divdropdown").removeClass("dropdown");
                            $(".divdropdown").addClass("dropup");
                        }
                        else {
                            $(".divdropdown").removeClass("dropup");
                            $(".divdropdown").addClass("dropdown");
                        }

                        $("tfoot", "#tblCaseList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.Caselist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: c.Cases.ApprovedList,
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

        RejectedList: function () {
            
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseList/CaseSearchList", function (response) {

                if (response.IsSuccess) {
                    $("tbody", "#tblCaseList").clearRow();
                    if (response.Data.TotalItemCount > 0) {
                        $(".info_inall.layoutfix").show();
                        $.each(response.Data.CaseList, function (i, c) {

                            var deadlinestyle = '';
                            if (c.Basic.DeadlineLeftDays < 5) {
                                deadlinestyle = 'color:red';
                            }
                            else if (c.Basic.DeadlineLeftDays < 10) {
                                deadlinestyle = 'color:red';
                            }
                            else if (c.Basic.DeadlineLeftDays >= 10) {
                                deadlinestyle = 'color:green';
                            }

                            var courtName = '';
                            var courtRoom = '';
                            var lawfulDay = '';

                            if (c.Basic.LastIntanceCourtName != null && c.Basic.LastIntanceCourtName != '') {
                                courtName = c.Basic.LastIntanceCourtName;
                                courtRoom = c.Basic.LastIntanceCourtRoom;
                                lawfulDay = c.Basic.LastIntanceLawfulDay == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.LastIntanceLawfulDay));
                            }
                            else if (c.Basic.SecondIntanceCourtName != null && c.Basic.SecondIntanceCourtName != '') {
                                courtName = c.Basic.SecondIntanceCourtName;
                                courtRoom = c.Basic.SecondIntanceCourtRoom;
                                lawfulDay = c.Basic.SecondIntanceLawfulDay == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.SecondIntanceLawfulDay));
                            }
                            else if (c.Basic.FirstIntanceCourtName != null && c.Basic.FirstIntanceCourtName != '') {
                                courtName = c.Basic.FirstIntanceCourtName;
                                courtRoom = c.Basic.FirstIntanceCourtRoom;
                                lawfulDay = c.Basic.FirstIntanceLawfulDay == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.FirstIntanceLawfulDay));
                            }
                            
                            $("tbody", "#tblCaseList").addRow(
                                "<input type='checkbox' id='chkCaseId' name='chkCaseId' class='ng-pristine ng-valid' customerid=" + c.Basic.CustomerNo + " caseno='" + c.Basic.CaseNo + "'   value=" + c.Basic.CaseNo + ">",
                                c.Basic.ToAuditApplicantName,
                                c.Basic.ToAuditTime == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.ToAuditTime)),
                                c.Basic.AuditorName,
                                c.Basic.AuditedTime == null ? '' : getDate(convertJsonDateToJSDate(c.Basic.AuditedTime)),
                               "<a href='javascript:void(0)' onclick='javascript:c.Cases.Case.View(\"" + c.Basic.CaseNo + "\")'>" + c.Basic.CaseNo + "</a>",

                                c.Basic.CasePhaseName,
                                courtName,
                                c.Basic.AppellantNames,
                                c.Basic.AppelleeNames,
                                c.Basic.CourtLawyerName,
                                c.Basic.CaseLawyerName,
                                c.Basic.CaseAssistantName
                                );


                            $("tbody", "#tblCaseList").append("<tr style='background-color: #f39c12'><td></td>"
                            + "<td>审核备注:</td><td style='text-align: left' colspan='3'>" + c.Basic.AuditedRemark + "</td>"
                            + "<td>提交备注:</td><td style='text-align: left' colspan='7'>" + c.Basic.ToAuditRemark + "</td>"
                            + "</tr> ");
                        });


                        if (response.Data.CaseList.length > 10) {
                            $(".divdropdown").removeClass("dropdown");
                            $(".divdropdown").addClass("dropup");
                        }
                        else {
                            $(".divdropdown").removeClass("dropup");
                            $(".divdropdown").addClass("dropdown");
                        }

                        $("tfoot", "#tblCaseList").show();
                        $(".simple-grid-none-data-wrap").hide();

                        $(".pull-right.page-box.Caselist").cPaging({
                            totalCount: response.Data.TotalItemCount,
                            pageNo: response.Data.PageNo,
                            pageSize: response.Data.PageSize,
                            callBack: c.Cases.RejectedList,
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

        ExportSelectedToExcel: function () {
            var caseNos = [];
            $("input[name='chkCaseId']:checked").each(
                function (i) { caseNos[i] = $(this).val(); }
            );
            if (caseNos.length < 1) {
                $.showModalMessageBox("请选择需要导出的案件.");
                return false;
            }
            var data = {
                caseNos: caseNos,
            };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseList/CaseListSelectedExportToExcel", data, function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/Legal/CaseList/CaseListExportToExcelDownload?fileName=" + response.Data);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        ExportAllToExcel: function () {
            $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseList/CaseListExportToExcel", function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/Legal/CaseList/CaseListExportToExcelDownload?fileName=" + response.Data);
                    $.showModalMessageBox("导出成功.");
                } else {
                    $.showModalMessageBox(response.Message);
                }
            });
        },

        ExportSelectedToExcelForManifest: function () {
            var caseNos = [];
            $("input[name='chkCaseId']:checked").each(
                function (i) { caseNos[i] = $(this).val(); }
            );
            if (caseNos.length < 1) {
                $.showModalMessageBox("请选择需要导出的案件.");
                return false;
            }
            var data = {
                caseNos: caseNos,
            };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseList/CaseListExportToExcelForManifest", data, function (response) {
                if (response.IsSuccess) {
                    window.open(AP_ROOT + AP_PAGE_ID + "/Legal/CaseList/CaseListExportToExcelDownload?fileName=" + response.Data);
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

            $("#SearchCondition_CasePhaseId").val('');

        },
        Selected: function (e) {
            if ($(e).prop('checked') == true) {
                $.checkbox.all("chkCaseId");
                $.checkbox.all("chkCaseAll");

            } else {
                $.checkbox.not("chkCaseId");
                $.checkbox.not("chkCaseAll");
            }
        },

        getCaseList: function (caseNos, callBack_Func) {
            var data = {
                caseNos: caseNos
            };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/Legal/CaseList/GetCaseListByCaseNos", data, function (response) {
                if (response.IsSuccess) {
                    if (callBack_Func != null) {
                        callBack_Func(response.Data.CaseList);
                    }
                }
            });
        }
    }
}

var court = {
    Courts:
        {
            Court: {
                CourtOfficer: {

                    AddIn: function (courtOfficerNo, courtOfficerName, courtOfficerInputLineName, courtOfficerInputName) {
                        
                        var existsUser = false;

                        $("a[name='" + courtOfficerInputLineName + "']").each(function () {
                            if ($(this).attr("courtofficerno") == courtOfficerNo) {
                                existsUser = true;
                                return true;
                            }
                        });

                        //重复

                        if (existsUser) return true;

                        var $tag = $("<span class='tag label label-info'>"
                                     + "<a name='" + courtOfficerInputLineName + "' style='color:white; width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'"
                                     + " courtofficerno='" + courtOfficerNo + "'"
                                     + " courtofficername='" + courtOfficerName + "'"
                                     + " title='' data-toggle='tooltip' data-container='body' href='javascript:void(0);'  onclick='javascript:court.Courts.Court.CourtOfficer.Edit(\"" + courtOfficerNo + "\")'  data-original-title=" + courtOfficerNo + " '>" + courtOfficerName + "</a>"
                                     + "<span class='courtofficerremove' data-role='remove'></span>"
                                   + "</span>");

                        
                        $("#" + courtOfficerInputName).before($tag);
                        
                        $("#" + courtOfficerInputName).css({
                            "width": 0
                        });
                        $tag.after(' ');

                    },

                    Remove: function (e) {
                        $(e).parent().parent().find("input").css({
                            "width": 100
                        });

                        $(e).parent().remove();
                        
                    },

                    Open: function (courtNo, callBackFunc) {

                        var data = {
                            courtNo: courtNo,
                        };
                        var url = AP_ROOT + AP_PAGE_ID + "/BAS/CourtOfficer/Create";
                        $.openLoading();
                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#courtOfficerModal').modal({ backdrop: 'static', keyboard: false });
                            $('#courtOfficerModal').on('hidden.bs.modal', function () {
                                $("#courtOfficerModal").remove();
                            });

                            $(document).off('click', '#btnCourtOfficerCreate').on('click', '#btnCourtOfficerCreate', function () {
                                javascript: court.Courts.Court.CourtOfficer.CreateUpdate(callBackFunc);
                            });
                        });
                    },

                    Edit: function (courtOfficerNo, callBackFunc) {

                        var data = {
                            courtOfficerNo: courtOfficerNo,
                        };
                        var url = AP_ROOT + AP_PAGE_ID + "/BAS/CourtOfficer/Edit";
                        $.openLoading();
                        $("<div></div>").load(url, data, function (result) {
                            $.closeLoading();
                            $(document.body).append(result);
                            $('#courtOfficerModal').modal({ backdrop: 'static', keyboard: false });
                            $('#courtOfficerModal').on('hidden.bs.modal', function () {
                                $("#courtOfficerModal").remove();
                            });

                            $(document).off('click', '#btnCourtOfficerCreate').on('click', '#btnCourtOfficerCreate', function () {
                                javascript: court.Courts.Court.CourtOfficer.CreateUpdate(callBackFunc);
                            });
                        });
                    },


                    CreateUpdate: function (callBackFunc) {
                        try {
                            var data = {};

                            if ($("#CourtOfficer_OfficerName").val() == '') {
                                $.showModalMessageBox("请输入姓名.");
                                return false;
                            }

                            data["CourtOfficer.OfficerNo"] = $("#CourtOfficer_OfficerNo").val();
                            data["CourtOfficer.CourtNo"] = $("#CourtOfficer_CourtNo").val();
                            data["CourtOfficer.OfficerName"] = $("#CourtOfficer_OfficerName").val();
                            data["CourtOfficer.Phone"] = $("#CourtOfficer_Phone").val();
                            data["CourtOfficer.Email"] = $("#CourtOfficer_Email").val();
                            data["CourtOfficer.Remark"] = $("#CourtOfficer_Remark").val();
                            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/BAS/CourtOfficer/CreateUpdate", data, function (response) {
                                if (response.IsSuccess) {
                                    if (callBackFunc != null) {
                                        
                                        callBackFunc(response.Data.OfficerNo, response.Data.OfficerName);
                                    }
                                    $('#courtOfficerModal').modal('hide');
                                }
                                else if (response.IsRedirect) {
                                    window.location = AP_ROOT + 'Home/Index';
                                } else {
                                    $.showModalMessageBox(response.Message);

                                }
                            });
                        } catch (e) {
                            alert(e);
                        }
                    },

                    CreateUpdate_CallBack_FirstIntanceJudge: function (firstIntanceJudgeNo, firstIntanceJudgeName) {
                        court.Courts.Court.CourtOfficer.AddIn(firstIntanceJudgeNo, firstIntanceJudgeName, "firstCourtOfficer", "Case_Basic_FirstIntanceJudge");
                     },

                    CreateUpdate_CallBack_FirstIntanceClerk: function (firstIntanceClerkNo, firstIntanceClerkName) {
                        court.Courts.Court.CourtOfficer.AddIn(firstIntanceClerkNo, firstIntanceClerkName, "firstCourtClerk", "Case_Basic_FirstIntanceClerk");
                    },

                    CreateUpdate_CallBack_SecondIntanceJudge: function (secondIntanceJudgeNo, secondIntanceJudgeName) {
                        court.Courts.Court.CourtOfficer.AddIn(secondIntanceJudgeNo, secondIntanceJudgeName, "secondCourtOfficer", "Case_Basic_SecondIntanceJudge");
                    },

                    CreateUpdate_CallBack_SecondIntanceClerk: function (secondIntanceClerkNo, secondIntanceClerkName) {
                        court.Courts.Court.CourtOfficer.AddIn(secondIntanceClerkNo, secondIntanceClerkName, "secondCourtClerk", "Case_Basic_SecondIntanceClerk");
                    },

                    CreateUpdate_CallBack_ExecutionIntanceJudge: function (executionIntanceJudgeNo, executionIntanceJudgeName) {
                        court.Courts.Court.CourtOfficer.AddIn(executionIntanceJudgeNo, executionIntanceJudgeName, "executionCourtOfficer", "Case_Basic_ExecutionIntanceJudge");
                    },

                    CreateUpdate_CallBack_ExecutionIntanceClerk: function (executionIntanceClerkNo, executionIntanceClerkName) {
                        court.Courts.Court.CourtOfficer.AddIn(executionIntanceClerkNo, executionIntanceClerkName, "executionCourtOfficer", "Case_Basic_ExecutionIntanceClerk");
                    },

                    CreateUpdate_CallBack_LastIntanceJudge: function (lastIntanceJudgeNo, lastIntanceJudgeName) {
                        court.Courts.Court.CourtOfficer.AddIn(lastIntanceJudgeNo, lastIntanceJudgeName, "lastCourtOfficer", "Case_Basic_LastIntanceJudge");
                    },

                    CreateUpdate_CallBack_LastIntanceClerk: function (lastIntanceClerkNo, lastIntanceClerkName) {
                        court.Courts.Court.CourtOfficer.AddIn(lastIntanceClerkNo, lastIntanceClerkName, "lastCourtOfficer", "Case_Basic_LastIntanceClerk");
                    },
                },
            }
        }
}


